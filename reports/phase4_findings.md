# Phase 4 findings — historical observed Bay Area records

Completed 2026-10-27. Phase 4 only; Phase 5 has not started. Source: Luke Barousse data_jobs, pinned 2023 release. [Attribution and license](../docs/data_attribution.md). Figures and results remain local/unpublished.

## Questions answered and methods

We describe accepted records by role, inherited skill tags, resolved geography and explicit title-based seniority. SQL is the measurement source; independently constructed pandas summaries reconcile all nine result tables. Distinct record IDs prevent skill/location joins from multiplying the cohort. Source/rule/schema identity is unchanged.

Role and seniority shares use all accepted records. Skill rates use populated inherited lists within the selected role/location; missing lists are not negatives. Comparisons with fewer than 10 usable lists are suppressed, while counts remain visible. Tag-count summaries use mean, median, linear-interpolated quartiles and range. Percentage-point contrasts are descriptive, unadjusted for seniority/employer mix. No p-values, confidence intervals, population estimates or causal tests are justified by this non-random, potentially dependent/reposted source.

## 1. Role composition and visible classification uncertainty

Accepted cohort: **12,631 / 16,223 retained Bay records (77.9%)**. Outside the denominator: ambiguous **209**; unclassified **3,103**; explicit non-target **280**. These are not silently dropped from the audit.

| Accepted role | Records n | Cohort share % | Usable tags n | Tag coverage % |
| --- | --- | --- | --- | --- |
| Data Analyst | 4,829 | 38.2 | 4,093 | 84.8 |
| Data Engineer | 2,035 | 16.1 | 1,928 | 94.7 |
| Data Scientist | 5,700 | 45.1 | 5,019 | 88.1 |
| Machine Learning Engineer | 67 | 0.5 | 61 | 91.0 |

Data Scientist has the largest accepted record count. The Machine Learning Engineer cohort is much smaller; the strict title rule and excluded mixed-role titles affect that count. These are sample composition differences, not market-wide role demand or hires.

## 2. Technical skill tags and missingness

Usable inherited lists: **11,101/12,631 (87.9%)**; missing lists: **1,530**; empty/malformed: **0**. Original descriptions are unavailable for all records, so full-text coverage is unavailable and required/preferred skill distinctions cannot be assessed.

- Data Analyst: sql 2,879/4,093 (70.3%), tableau 1,898/4,093 (46.4%), python 1,853/4,093 (45.3%)
- Data Engineer: python 1,461/1,928 (75.8%), sql 1,334/1,928 (69.2%), spark 796/1,928 (41.3%)
- Data Scientist: python 4,362/5,019 (86.9%), sql 3,283/5,019 (65.4%), r 2,495/5,019 (49.7%)
- Machine Learning Engineer: python 43/61 (70.5%), tensorflow 32/61 (52.5%), pytorch 26/61 (42.6%)

These rates are conditional on usable lists; they can sum above 100% because a record has multiple tags. Tags are inherited publisher output, not independently validated employer requirements. Missingness can differ by role.

| Role | Usable n | Mean tags | Q1 | Median | Q3 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Data Analyst | 4,093 | 4.2 | 2.0 | 4.0 | 5.0 | 1 | 18 |
| Data Engineer | 1,928 | 7.1 | 4.0 | 7.0 | 9.0 | 1 | 24 |
| Data Scientist | 5,019 | 5.3 | 3.0 | 5.0 | 7.0 | 1 | 24 |
| Machine Learning Engineer | 61 | 5.9 | 3.0 | 5.0 | 7.0 | 1 | 14 |

Illustrative within-sample percentage-point contrasts (first role minus second):

| Tag | First role | Second role | First usable n | Second usable n | Difference pp |
| --- | --- | --- | --- | --- | --- |
| python | Data Scientist | Data Engineer | 5,019 | 1,928 | 11.1 |
| sql | Data Analyst | Data Engineer | 4,093 | 1,928 | 1.1 |
| tableau | Data Analyst | Data Scientist | 4,093 | 5,019 | 25.5 |

| Tag contrast | Logical difference lower pp | Logical difference upper pp |
| --- | --- | --- |
| python | -0.5 | 16.7 |
| sql | -11.2 | 9.3 |
| tableau | 9.0 | 36.2 |

These difference ranges allow unavailable-list content to vary separately in each role. If a range includes zero, even the direction of the all-record tag gap is not fixed by observed lists. A range staying positive still does not establish a causal/population result or protect against extraction errors.

The sensitivity figure treats each unavailable list as either lacking or containing a selected tag: lower = tagged/all role records; upper = (tagged + unavailable)/all role records. These are logical missing-data bounds, not confidence intervals, imputed values or bounds on true requirements; extraction errors remain outside the calculation.

