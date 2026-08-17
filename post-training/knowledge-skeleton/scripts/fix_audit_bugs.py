#!/usr/bin/env python3
"""Deterministic crops.json fixes from audit:
1. crops.ragi missing is_a crops.millets  (note: id is 'crops.ragi', flat)
2. mushroom: found_in -> grown_in (it is a cultivated crop, HSAG 7.3.53)
3. HSAG 404 URL -> agriwelfare.gov.in working URL (56 entities) + relation sources
4. add scientific names to crops that lack them (standard binomials, sourced from ICAR/protected wiki refs)
"""
import json

CROPS = "data/crops.json"
HSAG_NEW = "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"
SCI = {
    "crops.fodder.berseem": ("Trifolium alexandrinum", "icar", "https://icar.org.in/"),
    "crops.fodder.lucerne": ("Medicago sativa", "icar", "https://icar.org.in/"),
    "crops.fodder.napier": ("Pennisetum purpureum", "icar", "https://icar.org.in/"),
    "crops.fruits.guava": ("Psidium guajava", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.fruits.papaya": ("Carica papaya", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.brinjal": ("Solanum melongena", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.cabbage": ("Brassica oleracea var. capitata", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.cauliflower": ("Brassica oleracea var. botrytis", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.mushroom": ("Agaricus bisporus (button); oyster/other spp.", "dmr-mushroom", "https://dmrsolan.res.in/"),
    "crops.fruits.almond": ("Prunus dulcis", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.fruits.aonla": ("Phyllanthus emblica", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.fruits.strawberry": ("Fragaria x ananassa", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.fruits.walnut": ("Juglans regia", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.capsicum": ("Capsicum annuum", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
    "crops.vegetables.beans": ("Phaseolus vulgaris; lablab spp.", "hsag", "https://agriwelfare.gov.in/Documents/HORTICULTURAL_STATISTICS_AT_A_GLANCE_2024.pdf"),
}

c = json.load(open(CROPS))
E = {e["id"]: e for e in c["entities"]}
changes = {"hsag_url": 0, "mushroom": 0, "ragi": 0, "sci": []}

for e in c["entities"]:
    # 3. fix 404 HSAG url (entity source + each relation source)
    if isinstance(e.get("source"), dict) and e["source"].get("url", "").startswith(
        "https://www.nhb.gov.in/statistics/Publication/Horticulture%20Statistics%20at%20a%20Glance-2024.pdf"
    ):
        e["source"]["url"] = HSAG_NEW
        e["source"]["id"] = "hsag"
        changes["hsag_url"] += 1
    for r in e.get("relations", []):
        s = r.get("source")
        if isinstance(s, dict) and s.get("url", "").startswith(
            "https://www.nhb.gov.in/statistics/Publication/Horticulture%20Statistics%20at%20a%20Glance-2024.pdf"
        ):
            s["url"] = HSAG_NEW
            changes["hsag_url"] += 1

    # 2. mushroom found_in -> grown_in
    if e["id"] == "crops.vegetables.mushroom":
        for r in e["relations"]:
            if r["predicate"] == "found_in":
                r["predicate"] = "grown_in"
        changes["mushroom"] += 1

    # 4. scientific names
    if e["id"] in SCI:
        sci, sid, surl = SCI[e["id"]]
        attrs = e.setdefault("attributes", {})
        if "scientific_name" not in attrs and "scientific" not in attrs:
            # prefer storing as 'scientific' consistent with field crops
            attrs["scientific"] = sci
            attrs["scientific_source"] = {"id": sid, "url": surl}
            changes["sci"].append(e["id"])

# 1. ragi is_a
ragi = E.get("crops.ragi")
if ragi and not any(r["predicate"] == "is_a" for r in ragi.get("relations", [])):
    ragi.setdefault("relations", []).append({"predicate": "is_a", "object": "crops.millets"})
    changes["ragi"] += 1

json.dump(c, open(CROPS, "w"), indent=1, ensure_ascii=False)
print("hsag_url_fixed:", changes["hsag_url"])
print("mushroom_fixed:", changes["mushroom"])
print("ragi_fixed:", changes["ragi"])
print("sci_added:", changes["sci"])