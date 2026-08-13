#!/usr/bin/env python3
"""
Fetch deterministic sources into data/_raw/<source_id>/.
Writes data/_raw/fetch_report.json with per-source status.
Source ids are defined in sources.md at the repo root of the skeleton.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "_raw"
REPORT = RAW / "fetch_report.json"
UA = {"User-Agent": "agri-slm-skeleton/1.0"}

SOURCES = {
    "census2011": {
        "index": "https://www.census2011.co.in/district.php",
        "desc": "State and district lists (Census of India 2011 mirror)",
    },
    "tnau-agritech": {
        "pages": [
            "https://agritech.tnau.ac.in/agriculture/agri_cropproduction_cereals%20index%20new_rice.html",
            "https://agritech.tnau.ac.in/agriculture/millets_index.html",
            "https://agritech.tnau.ac.in/agriculture/pulses_index.html",
            "https://agritech.tnau.ac.in/agriculture/oilseeds_index.html",
            "https://agritech.tnau.ac.in/agriculture/fibrecrops_index.html",
            "https://agritech.tnau.ac.in/agriculture/sugarcrops_index.html",
            "https://agritech.tnau.ac.in/agriculture/agri_cropproduction_forage%20index%20new_forage.html",
            "https://agritech.tnau.ac.in/agriculture/othercrops.html",
            "https://agritech.tnau.ac.in/crop_protection/crop_prot.html",
            "https://agritech.tnau.ac.in/agriculture/agri_nutrientmgt.html",
            "https://agritech.tnau.ac.in/agriculture/agri_soil.html",
        ],
        "desc": "TNAU Agritech Portal index pages",
    },
}


def fetch(url, retries=3, timeout=45):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"{type(e).__name__}: {e}")


def safe_name(url):
    return re.sub(r"[^a-z0-9]+", "_", urllib.parse.urlparse(url).path.lower()).strip("_") + ".html"


def main():
    RAW.mkdir(exist_ok=True)
    report = {}
    for sid, cfg in SOURCES.items():
        outdir = RAW / sid
        outdir.mkdir(exist_ok=True)
        urls = cfg.get("pages", [cfg.get("index")])
        report[sid] = {"desc": cfg["desc"], "files": [], "status": "ok"}
        for url in urls:
            name = safe_name(url) if "pages" in cfg else "index.html"
            dest = outdir / name
            try:
                body = fetch(url)
                dest.write_text(body, encoding="utf-8")
                report[sid]["files"].append(str(dest.relative_to(RAW)))
                print(f"  ok   {url} -> {name} ({len(body)} bytes)")
            except Exception as e:
                report[sid]["status"] = "failed"
                report[sid].setdefault("errors", []).append(f"{url}: {e}")
                print(f"  FAIL {url}: {e}")
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    ok = sum(1 for r in report.values() if r["status"] == "ok")
    print(f"\n{ok}/{len(report)} sources ok. Report: {REPORT}")
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    sys.exit(main())
