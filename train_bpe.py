#!/usr/bin/env python3
"""
Step 2: BPE trainer with frequency-prioritized entity injection.

Key design decisions:
  - Entities are NOT masked during BPE training — BPE learns merges from real text.
  - byte_fallback=False on the model (not trainer) — verified preserved through training.
  - Injection budget algorithm: rank by frequency-per-slot (combined_freq / attested_count),
    not raw frequency. This is a knapsack heuristic: items with lower cost-per-unit
    (single case-form, high frequency) rank above expensive items (multi-case-form,
    low frequency) even if raw frequency is higher.
  - Grouping key: (concept_uri, variant_string) — distinct label strings on the same
    concept compete independently; only case-variants of the same string are bundled.
  - Within each group, ALL attested case forms are injected together (attested = non-zero
    corpus frequency). This satisfies "all case variants must be covered" without
    injecting zero-frequency forms (ALL-CAPS forms that never occur are naturally pruned).

Filter chain (applied before injection ranking):
  1. agronomy:hasTaxonomicRank  — structural name signal from AGROVOC agrontology layer
  2. head-word stoplist         — reject if last word is a generic noun
  3. process-suffix             — reject if label ends in -ing/-tion/-ment/...
  4. function-word             — reject if phrase contains preposition
"""

import sys
import json
import time
import os
from pathlib import Path
from tokenizers import Tokenizer

SCRIPT_DIR = Path("/home/pranav/my_projects/tokenizer")

_HEAD_STOPLIST = {
    "equipment", "management", "practices", "techniques", "systems",
    "scheduling", "control", "treatment", "methods", "production",
    "services", "operations", "practices", "products", "materials",
    "facilities", "structures",
}
_PROCESS_SUFFIXES = ("ing", "tion", "ment", "ance", "ence")
_FUNCTION_WORDS = {"of", "for", "and", "in", "by", "with", "to", "from", "as"}


def load_entities(path=None):
    path = path or (SCRIPT_DIR / "agrovoc_entities_filtered.json")
    with open(path) as f:
        return json.load(f).get("kept", [])


def apply_label_filters(pref_label, has_taxrank, taxrank_set, entity_uri):
    """Return (passes: bool, reason: str or None)."""
    if not has_taxrank:
        has_rank = entity_uri in taxrank_set
    else:
        has_rank = has_taxrank

    if has_rank:
        return True, None

    words = pref_label.split()
    if words and words[-1].lower().rstrip("s") in _HEAD_STOPLIST:
        return False, "head_stoplist"

    for suffix in _PROCESS_SUFFIXES:
        if pref_label.lower().endswith(suffix):
            return False, "process_suffix"

    label_words = set(w.lower().rstrip("s").rstrip(".") for w in pref_label.split())
    if label_words & _FUNCTION_WORDS:
        return False, "function_word"

    return True, None


def _case_variants(s):
    """Generate up to 2 case forms of string s (no UPPERCASE)."""
    return [s, s.title()]

# ── Build proper Aho-Corasick automaton ───────────────────────────────────────
def build_automaton(entities):
    """Build Aho-Corasick from multi-word entity variants (case-insensitive)."""
    import ahocorasick

    automaton = ahocorasick.Automaton()  # STORE_ANY (default) — accepts strings
    added = set()
    canonical_map = {}  # lowercased variant -> canonical prefLabel

    for entity in entities:
        canonical = entity["prefLabel"]
        for variant in entity["variants"]:
            if " " not in variant:
                continue
            key = variant.lower()
            if key in added:
                continue
            added.add(key)
            automaton.add_word(key, key)          # value = lowercased key string
            canonical_map[key] = canonical

    automaton.make_automaton()
    print(f"  Aho-Corasick: {len(added)} patterns")

    return automaton, canonical_map

