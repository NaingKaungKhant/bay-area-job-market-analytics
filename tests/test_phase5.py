"""TEST_ONLY fixtures verify export math/serialization; never native Tableau claims."""
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as E
import zipfile

import numpy as np
import pandas as pd
import pytest

from test_phase4 import db,job,validated_project
from src.build_database import insert_row
from src.luke_dataset import digest_file
from src.tableau_exports import export,queries,validate_metrics,roundtrip_csv
from src.tableau_workbook import create

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def metric_db(db):
    insert_row(db,'collection_snapshots',dict(snapshot_id=1,source_name='TEST_ONLY',source_revision='TEST_ONLY',
        raw_sha256='TEST_ONLY',raw_row_count=0,acquired_at_utc='TEST_ONLY',rule_version='TEST_ONLY'))
    return db


def metrics(connection):
    return pd.read_sql_query(queries(ROOT)['dashboard_metrics'],connection)


def cell(frame,scope,role,panel,category,category_type=None):
    sub=frame.loc[frame.scope_key.eq(scope)&frame.role_selection.eq(role)&frame.panel.eq(panel)&frame.category.eq(category)]
    if category_type:sub=sub.loc[sub.category_type.eq(category_type)]
    assert len(sub)==1
    return sub.iloc[0]


def test_overlap_does_not_inflate_record_or_skill_counts(metric_db):
    c=metric_db
    job(c,1,tags=('sql','python'),locations=(1,2,5,6))
    job(c,2,tags=None,locations=(4,))
    job(c,3,role='Data Scientist',tags=('sql',),locations=(3,))
    job(c,4,status='ambiguous',tags=('sql',))
    frame=metrics(c);validate_metrics(frame)
    assert cell(frame,'All Bay Area','All roles','coverage','Selected records').numerator==3
    assert cell(frame,'County: Alameda','All roles','coverage','Selected records').numerator==2
    assert cell(frame,'All Bay Area','Data Analyst','skills','sql').numerator==1
    assert cell(frame,'All Bay Area','Data Analyst','skills','sql').denominator==1
    assert cell(frame,'All Bay Area','All roles','geography','Alameda','County').numerator==2
    assert cell(frame,'All Bay Area','All roles','geography','Oakland (Alameda)','City').numerator==1
    assert not frame.query("panel=='geography'").category.str.contains('Austin').any()
    # Regional records are not the sum of city/county rollups.
    counts=frame.query("scope_key=='All Bay Area' and role_selection=='All roles' and panel=='geography' and category_type=='County'")
    assert counts.numerator.sum()==4 and counts.denominator.iloc[0]==3


@pytest.mark.parametrize('n,allowed',[(0,0),(9,0),(10,1)])
def test_skill_suppression_and_zero_results(metric_db,n,allowed):
    c=metric_db
    # Keep a canonical tag even when there are zero selected accepted records.
    job(c,100,status='out_of_scope',tags=('sql',))
    for i in range(1,n+1):job(c,i,tags=('sql',))
    frame=metrics(c);validate_metrics(frame)
    row=cell(frame,'All Bay Area','Data Analyst','skills','sql')
    assert row.numerator==row.denominator==n
    assert row.comparison_allowed==allowed
    assert (not pd.isna(row.rate))==bool(allowed)
    if n==0:
        assert cell(frame,'All Bay Area','Data Analyst','coverage','Selected records').numerator==0


def test_missing_lists_remain_in_coverage_not_tag_denominator(metric_db):
    c=metric_db
    for i in range(1,11):job(c,i,tags=('sql',))
    job(c,11,tags=None);job(c,12,tags=())
    frame=metrics(c);validate_metrics(frame)
    row=cell(frame,'All Bay Area','Data Analyst','skills','sql')
    assert row.numerator==row.denominator==10 and row.rate==1
    coverage=cell(frame,'All Bay Area','Data Analyst','coverage','Usable inherited tags')
    assert coverage.numerator==10 and coverage.denominator==12 and coverage.rate==pytest.approx(10/12)
    assert cell(frame,'All Bay Area','Data Analyst','coverage','Missing skill lists').numerator==1
    assert cell(frame,'All Bay Area','Data Analyst','coverage','Empty skill lists').numerator==1


def test_role_share_uses_four_role_geo_denominator_and_audit_is_global(metric_db):
    job(metric_db,1,role='Data Analyst')
    job(metric_db,2,role='Data Scientist')
    job(metric_db,3,status='unclassified')
    frame=metrics(metric_db)
    assert cell(frame,'All Bay Area','Data Analyst','roles','Data Analyst').rate==.5
    assert cell(frame,'All Bay Area','Data Analyst','coverage','Selected records').numerator==1
    audit=cell(frame,'City: San Francisco (San Francisco)','Machine Learning Engineer','classification','unclassified')
    assert audit.numerator==1 and audit.denominator==3
    assert cell(frame,'City: San Francisco (San Francisco)','Machine Learning Engineer','coverage','Selected records').numerator==0


