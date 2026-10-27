"""Static Phase 4 figures built only from SQL tables already reconciled in pandas.

Artist-level assertions check that plotted bars/matrices match those tables. These
are explanatory research figures; no Tableau workbook or publication is created.
"""
from pathlib import Path
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from src.analysis import MIN_GROUP, records
from src.luke_dataset import digest_file

ROLE_ORDER = ['Data Analyst','Data Engineer','Data Scientist','Machine Learning Engineer']
SHORT = {'Data Analyst':'DA','Data Engineer':'DE','Data Scientist':'DS','Machine Learning Engineer':'ML'}
COLORS = dict(zip(ROLE_ORDER,['#247ba0','#33a47a','#8159a5','#d08a22']))
SOURCE = 'Luke Barousse data_jobs | pinned historical 2023 | accepted title-only Bay Area records'


def plot_figures(tables, output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    sns.set_theme(style='whitegrid',font_scale=.95)
    plt.rcParams.update({'figure.dpi':120,'savefig.dpi':160,'font.family':'DejaVu Sans'})
    manifest={}
    role=tables['role_summary'].set_index('role').reindex(ROLE_ORDER).dropna(subset=['records'])
    roles=role.index.tolist()
    total=int(role.records.sum())

    def finish(fig,name,table_names,data,footnote):
        # Wrap long caveats so source/coverage notes remain readable on export.
        caption=fig.text(.02,.015,SOURCE+'\n'+textwrap.fill(footnote,width=int(fig.get_figwidth()*17)),fontsize=8,va='bottom',color='#444444')
        fig.tight_layout(rect=(0,.10,1,.97))
        fig.canvas.draw()
        bounds=caption.get_window_extent(fig.canvas.get_renderer())
        if bounds.x0<0 or bounds.x1>fig.bbox.width or bounds.y0<0 or bounds.y1>fig.bbox.height:
            raise ValueError('Figure caption extends outside the canvas.')
        path=output/(name+'.png')
        fig.savefig(path,facecolor='white')
        plt.close(fig)
        manifest[name]={'file':str(path.name),'sha256':digest_file(path),
                        'sql_queries':table_names,'plotted_data':data,'artist_checks':'passed'}

    fig,ax=plt.subplots(figsize=(10,4.8))
    bars=ax.barh(roles,role.records,color=[COLORS[r] for r in roles])
    np.testing.assert_array_equal([b.get_width() for b in bars],role.records)
    for bar,(_,row) in zip(bars,role.iterrows()):
        ax.text(bar.get_width()+total*.004,bar.get_y()+bar.get_height()/2,
                f'{int(row.records):,} ({row.cohort_share_pct:.1f}%)',va='center',fontsize=10)
    ax.set_xlim(0,role.records.max()*1.27)
    ax.invert_yaxis();ax.set_xlabel('Retained records, counted once');ax.set_title(f'Role composition | accepted cohort n={total:,}',loc='left',weight='bold')
    audit=tables['cohort_audit'].set_index('role_status').records
    finish(fig,'phase4_role_composition',['role_summary','cohort_audit'],records(role.reset_index()[['role','records','cohort_share_pct']]),
           f'Outside denominator: ambiguous {int(audit.get("ambiguous",0)):,}; unclassified {int(audit.get("unclassified",0)):,}; non-target {int(audit.get("out_of_scope",0)):,}. Counts are not unique vacancies or hires.')

    fig,axes=plt.subplots(2,2,figsize=(12,8))
    plotted=[]
    for ax,r in zip(axes.flat,ROLE_ORDER):
        if r not in roles:
            ax.set_visible(False);continue
        row=role.loc[r]
        selected=tables['skill_by_role'].query('role == @r and comparison_allowed == 1 and tagged_records > 0').sort_values(['tagged_records','skill'],ascending=[False,True]).head(6).iloc[::-1]
        if selected.empty:
            ax.text(.5,.5,'Comparison suppressed: fewer than 10 usable lists',ha='center',transform=ax.transAxes)
        else:
            bars=ax.barh(selected.skill,selected.comparison_pct,color=COLORS[r])
            np.testing.assert_allclose([b.get_width() for b in bars],selected.comparison_pct)
            for b,(_,s) in zip(bars,selected.iterrows()):
                ax.text(b.get_width()+1,b.get_y()+b.get_height()/2,f'{int(s.tagged_records):,}/{int(s.usable_tag_records):,}',va='center',fontsize=8)
        ax.set_xlim(0,115);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('Tag presence among usable lists (%)')
        ax.set_title(f'{r}\nusable n={int(row.usable_tag_records):,}/{int(row.records):,} ({row.tag_coverage_pct:.1f}%)',fontsize=11)
        plotted.extend(records(selected))
    fig.suptitle('Most frequent inherited skill tags within each role',weight='bold',y=.99)
    finish(fig,'phase4_skill_profile',['skill_by_role','role_summary'],plotted,
           'Separate role denominators; missing lists are not zero skills. Top six per role, alphabetical ties. Tags are not verified requirements; rates can sum above 100%.')

    geo=tables['geography_by_role']
    city=geo.loc[geo.location_precision.eq('city')].groupby(['location_id','locality','role'],dropna=False).records.sum().reset_index()
    top=city.groupby(['location_id','locality']).records.sum().reset_index().sort_values(['records','locality'],ascending=[False,True]).head(10)
    city=city.merge(top[['location_id']],on='location_id')
    matrix=city.pivot(index='locality',columns='role',values='records').reindex(index=top.locality,columns=ROLE_ORDER).fillna(0)
    county=tables['county_by_role'].pivot(index='county',columns='role',values='records').reindex(columns=ROLE_ORDER).fillna(0)
    county=county.loc[county.sum(axis=1).sort_values(ascending=False).index]
    fig,axes=plt.subplots(1,2,figsize=(14,6))
    left=np.zeros(len(county))
    for r in ROLE_ORDER:
        bars=axes[0].barh(county.index,county[r],left=left,label=SHORT[r],color=COLORS[r])
        np.testing.assert_allclose([b.get_width() for b in bars],county[r])
        left+=county[r].to_numpy()
    axes[0].invert_yaxis();axes[0].set_title('County record memberships');axes[0].set_xlabel('Distinct records within each county');axes[0].legend(ncol=4,loc='lower right')
    labels=matrix.map(lambda x: f'{int(x):,}'+('*' if 0<x<MIN_GROUP else ''))
    sns.heatmap(matrix,annot=labels,fmt='',cmap='Blues',ax=axes[1],cbar_kws={'label':'Record memberships'})
    np.testing.assert_array_equal(np.asarray(axes[1].collections[0].get_array()).reshape(matrix.shape),matrix.to_numpy())
    axes[1].set_xticklabels([SHORT[r] for r in ROLE_ORDER],rotation=0);axes[1].set_xlabel('Accepted role');axes[1].set_ylabel('');axes[1].set_title('Ten cities with most accepted records')
    finish(fig,'phase4_geography',['geography_by_role','county_by_role'],{'cities':records(city),'counties':records(tables['county_by_role'])},
           'DA=Data Analyst; DE=Data Engineer; DS=Data Scientist; ML=Machine Learning Engineer. * cell n<10: descriptive count only. City/county totals are non-additive; communities excluded from city panel.')

    senior=tables['seniority_by_role']
    categories=['entry/junior','mid','senior','lead/staff/principal','management','mixed/conflicting','unknown']
    values=senior.pivot(index='role',columns='seniority',values='role_share_pct').reindex(index=roles,columns=categories).fillna(0)
    palette=['#2c9c78','#84c9ac','#286baa','#9464a8','#d0983f','#cf6f69','#c6cbd0']
    fig,ax=plt.subplots(figsize=(12,5.2));left=np.zeros(len(roles))
    for category,color in zip(categories,palette):
        bars=ax.barh(roles,values[category],left=left,color=color,label=category)
        np.testing.assert_allclose([b.get_width() for b in bars],values[category])
        left+=values[category].to_numpy()
    ax.set_xlim(0,100);ax.invert_yaxis();ax.set_xlabel('Share of accepted records in each role (%)')
    ax.set_yticks(range(len(roles)),[f'{r} (n={int(role.loc[r,"records"]):,})' for r in roles])
    ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.15),fontsize=8)
    ax.set_title('Explicit title-based seniority, with unknowns retained',loc='left',weight='bold')
    finish(fig,'phase4_seniority',['seniority_by_role','role_summary'],records(senior),
           'Unknown does not mean entry level. Numeric levels are not reclassified. Sparse categories are descriptive; exact counts and n<10 flags are in the analysis tables.')

    fig,ax=plt.subplots(figsize=(10,4.8));positions=np.arange(len(roles));height=.34
    for delta,column,label,color in [(-height/2,'tag_coverage_pct','Usable inherited tags','#247ba0'),(height/2,'derived_annual_coverage_pct','Derived annual value present (units unverified)','#b1b8be')]:
        bars=ax.barh(positions+delta,role[column],height,label=label,color=color)
        np.testing.assert_allclose([b.get_width() for b in bars],role[column])
    ax.set_yticks(positions,[f'{r} (n={int(role.loc[r,"records"]):,})' for r in roles]);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Percent of accepted role records');ax.legend(fontsize=8,loc='lower right')
    ax.set_title('Field coverage limits what can be compared',loc='left',weight='bold')
    finish(fig,'phase4_coverage',['role_summary'],records(role.reset_index()),
           'Salary bar shows field availability, not comparable advertised pay. Currency/provenance unresolved: salary comparisons disabled. Work arrangement is unknown for every accepted record.')

    fig,axes=plt.subplots(1,3,figsize=(13,5));plotted=[]
    for ax,skill in zip(axes,['python','sql','tableau']):
        sub=tables['skill_by_role'].query('skill == @skill').set_index('role').reindex(roles)
        lower=sub.all_record_lower_pct.to_numpy();upper=sub.all_record_upper_pct.to_numpy()
        ax.hlines(np.arange(len(roles)),lower,upper,color='#247ba0',linewidth=6,alpha=.55)
        conditional=pd.to_numeric(sub.comparison_pct,errors='raise').to_numpy(dtype=float)
        points=ax.scatter(conditional,np.arange(len(roles)),color='#262626',s=25,zorder=3)
        np.testing.assert_allclose(np.ma.filled(points.get_offsets()[:,0],np.nan),conditional,equal_nan=True)
        segments=ax.collections[0].get_segments()
        np.testing.assert_allclose([s[:,0] for s in segments],np.column_stack([lower,upper]))
        ax.set_yticks(range(len(roles)),[f'{SHORT[r]}: n={int(sub.loc[r,"usable_tag_records"]):,}/{int(sub.loc[r,"role_records"]):,}' for r in roles])
        ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Percent (%)');ax.set_title({'python':'Python','sql':'SQL','tableau':'Tableau'}[skill])
        plotted.extend(records(sub.reset_index()))
    fig.suptitle('Missing-tag sensitivity: logical ranges, not confidence intervals',weight='bold')
    finish(fig,'phase4_missingness_sensitivity',['skill_by_role'],plotted,
           'Blue range: all accepted records if every unavailable list lacks/has the tag. Dot: conditional rate among usable lists. Extraction errors are outside these bounds; no population inference.')

    summary=tables['skill_count_summary'].set_index('role').reindex(roles).dropna(subset=['usable_tag_records'])
    fig,ax=plt.subplots(figsize=(11,5));boxes=[]
    for r,row in summary.iterrows():
        boxes.append(dict(label=f'{r}\nusable n={int(row.usable_tag_records):,}',q1=row.q1_tags,med=row.median_tags,q3=row.q3_tags,whislo=row.min_tags,whishi=row.max_tags,mean=row.mean_tags,fliers=[]))
    artists=ax.bxp(boxes,vert=False,showmeans=True,patch_artist=True)
    for i,(r,row) in enumerate(summary.iterrows()):
        artists['boxes'][i].set_facecolor(COLORS[r]);artists['boxes'][i].set_alpha(.55)
        np.testing.assert_allclose(artists['medians'][i].get_xdata(),[row.median_tags,row.median_tags])
    ax.set_xlabel('Distinct inherited tags per populated record');ax.set_title('Tag-count distributions among usable records',loc='left',weight='bold');ax.invert_yaxis()
    finish(fig,'phase4_tag_count_distribution',['skill_count_summary'],records(summary.reset_index()),
           'Boxes: Q1/median/Q3; whiskers: observed min/max (not 1.5×IQR); triangle: mean. Linear-interpolated quantiles. Missing lists excluded, never assigned zero.')
    return manifest
