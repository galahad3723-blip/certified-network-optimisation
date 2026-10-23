"""Paired summaries and publication-style figures for the fixed CPU study."""
from pathlib import Path
import json
from certified_num import NUM
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT=Path(__file__).resolve().parent;R=ROOT/'results';F=ROOT/'figures'
COLORS={'cold':'#596774','warm':'#d27835','ray_warm':'#8c67a3','reuse':'#168783'}
LABELS={'cold':'Cold prices','warm':'Warm prices','ray_warm':'Ray warm start','reuse':'Certified reuse'}
SHOCKS=['uniform_10','uniform_30','local_30','heterogeneous_30']
SHOCK_LABELS=['Uniform 10%','Uniform 30%','Local 30%','Heterogeneous 30%']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.grid':True,'axes.axisbelow':True,
                     'grid.color':'#e4e8eb','grid.linewidth':.55,'legend.frameon':False,
                     'savefig.facecolor':'white','figure.facecolor':'white'})


def save(fig,name):
    F.mkdir(exist_ok=True)
    fig.savefig(F/(name+'.png'),dpi=300,bbox_inches='tight',pad_inches=.08)
    fig.savefig(F/(name+'.pdf'),bbox_inches='tight',pad_inches=.08)
    plt.close(fig)


def cluster_interval(frame,column,nboot=10000):
    groups=[g[column].to_numpy() for _,g in frame.groupby('topology')]
    rng=np.random.default_rng(20261022)
    boot=np.empty(nboot)
    for i in range(nboot):
        sampled=rng.integers(0,len(groups),len(groups))
        boot[i]=np.median(np.concatenate([groups[j] for j in sampled]))
    return np.percentile(boot,[2.5,97.5]).tolist()


