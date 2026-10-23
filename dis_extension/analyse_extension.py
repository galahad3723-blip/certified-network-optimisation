"""Analyse held-out paired replays and produce standalone scientific figures."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE/'results'; FIG=HERE/'figures'
METHODS=['ray_warm','ray_reuse','always_refine','heuristic','train_best','learned']
LABELS={'ray_warm':'Ray warm start','ray_reuse':'Original reuse','always_refine':'Always refine',
        'heuristic':'Capacity heuristic','train_best':'Training best fixed','learned':'Learned selector'}
COLORS={'ray_warm':'#687886','ray_reuse':'#969EA5','always_refine':'#AD7652',
        'heuristic':'#9780AB','train_best':'#718CAF','learned':'#177C80'}
SHOCK_LABELS={'uniform_10':'Uniform cut 10%','uniform_30':'Uniform cut 30%',
              'local_30':'Local cut 30%','heterogeneous_30':'Cuts up to 30%',
              'local_05':'Local cut 5%','local_50':'Local cut 50%',
              'heterogeneous_60':'Cuts up to 60%','mixed_recovery':'Loss and recovery'}


def paired(group,reference):
    values=group.merge(reference[['case','seconds']],on='case',suffixes=('','_reference'),validate='one_to_one')
    ratio=values.seconds/values.seconds_reference
    return {'cases':len(values),'median_ratio':float(ratio.median()),
            'mean_ratio':float(ratio.mean()),'total_time_ratio':float(values.seconds.sum()/values.seconds_reference.sum()),
            'p90_ratio':float(ratio.quantile(.9)), 'win_fraction':float((ratio<1).mean())}


def bootstrap(values,reference):
    data=values.merge(reference[['case','seconds']],on='case',suffixes=('','_reference'))
    groups=sorted(data.topology.unique()); arrays=[(g.seconds/g.seconds_reference).values for _,g in data.groupby('topology',sort=True)]
    rng=np.random.default_rng(20261023); samples=[]
    for _ in range(10000):
        chosen=rng.integers(0,len(groups),len(groups))
        samples.append(float(np.median(np.concatenate([arrays[i] for i in chosen]))))
    return np.quantile(samples,[.025,.975]).tolist()


def save(name):
    plt.savefig(FIG/(name+'.png'),dpi=220,bbox_inches='tight')
    plt.savefig(FIG/(name+'.pdf'),bbox_inches='tight')
    plt.close()


def main():
    runs=pd.read_csv(OUT/'replay_runs.csv')
    assert len(runs)==768*6*3
    assert not runs.duplicated(['case','method','repeat']).any()
    assert runs.groupby(['case','method']).size().eq(3).all()
    med=runs.groupby(['dataset','case','topology','d','xi','shock','method'],as_index=False).agg(
        seconds=('seconds','median'),amortized_seconds=('amortized_seconds','median'),
        gap=('verified_gap','max'),overload=('overload','max'),
        converged=('converged','all'),precheck=('precheck_certified','all'),
        light=('light_certified','all'),chose_refinement=('chose_refinement','all'),
        feature_seconds=('feature_seconds','median'),prediction_seconds=('prediction_seconds','median'),
        refinement_evaluations=('refinement_evaluations','median'),fg_evaluations=('fg_evaluations','median'))
    assert med.groupby('case').size().eq(6).all()
    med.to_csv(OUT/'replay_medians.csv',index=False)
    summary={'timing_records':len(runs),'core_cases':576,'shift_cases':192,'total_cases':768,
             'failed_runs':int((~runs.converged).sum()),'maximum_overload':float(runs.overload.max()),
             'maximum_accepted_gap':float(runs.loc[runs.converged,'verified_gap'].max()),
             'methods':{},'paired':{},'rejected_paired':{},'common_success_paired':{},
             'by_topology':{},'by_shock':{},'by_size':{}}
    for dataset,sub in med.groupby('dataset'):
        summary['methods'][dataset]={};summary['paired'][dataset]={};summary['by_topology'][dataset]={};summary['by_shock'][dataset]={};summary['by_size'][dataset]={}
        original=sub[sub.method=='ray_reuse']; warm=sub[sub.method=='ray_warm']; fixed=sub[sub.method=='train_best']
        rejected_cases=set(original.loc[~original.precheck,'case'])
        summary['rejected_paired'][dataset]={}
        common_success=set(sub.groupby('case').converged.all().loc[lambda x:x].index)
        summary['common_success_paired'][dataset]={}
        for method,g in sub.groupby('method'):
            summary['methods'][dataset][method]={'cases':len(g),'median_ms':float(1000*g.seconds.median()),
                'total_seconds':float(g.seconds.sum()),'solved':int(g.converged.sum()),
                'precheck_certified':int(g.precheck.sum()),'light_certified':int(g.light.sum()),
                'refinement_choices':int(g.chose_refinement.sum()),
                'median_feature_us':float(g.feature_seconds.median()*1e6),
                'median_prediction_us':float(g.prediction_seconds.median()*1e6)}
            summary['paired'][dataset][method]={'vs_reuse':paired(g,original),'vs_ray_warm':paired(g,warm),'vs_train_best':paired(g,fixed)}
            summary['paired'][dataset][method]['vs_reuse']['topology_bootstrap_interval']=bootstrap(g,original)
            selected=g[g.case.isin(rejected_cases)]
            summary['rejected_paired'][dataset][method]={
                'vs_reuse':paired(selected,original),
                'vs_ray_warm':paired(selected,warm),
                'vs_train_best':paired(selected,fixed)}
            summary['common_success_paired'][dataset][method]=paired(
                g[g.case.isin(common_success)],original)
        learned=sub[sub.method=='learned']
        for topo,g in learned.groupby('topology'):
            ref=original[original.topology==topo]
            summary['by_topology'][dataset][topo]=paired(g,ref)
        for shock,g in learned.groupby('shock'):
            summary['by_shock'][dataset][shock]=paired(g,original[original.shock==shock])
        for size,g in learned.groupby('d'):
            summary['by_size'][dataset][str(size)]=paired(g,original[original.d==size])
    folds=json.loads((OUT/'fold_models.json').read_text())
    summary['folds']={name:{'kind':r['model']['kind'],'spec':r['selection']['spec'],
                          'threshold':r['selection']['threshold'],'train_best_refines':r['train_best']['refine']}
                      for name,r in folds.items()}
    summary['training_seconds']=json.loads((OUT/'training_environment.json').read_text())['training_seconds']
    summary['inference_overhead_rejected_us']={dataset:float(g.loc[~g.precheck,'feature_seconds'].add(g.loc[~g.precheck,'prediction_seconds']).median()*1e6)
        for dataset,g in med[med.method=='learned'].groupby('dataset')}
    summary['scope']='Nested topology-held-out results on six convenience families; bootstrap intervals are descriptive, with no population coverage or independent test-set claim. Shift cases use unseen shock distributions but reuse nominal test anchors.'
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    runs.loc[~runs.converged].to_csv(OUT/'failed_replay_runs.csv',index=False)
    FIG.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':13,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120})
    fig,axes=plt.subplots(1,2,figsize=(10,3.9),sharey=True)
    for ax,dataset,title in zip(axes,['core','shift'],['Core workload','New shock regimes']):
        stats=summary['paired'][dataset]
        for j,method in enumerate(METHODS):
            s=stats[method]['vs_reuse'];lo,hi=s['topology_bootstrap_interval'];v=s['median_ratio']
            ax.errorbar(v,j,xerr=[[max(0,v-lo)],[max(0,hi-v)]],fmt='o',color=COLORS[method],capsize=3)
        ax.axvline(1,color='#606060',ls='--',lw=1);ax.set_title(title);ax.set_xlabel('Paired runtime / original reuse')
        ax.grid(axis='x',alpha=.18)
    axes[0].set_yticks(range(6),[LABELS[m] for m in METHODS]);axes[0].invert_yaxis()
    fig.tight_layout();save('01_held_out_runtime')
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    for ax,dataset,title in zip(axes,['core','shift'],['Core workload','Shifted capacity workload']):
        for j,method in enumerate(['ray_reuse','always_refine','learned']):
            s=summary['methods'][dataset][method]
            ax.bar(j,s['precheck_certified'],color='#A5B3BC')
            ax.bar(j,s['light_certified'],bottom=s['precheck_certified'],color=COLORS['learned'])
        ax.set_xticks(range(3),['Original','Always refine','Learned']);ax.set_title(title)
        ax.set_ylabel('Cases certified before full L-BFGS-B');ax.grid(axis='y',alpha=.15)
    axes[0].bar(0,0,color='#A5B3BC',label='Initial certificate')
    axes[0].bar(0,0,color=COLORS['learned'],label='After lightweight update');axes[0].legend(fontsize=11)
    fig.tight_layout();save('02_certificate_coverage')
    fig,ax=plt.subplots(figsize=(8.5,3.6))
    names=sorted(summary['by_topology']['core']); y=np.arange(len(names))
    for offset,dataset,color,label in [(-.12,'core','#177C80','Core'),(.12,'shift','#AD7652','Shifted shocks')]:
        ax.scatter([summary['by_topology'][dataset][n]['median_ratio'] for n in names],y+offset,color=color,label=label,s=40)
    ax.axvline(1,color='#606060',ls='--',lw=1);ax.set_yticks(y,names);ax.invert_yaxis()
    ax.set_xlabel('Learned selector runtime / original reuse');ax.legend();ax.grid(axis='x',alpha=.18)
    fig.tight_layout();save('03_topology_transfer')
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    for ax,dataset,title in zip(axes,['core','shift'],['Core shock types','Shifted shock types']):
        records=summary['by_shock'][dataset];names=list(records)
        ax.barh([SHOCK_LABELS.get(n,n) for n in names],
                [records[n]['median_ratio'] for n in names],color='#177C80')
        ax.axvline(1,color='#505050',ls='--',lw=1);ax.set_title(title);ax.set_xlabel('Learned runtime / original reuse')
        ax.grid(axis='x',alpha=.18)
    fig.tight_layout();save('04_shock_transfer')
    print(json.dumps({k:summary[k] for k in ['timing_records','core_cases','shift_cases','failed_runs','maximum_overload']},indent=2))
    print(json.dumps({d:summary['paired'][d]['learned'] for d in ['core','shift']},indent=2))


if __name__=='__main__':
    main()
