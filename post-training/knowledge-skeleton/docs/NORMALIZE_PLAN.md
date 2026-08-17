# Format-Normalization — completed

Goal: give every `(domain, type)` one canonical attribute contract so
cross-domain interconnections (KG edges) are consistent, WITHOUT losing a
single fact. This doc records what was applied and the verification that
proves zero data loss.

Ground truth at start: 1842 entities, 8619 relations, 19 JSON files, 182
registered sources, validate.py PASS (baseline commit `c52950e`).
Completed: 2026-08-17. Final: 1842 entities, 8619 relations, 0 ontology
warnings, validate PASS, audit_shapes 0 violations.

---

## 1. Canonical keys (schema.json `key_aliases`)

Only the LEFT key may appear in data. Migration renamed right→left.

| concept | canonical | aliases folded in | verified safe |
|---|---|---|---|
| free description | `note` | `notes` | 72 stale crop `notes` dropped (61 note+notes, 11 notes-only); all were false "TODO: variety registry" placeholders, real content lived in `note` |
| economic/agricultural purpose | `use` | `uses`, `purpose` | 3 `uses`, 15 `purpose` renamed; 0 entities had both |
| scientific name | `scientific` | `scientific_name` | 70 renamed; 0 entities had both |
| sub-type | `type` | `types` | 5 renamed; 0 entities had both |

**Corrected mid-work:** the original plan listed `species`→`scientific` and
`character`→`scientific`. That was WRONG — livestock `species` holds common
names ("pig", "goat", "cattle") and soil `character` holds a description.
Neither is a scientific binomial. They are semantically distinct keys and
were kept as-is.

`class` stays distinct from `type` for pesticides (a substance has both a
registration `class` and an entity `type`).

## 2. Re-types (semantic alignment, not data loss)

Two classes of entity were typed `entity` but are genuinely a specialised
class. Their `type` was corrected:

- **78 banned/restricted pesticide actives**: `entity` → `substance`
  (PesticideSubstance). They ARE active ingredients (e.g. alachlor, aldrin);
  they simply lack a current registration `class`. `class` was therefore
  moved from required → optional in the PesticideSubstance contract
  (present in 380/381 registered, 3/78 banned).
- **5 weather phenomena**: `entity` → `event` (WeatherEvent): hailstorm,
  frost, dry_spell, cloudburst, indian_ocean_dipole. They use `affects` on
  crops, which WeatherEvent permits; WeatherEntity did not.

Result: pesticides now 459/459 uniform `substance`; weather events uniformly
typed `event`.

## 3. Predicate contract corrections (schema.json `relation.predicates`)

Warn-mode surfaced predicates whose domain/range were narrower than actual
(legitimate) usage. Contracts were widened to match:

| predicate | change |
|---|---|
| `affects` | domain + `LivestockBreed` (livestock diseases), `Category`; range + `Category`, `CropSeason`, `WeatherEvent` |
| `requires` / `suited_for` | range + `Category` (soil suited_for crops.pulses etc.) |
| `registered_in` | domain + `LivestockVariety` (NBAGR), `Category` (seeds.varieties, pesticides.registered_actives) |
| `recommended_for` | domain `MarketMeasure`→`Measure` (class renamed), + `SeedEntity` (hybrids) |

## 4. Class contracts fixed

- `PesticideSubstance.required`: `class` → optional (banned actives).
- `Category.optional`: + `seasons` (weather.seasons), − `types` (canonical is `type`).
- `Institution.optional`: `purpose` → `use`.
- `Measure.optional`: − `purpose` (canonical is `use`).
- `WeatherEvent.optional`: `types` → `type`.

## 5. What stays multi-shape (by design)

Optional-key presence/absence is NOT flattened. A crop without a recorded
`water` need is not forced to carry a null — that would fabricate attribute
presence. Remaining ">1 shape" groups differ only in which optional keys are
present. `audit_shapes.py` reports 0 violations: no deprecated keys, no
synonym co-presence, no key outside its class contract.

## 6. Enforcement (in place)

- `scripts/normalize_shapes.py`: applies `key_aliases`, drops verified-stale
  markers, aborts with zero writes on any merge-risk (real content in both
  keys). Idempotent — re-running changes nothing.
