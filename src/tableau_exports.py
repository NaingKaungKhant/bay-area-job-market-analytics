"""Offline Phase 5 exports from verified SQLite; no source or schema mutation.

A single long aggregate CSV avoids physical skill/location joins in Tableau.
Parameters select EXACTLY one precomputed geography and role slice. These slices
are alternatives, not additive groups: never total across selector values.
"""
from __future__ import annotations

import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.analysis import verified_connection,compute_tables,reconcile
from src.luke_dataset import digest_file

SQL='sql/004_phase5_exports.sql'
KEY=['scope_key','role_selection','panel','category_type','category']


def queries(root):
    text=(Path(root)/SQL).read_text()
    common=text.split('-- common\n',1)[1].split('-- name: ',1)[0]
    parts=re.split(r'^-- name: (\w+)\s*$',text,flags=re.M)
    return {name:common+query for name,query in zip(parts[1::2],parts[2::2])}


def validate_metrics(frame):
    """Key, numerator/denominator, missingness and suppression checks are required."""
    if frame.empty or frame.duplicated(KEY).any():raise ValueError('Empty metrics or duplicate metric key.')
    for column in ['numerator','denominator','category_order','comparison_allowed']:
        values=frame[column]
        if values.isna().any() or (values<0).any() or (values%1!=0).any():
            raise ValueError('Invalid integer field: '+column)
    if (frame.numerator>frame.denominator).any():raise ValueError('Numerator exceeds denominator.')
    expected=frame.numerator/frame.denominator.replace(0,np.nan)
    expected=expected.where(frame.comparison_allowed.eq(1))
    np.testing.assert_allclose(frame.rate.to_numpy(dtype=float),expected.to_numpy(dtype=float),rtol=1e-12,atol=1e-12,equal_nan=True)
    skill=frame.loc[frame.panel.eq('skills')]
    if not (skill.comparison_allowed==(skill.denominator>=10)).all():raise ValueError('Skill n=10 suppression contract violated.')
    if not frame.source_revision.nunique()==frame.cleaning_rule_version.nunique()==1:
        raise ValueError('Mixed source/rule versions.')
    return {'unique_metric_keys':True,'nonnegative_integer_counts':True,'denominators_valid':True,
            'rates_reconciled':True,'skill_suppression_n10':True,'single_source_rule_version':True}


def roundtrip_csv(frame,path):
    """UTF-8, comma delimiter, dot decimal, unrounded numbers; blank means null."""
    frame.to_csv(path,index=False,encoding='utf-8',lineterminator='\n',na_rep='')
    back=pd.read_csv(path,encoding='utf-8',keep_default_na=False)
    if len(back)!=len(frame) or list(back.columns)!=list(frame.columns):raise ValueError('CSV round-trip shape mismatch.')
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            wanted=frame[column].to_numpy(dtype=float,na_value=np.nan)
            actual=pd.to_numeric(back[column].mask(back[column].eq('')),errors='raise').to_numpy(dtype=float)
            np.testing.assert_allclose(actual,wanted,rtol=1e-12,atol=1e-12,equal_nan=True)
        else:
            wanted=frame[column].where(frame[column].notna(),'').astype(str).tolist()
            if back[column].astype(str).tolist()!=wanted:raise ValueError('CSV text round-trip mismatch: '+column)
    return back