## 3. Geography and role/skill differences

The largest accepted city association is **San Francisco: 3,450 (27.3% of the accepted cohort)**. The largest county association is **Santa Clara: 5,130**.

| Incorporated city | Accepted record memberships |
| --- | --- |
| San Francisco | 3,450 |
| San Jose | 1,248 |
| Sunnyvale | 879 |
| Mountain View | 833 |
| Palo Alto | 682 |

Role mix in two major cities (within-city denominators, counts are not skills-expanded):

| City | Role | Role n | City n | Within-city role % |
| --- | --- | --- | --- | --- |
| San Francisco | Data Analyst | 1,233 | 3,450 | 35.7 |
| San Francisco | Data Engineer | 567 | 3,450 | 16.4 |
| San Francisco | Data Scientist | 1,625 | 3,450 | 47.1 |
| San Francisco | Machine Learning Engineer | 25 | 3,450 | 0.7 |
| San Jose | Data Analyst | 561 | 1,248 | 45.0 |
| San Jose | Data Engineer | 204 | 1,248 | 16.3 |
| San Jose | Data Scientist | 479 | 1,248 | 38.4 |
| San Jose | Machine Learning Engineer | 4 | 1,248 | 0.3 |

Three most frequent Data Analyst tags in each of these cities (usable lists only):

| City | Tag | Tagged n | Usable DA n | Conditional % |
| --- | --- | --- | --- | --- |
| San Francisco | sql | 851 | 1,113 | 76.5 |
| San Francisco | python | 515 | 1,113 | 46.3 |
| San Francisco | tableau | 515 | 1,113 | 46.3 |
| San Jose | sql | 374 | 494 | 75.7 |
| San Jose | tableau | 289 | 494 | 58.5 |
| San Jose | python | 223 | 494 | 45.1 |

Accepted records with city evidence: **12,366**; community evidence: **265**; county-only: **0**. Multi-Bay-location records: **0**. Each record counts once regionally and once per qualifying locality/county; geographic counts remain non-additive by definition even when this snapshot has no overlap.

Locality-role cells with n<10: **147/243**. City role-mix counts and locality/role/tag conditional rates are available in the result tables and notebook, with coverage/denominators. Sparse skill rankings are suppressed. Communities are not relabeled as incorporated cities, and unresolved geography remains excluded under the unchanged Phase 3 rules.

## 4. Explicit seniority

Unknown: **7,722/12,631 (61.1%)**; mixed/conflicting: **13**. Explicit entry/junior/intern: **492 (3.9%)**. The entry/junior category includes internships. Absence of a senior term does not imply entry level, and explicit seniority does not establish required years of experience.

## Disabled questions and limitations

- Derived annual fields are present in **1,192/12,631 (9.4%)**; hourly fields in **567/12,631**. Verified comparable advertised-pay records: **0**. Currency, advertised/estimated provenance and original bands remain unverified. **No salary amounts, medians, role/city pay comparisons or annualization are reported.**
- Work arrangement is unknown for every accepted record. No remote/hybrid/on-site share is inferred from false flags.
- Source dates span 2023, but original date meaning, timezone and stable collection coverage are unverified. **No posting or hiring trend is reported.**
- Reposts may remain; record IDs are file-row lineage, not independently verified vacancies. Several records can share an employer, and titles/skill extraction may contain errors.
- This is a historical convenience dataset with incomplete geographic/title coverage. It is not a census or probability sample of Bay Area employment. Large counts do not remove selection bias.
- Skills and seniority can vary with source coverage, employer mix and role mix. Observed associations do not establish effects of learning a skill on getting hired.

## Validation and reproducibility

- All **9 SQL/pandas tables** matched (counts and percentages/quantiles). Chart artists were checked against the reconciled SQL data; figure hashes and plotted data are recorded.
- Database content matches the recorded Phase 3 semantic checksum; read-only checks cover integrity, foreign keys, source lineage, Bay membership and skill bridges. Database file bytes are checked before/after analysis. Source, cleaning config and schema are unchanged.
- The raw directory read stalled, including its manifest. Phase 4 therefore did not repeat raw-file hashing; it uses the recorded Phase 3 source checksum and verifies the existing database. No new job data was downloaded.
- See [analysis tables/provenance](phase4_analysis.json), [verification results](phase4_verification.json), [methods guide](../docs/phase4_analysis_methods.md) and executed notebooks. Tests/notebook execution are recorded separately after their actual runs.

Potential portfolio discussion: the project demonstrates consistent denominators, explicit missingness, SQL window functions, relational joins, descriptive contrasts, reproducible plots and evidence-based limits. Broader business recommendations and Tableau delivery remain later phases.
