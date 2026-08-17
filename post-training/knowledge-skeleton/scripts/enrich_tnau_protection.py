#!/usr/bin/env python3
"""
Enrich plant_protection.json with `controlled_by` edges found on TNAU
crop-protection pest/disease detail pages.

Input:  data/_raw/tnau-agritech/tnau_control_pages.json  (one-time crawl output:
        per-page breadcrumb + pest/disease title + matched pesticide ids)
        data/pesticides.json, data/crops.json
Output: data/plant_protection.json with added controlled_by relations.

A page binds a pesticide to an entity only when:
  - the page title matches an entity name/alias (case/space-insensitive), and
  - the page crop (parsed from the breadcrumb, when resolvable) is among the
    entity's `affects` crops.  Unresolvable crops pass through.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / "data" / "plant_protection.json"
PAGES = ROOT / "data" / "_raw" / "tnau-agritech" / "tnau_control_pages.json"
PEST = ROOT / "data" / "pesticides.json"
CROPS = ROOT / "data" / "crops.json"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


def load_titles(entities):
    idx = {}
    for e in entities:
        if e.get("type") != "entity":
            continue
        idx[norm(e["name"])] = e["id"]
        for a in e.get("aliases", []):
            idx.setdefault(norm(a), e["id"])
    idx = {k: v for k, v in idx.items() if k}  # drop empty keys
    return idx


def load_crops():
    data = json.loads(CROPS.read_text(encoding="utf-8"))
    idx = {}
    for e in data.get("entities", []):
        if e.get("type") != "entity":
            continue
        n = e.get("name", "").lower()
        if n:
            idx.setdefault(norm(n), e["id"])
        for a in e.get("aliases", []):
            idx.setdefault(norm(a), e["id"])
    return idx


def page_crop(breadcrumb, cropmap):
    if not breadcrumb:
        return None
    seg = breadcrumb.split("::")[-1]
    seg = re.sub(r"pests? of", " ", seg, flags=re.I)
    nm = norm(seg)
    if nm in cropmap:
        return cropmap[nm]
    for tok in re.split(r"[,/\s]+", seg):
        t = norm(tok)
        if t in cropmap:
            return cropmap[t]
    return None


def main():
    pp = json.loads(PP.read_text(encoding="utf-8"))
    entities = pp["entities"]
    title2id = load_titles(entities)
    cropmap = load_crops()

    eid2affects = {}
    for e in entities:
        eid2affects[e["id"]] = {r["object"] for r in e.get("relations", [])
                                if r["predicate"] == "affects"}

    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    added = 0
    touched = set()
    for idx, rec in pages.items():
        title = rec.get("title")
        edges = rec.get("pesticide_edges") or []
        if not title or not edges:
            continue
        eid = title2id.get(norm(title))
        if not eid:
            continue
        affects = eid2affects.get(eid, set())
        crop = page_crop(rec.get("breadcrumb"), cropmap)
        if crop and affects and crop not in affects:
            continue  # page is for a different crop; name collision
        ent = next(e for e in entities if e["id"] == eid)
        have = {r["object"] for r in ent.get("relations", [])
                if r["predicate"] == "controlled_by"}
        new = sorted(set(e for e in edges if e not in have))
        for obj in new:
            ent.setdefault("relations", []).append(
                {"predicate": "controlled_by", "object": obj})
        added += len(new)
        if new:
            touched.add(eid)

    PP.write_text(json.dumps(pp, indent=1, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    print(f"added {added} controlled_by edges to {len(touched)} entities")


if __name__ == "__main__":
    main()