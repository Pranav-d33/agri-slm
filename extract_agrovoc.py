#!/usr/bin/env python3
"""
Final AGROVOC English name extraction.

Fetches all English prefLabels, altLabels, and hiddenLabels.
Outputs:
  1. agrovoc_labels.json  — full structured output
  2. agrovoc_names.txt    — flat list of all unique English name strings
"""

import json
import urllib.request
import urllib.parse
import time
from collections import defaultdict

SPARQL_ENDPOINT = "https://agrovoc.fao.org/sparql"
OUTPUT_JSON = "/home/pranav/my_projects/tokenizer/agrovoc_labels.json"
OUTPUT_TXT = "/home/pranav/my_projects/tokenizer/agrovoc_names.txt"

BATCH_SIZE = 10000

def sparql_query(query, retries=5, timeout=180):
    params = urllib.parse.urlencode({"query": query})
    url = f"{SPARQL_ENDPOINT}?{params}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "opencode-extractor/1.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt+1}/{retries}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise

def fetch_all_labels():
    """Fetch ALL English labels: prefLabel, altLabel, hiddenLabel."""
    print("=== Phase 1: Fetching all English labels ===")
    
    # prefLabels + altLabels
    data = sparql_query("""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?concept ?prefLabel ?altLabel WHERE {
  ?concept skos:prefLabel ?prefLabel .
  FILTER(lang(?prefLabel) = "en")
  OPTIONAL {
    ?concept skos:altLabel ?altLabel .
    FILTER(lang(?altLabel) = "en")
  }
}""")
    rows = data["results"]["bindings"]
    print(f"  prefLabel+altLabel rows: {len(rows)}")
    
    # hiddenLabels (separate query because they don't always have prefLabels)
    hidden_data = sparql_query("""PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?concept ?hiddenLabel WHERE {
  ?concept skos:hiddenLabel ?hiddenLabel .
  FILTER(lang(?hiddenLabel) = "en")
}""")
    hidden_rows = hidden_data["results"]["bindings"]
    print(f"  hiddenLabel rows: {len(hidden_rows)}")
    
    # Build per-concept structure
    concepts = {}
    for row in rows:
        uri = row["concept"]["value"]
        pref = row["prefLabel"]["value"]
        alt = row.get("altLabel", {}).get("value")
        if uri not in concepts:
            concepts[uri] = {"prefLabels": set(), "altLabels": set(), "hiddenLabels": set()}
        concepts[uri]["prefLabels"].add(pref)
        if alt:
            concepts[uri]["altLabels"].add(alt)
    
    for row in hidden_rows:
        uri = row["concept"]["value"]
        hidden = row["hiddenLabel"]["value"]
        if uri not in concepts:
            concepts[uri] = {"prefLabels": set(), "altLabels": set(), "hiddenLabels": set()}
        concepts[uri]["hiddenLabels"].add(hidden)
    
    print(f"  Unique concepts: {len(concepts)}")
    
    # Validate: count total unique name strings
    all_names = set()
    for labels in concepts.values():
        all_names.update(labels["prefLabels"])
        all_names.update(labels["altLabels"])
        all_names.update(labels["hiddenLabels"])
    print(f"  Total unique name strings: {len(all_names)}")
    
    return concepts

def build_output(concepts):
    """Build JSON and flat text output."""
    print("\n=== Phase 2: Building output files ===")
    
    entities = []
    all_names_set = set()
    
    for uri, labels in concepts.items():
        all_variants = list(labels["prefLabels"] | labels["altLabels"] | labels["hiddenLabels"])
        pref_label = next(iter(labels["prefLabels"])) if labels["prefLabels"] else all_variants[0]
        
        entity = {
            "uri": uri,
            "prefLabel": pref_label,
            "variants": sorted(all_variants),
        }
        entities.append(entity)
        all_names_set.update(all_variants)
    
    output = {
        "metadata": {
            "total_concepts_extracted": len(concepts),
            "total_variant_strings": len(all_names_set),
            "extraction_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "AGROVOC SPARQL endpoint (https://agrovoc.fao.org/sparql)",
            "label_types": ["prefLabel", "altLabel", "hiddenLabel"],
            "language": "en",
        },
        "entities": entities,
    }
    
    print(f"Writing JSON ({len(entities)} entities) ...")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Writing flat text ({len(all_names_set)} names) ...")
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        for name in sorted(all_names_set):
            f.write(name + "\n")
    
    json_size = __import__("os").path.getsize(OUTPUT_JSON) / 1024 / 1024
    txt_size = __import__("os").path.getsize(OUTPUT_TXT) / 1024 / 1024
    print(f"  {OUTPUT_JSON}: {json_size:.1f} MB")
    print(f"  {OUTPUT_TXT}: {txt_size:.1f} MB")
    
    return output

def verify(output):
    """Verify completeness."""
    print("\n=== Phase 3: Verification ===")
    
    # 1. Check expected counts
    print(f"  Concepts: {output['metadata']['total_concepts_extracted']}")
    print(f"  Name strings: {output['metadata']['total_variant_strings']}")
    
    # 2. Check for common ag terms
    checks = ["wheat", "Triticum aestivum", "glyphosate", "Puccinia graminis",
              "xylem", "soil", "fungus", "antibiotic", "growth stage"]
    found = 0
    all_names_lower = set()
    for e in output["entities"]:
        for v in e["variants"]:
            all_names_lower.add(v.lower())
    
    for term in checks:
        if term.lower() in all_names_lower:
            found += 1
            print(f"  ✓ '{term}' found")
        else:
            print(f"  ✗ '{term}' MISSING")
    
    print(f"  {found}/{len(checks)} expected terms found")
    
    # 3. Show a few samples
    print("\n  Sample entries:")
    for e in output["entities"][:3]:
        print(f"    {e['uri'].split('/')[-1]}: {e['prefLabel']} ({len(e['variants'])} variants)")
    
    multi = [e for e in output["entities"] if len(e["variants"]) > 2]
    print(f"\n  Concepts with 3+ variants: {len(multi)}")
    for e in multi[:3]:
        print(f"    {e['prefLabel']}: {e['variants']}")

def main():
    concepts = fetch_all_labels()
    output = build_output(concepts)
    verify(output)
    print("\nDone! Full English AGROVOC extraction complete.")

if __name__ == "__main__":
    main()
