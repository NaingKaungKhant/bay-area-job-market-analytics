# Proposed architecture

## Active source amendment — October 26, 2026

The approved Phase 2 source is a complete, pinned historical Luke CSV rather than a live job API. Raw storage contains immutable CSV plus source/license evidence and manifest. The generic source-native ID/description/salary-band fields in the conceptual schema below are not available in this source; leave them unavailable rather than inventing IDs, descriptions or pay bounds. A future record lineage key may identify a file row, not an independently verified unique posting. Store inherited role/skill/salary provenance distinctly. Phase 3 now implements the source-specific retained-record model, commented schema, offline cleaning loader and validation. See the [implemented schema/rules](phase3_cleaning_rules.md) and [cleaning report](../reports/phase3_cleaning_report.md). These supersede generic native-ID/salary assumptions below. SQL business analysis and Tableau remain planned. See [Phase 2 results](../reports/phase2_status.md).


Historical Phase 1 conceptual architecture follows. Phase 2 acquisition/profiling and Phase 3 cleaning/database now exist as described above; analytical queries and dashboard remain unimplemented. The original proposed table list is a historical design, not the exact implemented source schema.

```text
Approved Data Source
  -> Raw Data (restricted local snapshots + collection manifest)
  -> Python Cleaning & Validation
  -> SQLite Database
  -> SQL Analytics
  -> Dashboard-Ready Tables
  -> Tableau
  -> Business Insights
```

## Components and purpose

1. **Data source:** A permission-cleared provider or explicitly documented employer-board frame. Record the approved terms, query/board list, collection window and limits. This defines what the project can observe.
2. **Raw data:** Preserve permitted original responses without modifying them. A manifest will record source, safe request parameters, retrieval UTC timestamp, page/cursor, status, counts, checksum and file path. Never log credentials or credential-bearing URLs. Store restricted data outside Git and apply provider retention rules. If raw retention is prohibited, do not acquire under this design until an approved alternative exists.
3. **Python cleaning and validation:** pandas/numpy will normalize fields and produce audit counts, exclusions and quarantined records. Rules cover geography, classification, deduplication, skill aliases, salary provenance and date semantics. Unknown is a valid state, not a reason to invent a value. Reconcile input records with accepted, duplicate and rejected outcomes.
4. **SQLite:** A portable local relational database keeps one posting separate from its many skills and locations. Foreign keys prevent dangling links; transactions avoid half-loaded runs. SQLite is included with Python, so no database server is required.
5. **SQL analytics:** Reusable queries will compute the documented denominators, apply cohort filters, and reconcile totals. Aggregate postings before expanding bridges to prevent inflated counts.
6. **Dashboard-ready tables:** Export permitted aggregate tables at an explicit grain, with role, city, window, counts, coverage and rule versions. Keep separate role/skill and role/city summaries; neither is a table of independent vacancies. Aggregates are published only when source permissions allow them.
7. **Tableau:** Import clean, analysis-ready UTF-8 CSV exports from the validated SQL database using Tableau Desktop Public Edition or an appropriate Tableau Desktop edition on macOS. Plan interactive job demand, salary comparison, technical skill and geographic views with supported filters, unknown categories, non-additive city labels and salary/text coverage. Reconcile every metric with SQL at the same grain and filter state; do not sum overlapping city counts or average subgroup medians. Keep the workbook local until publication is authorized. Tableau Public uploads expose workbook data, so inspect all CSV fields and embedded extracts and publish only source-cleared content. CSV refresh/republication is manual. See the [Phase 5 delivery contract](project_roadmap.md) for export specifications, reconciliation and privacy requirements.
8. **Business insights:** Explain observed patterns, limitations, and actionable hypotheses. Distinguish evidence from recommendations; never infer actual hires from advertisements.

## Proposed relational schema

Keys are local surrogate integer IDs unless stated otherwise. These names describe a design, not existing tables. Text dates use ISO 8601; observation timestamps are UTC. Monetary values should use integer cents with documented units rather than floating-point storage. Nullable attributes remain unknown; missing numeric values are not zero.

