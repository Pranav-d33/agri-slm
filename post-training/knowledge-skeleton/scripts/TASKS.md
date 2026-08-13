# Task Specs — Phase 2: 127 NARP Zones + Remaining Gaps

Work stream specs for self + parallel subagents. Every output MUST pass `validate.py`
and be deterministic (source-registered, nothing fabricated).

## Conventions (from schema.json / existing files)

- Location ids: `location.states.<state>`, `location.uts.<ut>`, `location.districts.<state>.<district>`,
  `location.zones.pc_<n>` (existing 15). New: `location.zones.narp_<state>_<n>`.
- Entities live in `data/locations/*.json` under keys like `zones` / `districts` / `states`.
- Relations: `{predicate, object, source?}`. Location predicates: found_in/grown_in/practiced_in/produced_in/banned_in.
- Every entity + relation carries `source` referencing `sources.md`.
- Gaps go in `notes` as TODO with expected count — never fabricated.

---

## A1. NARP 127-zone registry — `data/locations/narp_zones.json`

**Source (verified)**: Venkateswarlu, Ramakrishna & Rao, "Agro-climatic Zones of India",
*Annals of Arid Zone* 35(1):1–7 (1996) — Table 1 lists state-wise NARP zones with
rainfall and major soils. URL: `https://epubs.icar.org.in/ejournal/index.php/AAZ/article/view/65198`.
Registered as source id `narp-zones`.

**Registry** (121 mainland zones across 17 states, from the paper's table):

| State | count | zone names |
|---|---|---|
| Andhra Pradesh | 7 | Krishna Godavari; North coastal AP; Southern AP; Northern Telangana; Southern Telangana; Scarce rainfall zone; High altitude zone |
| Assam | 6 | S. Arunachal Pradesh; Upper Brahmaputra Valley; Central Brahmaputra Valley; Lower Brahmaputra Valley; Barak valley; Nagaland/Meghalaya hill zone |
| Bihar | 6 | North west alluvial plain; North east alluvial plain; South Bihar alluvial plain; Central plateau; Western plateau; South eastern plateau |
| Gujarat | 8 | South Gujarat (x2); Middle; North; North west; North Saurashtra; South Saurashtra; Bhal and coastal |
| Haryana | 2 | Eastern; Western |
| Himachal Pradesh | 4 | Sub-montane/low hills; Mid hills sub-humid; High hills temperate; High hills |
| Jammu & Kashmir | 5 | Sub-tropical; Intermediate; Valley temperate; Temperate; Cold arid |
| Karnataka | 10 | NE transition; NE dry; Northern dry; Central dry; Eastern dry; Southern dry; Southern transition; Northern transition; Hill; Coastal |
| Kerala | 5 | Northern; Southern; Central; High altitude; Problem area |
| Madhya Pradesh | 12 | Chhattisgarh plain; Bastar plateau; North hill; Kymore plateau; Vidhya plateau; Central Narmada Valley; Gird; Bundelkhand; Satpura plateau; Malwa plateau; Nimar Valley; Jhabua hills |
| Maharashtra | 9 | South Konkan; North Konkan coast; Western Ghat; Sub-montane; Western Maharashtra plain; Scarcity zone; Central Maharashtra plateau; Central Vidharbha; Eastern Vidharbha |
| Orissa | 10 | NW plateau; North central plateau; NE plateau; E & SE coast; NE Ghat; E Ghat highland; SE Ghat; Western undulating; West central table land; Mid central table land |
| Punjab | 5 | Sub-montane; Undulating plains; Central plains; Western plains; Western zone |
| Rajasthan | 9 | Arid western plains; Irrigated north; Transitional plains; Transitional plain of Luni basin; Semi-arid eastern plains; Flood prone east; Sub-humid southern; Southern humid plains; SE humid plains |
| Tamil Nadu | 7 | NE; NW; Western; Cauvery Delta; Southern; High rainfall; High altitude |
| Uttar Pradesh | 10 | Hill; Bhabar & Tarai; Western plain; Mid-western plain; SW semi-arid; Central plains; Bundelkhand; NE Plains; Eastern plain; Vindhyan |
| West Bengal | 6 | Hilly; Tarai; Old alluvial; New alluvial; Laterite & red soil; Coastal saline |

Plus: NEH combined zone (Tripura/Mizoram/Manipur), Andaman & Nicobar, Lakshadweep,
Puducherry (2 zones). Paper notes 126 NARP zones for 17 states + NEH + islands;
Rajya Sabha (2021) official answer says 127. Count discrepancy recorded in `notes`,
reconciled toward **127**.

**Entity shape**:
```json
{
  "id": "location.zones.narp_up_3",
  "name": "Western plain of UP",
  "state": "Uttar Pradesh",
  "attributes": {"narp_zone_no": 107, "rainfall_mm": "700-1200", "major_soils": "Alluvial"},
  "relations": [
    {"predicate": "part_of", "object": "location.states.uttar_pradesh"},
    {"predicate": "part_of", "object": "location.zones.pc_5"},
    {"predicate": "found_in", "object": "<district id>", "source": {"id": "dac-sp-up"}}
  ],
  "source": {"id": "narp-zones", "url": "https://epubs.icar.org.in/ejournal/index.php/AAZ/article/view/65198"},
  "notes": "TODO: district list per zone from <state> agriculture profile; expected N districts"
}
```

## A2. Verified zone→district tables (from DAC State Agriculture Profiles)

**Source (verified)**: `https://sugarcane.dac.gov.in/pdf/May2024/SP_<State>.pdf`,
registered as `dac-sp`. Confirmed extractable for UP (9 zones, districts listed)
and Uttarakhand (4 sub-zones, no district table). Only these 2 profiles exist on that host.

**UP 9 zones → districts** (from SP_UttarPradesh.pdf p2):
- Tarai and Bhabar: Saharanpur, Muzaffarnagar, Bijnor, Moradabad, Rampur, Bareilly, Shahjahanpur, Pilibhit, Lakhimpur Kheri, Bahraich, Shravasti
- Western Plain: Saharanpur, Muzaffarnagar, Shamli, Meerut, Bagpat, Ghaziabad, Hapur, Gautambuddha Nagar, Bulandshahar
- Mid Western Plain: Bijnor, Amroha, Moradabad, Sambhal, Rampur, Bareilly, Budaun, Pilibhit, Shahjahanpur, Sitapur, Lakhimpur Kheri
- South Western Semi Arid: Agra, Mathura, Firozabad, Mainpuri, Aligarh, Hathras, Etah, Kasganj
- Central Plain: Farrukhabad, Kannauj, Etawah, Auraiya, Kanpur Nagar, Kanpur Dehat, Fatehpur, Kaushambi, Prayagraj, Hardoi, Unnao, Raebareilly, Lucknow
- Bundelkhand: Jhansi, Jalaun, Lalitpur, Hamirpur, Mahoba, Banda, Chitrakoot
- North East Plain: Bahraich, Shravasti, Balrampur, Gonda, Siddharth Nagar, Basti, Sant Kabir Nagar, Maharajganj, Gorakhpur, Kushinagar, Deoria
- Eastern Plain: Barabanki, Ayodhya, Amethi, Sultanpur, Ambedkar Nagar, Jaunpur, Varanasi, Chandauli, Bhadohi, Ghazipur, Azamgarh, Mau, Ballia, Pratapgarh
- Vindhyan: Mirzapur, Sonbhadra, Prayagraj (Southern part)

Note: UP DAC profile merges the ICAR paper's 10 zones into 9 (Tarai+Bhabar merged,
Hill zone omitted). Add `found_in` relations only where district ids resolve in
`districts.json`; mark the rest in `notes`.

