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
| agmarknet | AGMARKNET | market | https://agmarknet.gov.in/ | Mandi prices | manual |
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

## Fetch status (filled by scripts/fetch_sources.py)
<!-- fetch_sources.py appends a status table here -->
