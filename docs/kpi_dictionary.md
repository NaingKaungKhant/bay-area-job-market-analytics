# KPI dictionary

## Active Luke dataset amendment — approved October 26, 2026

This section takes precedence for the acquired historical source. The original strict definitions below remain references, not claims of available fields.

- **Observed dataset records:** count source rows or retained records under the [implemented Phase 3 policy](phase3_cleaning_rules.md). There is no native posting ID, so do not label row counts certified unique vacancies/postings. Any fingerprint is a duplicate candidate, not proof of identity.
- **Role record share:** denominator is `v_target_job_records`: accepted title-only target records under the versioned Phase 3 rulebook; publisher conflicts and ambiguity are disclosed. Senior labels must not be silently dropped or merged. Phase 2 counts are preliminary labels, not that final cohort.
- **Publisher-derived annual salary:** a potential separately named measure using positive finite salary_year_avg values; never substitute it for verified advertised-pay midpoint. Original bounds, currency and advertised-versus-estimated evidence are absent. Report source-unit uncertainty; do not show USD or compare currencies until original units are established. A median is Phase 4 work, not a Phase 2 result. Primary advertised-salary KPI stays unavailable.
- **Derived-pay coverage:** nonmissing/valid publisher annual values divided by the chosen record cohort, with missingness and period restrictions visible. Keep hourly values separate; no automatic annualization.
- **Publisher skill-tag presence/frequency:** in Phase 4, count distinct retained record-skill pairs already produced by safe Phase 3 parsing. Denominator is records with usable populated tag lists; disclose missing/empty/malformed lists separately. These are inherited tags, not our own text mentions or verified requirements. Original-description skill metrics stay unavailable.
- **Geography:** retained work-location evidence must meet the same nine-county definition. Phase 2's exact city/CA match is a conservative diagnostic; unincorporated/multi-location/vague labels need Phase 3 review. Never infer work location from search_location or company headquarters.
- **Work arrangements:** a parsed false work-from-home flag does not mean on-site. Explicit remote/hybrid/on-site shares and arrangement coverage under the original evidence requirement are unavailable.
- **Temporal comparisons:** dates describe publisher records from 2023. Timezone, original-posting semantics and collection consistency are not verified; hiring/posting-trend KPIs remain disabled. Calendar completeness in a file is not evidence of representative temporal coverage.

See the [field dictionary](phase2_field_dictionary.md) and [actual profile](../reports/luke_2023_profile.json). No unavailable value is replaced with zero or invented evidence.


Original conceptual definitions; source-specific availability is governed by the active amendment above. Phase 2 reports raw quality/coverage diagnostics, not accepted business KPI results. Scope and classification follow [business requirements](business_requirements.md).

## Common measurement contract

`C` is the set of distinct canonical posting IDs with a confirmed nine-county work location and one accepted target-role classification, within a stated observation window and fixed source/query/board sampling frame. `C_r` is the subset with role r. Keep geographically eligible ambiguous/unclassified candidates in an audit cohort outside C and disclose their counts. Each chart must name its window, cohort, source frame, exclusions, and denominator. Use the same cohort for role comparisons; do not combine incompatible source frames without source-specific reporting.

A report window uses first observation within that window for cumulative unique observed counts; an 'as observed at snapshot' report instead uses membership in that successful snapshot. These are different measures and must be labeled. When a job changes role/location/pay, retain its history and select its latest valid version observed within the reporting window (or at the snapshot); never sum versions. Later evidence cannot silently rewrite a published historical extract.

Percentages use distinct postings, not bridge rows. A zero denominator produces 'not available', never zero percent. Display the numerator and denominator with percentages. As a project reporting policy, suppress comparative salary/skill rankings for groups with fewer than 10 eligible observations, show their counts, and label small samples. This threshold is a communication rule, not a guarantee of statistical reliability.

## Salary normalization policy

Preserve source text, currency, pay period, bounds, employer-versus-estimated provenance, base-versus-total-compensation type, and location applicability. An eligible salary is explicitly employer-advertised USD annual base pay with valid positive bounds or an explicit single fixed amount. With two bounds L and U, require L <= U and use (L + U) / 2 as a posting-level midpoint. A fixed amount uses that amount. Open-ended 'up to'/'from' values do not become midpoints; retain them outside the primary salary KPI. Missing salary never becomes zero and is not imputed. Predicted/vendor-estimated salaries are excluded from advertised-pay metrics; report them separately only if permitted and clearly labeled. Unclear provenance, currency, or period excludes the record from comparable pay metrics until resolved.

