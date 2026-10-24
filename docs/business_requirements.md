# Business requirements

Status: Phase 1 design, prepared October 23, 2026. No job postings have been acquired and no findings are claimed. This document is the authority for scope; the KPI dictionary is the authority for measurement.

## Scenario and stakeholders

A hypothetical workforce intelligence and recruitment analytics company wants to help clients understand the tech roles advertised in the San Francisco Bay Area. This portfolio simulates that business problem as a personal educational project; it is not a commercial deployment or evidence of a real client engagement.

Stakeholders are recruiting managers planning searches, workforce planners assessing advertised requirements, educators designing training, job seekers prioritizing skills, and an analyst maintaining trustworthy reports. The portfolio audience also includes hiring managers evaluating reproducible Python, SQL, statistics, and business communication skills.

## Business problem and objectives

Job advertisements use inconsistent titles, locations, compensation formats, and skill names. Stakeholders need a transparent way to compare the observed postings without mistaking advertisements for hires or a convenience sample for the whole market.

The project will define a documented sampling frame, reconcile duplicates, normalize geography and salary, classify roles transparently, and measure advertised skills and work arrangements. Later phases will create a reproducible Python/SQLite workflow, SQL reporting tables, exploratory statistics, and a Tableau dashboard with visible coverage and uncertainty. Phase 1 delivers the specifications and feasibility assessment only.

## Geographic scope

Use the nine counties defined by the [Metropolitan Transportation Commission](https://www.mtc.ca.gov/about-mtc/what-mtc): Alameda, Contra Costa, Marin, Napa, San Francisco, San Mateo, Santa Clara, Solano, and Sonoma, California. County membership, rather than proximity to San Francisco or a vendor's metro label, determines eligibility. Santa Cruz and San Benito are outside this definition.

The scope includes San Francisco; San Jose, Palo Alto, Mountain View, Sunnyvale, Santa Clara, and Cupertino in Santa Clara County; Oakland, Fremont, and Berkeley in Alameda County; and Redwood City and Menlo Park in San Mateo County. Other municipalities and unincorporated places in the nine counties also qualify, for example Richmond, San Rafael, Napa, Fairfield, and Santa Rosa. A versioned city-to-county reference and documented manual review will be created in Phase 2/3. Postal and employer-headquarters addresses alone do not establish a job's work location.

A posting enters the core geographic cohort only when at least one explicit job work location resolves to a qualifying county. A county-only location can qualify regionally but is not assigned a city. Vague 'Bay Area' or 'California' locations remain unresolved unless further evidence establishes county membership. Query radius searches are retrieval aids, not the final boundary.

Remote jobs qualify for the core cohort only with an explicit qualifying work-location association. Nationwide/California remote jobs with no such association are excluded from the core and may be reported as a separate remote-accessible cohort if eligibility for Bay Area residents is explicit. Employer headquarters in the region is insufficient. Hybrid jobs need an explicit qualifying office/work location. Work arrangement and geographic eligibility are separate decisions.

For multi-location postings, retain every stated work location, including those outside the region. Count the posting once regionally if any location qualifies. Count it once in each eligible named city in the city view, label that view non-additive, and never sum city counts to get the regional total. Do not invent a primary city or spread one salary across city-specific pay bands without evidence.

## Role scope and classification strategy

The four target roles are Data Analyst, Data Scientist, Data Engineer, and Machine Learning Engineer. These are occupational roles across all employer industries; 'tech' does not restrict employers to the technology industry. Analyze all seniorities, with a separate explicit seniority breakdown useful to entry-level applicants. Exclude general talent pools, training advertisements, and postings outside the role scope. Internships and contract/part-time work may qualify but must carry separate employment-type flags and filters.

Planned classification is a versioned rulebook with human review, not an assumption that vendor categories are correct:

1. Preserve original title and available description; normalize case, punctuation, and abbreviations for matching without deleting seniority evidence.
2. Match explicit role phrases and approved aliases. 'ML Engineer' can be an alias for Machine Learning Engineer; 'BI Analyst' is a candidate for Data Analyst only when duties support analytical reporting. A generic 'Business Analyst', 'Research Scientist', 'Analytics Engineer', 'AI Engineer', or 'Software Engineer' is not automatically assigned.
3. Use responsibilities to resolve candidates: reporting/decision support for Data Analyst; statistical modeling/experimentation for Data Scientist; data infrastructure/pipelines for Data Engineer; production ML deployment/systems for Machine Learning Engineer. Skill keywords alone never determine the role.
4. Assign exactly one target role only when evidence supports a clear classification. Multiple competing role phrases or conflicting duties receive `ambiguous`; insufficient evidence receives `unclassified`; clear non-target work receives `out_of_scope`. Do not force a precedence rule to inflate target counts.
5. Save classification status, matched evidence, method, rule version, and reviewer decision. Manually review ambiguous records and a stratified sample of automatic assignments in Phase 3; report review coverage and disagreement. Publish the rulebook and later quality assessment.

Eligible ambiguous/unclassified candidates remain in an audit cohort outside the four-role KPI denominator. Report their counts and proportions alongside the classified cohort so uncertainty is visible. Source-supplied standardized titles are supporting evidence only.

Seniority is a separate attribute: entry/junior, mid, senior, lead/staff/principal, management, mixed/conflicting, or unknown. Explicit title/description statements determine the label; absence of 'senior' does not mean entry level. Preserve minimum/maximum years and whether experience is required or preferred. Do not equate years alone with seniority. Conflicts are reviewable and unknowns remain visible.

Work arrangement is remote, hybrid, on-site, conflicting, or unknown. Require explicit source fields or clear job-specific statements. 'Remote interview', office perks, a city name, or missing remote flags do not establish arrangement. Telework eligibility alone does not establish hybrid frequency. Conflicting evidence is not silently resolved.

## Analytical questions

1. Within the documented sample, how many unique postings fall into each target role, and what share does each role represent?
2. How do advertised annual base-pay distributions differ by role and explicitly stated seniority, given salary coverage and comparability limits?
3. Which technical skills are mentioned most often within each role, and how much usable description text supports those measures?
4. How do role mix and skill mentions vary across eligible cities, accounting for multi-location postings and small groups?
5. What seniority and minimum-experience requirements are explicitly advertised, and what is unknown or conflicting?
6. What shares explicitly identify remote, hybrid, or on-site arrangements, and what share cannot be classified?
7. Only if validated posting dates and comparable collection coverage exist, how do observed posting counts change over time?

## Expected value and limitations

Potential value is better-informed search criteria, training priorities, and workforce conversations. No savings, salary advantage, or hiring impact is quantified in Phase 1.

Observed postings are advertisements, not filled jobs, hires, unique vacancies, labor shortages, or employer headcount. One posting can cover several vacancies or none; reposts and evergreen ads can persist. Board/vendor selection, incomplete queries, restricted access, description truncation, and salary disclosure practices create bias. Skill mentions are not verified employer requirements or applicant proficiency. Pay bands are advertised base pay, not realized compensation or total compensation. Descriptive differences do not show causation, and the sample is not a probability sample of all Bay Area jobs. Temporal comparisons require stable coverage; collection dates cannot recreate historical posting dates.

Success for Phase 1 means real setup files, consistent definitions, evidence-linked feasibility research, a conceptual relational design, and an explicit Phase 2 approval gate. No data collection, production ETL, SQL tables, analytical results, or dashboard is part of Phase 1.