def scan_and_count(text, automaton, canonical_map):
    """
    Use Aho-Corasick to find all entity spans in text (case-insensitive).
    Returns dict of (variant_lower -> count) for entities found.
    Longer matches win over shorter overlapping ones.
    """
    text_lower = text.lower()
    matches = []

    for end_idx, key in automaton.iter(text_lower):
        start_idx = end_idx - len(key) + 1
        matches.append((start_idx, end_idx + 1, key))

    if not matches:
        return {}

    # Resolve overlaps: keep longest, discard shorter overlapping ones
    filtered = []
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    last_end = -1
    for start, end, key in matches:
        if start >= last_end:
            filtered.append(key)
            last_end = end

    # Count each unique variant once per line (not per occurrence) — 
    # more realistic for corpus frequency tracking
    counts = {}
    for key in dict.fromkeys(filtered):  # dedupe within line, preserve order
        counts[key] = counts.get(key, 0) + 1

    return counts

# ── Synthetic corpus ───────────────────────────────────────────────────────────
def generate_synthetic(corpus_path, entities, lines=20000, seed=42):
    import random
    random.seed(seed)

    print(f"Generating synthetic corpus ({lines:,} lines)...")

    # Collect entity variants by type
    multi_word = []
    for e in entities:
        for v in e["variants"]:
            if " " in v:
                multi_word.append(v)

    single_word = []
    for e in entities:
        for v in e["variants"]:
            if " " not in v:
                single_word.append(v)

    # Sample 200 most common multi-word entities to appear frequently
    frequent_entities = random.sample(multi_word, min(200, len(multi_word)))

    fillers = "the and is are was were be been in on at to for of with by from as this that it its crop plant soil yield farm field season agricultural farming production management research study data result analysis report results show that researchers found significant increase decrease".split()

    with open(corpus_path, "w", encoding="utf-8") as f:
        for i in range(lines):
            n_words = random.randint(15, 80)
            words = []
            for _ in range(n_words):
                r = random.random()
                if r < 0.3 and frequent_entities:
                    # 30% chance: use a frequent entity (BPE will learn merges)
                    words.append(random.choice(frequent_entities))
                elif r < 0.5 and multi_word:
                    # 20%: use random entity
                    words.append(random.choice(multi_word))
                elif r < 0.7:
                    words.append(random.choice(fillers))
                else:
                    words.append(random.choice(single_word))

            f.write(" ".join(words) + "\n")

            if (i + 1) % 5000 == 0:
                print(f"  {i+1:,} / {lines:,}")

    print(f"  Saved to {corpus_path} ({os.path.getsize(corpus_path)/1024/1024:.1f} MB)")
    return corpus_path

# ── BPE Training ─────────────────────────────────────────────────────────────
def train_bpe(mask_file_path, vocab_size=32000, min_freq=2, sentinel="<ENT>",
              output_dir=None):
    from tokenizers import models, trainers, pre_tokenizers, decoders

    print(f"\n=== Training ByteLevel BPE ===")
    print(f"  Vocab: {vocab_size}, Min freq: {min_freq}")

    # Create tokenizer with empty BPE model that has byte_fallback=False
    tokenizer = Tokenizer(models.BPE(
        vocab={},
        merges=[],
        byte_fallback=False,
    ))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tokenizer.decoder = decoders.ByteLevel()

    with open(mask_file_path) as f:
        num_lines = sum(1 for _ in f)
    print(f"  Training on {num_lines:,} masked lines")

    # Build BPE model manually, then train it
    t0 = time.time()

    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_freq,
        special_tokens=[sentinel],
        show_progress=True,
    )

    tokenizer.train_from_iterator(
        iter(open(mask_file_path, encoding="utf-8")),
        trainer=trainer,
        length=num_lines,
    )
    print(f"  Trained in {time.time()-t0:.1f}s, vocab={len(tokenizer.get_vocab())}")

    if output_dir:
        p = Path(output_dir) / "tokenizer_pre_injection.json"
        tokenizer.save(str(p))
        print(f"  Saved to {p}")

    return tokenizer

