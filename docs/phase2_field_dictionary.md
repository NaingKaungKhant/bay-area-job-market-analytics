# Phase 2 — observed Luke CSV field dictionary

The entire pinned CSV was read and the following 17 columns were verified. All are preserved as source strings during profiling; semantic types below describe meaning, not a cleaned schema. Publisher/source meaning is from the pinned dataset card. Measured missingness is in `reports/luke_2023_profile.json`.

| Field | Meaning / expected semantic type | Limitation for this project |
|---|---|---|
| job_title_short | Publisher's model-derived role label | Not our accepted classification; senior labels are separate |
| job_title | Original title string | No full description to resolve ambiguous duties |
| job_location | Source location string | Exact city/CA profiling only; no headquarters inference |
| job_via | Posting platform label | Not a source-native posting ID or canonical URL |
| job_schedule_type | Employment/schedule string | Missing/multiple values require later review |
| job_work_from_home | Publisher-parsed boolean text | False does not identify on-site versus hybrid |
| search_location | Collection query location | Not proof of the actual job work location |
| job_posted_date | Publisher-recorded date/time string | Naive timezone; collection completeness and original-date semantics not independently verified |
| job_no_degree_mention | Publisher-parsed boolean text | Not a full education-requirement field |
| job_health_insurance | Publisher-parsed boolean text | Not a compensation amount or verified total benefits measure |
| job_country | Publisher-parsed country string | Use with work location, not alone as geography evidence |
| salary_rate | Source pay frequency label | Some labels are month/week; do not silently annualize |
| salary_year_avg | Publisher-derived annual salary value | No original bounds, currency column, estimate/provenance flag or location-specific band evidence |
| salary_hour_avg | Publisher-derived hourly salary value | Keep separate; no automatic 2,080-hour conversion |
| company_name | Employer string | Name equality is not proof of employer identity |
| job_skills | Serialized publisher-extracted list | Safe structural parsing only; missing lists are not evidence of no skill requirements |
| job_type_skills | Serialized skill-category dictionary | Inherited taxonomy, not our own NLP result |

Absent from this schema: source-native posting ID, source posting URL, full original description, advertised salary lower/upper bounds, explicit currency, salary-estimate flag and original job-specific arrangement evidence. These absences disable the corresponding stricter KPIs or require a clearly renamed derived-field measure.

Missing tokens for profiling: blank/whitespace, NULL, null and None. Zero is not missing. Skill lists are missing, empty, populated or malformed; malformed values are not evaluated as executable code. Numeric validity/presence checks do not certify pay comparability. Counts are raw records until Phase 3 documents a deduplication policy.

The manifest contract is dataset-level source/revision/file, retrieval start/end UTC, exact size/SHA-256, expected publisher LFS hash, source-card/license hashes, completion status and actual CSV row count. There is no pagination for this one-file acquisition. Geography reference version and checksum are recorded in the profile; exact-match candidates are not claimed as a comprehensive canonical Bay Area cohort.
