"""Fixed-protocol CPU benchmark. All observations and failures are retained."""
from pathlib import Path
import hashlib,json,platform,sys,time
from certified_num import NUM,PriceRay,solve,run_method,topology,routing
import numpy as np
import pandas as pd
import scipy

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'InternetTopologyZoo'
OUT=ROOT/'results'
TOPOLOGIES=['Abilene','Geant2012','Cernet','Colt','UsCarrier','Cogentco']
SEEDS=[101,211,307]
SIZES=[1000,10000]
FAMILIES=['load_coupled','independent']
SHIFTS=[0.,.5]
METHODS=['cold','warm','ray_warm','reuse']
TARGET=1e-3
REFERENCE_TARGET=1e-7
REPEATS=3


def main():
    OUT.mkdir(exist_ok=True);saved=OUT/'instances';saved.mkdir(exist_ok=True)
    protocol={'core_topologies':TOPOLOGIES,'seeds':SEEDS,'sizes':SIZES,
              'capacity_families':FAMILIES,'utility_shifts':SHIFTS,
              'weights':'lognormal(0,0.5), normalised to mean one',
              'shocks':['uniform_10','uniform_30','local_30','heterogeneous_30'],
              'local_shock':'30% reduction of ceil(5% of used directed links), chosen before method evaluation',
              'methods':METHODS,'timing_repeats':REPEATS,'target_gap_per_total_weight':TARGET,
              'reference_target':REFERENCE_TARGET,'precheck_tolerances':[1e-4,1e-3,1e-2],
              'scaling_extension':{'topologies':['Abilene','Cogentco'],'seed':911,
                                   'sizes':[1000,10000,100000],'capacity_family':'independent',
                                   'shifts':SHIFTS,'shocks':['uniform_10','heterogeneous_30']},
              'source':'fixed nominal anchors; no sequence tracking or production trace',
              'data_use':'public topology structures; synthetic weights, capacities, routes and shocks',
              'statistics_unit':'six topology families; seeds/settings/shocks retained inside resampled topology',
              'timing_scope':'online method, including feasibility checks and certification; preparation separately recorded',
              'warm_start':'same nominal prices and feasible nominal anchor available to methods',
              'limits':{'maxiter':3000,'maxfun':45000},
              'selection':'all settings fixed before main benchmark execution; development smoke test uses Abilene, 100 flows, seed 7'}
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    settings=[]
    for topo in TOPOLOGIES:
        for seed in SEEDS:
            for d in SIZES:
                for family in FAMILIES:
                    for xi in SHIFTS:settings.append(('core',topo,seed,d,family,xi))
    for topo in ['Abilene','Cogentco']:
        for d in [1000,10000,100000]:
            for xi in SHIFTS:settings.append(('scaling',topo,911,d,'independent',xi))
    anchors=[];cases=[];runs=[];failures=[];topology_info={};route_cache={}
    began=time.perf_counter()
    for index,(split,tname,seed,d,family,xi) in enumerate(settings):
        key=f'{split}_{tname}_{seed}_{d}_{family}_xi{xi:g}'
        routekey=(tname,seed,d)
        if routekey not in route_cache:
            n,edges,info=topology(DATA/(tname+'.graphml'));topology_info[tname]=info
            route_cache[routekey]=routing(n,edges,d,seed)
        A,directed=route_cache[routekey]
        rng=np.random.default_rng(np.random.SeedSequence([20261022,seed,d,TOPOLOGIES.index(tname)]))
        w=np.exp(rng.normal(0,.5,d));w/=w.mean()
        offered=np.asarray(A@np.ones(d)).ravel()
        if family=='load_coupled':c=.8*offered*rng.uniform(.7,1.3,len(offered))
        else:c=.8*offered.mean()*np.exp(rng.normal(0,.7,len(offered)))
        model=NUM(A,w,np.full(d,xi))
        anchor=solve(model,c,np.full(model.m,.2),REFERENCE_TARGET,refine=True)
        cache=PriceRay(model,anchor['lam'])
        anchors.append({'anchor':key,'split':split,'topology':tname,'seed':seed,'d':d,
                        'capacity_family':family,'xi':xi,'used_links':model.m,'nnz':A.nnz,
                        'anchor_seconds':anchor['seconds'],'anchor_gap':anchor['gap_per_weight'],
                        'anchor_certified':anchor['converged'],'source_status':anchor['status'],
                        'cache_preparation_seconds':cache.preparation_seconds,
                        'zero_anchor_fraction':float(np.mean(anchor['x']<=1e-10))})
        if not anchor['converged']:failures.append({'anchor':key,'stage':'nominal reference','gap':anchor['gap_per_weight'],'status':anchor['status']})
        updates={'uniform_10':.9*c,'uniform_30':.7*c}
        local=c.copy();chosen=rng.choice(model.m,max(1,int(np.ceil(.05*model.m))),replace=False)
        local[chosen]*=.7;updates['local_30']=local
        updates['heterogeneous_30']=c*rng.uniform(.7,1,model.m)
        if split=='scaling':updates={k:v for k,v in updates.items() if k in ['uniform_10','heterogeneous_30']}
        arrays={'A_data':A.data,'A_indices':A.indices,'A_indptr':A.indptr,'A_shape':np.array(A.shape),
                'w':w,'xi':model.xi,'c0':c,'anchor_x':anchor['x'],'anchor_lam':anchor['lam'],'directed_edges':directed}
        for shock,cnew in updates.items():
            case=key+'_'+shock
            query=cache.query(cnew,anchor['x'])
            reference=solve(model,cnew,anchor['lam'],REFERENCE_TARGET,anchor['x'],refine=True)
            actual_lower=max(0,(reference['lower']-query['lower'])/model.W)
            actual_upper=max(0,(reference['upper']-query['lower'])/model.W)
            if not reference['converged']:failures.append({'anchor':key,'case':case,'stage':'updated reference','gap':reference['gap_per_weight'],'status':reference['status']})
            row={'case':case,'anchor':key,'split':split,'topology':tname,'seed':seed,'d':d,
                 'capacity_family':family,'xi':xi,'shock':shock,'precheck_gap':query['gap_per_weight'],
                 'fixed_price_gap':query['fixed_price_gap_per_weight'],'ray_scale':query['scale'],
                 'actual_regret_lower':actual_lower,'actual_regret_upper':actual_upper,
                 'reference_gap':reference['gap_per_weight'],'reference_certified':reference['converged'],
                 'reference_seconds':reference['seconds'],'query_seconds':query['seconds'],
                 'overload':model.overload(query['x'],cnew),
                 'suboptimality_interval_width':actual_upper-actual_lower}
            for tol in [1e-4,1e-3,1e-2]:
                label=f'{tol:g}';row['accept_'+label]=query['gap_per_weight']<=tol
                row['actual_good_'+label]=actual_upper<=tol
            cases.append(row)
            arrays[shock+'_c']=cnew;arrays[shock+'_reference_x']=reference['x']
            arrays[shock+'_reference_lam']=reference['lam'];arrays[shock+'_reuse_x']=query['x']
            for repeat in range(REPEATS):
                offset=(repeat+len(cases)-1)%len(METHODS)
                order=METHODS[offset:]+METHODS[:offset]
                for order_index,method in enumerate(order):
                    result=run_method(model,cnew,anchor,cache,method,TARGET)
                    if model.overload(result['x'],cnew)>1e-9:raise RuntimeError('Measured method returned infeasible allocation')
                    runs.append({'case':case,'anchor':key,'split':split,'topology':tname,'seed':seed,'d':d,
                                 'capacity_family':family,'xi':xi,'shock':shock,'method':method,
                                 'repeat':repeat,'order_index':order_index,
                                 **{k:v for k,v in result.items() if k in ['gap_per_weight','converged','fg_evaluations','accepted_iterations','seconds','status','precheck_seconds','skipped']},
                                 'amortized_seconds':result['seconds']+(cache.preparation_seconds/len(updates) if method in ['ray_warm','reuse'] else 0)})
            if reference['converged'] and query['gap_per_weight']<=TARGET and actual_lower>TARGET+1e-10:
                raise RuntimeError('Certificate falsely accepted a suboptimal allocation')
        np.savez_compressed(saved/(key+'.npz'),**arrays)
        pd.DataFrame(anchors).to_csv(OUT/'anchors.csv',index=False)
        pd.DataFrame(cases).to_csv(OUT/'cases.csv',index=False)
        pd.DataFrame(runs).to_csv(OUT/'runs.csv',index=False)
        (OUT/'failures.json').write_text(json.dumps(failures,indent=2)+'\n')
        if (index+1)%4==0 or index==0:
            print(f'Completed anchors {index+1}/{len(settings)}; cases {len(cases)}; runs {len(runs)}; elapsed {time.perf_counter()-began:.1f}s; reference misses {len(failures)}',flush=True)
    environment={'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,
                 'platform':platform.platform(),'threads':1,'total_seconds':time.perf_counter()-began,
                 'source_sha256':hashlib.sha256((ROOT/'certified_num.py').read_bytes()).hexdigest(),
                 'benchmark_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 'anchors':len(anchors),'cases':len(cases),'runs':len(runs),'reference_misses':len(failures),
                 'status':'Research benchmark; no claim of Q1 readiness or established novelty'}
    (OUT/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    (OUT/'topologies.json').write_text(json.dumps(topology_info,indent=2)+'\n')
    print(json.dumps(environment,indent=2))


if __name__=='__main__':main()
