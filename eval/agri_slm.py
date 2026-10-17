#!/usr/bin/env python3
"""Agri-SLM inference — self-contained.

A 134M-parameter Qwen3-style decoder trained from scratch on Indian agriculture
text. This file has no dependency on the training code: it defines the
architecture, loads a checkpoint, and generates.

Requires only: torch, tokenizers  (huggingface_hub if loading from the Hub)

Quick start
-----------
    # one-off generation
    python agri_slm.py --prompt "Rice blast disease is caused by"

    # interactive
    python agri_slm.py --interactive

    # explicit local files
    python agri_slm.py --ckpt final.pt --tokenizer tokenizer.json --interactive

As a library
------------
    from agri_slm import AgriSLM
    model = AgriSLM.from_pretrained("luffy19/custom_tokenizer")
    print(model.generate("Integrated pest management in cotton involves"))

Decoding defaults are the ones that measured best on this model; see README.md
for the sweep they came from. In short: greedy decoding degenerates into
verbatim loops, and a repetition penalty is what fixes it.
"""

import argparse
import math
import os
import re
from pathlib import Path
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "vocab_size": 40000,
    "embedding_rank": 256,
    "context_length": 8192,
    "emb_dim": 640,
    "n_heads": 10,
    "n_layers": 20,
    "hidden_dim": 2560,
    "head_dim": 64,
    "qk_norm": True,
    "n_kv_groups": 5,
    "rope_base": 1000000.0,
}


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
    b, h, seq_len, head_dim = x.shape
    x1, x2 = x[..., : head_dim // 2], x[..., head_dim // 2:]
    rotated = torch.cat((-x2, x1), dim=-1)
    c = cos[:seq_len, :].unsqueeze(0).unsqueeze(0)
    s = sin[:seq_len, :].unsqueeze(0).unsqueeze(0)
    return ((x * c) + (rotated * s)).to(dtype=x.dtype)


class GroupedQueryAttention(nn.Module):
    def __init__(self, d_in, num_heads, num_kv_groups, head_dim=None, qk_norm=False):
        super().__init__()
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

        # Fused kernel: never materializes the (b, heads, n, n) attention matrix.
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
        return self.fc3(F.silu(self.fc1(x)) * self.fc2(x))   # SwiGLU


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
    """Low-rank embedding: vocab -> rank -> emb_dim. The rank matrix is also
    tied to the output head, which is why the model is only 134M at 40k vocab."""

    def __init__(self, vocab_size, rank, emb_dim):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, rank)
        self.proj = nn.Linear(rank, emb_dim, bias=False)

    def forward(self, ids):
        return self.proj(self.embedding(ids))


