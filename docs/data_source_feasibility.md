# Data source feasibility

Research date: October 23, 2026. Status: documentation-only assessment. Official documentation was read through the web tool. No posting endpoint was called, no credentials were used, no account was created, and no posting dataset was downloaded or previewed. Field descriptions below are documentation claims, not observations from working API responses. Reachable documentation does not prove live service availability, account approval or Bay Area record coverage.

**Evidence labels:** Verified = stated in accessible official documentation; inferred = our assessment from that documentation; unresolved = not established in this phase. A source's own dataset card is primary evidence of what its publisher claims, not independent verification of underlying collection rights or data quality. No third-party pricing or rate-limit claims are treated as verified.

## Candidate comparison

| Candidate | Access and current availability | Fields and geography | Skills, freshness and history | Portfolio assessment |
|---|---|---|---|---|
| Greenhouse Job Board API | Verified: public GET access without authentication, by employer board token; documentation reachable. Actual boards/service not tested. | Verified: title, location, post/job IDs, full content option and updated_at; optional pay-range detail. Employer identity needs board mapping. Inferred: eligible Bay Area records may exist on selected boards; volume unverified. | Inferred: full descriptions suit auditable extraction. updated_at is not proof of original publication. Historical archive not verified. | Conditional primary: strongest documented description access among assessed commercial-board options; curated employer sample, not market-wide coverage. |
| Adzuna API | Verified: app_id/app_key registration; REST API and search documentation reachable. Account and US service not tested. | Verified: title, company, location, salary bounds/prediction indicator and created shown in documentation; descriptions are snippets. US Bay Area coverage, pay-period semantics and created meaning need validation. | Inferred: snippets undercount skills. Historical salary endpoint is not a raw-posting archive. | Conditional fallback: broader aggregation is attractive but sampled coverage and skills completeness must be assessed. |
| USAJOBS Search + Historic JOA | Verified: Search authentication documented; pages reachable. No API calls. Historic tutorial exists, but access requirements need reconciling with current authentication guidance. | Verified: title, organization, locations, pay range/period, publication date, qualifications/duties fields documented. Local role volume unknown. | Inferred: qualification/duty text can support skills extraction; historic federal announcements may support a retrospective study after validation. | Supplementary or explicitly federal-only alternative; does not replace a private-sector tech-role frame without changing scope. |
| lukebarousse/data_jobs public dataset | Verified: publisher card reachable; CSV and Apache-2.0 label. Files not downloaded or inspected. | Publisher documents title, company, location, dates, derived salary averages and extracted skills. Full descriptions and source-native IDs not established by the card. Local coverage unverified. | Publisher describes 2023 postings. Inferred: historical teaching resource, not evidence of today's market; preprocessed labels require audit. | Reserve historical candidate; provenance and underlying redistribution rights unresolved. Not the default fallback for current intelligence. |
| BLS Occupational Employment and Wage Statistics (OEWS) | Verified: official program and copyright pages reachable. No data downloaded. | Annual occupational employment/wage estimates by state and metro/nonmetro areas; no job-level title/company/description records. | Inferred: useful contextual benchmark, not skill extraction or posting activity. Geographic and occupational crosswalks needed. | Recommended supplementary context only; cannot supply the core posting KPIs. |
| The Muse API | Official developer URL timed out repeatedly in this research environment. | Field availability and Bay Area coverage unresolved. | Freshness, description completeness and history unresolved. | Not recommended pending accessible official documentation. Third-party descriptions were not accepted as verification. |

## Source evidence and operating constraints

### Greenhouse — conditional preferred primary

