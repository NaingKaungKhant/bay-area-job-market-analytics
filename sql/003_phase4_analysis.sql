-- Phase 4 read-only queries. Each named section is one SELECT statement.
-- All substantive metrics use v_target_job_records. Only cohort_audit describes
-- the retained audit cases outside that denominator. No schema/view changes occur.

-- name: cohort_audit
SELECT role_status, COUNT(*) AS records,
       100.0*COUNT(*)/NULLIF((SELECT COUNT(*) FROM fact_job_postings),0) AS retained_share_pct
FROM fact_job_postings GROUP BY role_status ORDER BY role_status;

-- name: role_summary
-- Aggregate before joining bridges: a record with 8 skills is still one record.
SELECT role, COUNT(*) AS records,
       100.0*COUNT(*)/NULLIF((SELECT COUNT(*) FROM v_target_job_records),0) AS cohort_share_pct,
       SUM(skill_list_status='populated') AS usable_tag_records,
       SUM(skill_list_status='missing') AS missing_tag_records,
       SUM(skill_list_status='empty') AS empty_tag_records,
       SUM(skill_list_status='malformed') AS malformed_tag_records,
       100.0*SUM(skill_list_status='populated')/COUNT(*) AS tag_coverage_pct,
       SUM(salary_year_x100 IS NOT NULL) AS derived_annual_present,
       SUM(salary_hour_x100 IS NOT NULL) AS derived_hourly_present,
       100.0*SUM(salary_year_x100 IS NOT NULL)/COUNT(*) AS derived_annual_coverage_pct,
       SUM(advertised_salary_eligible) AS verified_advertised_salary_records,
       SUM(seniority NOT IN ('unknown','mixed/conflicting')) AS explicit_seniority_records,
       SUM(seniority='unknown') AS unknown_seniority_records,
       SUM(seniority='mixed/conflicting') AS conflicting_seniority_records,
       SUM(work_arrangement='unknown') AS unknown_arrangement_records
FROM v_target_job_records GROUP BY role ORDER BY role;

-- name: skill_by_role
-- Populated inherited lists form the denominator. Missing lists are not negatives.
-- CROSS JOIN includes observed zeros, with NULL rates for roles lacking usable tags.
WITH denominators AS (
    SELECT role,COUNT(*) AS role_records,SUM(skill_list_status='populated') AS usable_tag_records
    FROM v_target_job_records GROUP BY role
), mentions AS (
    SELECT f.role,b.skill_id,COUNT(DISTINCT f.job_posting_id) AS tagged_records
    FROM v_target_job_records f JOIN bridge_job_skills b USING(job_posting_id)
    WHERE f.skill_list_status='populated' GROUP BY f.role,b.skill_id
)
SELECT d.role,s.canonical_name AS skill,COALESCE(m.tagged_records,0) AS tagged_records,
       d.role_records,d.usable_tag_records,
       100.0*COALESCE(m.tagged_records,0)/NULLIF(d.usable_tag_records,0) AS usable_tag_pct,
       CASE WHEN d.usable_tag_records>=10 THEN
         100.0*COALESCE(m.tagged_records,0)/d.usable_tag_records END AS comparison_pct,
       CASE WHEN d.usable_tag_records>=10 THEN 1 ELSE 0 END AS comparison_allowed,
       -- Logical sensitivity bounds if every unavailable list lacks/has this tag.
       -- These are NOT confidence intervals or bounds on true job requirements.
       100.0*COALESCE(m.tagged_records,0)/d.role_records AS all_record_lower_pct,
       100.0*(COALESCE(m.tagged_records,0)+d.role_records-d.usable_tag_records)/d.role_records AS all_record_upper_pct
FROM denominators d CROSS JOIN dim_skills s
LEFT JOIN mentions m ON m.role=d.role AND m.skill_id=s.skill_id
ORDER BY d.role,s.canonical_name;

-- name: geography_by_role
-- COUNT(DISTINCT) prevents skill/location inflation; all in-Bay localities retained.
-- A community or county-only label must not be relabeled as an incorporated city.
WITH membership AS (
    SELECT DISTINCT f.job_posting_id,f.role,f.skill_list_status,l.location_id,
           l.locality,l.county,l.location_precision
    FROM v_target_job_records f JOIN bridge_job_locations b USING(job_posting_id)
    JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
)
SELECT location_id,locality,county,location_precision,role,COUNT(*) AS records,
       SUM(skill_list_status='populated') AS usable_tag_records,
       100.0*SUM(skill_list_status='populated')/COUNT(*) AS tag_coverage_pct,
       100.0*COUNT(*)/NULLIF((SELECT COUNT(*) FROM v_target_job_records),0) AS cohort_membership_pct,
       CASE WHEN COUNT(*)<10 THEN 1 ELSE 0 END AS small_group
FROM membership GROUP BY location_id,role ORDER BY location_id,role;

-- name: county_by_role
-- Two locations within the same county still count once in that county.
WITH membership AS (
    SELECT DISTINCT f.job_posting_id,f.role,l.county
    FROM v_target_job_records f JOIN bridge_job_locations b USING(job_posting_id)
    JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
)
SELECT county,role,COUNT(*) AS records,CASE WHEN COUNT(*)<10 THEN 1 ELSE 0 END AS small_group
FROM membership GROUP BY county,role ORDER BY county,role;

