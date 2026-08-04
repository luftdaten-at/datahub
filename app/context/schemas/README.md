# Context import schemas

Versioned JSON contracts for externally pre-computed Copernicus Land (Modul 3) and
LST heat (Modul 6) artifacts.

## Files

| Schema | Module | Artifact pattern |
|--------|--------|------------------|
| `heat_profiles.v1.schema.json` | `heat` | `heat_profiles_<date>.json` |
| `land_profiles.v1.schema.json` | `land` | `land_profiles_<version>.json` |

## format_version policy

- Semantic versioning: Datahub accepts all `1.x` versions via JSON Schema pattern `^1\.`.
- `2.x` is rejected until a matching schema is added to this directory.
- Unknown extra fields in profiles are ignored (schema uses `additionalProperties: true` on profiles).

## Join key

All profiles use **`municipality_slug`** only — identical to slugs from `api.luftdaten.at`.

## Units

- Temperatures: °C
- Temperature differences (SUHI): K
- Percent shares: 0–100 (never fractions)
- Missing values: JSON `null` (never `0`, `-999`, or omitted keys)

## quality_flags

Allowed values (unknown values abort import):

- `insufficient_clear_pixels`
- `no_rural_reference`
- `high_relief`
- `weak_regression`
- `substituted_date`
- `population_suppressed`

Municipalities without a usable result must be included with flags set, not omitted.

## Contact

Schema changes require coordination with the Datahub team and the external pipeline
producer (`luftdaten-at/heat-pipeline` or land pipeline equivalent).

Test fixtures under `app/context/tests/fixtures/` are the executable reference for
external producers.
