"""TEST_ONLY structural fixtures; no invented market observations or real-data assertions."""
from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest

from src.luke_dataset import (
    EXPECTED_COLUMNS, acquire, digest_file, match_city, parse_skill_tags,
    profile, profile_frame, validate_approval, verify_manifest, verify_raw,
)

ROOT=Path(__file__).resolve().parents[1]
CITIES={'San Francisco':'San Francisco','South San Francisco':'San Mateo','San Jose':'Santa Clara'}


def test_actual_approved_release_configuration():
    validate_approval(json.loads((ROOT/'config/phase2_plan.json').read_text()),json.loads((ROOT/'config/source_access.json').read_text()))


@pytest.mark.parametrize('value,status',[('', 'missing'),('None','missing'),('[]','empty'),("['TEST_ONLY']",'populated'),('not a list','malformed'),("{'x':1}",'malformed'),('[1]','malformed'),("['']",'malformed'),("__import__('os').system('false')",'malformed')])
def test_skill_lists_are_safe_and_explicit(value,status):
    assert parse_skill_tags(value)[0]==status


@pytest.mark.parametrize('location,country,expected',[
    ('San Francisco, CA','United States','San Francisco'),
    ('South San Francisco, CA','United States','South San Francisco'),
    ('San Jose, California, United States','United States','San Jose'),
    ('San Francisco, CA','Other country',None),
    ('San Francisco Bay Area','United States',None),
    ('Anywhere','United States',None),
    ('San Francisco, CA; San Jose, CA','United States',None),
    ('San Francisco, TX','United States',None),
    ('Not San Francisco, CA','United States',None),
    ('San Jose, CA (Remote)','United States',None),
])
def test_exact_work_locations_no_headquarters_or_substrings(location,country,expected):
    assert match_city(location,country,CITIES)==expected


def sentinel_row(**changes):
    row={name:'' for name in EXPECTED_COLUMNS}
    row.update(job_title='TEST_ONLY',job_title_short='TEST_ONLY_LABEL',job_country='United States',job_location='San Francisco, CA',job_posted_date='2023-01-01 00:00:00',job_skills="['TEST_ONLY_TAG']")
    row.update(changes)
    return row


def test_raw_profile_preserves_strings_and_does_not_calculate_salary_kpis():
    frame=pd.DataFrame([sentinel_row(salary_year_avg='0'),sentinel_row(salary_year_avg='bad',job_posted_date='bad')])
    before=frame.copy(deep=True)
    result=profile_frame(frame,CITIES)
    pd.testing.assert_frame_equal(frame,before)
    assert result['rows']==2 and result['bay_rows']==2
    assert result['date_invalid_nonblank']==1
    assert result['bay_salary_fields']['salary_year_avg']['nonpositive']==1
    assert result['bay_salary_fields']['salary_year_avg']['invalid_numeric']==1
    assert 'median' not in result['bay_salary_fields']['salary_year_avg']


def test_missing_skill_list_is_not_empty_skill_list():
    frame=pd.DataFrame([sentinel_row(job_skills=''),sentinel_row(job_skills='[]')])
    assert profile_frame(frame,CITIES)['bay_skill_list_status']=={'missing':1,'empty':1}


@pytest.mark.parametrize('change',[
    {'source':'other'},{'revision':'main'},{'review_status':'pending'},
    {'license':'unknown'},{'license_evidence':'https://example.invalid'},
    {'permissions':{'download':'true','local_storage':True,'local_analysis':True}},
])
def test_incomplete_or_wrong_approval_cannot_download(change):
    plan=json.loads((ROOT/'config/phase2_plan.json').read_text())
    access=json.loads((ROOT/'config/source_access.json').read_text())
    access.update(change)
    with pytest.raises(PermissionError): validate_approval(plan,access)


def test_pin_checksum_and_byte_size_required(tmp_path):
    raw=tmp_path/'TEST_ONLY.csv';raw.write_text('TEST_ONLY')
    plan={'expected_bytes':raw.stat().st_size,'expected_sha256':digest_file(raw)}
    verify_raw(raw,plan)
    raw.write_text('TEST_ONLY_CHANGED')
    with pytest.raises(ValueError): verify_raw(raw,plan)


