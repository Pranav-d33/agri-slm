#!/usr/bin/env python3
"""Fetch a current mandi price + arrival + MSP snapshot from the live AGMARKNET
2.0 public API (https://api.agmarknet.gov.in/v1/dashboard-data/).

Writes the snapshot to market.prices.attributes.mandi_price_snapshot:
  {
    date: <reported_date>,
    source: {id: agmarknet-api, url: <api>},
    crops: {
      "<commodity>": {msp_price, price, arrival, unit:"Rs/quintal", trend}
    }
  }
National (all-states/UTs) aggregate per commodity. Only crops returned by the
API are recorded; the 2 pseudo-rows (All Commodities/Groups) are skipped.
"""

import json
import time
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parent.parent
MARKET = ROOT / "data" / "market.json"
API = "https://api.agmarknet.gov.in/v1/dashboard-data/"
FILTERS = "https://api.agmarknet.gov.in/v1/dashboard-filters/?dashboard_name=marketwise_price_arrival"
DATE = "2026-08-14"
SRC = {"id": "agmarknet-api", "url": API}


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "agri-slm-skeleton/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    # pull commodity ids from the public filters
    flt = post(FILTERS, {}) if False else json.loads(
        urllib.request.urlopen(urllib.request.Request(FILTERS, headers={"User-Agent": "agri-slm-skeleton/1.0"}), timeout=30).read()
    )
    crops = [c for c in flt["data"]["cmdt_data"] if c["cmdt_id"] not in (100000, 100001)]

    snapshot = {"date": None, "source": SRC, "crops": {}}
    for c in crops:
        cid = c["cmdt_id"]
        payload = {
            "dashboard": "marketwise_price_arrival", "date": DATE,
            "group": [100000], "commodity": [cid], "variety": 100021,
            "state": 100006, "district": [100007], "market": [100009],
            "grades": [4], "limit": 1, "format": "json",
        }
        try:
            resp = post(API, payload)
        except Exception as e:
            print(f"  ERR {c['cmdt_name']}: {e}")
            time.sleep(1)
            continue
        data = resp.get("data") if isinstance(resp, dict) else None
        recs = data.get("records", []) if isinstance(data, dict) else []
        if not recs:
            continue
        r = recs[0]
        snapshot["crops"][c["cmdt_name"]] = {
            "price": r.get("as_on_price"),
            "arrival": r.get("as_on_arrival"),
            "msp_price": r.get("msp_price"),
            "trend": r.get("trend"),
        }
        snapshot["date"] = r.get("reported_date")
        time.sleep(0.4)

    data = json.loads(MARKET.read_text(encoding="utf-8"))
    for e in data["entities"]:
        if e["id"] == "market.prices":
            e.setdefault("attributes", {})["mandi_price_snapshot"] = snapshot
    MARKET.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    n = len(snapshot["crops"])
    print(f"wrote mandi price snapshot: {n} crops, date={snapshot['date']}")


if __name__ == "__main__":
    main()
