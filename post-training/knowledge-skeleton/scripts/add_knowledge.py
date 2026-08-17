#!/usr/bin/env python3
"""Add finance sub-domain + deepen post_harvest.processing + refinements.

Edits data/*.json directly. Sources added to sources.md first.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "sources.md"

DACFW = {"id": "dacfw", "url": "https://agricoop.nic.in/"}
NABARD = {"id": "nabard", "url": "https://www.nabard.org/"}
RBI = {"id": "rbi", "url": "https://www.rbi.org.in/"}
MOFPI = {"id": "mofpi", "url": "https://www.mofpi.gov.in/"}
MOEFGEAC = {"id": "moef-geac", "url": "http://geacindia.gov.in/"}
DBT = {"id": "dbt", "url": "https://dbtindia.gov.in/"}
CSB = {"id": "csb", "url": "https://csb.gov.in/"}
DAHDC = {"id": "dahd-census", "url": "https://dahd.nic.in/"}
NHB = {"id": "nhb", "url": "https://nhb.gov.in/"}
PIB = {"id": "pib", "url": "https://pib.gov.in/"}

INDIA = "location.india"

# ---- register new sources ----
NEW_SOURCES = [
    ("nabard", "NABARD", "finance", "https://www.nabard.org/", "Govt of India; rural credit, refinance", "ready"),
    ("rbi", "RBI", "finance", "https://www.rbi.org.in/", "Govt of India; Priority Sector Lending norms", "ready"),
    ("moef-geac", "MoEF&CC GEAC (GM crops)", "seeds", "http://geacindia.gov.in/", "Govt of India; genetic engineering approval committee", "ready"),
    ("dbt", "DBT (Biotechnology, genome editing)", "seeds", "https://dbtindia.gov.in/", "Govt of India; SDN-1/SDN-2 guidelines", "ready"),
    ("csb", "Central Silk Board", "apiculture", "https://csb.gov.in/", "Govt of India; sericulture statistics", "ready"),
]
src_text = SRC.read_text(encoding="utf-8")
existing = set(re.findall(r"^\| (\w[\w-]*) \|", src_text, re.M))
added_sources = []
for row in NEW_SOURCES:
    if row[0] in existing:
        continue
    # insert before the "## Section 9(3)(i)" marker (a non-table line) is messy;
    # instead append right after the sebi row (last table row).
    sebi_row = "| sebi | SEBI (commodity futures regulator) | market | https://www.sebi.gov.in/ | Govt of India; FCRA 1952 | manual |\n"
    if sebi_row in src_text:
        src_text = src_text.replace(sebi_row, sebi_row + f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |\n")
    else:
        src_text = src_text + f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |\n"
    added_sources.append(row[0])
SRC.write_text(src_text, encoding="utf-8")
print("registered sources:", added_sources or "(none new)")

# ---- helpers ----
def ent(eid, name, dtype, domain, relations, source, attributes=None, aliases=None):
    e = {"id": eid, "name": name, "type": dtype, "domain": domain}
    if aliases:
        e["aliases"] = aliases
    if attributes:
        e["attributes"] = attributes
    e["relations"] = relations
    e["source"] = source
    return e


def rel(pred, obj, src=None):
    r = {"predicate": pred, "object": obj}
    if src:
        r["source"] = src
    return r


# ---- TASK 1: finance.json ----
finance_entities = [
    ent("finance", "Agricultural Finance", "domain", "finance",
        [rel("part_of", "agriculture"), rel("found_in", INDIA)], DACFW,
        attributes={"note": "Credit, refinance, subvention and allied financial support for agriculture"}),
    ent("finance.institutional_credit", "Institutional Credit", "category", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)], DACFW),
    ent("finance.cooperative_credit", "Cooperative Credit", "category", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)], NABARD),
    ent("finance.refinance", "Refinance", "category", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)], NABARD),
    ent("finance.subvention", "Interest Subvention", "category", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)], DACFW),
    ent("finance.microfinance", "Microfinance", "category", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)], NABARD),
    ent("finance.kcc", "Kisan Credit Card", "entity", "finance",
        [rel("is_a", "finance.institutional_credit"),
         rel("regulated_by", "institutions.nabard"),
         rel("found_in", INDIA)],
        DACFW,
        attributes={
            "launched": "1998",
            "note": "Short-term crop loans up to Rs 3 lakh at 4% effective interest after subvention; covers crop, animal husbandry and fisheries",
        }),
    ent("finance.interest_subvention", "Interest Subvention Scheme", "entity", "finance",
        [rel("is_a", "finance.subvention"), rel("found_in", INDIA)],
        DACFW,
        attributes={
            "note": "1.5% subvention to banks, farmer pays 7% on crop loans up to Rs 3 lakh; extra 3% prompt-repayment incentive brings effective rate to 4%",
        }),
    ent("finance.moratorium", "Interest Waiver and Moratorium", "entity", "finance",
        [rel("is_a", "finance.subvention"), rel("found_in", INDIA)],
        DACFW,
        attributes={"note": "Interest waiver/relief measures announced in distress years"}),
    ent("finance.refinance.nabard", "NABARD Refinance", "entity", "finance",
        [rel("is_a", "finance.refinance"), rel("found_in", INDIA)],
        NABARD,
        attributes={"note": "NABARD refinances cooperative banks, RRBs and commercial banks for agricultural credit"}),
    ent("finance.cooperative_banks", "Cooperative Banks", "entity", "finance",
        [rel("is_a", "finance.cooperative_credit"), rel("found_in", INDIA)],
        NABARD,
        attributes={"note": "3-tier cooperative credit structure: SCB -> DCCB -> PACS"}),
    ent("finance.rrb", "Regional Rural Banks", "entity", "finance",
        [rel("is_a", "finance.cooperative_credit"), rel("found_in", INDIA)],
        NABARD,
        attributes={"note": "~43 Regional Rural Banks (RRBs)"}),
    ent("finance.psl", "Priority Sector Lending", "entity", "finance",
        [rel("is_a", "finance.institutional_credit"), rel("found_in", INDIA)],
        RBI,
        attributes={"note": "18% of Adjusted Net Bank Credit to agriculture (10% to small/marginal farmers); total PSL target 40%"}),
    ent("finance.micro_irrigation_fund", "Micro Irrigation Fund", "entity", "finance",
        [rel("is_a", "finance"), rel("part_of", "water.schemes.pmksy"), rel("found_in", INDIA)],
        NABARD,
        attributes={"note": "NABARD Micro Irrigation Fund (MIF) of Rs 5,000 cr; cross-linked to PMKSY"}),
    ent("finance.agri_infra_fund", "Agriculture Infrastructure Fund", "entity", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)],
        DACFW,
        attributes={"note": "AIF Rs 1 lakh cr (2020-29), 3% interest subvention; for post-harvest infrastructure assets"}),
    ent("finance.kcc_animal_husbandry", "KCC for Animal Husbandry & Fisheries", "entity", "finance",
        [rel("is_a", "finance.kcc"), rel("found_in", INDIA)],
        DAHDC,
        attributes={"note": "KCC extended to animal husbandry and fisheries (2018-19)"}),
    ent("finance.credit_target", "Annual Agricultural Credit Target", "entity", "finance",
        [rel("is_a", "finance"), rel("found_in", INDIA)],
        DACFW,
        attributes={"note": "Agricultural credit target ~Rs 25 lakh cr (2024-25 Budget Estimate)"}),
]
# finance.pm_kisan cross-ref only via relation part_of schemes.pm_kisan (no entity)
finance_entities[0]["relations"].append(rel("part_of", "schemes.pm_kisan"))

json.dump({"_description": "Agricultural finance domain: institutional/cooperative credit, refinance, interest subvention and microfinance.",
           "source": DACFW,
           "entities": finance_entities},
          open(DATA / "finance.json", "w"), indent=1, ensure_ascii=False)
print("finance.json: entities =", len(finance_entities))

# ---- TASK 2: post_harvest.processing ----
ph = json.load(open(DATA / "post_harvest.json"))
ph_ids = {e["id"] for e in ph["entities"]}
new_ph = [
    ent("post_harvest.processing.sampada", "PM Kisan SAMPADA", "measure", "post_harvest",
        [rel("is_a", "post_harvest.processing"), rel("found_in", INDIA)],
        MOFPI,
        attributes={"note": "PM Kisan SAMPADA (2016), Rs 6,000 cr; end-to-end food processing infrastructure"}),
    ent("post_harvest.processing.food_processing_share", "Food Processing Share", "entity", "post_harvest",
        [rel("is_a", "post_harvest.processing"), rel("found_in", INDIA)],
        MOFPI,
        attributes={"note": "Less than 10% of perishables processed; food processing sector among the largest (~4th), GVA ~Rs 2 lakh cr"}),
    ent("post_harvest.processing.packhouse", "Packhouse / Pre-cooling", "entity", "post_harvest",
        [rel("is_a", "post_harvest.processing"), rel("found_in", INDIA)],
        MOFPI,
        attributes={"note": "Packhouses and pre-cooling units for horticulture export and supply chain"}),
    ent("post_harvest.processing.value_addition", "Value Addition in Food Processing", "entity", "post_harvest",
        [rel("is_a", "post_harvest.processing"), rel("found_in", INDIA)],
        MOFPI,
        attributes={"note": "Value addition in food processing ~6.76%"}),
    ent("post_harvest.processing.concentrations", "Food Processing Concentrations", "entity", "post_harvest",
        [rel("is_a", "post_harvest.processing"),
         rel("found_in", "location.states.uttar_pradesh"),
         rel("found_in", "location.states.punjab"),
         rel("found_in", "location.states.maharashtra"),
         rel("found_in", "location.states.west_bengal")],
        MOFPI,
        attributes={"note": "Leading food processing states: UP, Punjab, Maharashtra, West Bengal"}),
]
added = 0
for e in new_ph:
    if e["id"] in ph_ids:
        continue
    ph["entities"].append(e)
    ph_ids.add(e["id"])
    added += 1
json.dump(ph, open(DATA / "post_harvest.json", "w"), indent=1, ensure_ascii=False)
print("post_harvest.json: added", added)

# ---- TASK 3a: seeds.biotech ----
sd = json.load(open(DATA / "seeds.json"))
sd_ids = {e["id"] for e in sd["entities"]}

def add_sd(e):
    global added_sd
    if e["id"] in sd_ids:
        return
    sd["entities"].append(e)
    sd_ids.add(e["id"])
    added_sd += 1

added_sd = 0
add_sd(ent("seeds.biotech", "Biotech / GM Seeds", "category", "seeds",
           [rel("is_a", "seeds"), rel("found_in", INDIA)], MOEFGEAC,
           attributes={"note": "Genetically modified and genome-edited planting material; approvals by GEAC/MoEF&CC"}))
add_sd(ent("seeds.biotech.bt_brinjal", "Bt Brinjal", "entity", "seeds",
           [rel("is_a", "seeds.biotech"), rel("found_in", INDIA)], MOEFGEAC,
           attributes={"note": "GEAC approved 2009; indefinite moratorium on commercial release Feb 2010"}))
add_sd(ent("seeds.biotech.gm_mustard", "GM Mustard (DMH-11)", "entity", "seeds",
           [rel("is_a", "seeds.biotech"), rel("found_in", INDIA)],
           {"id": "moef-geac", "url": "http://geacindia.gov.in/"},
           attributes={"note": "DMH-11 (Barnase/Barstar) hybrid; GEAC recommended environmental release Oct 2022; MoEF&CC approved seed production May 2023 (not commercial)"}))
add_sd(ent("seeds.biotech.gene_editing", "Genome Editing (SDN-1/SDN-2)", "entity", "seeds",
           [rel("is_a", "seeds.biotech"), rel("found_in", INDIA)], DBT,
           attributes={"note": "SDN-1/SDN-2 genome-edited organism guidelines (DBT 2022); SDN-1 exempt from GM regulation"}))
add_sd(ent("seeds.nursery", "Nurseries and Planting Material", "entity", "seeds",
           [rel("is_a", "seeds"), rel("found_in", INDIA)], NHB,
           attributes={"note": "Planting material, nurseries, tissue culture; supported under MIDH"}))

# move bt_cotton under seeds.biotech (was seeds.types)
for e in sd["entities"]:
    if e["id"] == "seeds.bt_cotton":
        for r in e["relations"]:
            if r.get("predicate") == "is_a":
                r["object"] = "seeds.biotech"
json.dump(sd, open(DATA / "seeds.json", "w"), indent=1, ensure_ascii=False)
print("seeds.json: added", added_sd, "bt_cotton moved ->", [e for e in sd["entities"] if e["id"] == "seeds.bt_cotton"][0]["relations"][0]["object"])

# ---- TASK 3b: livestock.dairy ----
lv = json.load(open(DATA / "livestock.json"))
lv_ids = {e["id"] for e in lv["entities"]}
new_lv = [
    ent("livestock.dairy.value_of_output", "Dairy Value of Output", "entity", "livestock",
        [rel("is_a", "livestock.dairy"), rel("found_in", INDIA)], DAHDC,
        attributes={"note": "Dairy is India's largest agricultural commodity (~Rs 11.2 lakh cr), ~5% of GDP, ~30% of agri GVA"}),
    ent("livestock.dairy.per_capita_availability", "Milk Availability Per Capita", "entity", "livestock",
        [rel("is_a", "livestock.dairy"), rel("found_in", INDIA)], DAHDC,
        attributes={"note": "Per capita milk availability ~459 g/day (2022-23)"}),
]
n = 0
for e in new_lv:
    if e["id"] in lv_ids:
        continue
    lv["entities"].append(e)
    lv_ids.add(e["id"])
    n += 1
json.dump(lv, open(DATA / "livestock.json", "w"), indent=1, ensure_ascii=False)
print("livestock.json: added", n)

# ---- TASK 3c: apiculture.sericulture ----
ap = json.load(open(DATA / "apiculture.json"))
ap_ids = {e["id"] for e in ap["entities"]}
new_ap = [
    ent("apiculture.sericulture.mulberry", "Mulberry Silk", "entity", "apiculture",
        [rel("is_a", "apiculture.sericulture"), rel("produced_in", "location.states.karnataka")], CSB,
        attributes={"note": "Karnataka is the top mulberry silk producer (~74% of mulberry silk)"}),
    ent("apiculture.sericulture.tasar", "Tasar Silk", "entity", "apiculture",
        [rel("is_a", "apiculture.sericulture"),
         rel("produced_in", "location.states.jharkhand"),
         rel("produced_in", "location.states.chhattisgarh"),
         rel("produced_in", "location.states.karnataka")], CSB,
        attributes={"note": "Tasar silk concentrated in Jharkhand, Chhattisgarh, Mysore region"}),
    ent("apiculture.sericulture.muga", "Muga Silk", "entity", "apiculture",
        [rel("is_a", "apiculture.sericulture"), rel("produced_in", "location.states.assam")], CSB,
        attributes={"note": "Assam muga silk is a GI product"}),
    ent("apiculture.sericulture.eri", "Eri Silk", "entity", "apiculture",
        [rel("is_a", "apiculture.sericulture"), rel("produced_in", "location.states.assam"),
         rel("produced_in", "location.states.meghalaya")], CSB,
        attributes={"note": "Eri silk concentrated in North-Eastern India"}),
    ent("apiculture.sericulture.rank", "Silk Production Rank", "entity", "apiculture",
        [rel("is_a", "apiculture.sericulture"), rel("produced_in", INDIA)], CSB,
        attributes={"note": "India is the 2nd largest silk producer after China"}),
]
n = 0
for e in new_ap:
    if e["id"] in ap_ids:
        continue
    ap["entities"].append(e)
    ap_ids.add(e["id"])
    n += 1
json.dump(ap, open(DATA / "apiculture.json", "w"), indent=1, ensure_ascii=False)
print("apiculture.json: added", n)

# ---- TASK 3d: forestry.agroforestry_policy ----
fo = json.load(open(DATA / "forestry.json"))
if not any(e["id"] == "forestry.agroforestry_policy" for e in fo["entities"]):
    fo["entities"].append(
        ent("forestry.agroforestry_policy", "National Agroforestry Policy 2014", "measure", "forestry",
            [rel("is_a", "forestry.agroforestry"), rel("found_in", INDIA)], DACFW,
            attributes={"note": "National Agroforestry Policy 2014 (first in the world); Sub-Mission on Agroforestry (SMAF)"}))
    print("forestry.json: added forestry.agroforestry_policy")
json.dump(fo, open(DATA / "forestry.json", "w"), indent=1, ensure_ascii=False)

print("DONE")