@pytest.fixture
def synthetic_snapshot(tmp_path):
    plan=json.loads((ROOT/'config/phase2_plan.json').read_text())
    access=json.loads((ROOT/'config/source_access.json').read_text())
    plan.update(raw_directory='raw',profile_json='report.json',geographic_reference='cities.json',chunk_rows=1)
    raw=tmp_path/'raw/data_jobs.csv';raw.parent.mkdir()
    rows=[sentinel_row(),sentinel_row(),sentinel_row(job_location='Elsewhere, ZZ')]
    pd.DataFrame(rows).to_csv(raw,index=False)
    plan.update(expected_bytes=raw.stat().st_size,expected_sha256=digest_file(raw))
    manifest={'source':plan['source'],'revision':plan['revision'],'status':'complete','sha256':plan['expected_sha256'],'source_file':raw.name,'bytes':plan['expected_bytes']}
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    (tmp_path/'cities.json').write_text(json.dumps({'cities':CITIES,'counties':['San Francisco','San Mateo','Santa Clara']}))
    return plan,access,raw,manifest


def test_profile_reconciles_duplicates_across_chunks_and_keeps_raw(synthetic_snapshot,tmp_path):
    plan,access,raw,_=synthetic_snapshot
    before=raw.read_bytes()
    one=profile(plan,access,tmp_path)
    plan['chunk_rows']=100
    many=profile(plan,access,tmp_path)
    assert raw.read_bytes()==before
    assert one['raw_row_count']==3 and one['preliminary_bay_area']['row_count']==2
    assert one['exact_duplicate_row_candidates']==many['exact_duplicate_row_candidates']==1
    assert one['preliminary_bay_area']['exact_duplicate_row_candidates']==1
    assert one['preliminary_bay_area']['employer_title_location_date_duplicate_candidates']==1
    assert one['preliminary_bay_area']['salary_fields']==many['preliminary_bay_area']['salary_fields']


def test_corrupted_manifest_rejected(synthetic_snapshot,tmp_path):
    plan,access,raw,manifest=synthetic_snapshot
    manifest['revision']='bad'
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError): profile(plan,access,tmp_path)


def test_missing_columns_are_not_silently_filled(synthetic_snapshot,tmp_path):
    plan,access,raw,manifest=synthetic_snapshot
    pd.DataFrame([{'TEST_ONLY_COLUMN':''}]).to_csv(raw,index=False)
    plan.update(expected_bytes=raw.stat().st_size,expected_sha256=digest_file(raw))
    manifest.update(bytes=plan['expected_bytes'],sha256=plan['expected_sha256'])
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='schema'): profile(plan,access,tmp_path)


def test_permission_gate_runs_before_file_access(tmp_path):
    plan=json.loads((ROOT/'config/phase2_plan.json').read_text())
    access=json.loads((ROOT/'config/source_access.json').read_text())
    access['permissions']['local_storage']=False
    with pytest.raises(PermissionError): profile(plan,access,tmp_path)


def test_existing_verified_snapshot_is_reused_without_network(synthetic_snapshot,tmp_path,monkeypatch):
    import requests
    plan,access,raw,_=synthetic_snapshot
    def no_network(*args,**kwargs): raise AssertionError('No network should be used for verified existing data.')
    monkeypatch.setattr(requests,'Session',no_network)
    assert acquire(plan,access,tmp_path)['sha256']==digest_file(raw)


def test_city_reference_contains_nine_counties_and_all_required_cities():
    ref=json.loads((ROOT/'config/bay_area_cities.json').read_text())
    assert len(ref['cities'])==101
    assert len(ref['counties'])==9
    assert set(ref['cities'].values())==set(ref['counties'])
    for city in ['San Francisco','San Jose','Oakland','Palo Alto','Mountain View','Sunnyvale','Santa Clara','Cupertino','Redwood City','Menlo Park','Fremont','Berkeley']:
        assert city in ref['cities']


def test_record_count_corruption_cannot_be_silently_replaced(synthetic_snapshot,tmp_path):
    plan,access,raw,manifest=synthetic_snapshot
    manifest['row_count']=999
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='row count'):
        profile(plan,access,tmp_path)
