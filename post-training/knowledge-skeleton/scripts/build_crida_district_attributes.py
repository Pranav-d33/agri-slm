#!/usr/bin/env python3
"""Fill per-district attributes (agro_climatic_zone, narp_zone, primary_soils,
major_crops) in districts.json from ICAR-CRIDA Agriculture Contingency Plan
district PDFs (crida-cp source).

Reads previously-downloaded PDFs from a cache directory.  Each district's:
  - 1.1.pdf  -> agro-climatic (PC) + NARP zone
  - 1.4.pdf  -> major soils
  - 1.7.pdf  -> major field crops + horticulture crops

Only crops that map cleanly to a crops.json id are recorded; unmapped names
are skipped (never invented).  Districts without parseable data are left
untouched.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISTRICTS_PATH = os.path.join(ROOT, "data", "locations", "districts.json")
CROPS_PATH = os.path.join(ROOT, "data", "crops.json")
PDF_CACHE = os.environ.get("CRIDA_PDF_CACHE", "/tmp/opencode/pdfs")

# state name -> CRIDA abbreviation
ABBR = {
    "Maharashtra": "MH", "West Bengal": "WB", "Kerala": "KL",
    "Himachal Pradesh": "HP", "Haryana": "HR",
}

# JSON district name -> CRIDA PDF folder name
PDF_NAME = {
    "Maharashtra": {
        "Ahilyanagar": "Ahmednagar", "Chhatrapati Sambhajinagar": "Aurangabad",
        "Dharashiv": "Osmanabad", "Amravati": "Amravathi", "Sindhudurg": "Sindhudurga",
        "Raigad": "Raigarh", "Thane": "Thane and phalagar",
    },
    "Haryana": {"Gurugram": "Gurgoan", "Nuh": "Mewat", "Sonipat": "Sonipet"},
    "Kerala": {"Kasaragod": "Kasargod", "Thrissur": "Trissur"},
    "Himachal Pradesh": {"Lahaul And Spiti": "Lahaul & Spiti"},
    "West Bengal": {
        "Cooch Behar": "Coochbehar", "Uttar Dinajpur": "Uttar-Dinajpur",
        "North 24 Parganas": "North 24 parganas", "South 24 Parganas": "South 24-Parganas",
        "Purba Bardhaman": "Bardhaman",
    },
}

# crop name (lowercased, normalized) -> crops.json id
CROP_MAP = {
    "paddy": "crops.rice", "rice": "crops.rice",
    "wheat": "crops.wheat", "barley": "crops.barley", "oats": "crops.oats",
    "maize": "crops.maize", "sorghum": "crops.jowar", "jowar": "crops.jowar",
    "pearl millet": "crops.bajra", "bajra": "crops.bajra",
    "ragi": "crops.ragi", "finger millet": "crops.ragi",
    "kodo millet": "crops.kodo_millet", "little millet": "crops.little_millet",
    "foxtail millet": "crops.foxtail_millet", "barnyard millet": "crops.barnyard_millet",
    "proso millet": "crops.proso_millet", "browntop millet": "crops.browntop_millet",
    "millets": "crops.millets",
    "chick pea": "crops.gram", "gram": "crops.gram", "chickpea": "crops.gram",
    "pigeon pea": "crops.pigeon_pea", "tur": "crops.pigeon_pea", "arhar": "crops.pigeon_pea",
    "red gram": "crops.pigeon_pea",
    "green gram": "crops.green_gram", "moong": "crops.green_gram",
    "black gram": "crops.black_gram", "urd": "crops.black_gram",
    "lentil": "crops.lentil", "masoor": "crops.lentil",
    "field pea": "crops.field_pea", "peas": "crops.vegetables.peas",
    "rajma": "crops.rajma", "horse gram": "crops.horse_gram",
    "moth bean": "crops.moth_bean", "khesari": "crops.khesari",
    "cowpea": "crops.cowpea", "pulses": "crops.pulses",
    "groundnut": "crops.groundnut", "sesame": "crops.sesame", "til": "crops.sesame",
    "mustard": "crops.mustard", "rapeseed": "crops.mustard", "rapeseed mustard": "crops.mustard",
    "soyabean": "crops.soybean", "soybean": "crops.soybean",
    "safflower": "crops.safflower", "sunflower": "crops.sunflower",
    "linseed": "crops.linseed", "niger": "crops.niger", "castor": "crops.castor",
    "oil seeds": "crops.oilseeds", "oilseed": "crops.oilseeds",
    "cotton": "crops.cotton", "jute": "crops.jute", "mesta": "crops.mesta",
    "sugarcane": "crops.sugarcane", "sugar beet": "crops.sugar_beet",
    "tobacco": "crops.tobacco", "potato": "crops.potato",
    "sweet potato": "crops.vegetables.sweet_potato",
    "onion": "crops.onion", "tomato": "crops.tomato", "chilli": "crops.chili",
    "chili": "crops.chili", "chillies": "crops.chili", "green chilli": "crops.chili",
    "brinjal": "crops.vegetables.brinjal", "eggplant": "crops.vegetables.brinjal",
    "okra": "crops.vegetables.okra", "cabbage": "crops.vegetables.cabbage",
    "cauliflower": "crops.vegetables.cauliflower", "carrot": "crops.vegetables.carrot",
    "radish": "crops.vegetables.radish", "spinach": "crops.vegetables.spinach",
    "cucumber": "crops.vegetables.cucumber", "bottle gourd": "crops.vegetables.bottle_gourd",
    "bitter gourd": "crops.vegetables.bitter_gourd", "ridge gourd": "crops.vegetables.ridge_gourd",
    "pumpkin": "crops.vegetables.cucumber", "drumstick": "crops.vegetables.drumstick",
    "cucurbits": "crops.vegetables.cucumber",
    "amaranth": "crops.vegetables.amaranth", "beans": "crops.vegetables.beans",
    "capsicum": "crops.vegetables.capsicum", "mushroom": "crops.vegetables.mushroom",
    "tapioca": "crops.vegetables.tapioca", "cassava": "crops.vegetables.tapioca",
    "mango": "crops.mango", "guava": "crops.fruits.guava",
    "banana": "crops.banana", "plantain": "crops.banana",
    "papaya": "crops.fruits.papaya", "pappaya": "crops.fruits.papaya",
    "pineapple": "crops.fruits.pineapple", "jackfruit": "crops.fruits.jackfruit",
    "jack": "crops.fruits.jackfruit", "sapota": "crops.fruits.sapota", "chiku": "crops.fruits.sapota",
    "pomegranate": "crops.fruits.pomegranate", "grapes": "crops.grapes",
    "apple": "crops.apple", "pear": "crops.fruits.pear", "peach": "crops.fruits.peach",
    "plum": "crops.fruits.plum", "apricot": "crops.fruits.apricot",
    "walnut": "crops.fruits.walnut", "almond": "crops.fruits.almond",
    "strawberry": "crops.fruits.strawberry", "litchi": "crops.fruits.litchi",
    "lemon": "crops.fruits.lemon", "citrus": "crops.fruits.mandarin",
    "mandarin": "crops.fruits.mandarin", "orange": "crops.fruits.sweet_orange",
    "muskmelon": "crops.fruits.muskmelon", "watermelon": "crops.fruits.watermelon",
    "aonla": "crops.fruits.aonla", "custard apple": None,  # not in taxonomy
    "coconut": "crops.coconut", "arecanut": "crops.plantation.arecanut",
    "cashew": "crops.cashew", "rubber": "crops.rubber",
    "coffee": "crops.coffee", "tea": "crops.tea", "cocoa": "crops.plantation.cocoa",
    "cardamom": "crops.cardamom", "ginger": "crops.ginger",
    "turmeric": "crops.turmeric", "pepper": "crops.black_pepper",
    "black pepper": "crops.black_pepper", "coriander": "crops.spices.coriander",
    "cumin": "crops.spices.cumin", "fenugreek": "crops.spices.fenugreek",
    "garlic": "crops.spices.garlic", "fennel": "crops.spices.fennel",
    "ajwain": "crops.spices.ajwain", "tamarind": "crops.spices.tamarind",
    "cinnamon": "crops.spices.cinnamon", "clove": "crops.spices.clove",
    "nutmeg": "crops.spices.nutmeg", "vanilla": "crops.spices.vanilla",
    "asafoetida": "crops.spices.asafoetida",
    "flowers": "crops.horticulture.flowers", "floriculture": "crops.horticulture.flowers",
    "medicinal": "crops.horticulture.aromatics_medicinal",
    "aromatic": "crops.horticulture.aromatics_medicinal",
    "berseem": "crops.fodder.berseem", "lucerne": "crops.fodder.lucerne",
    "napier": "crops.fodder.napier", "guinea grass": "crops.fodder.guinea_grass",
    "stylo": "crops.fodder.stylo", "fodder grass": "crops.fodder",
    "fodder": "crops.fodder", "fodder crops": "crops.fodder",
    "jaggery": "crops.sugar", "sugar": "crops.sugar",
}


def norm(name):
    n = name.lower().strip().rstrip(".")
    n = re.sub(r"\s+", " ", n)
    return n


def map_crop(name):
    n = norm(name)
    if n in CROP_MAP:
        return CROP_MAP[n]
    return None


def parse_soils(text):
    """Return list of soil type names from a 1.4 soils table."""
    soils = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if re.match(r"^1\s*[.]?\s*4\b", raw) or re.match(r"^total\b", raw, re.I):
            continue
        if re.search(r"like red sandy loam deep soils|common names? like red", raw.lower()):
            continue
        # strip leading row number like "1." / "2." / "1." with no space
        body = re.sub(r"^\s*\d+\s*[.)]\s*", "", raw)
        body = re.sub(r"\s*[-–—]\s*", " ", body)
        # strip trailing area/percent figures (one or two numeric groups, optional *)
        body = re.sub(r"\s+\d[\d.,]*(?:\s+\d[\d.,]*\*?)?\s*$", "", body)
        body = body.strip(" .")
        if not body or len(body) < 3 or re.search(r"\d", body):
            continue
        if body.lower().startswith(("major soil", "common name", "sl.", "s.no", "area", "percent", "total", "others", "etc")):
            continue
        if "etc" in body.lower():
            continue
        # continuation line like "horizon" -> append to previous soil
        if body.lower() in ("horizon",) and soils:
            soils[-1] = soils[-1] + " " + body
            continue
        soils.append(body)
    return soils


def parse_crops(text):
    """Return ordered list of crops.json ids from a 1.7 crops table."""
    ids = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("1.7"):
            continue
        # crop name = leading alphabetic word-run (skip leading S.No number); strip trailing data
        m = re.match(r"^\s*\d*\s*([A-Za-z][A-Za-z ]+?)\s+[-–.\s]*\d", line)
        if not m:
            continue
        name = m.group(1).strip()
        cid = map_crop(name)
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids


def extract_zone(text):
    """Return (pc_zone, narp_zone) from a 1.1 PDF text."""
    # Normalize: reunite "(Planning ... \n Commission)" onto one line.
    blob = text.replace("(NARP)", "(NARP)").replace("(Narp)", "(NARP)")
    blob = re.sub(r"\(Planning\s*\n+\s*Commission\)", "(Planning Commission)", blob)
    pc = None
    narp = None
    for line in blob.splitlines():
        m = re.search(r"\(NARP\)[:]?\s*(.+)$", line)
        if m:
            narp = m.group(1).strip()
        if not narp:
            m = re.search(r"Zone\s*\(NARP\)\s*(.+)$", line, re.I)
            if m:
                narp = m.group(1).strip()
        m = re.search(r"\(Planning Commission\)\s*(.+)", line)
        if m and not pc:
            pc = m.group(1).strip()
    return pc, narp


def main():
    with open(DISTRICTS_PATH) as f:
        dist = json.load(f)
    with open(CROPS_PATH) as f:
        crops_data = json.load(f)
    crop_ids = {e["id"] for e in crops_data["entities"]}

    # load pre-parsed PDF text (state -> "AB__district__sec.pdf" -> text)
    with open(os.path.join(PDF_CACHE, "fulldump.json")) as f:
        dump = json.load(f)

    changed = 0
    for s in dist["states"]:
        state = s["state"]
        if state not in ABBR:
            continue
        ab = ABBR[state]
        pdfn = PDF_NAME.get(state, {})
        st_dump = dump.get(ab, {})
        for d in s["districts"]:
            name = d["name"]
            pname = pdfn.get(name, name)
            t1 = st_dump.get(f"{ab}__{pname}__1.1.pdf", "")
            t4 = st_dump.get(f"{ab}__{pname}__1.4.pdf", "")
            t7 = st_dump.get(f"{ab}__{pname}__1.7.pdf", "")

            # zone from 1.1
            pc, narp = extract_zone(t1)
            soils = parse_soils(t4)
            crops = [c for c in parse_crops(t7) if c in crop_ids]
            # dedupe preserving order, drop root 'crops'
            crops = [c for c in dict.fromkeys(crops) if c != "crops"]

            if not (pc or narp or soils or crops):
                continue

            attrs = d.setdefault("attributes", {})
            if pc:
                attrs["agro_climatic_zone"] = pc
            if narp:
                attrs["narp_zone"] = narp.strip().lstrip("*").strip()
            if soils:
                attrs["primary_soils"] = soils
            if crops:
                attrs["major_crops"] = crops
            attrs["source"] = {
                "id": "crida-cp",
                "url": f"https://icar-crida.res.in/CCP/{ab}/{pname.replace(' ', '%20')}/1.1.pdf",
            }
            # update note
            d["notes"] = "District attributes from ICAR-CRIDA Agriculture Contingency Plan (crida-cp)."
            changed += 1

    with open(DISTRICTS_PATH, "w") as f:
        json.dump(dist, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Updated attributes for {changed} districts.")


if __name__ == "__main__":
    main()
