#!/usr/bin/env python3
"""
Rebuild data/plant_protection.json pest + disease silos from the clean TNAU
crawl (data/_raw/tnau-agritech/tnau_clean.json).

The prior file's pest/disease silos overrode EVERY relation source with a
single mis-assigned rice-page URL (`insectpest _cereals_paddymain.html`),
mis-classified borers/milwues across silos, and captured crop names as pests.

This rebuild:
  - derives each pest/disease entity from the clean crawl key (name -> crops),
    dropping plant-as-pest captures (names equal to a crop name/alias),
  - merges dual-silo names to their correct silo by keyword (insect -> pest,
    fungal/viral -> disease), dropping boilerplate captures (source, families),
  - keeps the existing weeds + control categories + ipm measure verbatim,
  - re-applies controlled_by edges from tnau_control_pages.json when the page
    title matches an entity and its crop is among the entity's affects.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / "data" / "plant_protection.json"
CLEAN = ROOT / "data" / "_raw" / "tnau-agritech" / "tnau_clean.json"
PAGES = ROOT / "data" / "_raw" / "tnau-agritech" / "tnau_control_pages.json"
CROPS = ROOT / "data" / "crops.json"

SRC = {"id": "tnau-agritech", "url": "https://agritech.tnau.ac.in/crop_protection/crop_prot.html"}


def norm(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).strip()


INSECT_WORDS = ("worm", "moth", "borer", "weevil", "hopper", "aphid", "thrips",
                "bug", "mite", "caterpillar", "cutworm", "maggot", "miner",
                "fly", "beetle", "bollworm", "semilooper", "scale", "jassid",
                "mealybug", "mealworm", "looper", "grub", "termite", "earhead",
                "midge", "imago", "larva", "nymph", "pupa", "leafroller",
                "leaf roller", "leaf folder", "gall fly", "psyllid", "fruit fly",
                "ants", "crickets", "snail", "delia", "euborellia")
DISEASE_WORDS = ("mildew", "rust", "rot", "blight", "smut", "mosaic", "curl",
                 "crinkle", "spot", "canker", "wilt", "virus", "scab", "bacteria",
                 "fungus", "fungal", "disease", "dieback", "die back", "gummosis",
                 "decline", "yellow", "rosette", "little leaf", "leaf curl",
                 "foot rot", "bud rot", "anthracnose", "powdery", "downy",
                 "leaf spot", "cercospora", "black mould", "root rot")


def classify(name: str) -> str:
    """Return 'pest' | 'disease' | None (drop)."""
    n = name.lower()
    insect = any(w in n for w in INSECT_WORDS)
    disease = any(w in n for w in DISEASE_WORDS)
    if insect and not disease:
        return "pest"
    if disease and not insect:
        return "disease"
    if insect and disease:  # "leaf roller" insect in disease listing etc.
        return "pest"
    return None


def make_slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "untitled"


def main():
    clean = json.loads(CLEAN.read_text(encoding="utf-8"))
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    crops = json.loads(CROPS.read_text(encoding="utf-8"))

    crop_names = set()
    for e in crops["entities"]:
        if e.get("type") != "entity":
            continue
        for nm in [e.get("name", "")] + e.get("aliases", []):
            if nm:
                crop_names.add(norm(nm))

    pp = json.loads(PP.read_text(encoding="utf-8"))
    kept = [e for e in pp["entities"]
            if e["id"] not in ("plant_protection.pest.",
                               ) or True]  # placeholder; filtered below

    # keep everything EXCEPT old pest/disease entities (ids match pp.pest./pp.disease.)
    kept = [e for e in pp["entities"]
            if not (e["id"].startswith("plant_protection.pest.")
                    or e["id"].startswith("plant_protection.disease."))]
    kept_ids = {e["id"] for e in kept}

    BAD = ("fabaceae", "solanaceae", "euphorbiaceae", "arecaceae", "brassica",
           "source", "spp", "lab lab", "farmers inno", "vigna unguiculata",
           "malus sylvestris", "musa sp", "cicer arietinum l.", "citrus spp",
           "c. liberica", "prunus salicina", "carica papaya", "psidium guajava",
           "achras sapota", "carthamus tinctorius", "sesamum indicum",
           "sorghum bicolor", "glycine max", "camellia sinensis",
           "pennisetum glaucum", "vitis vinifera", "allium cepa",
           "ricinus communis", "lablab purpureus", "ananas comosus",
           "prunus persica", "pyrus communis", "sun flower", "tree fodder",
           "elettaria cardamomum", "myristica fragrans", "piper longum")

    def good(name: str) -> bool:
        n = norm(name)
        if not n:
            return False
        if n in crop_names:
            return False
        for bad in BAD:
            if bad in n:
                return False
        return True

    by_id = {}

    def add(name: str, silo: str, crops: list):
        eid = f"plant_protection.{silo}.{make_slug(name)}"
        ent = by_id.get(eid)
        rels = [{"predicate": "is_a",
                 "object": f"plant_protection.{silo}s"}] + \
            [{"predicate": "affects", "object": c} for c in sorted(set(crops))] + \
            [{"predicate": "found_in", "object": "location.india"}]
        if ent is None:
            by_id[eid] = {
                "id": eid, "name": name.title(), "type": "entity",
                "domain": "plant_protection", "aliases": [],
                "attributes": {}, "relations": rels,
                "source": dict(SRC),
            }
        else:
            for r in rels:
                if not any(x["predicate"] == r["predicate"] and x["object"] == r["object"]
                           for x in ent["relations"]):
                    ent["relations"].append(r)

    for name, rec in clean["pests"].items():
        if not good(name):
            continue
        add(name, "pest", rec.get("crops", []))

    for name, rec in clean["diseases"].items():
        if not good(name):
            continue
        add(name, "disease", rec.get("crops", []))

    # re-home dual-silo names: apply keyword classification so an insect listed
    # under diseases becomes a pest and vice versa; union the affects crops.
    dual = {}
    for eid, ent in list(by_id.items()):
        cls = classify(ent["name"])
        if cls is None:
            continue
        want = "pest" if cls == "pest" else "disease"
        cur = "disease" if eid.startswith("plant_protection.disease.") else "pest"
        if want == cur:
            continue
        dual.setdefault((ent["name"], want), {"id": None, "crops": []})["crops"] += \
            [r["object"] for r in ent["relations"] if r["predicate"] == "affects"]
        by_id.pop(eid)

    for (name, want), rec in dual.items():
        add(name.capitalize(), want, rec["crops"])

    # merge dual-silo names that classified differently: re-typing handled by
    # classify() above; builds union affects.

    # re-apply controlled_by edges from control pages
    title2id = {}
    for e in by_id.values():
        title2id.setdefault(norm(e["name"]), e["id"])
    cropid2affects = {e["id"]: {r["object"] for r in e["relations"]
                                if r["predicate"] == "affects"} for e in by_id.values()}

    # crop from control-page breadcrumb
    cropmap = {}
    for e in crops["entities"]:
        if e.get("type") != "entity":
            continue
        cropmap.setdefault(norm(e["name"]), e["id"])
        for a in e.get("aliases", []):
            cropmap.setdefault(norm(a), e["id"])

    for rec in pages.values():
        title = rec.get("title")
        edges = rec.get("pesticide_edges") or []
        if not title or not edges:
            continue
        eid = title2id.get(norm(title))
        if not eid:
            continue
        ent = by_id[eid]
        b = rec.get("breadcrumb") or ""
        seg = (b.split("::")[-1] if "::" in b else b).strip()
        seg = re.sub(r"pests? of", "", seg, flags=re.I).strip()
        crop = cropmap.get(norm(seg))
        if crop and cropid2affects.get(eid) and crop not in cropid2affects[eid]:
            continue
        have = {r["object"] for r in ent["relations"]
                if r["predicate"] == "controlled_by"}
        for obj in edges:
            if obj not in have:
                ent["relations"].append({"predicate": "controlled_by", "object": obj})

    # write: preserved (kept) + new (by_id)
    final = kept + sorted(by_id.values(), key=lambda e: e["id"])
    pp["entities"] = final
    # ensure source on domain-level untouched
    PP.write_text(json.dumps(pp, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"pests: {sum(1 for e in by_id.values() if e['id'].startswith('plant_protection.pest.') >= 0 and e['id'].startswith('plant_protection.pest.'))} "
          f"diseases: {sum(1 for e in by_id.values() if e['id'].startswith('plant_protection.disease.'))} "
          f"kept_shell: {len(kept)} total: {len(final)}")


if __name__ == "__main__":
    main()