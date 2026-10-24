# Bay Area Tech Job Market Intelligence & Skills Demand Analytics

**Current status: Phase 1 — setup, business understanding and documentation-based source feasibility complete. Phase 2 awaits explicit approval and source clearance.**

This portfolio project is designed for an Applied Mathematics graduate preparing for entry-level Data Analyst roles. It will demonstrate how to turn imperfect job advertisements into auditable business measures using Python, SQL, relational design, statistics and analytical storytelling. No postings have been collected and no salary, skill or hiring findings are available yet.

## Business problem and objectives

A hypothetical workforce intelligence/recruitment analytics company wants to compare advertised tech-role demand, salary bands and technical skills across the San Francisco Bay Area. Inconsistent titles, duplicate advertisements, missing pay and multi-city listings can produce misleading comparisons. The project will make those decisions explicit and reproducible.

Planned objectives are to build a documented sample, classify roles transparently, normalize locations and pay, validate a local relational database, answer supported questions in SQL/Python and communicate results through Tableau and a business brief. Observed advertisements are not actual hiring activity, headcount or a complete count of vacancies.

## Scope

Geography follows the nine-county Bay Area: Alameda, Contra Costa, Marin, Napa, San Francisco, San Mateo, Santa Clara, Solano and Sonoma. This includes San Francisco, San Jose, Oakland, Palo Alto, Mountain View, Sunnyvale, Santa Clara, Cupertino, Redwood City, Menlo Park, Fremont, Berkeley and other eligible places. See the [scope rules and official geographic reference](docs/business_requirements.md).

The four target roles are Data Analyst, Data Scientist, Data Engineer and Machine Learning Engineer across employer industries and seniorities. Ambiguous titles remain reviewable; vendor labels and keywords alone do not force a role assignment. Seniority and employment type will be separate filters.

Core geographic membership requires an explicit qualifying work location. Nationwide remote-accessible jobs without that association are separate from core totals. Hybrid and on-site locations follow the same county boundary. Unknown/conflicting arrangements stay visible. A multi-city posting counts once regionally and once in each explicitly listed eligible city; city counts are non-additive.

## Planned analytical questions

1. What is the count and share of observed postings for each target role?
2. How do comparable advertised annual base-pay distributions differ by role and explicit seniority?
3. Which technical skills are mentioned within each role, given available description coverage?
4. How do role mix and skill mentions vary across eligible cities?
5. What seniority and minimum-experience requirements are explicitly stated?
6. What remote, hybrid and on-site shares can be explicitly identified, and what is unknown?
7. Only with valid dates and comparable coverage, how do observed posting counts change over time?

## Proposed KPIs

Unique observed postings; posting share by role; median advertised annual base-pay midpoint; salary coverage; skill mention frequency; skill mention percentage by role; postings by city; arrangement shares and identification coverage; and conditional publication-time posting counts.

The [KPI dictionary](docs/kpi_dictionary.md) defines formulas, fields, quality conditions, biases and interpretation. Primary pay metrics exclude estimated salaries, missing/open-ended ranges and hourly conversions. Skill percentages use postings with usable text and disclose text coverage. No KPI results exist in Phase 1.

## Planned technology and architecture

Python 3.11+, pandas, numpy, SQLite via Python's built-in sqlite3, SQL, matplotlib, seaborn, Jupyter Notebook, Tableau, pytest, Git and GitHub. requests and python-dotenv are planned for approved API access and local configuration. Tableau is external software, not a Python package. Plan to use Tableau Desktop Public Edition or an appropriate Tableau Desktop edition on macOS. Published Tableau Public content is public; upload only source-cleared CSVs/workbooks after a publication review, and keep restricted work local. Confirm edition and Mac compatibility before Phase 5.

```text
Approved Data Source -> Raw Data -> Python Cleaning & Validation
  -> SQLite -> SQL Analytics -> Dashboard-Ready Tables -> Tableau -> Business Insights
```

The [architecture document](docs/architecture.md) proposes company/location/skill dimensions, one canonical-posting fact, posting-skill and posting-location bridges, source provenance and optional collection history. Tables and pipelines are designs only; no SQL schema or database exists yet.

