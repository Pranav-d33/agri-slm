#!/usr/bin/env python3
"""Build <cache>/fulldump.json from downloaded CRIDA PDFs.

Output: {abbr: {"AB__district__sec.pdf": "text", ...}}

Usage:
  CRIDA_PDF_CACHE=/tmp/opencode/pdfs python3 scripts/build_crida_fulldump.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_CACHE = os.environ.get("CRIDA_PDF_CACHE", "/tmp/opencode/pdfs")

import pdfplumber

FILES = ("1.1.pdf", "1.4.pdf", "1.7.pdf")


def extract(path):
    try:
        with pdfplumber.open(path) as pdf:
            parts = []
            for p in pdf.pages:
                t = p.extract_text() or ""
                parts.append(t)
            return "\n".join(parts)
    except Exception:
        return ""


def main():
    dump = {}
    for name in sorted(os.listdir(PDF_CACHE)):
        m = re.match(r"^([A-Z]{2})__(.+)__(1\.[147])\.pdf$", name)
        if not m:
            continue
        abbr, district, sec = m.groups()
        dump.setdefault(abbr, {})
        text = extract(os.path.join(PDF_CACHE, name))
        if text.strip():
            dump[abbr][f"{abbr}__{district}__{sec}.pdf"] = text
    out = os.path.join(PDF_CACHE, "fulldump.json")
    json.dump(dump, open(out, "w"))
    n = sum(len(v) for v in dump.values())
    print(f"wrote {out}: {len(dump)} states, {n} pdf texts")


if __name__ == "__main__":
    main()
