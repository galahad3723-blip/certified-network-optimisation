"""Frozen-policy validation on new graph structures and BLAS thread settings."""
from pathlib import Path
import os
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'
import argparse
import hashlib
import json
import platform
import sys
import time
import numpy as np
import pandas as pd
import scipy
from scipy import sparse
from threadpoolctl import threadpool_info, threadpool_limits
from certified_updates import NUM, TARGET, FEATURES, make_cache, features, predict, run_action, solve
from experiment import check_result
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from certified_num import topology, routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'transfer_results'
DATA=HERE/'data_external'
GRAPHS=['Dfn','Garr201201','Surfnet','BtEurope']
SEEDS=[1701,1907]
SIZES=[1000,10000]
FAMILIES=['load_coupled','independent']
SHIFTS=[0.,.5]
SHOCKS=['uniform_10','local_30','heterogeneous_30','mixed_recovery']
CONFIGURATIONS=[1,4]
METHODS=['ray_warm','ray_reuse','always_refine','heuristic','train_best','learned']
LABELS=['Ray warm start','Original reuse','Always refine','Capacity rule','Training fixed','Frozen learner']
REPEATS=3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_paths():
    return [Path(__file__),HERE/'certified_updates.py',HERE/'experiment.py',ROOT/'certified_num.py',
            HERE/'results/deployment_model.json',HERE/'results/action_runs.csv',HERE/'results/features.csv',
            DATA/'SOURCE_MANIFEST.json']+[DATA/(n+'.graphml') for n in GRAPHS]


def check_frozen():
    protocol=json.loads((OUT/'protocol.json').read_text())
    for relative,digest in protocol['source_sha256'].items():
        assert sha(HERE/relative)==digest,relative
    return protocol