Primary salary metrics use directly annual pay only. Hourly pay is retained separately. An optional sensitivity view may annualize explicitly full-time hourly base pay at 40 hours/week x 52 weeks = 2,080 hours/year, or use explicitly stated contractual hours with a documented factor; show the factor and keep that view separate from primary salary KPIs. This is an assumption about equivalence, not observed annual earnings. Do not annualize part-time/contract pay automatically. Do not mix annual and converted hourly observations in the primary median.

If pay varies by location or level, use only an unambiguous applicable Bay Area band. Several different applicable bands without a defensible single posting-level band make that posting ineligible for the regional median; preserve all bands for later separately scoped reporting. Do not take the outermost bounds across unrelated locations. Reject invalid ranges, flag extreme valid amounts for review without automatically deleting them, and disclose exclusions. Accompany medians with coverage, eligible n, and later quartiles/range summaries; a median of midpoints is not a median of accepted offers.

## Unique observed job postings

- **Business definition:** Number of distinct in-scope advertisements observed in the specified frame and window.
- **Formula:** |C|, or |C intersect successful snapshot membership| for a labeled snapshot view.
- **Required fields:** Canonical ID, source/board and posting ID, first/last observed timestamp, snapshot membership/status, scope status, accepted role, dedup decision/version.
- **Quality conditions:** Deduplicate repeated requests/snapshots and reviewed equivalents; retain exclusion and merge audit. Failed collection is not an empty snapshot. Exclude talent pools and unresolved scope.
- **Biases:** Incomplete source coverage, reposts, evergreen ads, missed pages, and false merges/splits.
- **Interpretation:** Count of observed advertisements; not hires, vacancies, or the entire market.

## Job posting share by role

- **Business definition:** A role's proportion of the four-role classified cohort.
- **Formula:** 100 x |C_r| / |C|.
- **Required fields:** Common cohort fields, accepted role, classification evidence/status/version.
- **Quality conditions:** One accepted role per posting; display audit-cohort ambiguity/unclassified rates separately. Four shares sum to 100% before rounding.
- **Biases:** Title conventions, classifier mistakes, role-specific retrieval and source selection.
- **Interpretation:** Sample composition, not a role's share of all employment.

## Median advertised annual salary

- **Business definition:** Median posting-level annual USD advertised base-pay midpoint among eligible salaries in the selected cohort.
- **Formula:** median({m_j : j in C, salary_eligible_j = true}); for a role restrict to C_r. Even n uses the average of the two central ordered midpoints.
- **Required fields:** Canonical ID, role, salary bounds/fixed amount, currency, period, provenance, compensation type, applicable locations, eligibility/exclusion reason.
- **Quality conditions:** Apply salary policy above and minimum comparison n; no imputation, predicted pay, open bounds, or hourly conversions in the primary KPI.
- **Biases:** Non-random salary disclosure, broad bands, seniority/industry mix, and midpoint approximation.
- **Interpretation:** Typical midpoint among comparable advertised ranges, conditional on disclosure; not actual earnings or an individual salary prediction.

## Salary coverage percentage

- **Business definition:** Share of the cohort with an eligible salary for the primary annual-pay KPI.
- **Formula:** 100 x count_distinct(j in C with salary_eligible) / |C|.
- **Required fields:** Canonical ID and all salary eligibility fields, including missing/exclusion reason.
- **Quality conditions:** Same cohort as salary chart; disclose annual, hourly-only, estimated, missing, invalid, and unresolved-band counts separately. 'Any salary text present' can be a separate diagnostic, never substituted for this coverage.
- **Biases:** Disclosure practices differ across employers, roles, and arrangements.
- **Interpretation:** Comparability/completeness of the pay analysis, not the proportion of employers paying salaries.

## Skill mention frequency

- **Business definition:** Number of unique postings whose available job-specific text mentions a normalized technical skill at least once.
- **Formula:** F_s = count_distinct(j in C with usable text and accepted skill s mention).
- **Required fields:** Canonical ID, description/title text availability, text completeness, skill ID, matched evidence and section, extractor version, required/preferred/context status.
- **Quality conditions:** At most one posting-skill pair. Use curated aliases, word boundaries, and context review for ambiguous tokens such as R or Go; exclude boilerplate, negated requirements, and irrelevant mentions. Retain required versus preferred evidence where explicit; never infer 'required' from a bare mention. Distinguish full-text and snippet cohorts.
- **Biases:** Truncated descriptions, keyword ambiguity, omitted skills, and extraction errors.
- **Interpretation:** Documented mentions within available text, not verified competency requirements. Repeated mentions do not add demand.

