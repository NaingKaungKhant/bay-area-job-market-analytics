"""Reproduce Phase 4 tables, figures and findings locally: python -m src.run_analysis.

Only analysis artifacts are written. The approved source, cleaning rules and
SQLite schema/content stay unchanged, and nothing is published or pushed.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import tempfile
from zoneinfo import ZoneInfo

import pandas as pd

from src.analysis import (compute_tables, descriptive_comparisons, records, reconcile,
                          SQL_FILE, verified_connection)
from src.analysis_charts import plot_figures
from src.luke_dataset import digest_file

VERSION='phase4-descriptive-v1'


def markdown_table(frame, columns, labels=None, precision=1):
    """Avoid an optional tabulate dependency; display null as unavailable."""
    def fmt(v):
        if pd.isna(v): return 'unavailable'
        if isinstance(v,float): return f'{v:,.{precision}f}'
        if isinstance(v,int): return f'{v:,}'
        return str(v)
    labels=labels or columns
    return '\n'.join(['| '+' | '.join(labels)+' |','| '+' | '.join(['---']*len(columns))+' |']+
        ['| '+' | '.join(fmt(row[c]) for c in columns)+' |' for row in frame.to_dict('records')])


def findings_markdown(tables, comparisons, payload):
    roles=tables['role_summary']
    cohort=int(roles.records.sum())
    audit=tables['cohort_audit'].set_index('role_status')
    retained=int(audit.records.sum())
    senior=tables['seniority_by_role'].groupby('seniority').records.sum()
    skills=tables['skill_by_role']
    tags=int(roles.usable_tag_records.sum())
    annual=int(roles.derived_annual_present.sum())
    hourly=int(roles.derived_hourly_present.sum())
    geo=tables['geography_by_role']
    city=geo.loc[geo.location_precision.eq('city')].groupby(['location_id','locality']).records.sum().reset_index().sort_values(['records','locality'],ascending=[False,True])
    county=tables['county_by_role'].groupby('county').records.sum().sort_values(ascending=False)
    city_mix=geo.loc[geo.location_precision.eq('city') & geo.locality.isin(['San Francisco','San Jose'])].copy()
    city_mix['city_records']=city_mix.groupby('location_id').records.transform('sum')
    city_mix['within_city_role_pct']=100*city_mix.records/city_mix.city_records
    city_skill=tables['locality_skill_by_role'].query("location_precision=='city' and locality in ['San Francisco','San Jose'] and role=='Data Analyst' and comparison_allowed==1").sort_values(['locality','tagged_records','skill'],ascending=[True,False,True]).groupby('locality').head(3)
    top_skills=[]
    for role in roles.role:
        top=skills.loc[(skills.role==role)&skills.comparison_allowed.eq(1)&skills.tagged_records.gt(0)].sort_values(['tagged_records','skill'],ascending=[False,True]).head(3)
        top_skills.append(role+': '+', '.join(f'{r.skill} {int(r.tagged_records):,}/{int(r.usable_tag_records):,} ({r.comparison_pct:.1f}%)' for r in top.itertuples()))
    missing=int(roles.missing_tag_records.sum())
    nonmissing_but_unusable=int((roles.empty_tag_records+roles.malformed_tag_records).sum())
    stats=tables['skill_count_summary']
    coverage=tables['geography_coverage'].iloc[0]
    lines=[
        '# Phase 4 findings — historical observed Bay Area records','',
        f'Completed {payload["analysis_date"]}. Phase 4 only; Phase 5 has not started. '
        'Source: Luke Barousse data_jobs, pinned 2023 release. '
        '[Attribution and license](../docs/data_attribution.md). Figures and results remain local/unpublished.','',
        '## Questions answered and methods','',
        'We describe accepted records by role, inherited skill tags, resolved geography and explicit '
        'title-based seniority. SQL is the measurement source; independently constructed pandas '
        'summaries reconcile all nine result tables. Distinct record IDs prevent skill/location '
        'joins from multiplying the cohort. Source/rule/schema identity is unchanged.','',
        'Role and seniority shares use all accepted records. Skill rates use populated inherited '
        'lists within the selected role/location; missing lists are not negatives. Comparisons '
        'with fewer than 10 usable lists are suppressed, while counts remain visible. '
        'Tag-count summaries use mean, median, linear-interpolated quartiles and range. '
        'Percentage-point contrasts are descriptive, unadjusted for seniority/employer mix. '
        'No p-values, confidence intervals, population estimates or causal tests are justified '
        'by this non-random, potentially dependent/reposted source.','',
        '## 1. Role composition and visible classification uncertainty','',
        f'Accepted cohort: **{cohort:,} / {retained:,} retained Bay records ({100*cohort/retained:.1f}%)**. '
        f'Outside the denominator: ambiguous **{int(audit.loc["ambiguous","records"]):,}**; '
        f'unclassified **{int(audit.loc["unclassified","records"]):,}**; explicit non-target '
        f'**{int(audit.loc["out_of_scope","records"]):,}**. These are not silently dropped from the audit.','',
        markdown_table(roles,['role','records','cohort_share_pct','usable_tag_records','tag_coverage_pct'],
            ['Accepted role','Records n','Cohort share %','Usable tags n','Tag coverage %']),'',
        'Data Scientist has the largest accepted record count. The Machine Learning Engineer '
        'cohort is much smaller; the strict title rule and excluded mixed-role titles affect that '
        'count. These are sample composition differences, not market-wide role demand or hires.','',
        '## 2. Technical skill tags and missingness','',
        f'Usable inherited lists: **{tags:,}/{cohort:,} ({100*tags/cohort:.1f}%)**; '
        f'missing lists: **{missing:,}**; empty/malformed: **{nonmissing_but_unusable:,}**. '
        'Original descriptions are unavailable for all records, so full-text coverage is unavailable '
        'and required/preferred skill distinctions cannot be assessed.','',
    ]
    lines += ['- '+text for text in top_skills]
    lines += ['', 'These rates are conditional on usable lists; they can sum above 100% because '
              'a record has multiple tags. Tags are inherited publisher output, not independently '
              'validated employer requirements. Missingness can differ by role.','',
        markdown_table(stats,['role','usable_tag_records','mean_tags','q1_tags','median_tags','q3_tags','min_tags','max_tags'],
            ['Role','Usable n','Mean tags','Q1','Median','Q3','Min','Max']),'',
        'Illustrative within-sample percentage-point contrasts (first role minus second):','',
        markdown_table(pd.DataFrame(comparisons),['skill','first_role','second_role','first_usable_n','second_usable_n','difference_pp'],
            ['Tag','First role','Second role','First usable n','Second usable n','Difference pp']),'',
        markdown_table(pd.DataFrame(comparisons),['skill','all_record_difference_lower_pp','all_record_difference_upper_pp'],
            ['Tag contrast','Logical difference lower pp','Logical difference upper pp']),'',
        'These difference ranges allow unavailable-list content to vary separately in each role. '
        'If a range includes zero, even the direction of the all-record tag gap is not fixed by observed lists. '
        'A range staying positive still does not establish a causal/population result or protect against extraction errors.','',
        'The sensitivity figure treats each unavailable list as either lacking or containing '
        'a selected tag: lower = tagged/all role records; upper = (tagged + unavailable)/all role '
        'records. These are logical missing-data bounds, not confidence intervals, imputed values '
        'or bounds on true requirements; extraction errors remain outside the calculation.','',
        '## 3. Geography and role/skill differences','',
        f'The largest accepted city association is **{city.iloc[0].locality}: {int(city.iloc[0].records):,} '
        f'({100*city.iloc[0].records/cohort:.1f}% of the accepted cohort)**. '
        f'The largest county association is **{county.index[0]}: {int(county.iloc[0]):,}**.','',
        markdown_table(city.head(5),['locality','records'],['Incorporated city','Accepted record memberships']),'',
        'Role mix in two major cities (within-city denominators, counts are not skills-expanded):','',
        markdown_table(city_mix,['locality','role','records','city_records','within_city_role_pct'],
            ['City','Role','Role n','City n','Within-city role %']),'',
        'Three most frequent Data Analyst tags in each of these cities (usable lists only):','',
        markdown_table(city_skill,['locality','skill','tagged_records','usable_tag_records','comparison_pct'],
            ['City','Tag','Tagged n','Usable DA n','Conditional %']),'',
        f'Accepted records with city evidence: **{int(coverage.records_with_city):,}**; community '
        f'evidence: **{int(coverage.records_with_community):,}**; county-only: **{int(coverage.county_only_records):,}**. '
        f'Multi-Bay-location records: **{int(coverage.multi_bay_location_records):,}**. '
        'Each record counts once regionally and once per qualifying locality/county; '
        'geographic counts remain non-additive by definition even when this snapshot has no overlap.','',
        f'Locality-role cells with n<10: **{int(geo.small_group.sum())}/{len(geo)}**. '
        'City role-mix counts and locality/role/tag conditional rates are available in the result '
        'tables and notebook, with coverage/denominators. Sparse skill rankings are suppressed. '
        'Communities are not relabeled as incorporated cities, and unresolved geography remains '
        'excluded under the unchanged Phase 3 rules.','',
        '## 4. Explicit seniority','',
        f'Unknown: **{int(senior.get("unknown",0)):,}/{cohort:,} ({100*senior.get("unknown",0)/cohort:.1f}%)**; '
        f'mixed/conflicting: **{int(senior.get("mixed/conflicting",0)):,}**. '
        f'Explicit entry/junior/intern: **{int(senior.get("entry/junior",0)):,} '
        f'({100*senior.get("entry/junior",0)/cohort:.1f}%)**. '
        'The entry/junior category includes internships. Absence of a senior term does not imply '
        'entry level, and explicit seniority does not establish required years of experience.','',
        '## Disabled questions and limitations','',
        f'- Derived annual fields are present in **{annual:,}/{cohort:,} ({100*annual/cohort:.1f}%)**; '
        f'hourly fields in **{hourly:,}/{cohort:,}**. Verified comparable advertised-pay records: **0**. '
        'Currency, advertised/estimated provenance and original bands remain unverified. '
        '**No salary amounts, medians, role/city pay comparisons or annualization are reported.**',
        '- Work arrangement is unknown for every accepted record. No remote/hybrid/on-site share is inferred from false flags.',
        '- Source dates span 2023, but original date meaning, timezone and stable collection coverage are unverified. '
        '**No posting or hiring trend is reported.**',
        '- Reposts may remain; record IDs are file-row lineage, not independently verified vacancies. '
        'Several records can share an employer, and titles/skill extraction may contain errors.',
        '- This is a historical convenience dataset with incomplete geographic/title coverage. '
        'It is not a census or probability sample of Bay Area employment. Large counts do not remove selection bias.',
        '- Skills and seniority can vary with source coverage, employer mix and role mix. '
        'Observed associations do not establish effects of learning a skill on getting hired.','',
        '## Validation and reproducibility','',
        f'- All **{len(payload["reconciliation"])} SQL/pandas tables** matched (counts and percentages/quantiles). '
        'Chart artists were checked against the reconciled SQL data; figure hashes and plotted data are recorded.',
        '- Database content matches the recorded Phase 3 semantic checksum; read-only checks cover '
        'integrity, foreign keys, source lineage, Bay membership and skill bridges. Database file bytes '
        'are checked before/after analysis. Source, cleaning config and schema are unchanged.',
        '- The raw directory read stalled, including its manifest. Phase 4 therefore did not repeat '
        'raw-file hashing; it uses the recorded Phase 3 source checksum and verifies the existing database. '
        'No new job data was downloaded.',
        '- See [analysis tables/provenance](phase4_analysis.json), [verification results](phase4_verification.json), '
        '[methods guide](../docs/phase4_analysis_methods.md) and executed notebooks. '
        'Tests/notebook execution are recorded separately after their actual runs.','',
        'Potential portfolio discussion: the project demonstrates consistent denominators, '
        'explicit missingness, SQL window functions, relational joins, descriptive contrasts, '
        'reproducible plots and evidence-based limits. Broader business recommendations and '
        'Tableau delivery remain later phases.',''
    ]
    return '\n'.join(lines)


def run(root=Path('.')):
    root=Path(root).resolve()
    with verified_connection(root) as (connection,summary,database_hash):
        tables=compute_tables(connection,root)
        reconciliation=reconcile(connection,root,tables)
    comparisons=descriptive_comparisons(tables['skill_by_role'])
    serial={name:records(table) for name,table in tables.items()}
    result_digest=hashlib.sha256(json.dumps({'tables':serial,'comparisons':comparisons},sort_keys=True,allow_nan=False).encode()).hexdigest()
    old_path=root/'reports/phase4_analysis.json'
    previous=json.loads(old_path.read_text()).get('result_sha256') if old_path.exists() else None
    hashes={name:digest_file(root/name) for name in [SQL_FILE,'src/analysis.py','src/analysis_charts.py','src/run_analysis.py']}
    payload=dict(analysis_version=VERSION,analysis_date=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat(),
        source=summary['source'],source_revision=summary['revision'],rule_version=summary['rule_version'],
        source_raw_sha256_recorded_phase3=summary['raw_sha256'],phase3_semantic_sha256=summary['semantic_sha256'],
        database_file_sha256=database_hash,analysis_code_sha256=hashes,
        raw_rehashed_in_phase4=False,raw_verification_note='Raw directory read stalled; use recorded Phase 3 integrity evidence. No raw-directory reads in the analysis runner.',
        cohort='v_target_job_records: accepted_title_only, unchanged Phase 3 nine-county/role rules',
        minimum_comparison_n=10,reconciliation=reconciliation,
        disabled_metrics=['salary_amounts_and_comparisons','posting_and_hiring_trends','explicit_work_arrangement_shares','original_text_skill_requirements'],
        statistical_policy='Descriptive within-sample contrasts and logical missingness sensitivity only; no p-values, confidence intervals or causal/population inference.',
        environment={p:importlib.metadata.version(p) for p in ['pandas','numpy','matplotlib','seaborn','nbformat','nbclient']},
        python=platform.python_version(),sqlite=sqlite3.sqlite_version,tables=serial,descriptive_comparisons=comparisons,
        result_sha256=result_digest,previous_result_sha256=previous,rerun_same_results=(previous==result_digest) if previous else None)
    with tempfile.TemporaryDirectory(prefix='phase4-',dir=root/'reports') as temporary:
        stage=Path(temporary)
        payload['figures']=plot_figures(tables,stage)
        (stage/'phase4_analysis.json').write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+'\n')
        (stage/'phase4_findings.md').write_text(findings_markdown(tables,comparisons,payload))
        # Only known Phase 4 artifacts are replaced; no data/schema files are written.
        for path in stage.glob('*.png'):
            path.replace(root/'reports/figures'/path.name)
        for name in ['phase4_analysis.json','phase4_findings.md']:
            (stage/name).replace(root/'reports'/name)
    return payload


if __name__=='__main__':
    result=run()
    print(json.dumps({'accepted_records':sum(r['records'] for r in result['tables']['role_summary']),
                      'sql_python_tables_matched':len(result['reconciliation']),
                      'figures':len(result['figures']),'result_sha256':result['result_sha256'],
                      'rerun_same_results':result['rerun_same_results']}))
