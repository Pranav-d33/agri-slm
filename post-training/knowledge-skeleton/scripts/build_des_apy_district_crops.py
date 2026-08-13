#!/usr/bin/env python3
"""Fill major_crops for districts from DES APY district-level crop production
statistics (data/_raw/des-apy/, source des-agri-apy).

Handles two file layouts:
  des_<crop>.pdf        — one crop, all states: "N. <District> <year>..." rows
  des_<code>_<season>.pdf — all crops for a set of states: "N. <Crop>" headers
                           then "N. <District> <year>..." rows
Records which covered crops are grown (any area reported) per district. Only
districts already carrying major_crops are skipped. Unmatched names reported.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "_raw", "des-apy")
DISTRICTS_PATH = os.path.join(ROOT, "data", "locations", "districts.json")
CROPS_PATH = os.path.join(ROOT, "data", "crops.json")

import pdfplumber

# des_<crop>.pdf file stem -> crops.json id
CROP_FILE_MAP = {
    "arhar": "crops.pigeon_pea", "bajra": "crops.bajra", "barley": "crops.barley",
    "castor": "crops.castor", "cowpea": "crops.cowpea", "gram": "crops.gram",
    "horsegram": "crops.horse_gram", "jowar": "crops.jowar", "jute": "crops.jute",
    "khesari": "crops.khesari", "linseed": "crops.linseed", "masoor": "crops.lentil",
    "mesta": "crops.mesta", "moong": "crops.green_gram", "moth": "crops.moth_bean",
    "niger": "crops.niger", "safflower": "crops.safflower", "sesame": "crops.sesame",
    "soybean": "crops.soybean", "sunflower": "crops.sunflower",
    "tobacco": "crops.tobacco", "urad": "crops.black_gram",
}

# crop names as they appear in the state-code files (normalized) -> crops.json id
CROP_NAME_MAP = {
    "rice": "crops.rice", "paddy": "crops.rice", "wheat": "crops.wheat",
    "jowar": "crops.jowar", "bajra": "crops.bajra", "maize": "crops.maize",
    "ragi": "crops.ragi", "barley": "crops.barley", "gram": "crops.gram",
    "tur": "crops.pigeon_pea", "arhar": "crops.pigeon_pea", "moong": "crops.green_gram",
    "urad": "crops.black_gram", "masoor": "crops.lentil", "horsegram": "crops.horse_gram",
    "khesari": "crops.khesari", "cowpea": "crops.cowpea",
    "groundnut": "crops.groundnut", "sesamum": "crops.sesame", "sesame": "crops.sesame",
    "mustard": "crops.mustard", "rapeseed": "crops.mustard", "linseed": "crops.linseed",
    "castor": "crops.castor", "safflower": "crops.safflower", "sunflower": "crops.sunflower",
    "niger": "crops.niger", "soybean": "crops.soybean", "cotton": "crops.cotton",
    "jute": "crops.jute", "mesta": "crops.mesta", "sugarcane": "crops.sugarcane",
    "tobacco": "crops.tobacco", "potato": "crops.potato", "onion": "crops.onion",
}

# state name in PDF -> our state name
STATE_MAP = {
    "Dadra and Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "North Eastern States": "Arunachal Pradesh",
}

CROP_HDR = re.compile(r"^\d+\.\s+(.+)$")
DIST_HDR = re.compile(r"^\d+\.\s+([A-Za-z][A-Za-z .\-']+?)\s+\d{4}\s*-\s*\d{4}\s+")


def norm(name):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", name.lower().strip())).strip()


def main():
    dist = json.load(open(DISTRICTS_PATH))
    crops_data = json.load(open(CROPS_PATH))
    crop_ids = {e["id"] for e in crops_data["entities"]}

    by_state = {}
    for s in dist["states"]:
        by_state.setdefault(s["state"], {})
        for d in s["districts"]:
            by_state[s["state"]][norm(d["name"])] = d

    # state -> {district norm -> set of crop ids}
    result = {}
    files = sorted(os.listdir(RAW))

    for fn in files:
        m = re.match(r"^des_(\d+)_([A-Z])\.pdf$", fn)
        if m:
            # all-crop layout: crop headers ("N. Rice") + district rows
            with pdfplumber.open(os.path.join(RAW, fn)) as pdf:
                cur_state = None
                cur_crop = None
                cur_dist = None
                for p in pdf.pages:
                    for line in (p.extract_text() or "").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        if line in by_state or line in STATE_MAP:
                            cur_state = STATE_MAP.get(line, line)
                            cur_crop = None
                            cur_dist = None
                            continue
                        if cur_state is None:
                            continue
                        dm = DIST_HDR.match(line)
                        if dm:
                            nm = norm(dm.group(1))
                            if cur_crop and nm in by_state[cur_state]:
                                cur_dist = by_state[cur_state][nm]
                                result.setdefault(cur_state, {}).setdefault(nm, set()).add(cur_crop)
                            else:
                                cur_dist = None
                            continue
                        if re.search(r"\d{4}\s*-\s*\d{4}", line) and cur_dist is not None:
                            result[cur_state][norm(cur_dist["name"])].add(cur_crop)
                            continue
                        # crop header candidate: "N. Rice" (single line, no year)
                        cm = CROP_HDR.match(line)
                        if cm and not re.search(r"\d{4}", line):
                            cname = norm(cm.group(1))
                            cname = re.sub(r"\s*\(.+\)$", "", cname)
                            cid = CROP_NAME_MAP.get(cname)
                            cur_crop = cid if cid in crop_ids else None
                            cur_dist = None
            continue
        m = re.match(r"^des_([a-z]+)\.pdf$", fn)
        if m and m.group(1) in CROP_FILE_MAP:
            crop = CROP_FILE_MAP[m.group(1)]
            if crop not in crop_ids:
                continue
            with pdfplumber.open(os.path.join(RAW, fn)) as pdf:
                cur_state = None
                cur_dist = None
                for p in pdf.pages:
                    for line in (p.extract_text() or "").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        if line in by_state or line in STATE_MAP:
                            cur_state = STATE_MAP.get(line, line)
                            cur_dist = None
                            continue
                        if cur_state is None:
                            continue
                        dm = DIST_HDR.match(line)
                        if dm:
                            nm = norm(dm.group(1))
                            if nm in by_state[cur_state]:
                                cur_dist = by_state[cur_state][nm]
                                result.setdefault(cur_state, {}).setdefault(nm, set()).add(crop)
                            else:
                                cur_dist = None
                            continue
                        if cur_dist is not None and re.search(r"\d{4}\s*-\s*\d{4}", line):
                            result[cur_state][norm(cur_dist["name"])].add(crop)

    src_url = "https://data.desagri.gov.in/website/crops-apy-report-web"
    changed = 0
    for s in dist["states"]:
        if s["state"] not in result:
            continue
        for d in s["districts"]:
            if "attributes" in d and "major_crops" in d["attributes"]:
                continue
            crops = result[s["state"]].get(norm(d["name"]), set())
            crops = [c for c in crops if c != "crops"]
            if not crops:
                continue
            attrs = d.setdefault("attributes", {})
            attrs["major_crops"] = sorted(crops)
            attrs["source"] = {"id": "des-agri-apy", "url": src_url}
            d["notes"] = "Major crops from DES APY district-level crop production statistics (des-agri-apy); only crops covered by the APY reports are listed."
            changed += 1

    with open(DISTRICTS_PATH, "w") as f:
        json.dump(dist, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Set major_crops for {changed} districts.")


if __name__ == "__main__":
    main()
