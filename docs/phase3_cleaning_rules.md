# Phase 3 cleaning and relational data contract

Implemented for the approved historical Luke release, using `config/phase3_rules.json`.
This document takes precedence over the original Phase 1 conceptual schema for this
source. No current-market, hiring, advertised-pay or full-description claims follow
from cleaning the file. Phase 4 analysis and Phase 5 Tableau work remain unstarted.

## Run and inspect

From the project root with the existing Python 3.11+ environment:

```bash
python -m src.build_database
python -m src.phase3_report
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

The build is offline. It verifies the existing approved revision, raw size/SHA-256,
manifest and exact 17-field header before processing. It never downloads or rewrites
raw data. A temporary database is loaded and validated before replacing a previous
managed output. Unmanaged output folders are protected. Reruns compare a semantic
checksum of relational content; runtime timestamps are not part of that comparison.
Use the same code, config, Python/SQLite environment and pinned source for replication.

`data/processed/phase3/` contains the SQLite database, full row decision audit,
field issue audit, unresolved location inventory and build summary. All stay ignored
by Git. The report command produces shareable aggregate cleaning diagnostics in
`reports/phase3_cleaning_report.md` and `.json`. No dashboard-ready CSV is exported:
the local audit CSVs explain processing decisions, not Tableau metrics.

## Row flow and duplicate identity

1. Safely read the complete CSV with Python's streaming `csv` reader. This preserves
   strings without pandas type inference and keeps transformation rules explicit.
   pandas remains available for later analysis; SQLite needs no server or extra package.
2. Serialize all 17 original field values in a stable order and hash with SHA-256.
   Equal hashes are also checked against the actual original serialized values.
   Remove only identical records, keeping the first CSV **data-row ordinal** (header
   excluded). This removes repeat records, not proven duplicate vacancies.
3. Resolve US work geography; exclude unresolved and confirmed outside-region rows.
   Then validate the 2023 source date and nonmissing title. Exclude explicit talent
   pool/training advertisements. The priority makes row outcomes mutually exclusive.
4. Retain every remaining Bay record, including uncertain/non-target role audit cases.
   Missing salary, skills or employer do not cause whole-record deletion.
5. Load dimensions, facts, bridges and source lineage transactionally; validate before
   publishing the generated directory. Every input row has one decision in `row_audit.csv`.

Similar employer/title/location/date keys are flagged as candidates and retained.
Without posting IDs or descriptions, merging them would risk deleting different jobs.
Full source rows are preserved locally for retained records. Excluded rows remain
traceable through raw-row ordinals and hashes. Exact duplicates outside the Bay scope
are counted globally before geographic filtering; report this separately from Bay dedup.

## Geography and arrangements

The Phase 2 101-incorporated-city reference remains unchanged. Phase 3 adds a curated
list of named communities, including Stanford and Castro Valley, plus an explicit
`St Helena` -> `St. Helena` alias. The nine counties are unchanged. Additions are
**communities**, not invented incorporated cities. Incorporated names resolve under
the published city reference; this is locality-label resolution, not geocoding or
proof of an address inside municipal boundaries. Modern references are not a 2023
address-boundary reconstruction.

Evidence reviewed October 26, 2026:

- The California Secretary of State's [2025 community/county roster](https://admin.cdn.sos.ca.gov/ca-roster/2025/unincorporated-areas.pdf) supports the named community mappings in config.
- The [Contra Costa housing document](https://www.contracosta.ca.gov/DocumentCenter/View/3223/2009-Housing-Element-Update) identifies Canyon; the [Marin assessment](https://www.marincounty.gov/sites/g/files/fdkgoe241/files/2024-02/marin-county-vulnerability-assessment_final_with-appendicies_reduced-20220117.pdf) identifies Lagunitas-Forest Knolls.
- [Santa Clara County](https://d5.santaclaracounty.gov/district-5-office) identifies Stanford; [NASA](https://historicproperties.arc.nasa.gov/h3historysite/one/) locates Moffett Field in Santa Clara County.
- [Census reference records](https://tigerweb.geo.census.gov/tigerwebmain/Files/acs26/tigerweb_acs26_cdp_2025_acs25_ca.html) show two California El Sobrante places. [San Diego](https://www.sandiego.gov/citycouncil/cd4/communities/emerald-hills) also uses Emerald Hills. These bare labels remain unresolved; do not choose a Bay location automatically. Princeton is not assumed to mean Princeton-by-the-Sea.

Unrecognized California locations are **unresolved**, not automatically outside the
Bay Area. This bucket therefore contains many obvious non-Bay cities too: no exhaustive
California gazetteer is claimed. Known non-CA state abbreviations are outside the Bay
Area. Vague California/Anywhere labels and unresolved multi-place segments are excluded
from the core. Further reference expansion would be a versioned revision, not a hidden
change. The unresolved inventory preserves candidate labels for future review.

A complete `City, State` label separated by `;` or `|` represents multiple locations.
Keep every resolved location, including outside-region locations. At least one Bay
location is required; county-only Bay locations qualify regionally with null locality.
If any segment cannot resolve, exclude pending review rather than silently drop it.
City counts will be non-additive. No search-location/headquarters inference is allowed.

Work arrangement remains `unknown` for this source. Preserve the raw flag; `False`
does not establish on-site/hybrid, and `True` alone is not evidence for the stricter
arrangement KPI. Explicit title clues are retained as original text but not interpreted
by an unvalidated arrangement classifier. Nationwide remote eligibility is not invented.

## Role and seniority

Match explicit Data Analyst, Data Scientist, Data Engineer, Machine Learning Engineer
or ML Engineer phrases with case-insensitive word boundaries and space/hyphen variants.
Preserve the original title and publisher label. Remove the publisher's `Senior ` prefix
only when comparing role families; seniority is extracted separately from original titles.

- Exactly one explicit target phrase with no conflicting target publisher label or
  explicit competing non-target occupation -> `accepted_title_only`.
- Multiple target phrases, explicit competing non-target occupation, or target publisher
  disagreement -> `ambiguous`; no target role assigned.
- An explicit non-target Business Analyst, Cloud Engineer, Software Engineer/Developer,
  or Java Developer/Programmer with no target phrase -> `out_of_scope`.
- Remaining titles -> `unclassified`. This includes BI/generic analyst, Analytics
  Engineer and Data Science management titles without a matching target phrase.

A single exact title/publisher exception in config was reviewed: an explicit Data Engineer title described prior Software Developer background, which is experience evidence rather than a second occupation. Its reason and method are saved in role evidence; no general exception is inferred.

This intentionally favors precision over recall. No missing duties are reconstructed,
no skill determines occupation, and publisher labels alone cannot admit a record.
`v_target_job_records` is the future four-role denominator; role audit cases remain
in the fact table but outside that view. Review coverage is recorded separately,
including its limitations; assistant title inspection is not human ground truth.

Seniority uses explicit title terms: entry/junior/intern, mid/intermediate, senior/Sr,
lead/staff/principal, management, mixed/conflicting, or unknown. Senior Manager maps
to management and Senior Staff to lead/staff/principal; these are compatible terms.
Junior+senior stays conflicting. Numeric levels, associate/expert and missing senior
words do not imply entry level. Experience years and required/preferred duties remain
unavailable. Raw schedule is preserved; recognized employment labels become a JSON
list without assuming hours or a primary employment type.

## Skills, pay and missing values

Use `ast.literal_eval`, never `eval`, to parse inherited skill lists. Reject malformed
structures; missing, empty, malformed and populated are separate states. Normalize
Unicode/whitespace/case, apply the small documented alias map, and collapse repeated
canonical tags within each record. Preserve original tags on each bridge pair.
Do not strip punctuation: C++, C# and C remain distinct. These are publisher tags,
not our extraction, verified requirements or proof that a missing tag is absent from
an original advertisement. Publisher skill categories remain in raw provenance;
no unreviewed category taxonomy is imposed.

Salary fields must be positive finite numbers. Preserve originals. Store valid values
as integer **hundredths of source units**, rounded with Decimal ROUND_HALF_EVEN.
Divide by 100 only to recover the normalized source-unit value; these are not verified
USD cents. Every rounding event is audited. Invalid/overflow values become null while
the record and raw value stay. Missing stays null, with no imputation, outlier deletion,
hourly conversion or invented salary bounds. Currency is null and primary advertised
salary eligibility is always false by database constraint. Hourly/annual values remain
separate. Numerical storage validation does not establish salary comparability.

Unicode normalization, whitespace cleanup and casefold keys consolidate text labels
without removing company suffixes or guessing corporate identities. Dimension companies
are name labels, not verified legal employers. Null employer -> null company FK.
Dates become ISO text, keeping source clock values without assigning a timezone.
The source's 2023 date semantics/collection coverage remain unverified: trends stay disabled.

## Implemented relational model

| Table/view | Grain / key | Relationships and purpose |
|---|---|---|
| collection_snapshots | One pinned source file, snapshot_id PK | Release, raw hash/count, acquisition timestamp, rule version; not a new live collection |
| dim_companies | One normalized name label, company_id PK | Optional company FK on facts; normalized name unique |
| dim_locations | One locality/county/state/country/precision tuple, location_id PK | Unique location_key; county-only has null locality |
| dim_skills | One canonical inherited skill tag, skill_id PK | Unique canonical_name with taxonomy/rule version |
| fact_job_postings | One retained exact-deduplicated source record, job_posting_id PK | Optional company FK; title/role/seniority, pay/skill status, date, raw flags; PK is kept raw-row ordinal |
| bridge_job_skills | One job-skill pair, composite PK | FKs to fact and skill; original-tag evidence; required/preferred unknown |
| bridge_job_locations | One job-location pair, composite PK | FKs to fact and location; complete raw location evidence |
| source_posting_records | One retained source row, source_record_id PK | Snapshot and fact FKs; unique(snapshot_id, source_row_number), full original row JSON and SHA-256; native ID null |
| pipeline_metadata | One metadata item, key PK | Producer, rule version and code/config/schema hashes |
| v_target_job_records | Accepted title-only target facts | View, not a separately copied/duplicated table |

No observation-history or salary-band table is needed for a single immutable file
without source bands. Source fact/row identity is documented differently from the
original generic API schema. A new release requires a reviewed adapter/history policy.
Never combine row ordinals from different revisions without their snapshot identity.

## Quality and review checks

The loader checks input/manifest/audit reconciliation; PK/FK/unique/enum/positive-pay
constraints; SQLite integrity; source lineage; qualifying Bay membership; skill-list/
bridge consistency; and target distinct counts across location bridges. Tests include
multi-location/skill multiplication, malicious skill strings, exact versus near
duplicates, unknown roles, null pay and rollback protection. The real file is rerun
and relational content checksummed. No live permission, Tableau installation,
statistical inference or dashboard metric is verified in Phase 3.