## A3. Pesticide formulations

**Source (verified)**: PPQS "Pesticide Formulations Registered for use in the Country
under the Insecticides Act, 1968 (Updated 31.03.2026)" — 28-page PDF at
`https://ppqs.gov.in/sites/default/files/list_pf_pesticide_formulations_registered_as_on_31.03.2026.pdf`.
Registered as source id `cibrc-formulations`.

**Task**: parse the PDF (sections A. Insecticides, B. Fungicides, C. Herbicides, D. Rodenticides,
E. Fumigants, F. Plant Growth Regulators, G. Public Health/Household/Rodenticide).
For each registered active in `data/pesticides.json` (371 actives), attach
`attributes.formulations` = list of "X% FORM" strings for that active where present
(active name prefix match, case-insensitive). Unmatched actives keep `notes` TODO.

## A4. Sources.md entries

Add rows: `narp-zones` (Annals of Arid Zone 1996 PDF), `dac-sp` (DAC state
agriculture profiles), `cibrc-formulations` (PPQS formulations PDF).

## A5. Bind zones into domains

- `data/weather.json`: add `part_of`/found_in references to relevant NARP zones
  (monsoon, agro-climate entities).
- `data/soil.json`: add `found_in` relations from soil types to NARP zones where
  the ICAR paper lists that soil as dominant.
- `data/crops.json`: no bulk edits; zone→crop suitability flows through queries.

## A6. Remaining gaps (secondary)

- District→state `part_of`: every district in districts.json gets `part_of` to its
  parent state id (mechanical, from file structure).
- Hindi aliases: top-200 entities get `aliases` Hindi common names (only well-attested,
  e.g. rice=धान). Mark source. No guessing.
- Variety registry: defer to a dedicated crawl; add `notes` TODO only.

## Verify

After all edits: `python3 scripts/validate.py` must PASS, `python3 scripts/coverage.py`
regenerates COVERAGE.md. Update README status line.