- `scripts/audit_shapes.py`: shape-conformance report; exit 1 on violations.
- `scripts/validate.py`: added warn-mode ontology conformance — attribute
  keys within Class contract, deprecated-alias and synonym-co-presence
  detection, predicate domain/range. 0 warnings today. Per
  `schema.json` `conventions.class_contract`, warnings become errors once
  conformance is declared complete.

## 7. Interaction with the 6 counted gaps

Normalization is orthogonal to gaps — it never fabricates data and doesn't
close them. Gaps remain as COVERAGE.md counts them; normalization guarantees
gap-data lands in the canonical slot. See COVERAGE.md.

## 8. What was deliberately skipped

- No per-entity `attributes_optional` flag (empty-attribute leaf rows like
  plant_protection taxonomy leaves are handled by contracts with empty
  required lists).
- No strict (error) mode yet — still warn-mode per the agreed
  "warn first, fail later".

## 9. Inverse consistency (post-hoc)

`scripts/sync_inverses.py` materializes missing inverse edges for declared
inverse pairs, reusing the forward edge's source. Idempotent.

- `requires` ↔ `suited_for`: 32 ↔ 32 (was 24 ↔ 27). Domain widened to
  `["Crop","Category"]` so category nodes (crops.millets, crops.pulses) can
  hold inverse edges.
- `part_of` ↔ `has_part`: 76 ↔ 76 (was 76 ↔ 0). `has_part` added to
  `validate.py` KNOWN_PREDICATES.
- Verify: `validate.py` PASS, 0 ontology warnings, audit_shapes 0 violations.
- 37 shared concept nodes referenced from 2+ domains; every node owned by
  exactly one domain, referenced from others — no inlined duplicates
  (verified: soil entities referenced via relations, never inlined).

## 10. Bare-minimum required attributes (curated, data-verified)

`schema.json` class `required` is a curated BARE-MINIMUM attribute set per
Class — the identifying minimum every entity should carry. The set was
REVISED against actual data coverage (2026-08-17): over-specified requireds
were dropped where data showed no single attribute is universal.

**Genuine universals (kept required):**

| Class | required | coverage |
|---|---|---|
| Crop | scientific | 100% (phenology* moved to optional: 96%, 8 niche crops lack it) |
| CropSeason | examples, months | 100% |
| LivestockBreed | note | 100% (species moved to optional: 92% — diseases/dairy ride the class and have none) |
| LivestockVariety | note, origin, species | 100% |
| FinanceEntity | note | 100% |
| WaterEntity | note | 100% (water_stats moved to optional: 83%) |
| Institution | use | 100% after role→use fold (was role 67%) |

**Heterogeneous classes (required empty — no single attribute is universal;**
**the class contract still constrains keys, so no random info):**
SoilType (natural: colour/texture/origin/fertility vs problem: note),
PesticideSubstance (registered: class/use/formulations vs banned: note),
FertilizerSubstance, Pest/PlantDisease/Weed (leaf rows), Measure,
FisherySpecies (marine: landings vs inland: note), ForestEntity,
MachineryEntity, WeatherEvent/WeatherEntity, SeedEntity, OrganicEntity,
PostHarvestEntity, GenericEntity.

**Synonym fold:** `role` → `use` (Institution). Data: 20 institutions use
role, 8 schemes use use, zero overlap, same semantics. Added to key_aliases.

**Deterministic fills applied (restatement of existing facts, no new data):**
- 3 exotic cattle breeds (Jersey, Holstein Friesian, Brown Swiss) + mithun/
  yak general anchors: added `species` (= cattle / mithun / yak).
- operation_flood: split mixed `period` ("1970-1996; India's largest dairy
  programme...") into real `period` + `note`.
- PM-KISAN and water.schemes.pmksy: `use` derived from their note / canonical
  sibling scheme.

Result: **0 ontology warnings.** No fabrication — every fill restates facts
already present in the entity or its source.

## 11. Location anchor (every domain reaches Location)

`validate.py` `check_location_anchor`: every non-exempt entity must reach a
location node (direct `found_in`/`grown_in`/`practiced_in`/`produced_in`/
`banned_in`, or transitively via part_of/is_a). measure/tool/event types are
exempt (spatially-agnostic practices). Verified: 0 warnings — all 19 domain
roots reach location, every concrete entity reaches a location node. Location
is the inter-domain anchor; other cross-domain edges (affects, requires,
registered_in, recommended_for) supplement it.