#!/usr/bin/env python3
"""Deterministic, source-backed partial fill of district-level attributes
(agro-climatic zone, major crops, primary soils) for Uttarakhand districts,
from ICAR-CRIDA Agriculture Contingency Plans (crida-cp).

Only facts present in the CRIDA CP PDFs are encoded. Other districts get a
TODO note. Run from the project root.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "data/locations/districts.json"

# crop display name -> crops.json entity id (mapped against data/crops.json)
C = {
    "rice": "crops.rice", "wheat": "crops.wheat", "maize": "crops.maize",
    "barley": "crops.barley", "finger_millet": "crops.ragi",
    "barnyard_millet": "crops.barnyard_millet", "sugarcane": "crops.sugarcane",
    "potato": "crops.potato", "lentil": "crops.lentil",
    "black_gram": "crops.black_gram", "gram": "crops.gram",
    "horse_gram": "crops.horse_gram", "pigeon_pea": "crops.pigeon_pea",
    "field_pea": "crops.field_pea", "soybean": "crops.soybean",
    "mustard": "crops.mustard", "sesame": "crops.sesame",
    "groundnut": "crops.groundnut", "amaranth": "crops.vegetables.amaranth",
    "mango": "crops.mango", "litchi": "crops.fruits.litchi",
    "guava": "crops.fruits.guava", "apple": "crops.apple",
    "pear": "crops.fruits.pear", "peach": "crops.fruits.peach",
    "plum": "crops.fruits.plum", "apricot": "crops.fruits.apricot",
    "walnut": "crops.fruits.walnut", "citrus": "crops.fruits.mandarin",
    "onion": "crops.onion", "tomato": "crops.tomato",
    "cabbage": "crops.vegetables.cabbage", "cauliflower": "crops.vegetables.cauliflower",
    "brinjal": "crops.vegetables.brinjal", "okra": "crops.vegetables.okra",
    "capsicum": "crops.vegetables.capsicum", "radish": "crops.vegetables.radish",
    "french_bean": "crops.vegetables.beans", "ginger": "crops.ginger",
}

# district id (suffix) -> attributes, all facts read from the CRIDA CP PDF
# keyed by district.json id suffix (district name slug)
PC_ZONE = "Western Himalayan Region (I)"
DATA = {
    "almora": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["rice", "wheat", "barley", "apple", "pear", "peach",
                        "plum", "apricot", "walnut", "mango"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD1-Almora-31.03.2013.pdf",
        "notes": "Major field-crops table partially extractable from PDF; only Rice/Wheat/Barley clearly read.",
    },
    "bageshwar": {
        "narp_zone": "Mid Hills (UK Region II, sub-humid 801-1800 m)",
        "major_crops": ["wheat", "maize", "rice", "barley", "finger_millet",
                        "lentil", "black_gram", "mustard", "apple", "pear",
                        "peach", "plum", "apricot", "walnut", "potato"],
        "primary_soils": ["Loamy-skeletal soil", "Deep loamy soil", "Shallow loamy soil"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD11-Bageshwar-01.08.14.pdf",
    },
    "chamoli": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["wheat", "rice", "finger_millet", "barnyard_millet",
                        "potato", "apple", "pear", "peach", "plum", "apricot",
                        "walnut", "mango"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD4-Chamoli-10.07.14.pdf",
    },
    "champawat": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["wheat", "barnyard_millet", "rice", "finger_millet",
                        "potato", "soybean", "mango", "pear", "plum", "walnut",
                        "apple"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD5-Champawat-10.07.14.pdf",
    },
    "dehradun": {
        "narp_zone": "Zone-1 Hill Zone",
        "major_crops": ["wheat", "rice", "maize", "barnyard_millet",
                        "finger_millet", "barley", "sugarcane", "amaranth",
                        "french_bean", "horse_gram", "black_gram", "lentil",
                        "pigeon_pea", "gram", "soybean", "mustard", "sesame",
                        "groundnut", "apple", "mango", "litchi", "guava"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD7-Dehradun-10.07.14.pdf",
    },
    "haridwar": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["rice", "wheat", "lentil", "groundnut", "mustard",
                        "mango", "litchi", "potato", "tomato"],
        "primary_soils": ["Sandy calcareous soil", "Banger soil", "Khaddar soil",
                          "Forest soil", "Marshy forest soil"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD2-Haridwar-31.3.2013.pdf",
    },
    "nainital": {
        "narp_zone": "Zone-1 Hill Zone",
        "major_crops": ["wheat", "rice", "soybean", "maize", "sugarcane",
                        "potato", "barnyard_millet", "barley", "lentil",
                        "mustard", "gram", "mango", "litchi", "peach", "pear"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD8-Nainital-10.07.14.pdf",
    },
    "pauri_garhwal": {
        "narp_zone": "Sub-Temperate to Temperate",
        "major_crops": ["rice", "maize", "finger_millet", "barnyard_millet",
                        "black_gram", "horse_gram", "pigeon_pea", "amaranth",
                        "wheat", "barley", "lentil", "mustard", "apple", "pear",
                        "peach", "plum", "apricot", "walnut"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD12-Pauri%20Garhwal-01.08.14.pdf",
    },
    "pithoragarh": {
        "narp_zone": "Hill Zone (AZ-26)",
        "major_crops": ["wheat", "rice", "finger_millet", "maize", "barley",
                        "barnyard_millet", "apple", "pear", "plum", "walnut",
                        "peach", "apricot", "mango"],
        "primary_soils": ["Alluvial sandy loam soil"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD9-Pithoragarh%2010.07.14.pdf",
    },
    "rudraprayag": {
        "narp_zone": "Mid Hills (AZ-27)",
        "major_crops": ["rice", "finger_millet", "barnyard_millet", "maize",
                        "amaranth", "wheat", "barley", "black_gram", "horse_gram",
                        "pigeon_pea", "mustard", "soybean", "sesame"],
        "primary_soils": ["Brown forest soil", "Residual sandy loam soil"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD10-Rudraprayag-10.07.14.pdf",
    },
    "tehri_garhwal": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["wheat", "barnyard_millet", "finger_millet", "rice",
                        "barley", "maize", "black_gram", "lentil", "mustard",
                        "pigeon_pea", "sesame", "soybean", "gram"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD6-Tehri%20Garhwal-10.07.14.pdf",
    },
    "udham_singh_nagar": {
        "narp_zone": "Hill Zone (UP-1)",
        "major_crops": ["sugarcane", "rice", "wheat", "maize", "mango",
                        "litchi", "guava", "okra", "potato", "cauliflower",
                        "onion", "cabbage"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD3-Udham%20Singh%20Nagar-31.03.2013.pdf",
        "notes": "PDF contains a partially corrupt page; crops read from extractable pages.",
    },
    "uttarkashi": {
        "narp_zone": "Hill Zone (AZ)",
        "major_crops": ["rice", "wheat", "finger_millet", "barnyard_millet",
                        "maize", "black_gram", "pigeon_pea", "lentil", "mustard",
                        "apple", "pear", "walnut", "plum", "potato", "tomato"],
        "primary_soils": ["Loamy-skeletal soil", "Deep loamy soil"],
        "url": "https://icar-crida.res.in/CP/Uttarkhand/UKD13-Uttarkashi-01.08.14.pdf",
    },
}

TODO_NOTE = "TODO: district crop attributes from DES APY / CRIDA contingency plan"


def main():
    dist = json.loads(DIST.read_text(encoding="utf-8"))
    states = dist["states"]
    ut_state = next(s for s in states if s["state"] == "Uttarakhand")

    done = 0
    for d in ut_state["districts"]:
        key = d["id"].rsplit(".", 1)[-1]
        spec = DATA.get(key)
        if spec is None:
            raise SystemExit(f"missing data for district {key}")
        attrs = {
            "agro_climatic_zone": PC_ZONE,
            "narp_zone": spec["narp_zone"],
            "major_crops": [C[c] for c in spec["major_crops"]],
            "source": {"id": "crida-cp", "url": spec["url"]},
        }
        if spec.get("primary_soils"):
            attrs["primary_soils"] = spec["primary_soils"]
        d["attributes"] = attrs
        if spec.get("notes"):
            d["notes"] = spec["notes"]
        done += 1

    # mark every district outside Uttarakhand as TODO
    todo = 0
    for s in states:
        if s["state"] == "Uttarakhand":
            continue
        for d in s["districts"]:
            d["notes"] = TODO_NOTE
            todo += 1

    dist["todo_gaps"] = [
        "district-level crop/soil attributes filled for Uttarakhand (13 districts) via "
        "ICAR-CRIDA contingency plans; remaining districts pending DES APY / CRIDA",
        f"TODO districts: {todo}",
    ]
    DIST.write_text(json.dumps(dist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"filled={done} todo={todo}")


if __name__ == "__main__":
    main()
