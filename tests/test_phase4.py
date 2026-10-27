"""TEST_ONLY records exercise analytical contracts, never real-market findings."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.analysis import (compute_tables, descriptive_comparisons, python_tables,
                          reconcile, verified_connection, records)
from src.build_database import build, insert_row
from src.luke_dataset import EXPECTED_COLUMNS, read_json

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def db():
    c=sqlite3.connect(':memory:')
    c.executescript((ROOT/'sql/001_schema.sql').read_text())
    yield c
    c.close()


def job(c,n,role='Data Analyst',tags=('sql',),status='accepted_title_only',seniority='unknown',locations=(1,)):
    """Construct only TEST_ONLY relational fixtures, respecting Phase 3 constraints."""
    insert_row(c,'fact_job_postings',dict(job_posting_id=n,original_title=f'TEST_ONLY {n}',
        normalized_title=f'test_only {n}',role=role if status=='accepted_title_only' else None,
        role_status=status,role_evidence_json='{}',seniority=seniority,source_posted_at='2023-01-01T00:00:00',
        employment_types_json='[]',skill_list_status=('missing' if tags is None else 'populated' if tags else 'empty'),rule_version='TEST_ONLY'))
    for tag in tags or []:
        found=c.execute('SELECT skill_id FROM dim_skills WHERE canonical_name=?',(tag,)).fetchone()
        skill_id=found[0] if found else insert_row(c,'dim_skills',dict(canonical_name=tag,taxonomy_version='TEST_ONLY'))
        insert_row(c,'bridge_job_skills',dict(job_posting_id=n,skill_id=skill_id,original_tags_json=json.dumps([tag])))
    known={1:('San Francisco','San Francisco','CA','city',1),2:('Oakland','Alameda','CA','city',1),
           3:('Stanford','Santa Clara','CA','community',1),4:(None,'Alameda','CA','county',1),
           5:('Berkeley','Alameda','CA','city',1),6:('Austin',None,'TX','city',0)}
    for loc in locations:
        if not c.execute('SELECT 1 FROM dim_locations WHERE location_id=?',(loc,)).fetchone():
            name,county,state,precision,bay=known[loc]
            insert_row(c,'dim_locations',dict(location_id=loc,location_key=f'TEST_ONLY_{loc}',locality=name,
                county=county,state=state,country='US',location_precision=precision,in_bay_area=bay))
        insert_row(c,'bridge_job_locations',dict(job_posting_id=n,location_id=loc,raw_location='TEST_ONLY'))


def test_join_inflation_and_audit_exclusion(db):
    job(db,1,tags=('sql','python'),locations=(1,2,5,6))
    job(db,2,tags=('sql',),locations=(4,))
    job(db,3,role='Data Scientist',tags=('python',),locations=(3,))
    job(db,4,tags=('sql',),status='ambiguous')
    job(db,5,tags=None,status='unclassified')
    t=compute_tables(db,ROOT)
    assert len(reconcile(db,ROOT,t))==9
    role=t['role_summary'].set_index('role')
    assert role.loc['Data Analyst','records']==2
    assert role.loc['Data Analyst','usable_tag_records']==2
    assert t['cohort_audit'].records.sum()==5
    assert t['role_summary'].records.sum()==3
    skill=t['skill_by_role'].query("role=='Data Analyst' and skill=='sql'").iloc[0]
    assert skill.tagged_records==2 and skill.usable_tag_pct==100
    coverage=t['geography_coverage'].iloc[0]
    assert coverage.multi_bay_location_records==1
    assert coverage.bay_location_memberships==5
    assert coverage.bay_county_memberships==4
    assert coverage.county_only_records==1
    assert coverage.records_with_community==1
    assert t['county_by_role'].query("county=='Alameda' and role=='Data Analyst'").iloc[0].records==2
    # One record has two skills and three Bay locations; a naive join has 6 rows.
    inflated=db.execute('SELECT COUNT(*) FROM v_target_job_records f JOIN bridge_job_skills s USING(job_posting_id) JOIN bridge_job_locations l USING(job_posting_id) WHERE f.job_posting_id=1').fetchone()[0]
    assert inflated==8  # Includes the outside-Bay location too; regional n still 1.


def test_missing_empty_malformed_and_zero_denominator(db):
    job(db,1,tags=None)
    job(db,2,tags=())
    job(db,3,role='Data Scientist',tags=('python',))
    db.execute("UPDATE fact_job_postings SET skill_list_status='malformed' WHERE job_posting_id=1")
    t=compute_tables(db,ROOT)
    reconcile(db,ROOT,t)
    a=t['role_summary'].set_index('role').loc['Data Analyst']
    assert a.records==2 and a.usable_tag_records==0 and a.empty_tag_records==1 and a.malformed_tag_records==1
    s=t['skill_by_role'].query("role=='Data Analyst' and skill=='python'").iloc[0]
    assert pd.isna(s.usable_tag_pct) and pd.isna(s.comparison_pct)
    assert s.all_record_lower_pct==0 and s.all_record_upper_pct==100
    assert 'Data Analyst' not in t['skill_count_summary'].role.tolist()


@pytest.mark.parametrize('n,allowed',[(9,0),(10,1)])
def test_existing_small_group_boundary(db,n,allowed):
    for i in range(1,n+1):job(db,i)
    t=compute_tables(db,ROOT)
    reconcile(db,ROOT,t)
    s=t['skill_by_role'].iloc[0]
    assert s.comparison_allowed==allowed
    assert (not pd.isna(s.comparison_pct))==bool(allowed)
    local=t['locality_skill_by_role'].iloc[0]
    assert local.comparison_allowed==allowed


@pytest.mark.parametrize('sizes',[[1],[1,2],[1,2,8],[1,2,4,8],[2,2,2,8,10]])
def test_sql_linear_quantiles_match_numpy(db,sizes):
    for i,size in enumerate(sizes,1):job(db,i,tags=tuple(f'TEST_ONLY_{k}' for k in range(size)))
    t=compute_tables(db,ROOT)
    reconcile(db,ROOT,t)
    row=t['skill_count_summary'].iloc[0]
    np.testing.assert_allclose([row.q1_tags,row.median_tags,row.q3_tags],np.quantile(sizes,[.25,.5,.75],method='linear'))
    assert row.mean_tags==pytest.approx(np.mean(sizes))


def test_unavailable_lists_bound_observed_tag_content(db):
    for n in range(1,13):
        tags=('sql',) if n<=5 else ('python',) if n<=10 else None
        job(db,n,tags=tags)
    s=compute_tables(db,ROOT)['skill_by_role'].query("skill=='sql'").iloc[0]
    assert s.usable_tag_pct==50
    assert s.all_record_lower_pct==pytest.approx(100*5/12)
    assert s.all_record_upper_pct==pytest.approx(100*7/12)
    assert s.all_record_lower_pct<=s.usable_tag_pct<=s.all_record_upper_pct


def test_descriptive_difference_is_percentage_points(db):
    for n in range(1,11):job(db,n,role='Data Scientist',tags=('python',) if n<=8 else ('sql',))
    for n in range(11,21):job(db,n,role='Data Engineer',tags=('python',) if n<=14 else ('sql',))
    t=compute_tables(db,ROOT)
    row=descriptive_comparisons(t['skill_by_role'])[0]
    assert row['first_pct']==80 and row['second_pct']==40 and row['difference_pp']==40
    assert 'p_value' not in row and 'confidence_interval' not in row


def test_unknown_seniority_not_entry_and_suppressed_contrast(db):
    job(db,1,role='Data Scientist',tags=('python',),seniority='unknown')
    job(db,2,role='Data Engineer',tags=('python',),seniority='mixed/conflicting')
    t=compute_tables(db,ROOT)
    reconcile(db,ROOT,t)
    assert set(t['seniority_by_role'].seniority)=={'unknown','mixed/conflicting'}
    assert all(r['explicit_seniority_records']==0 for r in records(t['role_summary']))
    contrast=descriptive_comparisons(t['skill_by_role'])[0]
    assert contrast['difference_pp'] is None and not contrast['comparison_allowed']


def test_reconciliation_detects_wrong_denominator(db):
    job(db,1)
    t=compute_tables(db,ROOT)
    t['role_summary'].loc[0,'records']=2
    with pytest.raises(AssertionError):reconcile(db,ROOT,t)


def test_no_accepted_records_is_not_zero_percent_finding(db):
    job(db,1,status='ambiguous')
    with pytest.raises(ValueError,match='No accepted'):python_tables(db)


def test_json_unavailable_is_null():
    assert records(pd.DataFrame({'value':[np.nan]}))==[{'value':None}]


@pytest.fixture
def validated_project(tmp_path):
    """Build tiny TEST_ONLY Phase 3 output to exercise Phase 4 provenance guards."""
    for name in ['config','sql','src','reports','data/raw/luke_2023']:(tmp_path/name).mkdir(parents=True)
    for name in ['phase2_plan.json','source_access.json','phase3_rules.json','bay_area_cities.json']:
        shutil.copy(ROOT/'config'/name,tmp_path/'config'/name)
    for name in ['001_schema.sql','002_validate.sql','003_phase4_analysis.sql']:
        shutil.copy(ROOT/'sql'/name,tmp_path/'sql'/name)
    for name in ['cleaning.py','build_database.py']:
        shutil.copy(ROOT/'src'/name,tmp_path/'src'/name)
    raw=tmp_path/'data/raw/luke_2023/data_jobs.csv'
    row=dict.fromkeys(EXPECTED_COLUMNS,'')
    row.update(job_title='TEST_ONLY Data Analyst',job_title_short='Data Analyst',company_name='TEST_ONLY',
               job_country='United States',job_location='San Francisco, CA',job_posted_date='2023-01-01',job_skills="['sql']")
    with raw.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=EXPECTED_COLUMNS);writer.writeheader();writer.writerow(row)
    plan=read_json(tmp_path/'config/phase2_plan.json')
    plan.update(expected_bytes=raw.stat().st_size,expected_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    (tmp_path/'config/phase2_plan.json').write_text(json.dumps(plan))
    manifest=dict(source=plan['source'],revision=plan['revision'],source_file='data_jobs.csv',status='complete',
        sha256=plan['expected_sha256'],bytes=plan['expected_bytes'],row_count=1,completed_at_utc='TEST_ONLY')
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    s=build(tmp_path)
    (tmp_path/'reports/phase3_cleaning_report.json').write_text(json.dumps(s))
    return tmp_path


def test_verified_connection_readonly_and_raw_directory_not_required(validated_project):
    root=validated_project
    # Simulate the observed inaccessible raw directory: analysis requires the
    # validated DB/report/plan, not another acquisition or raw-file read.
    shutil.rmtree(root/'data/raw')
    with verified_connection(root) as (c,s,before):
        t=compute_tables(c,root);reconcile(c,root,t)
        with pytest.raises(sqlite3.OperationalError):c.execute('DELETE FROM fact_job_postings')
    path=root/'data/processed/phase3/job_market.sqlite3'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_changed_database_rejected(validated_project):
    root=validated_project
    c=sqlite3.connect(root/'data/processed/phase3/job_market.sqlite3')
    c.execute("UPDATE fact_job_postings SET normalized_title='TEST_ONLY_changed'");c.commit();c.close()
    with pytest.raises(ValueError,match='content differs'):
        with verified_connection(root):pass


def test_changed_rules_rejected_without_cleaning(validated_project):
    path=validated_project/'config/phase3_rules.json'
    path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='code/config differs'):
        with verified_connection(validated_project):pass


def test_local_permission_still_required(validated_project):
    path=validated_project/'config/source_access.json';access=read_json(path)
    access['permissions']['local_analysis']=False;path.write_text(json.dumps(access))
    with pytest.raises(PermissionError):
        with verified_connection(validated_project):pass


def test_figures_use_reconciled_sql_values(db,tmp_path):
    from src.analysis_charts import plot_figures
    for k,role in enumerate(['Data Analyst','Data Engineer','Data Scientist','Machine Learning Engineer']):
        for j in range(10):job(db,k*10+j+1,role=role,tags=('python','sql','tableau'))
    job(db,99,status='ambiguous')
    job(db,100,status='unclassified')
    job(db,101,status='out_of_scope')
    t=compute_tables(db,ROOT);reconcile(db,ROOT,t)
    figures=plot_figures(t,tmp_path)
    assert len(figures)==7
    assert all(r['artist_checks']=='passed' for r in figures.values())
    assert all((tmp_path/r['file']).stat().st_size>1000 for r in figures.values())


def test_missingness_difference_ranges_are_not_confidence_intervals(db):
    for n in range(1,13):job(db,n,role='Data Scientist',tags=('python',) if n<=8 else ('sql',) if n<=10 else None)
    for n in range(13,25):job(db,n,role='Data Engineer',tags=('python',) if n<=16 else ('sql',) if n<=22 else None)
    row=descriptive_comparisons(compute_tables(db,ROOT)['skill_by_role'])[0]
    assert row['all_record_difference_lower_pp']==pytest.approx(100*(8-6)/12)
    assert row['all_record_difference_upper_pp']==pytest.approx(100*(10-4)/12)
    assert row['all_record_difference_lower_pp']<=row['difference_pp']<=row['all_record_difference_upper_pp']


def test_database_snapshot_cannot_silently_switch_source(validated_project):
    c=sqlite3.connect(validated_project/'data/processed/phase3/job_market.sqlite3')
    c.execute("UPDATE collection_snapshots SET source_name='TEST_ONLY_unapproved_source'");c.commit();c.close()
    with pytest.raises(ValueError,match='snapshot differs'):
        with verified_connection(validated_project):pass


def test_small_skill_charts_keep_unavailable_rates(db,tmp_path):
    from src.analysis_charts import plot_figures
    for n,role in enumerate(['Data Analyst','Data Engineer','Data Scientist','Machine Learning Engineer'],1):
        job(db,n,role=role,tags=('python','sql','tableau'))
    t=compute_tables(db,ROOT);reconcile(db,ROOT,t)
    figs=plot_figures(t,tmp_path)
    assert figs['phase4_skill_profile']['plotted_data']==[]
    assert all(row['comparison_pct'] is None for row in figs['phase4_missingness_sensitivity']['plotted_data'])
