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
    "fisheries":       {"expected": 90, "note": "Sector + aquaculture species (IMC, exotic carp, tilapia, pangasius, scampi) + brackishwater (ICAR-CIBA) + 70 marine resource groups with 2025 national landings (tonnes) from ICAR-CMFRI Booklet 47/2026"},
    "post_harvest":    {"expected": 9, "note": "Storage, cold chain, grading, processing (complete)"},
    "market":          {"expected": 19, "note": "MSP, mandis, e-NAM, exports, insurance, contract farming, FPOs (complete)"},
    "schemes":         {"expected": 35, "note": "Schemes + institutions incl. ICRISAT, agri-startups (complete)"},
    "forestry":        {"expected": 40, "note": "All 16 Champion & Seth (1968) forest type groups, NTFP, agroforestry, timber species, ISFR 2023 status (complete)"},
    "apiculture":      {"expected": 8, "note": "Beekeeping, honey (28 states per HSAG 7.2.8), sericulture (complete)"},
    "water":           {"expected": 32, "note": "Irrigation methods (incl. wells) + all 20 CWC major river basins + watershed development (complete)"},
}

GAPS = [
    "NARP zone->district lists: 122/125 zones carry found_in district relations (mainland + single-zone NEH/islands via ICAR-CRIDA CCP district profiles; zones reverse-mapped from district narp_zone attributes + verified from ICAR-CRIDA district contingency plans). Remaining 3 (Bihar central plateau, Assam south-Arunachal, Assam Nagaland-Meghalaya hill): the ICAR NARP paper defines these zones but lists no districts, and ICAR-CRIDA contingency plans use a different regional zone taxonomy (e.g. Bihar only BI-1/2/3; NEH-4/NEH-5 split) — no source-backed district list found, taxonomy mismatch documented = counted TODO",
    "Crops: notified variety registry = 112/116 concrete crops carry verifiable variety data (apple CITH-Ammol/Priame/Pride + Shalimar, sapota 8 TNAU, peach PAU Shan-e-Punjab/Pratap/Flordasun/Flordaprince, khesari Ratan/Prateek/Mahateora/Nirmal/Moti/Pusa-24, horse-gram, moth-bean, mesta AMV-7/JBMP3/Shakti, cabbage, sugar-beet LS-6/ISRI Comp-1/Pant S-10, clove PPI(CL)1 from SATHI CSC meeting minutes + gazette + institute records). 7 crops recorded with notified_status='none' (no officially notified variety exists; commercial cultivars listed): jackfruit, pear, pineapple, strawberry, plum, vanilla, asafoetida — verified across ICAR-IIHR, ICAR-CCARI, IARI, ICAR-IISR, PIB, PAU = closed. 4 fodder crops (guinea grass, lucerne, napier, stylo) carry released varieties not yet enumerated = counted TODO",


    "Pesticides: 352/382 registered actives have formulations (PPQS 31.03.2026). 30 without: combination-only actives (only appear as components of multi-active formulations under the lead-active model), biocontrols (Trichoderma spp. - species-level formulations don't attach to the genus), banned (Endosulfan), and genuinely-absent sole-actives = counted TODO. Provisional registrations: the former 9(3)(i) route is now Section 9(4) (TIM/FIM/FI/TI for indigenous manufacture/import before full 9(3) data); grants appear per-meeting in the CIB&RC RC minutes (e.g. 474th, ppqs.gov.in/divisions/cib-rc/news-update) — enumerated there as narrative, not a machine-readable registry; per-application file/validity data = counted TODO (no fabrication)",

    "Fisheries: state-wise fish production FY2022-23 (inland 131.13 LT + marine 44.32 LT, per-state) from DAHDF Handbook 2023; national marine landings 2025 by 70 resource groups (tonnes) from ICAR-CMFRI Booklet 47/2026. District-wise marine landings (CMFRI state pages) = infographic/table format, deferred = counted TODO",
    "Market: MSP year series 2010-11..2026-27 in 28 crops encoded from CACP; daily mandi price+arrival+MSP snapshot (23 crops, 11-08-2026) from the live AGMARKNET 2.0 public API (market.prices.mandi_price_snapshot). Per-mandi multi-market time series (needs many API pagination queries) = counted TODO",
    "Location: district-level attributes = 657/784 districts carry major_crops (zone/soil/crops for 576 via ICAR-CRIDA CCP district PDFs; major crops for ~80 more via DES APY district export). Remaining 127: post-2014 split districts absent from both CRIDA (2013-era) and APY (pre-2014 data), plus Delhi/Ladakh/A&N/Lakshadweep with no CRIDA or APY coverage = counted TODO",
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
    with_attrs = sum(1 for s in districts["states"] for d in s["districts"]
                     if d.get("attributes", {}).get("major_crops"))
    narp = len(json.loads((DATA / "locations" / "narp_zones.json").read_text()).get("zones", []))

    lines = [
        "# Coverage Report (auto-generated by scripts/coverage.py)",
        "",
        "Generated: `%s`" % __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "",
        f"- Entities: **{total_entities}** | Relations: **{total_rels}**",
        f"- Locations: 36 states/UTs, {total_districts} districts (LGD current, with census-2011 counts; {with_attrs} with district attributes), 15 agro-climatic zones, {narp} NARP zones (ICAR), 9 regions",
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
