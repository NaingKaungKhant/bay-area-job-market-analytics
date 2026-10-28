# Phase 5 export dictionary

These are local derived aggregates from the approved 2023 Luke dataset and unchanged
`v_target_job_records` cohort. They are not source advertisements or unique vacancies.
SQL: `sql/004_phase5_exports.sql`. Run: `python -m src.tableau_exports`.
Files live in ignored `data/processed/phase5/`; manifest also has a readable copy at
`reports/phase5_export_manifest.json`. No database table/view/schema is created.

## Design and permitted controls

One long metric table supplies every worksheet. There are **no Tableau joins,
relationships or blends** between aggregate exports. `scope_catalog.csv` and
`role_catalog.csv` document parameter values; do not drag them into a data model.
Precomputed alternatives make arithmetic explicit and prevent bridge multiplication.

Select exactly one Scope and one Role parameter. Scope can be All Bay Area, one county,
one incorporated city, one community or one county-only source location. A record enters
a scope if any explicit Bay location matches it. Role is All roles or exactly one of
four accepted roles. Geography view selects City, County, Community or County-only for
the location panel only. These are controls, not newly expanded source/geographic scope.

No multi-select geography/role, skill-as-global-filter, seniority-as-global-filter,
freeform date filter, global mark-filter actions, drill-through sum, grand totals or
subtotals are enabled. Such selections need fresh distinct-record SQL; adding displayed
rollups would be wrong. Selecting a zero-record slice returns a count of zero and null
rates, with the global classification audit still visible.

Role shares keep all four accepted roles in the selected geography as denominator.
Selecting Data Analyst hides other role bars; it does not redefine DA's share to 100%.
Skills/seniority/coverage use the selected role-and-geography cohort and their documented
conditional denominator. Location counts show all Bay associations of selected records;
a multi-location record can appear under several displayed places, including another
location of a record that qualified through the selected place. Do not sum locations.

## Common serialization

UTF-8, comma delimiter, one header, LF line endings, decimal point, no thousands
separators in numbers. Counts are unformatted integers. `rate` is a fraction from 0 to 1;
format it in Tableau as Percentage, one decimal. Do not multiply by 100 again.
Empty numeric CSV fields mean unavailable/null, never zero. Catalog text blanks mean
not applicable (regional scope has no county or location ID). Data source/rule fields
are exact identifiers, not numbers. Exports contain no salary values/currencies, dates,
arrangements, job titles, descriptions, company names or record/native posting IDs.

## dashboard_metrics.csv

Grain: **one metric category in one panel, one geographic scope and one role selection**.
Composite key: `(scope_key, role_selection, panel, category_type, category)`.
It is not a record fact table; `COUNT(*)` counts metric rows, not job records.

| Field | Type / nulls | Meaning and safe use |
|---|---|---|
| scope_key | text, required | Exactly one parameter value; alternatives overlap and cannot be summed |
| role_selection | text, required | All roles or one accepted role; do not combine All roles with its components |
| panel | text, required | roles / skills / geography / seniority / coverage / classification; select one per worksheet |
| category_type | text, required | Role, Skill, Seniority, Coverage, Whole retained dataset; geography explicitly City/County/Community/County-only |
| category | text, required | Label within the panel; combine with category_type for a unique meaning |
| numerator | integer >=0, required | Record count for this exact metric/category; only aggregate after selecting one slice/panel/category |
| denominator | integer >=0, required | Defined below; repeated contextual value, never SUM across categories |
| comparison_allowed | integer 0/1, required | Skill groups require >=10 populated inherited lists; other panels use 1 (zero denominator still produces null rate) |
| warning | text, required | Coverage, suppression, global audit or non-additivity note for the relevant panel |
| category_order | positive integer | SQL order; skills use descending count/alphabetical ties, geography descending count within view type; no ranking when skill denominator <10 |
| rate | real fraction or null | numerator/denominator only if denominator>0 and comparisons allowed; MAX per category or guarded Tableau formula, never SUM |
| source_revision | text, required | Pinned `ed776e5a0a8c40ea9d5efbd800772ae52e140f3e` |
| cleaning_rule_version | text, required | Existing `luke-cleaning-v1` (no mapping change) |

