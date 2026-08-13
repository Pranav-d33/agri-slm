#!/usr/bin/env python3
"""
Attach registered pesticide formulations to active-ingredient entities.

Source: PPQS "Pesticide Formulations Registered for use in the Country under
the Insecticides Act, 1968 (Updated 31.03.2026)" (28-page PDF). Each row like
"Acephate 75% SP" is a registered formulation; actives with multiple rows get a
formulations list. Matching is prefix-based on normalized names (exact, then
fuzzy with ratio>=0.9 against a single candidate) so nothing is misattributed.
Unmatched lines are counted and reported, never invented.
"""

import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEST = ROOT / "data" / "pesticides.json"
RAW = ROOT / "data" / "_raw" / "cibrc" / "registered_actives_9_3.json"
FORMULATIONS_TXT = Path("/tmp/opencode/formulations_full.txt")  # pre-extracted PDF text
SRC = {
    "id": "cibrc-formulations",
    "url": "https://ppqs.gov.in/sites/default/files/list_pf_pesticide_formulations_registered_as_on_31.03.2026.pdf",
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def base(s):
    return re.sub(r"\s*\(.*?\)\s*", "", s).strip()


def parse_rows():
    txt = re.sub(r"===PAGE\d+===\n?", "", FORMULATIONS_TXT.read_text(encoding="utf-8"))
    rows = []
    for l in txt.split("\n"):
        l = l.strip()
        if re.match(r"^\d+\s", l):
            rows.append(re.sub(r"^\d+\s+", "", l))
    return rows


def build_matcher():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    # (base_norm, raw_norm, raw_name) for exact prefix matching
    exact = [(norm(base(r)), norm(r), r) for r in raw]
    # also match against pesticide entity names (canonical spellings differ from raw)
    data = json.loads(PEST.read_text(encoding="utf-8"))
    for e in data["entities"]:
        if e["type"] == "substance":
            exact.append((norm(base(e["name"])), norm(e["name"]), e["name"]))
    # fuzzy candidates keyed by leading token
    fuzzy = {}
    for r in raw:
        for k in (norm(base(r)), norm(r)):
            if len(k) >= 5:
                fuzzy.setdefault(k[:5], set()).add(r)
    for e in data["entities"]:
        if e["type"] == "substance":
            for k in (norm(base(e["name"])), norm(e["name"])):
                if len(k) >= 5:
                    fuzzy.setdefault(k[:5], set()).add(e["name"])
    return exact, fuzzy


def find_active(form, exact, fuzzy):
    fn = norm(form)
    best = None
    best_len = 0
    for bn, rn, name in exact:
        if len(bn) >= 4 and fn.startswith(bn) and len(bn) > best_len:
            best, best_len = name, len(bn)
    if best:
        return best
    lead = re.match(r"^([a-z][a-z0-9\- ]*?)(?=[\d%])", fn)
    if not lead:
        lead = re.match(r"^([a-z][a-z ]*)", fn)
    if lead:
        tok = re.sub(r"[^a-z0-9]", "", lead.group(1))
        if len(tok) >= 5:
            cands = fuzzy.get(tok[:5], set())
            good = [n for n in cands if difflib.SequenceMatcher(None, tok, norm(n)).ratio() >= 0.9]
            if len(good) == 1:
                return good[0]
    return None


def main():
    rows = parse_rows()
    exact, fuzzy = build_matcher()
    by_name = {}
    unmatched = []
    for r in rows:
        a = find_active(r, exact, fuzzy)
        if a:
            by_name.setdefault(a.lower(), []).append(r)
        else:
            unmatched.append(r)

    data = json.loads(PEST.read_text(encoding="utf-8"))
    added = 0
    for e in data["entities"]:
        key = e["name"].lower()
        if key in by_name:
            e.setdefault("attributes", {})["formulations"] = sorted(set(by_name[key]))
            e.setdefault("notes", "")
            if not e["notes"]:
                e["notes"] = f"formulations from PPQS list (31.03.2026): {len(by_name[key])} registered"
            added += 1
    PEST.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"attached formulations to {added} entities")
    print(f"unmatched formulation lines: {len(unmatched)}")
    for u in unmatched:
        print("  ?", u)


if __name__ == "__main__":
    main()
