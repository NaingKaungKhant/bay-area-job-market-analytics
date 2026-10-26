"""Phase 2 only: acquire a pinned licensed CSV and produce raw data-quality profiles.

No canonical cleaning, salary normalization, skill extraction, SQLite or business EDA.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

SOURCE = 'lukebarousse/data_jobs'
EXPECTED_COLUMNS = (
    'job_title_short','job_title','job_location','job_via','job_schedule_type',
    'job_work_from_home','search_location','job_posted_date','job_no_degree_mention',
    'job_health_insurance','job_country','salary_rate','salary_year_avg',
    'salary_hour_avg','company_name','job_skills','job_type_skills',
)


def read_json(path):
    value=json.loads(Path(path).read_text())
    if not isinstance(value,dict): raise ValueError('Expected a JSON object.')
    return value


def digest_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): digest.update(block)
    return digest.hexdigest()


def validate_approval(plan,access):
    if plan.get('source')!=SOURCE or access.get('source')!=SOURCE:
        raise PermissionError('Only the approved Luke dataset is supported.')
    revision=plan.get('revision','')
    if not re.fullmatch(r'[0-9a-f]{40}',revision) or access.get('revision')!=revision:
        raise PermissionError('An exact approved release is required.')
    if plan.get('filename')!='data_jobs.csv': raise ValueError('Unexpected dataset file.')
    if access.get('review_status')!='cleared_for_local_phase2' or access.get('license')!='Apache-2.0':
        raise PermissionError('Reviewed publisher license and local Phase 2 approval are required.')
    if access.get('license_evidence')!=f'https://huggingface.co/datasets/{SOURCE}/blob/{revision}/README.md':
        raise PermissionError('License evidence must match the approved release.')
    for field in ('download','local_storage','local_analysis'):
        if not isinstance(access.get('permissions'),dict) or access['permissions'].get(field) is not True:
            raise PermissionError('Required local-use permission is missing.')
    if not re.fullmatch(r'[0-9a-f]{64}',plan.get('expected_sha256','')):
        raise ValueError('Expected LFS SHA-256 is required.')
    if type(plan.get('expected_bytes')) is not int or not 0<plan['expected_bytes']<=plan.get('max_download_bytes',0):
        raise ValueError('Invalid download size bounds.')


def acquire(plan,access,root=Path('.')):
    """Use public HTTPS without credentials; refuse changed bytes or silent overwrites."""
    validate_approval(plan,access)
    import requests
    root=Path(root)
    raw=root/plan['raw_directory']
    raw.mkdir(parents=True,exist_ok=True)
    destination=raw/plan['filename']
    if destination.exists():
        verify_raw(destination,plan)
        manifest=read_json(raw/'manifest.json')
        verify_manifest(manifest,plan,destination)
        return manifest
    base=f'https://huggingface.co/datasets/{SOURCE}/resolve/{plan["revision"]}'
    started=datetime.now(timezone.utc).isoformat()
    with requests.Session() as session:
        card=session.get(base+'/README.md',timeout=(15,90))
        card.raise_for_status()
        if not re.search(r'^license:\s*apache-2\.0\s*$',card.text,re.MULTILINE):
            raise PermissionError('Pinned README no longer declares the reviewed license.')
        (raw/'README.source.md').write_bytes(card.content)
        license_response=session.get('https://www.apache.org/licenses/LICENSE-2.0.txt',timeout=(15,90))
        license_response.raise_for_status()
        (raw/'LICENSE.source.txt').write_bytes(license_response.content)
        temporary=raw/(destination.name+'.'+uuid.uuid4().hex+'.part')
        try:
            for attempt in range(3):
                try:
                    size=0
                    with session.get(base+'/'+plan['filename'],stream=True,timeout=(15,90)) as response:
                        response.raise_for_status()
                        with temporary.open('wb') as stream:
                            for block in response.iter_content(1024*1024):
                                size+=len(block)
                                if size>plan['max_download_bytes']: raise ValueError('Download exceeds project cap.')
                                stream.write(block)
                    verify_raw(temporary,plan)
                    break
                except requests.RequestException:
                    if attempt==2: raise
                    time.sleep(2*(attempt+1))
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    manifest={
        'source':SOURCE,'revision':plan['revision'],'source_file':plan['filename'],
        'request_url':base+'/'+plan['filename'],'started_at_utc':started,
        'completed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'complete',
        'bytes':destination.stat().st_size,'sha256':digest_file(destination),
        'expected_lfs_sha256':plan['expected_sha256'],'license':'Apache-2.0',
        'source_card_sha256':digest_file(raw/'README.source.md'),
        'license_text_sha256':digest_file(raw/'LICENSE.source.txt'),
        'row_count':None,'note':'CSV row count is assigned by the verified profiling pass, not inferred from download bytes.'
    }
    (raw/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def verify_raw(path,plan):
    if Path(path).stat().st_size!=plan['expected_bytes'] or digest_file(path)!=plan['expected_sha256']:
        raise ValueError('Raw file size/SHA-256 differs from the pinned publisher metadata.')


def verify_manifest(manifest,plan,path):
    if any((manifest.get('source')!=SOURCE,manifest.get('revision')!=plan['revision'],
            manifest.get('status')!='complete',manifest.get('sha256')!=plan['expected_sha256'],
            manifest.get('source_file')!=Path(path).name,manifest.get('bytes')!=plan['expected_bytes'])):
        raise ValueError('Manifest provenance mismatch.')


def parse_skill_tags(value):
    """Inspect publisher lists safely; do not eval or claim original text extraction."""
    if value in ('','NULL','null','None'): return 'missing',None
    try: parsed=ast.literal_eval(value)
    except (ValueError,SyntaxError,TypeError,RecursionError): return 'malformed',None
    if not isinstance(parsed,list) or not all(isinstance(v,str) and bool(v.strip()) for v in parsed):
        return 'malformed',None
    return ('empty' if not parsed else 'populated'),parsed


def match_city(location,country,cities):
    """Conservative preliminary exact city/CA diagnostic, not final Phase 3 geography."""
    if country!='United States': return None
    match=re.fullmatch(r'\s*([^,;|/]+),\s*(?:CA|California)(?:,\s*(?:United States|USA))?\s*',location)
    if not match: return None
    city=match.group(1).strip()
    return city if city in cities else None


def raw_missing(series):
    return series.astype(str).str.strip().isin(['','NULL','null','None'])


def profile_frame(frame,cities):
    """Diagnostics on raw strings; no imputation, accepted roles, or market KPIs."""
    import pandas as pd
    missing={c:int(raw_missing(frame[c]).sum()) for c in frame.columns}
    parsed_dates=pd.to_datetime(frame['job_posted_date'],errors='coerce')
    nonmissing_dates=~raw_missing(frame['job_posted_date'])
    city_labels=[match_city(loc,country,cities) for loc,country in zip(frame['job_location'],frame['job_country'])]
    labels=pd.Series(city_labels,index=frame.index,dtype='object')
    bay=frame.loc[labels.notna()]
    bay_labels=labels.loc[labels.notna()]
    roles=dict(bay['job_title_short'].value_counts().sort_index())
    skills=Counter()
    for value in bay['job_skills']: skills[parse_skill_tags(value)[0]]+=1
    salary={}
    for field in ['salary_year_avg','salary_hour_avg']:
        converted=pd.to_numeric(bay[field],errors='coerce')
        present=~raw_missing(bay[field])
        salary[field]={
            'present':int(present.sum()),'numeric':int(converted.notna().sum()),
            'invalid_numeric':int((present & converted.isna()).sum()),
            'nonpositive':int((converted<=0).sum()),
            'infinite':int(converted.isin([float('inf'),float('-inf')]).sum()),
        }
    role_quality={}
    for label,group in bay.groupby('job_title_short',dropna=False):
        values=pd.to_numeric(group['salary_year_avg'],errors='coerce')
        role_quality[str(label)]={
            'rows':len(group),
            'positive_finite_annual_values':int(((values>0) & ~values.isin([float('inf'),float('-inf')])).sum()),
            'populated_skill_lists':sum(parse_skill_tags(value)[0]=='populated' for value in group['job_skills']),
        }
    evidence_keys=['company_name','job_title','job_location','job_posted_date']
    return {
        'rows':len(frame),'missing':missing,
        'date_invalid_nonblank':int((nonmissing_dates & parsed_dates.isna()).sum()),
        'date_min':None if parsed_dates.dropna().empty else parsed_dates.min().isoformat(),
        'date_max':None if parsed_dates.dropna().empty else parsed_dates.max().isoformat(),
        'years':{str(k):int(v) for k,v in parsed_dates.dt.year.dropna().astype(int).value_counts().items()},
        'publisher_role_labels':{str(k):int(v) for k,v in frame['job_title_short'].value_counts().items()},
        'countries':{str(k):int(v) for k,v in frame['job_country'].value_counts().items()},
        'bay_rows':len(bay),'bay_missing':{c:int(raw_missing(bay[c]).sum()) for c in bay.columns},
        'bay_role_labels':{str(k):int(v) for k,v in roles.items()},
        'bay_role_quality':role_quality,
        'bay_salary_rate_values':{str(k):int(v) for k,v in bay['salary_rate'].value_counts(dropna=False).items()},
        'bay_city_counts':{str(k):int(v) for k,v in bay_labels.value_counts().items()},
        'bay_skill_list_status':dict(skills),'bay_salary_fields':salary,
        'bay_wfh_values':{str(k):int(v) for k,v in bay['job_work_from_home'].value_counts(dropna=False).items()},
        'bay_source_location_labels':{str(k):int(v) for k,v in bay['job_location'].value_counts().items()},
        'bay_duplicate_key_hashes':pd.util.hash_pandas_object(bay[evidence_keys],index=False).tolist(),
        'all_row_hashes':pd.util.hash_pandas_object(frame,index=False).tolist(),
        'bay_row_hashes':pd.util.hash_pandas_object(bay,index=False).tolist(),
    }


def _merge_counts(destination,source):
    for key,value in source.items(): destination[key]=destination.get(key,0)+int(value)


def profile(plan,access,root=Path('.')):
    validate_approval(plan,access)
    import pandas as pd
    root=Path(root)
    raw=root/plan['raw_directory']/plan['filename']
    verify_raw(raw,plan)
    manifest_path=raw.parent/'manifest.json'
    manifest=read_json(manifest_path)
    verify_manifest(manifest,plan,raw)
    city_reference=read_json(root/plan['geographic_reference'])
    cities=city_reference['cities']
    header=pd.read_csv(raw,nrows=0).columns.tolist()
    if header!=list(EXPECTED_COLUMNS): raise ValueError('CSV schema differs from the documented 17-column contract.')
    sums={k:{} for k in ['missing','years','publisher_role_labels','countries','bay_missing','bay_role_labels','bay_city_counts','bay_skill_list_status','bay_wfh_values','bay_source_location_labels','bay_salary_rate_values']}
    role_quality={}
    n=bay_n=invalid_dates=0
    date_min=date_max=None
    seen_all=set();seen_bay=set();seen_key=set()
    exact_duplicates=bay_duplicates=bay_key_duplicates=0
    salary={field:{k:0 for k in ['present','numeric','invalid_numeric','nonpositive','infinite']} for field in ['salary_year_avg','salary_hour_avg']}
    for frame in pd.read_csv(raw,dtype=str,keep_default_na=False,chunksize=plan['chunk_rows']):
        part=profile_frame(frame,cities)
        n+=part['rows'];bay_n+=part['bay_rows'];invalid_dates+=part['date_invalid_nonblank']
        if part['date_min']: date_min=min(date_min or part['date_min'],part['date_min'])
        if part['date_max']: date_max=max(date_max or part['date_max'],part['date_max'])
        for key in sums: _merge_counts(sums[key],part[key])
        for label,counts in part['bay_role_quality'].items():
            _merge_counts(role_quality.setdefault(label,{}),counts)
        for field in salary: _merge_counts(salary[field],part['bay_salary_fields'][field])
        for key,seen in [('all_row_hashes',seen_all),('bay_row_hashes',seen_bay),('bay_duplicate_key_hashes',seen_key)]:
            count=0
            for value in part[key]:
                count+=value in seen
                seen.add(value)
            if key=='all_row_hashes': exact_duplicates+=count
            elif key=='bay_row_hashes': bay_duplicates+=count
            else: bay_key_duplicates+=count
    county_counts={county:0 for county in city_reference['counties']}
    for city,count in sums['bay_city_counts'].items(): county_counts[cities[city]]+=count
    result={
        'status':'phase2_raw_profiling_complete','source':SOURCE,'revision':plan['revision'],
        'raw_sha256':manifest['sha256'],'download_bytes':manifest['bytes'],
        'profiled_at_utc':datetime.now(timezone.utc).isoformat(),'columns':header,
        'raw_row_count':n,'raw_missing_counts':sums['missing'],
        'date_min':date_min,'date_max':date_max,'invalid_nonblank_dates':invalid_dates,'year_counts':sums['years'],
        'country_counts':sums['countries'],'publisher_role_label_counts':sums['publisher_role_labels'],
        'exact_duplicate_row_candidates':exact_duplicates,
        'preliminary_bay_area':{
            'definition':'United States country + exact recognized city, CA/California; no fuzzy, headquarters or search_location inference; preliminary Phase 2 diagnostic only',
            'reference_sha256':digest_file(root/plan['geographic_reference']),
            'row_count':bay_n,'missing_counts':sums['bay_missing'],'publisher_role_label_counts':sums['bay_role_labels'],
            'city_counts':sums['bay_city_counts'],'county_counts':county_counts,
            'role_quality':role_quality,'salary_rate_values':sums['bay_salary_rate_values'],
            'source_location_labels':sums['bay_source_location_labels'],
            'skill_list_status':sums['bay_skill_list_status'],'salary_fields':salary,
            'work_from_home_raw_values':sums['bay_wfh_values'],
            'exact_duplicate_row_candidates':bay_duplicates,
            'employer_title_location_date_duplicate_candidates':bay_key_duplicates,
        },
        'important_limits':[
            'Raw rows and duplicate candidates are not canonical unique postings or validated role counts.',
            'Publisher role labels and skill tags are inherited, not our own classification or text extraction.',
            'No source-native posting ID, original description, advertised salary bounds/currency/provenance evidence is present in this schema.',
            'Parsed work-from-home false cannot distinguish on-site from hybrid.',
            'Source dates have no timezone evidence or stable collection-coverage proof; no posting/hiring trend is approved.',
            'Geography reference covers the 101 incorporated cities; unincorporated, vague and multi-location labels require later review.',
            'Duplicate hashes use pandas 64-bit fingerprints as candidate diagnostics, not certified identity keys.',
        ],
    }
    if manifest.get('row_count') is not None and manifest['row_count']!=n:
        raise ValueError('Existing manifest row count does not reconcile with the verified full scan.')
    manifest['row_count']=n
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    (root/plan['profile_json']).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['acquire','profile'])
    parser.add_argument('--plan',type=Path,default=Path('config/phase2_plan.json'))
    parser.add_argument('--access',type=Path,default=Path('config/source_access.json'))
    args=parser.parse_args()
    plan,access=read_json(args.plan),read_json(args.access)
    result=acquire(plan,access) if args.command=='acquire' else profile(plan,access)
    if args.command=='profile':
        print(json.dumps({key:result[key] for key in ['status','raw_row_count','date_min','date_max']}))
        print(json.dumps(result['preliminary_bay_area'],indent=2))
    else: print(json.dumps(result,indent=2))


if __name__=='__main__': main()
