"""Write brief aggregate quality reports from a validated local Phase 3 run.

This is a cleaning audit, not business analysis. Detail rows remain local/ignored.
Run explicitly after a build so tracked reports describe the current database.
"""
from pathlib import Path
import json
import sqlite3

from src.build_database import semantic_digest, validate_database
from src.luke_dataset import digest_file, read_json


def write_report(root=Path('.')):
    root = Path(root).resolve()
    local = root/'data/processed/phase3'
    summary = read_json(local/'build_summary.json')
    for name, expected in summary['config_sha256'].items():
        if digest_file(root/name) != expected:
            raise ValueError('Code/config changed since the database build. Rebuild before reporting.')
    raw = root/'data/raw/luke_2023/data_jobs.csv'
    if digest_file(raw) != summary['raw_sha256']:
        raise ValueError('Raw data changed since the validated build.')
    connection = sqlite3.connect(f'file:{local / "job_market.sqlite3"}?mode=ro', uri=True)
    try:
        validate_database(connection, root, summary['retained_records'])
        if semantic_digest(connection) != summary['semantic_sha256']:
            raise ValueError('Database content no longer matches the build.')
    finally:
        connection.close()
    review_path = root/'reports/phase3_classification_review.json'
    review = read_json(review_path) if review_path.exists() else None
    # Bind title review to source bytes and classification code/rules. Another
    # permitted download has a different acquisition timestamp but the same titles.
    if review and (review['rule_config_sha256'] != summary['config_sha256']['config/phase3_rules.json']
                   or review['raw_sha256'] != summary['raw_sha256']
                   or review['cleaning_code_sha256'] != summary['config_sha256']['src/cleaning.py']):
        raise ValueError('Classification review is stale for this run.')
    report = dict(summary)
    report['classification_review'] = review
    (root/'reports/phase3_cleaning_report.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    counts = summary['decisions']
    status = summary['role_status_counts']
    missing = summary['missing_counts_retained']
    lines = [
        '# Phase 3 data quality and cleaning report', '',
        'Completed local cleaning/database validation for the pinned historical 2023 Luke CSV. '
        'Counts describe processing, not actual hires or certified unique postings. Phase 4 has not started.', '',
        '## Input and output reconciliation', '',
        '| Mutually exclusive row outcome | Rows |', '|---|---:|',
    ]
    labels = {
        'exact_duplicate': 'Exact duplicate records removed (entire file)',
        'country_missing_or_outside_us': 'Country missing or outside US',
        'outside_bay_area': 'Confirmed non-CA work locations',
        'unresolved_geography': 'Unresolved geography (includes unmatched California places)',
        'invalid_or_missing_date': 'Invalid/missing date', 'outside_historical_year': 'Outside 2023',
        'missing_title': 'Missing title', 'talent_pool_or_training': 'Training/talent-pool advertisement',
        'retained_bay_record': 'Retained Bay records in SQLite',
    }
    for key, label in labels.items():
        lines.append(f'| {label} | {counts.get(key, 0):,} |')
    lines += [f'| **Total input / reconciled outcomes** | **{summary["input_rows"]:,}** |', '',
        f'Fact output: **{summary["retained_records"]:,}**. Accepted title-only target cohort: '
        f'**{status.get("accepted_title_only",0):,}**; ambiguous: **{status.get("ambiguous",0):,}**; '
        f'unclassified: **{status.get("unclassified",0):,}**; explicit non-target: **{status.get("out_of_scope",0):,}**. '
        'The latter three remain in the fact/audit cohort, outside `v_target_job_records`.', '',
        '## Corrections and detected issues', '',
        f'- {summary["similar_key_candidates_preserved"]} similar employer/title/location/date candidates preserved; '
        f'only all-field exact duplicates removed; {summary["bay_exact_duplicates_removed"]} retained-Bay duplicates removed. '
        'Global duplicate counts are not Bay duplicate-job counts.',
        f'- Added {sum(summary["added_community_record_memberships"].values()):,} community memberships using referenced county mappings; '
        'also normalized St Helena spelling. One explicit bootcamp advertisement excluded. '
        'This explains differences from the unchanged Phase 2 preliminary city-only profile.',
    ]
    for key, count in sorted(summary['corrections'].items()):
        lines.append(f'- `{key}`: {count:,}.')
    lines += [
        '- Invalid/nonpositive/overflow salary and malformed skill values: '
        f'{sum(v for k,v in summary["field_issues"].items() if "rounded" not in k):,} detected among retained records. '
        'Salary rounding events are storage corrections, not source-error claims. '
        'Original values are preserved; missing values are never imputed.',
        f'- Missing annual values: {missing.get("salary_year_avg",0):,}; valid annual values: {summary["valid_annual_values"]:,}. '
        f'Missing hourly values: {missing.get("salary_hour_avg",0):,}; valid hourly values: {summary["valid_hourly_values"]:,}. '
        'Unknown currency/provenance remains unresolved; no advertised-pay metric is enabled.',
        f'- Inherited skill lists: {json.dumps(summary["skill_status_counts"],sort_keys=True)}. '
        f'Missing schedules: {missing.get("job_schedule_type",0):,}. '
        'Missing employer/title/date among retained records: '
        f'{missing.get("company_name",0):,}/{missing.get("job_title",0):,}/{missing.get("job_posted_date",0):,}.',
        '- Work arrangements remain unknown. No descriptions, requirements, experience years, '
        'salary bounds, native posting IDs or timezone evidence have been invented.', '',
        '## Validation and review', '',
        f'- All {len(summary["validation_violations"])} reconciliation/integrity checks have zero violations; '
        'PK/FK/unique constraints were enforced during loading. Raw SHA-256 remains unchanged.',
        f'- Repeat run, identical relational content: **{summary["rerun_same_content"]}**. '
        f'Semantic SHA-256: `{summary["semantic_sha256"]}`.',
    ]
    if review:
        lines += [f'- Assistant inspected {len(review["accepted_sample_data_rows"])} accepted records '
                  '(20 per role, spread through source-row order), plus all '
                  f'{review["ambiguous_distinct_title_publisher_pairs"]} ambiguous title/publisher pairs '
                  f'covering {review["ambiguous_records"]} records. '
                  'Title-only conflicts remain unresolved where duties are missing.',
                  '- Review corrected compatible Senior Staff seniority and one narrowly documented '
                  'prior-background/occupation conflict. Final accepted sample has no role disagreements. '
                  'This is assistant review, not independent human labeling or a measured classifier accuracy.']
    else:
        lines += ['- Classification review has not been recorded; acceptance remains incomplete.']
    lines += ['', '## Local evidence and remaining limitations', '',
        '- `data/processed/phase3/job_market.sqlite3`: validated local relational data.',
        '- `row_audit.csv`: every input row, reason, exact-duplicate keeper and retained record key.',
        '- `field_issue_audit.csv`: per-record salary rounding/error and malformed-tag decisions.',
        '- `unresolved_locations.json`: unresolved location labels/counts; reference is not exhaustive.',
        '- `build_summary.json`: counts, code/config hashes, source lineage and environment.',
        '- [Rules/schema guide](../docs/phase3_cleaning_rules.md), '
        '[classification review](phase3_classification_review.json), '
        '[test/verification record](phase3_verification.json).', '',
        'Raw/processed data and detail audits remain ignored by Git. Public release still needs '
        'the license/attribution/embedded-data review. Source selection, unknown geography/roles and '
        'missing/preprocessed fields limit later analysis. Salary medians/rankings, statistical '
        'comparisons, charts, Tableau exports and dashboards remain future work.', '',
    ]
    (root/'reports/phase3_cleaning_report.md').write_text('\n'.join(lines))
    return report


if __name__ == '__main__':
    result = write_report()
    print(json.dumps({'status': result['status'], 'retained_records': result['retained_records'],
                      'report': 'reports/phase3_cleaning_report.md'}))