def expected_states(metrics,connection):
    """Independent parameterized SQL controls; actual Tableau cells stay blank.

    These checks read fact/bridge records directly, rather than querying the
    aggregate export again. Null scope/role controls mean all accepted records.
    """
    cases=[('default','All Bay Area','All roles',None,None,None),
           ('data_analyst','All Bay Area','Data Analyst','Data Analyst',None,None),
           ('sf_data_analyst','City: San Francisco (San Francisco)','Data Analyst','Data Analyst','city','San Francisco'),
           ('santa_clara_county','County: Santa Clara','All roles',None,'county','Santa Clara'),
           ('stanford_community','Community: Stanford (Santa Clara)','All roles',None,'community','Stanford'),
           ('small_group','City: San Jose (Santa Clara)','Machine Learning Engineer','Machine Learning Engineer','city','San Jose'),
           ('zero_results','City: Alameda (Alameda)','Machine Learning Engineer','Machine Learning Engineer','city','Alameda')]
    rows=[]
    for case,scope,selector,role,kind,place in cases:
        subset=metrics.loc[metrics.scope_key.eq(scope)&metrics.role_selection.eq(selector)]
        if subset.empty:continue
        where="(:role IS NULL OR f.role=:role) AND (:kind IS NULL OR EXISTS (SELECT 1 FROM bridge_job_locations b JOIN dim_locations l USING(location_id) WHERE b.job_posting_id=f.job_posting_id AND l.in_bay_area=1 AND ((:kind='county' AND l.county=:place) OR (l.location_precision=:kind AND l.locality=:place))))"
        params={'role':role,'kind':kind,'place':place}
        sql='SELECT COUNT(*) FROM v_target_job_records f WHERE '+where
        n=connection.execute(sql,params).fetchone()[0]
        usable=connection.execute(sql+" AND f.skill_list_status='populated'",params).fetchone()[0]
        checks=[('coverage','Selected records',n,n),('coverage','Usable inherited tags',usable,n)]
        known_tags=set(metrics.loc[metrics.panel.eq('skills'),'category'])
        for tag in ['sql','python','tableau']:
            if tag not in known_tags:continue
            tagged=connection.execute(sql+" AND f.skill_list_status='populated' AND EXISTS (SELECT 1 FROM bridge_job_skills b JOIN dim_skills s USING(skill_id) WHERE b.job_posting_id=f.job_posting_id AND s.canonical_name=:skill)",dict(params,skill=tag)).fetchone()[0]
            checks.append(('skills',tag,tagged,usable))
        # Role shares retain the four-role geographic denominator under a role selector.
        base_params=dict(params,role=None)
        base_n=connection.execute(sql,base_params).fetchone()[0]
        role_values=['Data Analyst','Data Engineer','Data Scientist','Machine Learning Engineer'] if role is None else [role]
        for item_role in role_values:
            count=connection.execute(sql,dict(params,role=item_role)).fetchone()[0]
            checks.append(('roles',item_role,count,base_n))
        for seniority in ['entry/junior','mid','senior','lead/staff/principal','management','mixed/conflicting','unknown']:
            count=connection.execute(sql+' AND f.seniority=:seniority',dict(params,seniority=seniority)).fetchone()[0]
            checks.append(('seniority',seniority,count,n))
        for status,count in connection.execute('SELECT role_status,COUNT(*) FROM fact_job_postings GROUP BY role_status'):
            checks.append(('classification',status,count,connection.execute('SELECT COUNT(*) FROM fact_job_postings').fetchone()[0]))
        geography_view='County' if kind=='county' else 'Community' if kind=='community' else 'City'
        # Validate representative geographic bars using a separate record-grain join.
        place_sql="l.county" if geography_view=='County' else "COALESCE(l.locality,l.county)||' ('||l.county||')'"
        extra="" if geography_view=='County' else " AND l.location_precision=:precision"
        geo_sql='SELECT '+place_sql+',COUNT(DISTINCT f.job_posting_id) FROM v_target_job_records f JOIN bridge_job_locations b USING(job_posting_id) JOIN dim_locations l USING(location_id) WHERE l.in_bay_area=1 AND '+where+extra+' GROUP BY '+place_sql+' ORDER BY 2 DESC,1 LIMIT 3'
        geo_checks=connection.execute(geo_sql,dict(params,precision=geography_view.lower())).fetchall()
        for panel,category,num,den in checks+ [('geography',name,count,n) for name,count in geo_checks]:
            match=subset.loc[subset.panel.eq(panel)&subset.category.eq(category)]
            if panel=='geography':match=match.loc[match.category_type.eq(geography_view)]
            if match.empty:raise ValueError('Expected reconciliation metric missing: '+str((case,panel,category)))
            item=match.iloc[0]
            assert (int(item.numerator),int(item.denominator))==(num,den),(case,panel,category)
            rate=num/den if den and (panel!='skills' or den>=10) else None
            actual=None if pd.isna(item.rate) else float(item.rate)
            assert actual is None if rate is None else abs(actual-rate)<1e-12
            rows.append(dict(case=case,scope_key=scope,role_selection=selector,geography_view=geography_view,panel=panel,category=category,
                sql_numerator=num,sql_denominator=den,sql_rate=rate,csv_numerator=int(item.numerator),
                csv_denominator=int(item.denominator),csv_rate=actual,csv_status='matched',
                tableau_numerator=None,tableau_denominator=None,tableau_rate=None,
                tableau_status='NOT_RUN_COMPUTER_USE_PERMISSION',notes='Record actual Tableau results after applying the exact parameter state; do not overwrite expected values.'))
    return pd.DataFrame(rows)


