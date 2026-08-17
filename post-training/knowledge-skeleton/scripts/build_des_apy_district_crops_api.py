#!/usr/bin/env python3
"""Fill major_crops for districts from DES APY district-level crop production
statistics, fetched live from the DES report builder API
(data/_raw/des-apy/api/des_extract_2022.json, source des-apy-district).

The extract maps each DES crop code -> ["State|District", ...] for every
district that reported any area for that crop in crop-year 2022-2023. This
script inverts that map and writes major_crops (crops.json ids) for districts
that lack them, matching our LGD district names to DES names via an explicit
rename map. Districts with no DES data at all stay untouched.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISTRICTS_PATH = os.path.join(ROOT, "data", "locations", "districts.json")
EXTRACT = os.path.join(ROOT, "data", "_raw", "des-apy", "api", "des_extract_2022.json")
SRC_URL = "https://data.desagri.gov.in/website/crops-apy-report-web"

# DES crop code -> crops.json entity id (only crops we fill)
CROP_CODE_MAP = {
    "1": "crops.rice", "2": "crops.wheat", "3": "crops.jowar", "4": "crops.bajra",
    "5": "crops.maize", "6": "crops.ragi", "7": "crops.barley",
    "14": "crops.pigeon_pea", "65": "crops.green_gram", "55": "crops.black_gram",
    "13": "crops.gram", "75": "crops.moth_bean", "74": "crops.khesari",
    "76": "crops.horse_gram", "155": "crops.cowpea", "73": "crops.lentil",
    "78": "crops.field_pea", "18": "crops.linseed", "19": "crops.castor",
    "17": "crops.mustard", "21": "crops.niger", "23": "crops.sunflower",
    "16": "crops.sesame", "15": "crops.groundnut", "24": "crops.soybean",
    "20": "crops.safflower", "26": "crops.cotton", "27": "crops.jute",
    "28": "crops.mesta", "29": "crops.fibre.sannhemp", "22": "crops.coconut",
    "62": "crops.sugarcane", "38": "crops.black_pepper", "39": "crops.chili",
    "122": "crops.ginger", "50": "crops.cashew", "63": "crops.tobacco",
    "124": "crops.banana", "95": "crops.plantation.arecanut", "42": "crops.cardamom",
    "43": "crops.spices.coriander", "47": "crops.spices.garlic", "46": "crops.vegetables.tapioca",
    "49": "crops.onion", "45": "crops.potato", "48": "crops.vegetables.sweet_potato",
    "41": "crops.turmeric",
}

# our (state, district) -> DES district name (when LGD name differs from DES)
DISTRICT_RENAME = {
    ("Andhra Pradesh", "Eluru"): "Eluru",
    ("Bihar", "Kaimur (Bhabua)"): "Kaimur (bhabua)",
    ("Chhattisgarh", "Balodabazar-Bhatapara"): "Baloda bazar",
    ("Chhattisgarh", "Gaurela-Pendra-Marwahi"): "Gaurella-pendra-marwahi",
    ("Chhattisgarh", "Khairagarh-Chhuikhadan-Gandai"): "Khairgarh chhuikhadan gandai",
    ("Chhattisgarh", "Manendragarh-Chirmiri-Bharatpur(M C B)"): "Manendragarh chirimiri bharatpur",
    ("Chhattisgarh", "Mohla-Manpur-Ambagarh Chouki"): "Mohla manpur ambagarh chouki",
    ("Chhattisgarh", "Sakti"): "Sakti",
    ("Chhattisgarh", "Sarangarh-Bilaigarh"): "Sarangarh bilaigarh",
    ("Haryana", "Charkhi Dadri"): "Charki dadri",
    ("Karnataka", "Dakshina Kannada"): "Dakshin kannad",
    ("Karnataka", "Uttara Kannada"): "Uttar kannad",
    ("Karnataka", "Vijayanagara"): "Vijayanagar",
    ("Karnataka", "Bengaluru South"): "Bengaluru urban",
    ("Mizoram", "Siaha"): "Saiha",
    ("Nagaland", "Niuland"): "Nuiland",
    ("Odisha", "Jajpur"): "Jajapur",
    ("Odisha", "Nayagada"): "Nayagarh",
    ("Odisha", "Sundaragada"): "Sundargarh",
    ("Puducherry", "Puducherry"): "Pondicherry",
    ("Punjab", "Ferozepur"): "Firozepur",
    ("Rajasthan", "Khairthal-Tijara"): "Khairtal-Tijara",
    ("Tamil Nadu", "Tenkasi"): "Thenkasi",
    ("Telangana", "Bhadradri Kothagudem"): "Bhadradri",
    ("Telangana", "Hanumakonda"): "Warangal urban",
    ("Telangana", "Jayashankar Bhupalapally"): "Jayashankar",
    ("Telangana", "Jogulamba Gadwal"): "Jogulamba",
    ("Telangana", "Kumuram Bheem Asifabad"): "Komaram bheem asifabad",
    ("Telangana", "Mahabubnagar"): "Mahbubnagar",
    ("Telangana", "Medchal Malkajgiri"): "Medchal",
    ("Telangana", "Narayanpet"): "Narayanapet",
    ("Telangana", "Rajanna Sircilla"): "Rajanna",
    ("Telangana", "Ranga Reddy"): "Rangareddi",
    ("Telangana", "Yadadri Bhuvanagiri"): "Yadadri",
    ("Uttar Pradesh", "Bhadohi"): "Sant ravidas nagar",
}


def norm(s):
    s = s.lower().replace("&", "and")
    s = s.strip().lstrip("the ").strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    dist = json.load(open(DISTRICTS_PATH))
    extract = json.load(open(EXTRACT))

    # invert extract: (state_norm, district_norm) -> set of crop ids
    des_map = {}
    for code, pairs in extract.items():
        cid = CROP_CODE_MAP.get(code)
        if not cid:
            continue
        for p in pairs:
            st, di = p.split("|")
            key = (norm(st), norm(di))
            des_map.setdefault(key, set()).add(cid)

    changed = 0
    for s in dist["states"]:
        for d in s["districts"]:
            if "attributes" in d and "major_crops" in d["attributes"]:
                continue
            des_name = DISTRICT_RENAME.get((s["state"], d["name"]), d["name"])
            crops = des_map.get((norm(s["state"]), norm(des_name)), set())
            if not crops:
                continue
            attrs = d.setdefault("attributes", {})
            attrs["major_crops"] = sorted(crops)
            attrs["source"] = {"id": "des-apy-district", "url": SRC_URL}
            d["notes"] = "Major crops from DES APY district-level crop production statistics (des-agri-apy); only crops covered by the APY reports are listed."
            changed += 1

    with open(DISTRICTS_PATH, "w") as f:
        json.dump(dist, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Set major_crops for {changed} districts.")


if __name__ == "__main__":
    main()