## Data source status

Official documentation was researched on October 23, 2026; services were not tested with live posting requests. The [evidence-based feasibility assessment](docs/data_source_feasibility.md) compares Greenhouse, Adzuna, USAJOBS, a publisher-hosted historical dataset, BLS OEWS and The Muse, including unresolved permissions, coverage and access.

- **Conditional primary:** Greenhouse employer boards, because documented full-description access fits the skills objective. Requires approved employer sampling and storage/publication rights.
- **Conditional fallback:** Adzuna, subject to terms/access clearance and acceptance of description-snippet limits.
- **Supplementary:** BLS OEWS for contextual employment/wages; USAJOBS for a separately labeled federal perspective. A historical public dataset remains a reserve candidate.

These are recommendations, not cleared acquisition plans. No data, credentials or API responses are included. Do not infer permission to redistribute raw records or even aggregates from public access alone.

## Repository contents

```text
bay-area-job-market-analytics/
  README.md
  requirements.txt
  .gitignore
  .env.example
  data/
    raw/.gitkeep
    processed/.gitkeep
  docs/
    business_requirements.md
    kpi_dictionary.md
    data_source_feasibility.md
    architecture.md
    project_roadmap.md
    github_workflow.md
  src/__init__.py
  sql/.gitkeep
  notebooks/.gitkeep
  dashboard/.gitkeep
  reports/
    phase1_quality_review.md
    figures/.gitkeep
  tests/.gitkeep
```

Completed: the files above, documented decisions, source research and [Phase 1 quality review](reports/phase1_quality_review.md). Folder placeholders deliberately contain no datasets, ETL, analytical notebooks, SQL tables, dashboard or results. Expected later deliverables are permitted acquisition manifests, validated SQLite storage, tested processing code, SQL KPIs, notebooks/figures, reporting exports, a Tableau dashboard and a business recommendations brief.

## Setup for Phase 1

Reading the Markdown documents requires no installation, account or API key. To prepare an optional local environment, open a terminal in this project directory and run:

```bash
python3 --version  # confirm Python 3.11 or newer
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux; Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Installation is optional for reviewing Phase 1 and was not performed as part of this task. Version ranges in requirements are a starting compatibility policy, not a tested lockfile. After a successful authorized setup in Phase 2, record resolved versions for reproducibility. SQLite needs no separate Python package. Do not run an ingestion command: none exists yet.

The `.env.example` contains empty placeholder variable names only. No `.env` is needed in Phase 1. When an approved later phase needs credentials, copy it locally to `.env`, fill only the selected provider's values privately and keep it ignored. Never put keys in notebooks, screenshots, request logs or GitHub. Source restrictions also apply to exported files; the ignore rules are a safeguard, not a license decision.

Git tracks this project locally; the chosen GitHub visibility is private while developing. The [Git and GitHub working guide](docs/github_workflow.md) explains commits, branches, pushing, pull requests and GitHub Desktop. Check `git remote -v` and the GitHub commit history to verify remote linkage and upload status; a local commit alone does not mean the project is on GitHub. Review staged files and source permissions before every upload. Git setup does not authorize Phase 2.

## Project phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Setup, Business Understanding, Data Feasibility | Complete: documentation and skeleton only |
| 2 | Data Acquisition & Data Profiling | Planned; requires explicit approval and source gates |
| 3 | Data Cleaning, Validation & SQL Database | Planned |
| 4 | Exploratory & Statistical Analysis | Planned |
| 5 | Tableau Dashboard | Planned |
| 6 | Business Recommendations, GitHub Portfolio & Resume | Planned |

The [six-phase roadmap](docs/project_roadmap.md) lists goals, deliverables, acceptance criteria, dependencies and estimated effort, including the five-day accelerated target after approval and prerequisites. Its unchanged remaining estimate is 48–84 focused hours; the five-day target is ambitious and not a guaranteed normal-hours schedule. Phase 5 will prepare analysis-ready SQL-to-CSV exports and reconcile the interactive Tableau dashboard with SQL before any authorized publication. Phase 1 ends here. Source permission, sample design and the Phase 2 approval decision remain outstanding.