def export(root=Path('.')):
    root=Path(root).resolve()
    out=root/'data/processed/phase5';out.mkdir(parents=True,exist_ok=True)
    checklist=root/'reports/phase5_reconciliation.csv'
    if checklist.exists():
        with checklist.open(newline='',encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                if any(row.get(key,'').strip() for key in ['tableau_numerator','tableau_denominator','tableau_rate']):
                    raise ValueError('Archive completed manual Tableau reconciliation before regenerating exports/checklist.')
    old_path=out/'export_manifest.json'
    previous=json.loads(old_path.read_text()).get('content_sha256') if old_path.exists() else None
    with verified_connection(root) as (connection,phase3,database_hash):
        # Preserve Phase 4's independently reconciled analytical foundation.
        phase4=compute_tables(connection,root);reconciled=reconcile(connection,root,phase4)
        query=queries(root)
        tables={name:pd.read_sql_query(sql,connection) for name,sql in query.items()}
        tables['scope_catalog']['location_id']=tables['scope_catalog'].location_id.astype('Int64')
        checks=validate_metrics(tables['dashboard_metrics'])
        expected=expected_states(tables['dashboard_metrics'],connection)
        # Default role counts/skills/seniority must agree with Phase 4 outputs.
        default=tables['dashboard_metrics'].query("scope_key=='All Bay Area' and role_selection=='All roles'")
        got=default.query("panel=='roles'").set_index('category').numerator
        want=phase4['role_summary'].set_index('role').records.reindex(got.index,fill_value=0)
        pd.testing.assert_series_equal(got.sort_index(),want.sort_index(),check_names=False,check_dtype=False)
        for role in want.index:
            subset=tables['dashboard_metrics'].query("scope_key=='All Bay Area' and role_selection==@role and panel=='skills'").set_index('category')
            original=phase4['skill_by_role'].query('role==@role').set_index('skill')
            np.testing.assert_array_equal(subset.loc[original.index,'numerator'],original.tagged_records)
            np.testing.assert_array_equal(subset.loc[original.index,'denominator'],original.usable_tag_records)
    files={}
    with tempfile.TemporaryDirectory(prefix='phase5-export-',dir=out.parent) as temporary:
        stage=Path(temporary)
        for name,frame in tables.items():
            path=stage/(name+'.csv');roundtrip_csv(frame,path)
            files[path.name]={'rows':len(frame),'columns':list(frame.columns),'sha256':digest_file(path),
                             'query_sha256':hashlib.sha256(query[name].encode()).hexdigest(),
                             'key':KEY if name=='dashboard_metrics' else ['scope_key'] if name=='scope_catalog' else ['role_selection']}
        content=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        manifest=dict(export_version='phase5-aggregate-v1',generated_at=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
            source=phase3['source'],source_revision=phase3['revision'],cleaning_rule_version=phase3['rule_version'],
            database_file_sha256=database_hash,phase3_semantic_sha256=phase3['semantic_sha256'],
            sql_file_sha256=digest_file(root/SQL),export_script_sha256=digest_file(root/'src/tableau_exports.py'),
            encoding='UTF-8',delimiter=',',null_encoding='empty CSV field; never interpret as zero',
            percentage_storage='fraction 0..1; Tableau format Percentage (1 decimal)',
            files=files,validation=checks,phase4_reconciliation=reconciled,
            expected_state_checks=len(expected),native_tableau_validation='NOT PERFORMED: Computer Use permissions not granted',
            content_sha256=content,rerun_same_content=previous==content if previous else None,
            prohibited_fields_absent=['salary_amounts','currency','posting_dates','work_arrangement','company_names','job_titles','native_posting_ids','descriptions'],
            publication_authorized=False,limitations='Precomputed single-selector slices only. Do not join aggregate rollups or sum across scope/role_selection/panels. Raw checksum is recorded Phase 3 evidence; no new raw data read.')
        for path in stage.iterdir():path.replace(out/path.name)
        (out/'export_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # The checklist is local documentation, not a fabricated Tableau result.
    expected.to_csv(root/'reports/phase5_reconciliation.csv',index=False,encoding='utf-8',lineterminator='\n',na_rep='')
    (root/'reports/phase5_export_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    result=export()
    print(json.dumps({'files':{n:m['rows'] for n,m in result['files'].items()},'expected_state_checks':result['expected_state_checks'],'rerun_same_content':result['rerun_same_content']}))