class Qwen3Model(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.tok_emb = FactorizedEmbedding(
            cfg["vocab_size"], cfg["embedding_rank"], cfg["emb_dim"])
        self.trf_blocks = nn.ModuleList(
            [TransformerBlock(cfg) for _ in range(cfg["n_layers"])])
        self.final_norm = RMSNorm(cfg["emb_dim"])
        self.output_proj = nn.Linear(cfg["emb_dim"], cfg["embedding_rank"], bias=False)

        head_dim = cfg["head_dim"] or cfg["emb_dim"] // cfg["n_heads"]
        cos, sin = compute_rope_params(
            head_dim, cfg["rope_base"], cfg["context_length"])
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def forward(self, ids):
        x = self.tok_emb(ids)
        for block in self.trf_blocks:
            x = block(x, self.cos, self.sin)
        x = self.output_proj(self.final_norm(x))
        # Output head tied to the embedding table.
        return F.linear(x, self.tok_emb.embedding.weight)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class AgriTokenizer:
    """Wraps a `tokenizers` JSON file. Special tokens are split out before BPE
    so each maps to exactly one id."""

    _SPECIALS = ["<|endoftext|>", "<|im_start|>", "<|im_end|>",
                 "<think>", "</think>", "<ENT>"]
    _SPLIT_RE = re.compile(
        r"(<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|<think>|</think>)")

    def __init__(self, path):
        from tokenizers import Tokenizer
        self._tok = Tokenizer.from_file(str(path))
        self.vocab_size = self._tok.get_vocab_size()
        self._special = {t: self._tok.token_to_id(t) for t in self._SPECIALS
                         if self._tok.token_to_id(t) is not None}
        eos = self._special.get("<|endoftext|>")
        self.eos_token_id = eos if eos is not None else 0
        self.pad_token_id = self.eos_token_id

    def encode(self, text: str) -> List[int]:
        ids = []
        for part in filter(None, self._SPLIT_RE.split(text)):
            if part in self._special:
                ids.append(self._special[part])
            else:
                ids.extend(self._tok.encode(part).ids)
        return ids

    def decode(self, ids: List[int]) -> str:
        return self._tok.decode(ids, skip_special_tokens=False)


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

class AgriSLM:
    """Load a checkpoint and generate text.

    Defaults come from a measured sweep over decoding settings, not taste. The
    important one is `repetition_penalty`: with it off and temperature at 0 this
    model produces 37-token verbatim loops.
    """

    def __init__(self, model, tokenizer, device=None):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device or next(model.parameters()).device

    # -- constructors -------------------------------------------------------

    @classmethod
    def from_files(cls, ckpt, tokenizer, device=None, dtype=None):
        device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu"))
        if dtype is None:
            dtype = torch.bfloat16 if device.type == "cuda" else torch.float32

        blob = torch.load(ckpt, map_location="cpu", weights_only=False)
        state = blob["model"] if "model" in blob else blob
        cfg = dict(blob.get("config") or DEFAULT_CONFIG)

        tok = AgriTokenizer(tokenizer)
        cfg["vocab_size"] = tok.vocab_size

        model = Qwen3Model(cfg)
        missing, unexpected = model.load_state_dict(state, strict=False)
        # The training checkpoints carry instrumentation buffers this
        # inference-only definition does not declare; genuine weight mismatches
        # would show up as `missing`, which must stay empty.
        if missing:
            raise RuntimeError(f"checkpoint is missing weights: {missing[:5]}")
        model.to(device=device, dtype=dtype).eval()
        return cls(model, tok, device)

    @classmethod
    def from_pretrained(cls, repo_id="luffy19/custom_tokenizer",
                        ckpt_file=None, tokenizer_file=None,
                        token=None, device=None, dtype=None):
        """Download from the HuggingFace Hub. Needs `huggingface_hub`, and a
        token if the repo is private."""
        from huggingface_hub import hf_hub_download

        token = token or os.environ.get("HF_TOKEN")
        defaults = {
            "luffy19/custom_tokenizer": ("hybrid40k/final.pt",
                                         "tokenizer/tokenizer_final.json"),
            "luffy19/agri-slm_qwen40k": ("qwen40k/final.pt", "tokenizer/tokenizer_final.json"),
        }
        d_ckpt, d_tok = defaults.get(repo_id, (None, None))
        ckpt_file = ckpt_file or d_ckpt
        tokenizer_file = tokenizer_file or d_tok
        if not ckpt_file or not tokenizer_file:
            raise ValueError(
                "Pass ckpt_file and tokenizer_file for this repo.")

        ckpt = hf_hub_download(repo_id, ckpt_file, token=token)
        tok_repo = "luffy19/custom_tokenizer" if "agri-slm" in repo_id else repo_id
        tok = hf_hub_download(tok_repo, tokenizer_file, token=token)
        return cls.from_files(ckpt, tok, device=device, dtype=dtype)

    # -- generation ---------------------------------------------------------

    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 150,
                 temperature: float = 1.0, top_k: int = 50, top_p: float = 0.95,
                 repetition_penalty: float = 1.1, no_repeat_ngram: int = 0,
                 seed: Optional[int] = None, stream: bool = False) -> str:
        if seed is not None:
            torch.manual_seed(seed)

        ids = torch.tensor([self.tokenizer.encode(prompt)], device=self.device)
        ctx = self.model.cfg["context_length"]
        out_ids = []

        for _ in range(max_new_tokens):
            if ids.shape[1] >= ctx:
                break
            logits = self.model(ids)[:, -1].float()

            # CTRL-style penalty. Dividing keeps it proportional; the sign check
            # matters because dividing a negative logit would raise it.
            if repetition_penalty != 1.0:
                for t in set(ids[0].tolist()):
                    v = logits[0, t]
                    logits[0, t] = (v / repetition_penalty if v > 0
                                    else v * repetition_penalty)

            if no_repeat_ngram > 0 and ids.shape[1] >= no_repeat_ngram:
                seq = ids[0].tolist()
                k = no_repeat_ngram
                prefix = tuple(seq[-(k - 1):]) if k > 1 else ()
                for i in range(len(seq) - k + 1):
                    if tuple(seq[i:i + k - 1]) == prefix:
                        logits[0, seq[i + k - 1]] = float("-inf")

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
                    logits = torch.full_like(logits, float("-inf")).scatter(
                        -1, s_idx, s_logits)
                nxt = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)

            tok_id = nxt.item()
            if tok_id == self.tokenizer.eos_token_id:
                break
            out_ids.append(tok_id)
            ids = torch.cat([ids, nxt], dim=1)
            if stream:
                print(self.tokenizer.decode([tok_id]), end="", flush=True)

        if stream:
            print()
        return self.tokenizer.decode(out_ids)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PRESETS = {
    # label: (temperature, top_k, top_p, repetition_penalty, no_repeat_ngram)
    "balanced":   (1.0, 50, 0.95, 1.10, 0),   # best measured overall
    "safe":       (0.9, 50, 0.95, 1.15, 4),   # zero loops, guaranteed
    "focused":    (0.7, 50, 0.90, 1.15, 0),   # more deterministic
    "greedy":     (0.0, 0,  1.00, 1.20, 3),   # deterministic; penalty required
    "raw-greedy": (0.0, 0,  1.00, 1.00, 0),   # no penalty — will loop (demo)
}


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default="luffy19/custom_tokenizer",
                   help="HF repo to download from if --ckpt is not given")
    p.add_argument("--ckpt", help="Local checkpoint (.pt)")
    p.add_argument("--tokenizer", help="Local tokenizer JSON")
    p.add_argument("--prompt", action="append", default=[])
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--preset", choices=sorted(PRESETS), default="balanced")
    p.add_argument("--max-new-tokens", type=int, default=150)
    p.add_argument("--temperature", type=float)
    p.add_argument("--top-k", type=int)
    p.add_argument("--top-p", type=float)
    p.add_argument("--repetition-penalty", type=float)
    p.add_argument("--no-repeat-ngram", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--device")
    args = p.parse_args()

    t, k, pp, rp, ng = PRESETS[args.preset]
    kw = dict(
        temperature=args.temperature if args.temperature is not None else t,
        top_k=args.top_k if args.top_k is not None else k,
        top_p=args.top_p if args.top_p is not None else pp,
        repetition_penalty=(args.repetition_penalty
                            if args.repetition_penalty is not None else rp),
        no_repeat_ngram=(args.no_repeat_ngram
                         if args.no_repeat_ngram is not None else ng),
        max_new_tokens=args.max_new_tokens,
    )

    if args.ckpt:
        if not args.tokenizer:
            p.error("--tokenizer is required with --ckpt")
        slm = AgriSLM.from_files(args.ckpt, args.tokenizer, device=args.device)
    else:
        print(f"downloading {args.repo} ...")
        slm = AgriSLM.from_pretrained(args.repo, device=args.device)

    n_params = sum(x.numel() for x in slm.model.parameters())
    print(f"loaded: {n_params:,} params | vocab {slm.tokenizer.vocab_size:,} "
          f"| device {slm.device}")
    print(f"preset '{args.preset}': T={kw['temperature']} top_k={kw['top_k']} "
          f"top_p={kw['top_p']} rep_pen={kw['repetition_penalty']} "
          f"no_repeat_ngram={kw['no_repeat_ngram']}")
    print("-" * 70)

    if args.interactive:
        print("Type a prompt (empty line or Ctrl-D to exit).\n")
        while True:
            try:
                prompt = input("prompt> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not prompt or prompt in {"exit", "quit"}:
                break
            print(f"\n{prompt}", end="")
            slm.generate(prompt, stream=True, **kw)
            print()
        return

    prompts = args.prompt or ["Rice blast disease is caused by"]
    for prompt in prompts:
        out = slm.generate(prompt, seed=args.seed, **kw)
        print(f"\n{prompt}{out}\n")


if __name__ == "__main__":
    main()
