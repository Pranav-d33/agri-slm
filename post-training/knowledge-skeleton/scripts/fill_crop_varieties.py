#!/usr/bin/env python3
"""Fill notified/released crop varieties for the 16 crops that previously had none.

Sources:
- SATHI/seednet CSC (Central Sub-Committee on Crop Standards, Notification and
  Release of Varieties) meeting minutes + gazette (data/_raw/sathi/, id sathi-notices)
- ICAR institute + state SAU release records (via research-verified citations)

Crops with a genuinely verified official release get `notified_varieties[]`.
Crops with NO officially released/notified variety get `notified_status` = "none",
recording the commercial cultivars actually grown instead (never fabricated).
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROPS = os.path.join(BASE, "data", "crops.json")

SATHI = {"id": "sathi-notices", "url": "https://seedtrace.gov.in/ms015/seedNet/noticeDetails"}

def v(name, source):
    return {"name": name, "type": "released", "source": source}

# Notifier per variety, with source URLs
APPLE_SRC = {**SATHI, "url": "https://seedtrace.gov.in/ms015/seedNet/noticeDetails?type=HorticultureCrops"}
SAPOTA_SRC = {"id": "tnau-agritech", "url": "https://agritech.tnau.ac.in/horticulture/horti_TNAU_varieties_fc_sapota.html"}
PEACH_SRC = {"id": "pauc", "url": "https://www.apnikheti.com/en/pn/agriculture/horticulture/fruit/peach"}

def fill():
    data = json.load(open(CROPS))
    by_id = {e["id"]: e for e in data["entities"]}

    def add(id_, key, val):
        by_id[id_].setdefault("attributes", {})[key] = val

    # --- Apple: CITH series (gazette + 32nd hort minutes) ---
    add("crops.apple", "notified_varieties", [
        v("CITH-Ammol", APPLE_SRC),
        v("CITH-Priame", APPLE_SRC),
        v("CITH-Pride", APPLE_SRC),
        v("Shalimar Apple-1", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/Horticulture/HC24.pdf"}),
        v("Shalimar Apple-2", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/Horticulture/HC24.pdf"}),
    ])

    # --- Cabbage: Pusa Red Cabbage-5, Pusa Cabbage-1 ---
    add("crops.vegetables.cabbage", "notified_varieties", [
        v("Pusa Red Cabbage-5 (KTCBR-5)", APPLE_SRC),
        v("Pusa Cabbage-1 (KGMR-1) (Hybrid)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/Horticulture/CSC19Hort.pdf"}),
    ])

    # --- Horse Gram ---
    add("crops.horse_gram", "notified_varieties", [
        v("VL Gahat-19 (VLG-19)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/CSC54MINUTES.pdf"}),
        v("Indira Kulthi-1 (IKGH-05-01)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/CSC60MINUTES.pdf"}),
    ])

    # --- Moth Bean ---
    add("crops.moth_bean", "notified_varieties", [
        v("Marudhar P.ntab (RM0-2251 / RMO-225-1-6-3)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/minutes_of_the_meeting_of_Central_Sub-_Committee_Meeting_0001.pdf"}),
    ])

    # --- Mesta (Kenaf) ---
    add("crops.mesta", "notified_varieties", [
        v("AMV-7 (AHS 160)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/CSC60MINUTES.pdf"}),
        v("JBMP 3 (Priya)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/minutes_of_the_meeting_of_Central_Sub-_Committee_Meeting_0001.pdf"}),
        v("Shakti (JBM-81)", {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/CMS/CSC/CSC64MINUTES.pdf"}),
    ])

    # --- Sapota: TNAU releases ---
    sapota_varieties = [
        ("CO.1", "1972"), ("CO.2", "1974"), ("PKM 1", "1981"), ("PKM 2 (H-2/4)", "1992"),
        ("PKM.3", "1994"), ("CO 3", "2000"), ("PKM (Sa) 4", "2003"), ("PKM (Sa) 5", "2007"),
    ]
    add("crops.fruits.sapota", "notified_varieties", [
        {"name": f"{n}", "type": "released", "year": yr, "source": SAPOTA_SRC} for n, yr in sapota_varieties
    ])

    # --- Clove: PPI (CL) 1 ---
    add("crops.spices.clove", "notified_varieties", [
        {"name": "PPI (CL) 1", "type": "released", "year": "2012",
         "source": {"id": "aicrps", "url": "https://aicrps.res.in/pdf/ICAR%20AICRPS%20Varieties.pdf"}},
    ])

    # --- Sugar Beet ---
    add("crops.sugar_beet", "notified_varieties", [
        v("LS-6", {"id": "isri-sugarbeet", "url": "https://isri.res.in/iisr/pages/breedsugarbeet.jsp"}),
        v("ISRI Comp-1", {"id": "isri-sugarbeet", "url": "https://isri.res.in/iisr/pages/breedsugarbeet.jsp"}),
        v("Pant S-10", {"id": "gbpant", "url": "https://link.springer.com/content/pdf/10.1007/978-981-19-2730-0.pdf"}),
    ])

    # --- Peach: PAU releases (verified by independent research) ---
    add("crops.fruits.peach", "notified_varieties", [
        v("Shan-e-Punjab (16-33)", PEACH_SRC),
        v("Pratap (TA-170)", PEACH_SRC),
        v("Flordasun", PEACH_SRC),
        v("Flordaprince", PEACH_SRC),
    ])

    # --- Jackfruit: commercial cultivars, no central notified release found ---
    add("crops.fruits.jackfruit", "notified_status", {
        "status": "none",
        "note": "No officially notified/released variety under the CSC. Grown from local cultivars (e.g. Singapura, Muttom Varikka, Chakka).",
        "source": {**SATHI, "url": "https://seedtrace.gov.in/ms015/seedNet/noticeDetails?type=HorticultureCrops"},
    })

    # --- No released variety: record commercial cultivars (verified) ---
    add("crops.fruits.pineapple", "notified_status", {
        "status": "none",
        "commercial_cultivars": ["Giant Kew", "Queen (Common Queen)", "Red Spanish", "Mauritius"],
        "source": {"id": "ccari", "url": "https://ccari.res.in/dss/pineapple.html"},
    })
    add("crops.fruits.strawberry", "notified_status", {
        "status": "none",
        "commercial_cultivars": ["Sweet Charlie", "Chandler", "Winter Dawn", "Camarosa", "Festival", "Nabila"],
        "source": {"id": "icar-jas", "url": "https://epubs.icar.org.in/index.php/IJAgS/article/view/76497"},
    })
    add("crops.fruits.plum", "notified_status", {
        "status": "none",
        "commercial_cultivars": ["Satluj Purple", "Kala Amritsari", "Alubokhara", "Titron", "Kataruchak"],
        "source": {"id": "pauc", "url": "https://www.apnikheti.com/en/pn/agriculture/horticulture/fruit/plum"},
    })
    add("crops.spices.asafoetida", "notified_status", {
        "status": "none",
        "note": "Ferula assa-foetida grown experimentally (CSIR-IHBT 2020 intro via ICAR-NBPGR; first seed-set 2025); no released variety.",
        "source": {"id": "pib", "url": "https://pib.gov.in/PressReleasePage.aspx?PRID=1665796"},
    })
    add("crops.spices.vanilla", "notified_status", {
        "status": "none",
        "commercial_cultivars": ["Vanilla planifolia (Bourbon type)"],
        "source": {"id": "iisr-spices", "url": "https://www.spices.res.in/"},
    })

    # --- Pear: no central notified release (deferred); note it ---
    add("crops.fruits.pear", "notified_status", {
        "status": "none",
        "note": "Punjab Nakh deferred in 17th CSC hort meeting (AICRIP data missing); no notified variety. Grown from cultivars e.g. Punjab Nakh, Bagugosha.",
        "source": {**SATHI, "url": "https://seedtrace.gov.in/ms012/inspection/getSeedGOFile/SeedGO/PDFFILES/CSC17Hort.pdf"},
    })

    # --- Khesari (Grass Pea): released varieties (verified ICAR/IARI + SAU) ---
    add("crops.khesari", "notified_varieties", [
        {"name": "Ratan (BioL-212)", "type": "released", "year": "1999",
         "source": {"id": "icar", "url": "https://icar.org.in/"}},
        {"name": "Prateek (LS 157-14)", "type": "released", "year": "2016",
         "source": {"id": "icar", "url": "https://icar.org.in/"}},
        {"name": "Mahateora", "type": "released", "year": "2016",
         "source": {"id": "icar", "url": "https://icar.org.in/"}},
        {"name": "Nirmal (B-1 Nirmal)", "type": "released",
         "source": {"id": "icarda", "url": "https://www.icarda.org/media/news/grasspea-back-menu-indias-agriculture"}},
        {"name": "Moti (BioL-208)", "type": "released",
         "source": {"id": "icar", "url": "https://icar.org.in/"}},
        {"name": "Pusa 24", "type": "released",
         "source": {"id": "icar", "url": "https://icar.org.in/"}},
    ])

    json.dump(data, open(CROPS, "w"), indent=2, ensure_ascii=False)

if __name__ == "__main__":
    fill()
    print("filled crop varieties")
