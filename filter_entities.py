#!/usr/bin/env python3
"""
Step 1: Build filtered AGROVOC entity list
- Only keeps: organisms, substances, features, objects, stages (domain names)
- Discards: methods, processes, properties, phenomena, products, activities, etc.
- Generates case variants for each entity
"""

import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path("/home/pranav/my_projects/tokenizer")

# ── Category roots for names (not phrases) ────────────────────────────────────
KEEP_ROOTS = {
    "organisms",   # plants, animals, fungi, pathogens, pests
    "substances",  # chemicals, pesticides, medicines
    "objects",     # physical things (some soil types, tools)
    "features",    # anatomical structures, soil features
    "stages",      # growth stages
}

SKIP_ROOTS = {
    "methods", "processes", "properties", "phenomena",
    "activities", "products", "entities", "strategies",
    "systems", "factors", "resources", "location",
    "subjects", "state", "time", "events", "groups",
    "technology", "measure", "site",
}

# ── AGROVOC SPARQL endpoint ────────────────────────────────────────────────────
SPARQL = "https://agrovoc.fao.org/sparql"

def sparql(query, retries=4, timeout=120):
    params = urllib.parse.urlencode({"query": query})
    url = f"{SPARQL}?{params}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "agrovoc-filter/1.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                import time; time.sleep(2 ** attempt)
            else:
                raise

def get_broader_tree():
    """Fetch all skos:broader edges and build parent_of / children_of maps."""
    print("Fetching broader edges from AGROVOC...")
    data = sparql("""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?child ?parent WHERE { ?child skos:broader ?parent }""")
    edges = [(r["child"]["value"], r["parent"]["value"]) for r in data["results"]["bindings"]]
    print(f"  {len(edges)} broader edges fetched")

    parent_of = defaultdict(list)
    children_of = defaultdict(list)
    for child, parent in edges:
        parent_of[child].append(parent)
        children_of[parent].append(child)
    return parent_of, children_of

def find_top_root(uri, parent_of, memo={}):
    """Walk up the broader chain to the top-level root (no broader parent)."""
    if uri in memo:
        return memo[uri]
    if uri not in parent_of:
        memo[uri] = uri
        return memo[uri]
    roots = set()
    for p in parent_of[uri]:
        roots.add(find_top_root(p, parent_of, memo))
    memo[uri] = next(iter(roots))  # Should have only one top root
    return memo[uri]

def build_uri_to_toproot(parent_of):
    """Memoized top-root finder for all concepts in the graph."""
    memo = {}
    result = {}
    for uri in parent_of:
        result[uri] = find_top_root(uri, parent_of, memo)
    return result

def get_root_labels(top_root_uris):
    """Fetch English prefLabels for the top-level root URIs."""
    values = "\n    ".join(f"<{u}>" for u in top_root_uris)
    data = sparql(f"""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?concept ?label WHERE {{
  VALUES ?concept {{ {values} }}
  ?concept skos:prefLabel ?label .
  FILTER(lang(?label) = "en")
}}""")
    return {r["concept"]["value"]: r["label"]["value"] for r in data["results"]["bindings"]}

def load_existing_entities():
    """Load our already-extracted AGROVOC labels."""
    with open(SCRIPT_DIR / "agrovoc_labels.json") as f:
        data = json.load(f)
    return {e["uri"]: e for e in data["entities"]}

# ── Variant generation ────────────────────────────────────────────────────────
def is_latin_binomial(label):
    """Return True if label looks like 'Genus species' (Latin binomial)."""
    # Pattern: Capitalized word + space + lowercase/mixed rest
    return bool(re.match(r"^[A-Z][a-z]+(\s+[a-z]+)+$", label))

def is_single_word(label):
    return " " not in label and "\t" not in label