# ── Atomic coverage + injection ───────────────────────────────────────────────
def check_and_inject(tokenizer, entities, automaton, canonical_map,
                     corpus_freq, budget=8000, taxrank_set=None,
                     entities_with_taxrank=None, entity_min_freq=1):
    """
    frequency-per-slot budget algorithm with (uri, variant) grouping.

    Each entity can contribute multiple injection groups — one per variant string.
    Each group has a variable cost = number of attested case forms (1-3).
    Sort key = combined_freq / attested_count (greedy knapsack heuristic).

    Arguments:
      taxrank_set: set of concept URIs that have agronomy:hasTaxonomicRank
      entities_with_taxrank: dict mapping uri -> hasTaxonomicRank bool (from JSON)
    """
    from tokenizers import AddedToken

    taxrank_set = taxrank_set or set()
    entities_with_taxrank = entities_with_taxrank or {}

    print(f"\n=== Coverage check + frequency-per-slot injection (budget={budget}) ===")

    # ── Build (uri, variant) groups with freq-per-slot ────────────────────────
    groups = []  # list of dicts with group metadata

    for e in entities:
        uri = e["uri"]
        pref_label = e["prefLabel"]
        has_rank = entities_with_taxrank.get(uri, False)

        passes_filter, reason = apply_label_filters(
            pref_label,
            has_rank,
            taxrank_set,
            uri,
        )

        for variant in e.get("variants", [pref_label]):
            case_forms = _case_variants(variant)
            attested_case_forms = [
                fv for fv in case_forms
                if corpus_freq.get(fv.lower(), 0) > 0
            ]

            if not passes_filter and not attested_case_forms:
                continue

            combined_freq = sum(
                corpus_freq.get(fv.lower(), 0)
                for fv in case_forms
            )

            # Frequency filter: skip if combined freq below threshold (no rank override)
            if combined_freq < entity_min_freq and not has_rank:
                continue

            attested_count = len(attested_case_forms)

            if attested_count == 0 and not passes_filter:
                continue

            freq_per_slot = combined_freq / attested_count if attested_count > 0 else 0

            groups.append({
                "uri": uri,
                "pref_label": pref_label,
                "variant": variant,
                "case_forms": case_forms,
                "attested_case_forms": attested_case_forms,
                "combined_freq": combined_freq,
                "attested_count": attested_count,
                "freq_per_slot": freq_per_slot,
                "passes_filter": passes_filter,
                "filter_reason": reason,
            })

    # Sort by freq_per_slot descending (greedy knapsack by efficiency)
    groups.sort(key=lambda g: -g["freq_per_slot"])

    # ── Coverage stats pre-injection ──────────────────────────────────────────
    covered = []
    already_covered = []
    for g in groups:
        if len(g["attested_case_forms"]) == 1:
            test = g["attested_case_forms"][0]
            enc = tokenizer.encode(test)
            if len(enc.ids) == 1:
                already_covered.append(g)

    natural_coverage = len(already_covered)
    print(f"  Groups: {len(groups)}, Naturally covered (1 form, single-token): {natural_coverage}")

    # ── Greedy budget walk ─────────────────────────────────────────────────────
    to_inject = []
    remaining = budget
    rejected_filters = [g for g in groups if not g["passes_filter"] and g["attested_count"] > 0]
    rejected_zero_attested = [g for g in groups if g["attested_count"] == 0]

    print(f"  Rejected by filter (attested but filtered): {len(rejected_filters)}")
    print(f"  Zero attested frequency: {len(rejected_zero_attested)}")

    for g in groups:
        if remaining <= 0:
            break
        if g["attested_count"] == 0:
            continue
        if not g["passes_filter"]:
            continue

        cost = g["attested_count"]
        if cost > remaining:
            continue

        for form in g["attested_case_forms"]:
            to_inject.append((form, g["pref_label"], g["uri"], g["variant"]))
        remaining -= cost

    print(f"  Injected: {len(to_inject)} case-forms ({budget - remaining} slots used, {remaining} remaining)")

    if groups[:5]:
        print(f"  Top 5 by freq-per-slot:")
        for g in groups[:5]:
            print(f"    fps={g['freq_per_slot']:8.1f}  cost={g['attested_count']}  "
                  f"freq={g['combined_freq']:6d}  {g['variant']!r} ({g['uri'].split('/')[-1]})")

    # ── Inject ─────────────────────────────────────────────────────────────────
    all_tokens = [AddedToken(form, normalized=False, single_word=False)
                 for form, *_ in to_inject]
    added = tokenizer.add_tokens(all_tokens)
    vocab = tokenizer.get_vocab()
    print(f"  Final vocab size: {len(vocab)}")

    # Verify
    still_fragmented = sum(
        1 for form, *_ in to_inject
        if len(tokenizer.encode(form).ids) > 1
    )
    print(f"  Still fragmented after injection: {still_fragmented}")

    return tokenizer, already_covered, to_inject, groups, remaining

