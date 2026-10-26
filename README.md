# 2023 Bay Area Data Jobs & Skills Analysis

**Status: Phase 2 acquisition and raw-data profiling complete. Phase 3 has not started and requires approval.**

An end-to-end Data Analyst portfolio project examining historical data-career advertisements in the nine-county San Francisco Bay Area. The approved source is Luke Barousse's 2023 dataset. This is a historical observed-record study, not current market intelligence or a count of actual hires.

## Business problem and objectives

A hypothetical workforce intelligence/career-services team wants to understand advertised data-career roles, inherited skill tags and geographic differences to help graduates prioritize learning. Inconsistent titles, missing pay, duplicate candidates and preprocessed fields require transparent definitions.

The project will demonstrate reproducible Python ingestion, relational design, SQL, statistical reasoning and Tableau. Acquisition and quality profiling are implemented; production cleaning, SQLite, business analysis and the dashboard remain planned. Source limitations are documented instead of filled with invented values.

## Scope and analytical questions

Geography includes Alameda, Contra Costa, Marin, Napa, San Francisco, San Mateo, Santa Clara, Solano and Sonoma counties, including the requested San Francisco, San Jose, Oakland, Palo Alto, Mountain View, Sunnyvale, Santa Clara, Cupertino, Redwood City, Menlo Park, Fremont and Berkeley cities. Phase 2 uses a conservative exact city/state diagnostic across 101 incorporated-city references; unincorporated, vague and multi-location evidence remains for later review.

Target roles are Data Analyst, Data Scientist, Data Engineer and Machine Learning Engineer across industries and seniorities. Publisher labels are evidence, not our final accepted classifications. Ambiguous original titles remain reviewable; senior labels will not be silently discarded or merged. Remote eligibility and actual work location stay distinct; search_location and employer headquarters do not establish a Bay Area job location.

Supported candidate questions, subject to later validation:

1. How are historical retained records distributed across the four target roles and explicit title-based seniority?
2. Which publisher-extracted skill tags occur within roles, and what usable-tag coverage supports comparisons?
3. How do role/skill distributions differ across eligible cities, with small samples and multi-location rules visible?
4. What does missingness tell us about the reliability of role, location and pay comparisons?
5. What can comparable publisher-derived annual salary values show, once original units/meaning are established?

Original-text skill requirements, verified advertised salary midpoints, detailed experience requirements, explicit hybrid/on-site shares and population hiring trends are unavailable in this source. No assumption that missing/false flags mean no requirements or on-site work is permitted. The [business requirements](docs/business_requirements.md) and [KPI dictionary](docs/kpi_dictionary.md) contain active dataset amendments and the original stricter conceptual reference.

## Source, license and measured Phase 2 coverage

