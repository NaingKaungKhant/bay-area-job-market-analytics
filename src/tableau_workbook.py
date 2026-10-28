"""Create a local Tableau XML draft and self-contained package from SQL exports.

XML follows Tableau's installed sample workbook structure. Parsing this file is
NOT a Tableau engine validation. Desktop automation is unavailable, so native
open/render/filter checks remain explicitly pending in the acceptance checklist.
"""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
import plistlib
import xml.etree.ElementTree as E
import zipfile

from src.luke_dataset import digest_file

DS='bay_metrics'


def sub(parent,tag,text=None,**attrs):
    node=E.SubElement(parent,tag,{key.replace('_','-'):str(value) for key,value in attrs.items()})
    if text is not None:node.text=str(text)
    return node


def ref(instance):return f'[{DS}].[{instance}]'


def parameter(parent,name,values,default):
    col=sub(parent,'column',caption=name,datatype='string',name=f'[{name}]',param_domain_type='list',role='measure',type='nominal',value=json.dumps(default))
    sub(col,'calculation',class_='tableau',formula=json.dumps(default))
    members=sub(col,'members')
    for value in values:sub(members,'member',value=json.dumps(value))
    return col


def create(root=Path('.')):
    root=Path(root).resolve();directory=root/'dashboard';directory.mkdir(exist_ok=True)
    data=root/'data/processed/phase5'
    manifest=json.loads((data/'export_manifest.json').read_text())
    for filename,meta in manifest['files'].items():
        if digest_file(data/filename)!=meta['sha256']:raise ValueError('Export changed since validation.')
    with (data/'scope_catalog.csv').open(newline='',encoding='utf-8') as f:scopes=[r['scope_key'] for r in csv.DictReader(f)]
    with (data/'role_catalog.csv').open(newline='',encoding='utf-8') as f:roles=[r['role_selection'] for r in csv.DictReader(f)]
    with (data/'dashboard_metrics.csv').open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f);headers=reader.fieldnames
        audit={r['category']:int(r['numerator']) for r in reader if r['scope_key']=='All Bay Area' and r['role_selection']=='All roles' and r['panel']=='classification'}
    workbook=E.Element('workbook',{'original-version':'18.1','source-platform':'mac','version':'18.1'})
    workbook.append(E.Comment('Generated local DRAFT. Tableau native validation NOT performed. Do not publish.'))
    sub(workbook,'document-format-change-manifest')
    sub(workbook,'preferences')
    sources=sub(workbook,'datasources')
    params=sub(sources,'datasource',hasconnection='false',inline='true',name='Parameters',version='18.1')
    sub(params,'aliases',enabled='yes')
    parameter(params,'Scope',scopes,'All Bay Area')
    parameter(params,'Role',roles,'All roles')
    parameter(params,'Geography view',['County','City','Community','County-only'],'City')
    source=sub(sources,'datasource',caption='2023 accepted Bay records — SQL aggregate slices',inline='true',name=DS,version='18.1')
    connection=sub(source,'connection',class_='textscan',directory='../data/processed/phase5',filename='dashboard_metrics.csv',password='',server='')
    relation=sub(connection,'relation',name='dashboard_metrics.csv',table='[dashboard_metrics#csv]',type='table')
    cols=sub(relation,'columns',character_set='UTF-8',header='yes',locale='en_US',separator=',')
    integers={'numerator','denominator','comparison_allowed','category_order'}
    definitions={}
    sub(source,'aliases',enabled='yes')
    for ordinal,name in enumerate(headers):
        dtype='integer' if name in integers else 'real' if name=='rate' else 'string'
        sub(cols,'column',datatype=dtype,name=name,ordinal=ordinal)
        measure=name in {'numerator','denominator','rate'}
        aggregation='Sum' if name=='numerator' else 'Max' if measure else None
        attrs=dict(datatype=dtype,name=f'[{name}]',role='measure' if measure else 'dimension',type='quantitative' if measure else 'nominal')
        if aggregation:attrs['aggregation']=aggregation
        if name=='rate':attrs['default_format']='p0.0%'
        definitions[name]=sub(source,'column',**attrs)
    calculations={
        'Selected slice':("[scope_key]=[Parameters].[Scope] AND [role_selection]=[Parameters].[Role]",'boolean','dimension','nominal'),
        'Skill top twelve':('[category_order]<=12 AND [comparison_allowed]=1','boolean','dimension','nominal'),
        'Selected geography':('[category_type]=[Parameters].[Geography view] AND [category_order]<=15','boolean','dimension','nominal'),
        'Display rate':('IF MIN([comparison_allowed])=1 AND MAX([denominator])>0 THEN SUM([numerator])/MAX([denominator]) END','real','measure','quantitative'),
        'Count and denominator':('STR(SUM([numerator])) + " / " + STR(MAX([denominator])) + IF MIN([comparison_allowed])=0 THEN " — comparison suppressed" ELSE IF MAX([denominator])=0 THEN " — unavailable" ELSE " (" + STR(ROUND(100*SUM([numerator])/MAX([denominator]),1)) + "%)" END END','string','measure','nominal'),
        'Skill coverage message':('IF SUM([numerator])<10 THEN "Skill comparisons suppressed: fewer than 10 usable lists. n=" ELSE "Usable inherited lists: n=" END + STR(SUM([numerator])) + " / " + STR(MAX([denominator]))','string','measure','nominal'),
    }
    for name,(formula,dtype,role,kind) in calculations.items():
        col=sub(source,'column',caption=name,datatype=dtype,name=f'[{name}]',role=role,type=kind)
        if name=='Display rate':col.set('default-format','p0.0%')
        sub(col,'calculation',class_='tableau',formula=formula)
        definitions[name]=col
    sub(source,'layout',dim_ordering='alphabetic',measure_ordering='alphabetic')
    sheets=sub(workbook,'worksheets')
    specs=[
      ('Selected records','coverage','Selected records','numerator','Text',False),
      ('Role records','roles',None,'numerator','Bar',True),
      ('Role shares','roles',None,'Display rate','Bar',True),
      ('Inherited skill percentages','skills',None,'Display rate','Bar',True),
      ('Location associations','geography',None,'numerator','Bar',True),
      ('Explicit seniority','seniority',None,'Display rate','Bar',True),
      ('Data coverage','coverage',None,'Count and denominator','Text',True),
      ('Classification audit','classification',None,'Count and denominator','Text',True),
      ('Skill detail counts','skills',None,'Count and denominator','Text',True),
      ('Skill coverage warning','coverage','Usable inherited tags','Skill coverage message','Text',False),
    ]
    instances={}
    for name,col in definitions.items():
        if name in calculations and col.get('role')=='measure':derivation='User'
        elif col.get('role')=='measure':derivation='Sum' if name=='numerator' else 'Max'
        else:derivation='None'
        code={'User':'usr','Sum':'sum','Max':'max','None':'none'}[derivation]
        kind='qk' if col.get('type')=='quantitative' else 'nk'
        instances[name]=(f'{code}:{name}:{kind}',derivation,col.get('type'))

    def categorical(view,field,value):
        fil=sub(view,'filter',class_='categorical',column=ref(instances[field][0]))
        sub(fil,'groupfilter',function='member',level=f'[{instances[field][0]}]',member=value)

    for name,panel,category,value,mark,grouped in specs:
        ws=sub(sheets,'worksheet',name=name)
        opts=sub(ws,'layout-options');title=sub(opts,'title');sub(sub(title,'formatted-text'),'run',name,fontsize='12',bold='true')
        table=sub(ws,'table');view=sub(table,'view');viewsources=sub(view,'datasources')
        sub(viewsources,'datasource',caption=source.get('caption'),name=DS)
        sub(viewsources,'datasource',name='Parameters')
        deps=sub(view,'datasource-dependencies',datasource=DS)
        for field,col in definitions.items():
            deps.append(copy.deepcopy(col));instance,deriv,kind=instances[field]
            sub(deps,'column-instance',column=f'[{field}]',derivation=deriv,name=f'[{instance}]',pivot='key',type=kind)
        pdeps=sub(view,'datasource-dependencies',datasource='Parameters')
        for col in params.findall('column'):pdeps.append(copy.deepcopy(col))
        categorical(view,'Selected slice','true');categorical(view,'panel',json.dumps(panel))
        if category:categorical(view,'category',json.dumps(category))
        if panel=='skills' and name!='Skill detail counts':categorical(view,'Skill top twelve','true')
        if panel=='geography':categorical(view,'Selected geography','true')
        sub(view,'aggregation',value='true')
        style=sub(table,'style');rule=sub(style,'style-rule',element='worksheet')
        sub(rule,'format',attr='display-field-labels',scope='rows',value='false')
        if mark=='Bar':
            axis=sub(style,'style-rule',element='axis')
            sub(axis,'format',attr='title',scope='cols',value='Share (0–100%)' if value=='Display rate' else 'Observed record count',field=ref(instances[value][0]))
        pane=sub(sub(table,'panes'),'pane',selection_relaxation_option='selection-relaxation-allow')
        sub(sub(pane,'view'),'breakdown',value='auto');sub(pane,'mark',class_=mark)
        enc=sub(pane,'encodings');sub(enc,'text',column=ref(instances[value][0]))
        if mark=='Bar':sub(enc,'color',column=ref(instances['category_type'][0]))
        tooltip=sub(sub(pane,'customized-tooltip'),'formatted-text')
        sub(tooltip,'run',f'<{ref(instances["category"][0])}>\nCount / denominator: <{ref(instances["Count and denominator"][0])}>\n<{ref(instances["warning"][0])}>\nHistorical 2023 records; not actual hires or verified unique vacancies.')
        pstyle=sub(sub(pane,'style'),'style-rule',element='mark')
        sub(pstyle,'format',attr='mark-labels-show',value='true')
        sub(table,'rows',ref(instances['category'][0]) if grouped else '')
        sub(table,'cols',ref(instances[value][0]) if mark=='Bar' else '')
    dashboards=sub(workbook,'dashboards')

    def text_zone(zones,i,x,y,w,h,text,font=10,bold=False):
        z=sub(zones,'zone',id=i,x=x,y=y,w=w,h=h,type_v2='text')
        sub(sub(z,'formatted-text'),'run',text,fontname='Tableau Book',fontsize=font,bold=str(bold).lower())
        return z

    def dashboard(name,quality=False):
        d=sub(dashboards,'dashboard',name=name)
        sub(d,'style');sub(d,'size',maxheight=1200,maxwidth=1440,minheight=1200,minwidth=1440,sizing_mode='fixed')
        zs=sub(d,'zones');layout=sub(zs,'zone',id='1',x='0',y='0',w='100000',h='100000',type_v2='layout-basic')
        text_zone(layout,2,1000,500,98000,5200,'2023 Bay Area Data Jobs & Skills — local Tableau draft',20,True)
        text_zone(layout,3,1000,5700,98000,4000,'Historical observed records. Not current market demand, actual hires or verified unique vacancies. Native Tableau acceptance checks are pending.',10)
        for i,(param,x,w) in enumerate([('Scope',1000,45000),('Role',47000,25000),('Geography view',73000,26000)],10):
            sub(layout,'zone',id=i,x=x,y=10000,w=w,h=4500,type_v2='paramctrl',mode='compact',param=f'[Parameters].[{param}]')
        if quality:
            positions=[('Classification audit',1000,17000,40000,25000),('Data coverage',43000,17000,56000,25000),('Skill detail counts',1000,44000,98000,44000)]
        else:
            positions=[('Selected records',1000,15500,26000,6500),('Skill coverage warning',28000,15500,71000,6500),
                ('Role records',1000,23500,48000,18000),('Role shares',51000,23500,48000,18000),
                ('Inherited skill percentages',1000,43500,48000,24000),('Location associations',51000,43500,48000,24000),
                ('Explicit seniority',1000,69500,48000,18500),('Data coverage',51000,69500,48000,18500)]
        for i,(sheet,x,y,w,h) in enumerate(positions,20):sub(layout,'zone',id=i,x=x,y=y,w=w,h=h,name=sheet)
        text_zone(layout,40,1000,89000,98000,4500,'Role shares use all four accepted roles in the chosen geography. Location associations are non-additive. Skill rates use populated inherited lists; n<10 comparisons are suppressed.',10)
        text_zone(layout,41,1000,93700,98000,5500,f'Global retained audit (not filtered): ambiguous {audit.get("ambiguous",0):,}; unclassified {audit.get("unclassified",0):,}; non-target {audit.get("out_of_scope",0):,}. Source: Luke Barousse data_jobs (Apache-2.0), pinned 2023 release. Salary amounts, trends and arrangement shares disabled. Local only; do not publish.',9)
        return d
    dashboard('Historical overview');dashboard('Coverage and classification',quality=True)
    windows=sub(workbook,'windows')
    for name in ['Historical overview','Coverage and classification']:
        w=sub(windows,'window',class_='dashboard',name=name,maximized='true')
        points=sub(w,'viewpoints')
        for sheet,*_ in specs:sub(sub(points,'viewpoint',name=sheet),'zoom',type='entire-view')
        sub(w,'active',id='-1')
    # Python cannot use `class` as a keyword; normalize this XML attribute once.
    for element in workbook.iter():
        if 'class-' in element.attrib:element.set('class',element.attrib.pop('class-'))
    E.indent(workbook,space='  ')
    twb=directory/'bay_area_2023_DRAFT.twb'
    E.ElementTree(workbook).write(twb,encoding='utf-8',xml_declaration=True)
    E.parse(twb)  # Syntax check only; no assertion about Tableau rendering.
    package=directory/'bay_area_2023_DRAFT.twbx'
    packaged=copy.deepcopy(workbook)
    packaged.find('.//connection').set('directory','Data')
    attribution='Derived aggregate exports from Luke Barousse data_jobs, Apache-2.0. Source revision '+manifest['source_revision']+'. Modified by project SQL aggregation and Phase 3 cleaning '+manifest['cleaning_rule_version']+'. Not original advertisements. LOCAL DRAFT; not published; native Tableau checks pending.\n'
    # Fixed ZIP timestamps make packaging reproducible; these are archive
    # metadata, not acquisition/posting dates. Source/run dates stay in manifests.
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
        def add(name,content):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,content)
        add('bay_area_2023_DRAFT.twb',E.tostring(packaged,encoding='utf-8',xml_declaration=True))
        add('Data/dashboard_metrics.csv',(data/'dashboard_metrics.csv').read_bytes())
        add('Data/ATTRIBUTION.txt',attribution)
        add('Data/LICENSE-2.0.txt',(root/'docs/data_licenses/Apache-2.0.txt').read_bytes())
    version=None
    app=Path('/Applications/Tableau Public (Apple silicon).app/Contents/Info.plist')
    if app.exists():version=plistlib.loads(app.read_bytes()).get('CFBundleShortVersionString')
    result={'status':'local_xml_draft_created_native_validation_pending','installed_tableau_public_version':version,
        'computer_use':'permissions_not_granted','native_open_render_filter_validation':False,
        'workbook_sha256':digest_file(twb),'package_sha256':digest_file(package),'export_content_sha256':manifest['content_sha256'],
        'worksheets':len(specs),'dashboards':2,'selectors':['Scope','Role','Geography view'],
        'joins':0,'publication_authorized':False,
        'package_contents':['bay_area_2023_DRAFT.twb','Data/dashboard_metrics.csv','Data/ATTRIBUTION.txt','Data/LICENSE-2.0.txt'],
        'checks_performed':['XML well-formedness','validated export hashes','known package members'],
        'pending':['Open workbook in installed Tableau','Resolve text connection/create local extract if prompted','Check all sheets and dashboard layouts','Run expected-versus-actual reconciliation','Save native workbook locally','Capture actual Tableau screenshots']}
    (root/'reports/phase5_workbook_status.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(create(),indent=2))