### Panel denominators

| Panel | Numerator | Denominator and scope |
|---|---|---|
| roles | Accepted records of the displayed role | All four accepted roles in selected geography, even with a single-role selector |
| skills | Distinct selected records with inherited canonical tag | Populated skill lists in selected role/geography; missing/empty/malformed lists excluded and separately disclosed |
| seniority | Selected records in explicit/unknown/conflicting category | All selected accepted records; unknown does not mean junior; entry/junior includes interns |
| geography | Distinct selected records associated with displayed Bay location/county | All selected records; membership rates are non-additive across places |
| coverage | Selected count, usable/missing/empty/malformed lists, unknown/conflicting seniority or annual field presence | All selected records; annual field presence is not comparable advertised salary |
| classification | Count in each original role_status | ALL retained Phase 3 records (16,223), deliberately global and unaffected by selection; audit label states this |

All skill taxonomy values are exported for every selection, including observed zero
counts. A null/suppressed rate is not a zero rate. The top-12 percentage sheet excludes
groups with <10 usable lists; the separate alphabetical Skill detail counts sheet retains
counts/denominators without pretending that sparse rates support a ranking.

## scope_catalog.csv

Grain/key: one `scope_key`. Fields: `scope_key` (required text), `scope_type` (region,
county, city, community), `location_id` (nullable integer, internal Phase 3 dimension key;
not a source posting ID), `county` (nullable text). Location-based county-only evidence
uses `scope_type=county` with nonnull location_id and a distinct County-only location label.
Regional/county rollups have null location_id; the regional row also has null county.
It is a control dictionary, not additive statistical data. Some city/role combinations
have no accepted records: zero results are valid, not evidence of missing export rows.

## role_catalog.csv

Grain/key: one `role_selection` text value: All roles plus Data Analyst, Data Engineer,
Data Scientist, Machine Learning Engineer. It defines a single-choice parameter.
No ambiguous/unclassified role is added to the accepted cohort.

## Manifest and validation

`export_manifest.json` records full effective query SHA-256 (shared CTE + SELECT), SQL
file/script hashes, UTF-8 file hashes, headers, row counts, keys, original source/rule
versions, Phase 3 semantic and database byte checksums, real validation outcomes and
rerun content hash. The report copy does not embed CSV rows. Counts and rates round-trip
back from CSV; all metric keys, numerator/denominator conditions, nulls and n=10 suppression
are checked. Phase 4's nine independent SQL/pandas comparisons remain required before export.

`reports/phase5_reconciliation.csv` contains representative direct-SQL controls for
default, role, city-role, county, community, sparse and zero-result states. It records
expected SQL values and matched CSV values. Tableau actual columns remain blank and
status NOT_RUN until measured in Tableau. It includes role shares, seniority, skills,
coverage, geographic bars and the unfiltered classification audit. A populated manual
actual column blocks regeneration until that checklist is archived, protecting user work.
No checklist row claims native Tableau validation based only on XML or Python tests.

## Refresh and publication

Regenerate all CSVs as one set; rebuild the local draft package from the new manifest.
A packaged workbook contains a copy of the CSV, so changing external CSVs does not
refresh an existing package. Repackage or explicitly replace/refresh its data source
locally. After any refresh repeat native acceptance checks and screenshots. No live
SQLite connection or automatic Tableau Public refresh is claimed.

These are modified derived datasets. Preserve Luke Barousse attribution and Apache-2.0
license, inspect every embedded field/extract/hidden worksheet, and obtain separate
publication approval before sharing any CSV, TWB/TWBX, screenshot or Tableau Public link.
Aggregation alone does not remove publication restrictions. No publication occurs here.
