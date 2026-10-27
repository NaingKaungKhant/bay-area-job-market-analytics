"""Offline Phase 3: verify, clean, load and validate the approved CSV.

Run from the project root: python -m src.build_database
No acquisition, business KPI analysis, chart or Tableau export occurs here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import tempfile

from src.cleaning import (clean_text, classify_role, classify_seniority,
                          employment_types, parse_date, parse_salary, parse_skills,
                          resolve_locations)
from src.luke_dataset import (EXPECTED_COLUMNS, read_json, validate_approval,
                              verify_manifest, verify_raw, digest_file)

PRODUCER = 'bay-area-phase3-v1'
TABLES = ('collection_snapshots', 'dim_companies', 'dim_locations', 'dim_skills',
          'fact_job_postings', 'bridge_job_skills', 'bridge_job_locations', 'source_posting_records')


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def insert_row(connection, table, values):
    """Only internal table/column names reach SQL; all data values are parameters."""
    names = ','.join(values)
    marks = ','.join('?' for _ in values)
    return connection.execute(f'INSERT INTO {table} ({names}) VALUES ({marks})', tuple(values.values())).lastrowid


def semantic_digest(connection):
    """Compare table content on reruns, excluding wall-clock run timestamps."""
    digest = hashlib.sha256()
    for table in TABLES:
        digest.update(table.encode())
        for row in connection.execute(f'SELECT * FROM {table} ORDER BY 1,2'):
            digest.update(json_text(row).encode())
    return digest.hexdigest()


def validate_database(connection, root, expected_count):
    """FK/PK constraints are active during loading; these checks reconcile the result."""
    checks = dict(connection.execute((root/'sql/002_validate.sql').read_text()))
    checks['foreign_key_violations'] = len(connection.execute('PRAGMA foreign_key_check').fetchall())
    checks['integrity_failures'] = int(connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)])
    checks['fact_count_difference'] = abs(connection.execute('SELECT COUNT(*) FROM fact_job_postings').fetchone()[0] - expected_count)
    checks['source_count_difference'] = abs(connection.execute('SELECT COUNT(*) FROM source_posting_records').fetchone()[0] - expected_count)
    if any(checks.values()):
        raise ValueError(f'Database validation failed: {checks}')
    return checks


def build(root=Path('.'), output=None):
    root = Path(root).resolve()
    output = Path(output).resolve() if output else root/'data/processed/phase3'
    plan = read_json(root/'config/phase2_plan.json')
    access = read_json(root/'config/source_access.json')
    rules = read_json(root/'config/phase3_rules.json')
    reference = read_json(root/plan['geographic_reference'])
    validate_approval(plan, access)
    if rules['historical_year'] != plan['historical_year']:
        raise ValueError('Cleaning rules and approved historical window disagree.')
    raw = root/plan['raw_directory']/plan['filename']
    manifest = read_json(raw.parent/'manifest.json')
    # Fail before writing output if raw bytes, provenance or release approval changed.
    verify_raw(raw, plan)
    verify_manifest(manifest, plan, raw)
    if type(manifest.get('row_count')) is not int:
        raise ValueError('A completed Phase 2 row-count manifest is required.')
    output.parent.mkdir(parents=True, exist_ok=True)
    previous_digest = None
    allowed_outputs = {'build_summary.json', 'job_market.sqlite3', 'row_audit.csv',
                       'field_issue_audit.csv', 'unresolved_locations.json'}
    if output.exists() and any(output.iterdir()):
        marker = output/'build_summary.json'
        if not marker.exists() or read_json(marker).get('producer') != PRODUCER:
            raise ValueError('Refusing to overwrite an unmanaged output directory.')
        if any(path.name not in allowed_outputs for path in output.iterdir()):
            raise ValueError('Refusing to remove unrecognized files from a managed output directory.')
        previous_digest = read_json(marker).get('semantic_sha256')
    stage = Path(tempfile.mkdtemp(prefix='.phase3-build-', dir=output.parent))
    connection = None
    try:
        connection = sqlite3.connect(stage/'job_market.sqlite3')
        connection.executescript((root/'sql/001_schema.sql').read_text())
        connection.execute('PRAGMA foreign_keys = ON')
        config_hashes = {str(path.relative_to(root)): digest_file(path) for path in
                         [root/'config/phase3_rules.json', root/plan['geographic_reference'],
                          root/'sql/001_schema.sql', root/'sql/002_validate.sql',
                          root/'src/cleaning.py', root/'src/build_database.py']}
        connection.executemany('INSERT INTO pipeline_metadata VALUES (?,?)',
                               [('producer', PRODUCER), ('rule_version', rules['version']),
                                ('config_sha256_json', json_text(config_hashes))])
        insert_row(connection, 'collection_snapshots', dict(snapshot_id=1, source_name=plan['source'],
                   source_revision=plan['revision'], raw_sha256=plan['expected_sha256'],
                   raw_row_count=manifest['row_count'], acquired_at_utc=manifest['completed_at_utc'],
                   rule_version=rules['version']))
        decisions, issues, corrections, roles, skills_status, missing = [Counter() for _ in range(6)]
        company_ids, location_ids, skill_ids, geo_cache, seen = {}, {}, {}, {}, {}
        geographic_additions, unresolved_locations = Counter(), Counter()
        near_keys, retained_hashes = Counter(), {}
        annual_n = hourly_n = retained = n = bay_exact_duplicates = 0
        # Audit every input row, including excluded rows, without copying restricted
        # raw data into the public report. The detailed CSVs stay local/ignored.
        with raw.open(newline='', encoding='utf-8') as stream, \
             (stage/'row_audit.csv').open('w', newline='', encoding='utf-8') as audit_stream, \
             (stage/'field_issue_audit.csv').open('w', newline='', encoding='utf-8') as issue_stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
                raise ValueError('CSV schema drift: expected the approved 17-column schema.')
            audit = csv.writer(audit_stream)
            audit.writerow(['source_data_row', 'raw_record_sha256', 'decision', 'kept_data_row', 'job_posting_id'])
            issue_audit = csv.writer(issue_stream)
            issue_audit.writerow(['source_data_row', 'field', 'issue', 'action'])

            def flag(row_number, field, issue, action):
                issues[f'{field}:{issue}'] += 1
                issue_audit.writerow([row_number, field, issue, action])

            for n, row in enumerate(reader, 1):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f'Malformed CSV column count at data row {n}.')
                payload = json_text(row)
                row_hash = hashlib.sha256(payload.encode()).digest()
                if row_hash in seen:
                    keeper, previous_payload = seen[row_hash]
                    if payload != previous_payload:
                        raise ValueError('Hash collision: stop instead of silently merging different records.')
                    decisions['exact_duplicate'] += 1
                    bay_exact_duplicates += int(row_hash in retained_hashes)
                    audit.writerow([n, row_hash.hex(), 'exact_duplicate', keeper, retained_hashes.get(row_hash, '')])
                    continue
                seen[row_hash] = (n, payload)
                geo_key = (row['job_location'], row['job_country'])
                if geo_key not in geo_cache:
                    geo_cache[geo_key] = resolve_locations(*geo_key, reference, rules)
                locations, decision = geo_cache[geo_key]
                if decision != 'eligible_geography':
                    decisions[decision] += 1
                    if decision == 'unresolved_geography':
                        unresolved_locations[geo_key] += 1
                    audit.writerow([n, row_hash.hex(), decision, '', ''])
                    continue
                date, date_issue = parse_date(row['job_posted_date'], rules['historical_year'])
                title = clean_text(row['job_title'])
                if date_issue or not title:
                    reason = date_issue or 'missing_title'
                    decisions[reason] += 1
                    flag(n, 'job_posted_date' if date_issue else 'job_title', reason, 'exclude_record')
                    audit.writerow([n, row_hash.hex(), reason, '', ''])
                    continue
                # Explicit talent pools/training advertisements are not job records.
                if re.search(r'\b(?:talent pool|talent community|training course|bootcamp)\b', title, re.I):
                    decisions['talent_pool_or_training'] += 1
                    audit.writerow([n, row_hash.hex(), 'talent_pool_or_training', '', ''])
                    continue
                retained += 1
                decisions['retained_bay_record'] += 1
                retained_hashes[row_hash] = n
                audit.writerow([n, row_hash.hex(), 'retained_bay_record', n, n])
                # Record-grain completeness is diagnostic: missing pay/tags do not
                # exclude an otherwise eligible job and never become zero values.
                for field, value in row.items():
                    cleaned = clean_text(value)
                    missing[field] += int(cleaned is None)
                    if cleaned is not None and cleaned != value:
                        corrections[f'{field}:unicode_or_whitespace'] += 1
                for alias in rules['location_aliases']:
                    if re.search(r'(?:^|[;|])\s*'+re.escape(alias)+r'\s*,', row['job_location'], re.I):
                        corrections['job_location:approved_alias'] += 1
                company = clean_text(row['company_name'])
                company_id = None
                if company:
                    key = company.casefold()
                    corrections['company_name:casefold_key'] += int(key != company)
                    if key not in company_ids:
                        company_ids[key] = insert_row(connection, 'dim_companies',
                            dict(display_name=company, normalized_name=key))
                    company_id = company_ids[key]
                corrections['job_title:casefold_key'] += int(title.casefold() != title)
                role, role_status, evidence = classify_role(title, row['job_title_short'], rules)
                roles[role_status] += 1
                skill_status, skills, tag_corrections = parse_skills(row['job_skills'], rules)
                skills_status[skill_status] += 1
                corrections['skill_tag_normalizations'] += tag_corrections
                if skill_status == 'malformed':
                    flag(n, 'job_skills', 'malformed_skill_list', 'retain_record_without_skills')
                skill_duplicates = sum(len(values)-1 for values in skills.values())
                corrections['repeated_canonical_skill_tags_collapsed'] += skill_duplicates
                salaries = []
                for field in ['salary_year_avg', 'salary_hour_avg']:
                    amount, issue = parse_salary(row[field])
                    salaries.append(amount)
                    if issue:
                        action = 'round_half_even' if 'rounded' in issue else 'set_null_preserve_raw'
                        flag(n, field, issue, action)
                        if 'rounded' in issue:
                            corrections[f'{field}:rounded'] += 1
                annual_n += salaries[0] is not None
                hourly_n += salaries[1] is not None
                insert_row(connection, 'fact_job_postings', dict(job_posting_id=n,
                    company_id=company_id, original_title=row['job_title'], normalized_title=title.casefold(),
                    publisher_role=clean_text(row['job_title_short']), role=role, role_status=role_status,
                    role_evidence_json=json_text(evidence), seniority=classify_seniority(title),
                    source_posted_at=date, employment_types_json=json_text(employment_types(row['job_schedule_type'])),
                    raw_schedule=row['job_schedule_type'], raw_work_from_home=row['job_work_from_home'],
                    skill_list_status=skill_status, salary_year_x100=salaries[0], salary_hour_x100=salaries[1],
                    raw_salary_year=row['salary_year_avg'], raw_salary_hour=row['salary_hour_avg'],
                    raw_salary_rate=row['salary_rate'], rule_version=rules['version']))
                for skill, original_tags in skills.items():
                    if skill not in skill_ids:
                        skill_ids[skill] = insert_row(connection, 'dim_skills',
                            dict(canonical_name=skill, taxonomy_version=rules['version']))
                    insert_row(connection, 'bridge_job_skills', dict(job_posting_id=n, skill_id=skill_ids[skill],
                               original_tags_json=json_text(original_tags)))
                for location in locations:
                    location_key = json_text(location)
                    if location_key not in location_ids:
                        location_ids[location_key] = insert_row(connection, 'dim_locations', dict(
                            location_key=location_key, locality=location[0], county=location[1], state=location[2],
                            country=location[3], location_precision=location[4], in_bay_area=location[5]))
                    insert_row(connection, 'bridge_job_locations', dict(job_posting_id=n,
                               location_id=location_ids[location_key], raw_location=row['job_location']))
                    if location[4] == 'community':
                        geographic_additions[location[0]] += 1
                insert_row(connection, 'source_posting_records', dict(snapshot_id=1, source_row_number=n,
                    job_posting_id=n, raw_record_sha256=row_hash.hex(), raw_record_json=payload))
                near_keys[(company.casefold() if company else '', title.casefold(),
                           row['job_location'], date)] += 1
        if n != manifest['row_count'] or sum(decisions.values()) != n:
            raise ValueError('Input rows do not reconcile with manifest/audit decisions.')
        # Cache data no longer needed can be released before SQLite integrity checks.
        seen.clear()
        checks = validate_database(connection, root, retained)
        table_counts = {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in TABLES}
        semantic = semantic_digest(connection)
        connection.commit()
        connection.close()
        connection = None
        unresolved = sorted(({'location': key[0], 'country': key[1], 'rows': count}
                             for key, count in unresolved_locations.items()), key=lambda x: (-x['rows'], x['location']))
        (stage/'unresolved_locations.json').write_text(json.dumps(unresolved, indent=2)+'\n')
        summary = dict(producer=PRODUCER, status='validated', run_at_utc=datetime.now(timezone.utc).isoformat(),
            source=plan['source'], revision=plan['revision'], raw_sha256=plan['expected_sha256'],
            rule_version=rules['version'], config_sha256=config_hashes, input_rows=n,
            decisions=dict(decisions), bay_exact_duplicates_removed=bay_exact_duplicates, retained_records=retained, role_status_counts=dict(roles),
            skill_status_counts=dict(skills_status), valid_annual_values=annual_n, valid_hourly_values=hourly_n,
            missing_counts_retained=dict(missing), field_issues=dict(issues), corrections=dict(corrections),
            added_community_record_memberships=dict(geographic_additions),
            similar_key_candidates_preserved=sum(count-1 for count in near_keys.values()),
            table_counts=table_counts, validation_violations=checks, semantic_sha256=semantic,
            previous_semantic_sha256=previous_digest,
            rerun_same_content=(semantic == previous_digest) if previous_digest else None,
            environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version),
            no_network_requests=True, raw_unchanged=(digest_file(raw) == plan['expected_sha256']))
        (stage/'build_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
        # Publish a complete validated directory, retaining the previous one until
        # the swap succeeds. A failed build leaves the previous database intact.
        backup = output.with_name(output.name+'.previous')
        if backup.exists():
            raise ValueError('Previous output backup exists; inspect it before rerunning.')
        if output.exists():
            output.rename(backup)
        try:
            stage.rename(output)
        except Exception:
            if backup.exists():
                backup.rename(output)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        return summary
    finally:
        if connection is not None:
            connection.close()
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Local generated directory; unmanaged directories are never overwritten.')
    args = parser.parse_args()
    summary = build(output=args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
