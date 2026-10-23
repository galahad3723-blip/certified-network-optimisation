"""Nested topology-held-out algorithm selection with portable fitted policies."""
from pathlib import Path
import os
for _thread_setting in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_thread_setting]='1'
import json
import time
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor
import sklearn
from certified_updates import FEATURES, TARGET, predict

HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
SPECS=[{'kind':'ridge','alpha':v} for v in [1.,10.]]+[
       {'kind':'tree','depth':d} for d in [1,2,3]]


def fit_record(X,y,spec,threshold):
    if spec['kind']=='ridge':
        scale=StandardScaler().fit(X)
        model=Ridge(alpha=spec['alpha']).fit(scale.transform(X),y)
        result={'kind':'ridge','mean':scale.mean_.tolist(),'scale':scale.scale_.tolist(),
                'coef':model.coef_.tolist(),'intercept':float(model.intercept_)}
    else:
        model=DecisionTreeRegressor(max_depth=spec['depth'],min_samples_leaf=20,
                                    random_state=20261023).fit(X,y)
        tree=model.tree_
        result={'kind':'tree','left':tree.children_left.tolist(),'right':tree.children_right.tolist(),
                'feature':tree.feature.tolist(),'threshold':tree.threshold.tolist(),
                'value':tree.value[:,0,0].tolist()}
    result['decision_threshold']=float(threshold)
    return result


def select_spec(table):
    groups=sorted(table.topology.unique())
    candidates=[]
    for spec in SPECS:
        for threshold in [0.,-.05]:
            scores=[]
            for group in groups:
                train=table[table.topology!=group]
                validation=table[table.topology==group]
                record=fit_record(train[FEATURES].values,train.target.values,spec,threshold)
                decisions=np.array([predict(record,z) for z in validation[FEATURES].values])
                ratios=validation.refine_seconds.values/validation.reuse_seconds.values
                overhead=validation.feature_seconds.values/validation.reuse_seconds.values
                scores.append(float(np.mean(np.where(decisions,ratios,1.)+overhead)))
            candidates.append({'spec':spec,'threshold':threshold,'score':float(np.mean(scores))})
    selected=min(candidates,key=lambda v:v['score'])
    return selected,candidates


def main():
    assert (OUT/'collection_complete.json').exists()
    assert not (OUT/'fold_models.json').exists(), 'Do not silently refit after examining replay outcomes'
    began=time.perf_counter()
    descriptors=pd.read_csv(OUT/'features.csv')
    runs=pd.read_csv(OUT/'action_runs.csv')
    times=runs.groupby(['case','method']).seconds.median().unstack()
    table=descriptors.merge(times,left_on='case',right_index=True,validate='one_to_one')
    table=table.rename(columns={'ray_reuse':'reuse_seconds','always_refine':'refine_seconds'})
    table['target']=np.log(table.refine_seconds/table.reuse_seconds)
    rejected=table[table.precheck_gap>TARGET].copy()
    assert len(table)==576 and len(rejected)==360
    models={};predictions=[];selections=[];split_manifest=[]
    for group in sorted(table.topology.unique()):
        train=rejected[rejected.topology!=group]
        test=table[table.topology==group]
        assert set(train.anchor).isdisjoint(test.anchor)
        assert set(train.topology).isdisjoint(test.topology)
        selected,candidates=select_spec(train)
        record=fit_record(train[FEATURES].values,train.target.values,selected['spec'],selected['threshold'])
        train_ratio=float(np.mean(train.refine_seconds/train.reuse_seconds))
        fixed={'kind':'constant','refine':bool(train_ratio<1.)}
        models[group]={'held_out_topology':group,'training_topologies':sorted(train.topology.unique()),
                       'model':record,'selection':selected,'train_best':fixed,
                       'training_refine_to_reuse_mean_ratio':train_ratio}
        for row in test.itertuples():
            z=np.array([getattr(row,k) for k in FEATURES])
            decision=bool(row.precheck_gap>TARGET and predict(record,z))
            predictions.append({'case':row.case,'topology':group,'chose_refinement':decision,
                                'rejected_by_initial_certificate':row.precheck_gap>TARGET,
                                'training_refine_mean_ratio':train_ratio})
        selections.append({'held_out_topology':group,'selected':selected,'inner_candidates':candidates})
        split_manifest.append({'held_out_topology':group,'training_cases':train.case.tolist(),
                               'test_cases':test.case.tolist(),'training_anchors':sorted(train.anchor.unique()),
                               'test_anchors':sorted(test.anchor.unique()),'disjoint_topologies_and_anchors':True})
        print(f'Fitted outer fold {group}: {selected["spec"]}, threshold {selected["threshold"]}',flush=True)
    selected,candidates=select_spec(rejected)
    deployment=fit_record(rejected[FEATURES].values,rejected.target.values,selected['spec'],selected['threshold'])
    (OUT/'fold_models.json').write_text(json.dumps(models,indent=2)+'\n')
    (OUT/'deployment_model.json').write_text(json.dumps({'model':deployment,'selection':selected,
        'scope':'Fitted on all core observations for future use; reported test performance comes from held-out fold models, not this fit'},indent=2)+'\n')
    pd.DataFrame(predictions).to_csv(OUT/'held_out_predictions.csv',index=False)
    (OUT/'model_selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (OUT/'split_manifest.json').write_text(json.dumps(split_manifest,indent=2)+'\n')
    (OUT/'training_environment.json').write_text(json.dumps({'sklearn':sklearn.__version__,
        'features':FEATURES,'training_seconds':time.perf_counter()-began,'outer_folds':6,
        'rows':len(table),'modelled_rejected_cases':len(rejected),'no_reference_or_test_timing_features':True,
        'all_outer_training_and_test_topologies_disjoint':True},indent=2)+'\n')


if __name__=='__main__':
    main()