def freeze():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'protocol.json').exists(),'Do not overwrite a frozen protocol'
    old=pd.read_csv(HERE/'results/features.csv')
    assert set(GRAPHS).isdisjoint(old.topology)
    times=pd.read_csv(HERE/'results/action_runs.csv').groupby(['case','method']).seconds.median().unstack()
    rejected=old[old.precheck_gap>TARGET].case
    ratio=float((times.loc[rejected,'always_refine']/times.loc[rejected,'ray_reuse']).mean())
    deployment=json.loads((HERE/'results/deployment_model.json').read_text())
    policy={'model':deployment['model'],'training_fixed':{'kind':'constant','refine':ratio<1.},
            'training_fixed_mean_ratio':ratio,'fitting_source':'Original six-topology core action observations only',
            'training_topologies':sorted(old.topology.unique()),'training_cases':576,'modelled_rejected_cases':360}
    (OUT/'policy_snapshot.json').write_text(json.dumps(policy,indent=2)+'\n')
    record={
        'frozen_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'chronology':'The earlier 768-case study, including its unfavourable learner-to-rule comparison, motivated this follow-up. These four graphs were chosen by identity and size without inspecting their new action outcomes. The previously exported all-core deployment model is frozen; no retraining or threshold selection uses new data.',
        'question':'Does the frozen learned selector add net computational value over the simple capacity rule on previously unused graphs and a different BLAS thread setting?',
        'graphs':GRAPHS,'route_seeds':SEEDS,'sizes':SIZES,'capacity_families':FAMILIES,'utility_shifts':SHIFTS,
        'anchors':64,'cases':256,'shocks':SHOCKS,'repeats':REPEATS,'methods':METHODS,
        'blas_thread_settings':CONFIGURATIONS,'timing_records':9216,'target':TARGET,'reference_target':1e-7,
        'workload':'Same lognormal mean-one weights and two nominal-capacity laws as the earlier study; all nominal arrays and routes freshly generated. Local shocks reduce ceil(5% of used links) by 30%; heterogeneous factors uniform in [0.7,1]; recovery factors uniform in [0.8,1.2].',
        'primary_comparison':'Frozen learner versus capacity rule; report paired median and sum-of-case-medians ratios, failures and common-success subset separately for each thread setting.',
        'secondary_comparisons':'All six pipelines relative to the capacity rule, and learner-to-rule by graph and size. No population confidence claim from four convenience-selected graph structures.',
        'diagnostic':'Hindsight best-of-two action times and the possible extra-overhead budget relative to the measured capacity rule. Uses test timings only for diagnosis, never for online selection. It is an optimistic observed comparator, not a deployable policy or an expected-runtime lower-bound theorem.',
        'measurement':'One machine. Configurations 1 and 4 alternate in order across cases; all loaded BLAS pools are verified at the requested limit. Within each configuration methods rotate across three repeats. Context switching and data loading are outside online timers; features, prediction, update, certificates and fallback are charged. Same nominal cache for every pipeline.',
        'independence':'No graph identity, nominal anchor or route matrix overlaps the six training graph identities. The four additional structures still come from the same Topology Zoo collection, may share geographical context, and are not independent random draws or measured production traffic. Thread settings are not different hardware.',
        'failure_handling':'All numerical outcomes and iteration-cap failures retained. Reference misses retained and disclosed. No output accepted without its actual certificate.',
        'policy_snapshot_sha256':sha(OUT/'policy_snapshot.json'),
        'source_sha256':{os.path.relpath(p,HERE):sha(p) for p in source_paths()}}
    (OUT/'protocol.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'protocol_frozen':True,'anchors':64,'cases':256,'timings':9216,'training_fixed_refines':ratio<1.},indent=2),flush=True)


def load_instance(key):
    with np.load(OUT/'instances'/(key+'.npz'),allow_pickle=False) as z:
        data={n:z[n] for n in z.files}
    A=sparse.csr_matrix((data['A_data'],data['A_indices'],data['A_indptr']),shape=tuple(data['A_shape']))
    model=NUM(A,data['w'],data['xi'])
    return model,make_cache(model,data['c0'],data['anchor_x'],data['anchor_lam']),data


def prepare():
    check_frozen()
    assert not (OUT/'cases.csv').exists(),'Do not overwrite generated instances'
    folder=OUT/'instances';folder.mkdir(exist_ok=True)
    anchors=[];cases=[];route_cache={};began=time.perf_counter()
    for ti,name in enumerate(GRAPHS):
        n,edges,info=topology(DATA/(name+'.graphml'))
        for seed in SEEDS:
            for d in SIZES:
                A,directed=routing(n,edges,d,seed)
                for family in FAMILIES:
                    for xi in SHIFTS:
                        key=f'transfer_{name}_{seed}_{d}_{family}_xi{xi:g}'
                        rng=np.random.default_rng(np.random.SeedSequence([20261023,ti,seed,d]))
                        w=np.exp(rng.normal(0,.5,d));w/=w.mean()
                        offered=np.asarray(A@np.ones(d)).ravel()
                        c0=(.8*offered*rng.uniform(.7,1.3,len(offered)) if family=='load_coupled'
                            else .8*offered.mean()*np.exp(rng.normal(0,.7,len(offered))))
                        model=NUM(A,w,np.full(d,xi))
                        anchor=solve(model,c0,np.full(model.m,.2),1e-7,refine=True)
                        cache=make_cache(model,c0,anchor['x'],anchor['lam'])
                        local=c0.copy();chosen=rng.choice(model.m,max(1,int(np.ceil(.05*model.m))),replace=False)
                        local[chosen]*=.7
                        updates={'uniform_10':.9*c0,'local_30':local,
                                 'heterogeneous_30':c0*rng.uniform(.7,1,model.m),
                                 'mixed_recovery':c0*rng.uniform(.8,1.2,model.m)}
                        arrays={'A_data':A.data,'A_indices':A.indices,'A_indptr':A.indptr,'A_shape':np.asarray(A.shape),
                                'directed_edges':directed,'w':w,'xi':model.xi,'c0':c0,
                                'anchor_x':anchor['x'],'anchor_lam':anchor['lam']}
                        meta={'anchor':key,'topology':name,'seed':seed,'d':d,'capacity_family':family,'xi':xi}
                        anchors.append({**meta,'used_links':model.m,'nnz':A.nnz,'graph_nodes':n,
                                        'anchor_gap':anchor['gap_per_weight'],'anchor_converged':anchor['converged'],
                                        'anchor_status':anchor['status']})
                        for shock,c in updates.items():
                            reference=solve(model,c,anchor['lam'],1e-7,anchor['x'],refine=True)
                            query=cache.query(c,anchor['x'])
                            z=features(model,cache,c0,c,anchor['lam'],query)
                            cases.append({**meta,'case':key+'_'+shock,'shock':shock,'precheck_gap':query['gap_per_weight'],
                                          'reference_gap':reference['gap_per_weight'],'reference_converged':reference['converged'],
                                          'reference_status':reference['status'],**dict(zip(FEATURES,z))})
                            arrays[shock+'_c']=c;arrays[shock+'_reference_x']=reference['x'];arrays[shock+'_reference_lam']=reference['lam']
                        np.savez_compressed(folder/(key+'.npz'),**arrays)
                        pd.DataFrame(anchors).to_csv(OUT/'anchors.csv',index=False)
                        pd.DataFrame(cases).to_csv(OUT/'cases.csv',index=False)
                        if len(anchors)%8==0:print(f'New-graph preparation {len(anchors)}/64 anchors, {len(cases)}/256 cases, {time.perf_counter()-began:.1f}s',flush=True)
    assert len(anchors)==64 and len(cases)==256
    (OUT/'preparation.json').write_text(json.dumps({'anchors':64,'cases':256,'seconds':time.perf_counter()-began,
        'nominal_misses':sum(not r['anchor_converged'] for r in anchors),
        'reference_misses':sum(not r['reference_converged'] for r in cases),
        'instance_sha256':{p.name:sha(p) for p in sorted(folder.glob('*.npz'))}},indent=2)+'\n')


def replay():
    check_frozen()
    assert (OUT/'preparation.json').exists()
    assert not (OUT/'runs.csv').exists(),'Do not overwrite measured outcomes'
    policy=json.loads((OUT/'policy_snapshot.json').read_text())
    cases=pd.read_csv(OUT/'cases.csv')
    records=[];pools={};case_index=0;began=time.perf_counter()
    states=OUT/'states';states.mkdir(exist_ok=True)
    for key,group in cases.groupby('anchor',sort=False):
        model,cache,data=load_instance(key)
        for row in group.itertuples():
            c=data[row.shock+'_c'];arrays={}
            configurations=CONFIGURATIONS if case_index%2==0 else CONFIGURATIONS[::-1]
            for setting in configurations:
                with threadpool_limits(limits=setting,user_api='blas'):
                    current=threadpool_info()
                    assert all(p['num_threads']==setting for p in current if p['user_api']=='blas')
                    pools[str(setting)]=current
                    for repeat in range(REPEATS):
                        offset=(case_index+repeat+CONFIGURATIONS.index(setting))%len(METHODS)
                        order=METHODS[offset:]+METHODS[:offset]
                        for position,method in enumerate(order):
                            fitted=policy['model'] if method=='learned' else policy['training_fixed']
                            result=run_action(model,cache,data['c0'],c,data['anchor_x'],data['anchor_lam'],method,fitted)
                            checked=check_result(model,c,result,data[row.shock+'_reference_x'],data[row.shock+'_reference_lam'])
                            keep=['seconds','converged','fg_evaluations','accepted_iterations','status','precheck_certified',
                                  'light_certified','chose_refinement','feature_seconds','prediction_seconds',
                                  'refinement_steps','refinement_evaluations']
                            meta={k:getattr(row,k) for k in ['case','anchor','topology','seed','d','capacity_family','xi','shock']}
                            records.append({**meta,'threads':setting,'method':method,'repeat':repeat,'order':position,
                                            **{k:result.get(k,0) for k in keep},**checked})
                            if repeat==0:
                                prefix=f't{setting}_{method}'
                                arrays[prefix+'_x']=result['x'];arrays[prefix+'_lam']=result['lam']
            np.savez_compressed(states/(row.case+'.npz'),**arrays)
            case_index+=1
        pd.DataFrame(records).to_csv(OUT/'runs.csv',index=False)
        if case_index%32==0:print(f'New-graph replay {case_index}/256 cases, {len(records)}/9216 timings, {time.perf_counter()-began:.1f}s',flush=True)
    assert len(records)==9216
    cpuinfo=Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    models=[line.split(':',1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('model name')]
    environment={'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'platform':platform.platform(),
                 'cpu_model':models[0] if models else 'unrecorded','cpu_count':os.cpu_count(),
                 'available_affinity':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                 'cgroup_cpu_max':Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else None,
                 'blas_pools_by_setting':pools,'replay_seconds':time.perf_counter()-began,
                 'cases':256,'timing_records':9216,'policy_snapshot_sha256':sha(OUT/'policy_snapshot.json'),
                 'source_sha256':check_frozen()['source_sha256'],
                 'scope':'Same CPU and software; two thread configurations. This is not cross-hardware replication.'}
    (OUT/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')


def paired(values,reference):
    table=values.merge(reference[['case','seconds']],on='case',suffixes=('','_reference'),validate='one_to_one')
    ratios=table.seconds/table.seconds_reference
    return {'cases':len(table),'median_ratio':float(ratios.median()),'total_time_ratio':float(table.seconds.sum()/table.seconds_reference.sum()),
            'p10_ratio':float(ratios.quantile(.1)),'p90_ratio':float(ratios.quantile(.9)),'win_fraction':float((ratios<1).mean())}


def analyse():
    check_frozen()
    runs=pd.read_csv(OUT/'runs.csv')
    assert len(runs)==9216 and not runs.duplicated(['case','threads','method','repeat']).any()
    assert runs.groupby(['case','threads','method']).size().eq(3).all()
    med=runs.groupby(['case','anchor','topology','d','xi','shock','threads','method'],as_index=False).agg(
        seconds=('seconds','median'),converged=('converged','all'),precheck=('precheck_certified','all'),
        light=('light_certified','all'),chose_refinement=('chose_refinement','all'),
        feature_seconds=('feature_seconds','median'),prediction_seconds=('prediction_seconds','median'))
    med.to_csv(OUT/'medians.csv',index=False)
    summary={'cases':256,'anchors':64,'graphs':GRAPHS,'timing_records':len(runs),'by_setting':{},
             'failed_runs':int((~runs.converged).sum()),'maximum_overload':float(runs.overload.max()),
             'maximum_accepted_gap':float(runs.loc[runs.converged,'verified_gap'].max()),
             'scope':'Four additional convenience-selected historical structures from the same source collection. Same machine under one/four BLAS threads. Descriptive comparisons, with no random-population or independent-hardware inference.'}
    diagnostics=[]
    for setting,sub in med.groupby('threads'):
        heuristic=sub[sub.method=='heuristic'];learned=sub[sub.method=='learned'];reuse=sub[sub.method=='ray_reuse'];refine=sub[sub.method=='always_refine']
        common=set(sub.groupby('case').converged.all().loc[lambda x:x].index)
        methods={}
        for method,g in sub.groupby('method'):
            methods[method]={'solved':int(g.converged.sum()),'initial_certified':int(g.precheck.sum()),
                'light_certified':int(g.light.sum()),'refinement_choices':int(g.chose_refinement.sum()),
                'total_seconds':float(g.seconds.sum()),'vs_heuristic':paired(g,heuristic),
                'vs_reuse':paired(g,reuse),'common_success_vs_heuristic':paired(g[g.case.isin(common)],heuristic)}
        joined=reuse[['case','seconds','precheck','topology','d']].rename(columns={'seconds':'reuse_seconds'})
        joined=joined.merge(refine[['case','seconds']].rename(columns={'seconds':'refine_seconds'}),on='case')
        joined=joined.merge(heuristic[['case','seconds']].rename(columns={'seconds':'heuristic_seconds'}),on='case')
        joined=joined.merge(learned[['case','chose_refinement','feature_seconds','prediction_seconds']],on='case')
        joined['best_action_seconds']=joined[['reuse_seconds','refine_seconds']].min(axis=1)
        joined['hindsight_budget_us']=np.maximum(0,joined.heuristic_seconds-joined.best_action_seconds)*1e6
        joined['gate_overhead_us']=(joined.feature_seconds+joined.prediction_seconds)*1e6
        joined['oracle_refines']=joined.refine_seconds<joined.reuse_seconds
        joined['threads']=setting
        rejected=joined[~joined.precheck]
        summary['by_setting'][str(setting)]={'methods':methods,'common_success_cases':len(common),
            'learner_vs_heuristic_by_topology':{name:paired(g,heuristic[heuristic.topology==name]) for name,g in learned.groupby('topology')},
            'learner_vs_heuristic_by_size':{str(size):paired(g,heuristic[heuristic.d==size]) for size,g in learned.groupby('d')},
            'rejected_cases':len(rejected),'learner_rejected_vs_heuristic':paired(learned[learned.case.isin(rejected.case)],heuristic),
            'median_gate_overhead_us':float(rejected.gate_overhead_us.median()),
            'median_hindsight_budget_us':float(rejected.hindsight_budget_us.median()),
            'budget_covers_measured_gate_fraction':float((rejected.hindsight_budget_us>=rejected.gate_overhead_us).mean()),
            'hindsight_action_disagreement_fraction':float((rejected.chose_refinement!=rejected.oracle_refines).mean()),
            'hindsight_best_total_vs_heuristic':float(joined.best_action_seconds.sum()/joined.heuristic_seconds.sum()),
            'diagnostic_scope':'Observed timing oracle and budget use held-out timings retrospectively. No deployment claim or guarantee of expected achievable speed.'}
        diagnostics.append(joined)
    pd.concat(diagnostics).to_csv(OUT/'cost_diagnostics.csv',index=False)
    runs.loc[~runs.converged].to_csv(OUT/'failures.csv',index=False)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':13,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,3.9),sharey=True)
    for ax,setting in zip(axes,CONFIGURATIONS):
        stats=summary['by_setting'][str(setting)]['methods']
        for j,method in enumerate(METHODS):
            ax.scatter(stats[method]['vs_heuristic']['median_ratio'],j,
                       color='#177C80' if method=='learned' else '#718392',s=45)
        ax.axvline(1,color='#555555',ls='--',lw=1)
        ax.set_title(f'{setting} BLAS thread'+('s' if setting>1 else ''))
        ax.set_xlabel('Paired runtime / capacity rule');ax.grid(axis='x',alpha=.18)
    axes[0].set_yticks(range(6),LABELS);axes[0].invert_yaxis();fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(HERE/'figures'/('05_new_graph_validation.'+suffix),dpi=220,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.7))
    budgets=np.logspace(0,5,200)
    for setting,color in [(1,'#177C80'),(4,'#AD7652')]:
        frame=diagnostics[CONFIGURATIONS.index(setting)];frame=frame[~frame.precheck]
        y=[np.mean(frame.hindsight_budget_us>=b) for b in budgets]
        overhead=summary['by_setting'][str(setting)]['median_gate_overhead_us']
        ax.plot(budgets,y,color=color,label=f'{setting} thread'+('s' if setting>1 else ''))
        ax.axvline(overhead,color=color,ls='--',lw=1)
    ax.set_xscale('log');ax.set_ylim(0,1)
    ax.set_xlabel('Hindsight extra computation budget relative to capacity rule (microseconds)')
    ax.set_ylabel('Fraction of rejected cases');ax.grid(alpha=.15);ax.legend()
    fig.tight_layout()
    for suffix in ['png','pdf']:fig.savefig(HERE/'figures'/('06_selection_budget.'+suffix),dpi=220,bbox_inches='tight')
    plt.close(fig)
    print(json.dumps({'failed_runs':summary['failed_runs'],'learner_vs_rule':{s:v['methods']['learned']['vs_heuristic'] for s,v in summary['by_setting'].items()}},indent=2))


def audit():
    protocol=check_frozen()
    policy=json.loads((OUT/'policy_snapshot.json').read_text())
    assert sha(OUT/'policy_snapshot.json')==protocol['policy_snapshot_sha256']
    assert policy['model']==json.loads((HERE/'results/deployment_model.json').read_text())['model']
    assert set(GRAPHS).isdisjoint(policy['training_topologies'])
    preparation=json.loads((OUT/'preparation.json').read_text())
    for name,digest in preparation['instance_sha256'].items():assert sha(OUT/'instances'/name)==digest
    environment=json.loads((OUT/'environment.json').read_text())
    for setting,pools in environment['blas_pools_by_setting'].items():
        assert all(p['num_threads']==int(setting) for p in pools if p['user_api']=='blas')
    runs=pd.read_csv(OUT/'runs.csv');cases=pd.read_csv(OUT/'cases.csv');anchors=pd.read_csv(OUT/'anchors.csv')
    assert len(runs)==9216 and len(cases)==256 and len(anchors)==64
    assert not runs.duplicated(['case','threads','method','repeat']).any()
    assert runs.groupby(['case','threads','method']).size().eq(3).all()
    indexed=runs[runs.repeat==0].set_index(['case','threads','method'])
    maximum_error=0.;states_checked=0;choices_checked=0
    for key,group in cases.groupby('anchor',sort=False):
        model,cache,data=load_instance(key)
        for row in group.itertuples():
            c=data[row.shock+'_c'];query=cache.query(c,data['anchor_x'])
            z=features(model,cache,data['c0'],c,data['anchor_lam'],query)
            assert np.allclose(z,np.asarray([getattr(row,k) for k in FEATURES]),rtol=1e-11,atol=1e-12)
            expected=bool(query['gap_per_weight']>TARGET and predict(policy['model'],z))
            for setting in CONFIGURATIONS:
                assert (runs[(runs.case==row.case)&(runs.threads==setting)&(runs.method=='learned')].chose_refinement==expected).all()
                choices_checked+=1
            with np.load(OUT/'states'/(row.case+'.npz'),allow_pickle=False) as state:
                for setting in CONFIGURATIONS:
                    for method in METHODS:
                        prefix=f't{setting}_{method}';x=state[prefix+'_x'];lam=state[prefix+'_lam']
                        assert model.overload(x,c)<1e-9
                        gap=max(0,(model.dual(lam,c)[0]-model.utility(x))/model.W)
                        saved=indexed.loc[(row.case,setting,method),'verified_gap']
                        maximum_error=max(maximum_error,abs(gap-saved));assert abs(gap-saved)<1e-10
                        states_checked+=1
    accepted=runs[runs.converged]
    assert (accepted.verified_gap<=TARGET+1e-10).all() and (accepted.regret_lower<=TARGET+1e-8).all()
    assert (runs.overload<1e-9).all()
    result={'passed':True,'cases':256,'timing_records':9216,'stored_states_recomputed':states_checked,
            'policy_decisions_recomputed':choices_checked,'maximum_saved_gap_error':maximum_error,
            'maximum_overload':float(runs.overload.max()),'failed_runs':int((~runs.converged).sum()),
            'nominal_reference_misses':int((~anchors.anchor_converged).sum()),'updated_reference_misses':int((~cases.reference_converged).sum()),
            'training_and_test_graph_identities_disjoint':True,'frozen_model_unchanged':True,'source_hashes_match':True,
            'blas_limits_verified':True,'scope':'Float64 numerical consistency and graph-identity separation, not interval arithmetic or statistical independence of network populations.'}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','prepare','replay','analyse','audit'])
    args=parser.parse_args();globals()[args.stage]()
