# Agriculture Domain Transformer (~140M params)

Two training-from-scratch transformer notebooks for the agriculture domain, sharing an identical Qwen3-style architecture. The only difference is the tokenizer: one uses a pruned Qwen BPE, the other uses a domain-specific hybrid BPE with AGROVOC entity injection.

## Architecture

| Parameter | Value |
|-----------|-------|
| vocab_size | 40,000 |
| embedding_rank | 256 |
| context_length | 8,192 |
| emb_dim | 640 |
| n_heads | 10 |
| n_kv_groups | 5 |
| n_layers | 20 |
| hidden_dim | 2,560 |
| head_dim | 64 |
| qk_norm | True |
| rope_base | 1,000,000 |
| activation | SwiGLU |
| approx. params | ~134M |

Key design: factorized embedding (ALBERT-style, rank=256), grouped-query attention (10 heads, 5 KV groups), SwiGLU feed-forward, RoPE at 1M base, all fp32 weights.

## Tokenizers

### Qwen BPE (`tokenizer_output/tokenizer_qwen40k.json`)
- Pruned from Qwen2.5-0.5B tokenizer (151k → 40k tokens)
- 39,978 BPE tokens + 22 special tokens = 40,000 total
- ByteLevel with `byte_fallback=True`
- Ready to use with `Qwen.ipynb`

### Hybrid BPE (needs training)
- Base: pruned Qwen BPE (32k tokens)
- Injection: ~8k AGROVOC entity tokens (frequency-per-slot greedy selection)
- Entity sources: organisms, substances, features, objects, stages from AGROVOC
- Target total: 40,000 tokens
- To train: `train_bpe.py --base-tokenizer tokenizer.json --vocab-size 32000 --injection-budget 8000 --hf-dataset <dataset>`

## Files

| File | Purpose |
|------|---------|
| `Qwen.ipynb` | Training notebook using pruned Qwen BPE tokenizer (40k vocab) |
| `Hybrid.ipynb` | Training notebook using hybrid BPE tokenizer |
| `train_bpe.py` | Build the hybrid tokenizer (prune + entity injection) |
| `filter_entities.py` | Filter AGROVOC entities to domain-relevant categories |
| `extract_agrovoc.py` | Fetch English labels from AGROVOC SPARQL endpoint |
| `config.json` | All architecture and training numbers in one place |
| `agrovoc_entities_filtered.json` | Filtered AGROVOC entity list (28k entities) |
| `tokenizer.json` | Full Qwen2.5-0.5B tokenizer (source for pruning) |
| `tokenizer_output/tokenizer_qwen40k.json` | Qwen BPE tokenizer pruned to 40k (ready) |

## Training

### Qwen notebook
Opens `tokenizer_output/tokenizer_qwen40k.json`, instantiates the model, trains from scratch. No pretrained weights.

### Hybrid notebook
Needs `tokenizer_output/tokenizer_final.json` first. Generate it:

```bash
python3 train_bpe.py \
  --base-tokenizer tokenizer.json \
  --vocab-size 32000 \
  --injection-budget 8000 \
  --hf-dataset <your-agriculture-corpus> \
  --hf-samples 20000
```

Then update `Hybrid.ipynb` to point at the new `tokenizer_final.json`.

## Pipeline

1. `extract_agrovoc.py` — Fetch all English labels from AGROVOC SPARQL
2. `filter_entities.py` — Keep only name categories (organisms, substances, etc.)
3. `train_bpe.py` — Prune Qwen BPE to 32k, inject entities with 8k budget
4. `Qwen.ipynb` / `Hybrid.ipynb` — Train model from scratch

## Notes

- Both notebooks produce the same architecture (40k vocab, 20 layers, 640-dim)
- Qwen notebook is ready to run; Hybrid notebook needs the tokenizer trained first
- No HuggingFace or safetensors dependencies at training time
- All linear layers use default fp32 (no dtype casting)
- RMSNorm without bias/shift parameters
- No KV cache during generation (recomputes full sequence each step)
