# Phase 2 — approved historical acquisition and profiling

Completed October 26, 2026 for the approved Luke Barousse source. This supersedes the earlier Greenhouse-only readiness plan; the blocked Greenhouse configuration is preserved as `config/greenhouse_plan.json` and `config/greenhouse_access.json`. No Phase 3 implementation is included.

## Source, population and permissions

The user approved Luke's dataset after discussion of historical scope, publisher-derived salary/skills and missing original evidence. `config/phase2_plan.json` pins revision `ed776e5a0a8c40ea9d5efbd800772ae52e140f3e`, exact file, expected byte size and publisher LFS SHA-256. `config/source_access.json` records Apache-2.0 evidence and approved local Phase 2 use. See [data attribution](data_attribution.md) for the exact source and license.

The sampling frame is the complete pinned CSV, not selected favorable rows: 785,741 records with dates in 2023. Country/role/location labels are inherited. Initial Bay Area coverage uses exact United States + recognized city, CA/California matches against the versioned 101-city reference from [Bay Area Census](https://census.bayareametro.gov/cities-counties). This is a preliminary coverage diagnostic, not final cleaning/classification. Nationwide remote, vague regional labels, multi-location strings, aliases and unincorporated places are not inferred from headquarters or search_location. Later geographic review may change the cohort.

## Acquisition

`src/luke_dataset.py acquire` downloads only the approved pinned CSV and source/license documentation via HTTPS without credentials. It streams within a 300 MB project cap, validates the exact expected bytes and SHA-256, and installs the final file only after successful verification. Transient request failures have a bounded retry count; incomplete temporary files are removed. It reuses an already verified snapshot instead of downloading again. There is no live scrape or API-key use.

The ignored local manifest records source/revision/file, requested URL without redirected signed tokens, actual UTC retrieval start/end, size, checksum, source README/license hashes, completion status and row count. A complete checked file, not an HTTP error or partial download, is required for profiling. No source-native row ID is created as a supposed unique vacancy ID.

## Profiling and reproducibility

The whole CSV is read in 50,000-row chunks as original strings with explicit missing-token handling. The profiler checks the exact 17-column schema, nonblank date validity/year coverage, field missingness, publisher role/country categories, raw duplicate fingerprints, and preliminary city/county coverage. It also inspects inherited skill-list structure safely with `ast.literal_eval`, pay-field numeric validity/presence and raw arrangement flags. It does not compute salary medians, rank skills, classify accepted roles or construct the canonical SQL cohort.

The profiling run used the bundled Python 3.12.14/pandas 2.2.3/numpy 2.3.5 runtime; software paths/versions are recorded in the environment report. The existing project `.venv` remains available for tests and acquisition. The notebook uses the stored profile and verifies the pinned raw hash before displaying diagnostic tables. The same raw input and rules reproduce counts; observation/profile timestamps can differ between runs.

From the project root:

```bash
.venv/bin/python -m src.luke_dataset acquire
.venv/bin/python -m src.luke_dataset profile
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
```

Acquisition needs network access only if the verified file is absent. Profiling/tests are offline. `notebooks/01_data_profiling.ipynb` shows the real profile. Full counts and coverage are in [the status report](../reports/phase2_status.md) and [machine-readable profile](../reports/luke_2023_profile.json). These are data-quality findings, not final job-market insights.

## Handoff boundary

No raw records were cleaned, dropped, imputed or normalized into production tables. No SQLite schema/database, canonical deduplication, accepted role classifier, independent skill extraction, statistical comparisons or Tableau dashboard was implemented. Source limitations are resolved by explicit disabled/revised metrics in the [KPI dictionary](kpi_dictionary.md). Phase 3 still requires approval. No commit, push or branch change was made.