| Table | Grain and primary key | Important attributes / foreign keys | Constraints and relationships |
|---|---|---|---|
| dim_companies | One resolved employer identity; company_id PK | canonical_name, normalized_name, optional verified domain | One company to many postings; identical names alone do not prove identity; staffing firm versus client preserved in provenance |
| dim_locations | One resolved work-location entity; location_id PK | city nullable, county nullable, state, country, location_precision, in_bay_area, reference_version | One location to many posting-location links; city/state/country and precision distinguish same-name places; county-only entities supported |
| dim_skills | One canonical skill; skill_id PK | canonical_name, category, taxonomy_version | Unique canonical name within taxonomy version; aliases live in a versioned rule file, not duplicated skill rows |
| fact_job_postings | One canonical observed advertisement, latest accepted state; job_posting_id PK | company_id FK nullable; original_title, normalized_title, role, role_status, seniority, experience_min/max, employment_type, work_arrangement, published_at nullable, publication_date_status, first_seen_at, last_seen_at, description_status, salary bounds/currency/period/type/provenance, salary_eligible, rule_version | company FK -> dim_companies; one target role or explicit unresolved/out-of-scope status; check salary bounds; no location FK forcing a single city |
| bridge_job_skills | One accepted posting-skill pair; (job_posting_id, skill_id) composite PK | both FKs, evidence, evidence_section, requirement_status, extractor_version | Many-to-many postings and skills; repeated mentions collapse to one pair |
| bridge_job_locations | One posting-work-location association; (job_posting_id, location_id) composite PK | both FKs, raw_location_text, evidence, confidence, scope_status | Many-to-many postings and locations; preserves outside-region locations too; required extension to support the scope |
| source_posting_records | One source-native posting; source_record_id PK | source_name, board_namespace, source_posting_id, job_posting_id FK, source_url, requisition_id, duplicate_decision/evidence | Unique (source_name, board_namespace, source_posting_id); many source records may map to one canonical posting; no IDs merged across boards accidentally |
| collection_snapshots (optional until repeated collection) | One collection run; snapshot_id PK | source/frame_version, started_at, finished_at, status, expected/completed pages, row_count, manifest_path, checksum, terms_reference | A failed or partial run is never treated as a complete empty inventory |
| posting_observations (required if snapshots/history used) | One source record observed per run; (snapshot_id, source_record_id) composite PK | snapshot_id FK, source_record_id FK, observed_at, payload_hash, permitted raw reference, normalized_state/version reference | Resolves many-to-many snapshots/source records; supports membership and retained as-of state rather than counting repeated sightings as new jobs |
| posting_salary_bands (when multiple bands exist) | One explicit source salary band per observation; salary_band_id PK | observation composite FK, band ordinal, raw bounds/unit/currency, advertised_or_estimated, base_or_total, raw applicability, location_id FK nullable, seniority applicability | Distinct ordinal per observation; preserve raw applicability if city mapping is unresolved; multiple bands do not multiply posting counts |

A single-band source can populate the fact salary attributes directly through a documented chosen observation. Multiple-band sources require the salary-band extension; the fact holds only an eligible, unambiguous selected band or null with exclusion reason. The fact's latest state supports a current report; historical/window reports must reconstruct the selected normalized observation state and retain canonical mapping/rule versions. Raw hashes alone cannot reconstruct historical pay/classification if payloads are unavailable.

## Relationship sketch

```text
dim_companies 1 ---- many fact_job_postings
fact_job_postings 1 ---- many bridge_job_skills many ---- 1 dim_skills
fact_job_postings 1 ---- many bridge_job_locations many ---- 1 dim_locations
fact_job_postings 1 ---- many source_posting_records
source_posting_records 1 ---- many posting_observations
collection_snapshots 1 ---- many posting_observations
posting_observations 1 ---- many posting_salary_bands
```

## Integrity, provenance and reproducibility

All future loads will enable SQLite foreign-key enforcement and check key uniqueness, referential integrity, allowed statuses and salary ordering. Unknown companies may use a null company FK with source employer text retained; do not merge every missing employer into a real company. Missing descriptions exclude skill denominators; missing publication dates disable publication-time classification for those records. Geography and role uncertainty remain auditable.

Retain a source-to-canonical crosswalk, merge/split decisions, raw field text when allowed, selected observation, extraction/classification versions and timestamps. Duplicates across queries and snapshots are reconciled before reporting. A posting with several skills and cities must still count once regionally. Do not deduplicate solely on title and company.

Reproducibility means a future user can understand the frame and rerun code with authorized access. Live source contents will change, so identical results require permitted versioned snapshots, checksums and rule/environment versions. A public repository may contain documentation, code and approved aggregates; it must not presume permission to distribute raw descriptions, credentials or local databases. No permission is granted merely because an endpoint is public.

## Planned quality and analysis checks

Phase 3 tests will cover alias boundary cases, conflicting roles, nine-county decisions, duplicate observations, multi-city non-additivity, salary exclusions and bridge uniqueness. SQL reconciliation will verify four-role totals, coverage bounds and unique posting counts. Phase 4 may compare distributions and effect sizes; any resampling intervals describe this sample's variability, not representative market confidence. No tests or results are implemented in Phase 1.
