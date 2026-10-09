# Supervised Fine-Tuning (SFT) Guide for Agri-SLM

This guide explains how to use `sft_train.py` to fine-tune the Agri-SLM model on your datasets, with or without LoRA (Low-Rank Adaptation).

## Prerequisites

1. **Environment**: Ensure you have `torch`, `tokenizers`, and `numpy` installed.
2. **LoRA Support (Optional)**: If you plan to train using LoRA, you must install the `peft` library:
   ```bash
   pip install peft
   ```

## Preparing the Data

Before running `sft_train.py`, your dataset must be tokenized and saved as PyTorch `.pt` files. 

You can use the data preparation steps provided in `SFT.ipynb` to download, clean, structure (into ChatML format), and tokenize your dataset. By default, `sft_train.py` expects:
- `--train_pt`: Path to the tokenized training data (e.g. `data/sft/tokenized/train.pt`)
- `--val_pt`: Path to the tokenized validation data (e.g. `data/sft/tokenized/val.pt`)

## Running the Training

You can run the script from the command line, providing the path to your base checkpoint and tokenizer. 

### 1. Standard Full Fine-Tuning

To perform a full fine-tuning of all model parameters:

```bash
python3 sft_train.py \
    --base_ckpt "checkpoints/pretrained_domain_model.pt" \
    --tokenizer "tokenizer/tokenizer_qwen40k.json" \
    --train_pt "data/sft/tokenized/train.pt" \
    --val_pt "data/sft/tokenized/val.pt" \
    --out_dir "checkpoints/sft_run"
```

### 2. Fine-Tuning with LoRA (Parameter-Efficient)

To fine-tune using LoRA, append the `--use_lora` flag. This injects trainable low-rank matrices into the attention and feed-forward layers, drastically reducing VRAM usage and training time while freezing the base model weights.

```bash
python3 sft_train.py \
    --base_ckpt "checkpoints/pretrained_domain_model.pt" \
    --tokenizer "tokenizer/tokenizer_qwen40k.json" \
    --train_pt "data/sft/tokenized/train.pt" \
    --val_pt "data/sft/tokenized/val.pt" \
    --out_dir "checkpoints/sft_run_lora" \
    --use_lora \
    --lora_rank 8 \
    --lora_alpha 32
```

## Configuration Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--base_ckpt` | `str` | **Required** | Path to the `.pt` base model checkpoint. |
| `--tokenizer` | `str` | **Required** | Path to the tokenizer JSON file. |
| `--train_pt` | `str` | **Required** | Path to tokenized `train.pt` dataset. |
| `--val_pt` | `str` | **Required** | Path to tokenized `val.pt` dataset. |
| `--out_dir` | `str` | `checkpoints/sft_run` | Output directory where checkpoints will be saved. |
| `--use_lora` | `flag` | `False` | Pass this flag to wrap the model in LoRA. |
| `--lora_rank` | `int` | `8` | Rank (r) of the LoRA matrices. |
| `--lora_alpha` | `int` | `32` | Scaling factor for LoRA. |
| `--lora_dropout` | `float` | `0.05` | Dropout probability for LoRA layers. |
| `--epochs` | `int` | `3` | Total number of training epochs. |
| `--micro_batch_size` | `int` | `8` | Number of samples per forward pass per device. |
| `--grad_accum` | `int` | `4` | Number of forward passes before an optimizer step. |
| `--lr` | `float` | `1e-5` | Peak learning rate. |
| `--weight_decay` | `float` | `0.01` | Weight decay to prevent overfitting. |

## Checkpoints

The script will save two checkpoints in your `--out_dir`:
1. `last.pt`: The model state at the very end of training.
2. `best.pt`: The model state corresponding to the lowest validation loss achieved during evaluation cycles.

Training metrics (loss, learning rate, gradient norm) are saved in `metrics.json` and the used arguments are saved in `run_config.json` inside the output directory.