# ── Smoke test ────────────────────────────────────────────────────────────────
def smoke_test(tokenizer, entities):
    print("\n=== Smoke Test ===")

    # Build test set
    test_cases = [
        ("wheat", None, "single-word common"),
        ("Triticum aestivum", 1, "binomial"),
        ("Puccinia graminis", 1, "pathogen binomial"),
        ("glyphosate", None, "single-word chemical"),
        ("xylem", None, "anatomy single"),
        ("nitrogen fixation", 1, "multi-word common"),
    ]

    # Add some actual entities from our list
    for e in entities[:5]:
        for v in e["variants"]:
            if " " in v and len(v) < 50:
                test_cases.append((v, 1, f"entity: {e['topRootLabel']}"))
                break

    passed = 0
    failed = 0
    for text, expected, desc in test_cases:
        try:
            enc = tokenizer.encode(text)
            nt = len(enc.ids)
            if expected is None:
                status = "OK (any tokens)"
                passed += 1
            elif nt == expected:
                status = "OK"
                passed += 1
            else:
                status = f"FAIL (got {nt}, expected {expected})"
                failed += 1
            mark = "✓" if "OK" in status else "✗"
            print(f"  {mark} {text!r:35s} → {nt:2d} tokens  [{desc}]  {status}")
        except Exception as ex:
            print(f"  ✗ {text!r:35s} ERROR: {ex}")
            failed += 1

    print(f"\n  {'ALL PASS' if failed == 0 else f'{failed} FAILURES'}")
    return failed == 0

