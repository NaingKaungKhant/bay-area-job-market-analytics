# Phase 4 analysis contract and reproduction

Phase 4 uses the existing validated SQLite database read-only. The approved historical
source, nine counties, four roles, cleaning rules, skill aliases and database schema
are unchanged. No acquisition, new job data, dashboard, public upload or Git operation
is part of this phase. Attribution: [Luke dataset decision](data_attribution.md).

## Reproduce locally

Use the existing Python 3.11+ environment from the project root:

```bash
source .venv/bin/activate
python -m src.run_analysis
python -m src.execute_analysis_notebooks
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

The existing requirements already contain pandas/numpy/matplotlib/seaborn/Jupyter/pytest;
no statistical library or server database is added. Notebook/nbclient/ipykernel come
with the existing Jupyter environment. The notebook executor uses the current Python
interpreter, a temporary kernel specification/runtime folder, and real Jupyter kernels.
On systems restricting localhost ports, kernel startup may need OS/tool approval.
Do not replace a failed execution with fabricated cell outputs.

`src/analysis.py` verifies Phase 3 code/config hashes, source approval/checksum lineage,
SQLite integrity/foreign keys, source-row coverage, skill bridges and Bay membership.
It compares the actual database's semantic checksum with Phase 3 and checks database
file bytes before/after analysis. The connection uses SQLite `mode=ro` and `query_only`.
The raw directory read stalled on the execution host (including its manifest); Phase 4
therefore does not reopen it or repeat its byte checksum. Original acquisition integrity
is recorded Phase 3 evidence. This does not change the source or require new data.

## One cohort, visible exclusions

All substantive results use `v_target_job_records`: one retained exact-deduplicated
source record with `accepted_title_only` status under the existing Phase 3 rules.
The classifier is conservative and has no original duties to resolve ambiguities.
The cohort audit alone uses all retained facts to show accepted, ambiguous,
unclassified and explicit non-target counts/shares. Those audit cases are never
substituted into role, skill, seniority or geographic denominators.

Record IDs identify source-file lineage, not certified unique advertisements/vacancies.
Uncertain similar-key candidates were retained in Phase 3; no further deduplication
occurs here. Reposts/employer clustering may create dependence. The complete publisher
file is a convenience collection, not a probability sample of Bay Area jobs.

## SQL result dictionary

Named SELECT sections in `sql/003_phase4_analysis.sql` do not create tables or views.
`src/analysis.py` rebuilds all nine summaries independently in pandas from fact and
bridge rows, checking every output column against SQL (float tolerance 1e-10 absolute,
1e-12 relative; integer counts must agree). The report stores query/code hashes,
source release/rule versions, database checksums, environment and result checksum.

| SQL section | Grain | Denominator / interpretation |
|---|---|---|
| cohort_audit | One role-status | All retained Bay facts; not the target analysis cohort |
| role_summary | One accepted role | All accepted records; tag/annual presence and seniority coverage shown |
| skill_by_role | One role × canonical skill | Populated inherited lists in that role; zeros explicit, zero denominator -> null |
| geography_by_role | One resolved Bay location × role | Distinct records with that location; coverage and small-cell flag |
| county_by_role | One county × role | Distinct records within county, even with two localities in same county |
| geography_coverage | One cohort summary | Regional count, city/community/county-only evidence and overlapping memberships |
| seniority_by_role | One explicit/unknown/conflicting seniority × role | All accepted records in that role |
| locality_skill_by_role | One observed location × role × tag | Usable lists in that location/role; only observed tag rows; absent tag row is zero only if a usable denominator exists |
| skill_count_summary | One role with usable lists | Mean/min/max and linear-interpolated Q1/median/Q3 distinct tags per populated list |

Locations are many-to-many: count a record once regionally and once within each qualifying
location/county. Geographic summaries are non-additive even if this release has no
multi-location accepted records. Communities remain communities; the city figure
includes incorporated cities only. County-only records retain a null locality.
No headquarters, search-location or remote-eligibility inference is added.

## Descriptive statistics, comparisons and uncertainty

Role/seniority shares use all accepted records. Skills are inherited publisher tags,
not independent extraction, verified requirements or required/preferred distinctions.
A usable list is populated and safely parsed in Phase 3. Missing, empty and malformed
lists are disclosed separately; they do not become zero skills. Per-role tag percentages
can sum above 100%. Original full-description text is unavailable throughout the cohort.

Quartiles interpolate between sorted tag counts at position `(n-1)*q`, for q=.25,.5,.75.
The box figure uses observed min/max whiskers (not the conventional 1.5×IQR rule), and
shows means separately. These distributions describe tag-list length, not job difficulty.

Illustrative contrasts compare Python (Data Scientist minus Data Engineer), SQL (Data
Analyst minus Data Engineer), and Tableau (Data Analyst minus Data Scientist). Compute
**percentage-point differences**, not relative percent increases. These examples are
exploratory, not preregistered hypotheses or an exhaustive search for significant effects.
All inputs reconcile with SQL. Role-specific list coverage and sample sizes accompany
contrasts. Differences are unadjusted for seniority, company, location or source mix;
no causal interpretation is supported.

The existing KPI policy suppresses skill comparisons/rankings for groups with fewer
than **10 usable lists**; counts remain visible. A zero denominator is unavailable,
not 0%. The threshold is not a reliability guarantee. Large imbalance (especially a
small Machine Learning Engineer cohort), rare tag counts and small city/role cells
still need caution. Small geographic counts are labeled; do not rank sparse skill groups.

For Python/SQL/Tableau, logical missingness ranges are:

- Lower bound: `100 × tagged records / all accepted role records`.
- Upper bound: `100 × (tagged records + unavailable lists) / all accepted role records`.

This varies only unavailable-list content while leaving observed tags unchanged.
For a first-minus-second role contrast, difference bounds are first.lower−second.upper and first.upper−second.lower. These describe logical sensitivity, not statistical confidence.

It is not imputation, a confidence interval, a bound on true requirements or protection
against publisher extraction errors. A gap conditional on observed tags may change
when missing lists are considered. Sample-selection and classification uncertainty
cannot be estimated from these records alone.

No p-values, confidence intervals or resampling-based population claims are produced.
Independent random sampling and stable job identity are not established. Descriptive
contrasts, coverage, logical sensitivity and small-group flags better match the evidence.

## Disabled metrics and limits

Only derived salary **presence/coverage** is measured; annual and hourly fields remain
separate. Currency, advertised/estimated provenance, original pay bounds and comparability
remain unresolved. No salary amounts, medians, pay rankings, currency symbols, outlier
salary filtering, imputation or hourly annualization are introduced. Primary advertised
pay eligibility is zero under the unchanged schema. Phase 4 does not try to resolve
these limitations by downloading more data.

False work-from-home flags do not establish hybrid/on-site work. Explicit arrangement
shares remain unavailable; unknowns are visible. Title-based seniority does not establish
required years, and unknown seniority does not mean junior. The entry/junior category
includes internships under the unchanged rulebook.

Source dates describe 2023 records, without verified original-publication semantics,
timezone or stable collection coverage. No monthly/weekly posting counts, hiring trends,
seasonality inference or current-market claims are produced.

## Artifacts and validation

- `src/run_analysis.py`: reproducible offline report/figure orchestration.
- `src/analysis.py`: queries, independent pandas checks and descriptive contrasts.
- `src/analysis_charts.py`: seven static figures; plotted artists asserted against SQL data.
- `notebooks/02_exploratory_analysis.ipynb`: scope, coverage, role/skill/geography/seniority results.
- `notebooks/03_descriptive_comparisons.ipynb`: tag-count distributions, contrasts and missingness sensitivity.
- `reports/phase4_analysis.json`: aggregate result tables, plot data/hashes, provenance and reconciliation.
- `reports/phase4_findings.md`: brief methods, measured findings and limitations.
- `reports/phase4_verification.json`: actual tests, notebook execution and rerun evidence.
- `reports/figures/phase4_*.png`: local, source-attributed charts, with no embedded raw job rows.

Tests use labeled synthetic TEST_ONLY fixtures to exercise overlapping skill/location
joins, non-target audit records, missing/unusable lists, the n=10 boundary, singleton/
even/odd quantiles, logical bounds, changed data and read-only protections. Synthetic
fixtures never appear in research findings. Local report creation is not publication:
license/attribution/embedded-data review remains required before GitHub/Tableau upload.
Phase 5 remains unstarted and requires explicit approval.