def test_community_county_only_unknown_and_conflicting_are_distinct(metric_db):
    job(metric_db,1,locations=(3,),seniority='unknown')
    job(metric_db,2,locations=(4,),seniority='mixed/conflicting')
    frame=metrics(metric_db);validate_metrics(frame)
    assert cell(frame,'All Bay Area','All roles','geography','Stanford (Santa Clara)','Community').numerator==1
    assert cell(frame,'All Bay Area','All roles','geography','Alameda (Alameda)','County-only').numerator==1
    assert cell(frame,'All Bay Area','All roles','seniority','unknown').numerator==1
    assert cell(frame,'All Bay Area','All roles','seniority','entry/junior').numerator==0


def test_unique_keys_and_bad_rate_fail(metric_db):
    job(metric_db,1)
    frame=metrics(metric_db)
    with pytest.raises(ValueError,match='duplicate'):validate_metrics(pd.concat([frame,frame.iloc[[0]]]))
    frame.loc[frame.rate.notna(),'rate']=9
    with pytest.raises(AssertionError):validate_metrics(frame)


def test_csv_utf8_null_zero_and_text_round_trip(tmp_path):
    frame=pd.DataFrame({'category':['TEST_ONLY café','TEST_ONLY 文字'],'numerator':[0,3],'rate':[np.nan,.5]})
    back=roundtrip_csv(frame,tmp_path/'TEST_ONLY.csv')
    assert back.loc[0,'rate']=='' and back.loc[0,'numerator']==0
    assert '文字' in (tmp_path/'TEST_ONLY.csv').read_text(encoding='utf-8')


@pytest.fixture
def export_project(validated_project):
    root=validated_project
    shutil.copy(ROOT/'sql/004_phase5_exports.sql',root/'sql/004_phase5_exports.sql')
    shutil.copy(ROOT/'src/tableau_exports.py',root/'src/tableau_exports.py')
    (root/'docs/data_licenses').mkdir(parents=True)
    shutil.copy(ROOT/'docs/data_licenses/Apache-2.0.txt',root/'docs/data_licenses/Apache-2.0.txt')
    return root


def test_export_idempotence_sql_csv_checks_and_readonly(export_project):
    root=export_project
    database=root/'data/processed/phase3/job_market.sqlite3';before=digest_file(database)
    first=export(root);second=export(root)
    assert first['content_sha256']==second['content_sha256'] and second['rerun_same_content']
    assert digest_file(database)==before
    assert all(second['validation'].values())
    expected=pd.read_csv(root/'reports/phase5_reconciliation.csv',keep_default_na=False)
    assert len(expected)>0 and set(expected.csv_status)=={'matched'}
    assert expected.tableau_numerator.eq('').all()
    assert expected.tableau_status.eq('NOT_RUN_COMPUTER_USE_PERMISSION').all()


def test_manual_native_results_are_not_overwritten(export_project):
    root=export_project;export(root)
    path=root/'reports/phase5_reconciliation.csv'
    frame=pd.read_csv(path,keep_default_na=False);frame.loc[0,'tableau_numerator']='TEST_ONLY_manual_actual'
    frame.to_csv(path,index=False)
    before=path.read_bytes()
    with pytest.raises(ValueError,match='Archive completed'):export(root)
    assert path.read_bytes()==before


def test_workbook_draft_structure_filters_package_and_native_status(export_project):
    root=export_project;export(root);result=create(root)
    tree=E.parse(root/'dashboard/bay_area_2023_DRAFT.twb')
    assert len(tree.findall('./worksheets/worksheet'))==10
    assert len(tree.findall('./dashboards/dashboard'))==2
    assert not tree.findall('.//relation[@type="join"]')
    assert tree.find('.//connection').get('class')=='textscan'
    for sheet in tree.findall('./worksheets/worksheet'):
        assert sheet.find('.//filter[@column="[bay_metrics].[none:Selected slice:nk]"]') is not None
    formulas=[e.get('formula') for e in tree.findall('.//calculation')]
    assert 'IF MIN([comparison_allowed])=1 AND MAX([denominator])>0 THEN SUM([numerator])/MAX([denominator]) END' in formulas
    assert not any('SUM([rate])' in f for f in formulas)
    assert result['native_open_render_filter_validation'] is False
    repeated=create(root)
    assert repeated['workbook_sha256']==result['workbook_sha256']
    assert repeated['package_sha256']==result['package_sha256']
    with zipfile.ZipFile(root/'dashboard/bay_area_2023_DRAFT.twbx') as z:
        assert set(z.namelist())==set(result['package_contents'])
        assert hashlib.sha256(z.read('Data/dashboard_metrics.csv')).hexdigest()==digest_file(root/'data/processed/phase5/dashboard_metrics.csv')
        assert b'TEST_ONLY' in z.read('Data/dashboard_metrics.csv') or b'All Bay Area' in z.read('Data/dashboard_metrics.csv')
        assert E.fromstring(z.read('bay_area_2023_DRAFT.twb')).find('.//connection').get('directory')=='Data'


def test_workbook_rejects_tampered_csv(export_project):
    root=export_project;export(root)
    path=root/'data/processed/phase5/dashboard_metrics.csv';path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='Export changed'):create(root)
