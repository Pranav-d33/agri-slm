#!/usr/bin/env python3
"""
Level-2 completion backfill: enumerate every category fully per its
authoritative source (DAC&FW crops, NBAGR breeds, CIB&RC banned list,
CWC basins, IMD events). Also:
- fixes chilli's dual parent (canonical parent = spices)
- strips agrovocId fields (AGROVOC used for aliases only, extract-only)
- adds found_in location.india to any entity lacking a location anchor
Idempotent: skips ids that already exist; run any time.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SRC = {"dacfw": "https://agricoop.nic.in/", "nhb": "https://nhb.gov.in/",
       "spicesboard": "https://www.indianspices.com/", "nbragr": "https://nbagr.res.in/",
        "cibrc": "https://cibrc.gov.in/", "cibrc-ban": "https://ppqs.gov.in/",
        "cibrc-9-3": "https://www.ppqs.gov.in/divisions/cib-rc/registered-products",
       "cwc": "https://cwc.gov.in/", "imd": "https://mausam.imd.gov.in/",
       "icar": "https://icar.org.in/", "seednet": "https://seednet.gov.in/",
       "tnau-agritech": "https://agritech.tnau.ac.in/agriculture/agri_index.html"}

# (id, name, parent, source, attributes, [states])  -- states are top producers
NEW = [
    # ---- cereals (DAC&FW major cereals, complete) ----
    ("crops.oats", "Oats", "crops.cereals", "dacfw",
     {"scientific": "Avena sativa", "season": "Rabi", "note": "Grown mainly as fodder; grain minor"},
     ["uttar_pradesh", "haryana", "madhya_pradesh"]),
    # ---- millets (GoI 'Shree Anna' list, complete) ----
    ("crops.foxtail_millet", "Foxtail Millet", "crops.millets", "dacfw",
     {"scientific": "Setaria italica", "season": "Kharif", "aliases": ["Kangni"], "note": "Short-duration, drought-tolerant"},
     ["andhra_pradesh", "karnataka", "tamil_nadu"]),
    ("crops.proso_millet", "Proso Millet", "crops.millets", "dacfw",
     {"scientific": "Panicum miliaceum", "season": "Kharif", "aliases": ["Cheena"], "note": "Grown in NE hills and Himachal"},
     ["manipur", "himachal_pradesh", "uttarakhand"]),
    ("crops.little_millet", "Little Millet", "crops.millets", "dacfw",
     {"scientific": "Panicum sumatrense", "season": "Kharif", "aliases": ["Kutki"], "note": "Hardy grain of poor, shallow soils"},
     ["madhya_pradesh", "chhattisgarh", "odisha"]),
    ("crops.kodo_millet", "Kodo Millet", "crops.millets", "dacfw",
     {"scientific": "Paspalum scrobiculatum", "season": "Kharif", "aliases": ["Kodra"], "note": "Highly drought-resistant"},
     ["madhya_pradesh", "chhattisgarh", "uttar_pradesh"]),
    ("crops.barnyard_millet", "Barnyard Millet", "crops.millets", "dacfw",
     {"scientific": "Echinochloa frumentacea", "season": "Kharif", "aliases": ["Sanwa"], "note": "Fastest-growing millet; 6-8 weeks to maturity"},
     ["uttarakhand", "uttar_pradesh", "madhya_pradesh"]),
    ("crops.browntop_millet", "Browntop Millet", "crops.millets", "dacfw",
     {"scientific": "Brachiaria ramosa", "season": "Kharif", "note": "Minor millet; Karnataka and AP"},
     ["karnataka", "andhra_pradesh"]),
    # ---- pulses (DAC&FW major pulses, complete) ----
    ("crops.moth_bean", "Moth Bean", "crops.pulses", "dacfw",
     {"scientific": "Vigna aconitifolia", "season": "Kharif", "aliases": ["Matki"], "note": "Drought-hardy pulse of arid Rajasthan"},
     ["rajasthan", "gujarat"]),
    ("crops.horse_gram", "Horse Gram", "crops.pulses", "dacfw",
     {"scientific": "Macrotyloma uniflorum", "season": "Kharif/rabi", "aliases": ["Kulthi"], "note": "Climate-resilient; rich in iron and protein"},
     ["karnataka", "andhra_pradesh", "tamil_nadu"]),
    ("crops.cowpea", "Cowpea", "crops.pulses", "dacfw",
     {"scientific": "Vigna unguiculata", "season": "Kharif and zaid", "aliases": ["Lobia"], "note": "Grain, vegetable and fodder"},
     ["rajasthan", "gujarat", "karnataka"]),
    ("crops.field_pea", "Field Pea", "crops.pulses", "dacfw",
     {"scientific": "Pisum sativum subsp. arvense", "season": "Rabi", "aliases": ["Matar"], "note": "Grain pea of the Gangetic plains"},
     ["uttar_pradesh", "madhya_pradesh", "bihar"]),
    ("crops.rajma", "Kidney Bean", "crops.pulses", "dacfw",
     {"scientific": "Phaseolus vulgaris", "season": "Kharif (hills)", "aliases": ["Rajma"], "note": "Hill pulse; HP, J&K and Uttarakhand"},
     ["himachal_pradesh", "uttarakhand", "jammu_kashmir"]),
    ("crops.khesari", "Khesari (Grass Pea)", "crops.pulses", "dacfw",
     {"scientific": "Lathyrus sativus", "season": "Rabi", "aliases": ["Kesari dal"], "note": "Tolerant to waterlogging; sale restricted due to lathyrism"},
     ["west_bengal", "bihar", "madhya_pradesh"]),
    # ---- oilseeds (DAC&FW nine-oilseed group, complete) ----
    ("crops.linseed", "Linseed", "crops.oilseeds", "dacfw",
     {"scientific": "Linum usitatissimum", "season": "Rabi", "aliases": ["Alsi"], "note": "Oilseed and fibre (flax)"},
     ["madhya_pradesh", "chhattisgarh", "uttar_pradesh"]),
    ("crops.niger", "Niger Seed", "crops.oilseeds", "dacfw",
     {"scientific": "Guizotia abyssinica", "season": "Kharif", "aliases": ["Ramtil"], "note": "Minor oilseed of central India"},
     ["madhya_pradesh", "chhattisgarh", "karnataka"]),
    ("crops.safflower", "Safflower", "crops.oilseeds", "dacfw",
     {"scientific": "Carthamus tinctorius", "season": "Rabi", "aliases": ["Kardi"], "note": "Minor oilseed; Maharashtra and Karnataka"},
     ["maharashtra", "karnataka", "andhra_pradesh"]),
    # ---- fibre ----
    ("crops.mesta", "Mesta (Kenaf)", "crops.fibre", "dacfw",
     {"scientific": "Hibiscus cannabinus", "season": "Kharif", "note": "Jute substitute fibre"},
     ["andhra_pradesh", "odisha", "west_bengal"]),
    # ---- sugar ----
    ("crops.sugar_beet", "Sugar Beet", "crops.sugar", "dacfw",
     {"scientific": "Beta vulgaris", "season": "Rabi", "note": "Minor; experimental cultivation in Uttar Pradesh"},
     ["uttar_pradesh"]),
    # ---- fruits (NHB major fruits, complete) ----
    ("crops.fruits.pomegranate", "Pomegranate", "crops.fruits", "nhb",
     {"scientific": "Punica granatum", "season": "Two crops/yr (mrig bahar, hastha bahar)", "aliases": ["Anar"], "note": "India largest producer; Maharashtra leads"},
     ["maharashtra", "karnataka", "andhra_pradesh"]),
    ("crops.fruits.mandarin", "Mandarin Orange", "crops.fruits", "nhb",
     {"scientific": "Citrus reticulata", "season": "Winter fruit", "aliases": ["Santra", "Nagpur orange"], "note": "Nagpur (MH) and Khasi (Meghalaya) mandarins"},
     ["maharashtra", "madhya_pradesh", "assam"]),
    ("crops.fruits.lemon", "Lemon", "crops.fruits", "nhb",
     {"scientific": "Citrus limon", "season": "Year-round", "aliases": ["Nimbu"], "note": "Key citrus after mandarin"},
     ["andhra_pradesh", "gujarat", "maharashtra"]),
    ("crops.fruits.sweet_orange", "Sweet Orange", "crops.fruits", "nhb",
     {"scientific": "Citrus sinensis", "season": "Winter fruit", "aliases": ["Malta"], "note": "Punjab and Telangana lead"},
     ["punjab", "telangana"]),
    ("crops.fruits.pineapple", "Pineapple", "crops.fruits", "nhb",
     {"scientific": "Ananas comosus", "season": "Year-round", "aliases": ["Ananas"], "note": "North-east and West Bengal lead"},
     ["west_bengal", "assam", "tripura"]),
    ("crops.fruits.litchi", "Litchi", "crops.fruits", "nhb",
     {"scientific": "Litchi chinensis", "season": "Summer fruit (May-Jun)", "note": "Bihar produces most of India's litchi"},
     ["bihar", "west_bengal", "uttar_pradesh"]),
    ("crops.fruits.sapota", "Sapota", "crops.fruits", "nhb",
     {"scientific": "Manilkara zapota", "season": "Two crops/yr", "aliases": ["Chikoo", "Sapodilla"], "note": "Gujarat and Maharashtra lead"},
     ["gujarat", "maharashtra", "karnataka"]),
    ("crops.fruits.watermelon", "Watermelon", "crops.fruits", "nhb",
     {"scientific": "Citrullus lanatus", "season": "Zaid (summer)", "aliases": ["Tarbooz"], "note": "Classic zaid crop"},
     ["uttar_pradesh", "maharashtra", "andhra_pradesh"]),
    ("crops.fruits.muskmelon", "Muskmelon", "crops.fruits", "nhb",
     {"scientific": "Cucumis melo", "season": "Zaid (summer)", "aliases": ["Kharbuja"], "note": "Zaid crop of north India"},
     ["uttar_pradesh", "punjab", "rajasthan"]),
    ("crops.fruits.jackfruit", "Jackfruit", "crops.fruits", "nhb",
     {"scientific": "Artocarpus heterophyllus", "season": "Summer fruit", "aliases": ["Kathal"], "note": "Largest tree-borne fruit; southern and eastern states"},
     ["kerala", "west_bengal", "tamil_nadu"]),
    ("crops.fruits.peach", "Peach", "crops.fruits", "nhb",
     {"scientific": "Prunus persica", "season": "Temperate; harvest May-Jul", "aliases": ["Aadu"], "note": "Temperate fruit of the Himalaya"},
     ["himachal_pradesh", "jammu_kashmir", "uttarakhand"]),
    ("crops.fruits.plum", "Plum", "crops.fruits", "nhb",
     {"scientific": "Prunus domestica", "season": "Temperate; harvest Jun-Aug", "aliases": ["Aloo Bukhara"], "note": "Himachal and J&K lead"},
     ["himachal_pradesh", "jammu_kashmir", "uttarakhand"]),
    ("crops.fruits.pear", "Pear", "crops.fruits", "nhb",
     {"scientific": "Pyrus communis", "season": "Temperate; harvest Jul-Sep", "aliases": ["Nashpati"], "note": "Temperate fruit; Kinnaur pears famous"},
     ["himachal_pradesh", "jammu_kashmir", "uttarakhand"]),
    ("crops.fruits.apricot", "Apricot", "crops.fruits", "nhb",
     {"scientific": "Prunus armeniaca", "season": "Temperate; harvest May-Jun", "aliases": ["Khubani"], "note": "Ladakh and Himachal; also dried fruit"},
     ["jammu_kashmir", "himachal_pradesh"]),
    # ---- vegetables (NHB major vegetables, complete) ----
    ("crops.vegetables.okra", "Okra", "crops.vegetables", "nhb",
     {"scientific": "Abelmoschus esculentus", "season": "Kharif and summer", "aliases": ["Bhindi", "Lady finger"], "note": "Major export vegetable"},
     ["gujarat", "west_bengal", "bihar"]),
    ("crops.vegetables.peas", "Garden Peas", "crops.vegetables", "nhb",
     {"scientific": "Pisum sativum", "season": "Rabi (winter)", "aliases": ["Matar"], "note": "Winter vegetable; also processed frozen"},
     ["uttar_pradesh", "madhya_pradesh", "punjab"]),
    ("crops.vegetables.bottle_gourd", "Bottle Gourd", "crops.vegetables", "nhb",
     {"scientific": "Lagenaria siceraria", "season": "Kharif and summer", "aliases": ["Lauki"], "note": "High-yielding cucurbit"},
     ["uttar_pradesh", "west_bengal", "bihar"]),
    ("crops.vegetables.bitter_gourd", "Bitter Gourd", "crops.vegetables", "nhb",
     {"scientific": "Momordica charantia", "season": "Kharif and summer", "aliases": ["Karela"], "note": "Medicinal value; bitter principle"},
     ["uttar_pradesh", "west_bengal", "gujarat"]),
    ("crops.vegetables.ridge_gourd", "Ridge Gourd", "crops.vegetables", "nhb",
     {"scientific": "Luffa acutangula", "season": "Kharif", "aliases": ["Tori"], "note": "Common cucurbit of the plains"},
     ["uttar_pradesh", "west_bengal", "andhra_pradesh"]),
    ("crops.vegetables.cucumber", "Cucumber", "crops.vegetables", "nhb",
     {"scientific": "Cucumis sativus", "season": "Kharif and zaid", "aliases": ["Kheera"], "note": "Salad and pickling crop"},
     ["uttar_pradesh", "bihar", "punjab"]),
    ("crops.vegetables.carrot", "Carrot", "crops.vegetables", "nhb",
     {"scientific": "Daucus carota", "season": "Rabi", "aliases": ["Gajar"], "note": "Root vegetable; black (desi) and orange types"},
     ["uttar_pradesh", "punjab", "haryana"]),
    ("crops.vegetables.radish", "Radish", "crops.vegetables", "nhb",
     {"scientific": "Raphanus sativus", "season": "Rabi", "aliases": ["Mooli"], "note": "Quick root vegetable"},
     ["west_bengal", "uttar_pradesh", "bihar"]),
    ("crops.vegetables.spinach", "Spinach", "crops.vegetables", "nhb",
     {"scientific": "Spinacia oleracea", "season": "Rabi (winter)", "aliases": ["Palak"], "note": "Iron-rich leafy vegetable"},
     ["punjab", "uttar_pradesh", "west_bengal"]),
    ("crops.vegetables.sweet_potato", "Sweet Potato", "crops.vegetables", "nhb",
     {"scientific": "Ipomoea batatas", "season": "Kharif", "aliases": ["Shakarkandi"], "note": "Starchy tuber; Odisha and WB lead"},
     ["odisha", "west_bengal", "uttar_pradesh"]),
    ("crops.vegetables.tapioca", "Tapioca", "crops.vegetables", "nhb",
     {"scientific": "Manihot esculenta", "season": "Annual; planted with monsoon", "aliases": ["Cassava"], "note": "Staple tuber of Kerala and Tamil Nadu"},
     ["kerala", "tamil_nadu", "andhra_pradesh"]),
    ("crops.vegetables.drumstick", "Drumstick", "crops.vegetables", "nhb",
     {"scientific": "Moringa oleifera", "season": "Year-round pods", "aliases": ["Sahjan", "Moringa"], "note": "Nutritious pods and leaves"},
     ["tamil_nadu", "andhra_pradesh", "karnataka"]),
    ("crops.vegetables.amaranth", "Amaranth", "crops.vegetables", "nhb",
     {"scientific": "Amaranthus spp.", "season": "Year-round", "aliases": ["Chauli"], "note": "Leafy vegetable; fast-growing"},
     ["karnataka", "kerala", "west_bengal"]),
    # ---- spices (Spices Board top spices, complete) ----
    ("crops.spices.cumin", "Cumin", "crops.spices", "spicesboard",
     {"scientific": "Cuminum cyminum", "season": "Rabi", "aliases": ["Jeera"], "note": "India largest producer and exporter"},
     ["gujarat", "rajasthan"]),
    ("crops.spices.coriander", "Coriander", "crops.spices", "spicesboard",
     {"scientific": "Coriandrum sativum", "season": "Rabi", "aliases": ["Dhania"], "note": "Seed spice; leaves used as vegetable"},
     ["rajasthan", "madhya_pradesh", "gujarat"]),
    ("crops.spices.fenugreek", "Fenugreek", "crops.spices", "spicesboard",
     {"scientific": "Trigonella foenum-graecum", "season": "Rabi", "aliases": ["Methi"], "note": "Seed spice; leaves used as vegetable"},
     ["rajasthan", "madhya_pradesh", "gujarat"]),
    ("crops.spices.fennel", "Fennel", "crops.spices", "spicesboard",
     {"scientific": "Foeniculum vulgare", "season": "Rabi", "aliases": ["Saunf"], "note": "Seed spice; Gujarat leads"},
     ["gujarat", "rajasthan", "uttar_pradesh"]),
    ("crops.spices.ajwain", "Ajwain", "crops.spices", "spicesboard",
     {"scientific": "Trachyspermum ammi", "season": "Rabi", "aliases": ["Carom"], "note": "Digestive seed spice"},
     ["gujarat", "rajasthan", "madhya_pradesh"]),
    ("crops.spices.clove", "Clove", "crops.spices", "spicesboard",
     {"scientific": "Syzygium aromaticum", "season": "Perennial", "aliases": ["Laung"], "note": "Tree spice; domestic production tiny, mostly imported"},
     ["kerala", "tamil_nadu"]),
    ("crops.spices.cinnamon", "Cinnamon", "crops.spices", "spicesboard",
     {"scientific": "Cinnamomum verum", "season": "Perennial", "aliases": ["Dalchini"], "note": "Bark spice of the Western Ghats"},
     ["kerala", "karnataka"]),
    ("crops.spices.nutmeg", "Nutmeg", "crops.spices", "spicesboard",
     {"scientific": "Myristica fragrans", "season": "Perennial", "aliases": ["Jaiphal"], "note": "Mace is the aril of the same fruit"},
     ["kerala", "tamil_nadu"]),
    ("crops.spices.vanilla", "Vanilla", "crops.spices", "spicesboard",
     {"scientific": "Vanilla planifolia", "season": "Perennial vine", "note": "High-value, labour-intensive; small area"},
     ["kerala", "karnataka", "tamil_nadu"]),
    ("crops.spices.tamarind", "Tamarind", "crops.spices", "spicesboard",
     {"scientific": "Tamarindus indica", "season": "Summer pods", "aliases": ["Imli"], "note": "Souring agent; TN and Karnataka lead"},
     ["tamil_nadu", "karnataka", "andhra_pradesh"]),
    ("crops.spices.garlic", "Garlic", "crops.spices", "spicesboard",
     {"scientific": "Allium sativum", "season": "Rabi", "aliases": ["Lahsun"], "note": "Bulb spice; MP and Gujarat lead"},
     ["madhya_pradesh", "gujarat", "rajasthan"]),
    ("crops.spices.asafoetida", "Asafoetida", "crops.spices", "spicesboard",
     {"scientific": "Ferula assa-foetida", "season": "Perennial", "aliases": ["Hing"], "note": "Mostly imported; India began cultivation in Himachal (2020)"},
     ["himachal_pradesh"]),
    # ---- plantation ----
    ("crops.plantation.arecanut", "Arecanut", "crops.plantation", "dacfw",
     {"scientific": "Areca catechu", "season": "Perennial palm", "aliases": ["Supari", "Betel nut"], "note": "Karnataka grows most of India's arecanut"},
     ["karnataka", "kerala", "assam"]),
    ("crops.plantation.cocoa", "Cocoa", "crops.plantation", "dacfw",
     {"scientific": "Theobroma cacao", "season": "Perennial", "note": "Grown under coconut and arecanut in the south"},
     ["kerala", "karnataka", "tamil_nadu"]),
    # ---- fodder ----
    ("crops.fodder.guinea_grass", "Guinea Grass", "crops.fodder", "dacfw",
     {"scientific": "Megathyrsus maximus", "season": "Perennial", "note": "High-biomass tropical fodder grass"},
     ["karnataka", "tamil_nadu", "maharashtra"]),
    ("crops.fodder.stylo", "Stylo", "crops.fodder", "dacfw",
     {"scientific": "Stylosanthes hamata", "season": "Perennial legume", "note": "Pasture legume for drylands"},
     ["maharashtra", "karnataka"]),
]

# livestock breeds per NBAGR registry -- COMPLETE (240 registered breeds + 4 synthetic),
# home tracts verbatim from nbagr.res.in breed tables (accessed 11.08.2026).
# id collisions across species resolved with a species suffix (_goat/_camel/_pig/_duck etc.).
LIVESTOCK = [
    # ---- cattle (55 indigenous) ----
    ("amritmahal", "Amritmahal", "cattle", ["karnataka"], "Draught; hardy of the south"),
    ("bachaur", "Bachaur", "cattle", ["bihar"], "Draught"),
    ("bargur", "Bargur", "cattle", ["tamil_nadu"], "Draught"),
    ("dangi", "Dangi", "cattle", ["maharashtra", "gujarat"], "Draught; heavy work in hills"),
    ("deoni", "Deoni", "cattle", ["maharashtra", "karnataka"], "Dual-purpose; saline-soil tolerant"),
    ("gaolao", "Gaolao", "cattle", ["maharashtra", "madhya_pradesh"], "Dual-purpose"),
    ("gir", "Gir", "cattle", ["gujarat"], "Milch; famous dairy breed"),
    ("hallikar", "Hallikar", "cattle", ["karnataka"], "Draught; ideal for road transport"),
    ("hariana", "Hariana", "cattle", ["haryana", "uttar_pradesh", "rajasthan"], "Dual-purpose; hardworking"),
    ("kangayam", "Kangayam", "cattle", ["tamil_nadu"], "Draught; strong, fast"),
    ("kankrej", "Kankrej", "cattle", ["gujarat", "rajasthan"], "Dual-purpose; large, hardy"),
    ("kenkatha", "Kenkatha", "cattle", ["uttar_pradesh", "madhya_pradesh"], "Draught; of Bundelkhand"),
    ("kherigarh", "Kherigarh", "cattle", ["uttar_pradesh"], "Draught"),
    ("khillar", "Khillar", "cattle", ["maharashtra", "karnataka"], "Draught; agile and disease-resistant"),
    ("krishna_valley", "Krishna Valley", "cattle", ["karnataka"], "Draught"),
    ("malvi", "Malvi", "cattle", ["madhya_pradesh"], "Draught"),
    ("mewati", "Mewati", "cattle", ["rajasthan", "haryana", "uttar_pradesh"], "Dual-purpose"),
    ("nagori", "Nagori", "cattle", ["rajasthan"], "Draught; handsome, hardy"),
    ("nimari", "Nimari", "cattle", ["madhya_pradesh"], "Draught"),
    ("ongole", "Ongole", "cattle", ["andhra_pradesh"], "Draught; white, large"),
    ("ponwar", "Ponwar", "cattle", ["uttar_pradesh"], "Draught"),
    ("punganur", "Punganur", "cattle", ["andhra_pradesh"], "Smallest Indian breed; high-fat milk"),
    ("rathi", "Rathi", "cattle", ["rajasthan"], "Milch; among best milkers"),
    ("red_kandhari", "Red Kandhari", "cattle", ["maharashtra"], "Draught"),
    ("red_sindhi", "Red Sindhi", "cattle", [], "Milch; maintained on organized farms only"),
    ("sahiwal", "Sahiwal", "cattle", ["punjab", "rajasthan"], "Milch; premier dairy breed"),
    ("siri", "Siri", "cattle", ["sikkim", "west_bengal"], "Draught; of the Himalayan foothills"),
    ("tharparkar", "Tharparkar", "cattle", ["rajasthan"], "Milch; heat-tolerant desert breed"),
    ("umblachery", "Umblachery", "cattle", ["tamil_nadu"], "Draught; of the Cauvery delta"),
    ("vechur", "Vechur", "cattle", ["kerala"], "Smallest cattle breed; high-fat milk"),
    ("motu", "Motu", "cattle", ["odisha", "chhattisgarh", "andhra_pradesh"], "Draught"),
    ("ghumusari", "Ghumusari", "cattle", ["odisha"], "Draught"),
    ("binjharpuri", "Binjharpuri", "cattle", ["odisha"], "Draught"),
    ("khariar", "Khariar", "cattle", ["odisha"], "Draught"),
    ("pulikulam", "Pulikulam", "cattle", ["tamil_nadu"], "Draught; hardy of the south"),
    ("kosali", "Kosali", "cattle", ["chhattisgarh"], "Dual-purpose"),
    ("malnad_gidda", "Malnad Gidda", "cattle", ["karnataka"], "Small milch cow of the Western Ghats"),
    ("belahi", "Belahi", "cattle", ["haryana", "chandigarh"], "Milch"),
    ("gangatiri", "Gangatiri", "cattle", ["uttar_pradesh", "bihar"], "Milch"),
    ("badri", "Badri", "cattle", ["uttarakhand"], "Milch; of the hills"),
    ("lakhimi", "Lakhimi", "cattle", ["assam"], "Dual-purpose"),
    ("ladakhi", "Ladakhi", "cattle", ["jammu_kashmir"], "Milch; of Ladakh"),
    ("konkan_kapila", "Konkan Kapila", "cattle", ["maharashtra", "goa"], "Milch"),
    ("poda_thurpu", "Poda Thurpu", "cattle", ["telangana"], "Dual-purpose"),
    ("nari", "Nari", "cattle", ["rajasthan", "gujarat"], "Draught"),
    ("dagri", "Dagri", "cattle", ["gujarat"], "Draught"),
    ("thutho", "Thutho", "cattle", ["nagaland"], "Draught; of the Naga hills"),
    ("shweta_kapila", "Shweta Kapila", "cattle", ["goa"], "Milch"),
    ("himachali_pahari", "Himachali Pahari", "cattle", ["himachal_pradesh"], "Dual-purpose"),
    ("purnea", "Purnea", "cattle", ["bihar"], "Draught"),
    ("kathani", "Kathani", "cattle", ["maharashtra"], "Draught"),
    ("sanchori", "Sanchori", "cattle", ["rajasthan"], "Draught"),
    ("masilum", "Masilum", "cattle", ["meghalaya"], "Dual-purpose"),
    ("medini", "Medini", "cattle", ["jharkhand"], "Dual-purpose"),
    ("rohilkhandi", "Rohilkhandi", "cattle", ["uttar_pradesh"], "Draught"),
    # ---- cattle synthetic (3) ----
    ("frieswal", "Frieswal", "cattle", ["uttar_pradesh", "uttarakhand"], "Synthetic: HF x Sahiwal crossbred"),
    ("karan_fries", "Karan Fries", "cattle", ["haryana"], "Synthetic: HF x Tharparkar crossbred"),
    ("vrindavani", "Vrindavani", "cattle", ["uttar_pradesh"], "Synthetic: multi-breed crossbred"),
    # ---- buffalo (22) ----
    ("murrah", "Murrah", "buffalo", ["haryana"], "Milch; world-class dairy breed"),
    ("niliravi", "Nili Ravi", "buffalo", ["punjab"], "Milch"),
    ("bhadawari", "Bhadawari", "buffalo", ["uttar_pradesh", "madhya_pradesh"], "Milch; high fat"),
    ("mehsana", "Mehsana", "buffalo", ["gujarat"], "Milch; excellent dairy breed"),
    ("surti", "Surti", "buffalo", ["gujarat"], "Milch; medium fat ~8%"),
    ("jaffarabadi", "Jaffarabadi", "buffalo", ["gujarat"], "Milch; heavy breed"),
    ("nagpuri", "Nagpuri", "buffalo", ["maharashtra"], "Dual; large horns"),
    ("pandharpuri", "Pandharpuri", "buffalo", ["maharashtra"], "Milch; very high fat (~9%)"),
    ("marathwadi", "Marathwadi", "buffalo", ["maharashtra"], "Draught"),
    ("toda", "Toda", "buffalo", ["tamil_nadu"], "Draught; of the Nilgiris; diminutive"),
    ("banni", "Banni", "buffalo", ["gujarat"], "Milch"),
    ("chilika", "Chilika", "buffalo", ["odisha"], "Swamp-type; of the Chilika lake region"),
    ("kalahandi", "Kalahandi", "buffalo", ["odisha"], "Dual"),
    ("luit", "Luit (Swamp)", "buffalo", ["assam", "manipur"], "Swamp buffalo of the Brahmaputra valley"),
    ("bargur_buffalo", "Bargur", "buffalo", ["tamil_nadu"], "Milch; of the Bargur hills"),
    ("chhattisgarhi", "Chhattisgarhi", "buffalo", ["chhattisgarh"], "Dual"),
    ("gojri", "Gojri", "buffalo", ["punjab", "himachal_pradesh"], "Milch; of the Gujjar pastoralists"),
    ("dharwadi", "Dharwadi", "buffalo", ["karnataka"], "Milch"),
    ("manda", "Manda", "buffalo", ["odisha"], "Dual"),
    ("purnathadi", "Purnathadi", "buffalo", ["maharashtra"], "Milch"),
    ("manah", "Manah", "buffalo", ["assam"], "Swamp-type"),
    ("melghati", "Melghati", "buffalo", ["maharashtra"], "Milch; of the Melghat forests"),
    # ---- goat (43) ----
    ("attapady_black", "Attapady Black", "goat", ["kerala"], "Meat"),
    ("barbari", "Barbari", "goat", ["uttar_pradesh", "rajasthan"], "Small, prolific; meat and milk"),
    ("beetal", "Beetal", "goat", ["punjab"], "Large; meat and milk"),
    ("black_bengal", "Black Bengal", "goat", ["west_bengal"], "Meat; prolific, small"),
    ("changthangi", "Changthangi", "goat", ["jammu_kashmir"], "Pashmina-wool goat of Ladakh"),
    ("chegu", "Chegu", "goat", ["himachal_pradesh"], "Pashmina-wool goat of high altitude"),
    ("gaddi_goat", "Gaddi", "goat", ["himachal_pradesh"], "Rearing flocks of the Himalayan hills"),
    ("ganjam", "Ganjam", "goat", ["odisha"], "Meat; black with white patches"),
    ("gohilwadi", "Gohilwadi", "goat", ["gujarat"], "Meat"),
    ("jakhrana", "Jakhrana", "goat", ["rajasthan"], "Milk; high yields"),
    ("jamunapari", "Jamunapari", "goat", ["uttar_pradesh"], "Tall; milk and meat"),
    ("kanni_adu", "Kanni Adu", "goat", ["tamil_nadu"], "Meat"),
    ("kutchi_goat", "Kutchi", "goat", ["gujarat"], "Milk and meat of Kutch"),
    ("malabari", "Malabari", "goat", ["kerala"], "Dual-purpose; coastal"),
    ("marwari_goat", "Marwari", "goat", ["rajasthan"], "Meat"),
    ("mehsana_goat", "Mehsana", "goat", ["gujarat"], "Milk"),
    ("osmanabadi", "Osmanabadi", "goat", ["maharashtra"], "Meat breed of the drought tract"),
    ("sangamneri", "Sangamneri", "goat", ["maharashtra"], "Meat breed of the drought tract"),
    ("sirohi", "Sirohi", "goat", ["rajasthan", "gujarat"], "Milk and meat"),
    ("surti_goat", "Surti", "goat", ["gujarat"], "Meat"),
    ("zalawadi", "Zalawadi", "goat", ["gujarat"], "Meat"),
    ("konkan_kanyal", "Konkan Kanyal", "goat", ["maharashtra"], "Meat"),
    ("berari", "Berari", "goat", ["maharashtra"], "Meat"),
    ("pantja", "Pantja", "goat", ["uttarakhand", "uttar_pradesh"], "Meat; of the foothills"),
    ("teressa", "Teressa", "goat", ["andaman_nicobar"], "Meat; of the Teressa island"),
    ("kodi_adu", "Kodi Adu", "goat", ["tamil_nadu"], "Meat"),
    ("salem_black", "Salem Black", "goat", ["tamil_nadu"], "Meat"),
    ("sumi_ne", "Sumi-Ne", "goat", ["nagaland"], "Meat; of the Naga hills"),
    ("kahmi", "Kahmi", "goat", ["gujarat"], "Meat"),
    ("rohilkhandi_goat", "Rohilkhandi", "goat", ["uttar_pradesh"], "Meat"),
    ("assam_hill", "Assam Hill", "goat", ["assam", "meghalaya"], "Meat; of the NE hills"),
    ("bidri", "Bidri", "goat", ["karnataka"], "Meat"),
    ("nandidurga", "Nandidurga", "goat", ["karnataka"], "Meat"),
    ("bhakarwali_goat", "Bhakarwali", "goat", ["jammu_kashmir"], "Meat; of Kashmir"),
    ("sojat", "Sojat", "goat", ["rajasthan"], "Meat"),
    ("karauli", "Karauli", "goat", ["rajasthan"], "Meat"),
    ("gujari", "Gujari", "goat", ["rajasthan"], "Milk; of the Gujjar pastoralists"),
    ("anjori", "Anjori", "goat", ["chhattisgarh"], "Meat"),
    ("andamani_goat", "Andamani", "goat", ["andaman_nicobar"], "Meat"),
    ("chaugarkha", "Chaugarkha", "goat", ["uttarakhand"], "Meat"),
    ("bundelkhandi", "Bundelkhandi", "goat", ["uttar_pradesh", "madhya_pradesh"], "Meat"),
    ("palamu", "Palamu", "goat", ["jharkhand"], "Meat"),
    ("udaipuri", "Udaipuri", "goat", ["uttarakhand"], "Meat"),
    # ---- sheep (46) ----
    ("bhakarwal", "Bhakarwal", "sheep", ["jammu_kashmir"], "Wool; migratory"),
    ("changthangi_sheep", "Changthangi", "sheep", ["jammu_kashmir"], "Fine wool; of Ladakh"),
    ("gaddi", "Gaddi", "sheep", ["himachal_pradesh"], "Migratory hill flock; wool"),
    ("gurez", "Gurez", "sheep", ["jammu_kashmir"], "Carpet wool; of the Gurez valley"),
    ("karnah", "Karnah", "sheep", ["jammu_kashmir"], "Wool"),
    ("poonchi", "Poonchi", "sheep", ["jammu_kashmir"], "Wool"),
    ("rampur_bushair", "Rampur Bushair", "sheep", ["himachal_pradesh"], "Wool"),
    ("chokla", "Chokla", "sheep", ["rajasthan"], "Fine carpet wool; Marwari cross"),
    ("jaisalmeri", "Jaisalmeri", "sheep", ["rajasthan"], "Carpet wool; desert breed"),
    ("jalauni", "Jalauni", "sheep", ["uttar_pradesh", "madhya_pradesh"], "Mutton"),
    ("magra", "Magra", "sheep", ["rajasthan"], "Carpet wool"),
    ("malpura", "Malpura", "sheep", ["rajasthan"], "Mutton"),
    ("marwari", "Marwari", "sheep", ["rajasthan", "gujarat"], "Carpet wool; hardy desert breed"),
    ("muzaffarnagri", "Muzaffarnagri", "sheep", ["uttar_pradesh", "uttarakhand"], "Mutton; heavy carcass"),
    ("nali", "Nali", "sheep", ["rajasthan"], "Carpet wool; fine fleece"),
    ("patanwadi", "Patanwadi", "sheep", ["gujarat"], "Wool"),
    ("pugal", "Pugal", "sheep", ["rajasthan"], "Carpet wool; desert breed"),
    ("sonadi", "Sonadi", "sheep", ["rajasthan"], "Mutton and wool"),
    ("bellary", "Bellary", "sheep", ["karnataka"], "Mutton"),
    ("coimbatore", "Coimbatore", "sheep", ["tamil_nadu"], "Mutton"),
    ("deccani", "Deccani", "sheep", ["andhra_pradesh", "maharashtra"], "Mutton; hardy of the Deccan"),
    ("hassan", "Hassan", "sheep", ["karnataka"], "Mutton"),
    ("kenguri", "Kenguri", "sheep", ["karnataka"], "Mutton"),
    ("kilakarsal", "Kilakarsal", "sheep", ["tamil_nadu"], "Mutton"),
    ("madras_red", "Madras Red", "sheep", ["tamil_nadu"], "Mutton; red coat"),
    ("mandya", "Mandya", "sheep", ["karnataka"], "Mutton; of southern Karnataka"),
    ("mecheri", "Mecheri", "sheep", ["tamil_nadu"], "Mutton"),
    ("nellore", "Nellore", "sheep", ["andhra_pradesh"], "Mutton; tall, hardy"),
    ("nilgiri", "Nilgiri", "sheep", ["tamil_nadu"], "Fine wool; of the Nilgiri hills"),
    ("ramnad_white", "Ramnad White", "sheep", ["tamil_nadu"], "Mutton"),
    ("tiruchi_black", "Tiruchi Black", "sheep", ["tamil_nadu"], "Mutton"),
    ("vembur", "Vembur", "sheep", ["tamil_nadu"], "Mutton"),
    ("balangir", "Balangir", "sheep", ["odisha"], "Mutton"),
    ("bonpala", "Bonpala", "sheep", ["sikkim"], "Wool; of Sikkim"),
    ("chottanagpuri", "Chottanagpuri", "sheep", ["jharkhand"], "Mutton"),
    ("ganjam_sheep", "Ganjam", "sheep", ["odisha"], "Mutton"),
    ("shahbadi", "Shahbadi", "sheep", ["bihar"], "Mutton"),
    ("tibetan", "Tibetan", "sheep", ["arunachal_pradesh"], "Wool; of the Tibetan plateau"),
    ("garole", "Garole", "sheep", ["west_bengal"], "Prolific; of the Sundarbans"),
    ("katchaikatty_black", "Katchaikatty Black", "sheep", ["tamil_nadu"], "Mutton"),
    ("chevaadu", "Chevaadu", "sheep", ["tamil_nadu"], "Mutton"),
    ("kendrapada", "Kendrapada", "sheep", ["odisha"], "Mutton"),
    ("panchali", "Panchali", "sheep", ["gujarat"], "Mutton"),
    ("kajali", "Kajali", "sheep", ["punjab"], "Mutton"),
    ("macherla", "Macherla", "sheep", ["andhra_pradesh"], "Mutton"),
    ("kheri", "Kheri", "sheep", ["rajasthan"], "Mutton"),
    # ---- sheep synthetic (1) ----
    ("avishaan", "Avishaan", "sheep", ["rajasthan"], "Synthetic: Malpura x Avikalin (fine wool)"),
    # ---- pig (15) ----
    ("ghoongroo", "Ghoongroo", "pig", ["west_bengal"], "Small, prolific"),
    ("niang_megha", "Niang Megha", "pig", ["meghalaya"], "Indigenous"),
    ("agonda_goan", "Agonda Goan", "pig", ["goa"], "Indigenous"),
    ("tenyi_vo", "Tenyi Vo", "pig", ["nagaland"], "Indigenous"),
    ("nicobari_pig", "Nicobari", "pig", ["andaman_nicobar"], "Indigenous of the Nicobar islands"),
    ("doom", "Doom", "pig", ["assam"], "Registered indigenous pig of the Doom valley"),
    ("zovawk", "Zovawk", "pig", ["mizoram"], "Registered indigenous pig of Mizoram"),
    ("ghurrah", "Ghurrah", "pig", ["uttar_pradesh"], "Indigenous"),
    ("mali", "Mali", "pig", ["tripura"], "Indigenous"),
    ("purnea_pig", "Purnea", "pig", ["bihar", "jharkhand"], "Indigenous"),
    ("banda", "Banda", "pig", ["jharkhand"], "Indigenous"),
    ("manipuri_black", "Manipuri Black", "pig", ["manipur"], "Indigenous"),
    ("wak_chambil", "Wak Chambil", "pig", ["meghalaya"], "Indigenous"),
    ("andamani_pig", "Andamani", "pig", ["andaman_nicobar"], "Indigenous"),
    ("karkambi", "Karkambi", "pig", ["maharashtra"], "Indigenous"),
    # ---- chicken (21) ----
    ("ankaleshwar", "Ankaleshwar", "poultry", ["gujarat"], "Desi fowl"),
    ("aseel", "Aseel", "poultry", ["chhattisgarh", "odisha", "andhra_pradesh"], "Game fowl; strong, aggressive; used in selective breeding"),
    ("busra", "Busra", "poultry", ["gujarat", "maharashtra"], "Desi fowl"),
    ("chittagong", "Chittagong", "poultry", ["meghalaya", "tripura"], "Desi fowl"),
    ("danki", "Danki", "poultry", ["andhra_pradesh"], "Desi fowl"),
    ("daothigir", "Daothigir", "poultry", ["assam"], "Desi fowl"),
    ("ghagus", "Ghagus", "poultry", ["andhra_pradesh", "karnataka"], "Desi fowl"),
    ("harringhata_black", "Harringhata Black", "poultry", ["west_bengal"], "Desi fowl"),
    ("kadaknath", "Kadaknath", "poultry", ["madhya_pradesh"], "Black-fleshed fowl of Jhabua"),
    ("kalasthi", "Kalasthi", "poultry", ["andhra_pradesh"], "Desi fowl"),
    ("kashmir_favorolla", "Kashmir Favorolla", "poultry", ["jammu_kashmir"], "Desi fowl"),
    ("miri", "Miri", "poultry", ["assam"], "Desi fowl"),
    ("nicobari", "Nicobari", "poultry", ["andaman_nicobar"], "Native of the Nicobar islands"),
    ("punjab_brown", "Punjab Brown", "poultry", ["punjab", "haryana"], "Desi fowl"),
    ("tellichery", "Tellichery", "poultry", ["kerala"], "Desi fowl"),
    ("mewari_chicken", "Mewari", "poultry", ["rajasthan"], "Desi fowl"),
    ("kaunayen", "Kaunayen", "poultry", ["manipur"], "Desi fowl"),
    ("hansli", "Hansli", "poultry", ["odisha"], "Desi fowl"),
    ("uttara", "Uttara", "poultry", ["uttarakhand"], "Desi fowl"),
    ("aravali", "Aravali", "poultry", ["gujarat"], "Desi fowl"),
    ("mala", "Mala", "poultry", ["jharkhand"], "Desi fowl"),
    # ---- camel (9) ----
    ("bikaneri", "Bikaneri", "camel", ["rajasthan"], "Riding and cart camel"),
    ("jaisalmeri_camel", "Jaisalmeri Camel", "camel", ["rajasthan"], "Riding and cart camel"),
    ("jalori", "Jalori", "camel", ["rajasthan"], "Riding camel"),
    ("kutchi_camel", "Kutchi", "camel", ["gujarat"], "Dual-purpose camel of Kutch"),
    ("malvi_camel", "Malvi", "camel", ["madhya_pradesh"], "Draught camel"),
    ("marwari_camel", "Marwari", "camel", ["rajasthan"], "Riding and cart camel"),
    ("mewari_camel", "Mewari", "camel", ["rajasthan"], "Riding camel"),
    ("mewati_camel", "Mewati", "camel", ["rajasthan", "haryana"], "Draught camel"),
    ("kharai", "Kharai", "camel", ["gujarat"], "Swimming camel of the Kutch coast"),
    # ---- donkey (4) ----
    ("spiti_donkey", "Spiti", "donkey", ["himachal_pradesh"], "Pack donkey of the Spiti valley"),
    ("halari", "Halari", "donkey", ["gujarat"], "Pack donkey"),
    ("kachchhi_donkey", "Kachchhi", "donkey", ["gujarat"], "Pack donkey of Kutch"),
    ("ladakhi_donkey", "Ladakhi", "donkey", ["ladakh"], "Pack donkey of Ladakh"),
    # ---- horse (7) ----
    ("bhutia", "Bhutia", "horse", ["sikkim", "arunachal_pradesh"], "Mountain pony"),
    ("kathiawari", "Kathiawari", "horse", ["gujarat"], "Light horse; curved ears"),
    ("manipuri", "Manipuri", "horse", ["manipur"], "Polo pony"),
    ("marwari_horse", "Marwari", "horse", ["rajasthan"], "Light horse; inward-curved ears"),
    ("spiti", "Spiti", "horse", ["himachal_pradesh"], "Mountain pony"),
    ("zanskari", "Zanskari", "horse", ["jammu_kashmir"], "Mountain pony of Zanskar"),
    ("kachchhi_sindhi", "Kachchhi-Sindhi", "horse", ["gujarat", "rajasthan"], "Light horse"),
    # ---- yak (2) ----
    ("arunachali", "Arunachali", "yak", ["arunachal_pradesh"], "Yak of the Eastern Himalayas"),
    ("ladakhi_yak", "Ladakhi", "yak", ["ladakh"], "Yak of Ladakh"),
    # ---- mithun (1) ----
    ("nagami", "Nagami", "mithun", ["nagaland"], "Mithun of the Naga hills"),
    # ---- geese (2) ----
    ("kashmir_anz", "Kashmir Anz", "geese", ["jammu_kashmir"], "Domestic geese of Kashmir"),
    ("rajdigheli", "Rajdigheli", "geese", ["assam"], "Domestic geese of Assam"),
    # ---- duck (9) ----
    ("pati", "Pati", "duck", ["assam"], "Desi duck"),
    ("maithili", "Maithili", "duck", ["bihar"], "Desi duck"),
    ("andamani_duck", "Andamani", "duck", ["andaman_nicobar"], "Desi duck"),
    ("tripureswari", "Tripureswari", "duck", ["tripura"], "Desi duck"),
    ("kodo", "Kodo", "duck", ["jharkhand"], "Desi duck"),
    ("kudu", "Kudu", "duck", ["odisha"], "Desi duck"),
    ("kuttanad", "Kuttanad", "duck", ["kerala"], "Desi duck of the Kuttanad backwaters"),
    ("manipuri_duck", "Manipuri", "duck", ["manipur"], "Desi duck"),
    ("nagi", "Nagi", "duck", ["assam"], "Desi duck"),
]
# improved/exotic poultry and wool lines kept from v1 (industry-relevant, not NBAGR-registered breeds)
LIVESTOCK_IMPROVED = [
    ("gramapriya", "Gramapriya", "poultry", ["andhra_pradesh"], "ICAR-DPR dual-purpose; rural backyard"),
    ("giriraja", "Giriraja", "poultry", ["karnataka"], "Backyard dual-purpose; hardy"),
    ("naked_neck", "Naked Neck", "poultry", ["bihar", "nagaland"], "Native; heat-tolerant; bare neck"),
    ("white_leghorn", "White Leghorn", "poultry", [], "Exotic layer; basis of commercial egg production"),
    ("bharat_merino", "Bharat Merino", "sheep", ["jammu_kashmir", "himachal_pradesh"], "Crossbred fine wool (CSWRI)"),
    ("vanaraja", "Vanaraja", "poultry", ["andhra_pradesh", "west_bengal", "bihar", "jharkhand"], "ICAR-DPR dual-purpose; rural backyard"),
]
LIVESTOCK_DISEASES = [
    ("anthrax", "Anthrax", "Bacillus anthracis; zoonotic; notifiable"),
    ("black_quarter", "Black Quarter", "Clostridium chauvoei; cattle and buffalo"),
    ("classical_swine_fever", "Classical Swine Fever", "Pestivirus; pigs; notifiable"),
    ("blue_tongue", "Blue Tongue", "Orbivirus; sheep; vector-borne"),
]

# banned actives (CIB&RC gazette list) + major actives missing
PESTICIDES = [
    ("aldrin", "Aldrin", "banned"),
    ("dieldrin", "Dieldrin", "banned"),
    ("chlordane", "Chlordane", "banned"),
    ("heptachlor", "Heptachlor", "banned"),
    ("toxaphene", "Toxaphene", "banned"),
    ("endrin", "Endrin", "banned"),
    ("methyl_parathion", "Methyl Parathion", "banned"),
    ("lindane", "Lindane", "banned"),
    ("methoxychlor", "Methoxychlor", "banned"),
    ("nitrofen", "Nitrofen", "banned"),
    ("chlordimeform", "Chlordimeform", "banned"),
    ("ethyl_parathion", "Ethyl Parathion", "banned"),
    ("quinalphos", "Quinalphos", "active"),
    ("profenofos", "Profenofos", "active"),
    ("fipronil", "Fipronil", "active"),
    ("lambda_cyhalothrin", "Lambda-cyhalothrin", "active"),
    ("deltamethrin", "Deltamethrin", "active"),
    ("chlorantraniliprole", "Chlorantraniliprole", "active"),
    ("emamectin_benzoate", "Emamectin Benzoate", "active"),
    ("buprofezin", "Buprofezin", "active"),
]

FERTILIZERS = [
    ("fertilizers.ammonium_sulphate", "Ammonium Sulphate", "fertilizers.chemical", "Straight N fertilizer (21% N, 24% S)"),
    ("fertilizers.can", "Calcium Ammonium Nitrate", "fertilizers.chemical", "Straight N fertilizer (25% N); CAN"),
    ("fertilizers.compost", "Compost", "fertilizers.manures", "Decomposed organic matter; farm-made"),
    ("fertilizers.poultry_manure", "Poultry Manure", "fertilizers.manures", "High-N farmyard manure"),
    ("fertilizers.neem_cake", "Neem Cake", "fertilizers.manures", "Oilseed cake manure; nitrification inhibitor"),
    ("fertilizers.azospirillum", "Azospirillum", "fertilizers.bio", "N-fixing biofertilizer for non-legumes"),
    ("fertilizers.vam", "VAM (AM Fungi)", "fertilizers.bio", "Arbuscular mycorrhiza; P-uptake biofertilizer"),
    ("fertilizers.kmb", "Potash Mobilizing Bacteria", "fertilizers.bio", "K-release biofertilizer; Frateuria aurantia"),
]

WATER_BASINS = [
    ("barak", "Barak Basin", "Separate basin of the Brahmaputra system; NE states"),
    ("pennar", "Pennar Basin", "AP and Karnataka; rain-fed delta"),
    ("brahmani", "Brahmani-Baitarani Basin", "Odisha; combined basin"),
    ("subarnarekha", "Subarnarekha Basin", "Jharkhand, Odisha, West Bengal"),
    ("sabarmati", "Sabarmati Basin", "Gujarat and Rajasthan"),
    ("mahi", "Mahi Basin", "Gujarat, Rajasthan, Madhya Pradesh"),
    ("luni", "Luni Basin", "Rajasthan; ends in the Rann of Kutch"),
    ("periyar", "Periyar Basin", "Kerala; largest river of the state"),
    ("indus", "Indus Basin", "Shared basin; J&K, Ladakh, HP, Punjab in India"),
    ("ghaghar", "Ghaggar Basin", "Seasonal river of Haryana, Punjab, Rajasthan"),
    ("west_flowing_south_tapi", "West-flowing Rivers south of Tapi", "CWC basin group; Tapi-Tadri to Kanyakumari west coast rivers"),
    ("east_flowing_mahanadi_pennar", "East-flowing Rivers between Mahanadi and Pennar", "CWC basin group; includes Rushikulya, Vamsadhara, Nagavali"),
    ("east_flowing_pennar_kanyakumari", "East-flowing Rivers between Pennar and Kanyakumari", "CWC basin group; includes Palar, Ponnaiyar, Vaigai, Tambraparni"),
]

WEATHER = [
    ("la_nina", "La Nina", "Cooling of the equatorial Pacific; strengthens Indian monsoon"),
    ("western_disturbances", "Western Disturbances", "Winter rain in north-west India; Rabi irrigation support"),
    ("cyclone", "Cyclone", "Bay of Bengal and Arabian Sea storms; coastal risk"),
    ("heat_wave", "Heat Wave", "May-Jun; crop and livestock stress"),
    ("cold_wave", "Cold Wave", "Winter; frost damage to rabi crops"),
]

FORESTRY = [
    ("forestry.ntfp.gum_karaya", "Gum Karaya", "forestry.ntfp", "Sterculia urens; MP, Maharashtra, Chhattisgarh"),
    ("forestry.ntfp.chironji", "Chironji", "forestry.ntfp", "Buchanania lanzan; edible nut; central India"),
    ("forestry.agroforestry.casuarina", "Casuarina", "forestry.agroforestry", "Casuarina equisetifolia; pulp and poles; TN, AP"),
    ("forestry.agroforestry.melia_dubia", "Melia Dubia", "forestry.agroforestry", "Fast-growing timber; plywood; Karnataka, TN"),
    ("forestry.timber.deodar", "Deodar", "forestry.timber_species", "Cedrus deodara; Himalayan construction timber"),
    ("forestry.timber.rosewood", "East Indian Rosewood", "forestry.timber_species", "Dalbergia latifolia; fine furniture wood; southern forests"),
    ("forestry.timber.chir_pine", "Chir Pine", "forestry.timber_species", "Pinus roxburghii; resin and timber; Himachal, Uttarakhand"),
]

MACHINERY = [
    ("machinery.tractors.john_deere", "John Deere", "machinery.tractors", "Multinational tractor maker; Pune plant"),
    ("machinery.tractors.swaraj", "Swaraj", "machinery.tractors", "Indian brand (now Mahindra); Punjab origin"),
    ("machinery.tractors.escorts", "Escorts (Farmtrac)", "machinery.tractors", "Indian tractor maker; now Kubota"),
    ("machinery.tractors.new_holland", "New Holland", "machinery.tractors", "CNH brand; Noida plant"),
    ("machinery.implements.rotavator", "Rotavator", "machinery.implements", "Power-driven tillage; one-pass seedbed"),
    ("machinery.implements.disc_harrow", "Disc Harrow", "machinery.implements", "Secondary tillage; clod and weed control"),
    ("machinery.implements.seed_drill", "Seed Drill", "machinery.implements", "Row seeding with fertilizer placement"),
    ("machinery.implements.laser_leveler", "Laser Land Leveller", "machinery.implements", "Precision levelling; water saving"),
    ("machinery.implements.straw_reaper", "Straw Reaper", "machinery.implements", "Combine stubble harvest; residue management"),
    ("machinery.harvesting.thresher", "Thresher", "machinery.harvesting", "Grain separation from straw"),
    ("machinery.protection.power_sprayer", "Power Sprayer", "machinery.protection", "Engine-driven sprayer for larger areas"),
]

WEEDS = [
    ("plant_protection.weeds.asphodelus", "Asphodelus (Wild Onion Weed)", "Asphodelus tenuifolius; major weed of rabi wheat and mustard"),
    ("plant_protection.weeds.chenopodium", "Chenopodium (Bathua)", "Chenopodium album; rabi weed; also eaten as vegetable"),
]

SEEDS = [
    ("seeds.opv", "Open-Pollinated Varieties", "seeds.types", "Non-hybrid varieties; farmer-saved seed possible"),
]

# Official CIB&RC list: 'LIST OF PESTICIDES WHICH ARE BANNED, REFUSED REGISTRATION AND
# RESTRICTED IN USE (updated 31.07.2026)' from ppqs.gov.in. id, name, note.
BANNED_A = [  # I.A: banned for manufacture, import and use (49)
    ("alachlor", "Alachlor", "S.O. 3951(E) dated 08.08.2018"),
    ("aldicarb", "Aldicarb", "S.O. 682(E) dated 17.07.2001"),
    ("aldrin", "Aldrin", ""), ("bhc", "Benzene Hexachloride (BHC)", ""),
    ("benomyl", "Benomyl", "S.O. 3951(E) dated 08.08.2018"),
    ("calcium_cyanide", "Calcium Cyanide", ""),
    ("carbaryl", "Carbaryl", "S.O. 3951(E) dated 08.08.2018"),
    ("chlorbenzilate", "Chlorbenzilate", "S.O. 682(E) dated 17.07.2001"),
    ("chlordane", "Chlordane", ""), ("chlorfenvinphos", "Chlorfenvinphos", ""),
    ("copper_acetoarsenite", "Copper Acetoarsenite", ""),
    ("diazinon", "Diazinon", "S.O. 3951(E) dated 08.08.2018"),
    ("dbcp", "Dibromochloropropane (DBCP)", "S.O. 569(E) dated 25.07.1989"),
    ("dichlorvos", "Dichlorvos", "S.O. 3951(E) dated 08.08.2018"),
    ("dicofol", "Dicofol", "S.O. 4294(E) dated 03.10.2023"),
    ("dieldrin", "Dieldrin", "S.O. 682(E) dated 17.07.2001"),
    ("dinocap", "Dinocap", "S.O. 4294(E) dated 03.10.2023"),
    ("endosulfan", "Endosulfan", "Banned by Supreme Court order (2011 interim; final 10.01.2017)"),
    ("endrin", "Endrin", ""), ("ethyl_mercury_chloride", "Ethyl Mercury Chloride", ""),
    ("ethyl_parathion", "Ethyl Parathion", ""), ("edb", "Ethylene Dibromide (EDB)", "S.O. 682(E) dated 17.07.2001"),
    ("fenarimol", "Fenarimol", "S.O. 3951(E) dated 08.08.2018"),
    ("fenthion", "Fenthion", "S.O. 3951(E) dated 08.08.2018"),
    ("heptachlor", "Heptachlor", ""), ("lindane", "Lindane (Gamma-HCH)", ""),
    ("linuron", "Linuron", "S.O. 3951(E) dated 08.08.2018"),
    ("maleic_hydrazide", "Maleic Hydrazide", "S.O. 682(E) dated 17.07.2001"),
    ("menazon", "Menazon", ""), ("methomyl", "Methomyl", "S.O. 4294(E) dated 03.10.2023"),
    ("methoxy_ethyl_mercury_chloride", "Methoxy Ethyl Mercury Chloride", "S.O. 3951(E) dated 08.08.2018"),
    ("methyl_parathion", "Methyl Parathion", "S.O. 3951(E) dated 08.08.2018"),
    ("metoxuron", "Metoxuron", ""), ("nitrofen", "Nitrofen", ""),
    ("paraquat", "Paraquat Dimethyl Sulphate", ""),
    ("pcnb", "Pentachloro Nitrobenzene (PCNB)", "S.O. 569(E) dated 25.07.1989"),
    ("pentachlorophenol", "Pentachlorophenol", ""), ("phenyl_mercury_acetate", "Phenyl Mercury Acetate", ""),
    ("phorate", "Phorate", "S.O. 3951(E) dated 08.08.2018"),
    ("phosphamidon", "Phosphamidon", "S.O. 3951(E) dated 08.08.2018"),
    ("sodium_cyanide", "Sodium Cyanide", "Banned for insecticidal use only; S.O. 3951(E) dated 08.08.2018"),
    ("sodium_methane_arsonate", "Sodium Methane Arsonate", ""),
    ("tetradifon", "Tetradifon", ""), ("thiometon", "Thiometon", "S.O. 3951(E) dated 08.08.2018"),
    ("toxaphene", "Toxaphene (Camphechlor)", "S.O. 569(E) dated 25.07.1989"),
    ("triazophos", "Triazophos", "S.O. 3951(E) dated 08.08.2018"),
    ("tridemorph", "Tridemorph", "S.O. 3951(E) dated 08.08.2018"),
    ("tca", "Trichloroacetic Acid (TCA)", "S.O. 682(E) dated 17.07.2001"),
    ("trichlorfon", "Trichlorfon", "S.O. 3951(E) dated 08.08.2018"),
]
BANNED_B = [  # I.B: banned for use, manufacture continued for export (5)
    ("captafol", "Captafol 80% Powder", "S.O. 679(E) dated 17.07.2001"),
    ("nicotine_sulfate", "Nicotine Sulfate", "S.O. 325(E) dated 11.05.1992"),
]
WITHDRAWN = [  # I.C: withdrawn (8)
    ("dalapon", "Dalapon", ""), ("ferbam", "Ferbam", ""), ("formothion", "Formothion", ""),
    ("nickel_chloride", "Nickel Chloride", ""), ("pdcb", "Paradichlorobenzene (PDCB)", ""),
    ("simazine", "Simazine", ""), ("sirmate", "Sirmate", "S.O. 2485(E) dated 24.09.2014"),
    ("warfarin", "Warfarin", "S.O. 915(E) dated 15.06.2006"),
]
REFUSED = [  # II: refused registration (18)
    ("d_2_4_5_t", "2,4,5-T", ""), ("ammonium_sulphamate", "Ammonium Sulphamate", ""),
    ("azinphos_ethyl", "Azinphos Ethyl", ""), ("azinphos_methyl", "Azinphos Methyl", ""),
    ("binapacryl", "Binapacryl", ""), ("calcium_arsenate", "Calcium Arsenate", ""),
    ("carbophenothion", "Carbophenothion", ""), ("chinomethionate", "Chinomethionate (Morestan)", ""),
    ("dicrotophos", "Dicrotophos", ""), ("epn", "EPN", ""),
    ("fentin_acetate", "Fentin Acetate", ""), ("fentin_hydroxide", "Fentin Hydroxide", ""),
    ("lead_arsenate", "Lead Arsenate", ""), ("leptophos", "Leptophos (Phosvel)", ""),
    ("mephosfolan", "Mephosfolan", ""), ("mevinphos", "Mevinphos (Phosdrin)", ""),
    ("disulfoton", "Thiodemeton / Disulfoton", ""), ("vamidothion", "Vamidothion", ""),
]
RESTRICTED_NEW = [  # III: restricted for use (16; 7 already exist -> reparented below)
    ("aluminium_phosphide", "Aluminium Phosphide", "Fumigation only under Govt/PCO supervision; 3g tube packs banned (S.O. 677(E) dated 17.07.2001)"),
    ("carbofuran", "Carbofuran", "Only 3% CG formulation allowed; S.O. 4294(E) dated 03.10.2023"),
    ("dazomet", "Dazomet", "Use not permitted on Tea; S.O. 3006(E) dated 31.12.2008"),
    ("dimethoate", "Dimethoate", "Banned on fruits/vegetables consumed raw; S.O. 4294(E) dated 03.10.2023"),
    ("fenitrothion", "Fenitrothion", "Banned in agriculture except locust control in desert area; S.O. 706(E) dated 03.05.2007"),
    ("malathion", "Malathion", "Banned on sorghum, pea, soybean, castor, sunflower, bhindi, brinjal, cauliflower, radish, turnip, tomato, apple, mango, grape; S.O. 4294(E) dated 03.10.2023"),
    ("methyl_bromide", "Methyl Bromide", "Fumigation only under Govt/PCO supervision; G.S.R. 371(E) dated 20.05.1999"),
    ("oxyfluorfen", "Oxyfluorfen", "Banned on potato and groundnut; S.O. 4294(E) dated 03.10.2023"),
    ("trifluralin", "Trifluralin", "Only wheat use allowed; S.O. 3951(E) dated 08.08.2018"),
]
REPARENT = {  # existing actives -> correct official status
    "pesticides.banned.ddt": ("pesticides.restricted", "Restricted to public-health use (10,000 MT/yr); use in agriculture withdrawn; S.O. 295(E)/378(E)"),
    "pesticides.chlorpyrifos": ("pesticides.restricted", "Banned on ber, citrus and tobacco; S.O. 4294(E) dated 03.10.2023"),
    "pesticides.cypermethrin": ("pesticides.restricted", "3% smoke generator only via pest control operators"),
    "pesticides.mancozeb": ("pesticides.restricted", "Banned on guava, jowar and tapioca; S.O. 4294(E) dated 03.10.2023"),
    "pesticides.monocrotophos": ("pesticides.restricted", "Banned on vegetables; 36% SL discontinued; S.O. 1482(E)/4294(E)"),
    "pesticides.quinalphos": ("pesticides.restricted", "Banned on jute, cardamom and sorghum; S.O. 4294(E) dated 03.10.2023"),
    "pesticides.endosulfan": ("pesticides.banned", "Banned by Supreme Court order (2011 interim; final 10.01.2017)"),
    "pesticides.paraquat": ("pesticides.banned", "Paraquat Dimethyl Sulphate banned for manufacture, import and use"),
}
REMOVE_IDS = ["pesticides.methoxychlor", "pesticides.chlordimeform",
              "pesticides.banned.bhc"]  # not on the official list / legacy id replaced


UTS = {"jammu_kashmir", "andaman_nicobar", "ladakh", "chandigarh", "delhi",
       "dadra", "daman", "puducherry", "lakshadweep"}

SPECIES = {"cattle": "livestock.cattle", "buffalo": "livestock.buffalo",
           "goat": "livestock.goat", "sheep": "livestock.sheep",
           "poultry": "livestock.poultry", "camel": "livestock.camel",
           "pig": "livestock.pig", "horse": "livestock.horse",
           "donkey": "livestock.donkey", "yak": "livestock.yak",
           "mithun": "livestock.mithun", "geese": "livestock.geese",
           "duck": "livestock.duck"}

def build_entity(eid, name, parent, source, attributes, states, loc_predicate="grown_in"):
    rels = [{"predicate": "is_a", "object": parent}]
    for s in states:
        obj = s if s.startswith("location.") else (
            "location.uts." + s if s in UTS else "location.states." + s)
        rels.append({"predicate": loc_predicate, "object": obj})
    if not states:
        rels.append({"predicate": "found_in", "object": "location.india"})
    attrs = dict(attributes)
    if "aliases" in attrs:
        aliases = attrs.pop("aliases")
    else:
        aliases = []
    return {"id": eid, "name": name, "type": "entity", "domain": parent.split(".")[0],
            "attributes": attrs, "relations": rels,
            "source": {"id": source, "url": SRC[source]}, "aliases": aliases}


def main():
    existing = {}
    for path in DATA.glob("*.json"):
        for e in json.loads(path.read_text(encoding="utf-8")).get("entities", []):
            existing[e["id"]] = e

    added = 0
    for spec in NEW:
        eid, name, parent, src, attrs, states = spec
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, parent, src, attrs, states)
        added += 1

    # species anchors for breeds added from the full NBAGR registry
    for sid, name in [("livestock.horse", "Horse (Equine)"), ("livestock.donkey", "Donkey"),
                      ("livestock.geese", "Geese"), ("livestock.duck", "Duck")]:
        if sid in existing:
            continue
        existing[sid] = build_entity(sid, name, "livestock", "nbragr",
                                     {"note": "Species anchor (NBAGR registered breeds)"}, [])
        added += 1

    for lid, name, cat, states, note in LIVESTOCK + LIVESTOCK_IMPROVED:
        eid = f"livestock.breed.{lid}"
        if eid in existing:
            # registry is authoritative: overwrite location relations with official home tract
            e = existing[eid]
            e["relations"] = [r for r in e["relations"] if r["predicate"] not in ("grown_in", "found_in")]
            for s in states:
                obj = s if s.startswith("location.") else (
                    "location.uts." + s if s in UTS else "location.states." + s)
                e["relations"].append({"predicate": "grown_in", "object": obj})
            if not states:
                e["relations"].append({"predicate": "found_in", "object": "location.india"})
            e["attributes"]["species"] = cat
            e["source"] = {"id": "nbragr", "url": SRC["nbragr"]}
            continue
        parent = SPECIES[cat]
        existing[eid] = build_entity(eid, name, parent, "nbragr",
                                     {"note": note, "species": cat}, states)
        added += 1

    for lid, name, note in LIVESTOCK_DISEASES:
        eid = f"livestock.disease.{lid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "livestock.diseases", "nbragr",
                                     {"note": note}, [])
        added += 1

    for pid, name, kind in PESTICIDES:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        if kind == "banned":
            e = build_entity(eid, name, "pesticides.banned", "cibrc-ban",
                             {"note": "Banned for manufacture, sale and use in India (CIB&RC gazette)"}, [],
                             loc_predicate="banned_in")
            e["relations"] = [{"predicate": "is_a", "object": "pesticides.banned"},
                              {"predicate": "banned_in", "object": "location.india"}]
        else:
            e = build_entity(eid, name, "pesticides.classes", "cibrc",
                             {"class": "Insecticide"}, [])
        existing[eid] = e
        added += 1

    for fid, name, parent, note in FERTILIZERS:
        if fid in existing:
            continue
        existing[fid] = build_entity(fid, name, parent, "dacfw", {"note": note}, [])
        added += 1

    for bid, name, note in WATER_BASINS:
        eid = f"water.basin.{bid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "water.basins", "cwc", {"note": note}, [])
        added += 1

    for wid, name, note in WEATHER:
        eid = f"weather.{wid}"
        if eid in existing:
            continue
        parent = "weather.extreme_events" if wid in ("cyclone", "heat_wave", "cold_wave") else "weather.monsoon"
        existing[eid] = build_entity(eid, name, parent, "imd", {"note": note}, [])
        added += 1

    for fid, name, parent, note in FORESTRY:
        if fid in existing:
            continue
        existing[fid] = build_entity(fid, name, parent, "icar", {"note": note}, [])
        added += 1

    for mid, name, parent, note in MACHINERY:
        if mid in existing:
            continue
        existing[mid] = build_entity(mid, name, parent, "icar", {"note": note}, [])
        added += 1

    for wid, name, note in WEEDS:
        if wid in existing:
            continue
        existing[wid] = build_entity(wid, name, "plant_protection.weeds", "tnau-agritech", {"note": note}, [])
        added += 1

    for sid, name, parent, note in SEEDS:
        if sid in existing:
            continue
        existing[sid] = build_entity(sid, name, parent, "seednet", {"note": note}, [])
        added += 1

    # ---- official CIB&RC banned/refused/restricted classification (ppqs.gov.in, 31.07.2026) ----
    status_cats = {
        "pesticides.banned": "Banned for manufacture, import and use in India (49 actives per CIB&RC gazette list)",
        "pesticides.banned_export": "Banned for use in India; manufacture continued for export (5)",
        "pesticides.withdrawn": "Withdrawn from registration (8; may be reinstated if data generated)",
        "pesticides.refused": "Refused registration in India (18)",
        "pesticides.restricted": "Restricted for use in the country (16)",
    }
    for cid, note in status_cats.items():
        if cid in existing:
            continue
        existing[cid] = {"id": cid, "name": cid.split(".")[-1].replace("_", " ").title(),
                         "type": "category", "domain": "pesticides",
                         "attributes": {"note": note}, "relations": [
                             {"predicate": "is_a", "object": "pesticides"},
                             {"predicate": "part_of", "object": "pesticides"}],
                         "source": {"id": "cibrc-ban", "url": SRC["cibrc-ban"]}}
        added += 1

    for pid, name, note in BANNED_A:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "pesticides.banned", "cibrc-ban",
                                     {"note": ("Banned for manufacture, import and use. " + note).strip()}, [],
                                     loc_predicate="banned_in")
        existing[eid]["relations"] = [{"predicate": "is_a", "object": "pesticides.banned"},
                                      {"predicate": "banned_in", "object": "location.india"}]
        added += 1

    for pid, name, note in BANNED_B:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "pesticides.banned_export", "cibrc-ban",
                                     {"note": ("Banned for use in India; manufacture for export only. " + note).strip()}, [],
                                     loc_predicate="banned_in")
        existing[eid]["relations"] = [{"predicate": "is_a", "object": "pesticides.banned_export"},
                                      {"predicate": "banned_in", "object": "location.india"}]
        added += 1

    for pid, name, note in WITHDRAWN:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "pesticides.withdrawn", "cibrc-ban",
                                     {"note": ("Registration withdrawn. " + note).strip()}, [])
        added += 1

    for pid, name, note in REFUSED:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "pesticides.refused", "cibrc-ban",
                                     {"note": "Registration refused in India. " + note}, [])
        added += 1

    for pid, name, note in RESTRICTED_NEW:
        eid = f"pesticides.{pid}"
        if eid in existing:
            continue
        existing[eid] = build_entity(eid, name, "pesticides.restricted", "cibrc-ban", {"note": note}, [])
        added += 1

    # ---- registered active ingredients (CIB&RC 9(3) list, 371 actives, ppqs.gov.in) ----
    actives_path = ROOT / "data" / "_raw" / "cibrc" / "registered_actives_9_3.json"
    if actives_path.exists():
        registered = json.loads(actives_path.read_text(encoding="utf-8"))
        if "pesticides.registered_actives" not in existing:
            existing["pesticides.registered_actives"] = {
                "id": "pesticides.registered_actives", "name": "Registered Active Ingredients",
                "type": "category", "domain": "pesticides",
                "attributes": {"note": f"All {len(registered)} active ingredients registered for use in India under Section 9(3) of the Insecticides Act, 1968 (CIB&RC list)"},
                "relations": [{"predicate": "is_a", "object": "pesticides"},
                              {"predicate": "part_of", "object": "pesticides"},
                              {"predicate": "registered_in", "object": "institutions.cibrc"}],
                "source": {"id": "cibrc-9-3", "url": SRC.get("cibrc-9-3", "https://www.ppqs.gov.in/divisions/cib-rc/registered-products")}}
            added += 1
        for name in registered:
            pid = "pesticides." + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            if pid in existing:
                continue
            existing[pid] = build_entity(pid, name, "pesticides.registered_actives", "cibrc-9-3",
                                         {"note": "Registered active ingredient (CIB&RC 9(3) list)"}, [])
            added += 1

    # ---- MSP coverage: official 22 mandated crops (commodity list only, stable) ----
    MSP_CROPS = {  # crop id -> grade/type note; prices change yearly and are NOT stored
        "crops.rice": "paddy (common)", "crops.wheat": "wheat", "crops.maize": "maize",
        "crops.jowar": "jowar (hybrid)", "crops.bajra": "bajra", "crops.ragi": "ragi",
        "crops.barley": "barley", "crops.gram": "gram (chickpea)", "crops.pigeon_pea": "tur/arhar",
        "crops.green_gram": "moong", "crops.black_gram": "urad", "crops.lentil": "masur (lentil)",
        "crops.mustard": "rapeseed-mustard", "crops.groundnut": "groundnut",
        "crops.sunflower": "sunflower", "crops.soybean": "soybean (yellow)", "crops.sesame": "sesamum",
        "crops.niger": "nigerseed", "crops.safflower": "safflower", "crops.cotton": "cotton (medium staple)",
        "crops.jute": "raw jute", "crops.coconut": "copra (milling)",
    }
    if "market.msp" in existing:
        msp = existing["market.msp"]
        msp["attributes"]["crops"] = ("22 mandated commodities: "
                                      + ", ".join(v for v in MSP_CROPS.values())
                                      + "; sugarcane paid via FRP (separate from MSP)")
        msp["attributes"].pop("example", None)  # prices change yearly; never stored
        covered = {r["object"] for r in msp["relations"] if r["predicate"] == "recommended_for"}
        for cid in MSP_CROPS:
            if cid not in covered:
                msp["relations"].append({"predicate": "recommended_for", "object": cid})

    for eid, (parent, note) in REPARENT.items():
        if eid not in existing:
            continue
        e = existing[eid]
        e["relations"] = [r for r in e["relations"] if r.get("predicate") != "is_a"]
        e["relations"].insert(0, {"predicate": "is_a", "object": parent})
        if note not in e["attributes"].get("note", ""):
            e["attributes"]["note"] = e["attributes"].get("note", "") + "; " + note
        e["source"] = {"id": "cibrc-ban", "url": SRC["cibrc-ban"]}

    # substances in BOTH section A (banned) and B (manufacture for export continues)
    for pid in ("dichlorvos", "phorate", "triazophos"):
        eid = f"pesticides.{pid}"
        if eid in existing and not any(r.get("object") == "pesticides.banned_export" for r in existing[eid]["relations"]):
            existing[eid]["relations"].append({"predicate": "is_a", "object": "pesticides.banned_export"})
            if "manufacture for export continues" not in existing[eid]["attributes"].get("note", ""):
                existing[eid]["attributes"]["note"] = existing[eid]["attributes"].get("note", "") + "; manufacture for export continues (S.O. 1196(E) dated 20.03.2020)"

    # captafol: in section B (export) AND the restricted list (foliar spray banned, seed dresser only)
    if "pesticides.captafol" in existing:
        if not any(r.get("object") == "pesticides.restricted" for r in existing["pesticides.captafol"]["relations"]):
            existing["pesticides.captafol"]["relations"].append({"predicate": "is_a", "object": "pesticides.restricted"})
        if "seed-dresser use only" not in existing["pesticides.captafol"]["attributes"].get("note", ""):
            existing["pesticides.captafol"]["attributes"]["note"] = existing["pesticides.captafol"]["attributes"].get("note", "") + "; foliar spray banned, seed-dresser use only (S.O. 569(E) dated 25.07.1989)"

    for rid in REMOVE_IDS:
        existing.pop(rid, None)

    # not on the NBAGR registry (Kachchhi camel is a donkey breed; Agonhi pig never registered)
    for rid in ("livestock.breed.kachchhi", "livestock.breed.agonhi"):
        existing.pop(rid, None)

    # update banned category count
    if "pesticides.banned" in existing:
        existing["pesticides.banned"]["attributes"]["banned_count"] = len(BANNED_A)

    # chilli: canonical parent = spices only
    chili = existing["crops.chili"]
    chili["relations"] = [r for r in chili["relations"] if r["object"] != "crops.vegetables"]
    if "canonical parent" not in chili["attributes"].get("note", ""):
        chili["attributes"]["note"] = chili["attributes"].get("note", "") + "; dual-use (green vegetable and dried spice), canonical parent: Spices"
    # strip agrovocId everywhere (AGROVOC = aliases only)
    for e in existing.values():
        e.pop("agrovocId", None)

    # location anchor rule: every entity needs >=1 location relation
    fixed = 0
    for e in existing.values():
        if e["type"] != "entity":
            continue
        if any(r["predicate"] in ("found_in", "grown_in", "practiced_in", "produced_in", "banned_in", "registered_in")
               for r in e.get("relations", [])):
            continue
        e["relations"].append({"predicate": "found_in", "object": "location.india"})
        fixed += 1

    # write back by file: every entity goes to data/<domain>.json
    for path in sorted(DATA.glob("*.json")):
        dom = path.stem
        entities = [e for e in existing.values() if e["domain"] == dom]
        entities.sort(key=lambda e: e["id"])
        if entities:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["entities"] = entities
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"added {added} entities, anchored {fixed} entities, chilli fixed, agrovocId stripped")


if __name__ == "__main__":
    main()
