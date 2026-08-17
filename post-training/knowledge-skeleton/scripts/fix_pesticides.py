#!/usr/bin/env python3
"""
Fix data/pesticides.json per the 8-domain audit:

1. registered_actives membership: raw CIB&RC 9(3) list has 371 actives; the
   file only memberships 345. Add `is_a pesticides.registered_actives` to the
   26 non-banned entities whose name/alias normalizes to a raw active.
2. Merge the typo duplicate `pesticides.thiomethoxam` into
   `pesticides.thiamethoxam` (mis-spelled id; same substance, fuller record).
3. Add `pesticides.fumigants` category (CIB&RC formulations section E) and
   membership for aluminium/magnesium phosphide, methyl bromide, dazomet,
   DD-mixture. Acaricide/Nematicide are NOT CIB&RC list sections -> noted on
   the classes category instead of fabricated categories.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PEST = ROOT / "data" / "pesticides.json"
RAW = ROOT / "data" / "_raw" / "cibrc" / "registered_actives_9_3.json"


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


def main():
    p = json.loads(PEST.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    ents = p["entities"]

    def is_in(e, target):
        return any(r["predicate"] == "is_a" and r["object"] == target
                   for r in e.get("relations", []))

    member_of = "pesticides.registered_actives"

    # 1. register the missing non-banned actives
    def entity_of(name):
        n = norm(name)
        for e in ents:
            if norm(e.get("name", "")) == n:
                return e
        for e in ents:
            if any(norm(a) == n for a in e.get("aliases", [])):
                return e
        return None

    added = 0
    for name in raw:
        e = entity_of(name)
        if e is None or is_in(e, member_of) or is_in(e, "pesticides.banned"):
            continue
        e.setdefault("relations", []).append(
            {"predicate": "is_a", "object": member_of})
        added += 1

    # 2. merge typo duplicate into thiamethoxam
    typo = next(e for e in ents if e["id"] == "pesticides.thiomethoxam")
    main_ = next(e for e in ents if e["id"] == "pesticides.thiamethoxam")
    main_relations = {r["predicate"]: r["object"] for r in main_.get("relations", [])}
    for r in typo.get("relations", []):
        if r["predicate"] not in main_relations or main_relations[r["predicate"]] != r["object"]:
            main_.setdefault("relations", []).append(r)
    main_["notes"] = typo.get("notes", "")
    ents = [e for e in ents if e["id"] != "pesticides.thiomethoxam"]

    # 3. Fumigants category
    if not any(e["id"] == "pesticides.fumigants" for e in ents):
        ents.append({
            "id": "pesticides.fumigants", "name": "Fumigants",
            "type": "category", "domain": "pesticides", "aliases": [],
            "attributes": {"note": "CIB&RC formulations list section E (Fumigants)"},
            "relations": [
                {"predicate": "is_a", "object": "pesticides.classes"},
                {"predicate": "part_of", "object": "pesticides.classes"},
            ],
            "source": {"id": "cibrc-formulations",
                       "url": "https://ppqs.gov.in/sites/default/files/list_pf_pesticide_formulations_registered_as_on_31.03.2026.pdf"},
        })
    fumigant_ids = ("pesticides.aluminium_phosphide", "pesticides.magnesium_phosphide_plates",
                    "pesticides.methyl_bromide", "pesticides.dazomet",
                    "pesticides.dichloropropene_and_dichloropropane_mixture_dd_mixture")
    for e in ents:
        if e["id"] in fumigant_ids and not is_in(e, "pesticides.fumigants"):
            e.setdefault("relations", []).append(
                {"predicate": "is_a", "object": "pesticides.fumigants"})

    # acaricide/nematicide: not CIB&RC list sections; note, don't fabricate
    for e in ents:
        if e["id"] == "pesticides.classes":
            e.setdefault("attributes", {})["note"] = (
                "8 CIB&RC sections: Insecticides, Fungicides, Herbicides, Rodenticides, "
                "Fumigants, PGR, Public-Health, Biopesticides. Acaricides/nematicides are "
                "not separate CIB&RC list sections; such actives sit under Insecticides.")

    p["entities"] = ents
    PEST.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    member_count = sum(1 for e in ents if is_in(e, member_of))
    print(f"registered actives now: {member_count} (added {added}); "
          f"typo duplicate merged; fumigants category added")


if __name__ == "__main__":
    main()