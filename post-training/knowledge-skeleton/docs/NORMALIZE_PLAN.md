# Format-Normalization Plan (analysis, before any edits)

Goal: give every `(domain, type)` one canonical attribute contract so
cross-domain interconnections (KG edges) are consistent, WITHOUT losing a
single fact. This doc is the analysis + migration design. Nothing below has
been applied to the data yet.

Audit date: 2026-08-14. Ground truth: 1800 entities, 7365 relations, 20 JSON
files, 34 registered sources, validate.py PASS.

---

## 1. The one real disease: synonym keys

The kind that genuinely breaks interconnection is **two keys naming the same
concept inside one group**. Counted:

| collision | present in | found |
|---|---|---|
| `note` + `notes` on the same entity | crops | **61** |
| `use` + `uses` | (no entity has both) | 0 |
| `type` + `types` | (no entity has both) | 0 |

The `note`/`notes` collision in crops is a **stale-data bug, not a merge
problem**:
- All 61 `notes` values are leftover `"TODO: notified variety registry from
  SeedNet..."` markers from an earlier phase. They are already satisfied by
  the `notified_varieties`/`notified_status` work and must be **deleted**
  (that is not data loss — it removes a now-false placeholder).
- `note` in all 61 holds the real description. Kept.

So `notes` → folded into `note` is safe: no entity carries real content in
both. Verified above.

## 2. Two kinds of "inconsistency", only one needs fixing

**A. Optional-key presence/absence (NORMAL — do NOT flatten).**
E.g. crops `['scientific','season']` vs `['scientific','season','water']`;
soil `['colour','fertility','origin','texture']` vs the same + `region`.
This is legitimate: a crop without a recorded `seed_rate` should not be made
to carry a null. The volume of "shapes" above is mostly this.

Normalization contract = **required keys + optional keys + a value type per
key**, NOT "all entities must have identical key sets". Forcing 100% key
parity would FABRICATE attribute presence. This is the data-loss-free rule.

**B. Semantic collisions (the actual work).**
Same concept spelled as different keys / different value semantics:

| concept | current keys | canonical |
|---|---|---|
| free description | `note`, `notes` | `note` |
| economic/agricultural purpose | `use`, `uses`, `purpose` | `use` |
| meaningful sub-type within a type | `type`, `types`, `class` | `type` |
| organism label | `scientific`, `species`, `character` | `scientific` |
| (pesticide) registration class | `class` | `class` (keep distinct) |

`type` and `class` must stay separate for pesticides (a substance has both a
`type` and a `class`); for other groups `class` collapses into `type`.

## 3. Empty-attribute entities (not a defect)

- `plant_protection`: 530/550 have empty attributes. They are the TNAU-crawl
  taxonomy leaves (disease/pest names) that exist as `affects` relation
  targets, not attribute carriers. Leaf rows without facts should be allowed
  empty; the contract marks them `attributes_optional: true`.
- fisheries/weather empty entries are domain/category roots + unmeasured
  marine rows — same treatment.

## 4. Canonical per-group contracts (draft)

`type`: pesticide `substance` keeps `class`; all others use `type`.
`all`: use `use` (not `purpose`); description always `note`.

The 38 inconsistent groups each get a `required_keys` (+ `optional_keys`)
table in `schema.json`. Full per-group key sets are enumerated in the audit
output (scripts/audit_shapes.py, below).

## 5. Enforcement (so it stays fixed)

Extend `scripts/validate.py`:
- FAIL on any attribute key not in `required ∪ optional` for its group.
- FAIL on any `note`+`notes`, `use`+`uses`, `type`+`types` co-presence.
- ValueError on empty-required for non-optional groups.

## 6. Interaction with the 6 counted gaps

Normalization is orthogonal to the 6 gaps — it never fabricates data and
doesn't close gaps. Gaps remain as COVERAGE.md counts them. Normalization
merely guarantees that when gap-data later lands, it lands in the canonical
slot. See COVERAGE.md for the gap detail.

---

## Migration steps (when approved)
1. Write `scripts/audit_shapes.py` — the report generator behind this doc
   (the regex source of the shape tables above).
2. Repoint `notes`→`note`, drop the 61 stale crop `notes`.
3. Rewrite `schema.json` with per-(domain,type) `required_keys`/`optional_keys`.
4. One migration script `scripts/normalize_shapes.py`: renames keys,
   asserts zero info-loss (conservative: any `use`+`uses` both-filled would
   have failed loudly, none did), writes back.
5. Extend validate.py; run; confirm still PASS; commit.