import math
import re
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


HERE = Path(__file__).resolve().parent

MODEL_CONFIG = {
    "vocab_size": 40_000,          # overwritten by the tokenizer's vocab size
    "embedding_rank": 256,
    "context_length": 8192,
    "emb_dim": 640,
    "n_heads": 10,
    "n_kv_groups": 5,
    "head_dim": 64,
    "hidden_dim": 2560,
    "qk_norm": True,
    "rope_base": 1_000_000.0,
    "n_prelude": 2,                # blocks before the loop (run once)
    "n_core": 16,                  # weight-tied blocks inside the loop
    "n_coda": 2,                   # blocks after the loop (run once)
    "n_loops": 2,                  # default loop iterations T (training + inference)
}

N_LOOPS_TRAIN = 2
RANDOM_LOOPS = False               # sample T ~ U{1, N_LOOPS_TRAIN} per micro-batch
N_GRAD_LOOPS = 2                   # backprop through the last k loop iterations only
EVAL_LOOPS = [1, 2, 4, 8]

TOKENIZER_PATH = HERE / "tokenizer_output" / "tokenizer_qwen40k.json"

DATASET_NAME = "HuggingFaceFW/fineweb-edu"
DATASET_SUBSET = "sample-10BT"
SEQ_LEN = 2048
PHYSICAL_BATCH_SIZE = 1
ACCUMULATION_STEPS = 4
TRAIN_TOKENS_TARGET = 1_000_000_000
VAL_TOKENS_TARGET = 5_000_000
VAL_HOLDOUT_DOCS = 10_000
SHUFFLE_BUFFER = 10_000
DATA_SEED = 123

LEARNING_RATE = 3e-4
WEIGHT_DECAY = 0.01
GRAD_CLIP = 1.0
WARMUP_STEPS = 0
USE_BF16_AUTOCAST = True
MODEL_SEED = 123

LOG_EVERY = 10
EVAL_EVERY = 0                     # 0 = only at the end
EVAL_LOOPS_TOKENS = 1_000_000
SAVE_EVERY = 2000                  # 0 = only at the end
CHECKPOINT_PATH = HERE / "checkpoints" / "looped_agri_slm.pt"
USE_MLFLOW = False
MLFLOW_EXPERIMENT = "fineweb-edu-pilot-training"
SAMPLE_PROMPT = "Rice blast disease is caused by"


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.scale = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        dtype = x.dtype
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x * self.scale.float()).to(dtype)


