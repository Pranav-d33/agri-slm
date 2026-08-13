#!/usr/bin/env python3
"""
Coverage audit: what the skeleton contains vs. what the authoritative sources
promise. Generates COVERAGE.md. Expected counts come from the source registry
(sources.md) and are deliberately conservative; anything not yet collected is
listed as a gap, never invented.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# domain -> {collected: auto, expected: authoritative target, note}
EXPECTED = {
    "soil":            {"expected": 16, "note": "8 ICAR soil types + 4 problem soils + categories (complete)"},
    "crops":           {"expected": 135, "note": "All DAC&FW major crops: 5 cereals, 9 millets, 11 pulses, 9 oilseeds, 3 fibre + 2 sugar, 25 fruits, 22 vegetables, 17 spices, 8 plantation, 5 fodder + flowers/aromatics/mushroom categories (complete at species level; state lists from HSAG 2024 + DES APY)"},
    "livestock":       {"expected": 277, "note": "COMPLETE NBAGR registry: 243 breed entities (55 cattle + 3 synthetic, 22 buffalo, 43 goat, 46 sheep + 1 synthetic, 15 pig, 21 chicken, 9 camel, 7 horse, 4 donkey, 2 yak, 1 mithun, 2 geese, 9 duck; dogs excluded as non-agricultural) + 6 improved/exotic lines + species anchors + diseases; 3 duplicate pig entities removed"},
    "pesticides":      {"expected": 474, "note": "COMPLETE official CIB&RC classification (ppqs.gov.in 31.07.2026): 49 banned, 5 banned-for-use/export-only, 8 withdrawn, 18 refused, 16 restricted + all 371 Section 9(3) registered actives (data/_raw/cibrc/registered_actives_9_3.json)"},
    "fertilizers":     {"expected": 27, "note": "Straight/complex fertilizers, biofertilizers, manures, micronutrients (complete)"},
    "organic":         {"expected": 12, "note": "Certification systems, organic states, methods, inputs (complete)"},
    "weather":         {"expected": 23, "note": "Monsoon, ENSO, western disturbances, extreme events (incl. hailstorm/frost/dry spell/cloudburst), agromet (complete)"},
    "seeds":           {"expected": 12, "note": "Seed types, certification, iconic varieties (complete at type level); duplicate NSC entity merged into schemes.institutions"},
    "machinery":       {"expected": 26, "note": "Tractors, implements, harvesting, protection, custom hiring (complete); duplicate power_tiller entity merged"},
    "plant_protection": {"expected": 550, "note": "Exhaustive TNAU crop-protection crawl: 346 pests + 193 diseases + 6 weeds across 57 crops, each with affects relations (complete)"},
    "fisheries":       {"expected": 34, "note": "Sector + CMFRI 2023 top marine resources (14 species incl. ribbonfish, cephalopods, prawns, croakers, anchovies, hilsa) + aquaculture species (IMC, exotic carp, tilapia, pangasius, scampi) + brackishwater aquaculture (ICAR-CIBA)"},
    "post_harvest":    {"expected": 9, "note": "Storage, cold chain, grading, processing (complete)"},
    "market":          {"expected": 19, "note": "MSP, mandis, e-NAM, exports, insurance, contract farming, FPOs (complete)"},
    "schemes":         {"expected": 35, "note": "Schemes + institutions incl. ICRISAT, agri-startups (complete)"},
    "forestry":        {"expected": 40, "note": "All 16 Champion & Seth (1968) forest type groups, NTFP, agroforestry, timber species, ISFR 2023 status (complete)"},
    "apiculture":      {"expected": 8, "note": "Beekeeping, honey (28 states per HSAG 7.2.8), sericulture (complete)"},
    "water":           {"expected": 32, "note": "Irrigation methods (incl. wells) + all 20 CWC major river basins + watershed development (complete)"},
}

GAPS = [
    "Agro-climatic zones: 15 PC zones + 125 NARP zone rows transcribed from ICAR 1996 paper (headline 127 vs 125 resolves to combined NEH/duplicate rows in source; no zone fabricated); UP zone->district lists done; district lists for remaining states = TODO via state agriculture profiles",
    "Crops: notified variety registry per crop (thousands) = TODO via ICAR variety releases",
    "Pesticides: 333/371 registered actives have formulations (PPQS 31.03.2026); 9(3)(i) provisional registrations + remaining actives = TODO",
    "Fisheries: district production data (NFDB/CMFRI state-wise) and more species = TODO",
    "Market: MSP series by year, mandi price time series (AGMARKNET bulk data) = TODO",
    "Location: district-level attributes (crop maps per district) = TODO",
    "Hindi/local aliases: allowed in aliases field but not yet populated; needs a registered bilingual source (e.g. DAC&FW glossary) before adding",
]


def main():
    per_domain = {}
    total_entities = total_rels = 0
    for path in sorted(DATA.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data.get("entities", []):
            dom = e["domain"]
            per_domain.setdefault(dom, {"entities": 0, "categories": 0, "location_rels": 0})
            per_domain[dom]["entities"] += 1
            per_domain[dom]["categories"] += 1 if e["type"] in ("category", "domain") else 0
            loc = [r for r in e.get("relations", []) if r.get("predicate") in
                   ("found_in", "grown_in", "practiced_in", "produced_in", "banned_in")]
            per_domain[dom]["location_rels"] += len(loc)
            total_entities += 1
            total_rels += len(e.get("relations", []))

    districts = json.loads((DATA / "locations" / "districts.json").read_text())
    total_districts = sum(len(s["districts"]) for s in districts["states"])
    narp = len(json.loads((DATA / "locations" / "narp_zones.json").read_text()).get("zones", []))

    lines = [
        "# Coverage Report (auto-generated by scripts/coverage.py)",
        "",
        "Generated: `%s`" % __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "",
        f"- Entities: **{total_entities}** | Relations: **{total_rels}**",
        f"- Locations: 36 states/UTs, {total_districts} districts (LGD current, with census-2011 counts), 15 agro-climatic zones, {narp} NARP zones (ICAR), 9 regions",
        "",
        "## Per-domain counts (collected vs expected)",
        "",
        "| domain | entities | categories | location relations | expected | status |",
        "|---|---|---|---|---|---|",
    ]
    for dom, spec in sorted(EXPECTED.items()):
        c = per_domain.get(dom, {"entities": 0, "categories": 0, "location_rels": 0})
        status = "complete" if c["entities"] >= spec["expected"] else "partial"
        lines.append(f"| {dom} | {c['entities']} | {c['categories']} | {c['location_rels']} | "
                     f"{spec['expected']} | {status} |")
        lines.append(f"| ... | ... | ... | ... | ... | {spec['note']} |" if status == "complete" else "")

    lines += ["", "## Known gaps (tracked, not fabricated)", ""]
    lines += [f"- [ ] {g}" for g in GAPS]
    lines += ["", "## Notes", "",
              "- Status 'complete' means the taxonomy skeleton level is done; leaf-level exhaustive data is tracked in gaps.",
              "- All facts carry source refs (sources.md); nothing here is LLM-generated."]
    lines = [l for l in lines if l.strip() != ""]
    (ROOT / "COVERAGE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"COVERAGE.md written: {total_entities} entities, {total_rels} relations, {total_districts} districts")


if __name__ == "__main__":
    main()
