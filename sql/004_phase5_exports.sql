-- Phase 5 export contract. All statements are SELECTs; no SQLite schema changes.
-- One row is ONE metric category for ONE exact geography/role selection. Tableau
-- selects one slice with parameters, never sums overlapping geographic rollups.
-- common
WITH role_choices(role_selection) AS (
 VALUES('All roles'),('Data Analyst'),('Data Engineer'),('Data Scientist'),('Machine Learning Engineer')
), scopes AS (
 SELECT 'All Bay Area' AS scope_key,'region' AS scope_type,NULL AS location_id,NULL AS county
 UNION ALL SELECT 'County: '||county,'county',NULL,county FROM dim_locations WHERE in_bay_area=1 GROUP BY county
 UNION ALL SELECT CASE location_precision WHEN 'city' THEN 'City: ' WHEN 'community' THEN 'Community: ' ELSE 'County-only location: ' END||COALESCE(locality,county)||' ('||county||')',
 location_precision,location_id,county FROM dim_locations WHERE in_bay_area=1
), members AS (
 SELECT 'All Bay Area' AS scope_key,job_posting_id FROM v_target_job_records
 UNION
 SELECT 'County: '||l.county,f.job_posting_id FROM v_target_job_records f
 JOIN bridge_job_locations b USING(job_posting_id) JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
 UNION
 SELECT s.scope_key,f.job_posting_id FROM scopes s JOIN bridge_job_locations b ON b.location_id=s.location_id
 JOIN v_target_job_records f USING(job_posting_id)
), selections AS (
 SELECT s.scope_key,r.role_selection FROM scopes s CROSS JOIN role_choices r
), selected AS (
 SELECT m.scope_key,r.role_selection,f.* FROM members m JOIN v_target_job_records f USING(job_posting_id)
 JOIN role_choices r ON r.role_selection='All roles' OR r.role_selection=f.role
), totals AS (
 SELECT s.scope_key,s.role_selection,COUNT(f.job_posting_id) AS records,
 COALESCE(SUM(f.skill_list_status='populated'),0) AS usable,
 COALESCE(SUM(f.skill_list_status='missing'),0) AS missing,
 COALESCE(SUM(f.skill_list_status='empty'),0) AS empty_lists,
 COALESCE(SUM(f.skill_list_status='malformed'),0) AS malformed,
 COALESCE(SUM(f.salary_year_x100 IS NOT NULL AND f.job_posting_id IS NOT NULL),0) AS annual_present,
 COALESCE(SUM(f.seniority='unknown'),0) AS unknown_seniority,
 COALESCE(SUM(f.seniority='mixed/conflicting'),0) AS conflicting_seniority
 FROM selections s LEFT JOIN selected f ON f.scope_key=s.scope_key AND f.role_selection=s.role_selection
 GROUP BY s.scope_key,s.role_selection
), base_totals AS (
 SELECT scope_key,COUNT(*) AS records FROM members GROUP BY scope_key
), skill_counts AS (
 SELECT f.scope_key,f.role_selection,b.skill_id,COUNT(DISTINCT f.job_posting_id) AS n
 FROM selected f JOIN bridge_job_skills b USING(job_posting_id)
 WHERE f.skill_list_status='populated' GROUP BY f.scope_key,f.role_selection,b.skill_id
), skill_grid AS (
 SELECT t.scope_key,t.role_selection,s.canonical_name AS category,COALESCE(c.n,0) AS n,t.usable,t.records,
 ROW_NUMBER() OVER(PARTITION BY t.scope_key,t.role_selection ORDER BY COALESCE(c.n,0) DESC,s.canonical_name) AS category_order
 FROM totals t CROSS JOIN dim_skills s LEFT JOIN skill_counts c
 ON c.scope_key=t.scope_key AND c.role_selection=t.role_selection AND c.skill_id=s.skill_id
), seniority_choices(category,category_order) AS (
 VALUES('entry/junior',1),('mid',2),('senior',3),('lead/staff/principal',4),('management',5),('mixed/conflicting',6),('unknown',7)
), senior_counts AS (
 SELECT scope_key,role_selection,seniority,COUNT(*) AS n FROM selected GROUP BY scope_key,role_selection,seniority
), display_memberships AS (
 SELECT DISTINCT f.scope_key,f.role_selection,f.job_posting_id,'County' AS category_type,l.county AS category
 FROM selected f JOIN bridge_job_locations b USING(job_posting_id) JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
 UNION
 SELECT DISTINCT f.scope_key,f.role_selection,f.job_posting_id,
 CASE l.location_precision WHEN 'city' THEN 'City' WHEN 'community' THEN 'Community' ELSE 'County-only' END,
 COALESCE(l.locality,l.county)||' ('||l.county||')'
 FROM selected f JOIN bridge_job_locations b USING(job_posting_id) JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1
), geography_counts AS (
 SELECT scope_key,role_selection,category_type,category,COUNT(DISTINCT job_posting_id) AS n
 FROM display_memberships GROUP BY scope_key,role_selection,category_type,category
), audit_counts AS (
 SELECT role_status,COUNT(*) AS n FROM fact_job_postings GROUP BY role_status
), metric_rows AS (
 -- Role shares ALWAYS use all four accepted roles in the chosen geography. A
 -- single-role selection hides other bars but does not redefine its share as 100%.
 SELECT t.scope_key,t.role_selection,'roles' AS panel,'Role' AS category_type,r.role_selection AS category,
 CASE WHEN t.role_selection='All roles' OR t.role_selection=r.role_selection THEN COALESCE(x.records,0) ELSE 0 END AS numerator,
 COALESCE(bt.records,0) AS denominator,1 AS comparison_allowed,
 'Share of all four accepted roles in chosen geography' AS warning,1 AS category_order
 FROM totals t JOIN role_choices r ON r.role_selection!='All roles' AND (t.role_selection='All roles' OR t.role_selection=r.role_selection)
 LEFT JOIN totals x ON x.scope_key=t.scope_key AND x.role_selection=r.role_selection
 LEFT JOIN base_totals bt ON bt.scope_key=t.scope_key
 UNION ALL
 SELECT scope_key,role_selection,'skills','Skill',category,n,usable,CASE WHEN usable>=10 THEN 1 ELSE 0 END,
 CASE WHEN usable<10 THEN 'Skill comparisons suppressed: fewer than 10 usable lists' ELSE 'Inherited tags among usable lists; missing lists are not negatives' END,category_order FROM skill_grid
 UNION ALL
 SELECT t.scope_key,t.role_selection,'seniority','Seniority',s.category,COALESCE(c.n,0),t.records,1,
 'Unknown is not entry level; entry/junior includes interns',s.category_order
 FROM totals t CROSS JOIN seniority_choices s LEFT JOIN senior_counts c
 ON c.scope_key=t.scope_key AND c.role_selection=t.role_selection AND c.seniority=s.category
 UNION ALL
 SELECT g.scope_key,g.role_selection,'geography',g.category_type,g.category,g.n,t.records,1,
 CASE WHEN g.n<10 THEN 'Small group n<10; non-additive location association' ELSE 'Non-additive location association, not exclusive jobs' END,
 ROW_NUMBER() OVER(PARTITION BY g.scope_key,g.role_selection,g.category_type ORDER BY g.n DESC,g.category)
 FROM geography_counts g JOIN totals t ON t.scope_key=g.scope_key AND t.role_selection=g.role_selection
 UNION ALL
 SELECT scope_key,role_selection,'coverage','Coverage','Selected records',records,records,1,'Accepted title-only historical records',1 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Usable inherited tags',usable,records,1,'Missing lists are not evidence of absent skills',2 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Missing skill lists',missing,records,1,'Unavailable tags, not zero skills',3 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Empty skill lists',empty_lists,records,1,'Excluded from usable-list denominator',4 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Malformed skill lists',malformed,records,1,'Excluded from usable-list denominator',5 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Unknown seniority',unknown_seniority,records,1,'Not assumed to be entry level',6 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Conflicting seniority',conflicting_seniority,records,1,'Kept separate from explicit seniority',7 FROM totals
 UNION ALL SELECT scope_key,role_selection,'coverage','Coverage','Derived annual field present',annual_present,records,1,'Field coverage only; currency/provenance unverified; no pay comparison',8 FROM totals
 -- Replicated audit values are a GLOBAL, explicitly labeled context panel. The
 -- parameter filter retains exactly one copy per status, regardless of selection.
 UNION ALL SELECT t.scope_key,t.role_selection,'classification','Whole retained dataset',a.role_status,a.n,
 (SELECT COUNT(*) FROM fact_job_postings),1,'Global audit; unaffected by role/geography selectors',1
 FROM totals t CROSS JOIN audit_counts a
)
-- name: dashboard_metrics
SELECT *,CASE WHEN denominator>0 AND comparison_allowed=1 THEN 1.0*numerator/denominator END AS rate,
 (SELECT source_revision FROM collection_snapshots LIMIT 1) AS source_revision,
 (SELECT rule_version FROM collection_snapshots LIMIT 1) AS cleaning_rule_version
FROM metric_rows ORDER BY scope_key,role_selection,panel,category_type,category;

-- name: scope_catalog
SELECT scope_key,scope_type,location_id,county FROM scopes ORDER BY scope_key;

-- name: role_catalog
SELECT role_selection FROM role_choices ORDER BY role_selection;