def main():
    runs=pd.read_csv(R/'runs.csv');cases=pd.read_csv(R/'cases.csv');anchors=pd.read_csv(R/'anchors.csv')
    env=json.loads((R/'environment.json').read_text())
    assert len(runs)==env['runs'] and len(cases)==env['cases'] and len(anchors)==env['anchors']
    assert not runs[['seconds','amortized_seconds','gap_per_weight']].isna().any().any()
    invariant=runs.groupby(['case','method'])['fg_evaluations'].nunique()
    assert invariant.max()==1
    summary_runs=runs.groupby(['case','method'],as_index=False).agg(
        seconds=('seconds','median'),amortized_seconds=('amortized_seconds','median'),
        converged=('converged','all'),fg_evaluations=('fg_evaluations','first'),
        gap=('gap_per_weight','max'),skipped=('skipped','all'),precheck_seconds=('precheck_seconds','median'))
    joined=summary_runs.merge(cases[['case','anchor','split','topology','seed','d','xi','capacity_family','shock']],on='case')
    anchor_cost=anchors.set_index('anchor').anchor_seconds
    nupdates=cases.groupby('anchor').size()
    joined['with_anchor_seconds']=joined.amortized_seconds+joined.anchor.map(anchor_cost)/joined.anchor.map(nupdates)
    joined.to_csv(R/'per_case_methods.csv',index=False)
    core=joined[joined.split=='core'];cc=cases[cases.split=='core']
    table=[]
    for method,g in core.groupby('method'):
        success=g[g.converged]
        table.append({'method':method,'cases':len(g),'solved':int(g.converged.sum()),
                      'median_online_ms_all_budget':float(1000*g.seconds.median()),
                      'median_amortized_ms_all_budget':float(1000*g.amortized_seconds.median()),
                      'median_success_ms':float(1000*success.amortized_seconds.median()),
                      'median_fg_all':float(g.fg_evaluations.median()),
                      'skipped':int(g.skipped.sum())})
    paired={};stratified={}
    for other in ['cold','warm','ray_warm']:
        pair=core[core.method=='reuse'].merge(core[core.method==other],on='case',suffixes=('_reuse','_other'))
        valid=pair[pair.converged_reuse & pair.converged_other].copy()
        valid['time_ratio']=valid.amortized_seconds_reuse/valid.amortized_seconds_other
        valid['with_anchor_ratio']=valid.with_anchor_seconds_reuse/valid.with_anchor_seconds_other
        valid['topology']=valid.topology_reuse
        valid[['case','topology','time_ratio','with_anchor_ratio']].to_csv(R/('paired_reuse_'+other+'.csv'),index=False)
        paired[other]={'common_solved_cases':len(valid),'total_cases':len(pair),
                       'median_time_ratio':float(valid.time_ratio.median()),
                       'ratio_cluster_ci':cluster_interval(valid,'time_ratio'),
                       'median_ratio_with_anchor':float(valid.with_anchor_ratio.median()),
                       'fraction_faster':float((valid.time_ratio<1).mean())}
        masks={
            'excluding_known_uniform':~((valid.xi_reuse==0)&valid.shock_reuse.str.startswith('uniform')),
            'nonuniform':~valid.shock_reuse.str.startswith('uniform'),
            'shifted_only':valid.xi_reuse>0,
        }
        for name,mask in masks.items():
            subset=valid[mask]
            stratified.setdefault(name,{})[other]={
                'common_solved_cases':len(subset),
                'median_time_ratio':float(subset.time_ratio.median()),
                'ratio_cluster_ci':cluster_interval(subset,'time_ratio'),
                'fraction_faster':float((subset.time_ratio<1).mean())}
    coverage=[]
    for (shock,xi,family),g in cc.groupby(['shock','xi','capacity_family']):
        coverage.append({'shock':shock,'xi':xi,'capacity_family':family,'cases':len(g),
                         'acceptances':int(g['accept_0.001'].sum()),
                         'fixed_acceptances':int((g.fixed_price_gap<=1e-3).sum())})
    sensitivity=[]
    for tol in [1e-4,1e-3,1e-2]:
        label=f'{tol:g}'
        for shock,g in cc.groupby('shock'):
            accepted=g['accept_'+label].to_numpy()
            good=g['actual_good_'+label].to_numpy()
            definitely_poor=g.actual_regret_lower.to_numpy()>tol
            sensitivity.append({'tolerance':tol,'shock':shock,'cases':len(g),
                                'accepted':int(accepted.sum()),'reference_good':int(good.sum()),
                                'reference_good_rejected':int((good&~accepted).sum()),
                                'false_acceptances_observed':int((accepted&definitely_poor).sum()),
                                'unresolved_reference_cases':int((~good&~definitely_poor).sum())})
    failure_rows=runs[~runs.converged]
    summary={'core_cases':len(cc),'scaling_cases':int((cases.split=='scaling').sum()),
             'raw_timing_runs':len(runs),'anchors':len(anchors),'topology_families':int(cc.topology.nunique()),
             'method_table':table,'paired_timing':paired,'stratified_pairing':stratified,'coverage_cells':coverage,
             'tolerance_sensitivity':sensitivity,'reference_misses':env['reference_misses'],
             'maximum_reference_gap':float(cases.reference_gap.max()),
             'maximum_overload':float(cases.overload.max()),'failed_measured_runs':len(failure_rows),
             'failed_measured_cases':failure_rows[['case','method']].drop_duplicates().to_dict('records'),
             'reuse_acceptances_core':int(cc['accept_0.001'].sum()),
             'fixed_acceptances_core':int((cc.fixed_price_gap<=1e-3).sum()),
             'known_scaling_acceptances':int(cc[(cc.xi==0)&cc.shock.str.startswith('uniform')]['accept_0.001'].sum()),
             'known_scaling_cases':len(cc[(cc.xi==0)&cc.shock.str.startswith('uniform')]),
             'cache_preparation_ms_median':float(1000*anchors.cache_preparation_seconds.median()),
             'source_solve_ms_median':float(1000*anchors.anchor_seconds.median()),
             'qualifications':'paired median ratios, six topology clusters, CPU-only, synthetic capacities and no SOTA superiority claim'}
    (R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(7.4,2.9))
    amplitude=np.linspace(0,.25,80);theta=.3+amplitude[:,None]*np.cos(np.linspace(0,2*np.pi,40,endpoint=False))
    s=.7;z=s+(1-s)*theta
    jensen=np.log(z.mean(axis=1))-np.log(z).mean(axis=1)
    variance=(1-s)**2*theta.var(axis=1)/(2*s*s)
    axs[0].plot(theta.std(axis=1),jensen,color='#168783',label='Exact regret and Jensen bound')
    axs[0].plot(theta.std(axis=1),variance,'--',color='#d27835',label='Variance upper bound')
    axs[0].set(xlabel='Standard deviation of shift fractions',ylabel='Regret per total weight',title='One-link sharpness family')
    axs[0].legend(fontsize=7)
    r=np.logspace(-5,0,100);gap=.5*np.log((1+r)**2/(4*r))
    axs[1].plot(r,gap,color='#8c67a3',label='Best price-ray certificate')
    axs[1].plot(r,np.zeros_like(r),color='#168783',label='Actual regret of repaired optimum')
    axs[1].set(xlabel='Capacity ratio on the changed link',ylabel='Gap per total weight',xscale='log',title='Two-link limitation')
    axs[1].legend(fontsize=7)
    fig.tight_layout();save(fig,'01_theory_and_counterexample')
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.3))
    columns=[(0.,'load_coupled'),(0.,'independent'),(.5,'load_coupled'),(.5,'independent')]
    for ax,field,title in zip(axs,['fixed_acceptances','acceptances'],['Unchanged anchor prices','Best cached price ray']):
        values=np.array([[next(v for v in coverage if v['shock']==sh and v['xi']==xi and v['capacity_family']==fam)[field]/36 for xi,fam in columns] for sh in SHOCKS])
        ax.imshow(values,vmin=0,vmax=1,cmap='YlGnBu',aspect='auto')
        ax.set_xticks(range(4),['ξ=0\nload','ξ=0\nindep.','ξ=.5\nload','ξ=.5\nindep.'],fontsize=8)
        ax.set_yticks(range(4),SHOCK_LABELS if ax is axs[0] else [])
        ax.set_title(title,fontsize=10)
        for i in range(4):
            for j in range(4):ax.text(j,i,f'{100*values[i,j]:.0f}%',ha='center',va='center',color='white' if values[i,j]>.5 else 'black',fontsize=9)
        ax.grid(False)
    fig.tight_layout();save(fig,'02_certificate_coverage')
    fig,ax=plt.subplots(figsize=(7.1,3.65))
    palette=['#34495e','#d27835','#8c67a3','#168783']
    for sh,label,color in zip(SHOCKS,SHOCK_LABELS,palette):
        g=cc[cc.shock==sh]
        ax.scatter(np.maximum(1e-10,g.actual_regret_upper),np.maximum(1e-10,g.precheck_gap),s=14,alpha=.55,color=color,label=label)
    ax.axhline(1e-3,color='#aaaaaa',linestyle='--');ax.axvline(1e-3,color='#aaaaaa',linestyle='--')
    ax.plot([1e-10,1],[1e-10,1],color='#aaaaaa',linestyle=':',linewidth=.8)
    ax.set(xscale='log',yscale='log',xlabel='Regret upper bound from tight updated reference',ylabel='Cached price-ray gap per total weight')
    ax.legend(fontsize=8,loc='upper left')
    fig.tight_layout();save(fig,'03_certificate_conservatism')
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.1))
    for ax,column,title in zip(axs,['amortized_seconds','with_anchor_seconds'],['Online time with cache preparation','Time including amortised anchor solve']):
        times=core.pivot(index='case',columns='method',values=column)
        success=core.pivot(index='case',columns='method',values='converged')
        costs=times.where(success,np.inf)
        fastest=costs.min(axis=1)
        relative=costs.div(fastest,axis=0).fillna(np.inf)
        finite=relative.to_numpy()[np.isfinite(relative.to_numpy())]
        maximum=max(1.01,min(100,float(finite.max()))) if finite.size else 100.
        grid=np.geomspace(1,maximum+1e-9,250)
        for method in LABELS:
            ratios=relative[method].to_numpy()
            ax.plot(grid,[(ratios<=v).mean() for v in grid],color=COLORS[method],label=LABELS[method])
        ax.set(xscale='log',xlabel='Runtime / fastest method on same case',title=title,ylim=(-.02,1.03))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    axs[0].set_ylabel('Fraction of core cases')
    axs[1].legend(fontsize=7,loc='lower right')
    fig.tight_layout();save(fig,'04_runtime_profiles')
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.1),sharey=True)
    for ax,tname in zip(axs,['Abilene','Cogentco']):
        g=joined[(joined.split=='scaling')&(joined.topology==tname)]
        for method in LABELS:
            z=g[g.method==method].groupby('d').amortized_seconds
            xx=np.array(sorted(z.groups));med=z.median().reindex(xx).to_numpy()*1000
            lo=z.quantile(.25).reindex(xx).to_numpy()*1000;hi=z.quantile(.75).reindex(xx).to_numpy()*1000
            ax.plot(xx,med,'o-',color=COLORS[method],label=LABELS[method],markersize=4)
            ax.fill_between(xx,lo,hi,color=COLORS[method],alpha=.10)
        ax.set(xscale='log',yscale='log',xlabel='Number of flows',title=tname)
    axs[0].set_ylabel('Median amortised online time (ms)')
    axs[1].legend(fontsize=7)
    fig.tight_layout();save(fig,'05_scaling')
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.0))
    for sh,label,color in zip(SHOCKS,SHOCK_LABELS,palette):
        rr=sorted([z for z in sensitivity if z['shock']==sh],key=lambda z:z['tolerance'])
        xx=[z['tolerance'] for z in rr]
        axs[0].plot(xx,[z['accepted']/z['cases'] for z in rr],'o-',color=color,label=label)
        axs[1].plot(xx,[z['reference_good_rejected']/max(1,z['reference_good']) for z in rr],'o-',color=color,label=label)
    for ax in axs:
        ax.set(xscale='log',xlabel='Gap tolerance per total weight',ylim=(-.03,1.03))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    axs[0].set_ylabel('Accepted for certified reuse')
    axs[1].set_ylabel('Reference-good candidates rejected')
    axs[0].legend(fontsize=7)
    fig.tight_layout();save(fig,'06_tolerance_sensitivity')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
