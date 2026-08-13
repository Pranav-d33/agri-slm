#!/usr/bin/env python3
"""
Build data/locations/districts.json from Census of India 2011 (census2011.co.in mirror).
Districts are enumerated from official census data; post-2011 administrative changes
(district splits) are recorded as TODO gaps, never invented.
"""

import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "locations" / "districts.json"
BASE = "https://www.census2011.co.in"
UA = {"User-Agent": "agri-slm-skeleton/1.0"}

# All 28 states + 8 UTs (current list); census mirror may predate some splits
ALL_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Lakshadweep", "Puducherry",
]  # Telangana and Ladakh are produced by deterministic splits below

# post-2019: J&K split into two UTs; census mirror predates it
UT_SPLITS = {
    "Jammu and Kashmir": ["Jammu and Kashmir", "Ladakh"],
}

# census-2011: Telangana districts enumerated under Andhra Pradesh
TELANGANA_2011 = ["Adilabad", "Hyderabad", "Karimnagar", "Khammam", "Mahbubnagar",
                  "Medak", "Nalgonda", "Nizamabad", "Rangareddy", "Warangal"]


def slug(name):
    return urllib.parse.quote(name.lower().replace(" ", "+"))


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def crawl(state):
    slugs = [slug(state)]
    # census-2011 era names differ for some states/UTs
    ALIASES = {
        "Odisha": ["orissa"],
        "Dadra and Nagar Haveli and Daman and Diu": ["dadra+and+nagar+haveli", "daman+and+diu"],
    }
    slugs = ALIASES.get(state, slugs)
    by_id = {}
    for s in slugs:
        try:
            page = fetch(f"{BASE}/census/state/districtlist/{s}.html")
        except Exception:
            continue
        # each district appears once per name variant (short and qualified); take shortest name per id
        for did, name in re.findall(r"district/(\d+)-([a-z0-9-]+)\.html", page or ""):
            prev = by_id.get(did)
            if prev is None or len(name) < len(prev):
                by_id[did] = name
    return [n.replace("-", " ").title() for n in sorted(set(by_id.values()))]


def main():
    states = []
    for state in ALL_STATES:
        try:
            districts = crawl(state)
        except Exception as e:
            print(f"  FAIL {state}: {e}")
            states.append({"state": state, "census_district_count": 0,
                           "districts": [], "fetch_error": str(e)})
            continue
        # post-2019 split: Leh + Kargil -> Ladakh UT
        if state == "Jammu and Kashmir" and districts:
            ladakh = [d for d in districts if d in ("Leh", "Kargil")]
            jk = [d for d in districts if d not in ("Leh", "Kargil")]
            states.append({"state": "Ladakh", "census_district_count": len(ladakh), "districts": ladakh})
            states.append({"state": "Jammu and Kashmir", "census_district_count": len(jk), "districts": jk})
            print(f"  {state}: split -> JK {len(jk)} + Ladakh {len(ladakh)}")
        # census-2011: Andhra Pradesh page enumerates Telangana districts under AP
        elif state == "Andhra Pradesh" and districts:
            telangana = [d for d in districts if d in TELANGANA_2011]
            ap = [d for d in districts if d not in TELANGANA_2011]
            states.append({"state": "Andhra Pradesh", "census_district_count": len(ap), "districts": ap})
            states.append({"state": "Telangana", "census_district_count": len(telangana), "districts": telangana})
            print(f"  {state}: split -> AP {len(ap)} + Telangana {len(telangana)}")
        else:
            states.append({"state": state, "census_district_count": len(districts), "districts": districts})
            print(f"  {state}: {len(districts)} districts")
        time.sleep(1)

    data = {
        "metadata": {
            "source": "Census of India 2011 via census2011.co.in mirror",
            "source_url": f"{BASE}/district.php",
            "admin_geography": "Census 2011 district boundaries; J&K/Ladakh split per 2019 Reorganisation Act",
            "note": "Post-2011 district splits are tracked as TODO gaps; not invented.",
        },
        "states": states,
        "todo_gaps": [
            "District splits post-2011 (e.g. new districts in Telangana, UP, MP, etc.) "
            "to be reconciled against LGD master list (lgdirectory.gov.in)",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    total = sum(len(s["districts"]) for s in states)
    print(f"\n{len(states)} states/UTs, {total} districts -> {OUT}")


if __name__ == "__main__":
    main()
