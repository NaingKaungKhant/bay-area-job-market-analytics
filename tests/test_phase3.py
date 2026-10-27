"""TEST_ONLY fixtures verify rules and database safety, never market findings."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from src.build_database import build, validate_database
from src.cleaning import (clean_text, classify_role, classify_seniority,
                          employment_types, parse_date, parse_salary, parse_skills,
                          resolve_locations)
from src.luke_dataset import EXPECTED_COLUMNS, read_json

ROOT = Path(__file__).resolve().parents[1]
RULES = read_json(ROOT/'config/phase3_rules.json')
REFERENCE = read_json(ROOT/'config/bay_area_cities.json')


@pytest.mark.parametrize('title,publisher,role,status', [
    ('Senior Data Analyst', 'Senior Data Analyst', 'Data Analyst', 'accepted_title_only'),
    ('ML Engineer', 'Machine Learning Engineer', 'Machine Learning Engineer', 'accepted_title_only'),
    ('Data-Engineer', 'Data Engineer', 'Data Engineer', 'accepted_title_only'),
    ('Data Scientist / Data Engineer', 'Data Scientist', None, 'ambiguous'),
    ('Data Analyst', 'Data Scientist', None, 'ambiguous'),
    ('Analytics Engineer', 'Data Engineer', None, 'unclassified'),
    ('BI Analyst', 'Data Analyst', None, 'unclassified'),
    ('Analyst', 'Business Analyst', None, 'unclassified'),
    ('Data Analyst / Software Engineer', 'Data Analyst', None, 'ambiguous'),
    ('100% Remote Data Engineer | Software Developer background needed', 'Data Engineer', 'Data Engineer', 'accepted_title_only'),
    ('Software Engineer with Python', 'Software Engineer', None, 'out_of_scope'),
    ('Business Analyst', 'Business Analyst', None, 'out_of_scope'),
    ('Metadata Analyst', 'Data Analyst', None, 'unclassified'),
])
def test_role_evidence(title, publisher, role, status):
    assert classify_role(title, publisher, RULES)[:2] == (role, status)


@pytest.mark.parametrize('title,expected', [
    ('Data Analyst', 'unknown'), ('Senior Data Analyst', 'senior'),
    ('Sr. Data Engineer', 'senior'), ('Junior Data Scientist', 'entry/junior'),
    ('Data Analyst Intern', 'entry/junior'), ('Intermediate Data Analyst', 'mid'),
    ('Principal Data Scientist', 'lead/staff/principal'),
    ('Senior Staff Data Engineer', 'lead/staff/principal'), ('Senior Manager, Data Analyst', 'management'),
    ('Junior Senior Data Analyst', 'mixed/conflicting'),
])
def test_seniority_requires_evidence(title, expected):
    assert classify_seniority(title) == expected


@pytest.mark.parametrize('location,country,status,count', [
    ('San Francisco, CA', 'United States', 'eligible_geography', 1),
    ('  san jose, California ', 'United States', 'eligible_geography', 1),
    ('Stanford, CA', 'United States', 'eligible_geography', 1),
    ('Castro Valley, CA', 'United States', 'eligible_geography', 1),
    ('St Helena, CA', 'United States', 'eligible_geography', 1),
    ('Alameda County, CA', 'United States', 'eligible_geography', 1),
    ('San Jose, CA; Austin, TX', 'United States', 'eligible_geography', 2),
    ('San Jose, CA | San Jose, CA', 'United States', 'eligible_geography', 1),
    ('Austin, TX', 'United States', 'outside_bay_area', 1),
    ('San Francisco, CA', 'Canada', 'country_missing_or_outside_us', 0),
    ('Anywhere', 'United States', 'unresolved_geography', 0),
    ('California, MO', 'United States', 'outside_bay_area', 1),
    ('California', 'United States', 'unresolved_geography', 0),
    ('Princeton, CA', 'United States', 'unresolved_geography', 0),
    ('El Sobrante, CA', 'United States', 'unresolved_geography', 0),
    ('Emerald Hills, CA', 'United States', 'unresolved_geography', 0),
    ('San Jose, CA; Unknown', 'United States', 'unresolved_geography', 0),
    ('Los Angeles, CA', 'United States', 'unresolved_geography', 0),
])
def test_geography(location, country, status, count):
    places, reason = resolve_locations(location, country, REFERENCE, RULES)
    assert reason == status
    assert len(places) == count
    if location == 'Alameda County, CA':
        assert places[0][0] is None


@pytest.mark.parametrize('value,expected,issue', [
    ('', None, None), ('None', None, None), ('123456.78', 12345678, None),
    ('15.555', 1556, 'salary_rounded_to_hundredths'),
    ('15.545', 1554, 'salary_rounded_to_hundredths'),
    ('0', None, 'invalid_salary'), ('-1', None, 'invalid_salary'),
    ('inf', None, 'invalid_salary'), ('oops', None, 'invalid_salary'),
    ('1e50', None, 'invalid_salary'), ('1e17', None, 'salary_outside_storage_range'),
])
def test_salary(value, expected, issue):
    assert parse_salary(value) == (expected, issue)


@pytest.mark.parametrize('value,status', [('', 'missing'), ('None', 'missing'),
    ('[]', 'empty'), ("['python']", 'populated'), ('not a list', 'malformed'),
    ("{'python': 1}", 'malformed'), ('[1]', 'malformed'), ("['']", 'malformed'),
    ("__import__('os').system('echo TEST_ONLY')", 'malformed')])
def test_safe_skill_parser(value, status):
    assert parse_skills(value, RULES)[0] == status


def test_skills_aliases_without_punctuation_loss():
    status, skills, corrections = parse_skills("['Python', 'python3', 'C++', 'C#', 'powerbi']", RULES)
    assert status == 'populated'
    assert set(skills) == {'python', 'c++', 'c#', 'power bi'}
    assert skills['python'] == ['Python', 'python3']
    assert corrections == 5


def test_dates_and_text_and_employment():
    assert parse_date('2023-04-05 12:30:00', 2023) == ('2023-04-05T12:30:00', None)
    assert parse_date('2024-01-01', 2023)[1] == 'outside_historical_year'
    assert parse_date('bad', 2023)[1] == 'invalid_or_missing_date'
    assert clean_text('  Ｐython\n code  ') == 'Python code'
    assert employment_types('Full-time and Contractor') == ['full-time', 'contractor']
    assert employment_types('') == []


def source_row(**overrides):
    row = dict.fromkeys(EXPECTED_COLUMNS, '')
    row.update(job_title='TEST_ONLY Data Analyst', job_title_short='Data Analyst',
               company_name='TEST_ONLY Company', job_country='United States',
               job_location='San Francisco, CA', job_posted_date='2023-04-05 12:30:00',
               job_work_from_home='False', job_skills="['Python', 'python', 'C++']")
    row.update(overrides)
    return row


@pytest.fixture
def project(tmp_path):
    for folder in ['config', 'sql', 'src', 'data/raw/luke_2023']:
        (tmp_path/folder).mkdir(parents=True)
    for name in ['phase2_plan.json', 'source_access.json', 'phase3_rules.json', 'bay_area_cities.json']:
        shutil.copy(ROOT/'config'/name, tmp_path/'config'/name)
    for name in ['001_schema.sql', '002_validate.sql']:
        shutil.copy(ROOT/'sql'/name, tmp_path/'sql'/name)
    for name in ['cleaning.py', 'build_database.py']:
        shutil.copy(ROOT/'src'/name, tmp_path/'src'/name)
    return tmp_path


def write_fixture(root, rows):
    raw = root/'data/raw/luke_2023/data_jobs.csv'
    with raw.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    plan = read_json(root/'config/phase2_plan.json')
    plan['expected_bytes'] = raw.stat().st_size
    plan['expected_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
    (root/'config/phase2_plan.json').write_text(json.dumps(plan))
    manifest = dict(source=plan['source'], revision=plan['revision'], status='complete',
                    sha256=plan['expected_sha256'], source_file='data_jobs.csv',
                    bytes=plan['expected_bytes'], row_count=len(rows), completed_at_utc='2026-10-26T00:00:00+00:00')
    (raw.parent/'manifest.json').write_text(json.dumps(manifest))
    return raw


def test_end_to_end_audit_bridges_and_rerun(project):
    rows = [source_row(), source_row(), source_row(salary_year_avg='120000'),
            source_row(job_location='San Jose, CA; Austin, TX'),
            source_row(job_title='TEST_ONLY Data Scientist / Data Engineer'),
            source_row(job_title='TEST_ONLY Business Analyst', job_title_short='Business Analyst'),
            source_row(job_location='Anywhere'), source_row(job_country='Canada'),
            source_row(job_posted_date='bad'), source_row(job_title=''),
            source_row(job_skills='broken', salary_year_avg='-4'),
            source_row(job_title='TEST_ONLY Data Analyst talent pool')]
    raw = write_fixture(project, rows)
    before = raw.read_bytes()
    result = build(project)
    assert result['input_rows'] == 12
    assert result['retained_records'] == 6
    assert sum(result['decisions'].values()) == 12
    assert result['decisions']['exact_duplicate'] == 1
    assert result['similar_key_candidates_preserved'] == 2
    assert result['table_counts']['bridge_job_locations'] == 7
    assert result['table_counts']['bridge_job_skills'] == 10
    assert result['role_status_counts'] == {'accepted_title_only': 4, 'ambiguous': 1, 'out_of_scope': 1}
    assert result['field_issues']['salary_year_avg:invalid_salary'] == 1
    assert not any(result['validation_violations'].values())
    assert raw.read_bytes() == before
    second = build(project)
    assert second['rerun_same_content'] is True
    connection = sqlite3.connect(project/'data/processed/phase3/job_market.sqlite3')
    assert connection.execute('SELECT COUNT(*) FROM v_target_job_records').fetchone()[0] == 4
    assert connection.execute('SELECT COUNT(*) FROM fact_job_postings WHERE salary_currency IS NOT NULL OR work_arrangement != \'unknown\'').fetchone()[0] == 0
    assert connection.execute('SELECT salary_year_x100 FROM fact_job_postings WHERE job_posting_id=3').fetchone()[0] == 12000000
    connection.close()


def test_constraints_and_validation_detect_bad_relationships(project):
    write_fixture(project, [source_row()])
    build(project)
    connection = sqlite3.connect(project/'data/processed/phase3/job_market.sqlite3')
    connection.execute('PRAGMA foreign_keys = ON')
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO bridge_job_skills VALUES (999,1,'[]','publisher_tags','unknown')")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute('INSERT INTO bridge_job_skills SELECT * FROM bridge_job_skills')
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE fact_job_postings SET salary_currency='USD'")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE fact_job_postings SET role=NULL")
    connection.execute('DELETE FROM bridge_job_locations')
    with pytest.raises(ValueError, match='validation failed'):
        validate_database(connection, project, 1)
    connection.close()


def test_failed_build_preserves_previous_output(project):
    write_fixture(project, [source_row()])
    build(project)
    database = project/'data/processed/phase3/job_market.sqlite3'
    checksum = hashlib.sha256(database.read_bytes()).hexdigest()
    (project/'sql/002_validate.sql').write_text("SELECT 'TEST_ONLY_forced_failure', 1;")
    with pytest.raises(ValueError, match='validation failed'):
        build(project)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == checksum
    assert not list(database.parent.parent.glob('.phase3-build-*'))


def test_changed_raw_and_permission_cannot_bypass_approval(project):
    raw = write_fixture(project, [source_row()])
    raw.write_text(raw.read_text()+'\n')
    with pytest.raises(ValueError, match='SHA-256'):
        build(project)
    write_fixture(project, [source_row()])
    access_path = project/'config/source_access.json'
    access = read_json(access_path)
    access['permissions']['local_analysis'] = False
    access_path.write_text(json.dumps(access))
    with pytest.raises(PermissionError):
        build(project)


def test_manifest_count_and_schema_drift_fail(project):
    write_fixture(project, [source_row()])
    manifest_path = project/'data/raw/luke_2023/manifest.json'
    manifest = read_json(manifest_path)
    manifest['row_count'] = 2
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='reconcile'):
        build(project)


def test_unmanaged_outputs_not_overwritten(project):
    write_fixture(project, [source_row()])
    output = project/'data/processed/phase3'
    output.mkdir(parents=True)
    (output/'personal_file.txt').write_text('TEST_ONLY private work')
    with pytest.raises(ValueError, match='unmanaged'):
        build(project)
    assert (output/'personal_file.txt').read_text() == 'TEST_ONLY private work'


def test_schema_drift_with_otherwise_valid_checksum(project):
    raw = write_fixture(project, [source_row()])
    raw.write_text(raw.read_text().replace('job_title_short,', 'TEST_ONLY_changed_column,', 1))
    plan_path = project/'config/phase2_plan.json'
    plan = read_json(plan_path)
    plan['expected_bytes'] = raw.stat().st_size
    plan['expected_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
    plan_path.write_text(json.dumps(plan))
    manifest_path = raw.parent/'manifest.json'
    manifest = read_json(manifest_path)
    manifest.update(bytes=plan['expected_bytes'], sha256=plan['expected_sha256'])
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='schema drift'):
        build(project)


def test_missing_fields_do_not_delete_eligible_record(project):
    write_fixture(project, [source_row(company_name='', job_skills='', salary_year_avg='', salary_hour_avg='', job_schedule_type='')])
    result = build(project)
    assert result['retained_records'] == 1
    c = sqlite3.connect(project/'data/processed/phase3/job_market.sqlite3')
    assert c.execute('SELECT company_id, salary_year_x100, salary_hour_x100, employment_types_json FROM fact_job_postings').fetchone() == (None, None, None, '[]')
    c.close()


def test_review_override_is_narrow_and_traceable():
    title = RULES['reviewed_role_overrides'][0]['title']
    role, status, evidence = classify_role(title, 'Data Engineer', RULES)
    assert role == 'Data Engineer' and evidence['method'] == 'reviewed_title_exception'
    assert evidence['review_decision']
    assert classify_role(title, 'Software Engineer', RULES)[1] == 'ambiguous'


def test_bridge_cross_product_requires_distinct_record_count(project):
    write_fixture(project, [source_row(job_location='San Jose, CA; Oakland, CA')])
    result = build(project)
    assert result['table_counts']['bridge_job_locations'] == 2
    c = sqlite3.connect(project/'data/processed/phase3/job_market.sqlite3')
    total, distinct = c.execute('SELECT COUNT(*),COUNT(DISTINCT f.job_posting_id) FROM fact_job_postings f JOIN bridge_job_skills s USING(job_posting_id) JOIN bridge_job_locations l USING(job_posting_id)').fetchone()
    assert (total, distinct) == (4, 1)
    c.close()


def test_report_checks_staleness_and_keeps_detail_local(project):
    from src.phase3_report import write_report
    write_fixture(project, [source_row()])
    (project/'reports').mkdir()
    build(project)
    result = write_report(project)
    assert result['input_rows'] == 1
    report = (project/'reports/phase3_cleaning_report.md').read_text()
    assert 'TEST_ONLY Company' not in report
    assert 'Classification review has not been recorded' in report
    rules_path = project/'config/phase3_rules.json'
    rules_path.write_text(rules_path.read_text()+'\n')
    with pytest.raises(ValueError, match='Code/config changed'):
        write_report(project)


def test_report_rejects_changed_database(project):
    from src.phase3_report import write_report
    write_fixture(project, [source_row()])
    (project/'reports').mkdir()
    build(project)
    c=sqlite3.connect(project/'data/processed/phase3/job_market.sqlite3')
    c.execute("UPDATE fact_job_postings SET normalized_title='TEST_ONLY_changed'")
    c.commit()
    c.close()
    with pytest.raises(ValueError, match='content no longer matches'):
        write_report(project)


def test_unrecognized_file_inside_managed_output_is_protected(project):
    write_fixture(project, [source_row()])
    build(project)
    personal = project/'data/processed/phase3/personal_notes.txt'
    personal.write_text('TEST_ONLY keep me')
    with pytest.raises(ValueError, match='unrecognized'):
        build(project)
    assert personal.read_text() == 'TEST_ONLY keep me'


def test_review_is_bound_to_source_and_rules_not_download_timestamp(project):
    from src.phase3_report import write_report
    write_fixture(project, [source_row()])
    (project/'reports').mkdir()
    s=build(project)
    # This fixture is TEST_ONLY metadata, never actual research/review evidence.
    review=dict(rule_config_sha256=s['config_sha256']['config/phase3_rules.json'],
                raw_sha256=s['raw_sha256'],cleaning_code_sha256=s['config_sha256']['src/cleaning.py'],
                semantic_sha256='TEST_ONLY_other_acquisition_timestamp',
                accepted_sample_data_rows=[],ambiguous_distinct_title_publisher_pairs=0,ambiguous_records=0)
    path=project/'reports/phase3_classification_review.json'
    path.write_text(json.dumps(review))
    assert write_report(project)['classification_review']==review
    review['raw_sha256']='TEST_ONLY_wrong_release'
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError,match='review is stale'):
        write_report(project)
