import argparse
import math
import os
import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from tokenizers import Tokenizer

from eval.agri_slm import Qwen3Model, DEFAULT_CONFIG

IGNORE = -100

class SFTDataset(Dataset):
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        item = self.items[index]
        return (
            torch.tensor(item["input_ids"], dtype=torch.long),
            torch.tensor(item["labels"], dtype=torch.long),
        )

def collate_fn_factory(pad_id):
    def collate(batch):
        batch_size = len(batch)
        max_length = max(x.size(0) for x, _ in batch)

        input_ids = torch.full((batch_size, max_length), pad_id, dtype=torch.long)
        labels = torch.full((batch_size, max_length), IGNORE, dtype=torch.long)

        for i, (x, y) in enumerate(batch):
            input_ids[i, :len(x)] = x
            labels[i, :len(y)] = y

        return input_ids, labels
    return collate

@torch.no_grad()
def evaluate(model, loader, device, amp_dtype, max_batches=None):
    model.eval()
    loss_sum = 0.0
    n_tokens = 0

    for batch_idx, (x, y) in enumerate(loader):
        if max_batches is not None and batch_idx >= max_batches:
            break
        
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        supervised = (y != IGNORE).sum().item()
        if supervised == 0:
            continue

        if device.type == "cuda":
            with torch.autocast(device_type="cuda", dtype=amp_dtype):
                logits = model(x)
        else:
            logits = model(x)

        batch_loss = F.cross_entropy(
            logits.reshape(-1, logits.size(-1)).float(),
            y.reshape(-1),
            ignore_index=IGNORE,
            reduction="sum",
        )
        loss_sum += batch_loss.item()
        n_tokens += supervised

    if n_tokens == 0:
        return {"val_loss": float("inf"), "val_ppl": float("inf"), "val_tokens": 0}
        
    val_loss = loss_sum / n_tokens
    return {
        "val_loss": val_loss,
        "val_ppl": math.exp(min(val_loss, 20)),
        "val_tokens": n_tokens,
    }

def save_checkpoint(path, model, base_cfg, sft_cfg, step, metrics, optimizer=None, scheduler=None, scaler=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # If model is wrapped in PEFT or DDP, we want to save the unwrapped state
    # Wait, PEFT saving is handled differently (save_pretrained), but we'll extract the dict
    if hasattr(model, "peft_config"):
        state_dict = {}
        for k, v in model.state_dict().items():
            if "lora" in k or "modules_to_save" in k:
                state_dict[k] = v
    else:
        state_dict = model.state_dict()

    payload = {
        "model": state_dict,
        "config": base_cfg,
        "sft_config": asdict(sft_cfg) if not isinstance(sft_cfg, dict) else sft_cfg,
        "chat_format_version": "chatml-v1",
        "step": step,
        "metrics": metrics,
    }

    if optimizer is not None:
        payload["optimizer"] = optimizer.state_dict()
    if scheduler is not None:
        payload["scheduler"] = scheduler.state_dict()
    if scaler is not None:
        payload["scaler"] = scaler.state_dict()

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp_path)
    os.replace(tmp_path, path)