Official [Job Board API documentation](https://docs.greenhouse.io/job-board.html) documents board-specific listings, `content=true`, post IDs distinct from internal job IDs, location and update time, and optional `pay_transparency` ranges on job detail. Public GET access is unauthenticated. There is no documented global Bay Area search in the assessed page; collection would require an explicit employer-board frame. The list endpoint describes returning all posts on a board; a numeric request quota, fee schedule and historical-post archive were not established. Do not import Harvest API limits into this API's plan.

The attempted [Greenhouse terms URL](https://www.greenhouse.com/legal/terms-of-service) was inaccessible through the research tool; no terms clearance is claimed. Unresolved: permission for this project's local retention, historical snapshots, derived publication and raw redistribution. Public accessibility alone is insufficient. Review applicable platform/employer terms and obtain clarification where needed before acquisition. Planned public GitHub suitability is conditional on publishing authorized code/documentation and permitted outputs. Full text makes this the preferred technical choice, but the sample must be labeled as selected employer boards. Original publication trends may remain unavailable.

### Adzuna — conditional fallback

Official [overview](https://developer.adzuna.com/overview), [search documentation](https://developer.adzuna.com/docs/search) and [API terms](https://developer.adzuna.com/docs/terms_of_service) were accessible. Search is page-based with a results-per-page parameter; numeric ceilings were not verified. The terms describe a free evaluation key, account-specific paid plans/limits, personal/academic research with attribution, and additional restrictions for organizational/commercial use, including a limited trial and consent requirements. No fixed price or universal numeric quota is claimed.

Retention duration and public repository redistribution permission remain unresolved; confirm local storage and aggregate-publication rights for this personal portfolio, including whether organizational-use restrictions apply. Do not treat the fictional business scenario as a permitted commercial license. Descriptions are snippets, so fallback use requires separate snippet-based skill metrics or reduced skills scope. Validate US access, currency/period, prediction flags, created semantics and query completeness before committing. No source page authorizes this project to bypass access limits.

### USAJOBS — supplementary federal perspective

The official [Search reference](https://developer.usajobs.gov/api-reference/get-api-search) documents keyword/location filters, `Page`, up to 500 results per page, pay-period fields, publication dates, qualification summaries and duty text. The [rate-limit guide](https://developer.usajobs.gov/guides/rate-limiting) states a maximum 10,000 rows per search query; it does not establish a universal requests-per-hour entitlement. The [authentication guide](https://developer.usajobs.gov/guides/authentication) requires a requested API key with identifying headers for Search. A numeric price was not verified.

The [Historic JOA tutorial](https://developer.usajobs.gov/tutorials/past-job-announcements) demonstrates a past-announcement endpoint without headers, while the general authentication page broadly describes key requirements. Treat historic endpoint authentication, retention coverage, payload completeness and pagination as unresolved until current endpoint-specific guidance is reconciled; do not test them in Phase 1.

The accessible [current terms](https://developer.usajobs.gov/guides/terms-of-service) expressly allow storage, analysis and redistribution of defined Public Data, subject to specifically marked restrictions and accuracy/non-affiliation rules. Record retrieval dates, identify the source, avoid government endorsement claims and review metadata exceptions before publication. Federal titles and occupational series may not map to the four roles; local volume and skills-text quality are unverified. Federal-only results must not be blended into private-board market totals as though the frames were equivalent.

### Public dataset — historical reserve

Publisher [dataset card and dictionary](https://huggingface.co/datasets/lukebarousse/data_jobs/blob/main/README.md) identify 2023 postings, a CSV format, an Apache-2.0 license label, model-derived short titles, parsed remote flags, calculated salary averages and extracted skills. These derived fields do not establish explicit employer-advertised salary provenance or work arrangement under this project's stricter rules. The card describes Google-sourced collection via SerpAPI; that provenance needs review rather than being treated as permission from original posting owners.

Access to the card required no authentication in this session. Dataset downloads, possible access gates, platform quotas, costs and underlying file schema have not been tested. A fixed repository revision and checksums would improve reproducibility if approved. Confirm source rights, original identifiers, Bay Area counts, missingness, posting-date meaning and full-text availability in Phase 2. If the original evidence required by a KPI is absent, disable that KPI; do not reconstruct advertised ranges from derived averages or treat inherited skill labels as our own extraction. Historical coverage is publisher-described, not independently verified.

### BLS OEWS — contextual supplement

Official [program overview](https://www.bls.gov/oes/) describes annual occupational employment and wage estimates. [Copyright guidance](https://www.bls.gov/bls/linksite.htm) describes public-domain BLS material with exceptions for separately identified copyrighted content and recommends attribution. Public pages are accessible without credentials; download access was not tested. File-based acquisition, rather than the BLS time-series API, is the proposed route; file costs, download limits and a particular release's archival coverage were not verified here.

Select and record a specific release, area definitions and occupation codes later. Metropolitan boundaries do not automatically equal the nine counties, and these four role labels do not have a guaranteed one-to-one occupational-code mapping. Do not average area medians into a 'Bay Area median'. Keep survey employment/wages separate from advertisements, with source period and methodology labeled. This source can contextualize observations but cannot validate posting counts or fill missing advertised salaries.

### The Muse — unavailable documentation

Attempted official URL: [API v2 documentation](https://www.themuse.com/developers/api/v2). Repeated fetches timed out. Authentication, pricing, terms/storage rights, fields, freshness/history, pagination/limits, reproducibility and public-portfolio permissions are all unverified in this assessment. No 'free tier' or live availability claim is made.

## Recommendation and reproducibility plan

**Preferred primary: Greenhouse Job Board API, conditional on rights clearance and approval of a curated employer-board frame.** Full descriptions support the skills objective. This prioritizes transparent observed-posting evidence over an unsupported claim of complete market coverage. Phase 2 should assess geographic/role diversity without choosing employers to produce a desired result.

**Fallback: Adzuna, conditional on access, use/storage permissions and acceptance of snippet limitations.** If neither passes its gates, pause acquisition and select a newly researched source or explicitly revise scope; do not scrape another site to bypass a restriction. Use one primary frame initially. An eventual combined frame needs a cross-source deduplication and comparability protocol.

**Supplementary:** BLS OEWS for employment/pay context; USAJOBS for a separately labeled federal perspective. The public dataset is only a reserve for an explicitly historical study. Recommendations are analyst judgments, not verified statements about available record counts.

For reproducibility, later record exact source/board frame, safe parameters, collection timestamps, page completion/status, rule versions and permitted hashes/snapshots. Live APIs change; rerunning requests does not guarantee identical results. Public GitHub should include methods, provenance and allowed outputs. Raw data and database files remain ignored by default, even if some sources ultimately permit sharing. Aggregation alone does not remove licensing restrictions.

## Blockers before acquisition and publication

1. User must approve Phase 2 and the primary/fallback choice; no acquisition has been authorized by completion of this document.
2. Resolve applicable Greenhouse/employer terms for automated collection, raw retention, snapshots and aggregate publication, or establish Adzuna permission for the intended personal portfolio. Capture evidence and required attribution; public raw redistribution is a separate decision.
3. Approve a documented employer-board frame or API query plan, budget, quotas and retention rules. No credentials should be pasted into chat or committed; obtain them privately only after Phase 2 approval if needed.
4. Confirm live access, field semantics, completeness, Bay Area/role coverage and pagination during authorized Phase 2 profiling. Documentation cannot establish these facts.
5. Decide whether snippet-only skill analysis is acceptable if the fallback is used. Do not present it as full-description requirement prevalence.
6. Disable publication-time trends unless date semantics and comparable temporal coverage pass validation. Greenhouse update time is insufficient; first observation is a different measure.
7. Before Phase 5, confirm Tableau Desktop Public Edition or an appropriate Tableau Desktop edition on supported macOS. Prepare clean SQL-to-CSV exports and verify source rights for every published field/extract; Tableau Public is public hosting, so retain a local workbook if public redistribution is not cleared. See the [Phase 5 delivery contract](project_roadmap.md).

## Research verification limits

The shell initially failed because its default working directory no longer existed; using an explicit shell and existing temporary directory restored access. The supplied workspace was recreated at its authorized path. The Node REPL failed to start and was not needed. Web research succeeded for the cited sources except the documented Muse timeout and inaccessible attempted Greenhouse terms URL. API execution, account prices/quotas, full payload quality, data coverage and dataset contents are deliberately untested. No outside contact or permission request was sent on the user's behalf.