def generate_case_variants(label, is_binomial=False):
    """
    For a single label string, generate useful case variants.
    - Single-word common names: lowercase, title case
    - Multi-word names: preserve as-is (can't easily capitalize internal words)
    - Binomials: canonical title case only (scientific convention)
    """
    variants = [label]  # always keep the original

    if is_single_word(label):
        # Lowercase
        lc = label.lower()
        if lc != label:
            variants.append(lc)
        # Title case
        tc = label.title()
        if tc != label and tc != lc:
            variants.append(tc)

    # If it looks like a binomial, add canonical form
    if is_binomial:
        # Title case each word: "triticum aestivum" -> "Triticum Aestivum"
        canonical = " ".join(w.capitalize() for w in label.split())
        if canonical not in variants:
            variants.append(canonical)

    return list(dict.fromkeys(variants))  # deduplicate preserve order

def build_entity_list():
    """Main: filter entities to name-categories, generate variants."""
    print("\n=== Step 1: Building filtered entity list ===")

    # Load existing extracted entities
    entities_by_uri = load_existing_entities()
    print(f"  Loaded {len(entities_by_uri)} entities from agrovoc_labels.json")

    # Get broader tree
    parent_of, children_of = get_broader_tree()

    # Find top-level root for each entity URI
    uri_to_toproot = build_uri_to_toproot(parent_of)

    # Get labels for all top roots
    all_top_roots = set(uri_to_toproot.values())
    top_root_labels = get_root_labels(all_top_roots)

    # Categorize each entity by its top-level root
    kept = []
    discarded = []

    for uri, entity in entities_by_uri.items():
        top_root = uri_to_toproot.get(uri, None)
        root_label = top_root_labels.get(top_root, "unknown")

        record = {
            "uri": uri,
            "prefLabel": entity["prefLabel"],
            "variants": entity["variants"],
            "topRootLabel": root_label,
            "isBinomial": is_latin_binomial(entity["prefLabel"]),
        }

        if root_label in KEEP_ROOTS:
            kept.append(record)
        else:
            discarded.append(record)

    print(f"  KEPT:   {len(kept)} entities ({sum(len(e['variants']) for e in kept)} variants)")
    print(f"  DISCARDED: {len(discarded)} entities ({sum(len(e['variants']) for e in discarded)} variants)")

    # Breakdown by category
    from collections import Counter
    cat_counts = Counter(r["topRootLabel"] for r in kept)
    print("\n  By category:")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {cnt}")

    # Generate all case variants
    print("\n  Generating case variants...")
    all_variant_strings = set()
    for entity in kept:
        for variant in entity["variants"]:
            all_variant_strings.add(variant)
            for v in generate_case_variants(variant, entity["isBinomial"]):
                all_variant_strings.add(v)

    print(f"  Total unique variant strings: {len(all_variant_strings)}")

    # Save filtered entity list
    output_path = SCRIPT_DIR / "agrovoc_entities_filtered.json"
    with open(output_path, "w") as f:
        json.dump({
            "kept": kept,
            "discarded": discarded,
            "stats": {
                "kept_count": len(kept),
                "discarded_count": len(discarded),
                "total_variant_strings": len(all_variant_strings),
                "multi_word_count": sum(1 for v in all_variant_strings if " " in v),
                "single_word_count": sum(1 for v in all_variant_strings if " " not in v),
            }
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to {output_path}")

    # Also save just the variant strings for Aho-Corasick building
    variant_path = SCRIPT_DIR / "agrovoc_variants.txt"
    with open(variant_path, "w", encoding="utf-8") as f:
        for v in sorted(all_variant_strings):
            f.write(v + "\n")
    print(f"  Saved variant list to {variant_path}")

    # Show samples
    print("\n  Sample kept entities:")
    for e in kept[:8]:
        print(f"    [{e['topRootLabel']}] {e['prefLabel']}: {e['variants'][:3]}")

    print("\n  Sample discarded entities:")
    for e in discarded[:8]:
        print(f"    [{e['topRootLabel']}] {e['prefLabel']}")

    return kept, discarded

if __name__ == "__main__":
    build_entity_list()