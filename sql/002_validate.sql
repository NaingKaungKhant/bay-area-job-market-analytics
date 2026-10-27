-- Each query returns a named number of violations. Zero is required for every row.
-- Count facts before crossing two many-to-many bridges: joining skills to locations
-- directly would multiply records and inflate later dashboard metrics.
SELECT 'missing_bay_location' AS check_name, COUNT(*) AS violations
FROM fact_job_postings f WHERE NOT EXISTS (
    SELECT 1 FROM bridge_job_locations b JOIN dim_locations l USING(location_id)
    WHERE b.job_posting_id = f.job_posting_id AND l.in_bay_area = 1
)
UNION ALL
SELECT 'missing_source_lineage', COUNT(*) FROM fact_job_postings f WHERE NOT EXISTS (
    SELECT 1 FROM source_posting_records s WHERE s.job_posting_id = f.job_posting_id
)
UNION ALL
SELECT 'populated_skills_without_bridge', COUNT(*) FROM fact_job_postings f
WHERE skill_list_status = 'populated' AND NOT EXISTS (
    SELECT 1 FROM bridge_job_skills b WHERE b.job_posting_id = f.job_posting_id
)
UNION ALL
SELECT 'unexpected_skills_for_unusable_list', COUNT(*) FROM fact_job_postings f
WHERE skill_list_status != 'populated' AND EXISTS (
    SELECT 1 FROM bridge_job_skills b WHERE b.job_posting_id = f.job_posting_id
)
UNION ALL
SELECT 'inflated_target_location_membership',
    (SELECT COUNT(*) FROM v_target_job_records) -
    (SELECT COUNT(DISTINCT f.job_posting_id) FROM v_target_job_records f
     JOIN bridge_job_locations b USING(job_posting_id) JOIN dim_locations l USING(location_id)
     WHERE l.in_bay_area = 1)
UNION ALL
SELECT 'unsupported_salary_eligibility', COUNT(*) FROM fact_job_postings
WHERE advertised_salary_eligible != 0 OR salary_currency IS NOT NULL;