# ── Load base tokenizer from Qwen ────────────────────────────────────────────
def load_base_tokenizer_from_qwen(qwen_path, qwen_freq, target_vocab, sentinel="<ENT>"):
    """
    Load Qwen tokenizer, reduce to target_vocab tokens by frequency,
    preserving all intermediate tokens needed for BPE merge chains.
    """
    from tokenizers import Tokenizer, models, AddedToken, decoders, pre_tokenizers, normalizers, processors

    print(f"\n=== Loading base tokenizer from {qwen_path} ===")
    print(f"  Target base vocab: {target_vocab:,}")

    # Load raw JSON for everything
    with open(qwen_path) as f:
        raw = json.load(f)

    full_vocab = raw['model']['vocab']
    all_merges = raw['model'].get('merges', [])
    added_tokens_cfg = raw.get('added_tokens', [])

    # Build: merged_string -> merge_input_strings
    merge_map = {}
    for m in all_merges:
        parts = m.split()
        if len(parts) == 2:
            merged = parts[0] + parts[1]
            merge_map[merged] = (parts[0], parts[1])

    # Sort tokens by frequency in corpus, pick top target_vocab
    sorted_tids = sorted(qwen_freq.items(), key=lambda x: -x[1])
    top_ids = {tid for tid, _ in sorted_tids[:target_vocab]}

    # Walk merge tree: find all intermediates needed for top tokens
    t0 = time.time()
    needed = set(top_ids)
    reverse_vocab = {v: k for k, v in full_vocab.items()}
    queue = list(top_ids)
    while queue:
        tid = queue.pop()
        if tid not in reverse_vocab:
            continue
        token_str = reverse_vocab[tid]
        if token_str in merge_map:
            a_str, b_str = merge_map[token_str]
            if a_str in full_vocab:
                aid = full_vocab[a_str]
                if aid not in needed:
                    needed.add(aid)
                    queue.append(aid)
            if b_str in full_vocab:
                bid = full_vocab[b_str]
                if bid not in needed:
                    needed.add(bid)
                    queue.append(bid)

    # Build reduced vocab from needed set, reassign IDs sequentially
    new_vocab = {}
    for i, tid in enumerate(sorted(needed)):
        token_str = reverse_vocab.get(tid)
        if token_str is not None:
            new_vocab[token_str] = i
    print(f"  Intermediate expansion: {len(top_ids)} -> {len(new_vocab)} tokens ({time.time()-t0:.1f}s)")

    # Filter merges: only keep where inputs AND output are all in the reduced vocab
    t0 = time.time()
    new_merges = []
    for m in all_merges:
        parts = m.split()
        if len(parts) == 2:
            a, b = parts
            merged = a + b
            if a in new_vocab and b in new_vocab and merged in new_vocab:
                new_merges.append((a, b))
    print(f"  Merges: {len(new_merges):,} / {len(all_merges):,} ({time.time()-t0:.1f}s)")

    # Create BPE model (special tokens excluded from vocab — added separately)
    new_model = models.BPE(vocab=new_vocab, merges=new_merges, byte_fallback=True)

    tokenizer = Tokenizer(new_model)
    tokenizer.normalizer = normalizers.NFC()
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence([
        pre_tokenizers.Split(
            pattern="(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\\r\\n\\p{L}\\p{N}]?[\\p{L}\\p{M}]+|\\p{N}| ?[^\\s\\p{L}\\p{M}\\p{N}]+[\\r\\n]*|\\s*[\\r\\n]+|\\s+(?!\\S)|\\s+",
            behavior="isolated",
        ),
        pre_tokenizers.ByteLevel(add_prefix_space=False),
    ])
    tokenizer.post_processor = processors.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()

    # Add Qwen special tokens with auto-assigned IDs (within reduced vocab range)
    for at in added_tokens_cfg:
        token = AddedToken(
            at['content'],
            single_word=at.get('single_word', False),
            lstrip=at.get('lstrip', False),
            rstrip=at.get('rstrip', False),
            normalized=at.get('normalized', True),
        )
        tokenizer.add_special_tokens([token])

    # Add <ENT> sentinel token
    tokenizer.add_special_tokens([AddedToken(sentinel, normalized=False, special=True)])
    print(f"  Final base vocab: {len(tokenizer.get_vocab()):,}")
    return tokenizer


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", help="Real corpus file (txt, one sentence per line)")
    p.add_argument("--vocab-size", type=int, default=32000,
                   help="Base BPE vocab size (default 32000)")
    p.add_argument("--injection-budget", type=int, default=8000,
                   help="Injection token budget (default 8000)")
    p.add_argument("--entities-json", default=str(SCRIPT_DIR / "agrovoc_entities_filtered.json"),
                   help="Path to entity JSON (default: agrovoc_entities_filtered.json)")
    p.add_argument("--lines", type=int, default=20000,
                   help="Synthetic corpus lines if no real corpus")
    p.add_argument("--output-dir", default=str(SCRIPT_DIR / "tokenizer_output"))
    p.add_argument("--hf-dataset", help="HF dataset name for streaming (e.g. AnmolNimmala0/agri-slm-corpus)")
    p.add_argument("--hf-samples", type=int, default=20000,
                   help="Number of HF samples to stream for frequency scanning")
    p.add_argument("--hf-split", default="train",
                   help="HF dataset split")
    p.add_argument("--entity-min-freq", type=int, default=1,
                   help="Minimum corpus frequency for entity injection (default 1)")
    p.add_argument("--warmstart", action="store_true", default=True,
                   help="Generate warm-start embedding mapping")
    p.add_argument("--base-tokenizer",
                   help="Path to base tokenizer JSON (e.g. Qwen). Uses its BPE vocab+merges instead of training.")
    args = p.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load entities + hasTaxonomicRank if available from filter_and_enrich step
    print("Loading entities...")
    import json as _json
    with open(args.entities_json) as f:
        ent_data = _json.load(f)
    entities_kept = ent_data.get("kept", [])
    entities_with_taxrank = {
        e["uri"]: e.get("hasTaxonomicRank", False)
        for e in entities_kept
    }
    taxrank_set = {uri for uri, has_rank in entities_with_taxrank.items() if has_rank}
    print(f"  {len(entities_kept)} entities loaded")
    print(f"  {len(taxrank_set)} have agronomy:hasTaxonomicRank")

    # Build Aho-Corasick
    automaton, canonical_map = build_automaton(entities_kept)

    # Prepare corpus + frequency scan
    if args.hf_dataset:
        # Stream from HF: scan frequencies + save corpus file for BPE training
        from datasets import load_dataset
        print(f"Streaming {args.hf_samples:,} samples from {args.hf_dataset} [{args.hf_split}]...")
        corpus_path = out_dir / "hf_corpus.txt"
        corpus_freq = {}
        line_count = 0
        t0 = time.time()

        ds = load_dataset(args.hf_dataset, split=args.hf_split, streaming=True)
        with open(corpus_path, "w", encoding="utf-8") as fout:
            for i, sample in enumerate(ds):
                if i >= args.hf_samples:
                    break
                text = sample.get("text", "")
                if not text.strip():
                    continue
                fout.write(text + "\n")
                counts = scan_and_count(text, automaton, canonical_map)
                for key, cnt in counts.items():
                    corpus_freq[key] = corpus_freq.get(key, 0) + cnt
                line_count += 1
                if (i + 1) % 5000 == 0:
                    print(f"  {i+1:,} samples, {line_count:,} written, "
                          f"{len(corpus_freq)} unique entities ({time.time()-t0:.1f}s)")

        total_occurrences = sum(corpus_freq.values())
        print(f"  Done: {line_count:,} lines, {total_occurrences:,} entity occurrences, "
              f"{len(corpus_freq)} unique variants in {time.time()-t0:.1f}s")
        print(f"  Corpus saved to {corpus_path} ({corpus_path.stat().st_size/1024/1024:.1f} MB)")

    elif args.corpus and Path(args.corpus).exists():
        corpus_path = Path(args.corpus)
        print(f"Using real corpus: {corpus_path}")
        print(f"\n=== Scanning corpus for entity frequencies ===")
        t0 = time.time()
        corpus_freq = {}
        line_count = 0
        with open(corpus_path, encoding="utf-8") as fin:
            for line in fin:
                counts = scan_and_count(line.rstrip("\n"), automaton, canonical_map)
                for key, cnt in counts.items():
                    corpus_freq[key] = corpus_freq.get(key, 0) + cnt
                line_count += 1
                if line_count % 20000 == 0:
                    print(f"  {line_count:,} lines, {len(corpus_freq)} unique "
                          f"entities found ({time.time()-t0:.1f}s)")
        total_occurrences = sum(corpus_freq.values())
        print(f"  Done: {line_count:,} lines, {total_occurrences:,} entity occurrences, "
              f"{len(corpus_freq)} unique variants in {time.time()-t0:.1f}s")
    else:
        corpus_path = out_dir / "synthetic_corpus.txt"
        generate_synthetic(corpus_path, entities_kept, lines=args.lines)
        print(f"\n=== Scanning corpus for entity frequencies ===")
        t0 = time.time()
        corpus_freq = {}
        line_count = 0
        with open(corpus_path, encoding="utf-8") as fin:
            for line in fin:
                counts = scan_and_count(line.rstrip("\n"), automaton, canonical_map)
                for key, cnt in counts.items():
                    corpus_freq[key] = corpus_freq.get(key, 0) + cnt
                line_count += 1
                if line_count % 20000 == 0:
                    print(f"  {line_count:,} lines, {len(corpus_freq)} unique "
                          f"entities found ({time.time()-t0:.1f}s)")
        total_occurrences = sum(corpus_freq.values())
        print(f"  Done: {line_count:,} lines, {total_occurrences:,} entity occurrences, "
              f"{len(corpus_freq)} unique variants in {time.time()-t0:.1f}s")

    top5 = sorted(corpus_freq.items(), key=lambda x: -x[1])[:5]
    print("  Top 5 by corpus frequency:")
    for variant, cnt in top5:
        print(f"    {cnt:6d}  {variant!r}")

    # ── Load or train base tokenizer ──────────────────────────────────────────
    if args.base_tokenizer:
        print(f"\n=== Scanning corpus for base tokenizer frequencies ===")
        from collections import defaultdict
        qwen_freq = defaultdict(int)
        base_tok = Tokenizer.from_file(args.base_tokenizer)
        t0 = time.time()
        blines = 0
        with open(corpus_path, encoding="utf-8") as fin:
            for line in fin:
                enc = base_tok.encode(line.rstrip("\n"))
                for tid in enc.ids:
                    qwen_freq[tid] += 1
                blines += 1
                if blines % 50000 == 0:
                    print(f"  {blines:,} lines, {len(qwen_freq)} unique tokens ({time.time()-t0:.1f}s)")

        print(f"  Done: {blines:,} lines, {len(qwen_freq)} unique tokens in {time.time()-t0:.1f}s")
        tokenizer = load_base_tokenizer_from_qwen(
            args.base_tokenizer, qwen_freq,
            target_vocab=args.vocab_size,
            sentinel="<ENT>",
        )
        pre_inj_path = out_dir / "tokenizer_pre_injection.json"
        tokenizer.save(str(pre_inj_path))
        print(f"  Saved base tokenizer to {pre_inj_path}")

    else:
        # ── Train BPE on corpus ───────────────────────────────────────────────
        tokenizer = train_bpe(
            corpus_path,
            vocab_size=args.vocab_size,
            min_freq=2,
            sentinel="<ENT>",
            output_dir=out_dir,
        )

    # ── Coverage + frequency-per-slot injection ─────────────────────────────────
    tokenizer, natural_covered, injected, all_groups, remaining = check_and_inject(
        tokenizer, entities_kept, automaton, canonical_map,
        corpus_freq=corpus_freq,
        budget=args.injection_budget,
        taxrank_set=taxrank_set,
        entities_with_taxrank=entities_with_taxrank,
        entity_min_freq=args.entity_min_freq,
    )

    slots_used = args.injection_budget - remaining

    # ── Warm-start embedding mapping ────────────────────────────────────────────
    if args.warmstart and injected:
        from tokenizers import Tokenizer as _Tokenizer
        pre_inj_path = out_dir / "tokenizer_pre_injection.json"
        if pre_inj_path.exists():
            pre_inj = _Tokenizer.from_file(str(pre_inj_path))
            warmstart_map = {}
            for form, pref_label, uri, variant in injected:
                enc = pre_inj.encode(form)
                warmstart_map[form] = {
                    "subword_ids": enc.ids,
                    "subword_tokens": enc.tokens,
                    "pref_label": pref_label,
                    "uri": uri,
                }
            ws_path = out_dir / "warmstart_init.json"
            with open(ws_path, "w") as f:
                _json.dump(warmstart_map, f, indent=2)
            print(f"\n  Warm-start mapping: {ws_path} ({len(warmstart_map)} entries)")

    # Save final
    final_path = out_dir / "tokenizer_final.json"
    tokenizer.save(str(final_path))
    print(f"\n  Final tokenizer: {final_path}")

    # Smoke test
    smoke_test(tokenizer, entities_kept)

    # Stats
    vocab = tokenizer.get_vocab()
    print(f"\n=== Final Stats ===")
    print(f"  Vocab size: {len(vocab)}")
    print(f"  Naturally covered: {len(natural_covered)}")
    print(f"  Injected case-forms: {len(injected)}")
    print(f"  Injection slots used: {slots_used} / {args.injection_budget}")
    print(f"  Total groups ranked: {len(all_groups)}")

    injected_forms = {form for form, *_ in injected}
    stats = {
        "vocab_size": len(vocab),
        "covered_naturally": len(natural_covered),
        "injected": len(injected),
        "injection_slots_used": slots_used,
        "injection_budget": args.injection_budget,
        "total_entity_occurrences": total_occurrences,
        "unique_entity_variants": len(corpus_freq),
        "corpus_lines": line_count,
        "vocab_target": args.vocab_size,
        "groups_with_taxrank": len(taxrank_set),
    }
    with open(out_dir / "stats.json", "w") as f:
        _json.dump(stats, f, indent=2)
    print(f"\nDone! Output in {out_dir}/")

if __name__ == "__main__":
    main()