def compute_rope_params(head_dim, theta_base, context_length, dtype=torch.float32):
    inv_freq = 1.0 / (theta_base ** (
        torch.arange(0, head_dim, 2, dtype=dtype)[: head_dim // 2].float() / head_dim))
    positions = torch.arange(context_length, dtype=dtype)
    angles = positions[:, None] * inv_freq[None, :]
    angles = torch.cat([angles, angles], dim=1)
    return torch.cos(angles), torch.sin(angles)


def apply_rope(x, cos, sin):
    _, _, seq_len, head_dim = x.shape
    x1, x2 = x[..., : head_dim // 2], x[..., head_dim // 2:]
    rotated = torch.cat((-x2, x1), dim=-1)
    c = cos[:seq_len, :].unsqueeze(0).unsqueeze(0)
    s = sin[:seq_len, :].unsqueeze(0).unsqueeze(0)
    return ((x * c) + (rotated * s)).to(dtype=x.dtype)


class GroupedQueryAttention(nn.Module):
    def __init__(self, d_in, num_heads, num_kv_groups, head_dim=None, qk_norm=False):
        super().__init__()
        assert num_heads % num_kv_groups == 0, "num_heads must be divisible by num_kv_groups"
        self.num_heads = num_heads
        self.num_kv_groups = num_kv_groups
        self.group_size = num_heads // num_kv_groups
        self.head_dim = head_dim or (d_in // num_heads)
        self.d_out = num_heads * self.head_dim

        self.W_query = nn.Linear(d_in, self.d_out, bias=False)
        self.W_key = nn.Linear(d_in, num_kv_groups * self.head_dim, bias=False)
        self.W_value = nn.Linear(d_in, num_kv_groups * self.head_dim, bias=False)
        self.out_proj = nn.Linear(self.d_out, d_in, bias=False)
        self.q_norm = RMSNorm(self.head_dim) if qk_norm else None
        self.k_norm = RMSNorm(self.head_dim) if qk_norm else None

    def forward(self, x, cos, sin):
        b, n, _ = x.shape
        q = self.W_query(x).view(b, n, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.W_key(x).view(b, n, self.num_kv_groups, self.head_dim).transpose(1, 2)
        v = self.W_value(x).view(b, n, self.num_kv_groups, self.head_dim).transpose(1, 2)

        if self.q_norm is not None:
            q, k = self.q_norm(q), self.k_norm(k)

        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        k = k.repeat_interleave(self.group_size, dim=1)
        v = v.repeat_interleave(self.group_size, dim=1)

        ctx = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        ctx = ctx.transpose(1, 2).reshape(b, n, self.d_out)
        return self.out_proj(ctx)


class FeedForward(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.fc1 = nn.Linear(cfg["emb_dim"], cfg["hidden_dim"], bias=False)
        self.fc2 = nn.Linear(cfg["emb_dim"], cfg["hidden_dim"], bias=False)
        self.fc3 = nn.Linear(cfg["hidden_dim"], cfg["emb_dim"], bias=False)

    def forward(self, x):
        return self.fc3(F.silu(self.fc1(x)) * self.fc2(x))


class TransformerBlock(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.att = GroupedQueryAttention(
            cfg["emb_dim"], cfg["n_heads"], cfg["n_kv_groups"],
            cfg["head_dim"], cfg["qk_norm"])
        self.ff = FeedForward(cfg)
        self.norm1 = RMSNorm(cfg["emb_dim"])
        self.norm2 = RMSNorm(cfg["emb_dim"])

    def forward(self, x, cos, sin):
        x = x + self.att(self.norm1(x), cos, sin)
        return x + self.ff(self.norm2(x))


class FactorizedEmbedding(nn.Module):
    def __init__(self, vocab_size, rank, emb_dim):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, rank)
        self.proj = nn.Linear(rank, emb_dim, bias=False)

    def forward(self, ids):
        return self.proj(self.embedding(ids))


class LoopedQwen3Model(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        if cfg["n_core"] < 1:
            raise ValueError("n_core must be >= 1")
        self.cfg = cfg
        d = cfg["emb_dim"]

        self.tok_emb = FactorizedEmbedding(cfg["vocab_size"], cfg["embedding_rank"], d)
        self.prelude = nn.ModuleList([TransformerBlock(cfg) for _ in range(cfg["n_prelude"])])
        self.adapter = nn.Linear(2 * d, d, bias=False)
        self.core = nn.ModuleList([TransformerBlock(cfg) for _ in range(cfg["n_core"])])
        self.loop_norm = RMSNorm(d)
        self.coda = nn.ModuleList([TransformerBlock(cfg) for _ in range(cfg["n_coda"])])
        self.final_norm = RMSNorm(d)
        self.output_proj = nn.Linear(d, cfg["embedding_rank"], bias=False)

        head_dim = cfg["head_dim"] or d // cfg["n_heads"]
        cos, sin = compute_rope_params(head_dim, cfg["rope_base"], cfg["context_length"])
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def recur(self, h, x):
        h = self.adapter(torch.cat([h, x], dim=-1))
        for block in self.core:
            h = block(h, self.cos, self.sin)
        return self.loop_norm(h)

    def forward(self, ids, n_loops=None, n_grad_loops=None):
        if ids.shape[1] > self.cfg["context_length"]:
            raise ValueError(f"sequence length {ids.shape[1]} exceeds context_length")
        n_loops = self.cfg["n_loops"] if n_loops is None else n_loops
        if n_loops < 1:
            raise ValueError("n_loops must be >= 1")
        n_grad_loops = n_loops if n_grad_loops is None else max(1, min(n_grad_loops, n_loops))

        x = self.tok_emb(ids)
        for block in self.prelude:
            x = block(x, self.cos, self.sin)

        h = torch.zeros_like(x)
        n_free = n_loops - n_grad_loops
        if n_free > 0:
            with torch.no_grad():
                for _ in range(n_free):
                    h = self.recur(h, x)
            h = h.detach()
        for _ in range(n_grad_loops):
            h = self.recur(h, x)

        for block in self.coda:
            h = block(h, self.cos, self.sin)
        h = self.output_proj(self.final_norm(h))
        return F.linear(h, self.tok_emb.embedding.weight)


class Qwen3Tokenizer:
    _SPECIALS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<think>", "</think>", "<ENT>"]
    _SPLIT_RE = re.compile(r"(<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|<think>|</think>)")

    def __init__(self, tokenizer_file_path):
        from tokenizers import Tokenizer
        tok_file = Path(tokenizer_file_path)
        if not tok_file.exists():
            raise FileNotFoundError(f"Tokenizer file not found: {tok_file}")
        self._tok = Tokenizer.from_file(str(tok_file))
        self.vocab_size = self._tok.get_vocab_size()
        self._special_to_id = {}
        for t in self._SPECIALS:
            tid = self._tok.token_to_id(t)
            if tid is not None:
                self._special_to_id[t] = tid
        eos = self._special_to_id.get("<|endoftext|>")
        self.pad_token_id = eos if eos is not None else 0
        self.eos_token_id = self.pad_token_id

    def encode(self, text):
        ids = []
        for part in filter(None, self._SPLIT_RE.split(text)):
            if part in self._special_to_id:
                ids.append(self._special_to_id[part])
            else:
                ids.extend(self._tok.encode(part).ids)
        return ids

    def decode(self, ids):
        return self._tok.decode(ids, skip_special_tokens=False)


class PackedDataset(torch.utils.data.IterableDataset):
    def __init__(self, hf_stream, tokenizer, seq_len, max_tokens):
        self.hf_stream = hf_stream
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.max_tokens = max_tokens

    def __iter__(self):
        buffer, tokens_yielded = [], 0
        for example in self.hf_stream:
            if tokens_yielded >= self.max_tokens:
                break
            text = example.get("text", "")
            if not text.strip():
                continue
            new_ids = self.tokenizer.encode(text)
            if any(t < 0 or t >= self.tokenizer.vocab_size for t in new_ids):
                raise ValueError("Tokenizer produced invalid token IDs.")
            buffer.extend(new_ids)
            while len(buffer) >= self.seq_len + 1 and tokens_yielded < self.max_tokens:
                block = torch.tensor(buffer[: self.seq_len + 1], dtype=torch.long)
                buffer = buffer[self.seq_len + 1:]
                tokens_yielded += self.seq_len
                yield block[:-1], block[1:]


def build_loaders(tokenizer):
    from datasets import load_dataset

    raw_stream = load_dataset(
        DATASET_NAME, name=DATASET_SUBSET, split="train", streaming=True,
    ).shuffle(seed=DATA_SEED, buffer_size=SHUFFLE_BUFFER)
    val_stream = raw_stream.take(VAL_HOLDOUT_DOCS)
    train_stream = raw_stream.skip(VAL_HOLDOUT_DOCS)

    pin = torch.cuda.is_available()
    train_loader = torch.utils.data.DataLoader(
        PackedDataset(train_stream, tokenizer, SEQ_LEN, TRAIN_TOKENS_TARGET),
        batch_size=PHYSICAL_BATCH_SIZE, pin_memory=pin, drop_last=True)

    def val_loader(max_tokens=VAL_TOKENS_TARGET):
        return torch.utils.data.DataLoader(
            PackedDataset(val_stream, tokenizer, SEQ_LEN, max_tokens),
            batch_size=PHYSICAL_BATCH_SIZE, pin_memory=pin, drop_last=True)

    return train_loader, val_loader


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def autocast_ctx(device):
    enabled = USE_BF16_AUTOCAST and device.type == "cuda"
    return torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=enabled)


def lm_loss(logits, targets):
    return F.cross_entropy(logits.float().view(-1, logits.size(-1)), targets.view(-1))


@torch.no_grad()
def evaluate(model, loader, device, n_loops):
    model.eval()
    total, batches = 0.0, 0
    for inputs, targets in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        with autocast_ctx(device):
            logits = model(inputs, n_loops=n_loops)
        total += lm_loss(logits, targets).item()
        batches += 1
    model.train()
    avg = total / max(batches, 1)
    return avg, math.exp(min(avg, 20))


@torch.no_grad()
def generate(model, tokenizer, prompt, device, n_loops=None, max_new_tokens=150,
             temperature=1.0, top_k=50, top_p=0.95, repetition_penalty=1.1):
    model.eval()
    ids = torch.tensor([tokenizer.encode(prompt)], device=device)
    out_ids = []
    for _ in range(max_new_tokens):
        if ids.shape[1] >= model.cfg["context_length"]:
            break
        with autocast_ctx(device):
            logits = model(ids, n_loops=n_loops)[:, -1].float()
        if repetition_penalty != 1.0:
            for t in set(ids[0].tolist()):
                v = logits[0, t]
                logits[0, t] = v / repetition_penalty if v > 0 else v * repetition_penalty
        if temperature <= 0:
            nxt = logits.argmax(dim=-1, keepdim=True)
        else:
            logits = logits / temperature
            if top_k:
                kth = torch.topk(logits, min(top_k, logits.size(-1)))[0][..., -1, None]
                logits = logits.masked_fill(logits < kth, float("-inf"))
            if top_p and top_p < 1.0:
                s_logits, s_idx = torch.sort(logits, descending=True, dim=-1)
                probs = F.softmax(s_logits, dim=-1)
                cum = torch.cumsum(probs, dim=-1) - probs
                s_logits = s_logits.masked_fill(cum > top_p, float("-inf"))
                logits = torch.full_like(logits, float("-inf")).scatter(-1, s_idx, s_logits)
            nxt = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)
        if nxt.item() == tokenizer.eos_token_id:
            break
        out_ids.append(nxt.item())
        ids = torch.cat([ids, nxt], dim=1)
    model.train()
    return tokenizer.decode(out_ids)


def save_checkpoint(model, optimizer, scheduler, step):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "config": model.cfg,
        "step": step,
    }, CHECKPOINT_PATH)
    print(f"saved checkpoint to {CHECKPOINT_PATH} (step {step})")


def main():
    device = get_device()
    tokenizer = Qwen3Tokenizer(TOKENIZER_PATH)
    cfg = dict(MODEL_CONFIG, vocab_size=tokenizer.vocab_size, n_loops=N_LOOPS_TRAIN)

    torch.manual_seed(MODEL_SEED)
    model = LoopedQwen3Model(cfg).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    n_unique = cfg["n_prelude"] + cfg["n_core"] + cfg["n_coda"]
    eff_depth = cfg["n_prelude"] + cfg["n_core"] * N_LOOPS_TRAIN + cfg["n_coda"]
    print(f"device={device} | params={n_params:,} | unique blocks={n_unique} | "
          f"effective depth at T={N_LOOPS_TRAIN}: {eff_depth} blocks")

    train_loader, val_loader = build_loaders(tokenizer)
    total_physical_steps = TRAIN_TOKENS_TARGET // (SEQ_LEN * PHYSICAL_BATCH_SIZE)
    total_steps = total_physical_steps // ACCUMULATION_STEPS
    print(f"optimizer steps: {total_steps} | tokens/step: "
          f"{SEQ_LEN * PHYSICAL_BATCH_SIZE * ACCUMULATION_STEPS:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

    def lr_lambda(step):
        if step < WARMUP_STEPS:
            return (step + 1) / WARMUP_STEPS
        progress = (step - WARMUP_STEPS) / max(1, total_steps - WARMUP_STEPS)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    if USE_MLFLOW:
        import mlflow
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        mlflow.start_run(run_name="looped-agri-slm")
        mlflow.log_params({**{k: v for k, v in cfg.items()}, "total_params": n_params,
                           "n_loops_train": N_LOOPS_TRAIN, "random_loops": RANDOM_LOOPS,
                           "n_grad_loops": N_GRAD_LOOPS, "lr": LEARNING_RATE,
                           "seq_len": SEQ_LEN, "accumulation_steps": ACCUMULATION_STEPS,
                           "train_tokens_target": TRAIN_TOKENS_TARGET})

    model.train()
    optimizer.zero_grad(set_to_none=True)
    opt_step, accum_loss, t0 = 0, 0.0, time.time()

    for micro_step, (inputs, targets) in enumerate(train_loader):
        inputs, targets = inputs.to(device), targets.to(device)
        n_loops = (int(torch.randint(1, N_LOOPS_TRAIN + 1, (1,)))
                   if RANDOM_LOOPS else N_LOOPS_TRAIN)

        with autocast_ctx(device):
            logits = model(inputs, n_loops=n_loops, n_grad_loops=N_GRAD_LOOPS)
        loss = lm_loss(logits, targets)
        (loss / ACCUMULATION_STEPS).backward()
        accum_loss += loss.item() / ACCUMULATION_STEPS

        if (micro_step + 1) % ACCUMULATION_STEPS != 0:
            continue

        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        opt_step += 1

        if opt_step % LOG_EVERY == 0 or opt_step == 1:
            dt = time.time() - t0
            tok_s = LOG_EVERY * ACCUMULATION_STEPS * SEQ_LEN * PHYSICAL_BATCH_SIZE / dt
            lr = scheduler.get_last_lr()[0]
            print(f"step {opt_step:6d}/{total_steps} | loss {accum_loss:.4f} | "
                  f"ppl {math.exp(min(accum_loss, 20)):.2f} | lr {lr:.2e} | "
                  f"grad {grad_norm:.2f} | tok/s {tok_s:.0f}")
            if USE_MLFLOW:
                mlflow.log_metrics({"loss": accum_loss, "learning_rate": lr,
                                    "global_grad_norm": float(grad_norm),
                                    "tokens_per_sec": tok_s}, step=opt_step)
            t0 = time.time()
        accum_loss = 0.0

        if EVAL_EVERY and opt_step % EVAL_EVERY == 0:
            val_loss, val_ppl = evaluate(model, val_loader(), device, N_LOOPS_TRAIN)
            print(f"step {opt_step} | val loss {val_loss:.4f} | val ppl {val_ppl:.2f}")
            if USE_MLFLOW:
                mlflow.log_metrics({"val_loss": val_loss, "val_perplexity": val_ppl}, step=opt_step)
        if SAVE_EVERY and opt_step % SAVE_EVERY == 0:
            save_checkpoint(model, optimizer, scheduler, opt_step)

    save_checkpoint(model, optimizer, scheduler, opt_step)

    val_loss, val_ppl = evaluate(model, val_loader(), device, N_LOOPS_TRAIN)
    print(f"\nVal (T={N_LOOPS_TRAIN}) | loss {val_loss:.4f} | ppl {val_ppl:.2f}")
    if USE_MLFLOW:
        mlflow.log_metrics({"val_loss": val_loss, "val_perplexity": val_ppl}, step=opt_step)

    print(f"\nVal loss vs loop iterations (first {EVAL_LOOPS_TOKENS:,} val tokens):")
    for t in EVAL_LOOPS:
        l, p = evaluate(model, val_loader(EVAL_LOOPS_TOKENS), device, t)
        print(f"  T={t:3d} | loss {l:.4f} | ppl {p:.2f}")
        if USE_MLFLOW:
            mlflow.log_metrics({f"val_loss_T{t}": l})

    print(f"\nSample (T={N_LOOPS_TRAIN}):\n{SAMPLE_PROMPT}"
          f"{generate(model, tokenizer, SAMPLE_PROMPT, device, n_loops=N_LOOPS_TRAIN)}")
    if USE_MLFLOW:
        mlflow.end_run()


if __name__ == "__main__":
    main()
