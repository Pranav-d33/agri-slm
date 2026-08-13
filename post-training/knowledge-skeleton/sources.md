# Source Registry

Every fact in this skeleton traces to a source below. `id` is referenced from entity/relation `source` fields. Only deterministic sources: government portals, ICAR institutes, state agricultural universities, commodity boards, official statistics. No news snippets, no LLM content.

## Status legend
- `ready` — verified fetchable from this machine
- `mirror` — primary site blocked/unavailable; use listed mirror
- `manual` — data encoded by hand from public documents; URL cites the document

| id | name | domain | url | license/notes | status |
|----|------|--------|-----|----------------|--------|
| agrovoc | AGROVOC (FAO) | all | https://agrovoc.fao.org/browse | CC BY 4.0-ish; already extracted in `agrovoc_entities_filtered.json` | ready |
| tnau-agritech | TNAU Agritech Portal | crops, soil, protection | https://agritech.tnau.ac.in/ | State agri university; educational use | ready |
| icar | ICAR (Indian Council of Agricultural Research) | all | https://icar.org.in/ | Govt of India | manual |
| fsi-isfr | FSI India State of Forest Report 2023 | forestry | https://fsi.nic.in/isfr-2023 | Govt of India; Vol2 state-wise Champion & Seth forest-type tables (used for forest-type → state mapping) | ready |
| nbragr | ICAR-NBAGR (Animal Genetics Resources) | livestock | https://nbagr.res.in/ | Breed registry (240 registered breeds); nbagr.icar.gov.in unreachable, .res.in mirror used; horse via Wayback snapshot 2024-10 | ready |
| dahd-census | DAHD 20th Livestock Census 2019 | livestock | https://dahd.nic.in/ | Govt of India statistics | manual |
| cibrc | CIB&RC (Pesticides Registration) | pesticides | https://cibrc.gov.in/ | Govt of India; site intermittently down | mirror |
| cibrc-ban | CIB&RC banned/restricted list | pesticides | https://www.ppqs.gov.in/divisions/cib-rc/registered-products | Official 'Banned, Refused Registration and Restricted in Use' list (updated 31.07.2026) | ready |
| cibrc-9-3 | CIB&RC 9(3) registered actives | pesticides | https://www.ppqs.gov.in/divisions/cib-rc/registered-products | 371 registered active ingredients; extracted to data/_raw/cibrc/registered_actives_9_3.json | ready |
| ppqs | PPQS (Plant Protection & Quarantine) | pesticides, protection | https://ppqs.gov.in/ | Govt of India | manual |
| dacfw | DAC&FW (Agriculture & Farmers Welfare) | market, schemes, crops | https://agricoop.nic.in/ | Govt of India | manual |
| des | DES (Economics & Statistics, DAC&FW) crop APY reports | crops | https://data.desagri.gov.in/website/crops-apy-report-web | Govt of India; state-wise area/production via printdraft report (2000-2013); used for Moth/Khesari/Horse-gram/Cowpea/Ragi/Small-millets + 27 field crops (rice/wheat/maize/jowar/bajra/barley/gram/pulses/oilseeds/cotton/jute/mesta/sugarcane/tobacco); rice uses Kharif+Autumn+Winter+Summer union | ready |
| agridashboard | Agristack/DAC dashboard | market, crops | https://agridashboard.dac.gov.in/ | Govt of India | manual |
| apeda | APEDA (organic NPOP) | organic, market | https://apeda.gov.in/ | Govt of India | manual |
| pgsindia | PGS-India | organic | https://pgsindia-nocof.net/ | Govt of India | manual |
| nhb | National Horticulture Board | crops | https://nhb.gov.in/ | Govt of India | manual |
| imd | India Meteorological Department | weather | https://mausam.imd.gov.in/ | Govt of India | manual |
| nidm | NIC LGD (Local Government Directory) | location | https://lgdirectory.gov.in/ | Official districts/ULBs; 784 current districts + LGD codes via DWR API (data/_raw/lgd/); census-2011 counts retained per state | ready |
| census2011 | Census of India 2011 (via census2011.co.in) | location | https://www.census2011.co.in/district.php | Official census data mirror | mirror |
| pc-zones | Planning Commission agro-climatic zones | weather | https://www.niti.gov.in/ | 15 zones classification | manual |
| fssai | FSSAI | pesticides, market | https://www.fssai.gov.in/ | Food safety regulator | manual |
| nddb | NDDB (dairy) | livestock | https://www.nddb.coop/ | Dairy statistics | manual |
| nfdb | NFDB (fisheries) | fisheries | https://nfdb.gov.in/ | Govt of India | manual |
| ciba | ICAR-CIBA (Central Institute of Brackishwater Aquaculture) | fisheries | https://www.ciba.res.in/ | ICAR institute; brackishwater/shrimp aquaculture mandate, coastal producer states | ready |
| cmfri | CMFRI | fisheries | https://www.cmfri.org.in/ | ICAR institute | manual |
| dahd-fisheries | DAHDF Handbook on Fisheries Statistics 2023 (Dept of Fisheries) | fisheries | https://dof.gov.in/sites/default/files/2024-06/Handbook.pdf | Govt of India; authoritative state-wise inland & marine fish production. Live dof.gov.in 404s post site migration; fetched via Wayback snapshot of the same canonical URL (20241126) | mirror |
| cmfri-landings | CMFRI "Marine Fish Landings in India 2025" (Booklet Series No. 47/2026) | fisheries | https://eprints.cmfri.org.in/19715/1/Marine%20Fish%20Landings%20in%20India%20-%202025.pdf | ICAR-CMFRI; state-wise & district-wise marine landings for 2025 | ready |
| agmarknet | AGMARKNET | market | https://agmarknet.gov.in/ | Mandi prices | manual |
| agmarknet-api | AGMARKNET 2.0 public API | market | https://api.agmarknet.gov.in/v1/dashboard-data/ | Govt of India; daily mandi price+arrival+MSP snapshot (no auth) | manual |
| enam | e-NAM | market | https://www.enam.gov.in/ | Govt of India | manual |
| amfi | AMFI (APMC) | market | https://amfi.gov.in/ | Mandi regulation | manual |
| seednet | Seednet India | seeds | https://seednet.gov.in/ | Govt of India seed info | manual |
| nsc | National Seeds Corporation | seeds | https://www.indiaseeds.com/ | Govt of India | manual |
| india-wris | India-WRIS (water resources) | water | https://indiawris.gov.in/ | Govt of India | manual |
| cwc | Central Water Commission | water | https://cwc.gov.in/ | Govt of India; Water & Related Statistics 2023 Table 1.5(d) basin→state mapping (used for all basin relations) | ready |
| cbse-soils | ICAR soil classification (8 major types) | soil | https://icar.org.in/ | Standard ICAR classification | manual |
| ncaer | NCAER agri data | market | https://www.ncaer.org/ | Research institute | manual |
| iari | ICAR-IARI | crops, soil | https://iari.res.in/ | ICAR institute | manual |
| iihr | ICAR-IIHR (horticulture) | crops | https://iihr.res.in/ | ICAR institute | manual |
| crijaf | ICAR-CRIJAF (jute) | crops | https://crijaf.icar.gov.in/ | ICAR institute | manual |
| cicr | ICAR-CICR (cotton) | crops | https://cicr.org.in/ | ICAR institute | manual |
| spicesboard | Spices Board India | crops | https://www.indianspices.com/ | Commodity board | manual |
| teaboard | Tea Board India | crops | https://www.teaboard.gov.in/ | Commodity board | manual |
| coffeeboard | Coffee Board India | crops | https://coffeeboard.gov.in/ | Commodity board | manual |
| rubbersboard | Rubber Board India | crops | https://rubberboard.org.in/ | Commodity board | manual |
| sugarfed | Sugar industry (ISMA) | crops, market | https://www.indiansugar.com/ | Industry association statistics | manual |
| fci | Food Corporation of India | market | https://fci.gov.in/ | Govt of India | manual |
| bharat | Bharat Agri/Horticulture portal | crops | https://www.bharatagri.gov.in/ | Govt of India | manual |
| kyh | Krishi Yojana (KVK data) | schemes | https://kvk.icar.gov.in/ | ICAR KVK network | manual |
| wbf | World Bank agri India | market | https://www.worldbank.org/ | Statistics | manual |
| indiastat | IndiaStat (mirror of official stats) | market | https://www.indiastat.com/ | Mirror of govt statistics | manual |
| cib-pdf | CIB&RC registered pesticide PDF mirror | pesticides | https://ppqs.gov.in/sites/default/files/registered_pesticides.pdf | Official list mirror | mirror |
| nigms | NIGMS/Agro-chemical bans gazette | pesticides | https://egazette.gov.in/ | Gazette of India | manual |
| hsag | HSAG 2024: Horticultural Statistics at a Glance 2024, DAC&FW | crops | https://www.nhb.gov.in/statistics/Publication/Horticulture%20Statistics%20at%20a%20Glance-2024.pdf | Official govt publication; state-wise A/P/Y tables 7.3.1-7.3.53 (fruits, veg, plantation, spices, flowers, mushroom) + 7.2.5 aromatics/medicinal + 7.2.8 honey + Ch4 Value of Output tables; source of grown_in/found_in/produced_in for ~50 crops + flowers/aromatics/mushroom categories + honey | ready |
| hsag-2021 | HSAG 2021: Horticultural Statistics at a Glance 2021, DAC&FW | crops | https://agriwelfare.gov.in/Documents/Horticultural_Statistics_at__Glance_2021.pdf | Official govt publication; corroborates NAD Ch4 tables; no state-wise per-crop tables beyond NAD | ready |
| spicesboard-aps | Spices Board state/item-wise Area & Production of Spices 2024-25 | crops | https://www.indianspices.com/sites/default/files/all%20state%20item%20wise%20area%20and%20production%20of%20spices%202024-25%20web.pdf | Commodity board; Cardamom Small/Large, Cinnamon, Clove producing states | ready |
| narp-zones | Venkateswarlu et al. "Agro-climatic Zones of India", Annals of Arid Zone 35(1):1-7 (1996) | location, weather, soil | https://epubs.icar.org.in/ejournal/index.php/AAZ/article/view/65198 | ICAR/Central Arid Zone Research Institute journal paper; Table 1 = official state-wise NARP zone registry with rainfall and dominant soils; basis of the 127 NARP zone grid (Rajya Sabha 2021 confirms 127) | ready |
| dac-sp | DAC&FW State Agriculture Profile PDFs | location, crops | https://sugarcane.dac.gov.in/pdf/May2024/SP_UttarPradesh.pdf | Official state agriculture profiles with zone->district tables; only UP + Uttarakhand available on this host | ready |
| cibrc-formulations | PPQS: Pesticide Formulations Registered for use in the Country (updated 31.03.2026) | pesticides | https://ppqs.gov.in/sites/default/files/list_pf_pesticide_formulations_registered_as_on_31.03.2026.pdf | Official CIB&RC formulations list; sections Insecticides/Fungicides/Herbicides/Rodenticides/Fumigants/PGR/Public Health | ready |
| pib-109-2024 | PIB: Details of 109 varieties of Field and Horticultural crops released by PM (11 Aug 2024) | crops | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2044754 | Govt of India PIB release; per-crop table of released varieties/hybrids with sponsoring org, states, features; source of `released` variety names | ready |
| iihr-notified | ICAR-IIHR: List of Notified Varieties from 2009-19 | crops | https://www.iihr.res.in/varieties-and-technologies-released-icar-iihr | ICAR institute; PDF of notified horticultural varieties 2009-2019 (fetchable with browser UA/referer); source of `notified` variety names | ready |
| dod-castor | DOD: Castor recommended varieties | crops | https://oilseeds.dac.gov.in/Castor.aspx | Govt of India (DAC&FW); state-wise notified/released varieties | ready |
| dod-niger | DOD: Niger recommended varieties | crops | https://oilseeds.dac.gov.in/Niger.aspx | Govt of India (DAC&FW) | ready |
| dod-sesame | DOD: Sesame recommended varieties | crops | https://oilseeds.dac.gov.in/Sesame.aspx | Govt of India (DAC&FW) | ready |
| dod-linseed | DOD: Linseed recommended varieties | crops | https://oilseeds.dac.gov.in/Linseed.aspx | Govt of India (DAC&FW) | ready |
| dod-sunflower | DOD: Sunflower recommended varieties | crops | https://oilseeds.dac.gov.in/Sunflower.aspx | Govt of India (DAC&FW) | ready |
| dod-safflower | DOD: Safflower recommended varieties | crops | https://oilseeds.dac.gov.in/Safflower.aspx | Govt of India (DAC&FW) | ready |
| dod-groundnut | DOD: Groundnut recommended varieties | crops | https://oilseeds.dac.gov.in/Groundnut.aspx | Govt of India (DAC&FW) | ready |
| dod-rapeseed | DOD: Rapeseed & Mustard recommended varieties | crops | https://oilseeds.dac.gov.in/Rapeseed.aspx | Govt of India (DAC&FW) | ready |
| nsri-soybean | ICAR-NSRI: Soybean notified varieties | crops | https://icar-nsri.res.in/varieties.html | ICAR institute; list of notified soybean varieties 1973-2024 | ready |
| iisr-varieties | ICAR-IISR: Spices varieties released | crops | https://spices.res.in/pages/varieties-released | ICAR institute; released pepper/ginger/turmeric/cinnamon/nutmeg/cardamom | ready |
| iipr-varieties | ICAR-IIPR: Pulses varieties developed | crops | https://www.icar-iipr.org.in/varieties/ | ICAR institute; released chickpea/pigeonpea/mung/urd/lentil/fieldpea/rajma | ready |
| cacp-msp | CACP crop- and year-wise MSP (Recommended/Fixed), crop years 2010-11 to 2026-27 | market | https://cacp.da.gov.in/Home/MSP | Govt of India; values in ₹/qtl (INR per quintal); encoded as market.msp.msp_series | ready |
| crida-cp | ICAR-CRIDA Agriculture Contingency Plans (district-wise PDFs) | location, crops, soil | https://icar-crida.res.in/ccp.html | ICAR institute; one PDF per district listing agro-climatic zone (PC + NARP), major soils, major field crops (area) and fruits/vegetables; used for Uttarakhand district attributes (13 districts) in districts.json and for NARP zone→district `found_in` relations in narp_zones.json | ready |
| des-apy-district | DES (DAC&FW) district-wise crop Area/Production/Yield (APY) | crops | https://data.desagri.gov.in/website/crops-apy-report-web | Govt of India; district-level APY export (Excel/PDF); TODO for remaining districts | manual |
| jau | Junagadh Agricultural University (Saurashtra agro-climatic zones) | location | https://www.jau.in/university-jurisdiction | Official Gujarat SAU; Table of NARP zones 5-8 (North West/North Saurashtra/South Saurashtra/Bhal Coastal) with districts | ready |
| uasb | University of Agricultural Sciences, Bangalore (agro-climatic zones) | location | https://www.uasbangalore.edu.in/en/agro-climatic-zones-karnataka/ | Official Karnataka SAU; zone->district+taluks for Central/Eastern/Southern Dry and Southern Transition zones | ready |
| tnau | Tamil Nadu Agricultural University (agro-climatic zones) | location | https://tnau.ac.in/tamil-nadu-agro-climatic-zones/ | Official Tamil Nadu SAU; 7 agro-climatic zones with districts | ready |
| jnkvv | Jawaharlal Nehru Krishi Vishwa Vidyalaya (MP agro-climatic zones) | location | https://www.jnkvv.org/short-history | Official MP SAU; 7 zones with district lists (Chhattisgarh Plain, N Hill, Kymore, Vidhya, Narmada, Bundelkhand, Satpura) | ready |
| skuast-j | SKUAST-Jammu (Jammu agro-climatic zones) | location | https://skuastjammu.ac.in/newsite/about-introduction.php | Official J&K SAU; Sub-tropical/Intermediate/Temperate zone districts | ready |
| bameti | BAMETI Bihar (state agro-climatic zones) | location | https://www.bameti.org/wp-content/uploads/2021/02/State-Profile.pdf | Bihar Agriculture Management & Extension Training Institute; Zone 1/2/3A/3B district tables | ready |
| wb-racp | World Bank: Rajasthan Agriculture Competitiveness Project EAMF (2012) | location | https://documents1.worldbank.org/curated/en/571371468267617038/pdf/E29290REVISED00B0SAR0EA0P124614vol1.pdf | Govt of Rajasthan/World Bank; Table 2-2 Rajasthan agro-climatic zones with districts | ready |
| odisha-doa | Odisha Agriculture Statistics 2017-18, Directorate of A&FP | location | https://agri.odisha.gov.in/sites/default/files/2022-06/ODISHA%20AGRICULTURE%20STATISTICS_2017-18.pdf | Govt of Odisha; zone-wise district yield tables for all 10 agro-climatic zones | ready |
| nddb-punjab | NDDB: Dairying in Punjab - A Statistical Profile 2014 | location | https://www.nddb.coop/sites/default/files/pdfs/NDDB-Dairy_Digest_Punjab-17-10-2014.pdf | NDDB; Table VII.1.1 Punjab agro-climatic zones with districts | ready |
| aau | Assam Agricultural University (agro-climatic zones) | location | https://www.aau.ac.in/research | Official Assam SAU; UBVZ/CBVZ/LBVZ/Barak Valley zone districts | ready |
| iihr-varieties | ICAR-IIHR: Varieties and Technologies released | crops | https://www.iihr.res.in/varieties | ICAR institute; per-crop released variety pages (Arka series, grapes, papaya, cauliflower, carrot, radish, garden pea, onion, cowpea, ridge/bitter gourd, capsicum, coriander, palak, litchi, lemon/musk melon, dolichos, amaranth) | ready |
| cish-varieties | ICAR-CISH: Varieties for Commercialization | crops | https://www.cish.org.in/varieties | ICAR institute; released mango/guava/bael/jamun/banana/aonla varieties (Ambika, Arunika, Lalit, Lalima, Shweta, Awadh series, NA-6/7/10 aonla, etc.) | ready |
| nrcb-banana | ICAR-NRCB: Banana varieties released | crops | https://nrcb.org.in/ | ICAR institute; Kaveri Kanchan, Kaveri Vaman (TBM-9), Kaveri Saba, Kaveri Sugantham, Kaveri Kalki, Kaveri Kanya, NRCBGNM-1 | ready |
| ctcri-tuber | ICAR-CTCRI: Tropical tuber varieties | crops | https://www.ctcri.org/en/varieties | ICAR institute; Sree series cassava/sweet potato (Sree Kaveri, Sree Annam, Sree Manna, Bhu Sona, etc.) | ready |
| ccri-citrus | ICAR-CCRI: Citrus varieties | crops | https://ccri.org.in/ | ICAR institute; mandarin/sweet orange/acid lime/grapfruit/pummelo released varieties | ready |
| iivr-veg | ICAR-IIVR: Vegetable varieties | crops | https://icariivr.org.in/ | ICAR institute; Kashi series (Gobhi-25, Mooli-40, Nutan cucumber, Kashi Krishna carrot, etc.) | ready |
| cith-temperate | ICAR-CITH: Temperate fruit varieties | crops | https://icarcith.org.in/ | ICAR institute; released apple/apricot/walnut/almond/pear/plum/peach varieties | ready |
| ciah-varieties | ICAR-CIAH (Central Institute for Arid Horticulture): Varieties released | crops | https://icar-ciah.org/index.php?do=achivmnts_highlits&mod=achivmnts | ICAR institute; released arid fruit/vegetable varieties table (Tamarind 'Goma Prateek', etc.) | ready |
| dmr-mushroom | ICAR-DMR: Mushroom varieties/strains | crops | https://dmrsolan.res.in/ | ICAR institute; DMR button/milky/oyster/shiitake strains | ready |
| dogr-garlic | ICAR-DOGR: Onion & garlic varieties | crops | https://www.dogr.res.in/ | ICAR institute; Bhima onion / garlic varieties | ready |
| nrcss-spices | ICAR-NRCSS (Central Institute of Seed Spices): Seed spice varieties | crops | https://epubs.icar.org.in/index.php/IJSS | ICAR institute/journal; Ajmer coriander ACr, fenugreek AFg, cumin GC varieties | ready |
| rubberboard-clones | Rubber Board / RRII: Recommended rubber clones | crops | https://rubberboard.gov.in/ | Commodity board; RRII/RRIM/PB/GT clones | ready |
| ctcri | ICAR-CTCRI (herb/medicinal crops when applicable) | crops | https://www.ctcri.org/en/ | ICAR institute | ready |
| ctri-tobacco | ICAR-CTRI: Tobacco varieties | crops | https://ctri.icar.gov.in/ | ICAR institute; FCV/oriental/Natu/burley/chewing tobacco released varieties | ready |
| icar-iimr | ICAR-IIMR (Indian Institute of Millets Research): Small millet varieties | crops | https://www.millets.res.in/ | ICAR institute; released foxtail/little/kodo/browntop/pearl/barnyard millet varieties | ready |

## 9(3)(i) provisional registrations — status
No official machine-readable registry of Section 9(3)(i) provisional pesticide registrations exists on cibrc.gov.in (site down) or ppqs.gov.in/divisions/cib-rc/registered-products (only 9(3) formulations/actives, banned list, import sources, household/rodenticide and desert-locust lists). Provisional grants appear only per-meeting in RC minutes PDFs and convert to 9(3). COUNTED TODO: no 9(3)(i) provisional-registration entities added; do NOT fabricate.

## Fetch status (filled by scripts/fetch_sources.py)
<!-- fetch_sources.py appends a status table here -->
