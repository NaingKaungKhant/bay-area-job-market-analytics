"""Phase 4 read-only analysis and independent pandas/SQL reconciliation.

No source, cleaning rules or database schema is changed. This module estimates
no salaries, population demand, hiring trends or causal effects.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from src.build_database import semantic_digest
from src.luke_dataset import digest_file, read_json, validate_approval

SQL_FILE = 'sql/003_phase4_analysis.sql'
MIN_GROUP = 10  # Existing KPI policy, not a statistical reliability guarantee.
COMPARISONS = [('python', 'Data Scientist', 'Data Engineer'),
               ('sql', 'Data Analyst', 'Data Engineer'),
               ('tableau', 'Data Analyst', 'Data Scientist')]


def read_queries(root):
    """Named SELECT blocks make every output traceable to a reviewable SQL query."""
    text = (Path(root)/SQL_FILE).read_text()
    parts = re.split(r'^-- name: (\w+)\s*$', text, flags=re.M)
    queries = dict(zip(parts[1::2], parts[2::2]))
    if not queries or len(queries) != (len(parts)-1)//2:
        raise ValueError('Missing/duplicate SQL query names.')
    return queries


@contextmanager
def verified_connection(root):
    """Fail closed on stale Phase 3 inputs; SQLite mode=ro also prevents writes."""
    root = Path(root).resolve()
    plan, access = read_json(root/'config/phase2_plan.json'), read_json(root/'config/source_access.json')
    validate_approval(plan, access)
    summary = read_json(root/'data/processed/phase3/build_summary.json')
    for name, expected in summary['config_sha256'].items():
        if digest_file(root/name) != expected:
            raise ValueError('Phase 3 code/config differs from validated build; stop for review.')
    if summary['raw_sha256'] != plan['expected_sha256'] or summary['revision'] != plan['revision']:
        raise ValueError('Phase 3 source differs from approved release.')
    # Do not reopen the raw directory: on this host even its manifest read
    # stalled. Phase 4 relies on recorded Phase 3 acquisition evidence, then
    # verifies actual database content below. It makes no raw-file hash claim.
    recorded = read_json(root/'reports/phase3_cleaning_report.json')
    if recorded['raw_sha256'] != summary['raw_sha256'] or recorded['semantic_sha256'] != summary['semantic_sha256']:
        raise ValueError('Phase 3 report and local database lineage disagree.')
    path = root/'data/processed/phase3/job_market.sqlite3'
    before = digest_file(path)
    connection = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
    connection.execute('PRAGMA query_only = ON')
    try:
        snapshot = connection.execute('SELECT source_name,source_revision,raw_sha256,rule_version FROM collection_snapshots ORDER BY snapshot_id').fetchall()
        if snapshot != [(plan['source'],plan['revision'],plan['expected_sha256'],summary['rule_version'])]:
            raise ValueError('Database source snapshot differs from approved Phase 3 release.')
        validate_readonly_database(connection, summary['retained_records'])
        if semantic_digest(connection) != summary['semantic_sha256']:
            raise ValueError('Phase 3 database content differs from validated build.')
        yield connection, summary, before
    finally:
        connection.close()
        if digest_file(path) != before:
            raise ValueError('Database bytes changed during read-only analysis.')



def validate_readonly_database(connection, expected_count):
    """Set-based checks avoid expensive per-row scans without adding indexes."""
    n = connection.execute('SELECT COUNT(*) FROM fact_job_postings').fetchone()[0]
    source_n, source_distinct = connection.execute('SELECT COUNT(*),COUNT(DISTINCT job_posting_id) FROM source_posting_records').fetchone()
    bay_n = connection.execute('SELECT COUNT(DISTINCT b.job_posting_id) FROM bridge_job_locations b JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1').fetchone()[0]
    invalid_skills = connection.execute("""WITH sizes AS (SELECT job_posting_id,COUNT(*) AS n FROM bridge_job_skills GROUP BY job_posting_id)
        SELECT COUNT(*) FROM fact_job_postings f LEFT JOIN sizes s USING(job_posting_id)
        WHERE (f.skill_list_status='populated') != (COALESCE(s.n,0)>0)""").fetchone()[0]
    checks = {'fact_count':n==expected_count,'source_lineage_count':source_n==n==source_distinct,
              'bay_membership':bay_n==n,'skill_bridge_consistency':invalid_skills==0,
              'foreign_keys':not connection.execute('PRAGMA foreign_key_check').fetchall(),
              'sqlite_integrity':connection.execute('PRAGMA integrity_check').fetchall()==[('ok',)]}
    if not all(checks.values()):
        raise ValueError(f'Read-only database validation failed: {checks}')
    return checks


def compute_tables(connection, root):
    return {name: pd.read_sql_query(query, connection) for name, query in read_queries(root).items()}


def python_tables(connection):
    """Rebuild the SQL summaries independently from record/bridge data in pandas.

    This catches accidental SQL denominators or join multiplication, rather than
    comparing one SQL query with a renamed copy of the same result.
    """
    facts = pd.read_sql_query('SELECT job_posting_id,role_status,role,seniority,skill_list_status,'
        'salary_year_x100 IS NOT NULL AS annual_present,salary_hour_x100 IS NOT NULL AS hourly_present,'
        'advertised_salary_eligible,work_arrangement FROM fact_job_postings', connection)
    f = facts.loc[facts.role_status.eq('accepted_title_only')].copy()
    if f.empty:
        raise ValueError('No accepted target-role records; analysis cannot proceed.')
    if f.job_posting_id.duplicated().any() or f.role.isna().any():
        raise ValueError('Accepted cohort must contain unique record IDs and resolved roles.')
    skills = pd.read_sql_query('SELECT * FROM dim_skills', connection)
    b = pd.read_sql_query('SELECT job_posting_id,skill_id FROM bridge_job_skills', connection)
    locs = pd.read_sql_query('SELECT * FROM dim_locations', connection)
    links = pd.read_sql_query('SELECT job_posting_id,location_id FROM bridge_job_locations', connection)
    if b.duplicated().any() or links.duplicated().any():
        raise ValueError('Bridge pairs must be unique.')
    result = {}
    audit = facts.groupby('role_status').size().rename('records').reset_index()
    audit['retained_share_pct'] = 100*audit.records/len(facts)
    result['cohort_audit'] = audit
    f['usable'] = f.skill_list_status.eq('populated')
    role_rows = []
    for role, g in f.groupby('role'):
        n = len(g)
        usable = int(g.usable.sum())
        role_rows.append(dict(role=role, records=n, cohort_share_pct=100*n/len(f),
            usable_tag_records=usable, missing_tag_records=int(g.skill_list_status.eq('missing').sum()),
            empty_tag_records=int(g.skill_list_status.eq('empty').sum()),
            malformed_tag_records=int(g.skill_list_status.eq('malformed').sum()), tag_coverage_pct=100*usable/n,
            derived_annual_present=int(g.annual_present.sum()),derived_hourly_present=int(g.hourly_present.sum()),
            derived_annual_coverage_pct=100*g.annual_present.sum()/n,
            verified_advertised_salary_records=int(g.advertised_salary_eligible.sum()),
            explicit_seniority_records=int((~g.seniority.isin(['unknown','mixed/conflicting'])).sum()),
            unknown_seniority_records=int(g.seniority.eq('unknown').sum()),
            conflicting_seniority_records=int(g.seniority.eq('mixed/conflicting').sum()),
            unknown_arrangement_records=int(g.work_arrangement.eq('unknown').sum())))
    roles = pd.DataFrame(role_rows)
    result['role_summary'] = roles
    tagged = f.loc[f.usable, ['job_posting_id','role']].merge(b, on='job_posting_id', validate='one_to_many')
    tagged = tagged.merge(skills[['skill_id','canonical_name']], on='skill_id', validate='many_to_one')
    grid = pd.MultiIndex.from_product([roles.role, skills.canonical_name], names=['role','skill']).to_frame(index=False)
    counts = tagged.groupby(['role','canonical_name']).job_posting_id.nunique().rename('tagged_records').reset_index().rename(columns={'canonical_name':'skill'})
    grid = grid.merge(counts, how='left', on=['role','skill']).fillna({'tagged_records':0})
    grid = grid.merge(roles[['role','records','usable_tag_records']].rename(columns={'records':'role_records'}), on='role')
    grid['usable_tag_pct'] = 100*grid.tagged_records/grid.usable_tag_records.replace(0,np.nan)
    grid['comparison_allowed'] = (grid.usable_tag_records>=MIN_GROUP).astype(int)
    grid['comparison_pct'] = grid.usable_tag_pct.where(grid.comparison_allowed.eq(1))
    grid['all_record_lower_pct'] = 100*grid.tagged_records/grid.role_records
    grid['all_record_upper_pct'] = 100*(grid.tagged_records+grid.role_records-grid.usable_tag_records)/grid.role_records
    result['skill_by_role'] = grid
    # Left joins are deliberately not crossed with the skill bridge here.
    membership = f.merge(links, on='job_posting_id', validate='one_to_many').merge(locs,on='location_id',validate='many_to_one')
    membership = membership.loc[membership.in_bay_area.eq(1)].drop_duplicates(['job_posting_id','location_id'])
    geo = membership.groupby(['location_id','role']).agg(records=('job_posting_id','nunique'),usable_tag_records=('usable','sum')).reset_index()
    geo = geo.merge(locs[['location_id','locality','county','location_precision']],on='location_id',validate='many_to_one')
    geo['tag_coverage_pct'] = 100*geo.usable_tag_records/geo.records
    geo['cohort_membership_pct'] = 100*geo.records/len(f)
    geo['small_group'] = (geo.records<MIN_GROUP).astype(int)
    result['geography_by_role'] = geo
    county = membership.drop_duplicates(['job_posting_id','county']).groupby(['county','role']).size().rename('records').reset_index()
    county['small_group'] = (county.records<MIN_GROUP).astype(int)
    result['county_by_role'] = county
    coverage = membership.groupby('job_posting_id').agg(bay_locations=('location_id','nunique'),bay_counties=('county','nunique')).reindex(f.job_posting_id,fill_value=0)
    for precision in ['city','community']:
        s = membership.loc[membership.location_precision.eq(precision)].groupby('job_posting_id').location_id.nunique()
        coverage['bay_'+precision] = s.reindex(coverage.index,fill_value=0)
    result['geography_coverage'] = pd.DataFrame([dict(cohort_records=len(f),
        multi_bay_location_records=int((coverage.bay_locations>1).sum()),
        records_with_city=int((coverage.bay_city>0).sum()), records_with_community=int((coverage.bay_community>0).sum()),
        county_only_records=int(((coverage.bay_city==0)&(coverage.bay_community==0)).sum()),
        bay_location_memberships=int(coverage.bay_locations.sum()),bay_county_memberships=int(coverage.bay_counties.sum()))])
    senior = f.groupby(['role','seniority']).size().rename('records').reset_index().merge(roles[['role','records']].rename(columns={'records':'denominator'}),on='role')
    senior['role_share_pct'] = 100*senior.records/senior.denominator
    senior['small_group'] = (senior.records<MIN_GROUP).astype(int)
    result['seniority_by_role'] = senior.drop(columns='denominator')
    local_tagged = membership.loc[membership.usable].merge(b,on='job_posting_id',validate='many_to_many').merge(skills[['skill_id','canonical_name']],on='skill_id',validate='many_to_one')
    local = local_tagged.groupby(['location_id','role','canonical_name']).job_posting_id.nunique().rename('tagged_records').reset_index().rename(columns={'canonical_name':'skill'})
    local = local.merge(geo.drop(columns=['tag_coverage_pct','cohort_membership_pct','small_group']).rename(columns={'records':'role_location_records'}),on=['location_id','role'],validate='many_to_one')
    local['comparison_allowed'] = (local.usable_tag_records>=MIN_GROUP).astype(int)
    local['comparison_pct'] = (100*local.tagged_records/local.usable_tag_records).where(local.comparison_allowed.eq(1))
    result['locality_skill_by_role'] = local
    sizes = b.groupby('job_posting_id').skill_id.nunique()
    valid = f.loc[f.usable,['job_posting_id','role']].copy()
    valid['tags'] = valid.job_posting_id.map(sizes)
    if valid.tags.isna().any():
        raise ValueError('A populated list has no skill bridge evidence.')
    rows = []
    for role,g in valid.groupby('role'):
        q = g.tags.quantile([.25,.5,.75],interpolation='linear')
        rows.append(dict(role=role,usable_tag_records=len(g),mean_tags=g.tags.mean(),min_tags=g.tags.min(),max_tags=g.tags.max(),q1_tags=q.loc[.25],median_tags=q.loc[.5],q3_tags=q.loc[.75]))
    result['skill_count_summary'] = pd.DataFrame(rows,columns=['role','usable_tag_records','mean_tags','min_tags','max_tags','q1_tags','median_tags','q3_tags'])
    return result


KEYS = {'cohort_audit':['role_status'], 'role_summary':['role'], 'skill_by_role':['role','skill'],
        'geography_by_role':['location_id','role'], 'county_by_role':['county','role'],
        'geography_coverage':[], 'seniority_by_role':['role','seniority'],
        'locality_skill_by_role':['location_id','role','skill'], 'skill_count_summary':['role']}


def reconcile(connection, root, sql_tables):
    expected = python_tables(connection)
    evidence = {}
    for name, actual in sql_tables.items():
        other = expected[name].reindex(columns=actual.columns)
        keys = KEYS[name]
        a = actual.sort_values(keys).reset_index(drop=True) if keys else actual.reset_index(drop=True)
        b = other.sort_values(keys).reset_index(drop=True) if keys else other.reset_index(drop=True)
        # SQL NULL and numpy NaN represent the same unavailable numeric value.
        # Normalize numeric columns explicitly to avoid pandas' future null mismatch.
        for column in a.columns:
            if pd.api.types.is_numeric_dtype(a[column]) or pd.api.types.is_numeric_dtype(b[column]):
                integer_count = pd.api.types.is_integer_dtype(a[column])
                a[column] = pd.to_numeric(a[column],errors='raise')
                b[column] = pd.to_numeric(b[column],errors='raise')
                if integer_count:
                    np.testing.assert_array_equal(a[column].to_numpy(),b[column].to_numpy())
        assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-10)
        evidence[name] = {'status':'matched', 'rows':len(actual), 'columns':len(actual.columns)}
    return evidence


def descriptive_comparisons(skill_table):
    """Unadjusted percentage-point differences, with no population inference.

    Each pair compares rates conditional on usable inherited tags. No p-values,
    confidence intervals or causal interpretation are justified by the source.
    """
    rows=[]
    for skill,first,second in COMPARISONS:
        a=skill_table.loc[(skill_table.skill==skill)&(skill_table.role==first)]
        b=skill_table.loc[(skill_table.skill==skill)&(skill_table.role==second)]
        if a.empty or b.empty:
            continue
        a,b=a.iloc[0],b.iloc[0]
        allowed=bool(a.comparison_allowed and b.comparison_allowed)
        rows.append(dict(skill=skill,first_role=first,second_role=second,
            first_usable_n=int(a.usable_tag_records),second_usable_n=int(b.usable_tag_records),
            first_tagged_n=int(a.tagged_records),second_tagged_n=int(b.tagged_records),
            first_pct=float(a.usable_tag_pct) if allowed else None,
            second_pct=float(b.usable_tag_pct) if allowed else None,
            difference_pp=float(a.usable_tag_pct-b.usable_tag_pct) if allowed else None,
            all_record_difference_lower_pp=float(a.all_record_lower_pct-b.all_record_upper_pct) if allowed else None,
            all_record_difference_upper_pp=float(a.all_record_upper_pct-b.all_record_lower_pct) if allowed else None,
            comparison_allowed=allowed))
    return rows


def records(frame):
    """JSON null represents unavailable statistics; never emit nonstandard NaN."""
    return json.loads(frame.to_json(orient='records',double_precision=15))
