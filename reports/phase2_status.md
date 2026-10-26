# Phase 2 acquisition and profiling results

Completed October 26, 2026 for the user-approved **Luke Barousse historical 2023 dataset**. The earlier permission-blocked Greenhouse pilot has been superseded, not cleared. Phase 3 has not started. These are reproducible raw data-quality/coverage findings, not final analytical results.

## Source and integrity

- Acquired pinned revision `ed776e5a0a8c40ea9d5efbd800772ae52e140f3e`: 231,152,089 bytes.
- Download SHA-256 matches publisher LFS metadata: `635241ed09ccee18bdae1f83b45f26d6759e0aa2513c529f6190e9054062436c`.
- Complete CSV: **785,741 rows and 17 columns**.
- Parsed source dates: 2023-01-01T00:00:04 through 2023-12-31T23:59:58; 0 invalid nonblank dates; all rows have year 2023. Timezone and collection completeness remain unverified.
- Raw CSV, source evidence and provenance manifest are local/ignored. No credentials or scraping were used. Source license/attribution are recorded in [data attribution](../docs/data_attribution.md).

## Preliminary Bay Area coverage

Exact country + recognized city/state matching finds **15,892 raw records**, **87 cities**, and representation in all **nine counties**. The lookup contains 101 incorporated cities, not all unincorporated communities. This is not a final cleaned cohort; vague, nationwide-remote and multi-location labels require later review. Do not interpret unmatched records as all outside the region.

| Publisher role label | Matched raw rows | Positive finite annual values | Populated inherited skill lists |
|---|---:|---:|---:|
| Business Analyst | 523 | 29 | 449 |
| Cloud Engineer | 22 | 1 | 19 |
| Data Analyst | 4,640 | 274 | 3,879 |
| Data Engineer | 1,753 | 178 | 1,641 |
| Data Scientist | 5,557 | 605 | 4,702 |
| Machine Learning Engineer | 172 | 59 | 151 |
| Senior Data Analyst | 883 | 89 | 786 |
| Senior Data Engineer | 513 | 75 | 491 |
| Senior Data Scientist | 1,586 | 224 | 1,404 |
| Software Engineer | 243 | 50 | 215 |

All four target-role labels occur, with senior Data Analyst/Scientist/Engineer labels separately observed. No original-title review or final mapping has been applied. Other roles remain in profiling evidence rather than being silently removed.

## Quality findings and supported scope

- Derived annual values: **1,584 / 15,892 (9.97%)**. Numeric, positive and finite in this preliminary cohort; this does not establish original advertised pay, USD units or employer provenance.
- Derived hourly values: **720**; keep separate. The raw salary-rate profile also contains monthly/weekly labels; no conversion is performed.
- Populated publisher skill lists: **13,737 / 15,892 (86.44%)**. Missing lists: **2,155**. No malformed lists detected in this cohort. This validates structure, not extraction accuracy or required/preferred skill evidence.
- Work-from-home flag: every matched row has raw value `False`. This cannot identify on-site/hybrid and does not prove no remote opportunities existed; nationally remote/vague locations are outside the exact-city diagnostic.
- All-row exact fingerprint duplicate candidates: **101**; preliminary Bay Area exact candidates: **0**. Employer/title/location/date duplicate candidates: **5**. No rows were removed; fingerprints are diagnostics, not unique-posting identity.
- Title, employer, country, matched location and source date are nonmissing in the preliminary cohort. Full original descriptions, native posting IDs and salary bounds/currency/provenance are absent from the schema.

Proceeding to later phases is feasible for historical role-label/record distributions, inherited skill-tag exploration, geographic comparisons and carefully named derived salary diagnostics. Verified advertised-salary medians, original-text skills, explicit arrangement shares, experience requirements and population hiring trends are unsupported. Original raw salary units must be verified before using a currency symbol; no USD inference is made from a US location alone. Sparse county/city-role/pay groups will need minimum-size rules.

## Phase 2 acceptance review

| Criterion | Result |
|---|---|
| User/source approval and documented local use | Met: explicit Luke approval, pinned Apache-2.0 evidence; raw redistribution not enabled |
| Versioned frame/window | Met: complete immutable publisher CSV, historical 2023; nine-county rules retained |
| Permitted raw acquisition and provenance | Met: original bytes, manifest, timestamps, expected size/hash and license evidence |
| Actual profiling/field dictionary | Met: full scan with raw missingness, categories, dates, duplicates and text/pay evidence limitations |
| All-four-role/geographic suitability | Assessed: each publisher target label present; nine-county/87-city preliminary coverage; final classification deferred |
| Unsupportable KPIs revised or disabled | Met: active dataset amendment in business/KPI/architecture docs |
| Reproducible notebook and automated checks | Tests and notebook verification recorded in the completion check below |
| Stop before Phase 3 | Met: no SQL tables/database, production cleaning/deduplication, accepted classifier, independent NLP, EDA or dashboard |

## Completion check

**98 tests passed.** The real notebook executed successfully, and an independent standard-library CSV scan reconciled all rows, year coverage, exact-city counts, pay-field presence, skill-list presence and county totals. See `phase2_test_environment.json` for measured runtimes and verification details. Checks cover source approval, immutable version/checksum, safe skill parsing, geography boundaries, missingness, duplicate accounting across chunk boundaries, schema drift, legacy blocked-source behavior and no silent raw overwrite. Test fixtures are explicitly TEST_ONLY and never used as research evidence. The executed notebook uses the actual verified dataset/profile, not synthetic examples.

No commits or pushes were performed. Phase 3 requires explicit approval. Source-specific restrictions and data limitations are part of the handoff, not reasons to fabricate missing fields.
