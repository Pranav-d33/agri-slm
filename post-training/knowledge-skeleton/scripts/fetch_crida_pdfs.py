#!/usr/bin/env python3
"""Download ICAR-CRIDA Agriculture Contingency Plan district PDFs.

For each district of a state, probe CRIDA folder names (current name plus a few
known rename variants), download 1.1/1.4/1.7.pdf to <cache>/<ABBR>__<name>__<sec>.pdf,
and record the working folder name in <cache>/<ABBR>__names.json.

Usage:
  CRIDA_PDF_CACHE=/tmp/opencode/pdfs python3 scripts/fetch_crida_pdfs.py <ABBR>
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISTRICTS_PATH = os.path.join(ROOT, "data", "locations", "districts.json")
PDF_CACHE = os.environ.get("CRIDA_PDF_CACHE", "/tmp/opencode/pdfs")
BASE = "https://icar-crida.res.in/CCP"

# current district name (normalized) -> CRIDA folder names to try after the plain name
RENAMES = {
    "gurugram": ["gurgoan", "gurgaon"],
    "nuh": ["mewat"],
    "sonipat": ["sonipet"],
    "ahilyanagar": ["ahmednagar"],
    "chhatrapati sambhajinagar": ["aurangabad"],
    "dharashiv": ["osmanabad"],
    "amravati": ["amravathi"],
    "sindhudurg": ["sindhudurga"],
    "raigad": ["raigarh"],
    "thane": ["thane and phalagar"],
    "kasaragod": ["kasargod"],
    "thrissur": ["trissur"],
    "lahaul and spiti": ["lahaul spiti", "lahaul & spiti"],
    "cooch behar": ["coochbehar"],
    "purba bardhaman": ["bardhaman"],
    "kalaburagi": ["gulbarga"],
    "ballari": ["bellary"],
    "vijayapura": ["bijapur"],
    "mysuru": ["mysore"],
    "shivamogga": ["shimoga"],
    "chikkamagaluru": ["chickmagalur", "chikmagalur"],
    "tumakuru": ["tumkur"],
    "bengaluru urban": ["bengaluru urban", "bangalore urban"],
    "bengaluru rural": ["bengaluru rural", "bangalore rural"],
    "kodagu": ["kodagu", "coorg"],
    "prayagraj": ["allahabad"],
    "ayodhya": ["faizabad"],
    "sambhal": ["bhim nagar", "bhimnagar"],
    "amroha": ["jyotiba phule nagar", "j p nagar"],
    "hapur": ["hapur", "panchsheel nagar"],
    "shamli": ["shamli", "prabudh nagar"],
    "kanshiram nagar": ["kasganj"],
    "kasganj": ["kasganj", "kanshiram nagar"],
    "gautam buddha nagar": ["gautam budh nagar", "gautam buddha nagar"],
    "kanpur dehat": ["kanpur dehat", "ramabai nagar"],
    "kanpur nagar": ["kanpur nagar", "kanpur"],
    "bhadohi": ["sant ravidas nagar", "bhadohi"],
    "kushinagar": ["kushinagar", "kushi nagar"],
    "chitrakoot": ["chitrakoot", "chitrakut"],
    "sant kabeer nagar": ["sant kabir nagar"],
    "chandauli": ["chandauli", "chandoli"],
    "ghazipur": ["ghazipur", "gazipur"],
    "mahoba": ["mahoba"],
    "budaun": ["badaun", "budaun"],
    "bara banki": ["barabanki", "bara banki"],
    "rae bareli": ["raebareli", "rae bareli"],
    "sant kabeer nagar": ["sant kabir nagar"],
    "shrawasti": ["shravasti", "sravasti"],
    "shravasti": ["shravasti", "sravasti"],
    "maharajganj": ["maharajganj", "mahrajganj"],
    "mahrajganj": ["maharajganj"],
    "ambedkar nagar": ["ambedkar nagar", "ambedkar"],
    "gautam buddha nagar": ["gautam budh nagar"],
    "siddharthnagar": ["siddharth nagar"],
    "kheri": ["lakhimpur kheri", "kheri"],
    "lakhimpur kheri": ["lakhimpur kheri", "kheri"],
    "baghpat": ["bagpat", "baghpat"],
    "bhadohi": ["bhadohi", "sant ravidas nagar"],
    "kanpur dehat": ["kanpur dehat", "ramabai nagar", "ramabai"],
    "amroha": ["jyotiba phule nagar", "j p nagar", "amroha"],
    "rajanna sircilla": ["rajanna sircilla", "siricilla"],
    "komaram bheem": ["komaram bheem", "kumaram bheem"],
    "jogulamba gadwal": ["jogulamba gadwal"],
    "medchal malkajgiri": ["medchal malkajgiri", "malkajgiri"],
    "suryapet": ["suryapet", "suryapeta"],
    "yadadri bhuvanagiri": ["yadadri bhuvanagiri", "nalgonda"],
    "jayashankar bhupalpally": ["jayashankar bhupalpally", "bhupalpally"],
    "bhadradri kothagudem": ["bhadradri kothagudem", "kothagudem"],
    "warangal urban": ["warangal urban", "warangal"],
    "warangal rural": ["warangal rural", "warangal"],
    "mancherial": ["mancherial", "mancheriyal"],
    "nizamabad": ["nizamabad", "nijamabad"],
    "mahabubnagar": ["mahabubnagar", "mahaboobnagar"],
    "nagarkurnool": ["nagarkurnool", "nagarkurnool"],
    "mulugu": ["mulugu", "mulug"],
    "siddipet": ["siddipet"],
    "sangareddy": ["sangareddy", "sangareddi"],
    "kamareddy": ["kamareddy", "kamareddi"],
    "sathupalli": ["sathupalli", "sathupally"],
    "nirmal": ["nirmal"],
    "adilabad": ["adilabad"],
    "janagama": ["jangaon", "janagam"],
    "mahabubabad": ["mahabubabad"],
    "khammam": ["khammam"],
    "peddapalli": ["peddapalli"],
    "jagtial": ["jagtial", "jagityal"],
    "karimnagar": ["karimnagar"],
    "nalgonda": ["nalgonda"],
    "vikarabad": ["vikarabad"],
    "rangareddy": ["rangareddy", "ranga reddy"],
    "hyderabad": ["hyderabad"],
    "medak": ["medak"],
    "nagapattinam": ["nagapattinam", "nagai"],
    "mayiladuthurai": ["mayiladuthurai", "mayuram"],
    "tenkasi": ["tenkasi"],
    "tirunelveli": ["tirunelveli"],
    "virudhunagar": ["virudhunagar"],
    "karur": ["karur"],
    "perambalur": ["perambalur"],
    "ariyalur": ["ariyalur"],
    "cuddalore": ["cuddalore"],
    "villianur": ["villianur", "villupuram"],
    "tiruvallur": ["tiruvallur"],
    "chennai": ["chennai"],
    "kallakurichi": ["kallakurichi", "kalvarayan hills"],
    "ranipet": ["ranipet", "vellore"],
    "tirupathur": ["tirupathur", "vellore"],
    "chengalpattu": ["chengalpattu", "kancheepuram"],
    "kanyakumari": ["kanyakumari", "kanniyakumari"],
    "theni": ["theni"],
    "dindigul": ["dindigul"],
    "the nilgiris": ["nilgiris", "the nilgiris"],
    "sivaganga": ["sivaganga"],
    "ramanathapuram": ["ramanathapuram", "ramnad"],
    "thoothukudi": ["thoothukudi", "tuticorin"],
    "madurai": ["madurai"],
    "salem": ["salem"],
    "namakkal": ["namakkal"],
    "erode": ["erode"],
    "tiruppur": ["tiruppur", "tirupur"],
    "coimbatore": ["coimbatore"],
    "dharmapuri": ["dharmapuri"],
    "krishnagiri": ["krishnagiri"],
    "vellore": ["vellore"],
    "tiruvannamalai": ["tiruvannamalai"],
    "viluppuram": ["villupuram", "villianur"],
    "nagapattinam": ["nagapattinam"],
    "kumbakonam": ["thanjavur"],
    "thanjavur": ["thanjavur"],
    "tiruvarur": ["tiruvarur"],
    "pudukkottai": ["pudukkottai"],
    "sivaganga": ["sivaganga"],
    "virudhunagar": ["virudhunagar"],
    "raichur": ["raichur"],
    "koppal": ["koppal"],
    "gadag": ["gadag"],
    "dharwad": ["dharwad"],
    "uttara kannada": ["uttara kannada"],
    "haveri": ["haveri"],
    "davanagere": ["davanagere"],
    "shivamogga": ["shivamogga", "shimoga"],
    "udupi": ["udupi"],
    "dakshina kannada": ["dakshina kannada"],
    "chikkaballapura": ["chikkaballapur"],
    "kolar": ["kolar"],
    "chamarajanagara": ["chamarajanagar"],
    "mandya": ["mandya"],
    "ramanagara": ["ramanagara"],
    "bengaluru": ["bengaluru"],
    "chitradurga": ["chitradurga"],
    "hassan": ["hassan"],
    "tumakuru": ["tumakuru", "tumkur"],
    "chikkaballapur": ["chikkaballapura"],
    "bidar": ["bidar"],
    "belagavi": ["belgaum"],
    "bagalkot": ["bagalkot"],
    "bijapur": ["bijapur", "vijayapura"],
    "bagalkote": ["bagalkot"],
    "gadag": ["gadag"],
    "koppal": ["koppal"],
    "gulbarga": ["gulbarga", "kalaburagi"],
    "yadgir": ["yadgir"],
    "raichur": ["raichur"],
    "bellary": ["bellary", "ballari"],
    "chitradurga": ["chitradurga"],
    "davanagere": ["davanagere"],
    "shimoga": ["shimoga", "shivamogga"],
    "udupi": ["udupi"],
    "south kannada": ["dakshina kannada"],
    "mangalore": ["mangalore"],
    "chickmagalur": ["chikkamagaluru", "chickmagalur"],
    "tumkur": ["tumkur", "tumakuru"],
    "kolar": ["kolar"],
    "bangalore": ["bengaluru", "bangalore"],
    "bangalore urban": ["bengaluru urban", "bangalore urban"],
    "bangalore rural": ["bengaluru rural", "bangalore rural"],
    "ramanagara": ["ramanagara"],
    "chamarajanagar": ["chamarajanagar", "chamarajanagara"],
    "mysore": ["mysore", "mysuru"],
    "hassan": ["hassan"],
    "mandya": ["mandya"],
    "kodagu": ["kodagu", "coorg"],
    "bengaluru rural": ["bengaluru rural"],
    "rama nagara": ["ramanagara"],
    "kodagu": ["kodagu"],
    "uttarakhand": ["uk"],
}

ABBR_STATE = {
    "AN": "Andaman and Nicobar Islands", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh",
    "AS": "Assam", "BR": "Bihar", "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir",
    "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala", "MP": "Madhya Pradesh",
    "MH": "Maharashtra", "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland",
    "OR": "Odisha", "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim",
    "TN": "Tamil Nadu", "TR": "Tripura", "UP": "Uttar Pradesh", "UK": "Uttarakhand",
    "WB": "West Bengal",
}


def norm(name):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", name.lower().strip())).strip()


def load_variants():
    """RENAMES merged with optional per-state overrides in scripts/crida_variants/<ABBR>.json."""
    merged = {k: list(v) for k, v in RENAMES.items()}
    vdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crida_variants")
    if os.path.isdir(vdir):
        for fn in sorted(os.listdir(vdir)):
            if fn.endswith(".json"):
                try:
                    for k, v in json.load(open(os.path.join(vdir, fn))).items():
                        merged.setdefault(k, []).extend(v)
                except Exception:
                    pass
    return merged


VARIANTS = load_variants()


def candidates(district_name):
    n = norm(district_name)
    names = [n] + VARIANTS.get(n, [])
    seen, out = set(), []
    for x in names:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
        out.append(" ".join(w[:1].upper() + w[1:] for w in x.split()))
    return out


def get(url, timeout=25):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%"), headers={"User-Agent": "agri-slm-skeleton/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("abbr")
    ap.add_argument("--force", action="store_true", help="re-download even if names recorded")
    args = ap.parse_args()
    abbr = args.abbr.upper()

    os.makedirs(PDF_CACHE, exist_ok=True)
    state = ABBR_STATE.get(abbr)
    if not state:
        print(f"Unknown abbr {abbr}")
        sys.exit(1)
    dist = json.load(open(DISTRICTS_PATH))
    districts = next(s["districts"] for s in dist["states"] if s["state"] == state)

    nmap_path = os.path.join(PDF_CACHE, f"{abbr}__names.json")
    nmap = {} if args.force or not os.path.exists(nmap_path) else json.load(open(nmap_path))

    found, miss = 0, []
    for d in districts:
        dname = d["name"]
        if dname in nmap:
            print(f"  skip {dname}")
            continue
        hit = None
        for cand in candidates(dname):
            url = f"{BASE}/{abbr}/{cand}/1.1.pdf"
            try:
                data = get(url)
                if data[:4] == b"%PDF":
                    hit = cand
                    break
            except Exception:
                continue
        if not hit:
            miss.append(dname)
            print(f"  MISS {dname}")
            continue
        nmap[dname] = hit
        # download the three sections
        for sec in ("1.1", "1.4", "1.7"):
            out = os.path.join(PDF_CACHE, f"{abbr}__{dname}__{sec}.pdf")
            if os.path.exists(out) and not args.force:
                continue
            try:
                open(out, "wb").write(get(f"{BASE}/{abbr}/{hit}/{sec}.pdf"))
            except Exception as e:
                print(f"  warn {dname} {sec}: {e}")
        found += 1
        print(f"  ok   {dname} -> {hit}")

    json.dump(nmap, open(nmap_path, "w"), indent=1)
    print(f"\n{state}: {found} matched, {len(miss)} missing: {miss}")


if __name__ == "__main__":
    main()