## Skill demand percentage by role

- **Business definition:** Percentage of role-specific postings with usable text mentioning a skill; 'demand' is shorthand for observed mentions.
- **Formula:** 100 x count_distinct(j in C_r with usable text and accepted mention s) / count_distinct(j in C_r with usable text).
- **Required fields:** Role/classification, text usability/completeness, canonical ID, accepted posting-skill pairs and extractor version.
- **Quality conditions:** Publish text coverage = usable-text postings / |C_r| alongside the result. Missing text is not evidence of absence. Full text is the preferred comparison cohort; snippets must be separately labeled and not pooled with full text for role rankings. Skill percentages may sum above 100% because postings mention multiple skills.
- **Biases:** Non-random text availability, source truncation, taxonomy omissions, and extractor errors.
- **Interpretation:** Mention prevalence among text-observable postings in that role, not prevalence across all vacancies.

## Job postings by city

- **Business definition:** Distinct postings explicitly associated with each resolved in-scope city.
- **Formula:** N_c = count_distinct(j in C with a qualifying posting-location link to city c).
- **Required fields:** Canonical ID, raw work locations, normalized city/state/county/country, geographic confidence/status and bridge links.
- **Quality conditions:** One distinct posting-location pair; no headquarters inference. County-only records stay in regional totals and a 'city unavailable' diagnostic. City counts are non-additive: a multi-city posting counts once in each city but once regionally. No arbitrary primary city or fractional allocation in the default view.
- **Biases:** Multi-location advertisements, broad geography labels, and city-specific source coverage.
- **Interpretation:** Advertisements offering a city as a work location, not a count of jobs exclusively located there. A city share, if shown, uses |C| and is also non-additive.

## Remote / hybrid / on-site share

- **Business definition:** Distribution among postings with one explicitly identifiable arrangement.
- **Formula:** Let E = postings in C labeled remote, hybrid, or on-site. Share_a = 100 x count_distinct(j in E labeled a) / |E|. Arrangement coverage = 100 x |E| / |C|.
- **Required fields:** Canonical ID, arrangement label, explicit field/text evidence, conflicts, location eligibility, rule version.
- **Quality conditions:** Use only explicit evidence per scope rules. Publish unknown and conflicting counts against |C|; do not interpret either as on-site. Nationwide remote-accessible jobs outside C belong to a separate cohort.
- **Biases:** Selective disclosure, changing policies, snippets, and inconsistent use of 'telework'.
- **Interpretation:** Mix among identifiable arrangements, not a claim that every observed job can be classified.

## Time-series posting count — conditional

- **Business definition:** Distinct observed postings grouped by validated original publication period, within a documented collection frame.
- **Formula:** T_t = count_distinct(j in C with validated published_at in period t). Use non-overlapping calendar weeks in America/Los_Angeles, Monday through Sunday, after retaining original timestamps/timezones.
- **Required fields:** Canonical ID, original publication timestamp and meaning, timezone/precision, date validity, source/frame, collection logs and completeness.
- **Quality conditions:** Validate date semantics, plausible dates, timezone and missingness. Never substitute updated_at, retrieval time, or first_seen for published_at. Record date coverage; exclude unknown dates from the series. Mark partial periods and missing collection intervals. Historical conclusions require adequate historic coverage or a prospective stable collection protocol, not merely dates on currently active ads. Reposts follow documented dedup rules.
- **Biases:** Survivorship of active postings, backfills, vendor refreshes, sampling-frame changes, and missing periods.
- **Interpretation:** Observed advertisement activity only. If original dates are unavailable, this KPI is unavailable; successful-snapshot inventory or first-observed counts can be separately labeled, without calling them publication trends or hiring trends.

## Deduplication contract

Namespace source IDs by provider and board; repeated source IDs are observations of one source posting, not new postings. Candidate cross-source/repost matches use employer identity, normalized title, explicit locations, requisition ID, URL and content fingerprint. No single employer-title-city match automatically merges records. Review uncertain matches, retain mapping/evidence, and expose residual duplication limits. Explicitly new requisitions remain separate. A relisting with a new source ID becomes a new posting unless documented evidence supports merging; do not claim this estimates unique vacancies. Canonical counts must be computed before joining skills or locations.