-- name: geography_coverage
-- Overlapping membership counts are not substituted for the regional denominator.
WITH counts AS (
    SELECT f.job_posting_id,
           COUNT(DISTINCT CASE WHEN l.in_bay_area=1 THEN l.location_id END) AS bay_locations,
           COUNT(DISTINCT CASE WHEN l.in_bay_area=1 AND l.location_precision='city' THEN l.location_id END) AS bay_cities,
           COUNT(DISTINCT CASE WHEN l.in_bay_area=1 AND l.location_precision='community' THEN l.location_id END) AS bay_communities,
           COUNT(DISTINCT CASE WHEN l.in_bay_area=1 THEN l.county END) AS bay_counties
    FROM v_target_job_records f LEFT JOIN bridge_job_locations b USING(job_posting_id)
    LEFT JOIN dim_locations l USING(location_id) GROUP BY f.job_posting_id
)
SELECT COUNT(*) AS cohort_records,SUM(bay_locations>1) AS multi_bay_location_records,
       SUM(bay_cities>0) AS records_with_city,SUM(bay_communities>0) AS records_with_community,
       SUM(bay_cities=0 AND bay_communities=0) AS county_only_records,
       SUM(bay_locations) AS bay_location_memberships,SUM(bay_counties) AS bay_county_memberships
FROM counts;

-- name: seniority_by_role
-- Unknown/conflicting categories stay visible. No senior word does not mean junior.
SELECT f.role,f.seniority,COUNT(*) AS records,
       100.0*COUNT(*)/(SELECT COUNT(*) FROM v_target_job_records x WHERE x.role=f.role) AS role_share_pct,
       CASE WHEN COUNT(*)<10 THEN 1 ELSE 0 END AS small_group
FROM v_target_job_records f GROUP BY f.role,f.seniority ORDER BY f.role,f.seniority;

-- name: locality_skill_by_role
-- First make distinct record-location memberships, then join unique job-skill pairs.
-- The denominator is usable records in THIS locality and role, not all tagged records.
WITH membership AS (
    SELECT DISTINCT f.job_posting_id,f.role,f.skill_list_status,l.location_id,
           l.locality,l.county,l.location_precision
    FROM v_target_job_records f JOIN bridge_job_locations b USING(job_posting_id)
    JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
), denominators AS (
    SELECT location_id,role,locality,county,location_precision,COUNT(*) AS role_location_records,
           SUM(skill_list_status='populated') AS usable_tag_records
    FROM membership GROUP BY location_id,role
), mentions AS (
    SELECT m.location_id,m.role,b.skill_id,COUNT(DISTINCT m.job_posting_id) AS tagged_records
    FROM membership m JOIN bridge_job_skills b USING(job_posting_id)
    WHERE m.skill_list_status='populated' GROUP BY m.location_id,m.role,b.skill_id
)
SELECT d.location_id,d.locality,d.county,d.location_precision,d.role,s.canonical_name AS skill,
       m.tagged_records,d.role_location_records,d.usable_tag_records,
       CASE WHEN d.usable_tag_records>=10 THEN 100.0*m.tagged_records/d.usable_tag_records END AS comparison_pct,
       CASE WHEN d.usable_tag_records>=10 THEN 1 ELSE 0 END AS comparison_allowed
FROM denominators d JOIN mentions m ON m.location_id=d.location_id AND m.role=d.role
JOIN dim_skills s ON s.skill_id=m.skill_id ORDER BY d.location_id,d.role,s.canonical_name;

-- name: skill_count_summary
-- Only populated lists: missing/empty/malformed lists do not become zero skills.
-- Quantiles use linear interpolation at (n-1)*q, matching pandas/numpy defaults.
WITH counts AS (
    SELECT f.job_posting_id,f.role,COUNT(b.skill_id) AS tags
    FROM v_target_job_records f LEFT JOIN bridge_job_skills b USING(job_posting_id)
    WHERE f.skill_list_status='populated' GROUP BY f.job_posting_id
), ranked AS (
    SELECT role,tags,ROW_NUMBER() OVER(PARTITION BY role ORDER BY tags,job_posting_id)-1 AS ordinal,
           COUNT(*) OVER(PARTITION BY role) AS n FROM counts
), quantiles(q) AS (VALUES(0.25),(0.5),(0.75)), positions AS (
    SELECT r.*,q,q*(n-1) AS position FROM ranked r CROSS JOIN quantiles
), interpolated AS (
    SELECT role,q,
      MAX(CASE WHEN ordinal=CAST(position AS INTEGER) THEN tags END)*(1-(position-CAST(position AS INTEGER)))+
      MAX(CASE WHEN ordinal=CASE WHEN position=CAST(position AS INTEGER) THEN CAST(position AS INTEGER) ELSE CAST(position AS INTEGER)+1 END THEN tags END)*
      (position-CAST(position AS INTEGER)) AS value
    FROM positions GROUP BY role,q
), summaries AS (
    SELECT role,COUNT(*) AS usable_tag_records,AVG(tags) AS mean_tags,MIN(tags) AS min_tags,MAX(tags) AS max_tags
    FROM counts GROUP BY role
)
SELECT s.role,s.usable_tag_records,s.mean_tags,s.min_tags,s.max_tags,
       MAX(CASE WHEN q=0.25 THEN value END) AS q1_tags,
       MAX(CASE WHEN q=0.5 THEN value END) AS median_tags,
       MAX(CASE WHEN q=0.75 THEN value END) AS q3_tags
FROM summaries s JOIN interpolated i USING(role) GROUP BY s.role ORDER BY s.role;
