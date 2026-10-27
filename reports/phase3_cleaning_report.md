# Phase 3 data quality and cleaning report

Completed local cleaning/database validation for the pinned historical 2023 Luke CSV. Counts describe processing, not actual hires or certified unique postings. Phase 4 has not started.

## Input and output reconciliation

| Mutually exclusive row outcome | Rows |
|---|---:|
| Exact duplicate records removed (entire file) | 101 |
| Country missing or outside US | 579,353 |
| Confirmed non-CA work locations | 143,703 |
| Unresolved geography (includes unmatched California places) | 46,360 |
| Invalid/missing date | 0 |
| Outside 2023 | 0 |
| Missing title | 0 |
| Training/talent-pool advertisement | 1 |
| Retained Bay records in SQLite | 16,223 |
| **Total input / reconciled outcomes** | **785,741** |

Fact output: **16,223**. Accepted title-only target cohort: **12,631**; ambiguous: **209**; unclassified: **3,103**; explicit non-target: **280**. The latter three remain in the fact/audit cohort, outside `v_target_job_records`.

## Corrections and detected issues

- 5 similar employer/title/location/date candidates preserved; only all-field exact duplicates removed; 0 retained-Bay duplicates removed. Global duplicate counts are not Bay duplicate-job counts.
- Added 328 community memberships using referenced county mappings; also normalized St Helena spelling. One explicit bootcamp advertisement excluded. This explains differences from the unchanged Phase 2 preliminary city-only profile.
- `company_name:casefold_key`: 16,050.
- `company_name:unicode_or_whitespace`: 15.
- `job_location:approved_alias`: 4.
- `job_title:casefold_key`: 16,157.
- `job_title:unicode_or_whitespace`: 77.
- `repeated_canonical_skill_tags_collapsed`: 1,076.
- `salary_hour_avg:rounded`: 254.
- `salary_year_avg:rounded`: 9.
- `skill_tag_normalizations`: 76.
- Invalid/nonpositive/overflow salary and malformed skill values: 0 detected among retained records. Salary rounding events are storage corrections, not source-error claims. Original values are preserved; missing values are never imputed.
- Missing annual values: 14,622; valid annual values: 1,601. Missing hourly values: 15,499; valid hourly values: 724. Unknown currency/provenance remains unresolved; no advertised-pay metric is enabled.
- Inherited skill lists: {"missing": 2210, "populated": 14013}. Missing schedules: 180. Missing employer/title/date among retained records: 0/0/0.
- Work arrangements remain unknown. No descriptions, requirements, experience years, salary bounds, native posting IDs or timezone evidence have been invented.

## Validation and review

- All 10 reconciliation/integrity checks have zero violations; PK/FK/unique constraints were enforced during loading. Raw SHA-256 remains unchanged.
- Repeat run, identical relational content: **True**. Semantic SHA-256: `dcefe7b9aa81bfaeb2175b687b5d014e1bc6551fd752c37624a8639aa73b40d0`.
- Assistant inspected 80 accepted records (20 per role, spread through source-row order), plus all 126 ambiguous title/publisher pairs covering 209 records. Title-only conflicts remain unresolved where duties are missing.
- Review corrected compatible Senior Staff seniority and one narrowly documented prior-background/occupation conflict. Final accepted sample has no role disagreements. This is assistant review, not independent human labeling or a measured classifier accuracy.

## Local evidence and remaining limitations

- `data/processed/phase3/job_market.sqlite3`: validated local relational data.
- `row_audit.csv`: every input row, reason, exact-duplicate keeper and retained record key.
- `field_issue_audit.csv`: per-record salary rounding/error and malformed-tag decisions.
- `unresolved_locations.json`: unresolved location labels/counts; reference is not exhaustive.
- `build_summary.json`: counts, code/config hashes, source lineage and environment.
- [Rules/schema guide](../docs/phase3_cleaning_rules.md), [classification review](phase3_classification_review.json), [test/verification record](phase3_verification.json).

Raw/processed data and detail audits remain ignored by Git. Public release still needs the license/attribution/embedded-data review. Source selection, unknown geography/roles and missing/preprocessed fields limit later analysis. Salary medians/rankings, statistical comparisons, charts, Tableau exports and dashboards remain future work.
