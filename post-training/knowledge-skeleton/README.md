# Indian Agriculture Knowledge Skeleton

Deterministic, KG-ready skeleton of Indian agriculture (English) for training an Indian agricultural language model.

## What this is

A **taxonomy + fact skeleton** covering Indian agriculture in 18 domains, where every fact traces to a
registered source (`sources.md`) — nothing is LLM-generated. It is structured so it can be mechanically
converted into a **knowledge graph** later: each entity becomes a node, each relation becomes an edge.

**Location is the anchor.** Every domain entity ends in `found_in` / `grown_in` / `practiced_in` /
`produced_in` relations pointing at the location hierarchy
(`data/locations/`: India → 36 states/UTs → 640 districts (census-2011 baseline), 15 agro-climatic zones, regions).

## Layout

```
knowledge-skeleton/
├── README.md
├── schema.json          # entity/relation contract
├── sources.md           # source registry (id, url, status)
├── COVERAGE.md          # generated audit: what we have vs. what's missing
├── data/
│   ├── agriculture.json # root node + location anchor domain
│   ├── soil.json, crops.json, livestock.json, pesticides.json, fertilizers.json,
│   │   organic.json, water.json, weather.json, seeds.json, machinery.json,
│   │   plant_protection.json, fisheries.json, post_harvest.json, market.json,
│   │   schemes.json, forestry.json, apiculture.json
│   ├── locations/       # states_uts.json, districts.json, agro_climatic_zones.json
│   └── _raw/            # fetched source pages (TNAU, census mirror, fetch_report.json)
└── scripts/
    ├── fetch_sources.py  # download deterministic sources into _raw/
    ├── build_districts.py# crawl census-2011 district lists
    ├── validate.py       # referential integrity + schema check
    └── coverage.py       # expected-vs-collected audit -> COVERAGE.md
```

## Usage

```bash
python3 scripts/fetch_sources.py    # refresh raw source pages
python3 scripts/build_districts.py  # rebuild district enumeration
python3 scripts/validate.py         # must PASS
python3 scripts/coverage.py         # regenerate COVERAGE.md
```

## Conventions (see schema.json for full contract)

- `id`: dotted snake_case (`soil.black`, `crops.rice`, `location.states.maharashtra`)
- `relations`: `{predicate, object}`; predicates are fixed (is_a, part_of, found_in, grown_in,
  practiced_in, produced_in, registered_in, banned_in, recommended_for, controlled_by, affects,
  requires, suited_for, monitored_by, regulated_by, certified_by)
- `source`: `{id, url}` referencing `sources.md`; some entities carry `agrovocId` linking to the
  repo's existing `agrovoc_entities_filtered.json` (AGROVOC extraction)
- Gaps are tracked in `COVERAGE.md` and `notes` fields as TODO — never fabricated
- English only (v1); Hindi/local names allowed in `aliases`

## Status

1733 entities, 6536 relations, 1006 location nodes, 36 states/UTs, 784 LGD districts,
15 PC agro-climatic zones, 125 ICAR NARP zones (with UP zone->district lists),
9 regions. Soil/crops/livestock/pesticides/fertilizers/organic/water/weather/seeds/machinery/
plant-protection/fisheries/post-harvest/market/schemes/forestry/apiculture all have their
taxonomy skeleton at levels 0–2 with location anchoring; 333 registered pesticide actives
carry formulations (PPQS 31.03.2026); leaf-level exhaustive data (every variety, every
district zone-list, Hindi aliases) is enumerated as counted gaps in COVERAGE.md.

## KG conversion (future)

`(entity_id, predicate, object_id)` emission from every relation = the graph. Add
`agrovocId`/`sources.md` as node metadata. Then: Hindi aliases, district-level fact enrichment,
sentence generation for LM training.