Source: [Luke Barousse data_jobs](https://huggingface.co/datasets/lukebarousse/data_jobs/blob/ed776e5a0a8c40ea9d5efbd800772ae52e140f3e/README.md), pinned revision `ed776e5a0a8c40ea9d5efbd800772ae52e140f3e`. The publisher declares Apache-2.0. See [data attribution](docs/data_attribution.md) and the [license copy](docs/data_licenses/Apache-2.0.txt). No employer pages were scraped and no credentials were used. Raw redistribution is not enabled; any public outputs require an attribution/embedded-data review.

The verified 231,152,089-byte CSV contains **785,741 raw records and 17 fields**, all with source dates in 2023. Preliminary exact-city matching finds **15,892 records across 87 cities and all nine counties**. These are data-quality diagnostics, not final unique-posting counts or market findings. The [Phase 2 report](reports/phase2_status.md) records role coverage, missingness, duplicate candidates and limitations.

Publisher-derived annual salary values appear in 1,584 preliminary Bay Area records (9.97%); populated inherited skill lists appear in 13,737 (86.44%). All matched work-from-home flags are False, which cannot distinguish hybrid from on-site. Original descriptions, native posting IDs, salary bounds/currency/provenance are absent. No salary median, skill ranking or hiring trend has been calculated.

Greenhouse/Adzuna research and the USAJOBS proposal remain historical alternatives; the active source is Luke's dataset. The blocked Greenhouse configuration is retained separately, never silently cleared.

## Technology and planned architecture

Python 3.11+, pandas, numpy, SQLite via built-in sqlite3, SQL, matplotlib, seaborn, Jupyter Notebook, Tableau on macOS, pytest, Git and GitHub.

```text
Pinned CSV -> Immutable raw data + manifest -> Python cleaning/validation
  -> SQLite -> SQL analytics -> Approved CSV exports -> Tableau -> Business insights
```

Only acquisition and raw profiling are implemented. The [architecture](docs/architecture.md) still proposes company/location/skill dimensions, a canonical posting/record fact and skill/location bridges for Phase 3. Any future file-row key identifies lineage, not a certified unique vacancy. Tableau Desktop Public Edition or an appropriate Desktop edition on macOS is planned; Tableau Public uploads must contain only permission-cleared fields/extracts.

## Reproduce Phase 2

From this existing project directory, use Python 3.11+ and the [requirements](requirements.txt):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.luke_dataset acquire
python -m src.luke_dataset profile
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

The local `.venv` already exists; do not recreate it just to read the report. Actual execution used a project environment for acquisition/tests and bundled Python/pandas for the full profile; the [environment record](reports/phase2_test_environment.json) records versions and reproducibility limits. The requirements are ranges, not a full lockfile. SQLite requires no separate Python package; Tableau/Git are external software.

Acquisition needs network access only if the verified snapshot is absent. It downloads the immutable revision, checks publisher file size/SHA-256 and records a manifest. Re-running reuses validated bytes. Profiling/tests are offline. Open [the executed profiling notebook](notebooks/01_data_profiling.ipynb) for real coverage/quality tables. It verifies provenance before reading the stored profile; it contains no fabricated example market data.

## Repository layout and privacy

- `config/`: approved source/release, access decision and versioned city/county reference; blocked Greenhouse configs are retained as history.
- `data/raw/`: ignored original CSV, source evidence and manifest; `data/processed/` remains empty pending Phase 3.
- `src/luke_dataset.py`: approved acquisition and raw quality profiler. `src/phase2.py` retains the blocked legacy Greenhouse offline tool.
- `tests/`: synthetic TEST_ONLY structural tests, not research observations.
- `notebooks/01_data_profiling.ipynb`: Phase 2 integrity and raw quality review.
- `docs/`: requirements, KPIs, source evidence/attribution, execution plan, observed field dictionary, architecture, roadmap and Git guide.
- `reports/`: actual raw profiling results, acceptance review and environment/provenance summaries. Historical reviews are labeled separately.
- `sql/`, `dashboard/`, `reports/figures/`: placeholders for later approved phases.

`.env.example` contains empty names only. No API key is required for this source. `.gitignore` excludes raw/processed data, local databases, secrets, environments, caches and OS metadata. Review notebook outputs and Tableau extracts before sharing. Private GitHub visibility does not replace license compliance. No commit or push was performed in this task; the [Git guide](docs/github_workflow.md) explains the workflow.

## Phases and deliverables

| Phase | Scope | Status |
|---|---|---|
| 1 | Setup, Business Understanding, Data Feasibility | Complete; source-specific amendments recorded |
| 2 | Data Acquisition & Data Profiling | Complete for approved historical Luke source |
| 3 | Data Cleaning, Validation & SQL Database | Not started; requires approval |
| 4 | Exploratory & Statistical Analysis | Planned |
| 5 | Tableau Dashboard | Planned |
| 6 | Business Recommendations, GitHub Portfolio & Resume | Planned |

The [roadmap](docs/project_roadmap.md) retains the requested five-day accelerated target and its effort/capacity caveats. Later deliverables are a tested cleaning workflow, local relational database, SQL KPIs, statistical notebooks/figures, permitted reporting CSVs, Tableau workbook and business brief. They are not completed assets. Phase 2 ends here; Phase 3 requires explicit approval.
