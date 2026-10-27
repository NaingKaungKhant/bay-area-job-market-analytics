"""Synthetic structural unit cases only: never collected postings or research results.

All payloads live in pytest temporary folders and contain TEST_ONLY sentinels.
Test permission attestations are intentionally fictional and are never source clearance.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.phase2 import COUNTIES, ROLES, assess_plan, plan_digest, profile_records, profile_snapshot

TODAY = date(2026, 10, 25)
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scoped_plan():
    return {
        "version": "phase2-pilot-v1", "source": "greenhouse",
        "geography_counties": list(COUNTIES), "target_roles": list(ROLES),
        "board_tokens": ["TEST_ONLY_BOARD"],
        "collection_mode": "single_snapshot_after_clearance",
        "pilot_max_requests": 1, "request_interval_seconds": 2,
    }


@pytest.fixture
def test_access():
    return {
        "source": "greenhouse", "review_status": "cleared",
        "reviewed_by": "TEST_ONLY_NOT_A_REAL_REVIEWER",
        "reviewed_on": "2020-01-01", "valid_until": "2099-01-01",
        "evidence_reference": "unit-test://not-real-permission",
        "retention_policy": "TEST_ONLY temporary fixture cleanup",
        "permitted_board_tokens": ["TEST_ONLY_BOARD"],
        "permissions": {"automated_collection": True, "local_storage": True, "local_analysis": True},
    }


@pytest.fixture
def structural_snapshot(tmp_path, scoped_plan):
    # Not a fake market sample: minimal sentinel payload for validation tests only.
    jobs = [{"id": "TEST_ONLY_ID", "title": None, "location": {"name": None}}]
    raw = tmp_path / 'TEST_ONLY.json'
    raw.write_text(json.dumps({"jobs": jobs, "meta": {"total": len(jobs)}}))
    manifest = {
        "source": "greenhouse", "board_token": "TEST_ONLY_BOARD",
        "snapshot_status": "complete", "plan_sha256": plan_digest(scoped_plan),
        "raw_file": raw.name,
        "request_url": "https://boards-api.greenhouse.io/v1/boards/TEST_ONLY_BOARD/jobs?content=true",
        "retrieved_at_utc": "2025-01-01T00:00:00Z", "http_status": 200,
        "completed_requests": 1, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "row_count": len(jobs),
    }
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest))
    return raw, path, manifest


def test_repository_configuration_blocks_collection():
    plan = json.loads((ROOT/'config/greenhouse_plan.json').read_text())
    access = json.loads((ROOT/'config/greenhouse_access.json').read_text())
    result = assess_plan(plan, access, today=TODAY)
    assert result['status'] == 'blocked'
    assert result['observed_record_count'] is None
    assert result['network_requests_made'] == 0
    assert 'source_permission_not_cleared' in result['blockers']


def test_scoped_attestation_is_ready_but_does_not_claim_collection(scoped_plan, test_access):
    result = assess_plan(scoped_plan, test_access, today=TODAY)
    assert not result['blockers']
    assert result['phase2_acceptance'] == 'not_met_no_verified_live_snapshot'
    assert result['observed_record_count'] is None


@pytest.mark.parametrize('field', ['automated_collection', 'local_storage', 'local_analysis'])
def test_every_permission_is_required(scoped_plan, test_access, field):
    test_access['permissions'][field] = False
    assert f'permission_missing_{field}' in assess_plan(scoped_plan, test_access, today=TODAY)['blockers']


@pytest.mark.parametrize('bad', ['true', 1, None, False])
def test_truthy_values_are_not_permission(scoped_plan, test_access, bad):
    test_access['permissions']['local_storage'] = bad
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


@pytest.mark.parametrize('bad', [None, [], 'cleared'])
def test_malformed_permission_object_fails_closed(scoped_plan, test_access, bad):
    test_access['permissions'] = bad
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


@pytest.mark.parametrize('field', ['reviewed_by', 'evidence_reference', 'retention_policy'])
def test_flags_without_evidence_are_insufficient(scoped_plan, test_access, field):
    test_access[field] = ''
    assert 'missing_'+field in assess_plan(scoped_plan, test_access, today=TODAY)['blockers']


@pytest.mark.parametrize('field,value', [('valid_until','2020-01-01'), ('reviewed_on','2099-01-01'), ('reviewed_on',None)])
def test_expired_future_and_missing_review_dates_block(scoped_plan, test_access, field, value):
    test_access[field] = value
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


@pytest.mark.parametrize('boards', [[], ['OTHER_TEST_BOARD'], [{'bad':'shape'}]])
def test_permission_is_bound_to_board_frame(scoped_plan, test_access, boards):
    test_access['permitted_board_tokens'] = boards
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


@pytest.mark.parametrize('boards', [[], ['TEST_ONLY_BOARD','TEST_ONLY_BOARD'], ['../bad'], [True]])
def test_invalid_or_duplicate_frame_blocks(scoped_plan, test_access, boards):
    scoped_plan['board_tokens'] = boards
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


@pytest.mark.parametrize('field,value', [('geography_counties',['OUTSIDE_TEST_SCOPE']), ('target_roles',[]), ('source','adzuna'), ('pilot_max_requests',True), ('pilot_max_requests',11), ('request_interval_seconds',0)])
def test_scope_and_project_caps(scoped_plan, test_access, field, value):
    scoped_plan[field] = value
    assert assess_plan(scoped_plan, test_access, today=TODAY)['status'] == 'blocked'


def test_permission_checked_before_reading_raw_path(tmp_path, scoped_plan, test_access):
    test_access['review_status'] = 'pending'
    with pytest.raises(PermissionError):
        profile_snapshot(tmp_path/'MISSING', tmp_path/'MISSING_MANIFEST', scoped_plan, test_access, today=TODAY)


def test_profile_preserves_raw_bytes_and_reports_missingness(structural_snapshot, scoped_plan, test_access):
    raw, path, _ = structural_snapshot
    before = raw.read_bytes()
    result = profile_snapshot(raw, path, scoped_plan, test_access, today=TODAY)
    assert raw.read_bytes() == before
    assert result['raw_record_count'] == 1
    assert result['fields']['title']['missing_count'] == 1
    assert result['publication_time_kpi_available'] is False
    assert result['provenance']['board_token'] == 'TEST_ONLY_BOARD'


@pytest.mark.parametrize('field,value', [
    ('source','other'), ('snapshot_status','partial'), ('snapshot_status','failed'),
    ('board_token','OTHER_TEST_BOARD'), ('plan_sha256','bad'), ('raw_file','wrong.json'),
    ('request_url','https://example.invalid/?api_key=TEST_ONLY'),
    ('retrieved_at_utc','2025-01-01T00:00:00'), ('retrieved_at_utc','2999-01-01T00:00:00Z'),
    ('retrieved_at_utc','2019-01-01T00:00:00Z'), ('http_status',429),
    ('completed_requests',0), ('sha256','bad'), ('row_count',0), ('row_count',True),
])
def test_manifest_failures_rejected(structural_snapshot, scoped_plan, test_access, field, value):
    raw, path, manifest = structural_snapshot
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        profile_snapshot(raw, path, scoped_plan, test_access, today=TODAY)


def test_changed_raw_bytes_rejected(structural_snapshot, scoped_plan, test_access):
    raw, path, _ = structural_snapshot
    raw.write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        profile_snapshot(raw, path, scoped_plan, test_access, today=TODAY)


@pytest.mark.parametrize('payload', [{}, {'jobs':{}}, {'jobs':[None],'meta':{'total':1}}, {'jobs':[],'meta':{'total':1}}])
def test_malformed_or_unreconciled_payloads_rejected(structural_snapshot, scoped_plan, test_access, payload):
    raw,path,manifest=structural_snapshot
    raw.write_text(json.dumps(payload))
    manifest['sha256']=hashlib.sha256(raw.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        profile_snapshot(raw,path,scoped_plan,test_access,today=TODAY)


def test_valid_empty_inventory_differs_from_blocked_collection(structural_snapshot, scoped_plan, test_access):
    raw,path,manifest=structural_snapshot
    raw.write_text(json.dumps({'jobs':[], 'meta':{'total':0}}))
    manifest.update(row_count=0, sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    path.write_text(json.dumps(manifest))
    result=profile_snapshot(raw,path,scoped_plan,test_access,today=TODAY)
    assert result['raw_record_count']==0
    assert result['fields']['title']['missing_percentage'] is None
    assert result['status']=='profiled_raw_inventory_only'


def test_duplicate_diagnostics_do_not_drop_rows():
    records=[{'id':'TEST_ONLY_A'}, {'id':'TEST_ONLY_A'}, {'id':'TEST_ONLY_A','title':'TEST_ONLY'}, {}]
    before=deepcopy(records)
    result=profile_records(records)
    assert records==before
    assert result['raw_record_count']==4
    assert result['repeated_source_id_rows']==2
    assert result['exact_repeated_payload_rows']==1
    assert result['missing_source_id_rows']==1


def test_zero_is_not_a_missing_identifier():
    assert profile_records([{'id':0}])['missing_source_id_rows']==0


def test_update_time_is_not_publication_time():
    result=profile_records([{'updated_at':'bad'}, {'updated_at':'2025-01-01T00:00:00'}, {'updated_at':'2025-01-01T00:00:00Z'}, {}])
    assert result['updated_at_invalid_or_timezone_missing']==2
    assert result['publication_time_kpi_available'] is False


def test_preflight_cli_is_offline_and_nonzero_when_blocked():
    result=subprocess.run([sys.executable,'-m','src.phase2','preflight'],cwd=ROOT,text=True,capture_output=True)
    assert result.returncode==2
    assert json.loads(result.stdout)['network_requests_made']==0


def test_legacy_phase2_does_not_collect_or_load_database():
    source=(ROOT/'src/phase2.py').read_text()
    assert 'import requests' not in source
    # Phase 3 is now authorized in a separate module. The blocked legacy
    # Greenhouse tool must still remain offline and must not load databases.
    assert 'import sqlite3' not in source
    assert 'sqlite3.connect' not in source


def test_frame_cannot_exceed_planned_request_budget(scoped_plan, test_access):
    scoped_plan['board_tokens'] = ['TEST_ONLY_BOARD', 'TEST_ONLY_BOARD_B']
    test_access['permitted_board_tokens'] = scoped_plan['board_tokens']
    assert 'board_frame_exceeds_project_request_cap' in assess_plan(scoped_plan,test_access,today=TODAY)['blockers']


def test_boolean_completed_request_is_invalid(structural_snapshot, scoped_plan, test_access):
    raw,path,manifest=structural_snapshot
    manifest['completed_requests']=True
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        profile_snapshot(raw,path,scoped_plan,test_access,today=TODAY)


def test_oversized_pilot_file_rejected(structural_snapshot, scoped_plan, test_access, monkeypatch):
    import src.phase2 as phase2
    monkeypatch.setattr(phase2, 'MAX_RAW_BYTES', 1)
    raw,path,_=structural_snapshot
    with pytest.raises(ValueError,match='size cap'):
        profile_snapshot(raw,path,scoped_plan,test_access,today=TODAY)