def parse_args():
    parser = argparse.ArgumentParser(description="SFT Training Script for Agri-SLM")
    parser.add_argument("--base_ckpt", type=str, required=True, help="Path to base model checkpoint")
    parser.add_argument("--tokenizer", type=str, required=True, help="Path to tokenizer JSON")
    parser.add_argument("--train_pt", type=str, required=True, help="Path to tokenized train.pt dataset")
    parser.add_argument("--val_pt", type=str, required=True, help="Path to tokenized val.pt dataset")
    parser.add_argument("--out_dir", type=str, default="checkpoints/sft_run")
    
    parser.add_argument("--use_lora", action="store_true", help="Enable LoRA fine-tuning")
    parser.add_argument("--lora_rank", type=int, default=8)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)

    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--micro_batch_size", type=int, default=8)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--warmup_ratio", type=float, default=0.05)
    
    parser.add_argument("--eval_every", type=int, default=100)
    parser.add_argument("--log_every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Reproducibility
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")
    
    use_bf16 = (device.type == "cuda" and torch.cuda.is_bf16_supported())
    amp_dtype = torch.bfloat16 if use_bf16 else (torch.float16 if device.type == "cuda" else torch.float32)
    print(f"Selected compute dtype: {amp_dtype}")

    # Load tokenizer
    tok = Tokenizer.from_file(args.tokenizer)
    pad_id = tok.token_to_id("<|im_end|>")
    if pad_id is None:
        pad_id = 0
        
    # Load dataset
    print(f"Loading datasets from {args.train_pt} and {args.val_pt}")
    train_items = torch.load(args.train_pt)
    val_items = torch.load(args.val_pt)
    
    train_dataset = SFTDataset(train_items)
    val_dataset = SFTDataset(val_items)
    
    collate = collate_fn_factory(pad_id)
    
    train_loader = DataLoader(train_dataset, batch_size=args.micro_batch_size, shuffle=True, collate_fn=collate, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=args.micro_batch_size, shuffle=False, collate_fn=collate, drop_last=False)
    
    # Load model
    print(f"Loading base model from {args.base_ckpt}")
    checkpoint = torch.load(args.base_ckpt, map_location="cpu", weights_only=False)
    cfg = checkpoint.get("config", DEFAULT_CONFIG)
    
    model = Qwen3Model(cfg)
    model.load_state_dict(checkpoint["model"], strict=True)
    
    if args.use_lora:
        print("Applying LoRA...")
        try:
            from peft import LoraConfig, get_peft_model
        except ImportError:
            raise ImportError("Please install `peft` to use LoRA: pip install peft")
            
        lora_config = LoraConfig(
            r=args.lora_rank,
            lora_alpha=args.lora_alpha,
            target_modules=["W_query", "W_key", "W_value", "out_proj", "fc1", "fc2", "fc3"],
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
    
    model = model.to(device)
    
    # Optimizer
    decay_params = []
    no_decay_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad: continue
        if name.endswith(".bias") or "norm" in name.lower() or "ln_" in name.lower():
            no_decay_params.append(param)
        else:
            decay_params.append(param)
            
    optimizer = torch.optim.AdamW(
        [
            {"params": decay_params, "weight_decay": args.weight_decay},
            {"params": no_decay_params, "weight_decay": 0.0},
        ],
        lr=args.lr,
        betas=(0.9, 0.95),
    )
    
    updates_per_epoch = len(train_loader) // args.grad_accum
    if updates_per_epoch < 1:
        raise ValueError("Not enough training batches for one complete gradient-accumulation update.")
        
    total_steps = updates_per_epoch * args.epochs
    warmup_steps = max(1, int(total_steps * args.warmup_ratio))
    
    from torch.optim.lr_scheduler import LambdaLR
    def lr_multiplier(step):
        if step < warmup_steps: return (step + 1) / warmup_steps
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        progress = min(max(progress, 0.0), 1.0)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return 0.10 + 0.90 * cosine
        
    scheduler = LambdaLR(optimizer, lr_lambda=lr_multiplier)
    
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda" and amp_dtype == torch.float16))
    
    # Training Loop
    RUN_DIR = Path(args.out_dir)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    
    best_val = float("inf")
    bad_evals = 0
    global_step = 0
    history = []
    
    baseline_metrics = evaluate(model, val_loader, device, amp_dtype)
    print(f"Step 0 validation: {baseline_metrics}")
    
    model.train()
    optimizer.zero_grad(set_to_none=True)
    
    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")
        running_loss = 0.0
        running_batches = 0
        pending_micro_batches = 0
        
        for batch_idx, (x, y) in enumerate(train_loader):
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            
            if (y != IGNORE).sum().item() == 0:
                continue
                
            amp_context = torch.autocast(device_type="cuda", dtype=amp_dtype) if device.type == "cuda" else torch.autocast(device_type="cpu", enabled=False)
            
            with amp_context:
                logits = model(x)
                loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)).float(), y.reshape(-1), ignore_index=IGNORE)
                
            scaler.scale(loss / args.grad_accum).backward()
            
            running_loss += loss.item()
            running_batches += 1
            pending_micro_batches += 1
            
            if pending_micro_batches < args.grad_accum:
                continue
                
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            
            pending_micro_batches = 0
            global_step += 1
            
            if global_step % args.log_every == 0:
                train_loss = running_loss / max(1, running_batches)
                current_lr = optimizer.param_groups[0]["lr"]
                history.append({"epoch": epoch + 1, "step": global_step, "train_loss": train_loss, "lr": current_lr})
                print(f"step={global_step}/{total_steps} train_loss={train_loss:.4f} lr={current_lr:.3e}")
                running_loss = 0.0
                running_batches = 0
                
            if global_step % args.eval_every == 0 or global_step == total_steps:
                metrics = evaluate(model, val_loader, device, amp_dtype)
                metrics.update({"epoch": epoch + 1, "step": global_step})
                print(f"Validation at step {global_step}: {metrics}")
                
                save_checkpoint(RUN_DIR / "last.pt", model, cfg, vars(args), global_step, metrics, optimizer, scheduler, scaler)
                
                if metrics["val_loss"] < best_val:
                    best_val = metrics["val_loss"]
                    bad_evals = 0
                    save_checkpoint(RUN_DIR / "best.pt", model, cfg, vars(args), global_step, metrics)
                else:
                    bad_evals += 1
                    
                model.train()
                if bad_evals >= 2:
                    print("Early stopping triggered.")
                    break
        if bad_evals >= 2:
            break

    final_metrics = evaluate(model, val_loader, device, amp_dtype)
    save_checkpoint(RUN_DIR / "last.pt", model, cfg, vars(args), global_step, final_metrics, optimizer, scheduler, scaler)
    
    with open(RUN_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    with open(RUN_DIR / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=2)
        
    print("\nTraining completed.")

if __name__ == "__main__":
    main()
