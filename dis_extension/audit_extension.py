"""Recompute saved action certificates and verify topology-held-out execution."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from certified_updates import FEATURES, TARGET, features, predict
from experiment import OUT, ROOT, HERE, load_anchor, digest


def main():
    protocol=json.loads((OUT/'protocol.json').read_text())
    for name in ['certified_updates.py','experiment.py']:
        assert digest(HERE/name)==protocol['sources'][name]
    for name in ['cases.csv','anchors.csv']:
        assert digest(ROOT/'results'/name)==protocol['sources'][name]
    assert digest(ROOT/'certified_num.py')==protocol['sources']['certified_num.py']
    collection=json.loads((OUT/'collection_complete.json').read_text())
    env=json.loads((OUT/'environment.json').read_text())
    for record in [collection,env]:
        assert all(t['num_threads']==1 for t in record['threadpools'] if t['user_api']=='blas')
    for name,sha in env['source_sha256'].items():assert digest(HERE/name)==sha
    assert digest(OUT/'fold_models.json')==env['fold_models_sha256']
    descriptors=pd.read_csv(OUT/'features.csv').set_index('case')
    actions=pd.read_csv(OUT/'action_runs.csv')
    replay=pd.read_csv(OUT/'replay_runs.csv')
    assert (len(actions),len(descriptors),len(replay))==(3456,576,13824)
    assert not actions.duplicated(['case','method','repeat']).any()
    assert not replay.duplicated(['case','method','repeat']).any()
    assert replay.groupby(['case','method']).size().eq(3).all()
    splits=json.loads((OUT/'split_manifest.json').read_text())
    core=pd.read_csv(ROOT/'results/cases.csv');core=core[core.split=='core']
    bycase=core.set_index('case')
    for split in splits:
        train=bycase.loc[split['training_cases']]
        test=bycase.loc[split['test_cases']]
        assert set(train.topology).isdisjoint(test.topology)
        assert set(train.anchor).isdisjoint(test.anchor)
        assert set(test.topology)=={split['held_out_topology']}
    models=json.loads((OUT/'fold_models.json').read_text())
    expected=pd.read_csv(OUT/'held_out_predictions.csv').set_index('case')
    shifts=pd.read_csv(OUT/'shift_cases.csv')
    assert len(shifts)==192
    assert shifts.reference_converged.all()
    maximum_gap_error=0.;maximum_feature_error=0.;states_checked=0;policy_checked=0
    for key,group in core.groupby('anchor',sort=False):
        model,cache,data=load_anchor(key)
        for row in group.itertuples():
            c=data[row.shock+'_c'];query=cache.query(c,data['anchor_x'])
            z=features(model,cache,data['c0'],c,data['anchor_lam'],query)
            stored=descriptors.loc[row.case,FEATURES].astype(float).values
            maximum_feature_error=max(maximum_feature_error,float(np.max(abs(z-stored))))
            assert np.allclose(z,stored,rtol=1e-11,atol=1e-12)
            decision=bool(query['gap_per_weight']>TARGET and predict(models[row.topology]['model'],z))
            assert bool(expected.loc[row.case,'chose_refinement'])==decision
            decisions=replay[(replay.case==row.case)&(replay.method=='learned')].chose_refinement
            assert (decisions==decision).all()
            policy_checked+=1
            with np.load(OUT/'action_states'/(row.case+'.npz'),allow_pickle=False) as state:
                for method in ['ray_reuse','always_refine']:
                    x=state[method+'_x'];lam=state[method+'_lam']
                    assert model.overload(x,c)<1e-9
                    gap=max(0.,(model.dual(lam,c)[0]-model.utility(x))/model.W)
                    observed=actions[(actions.case==row.case)&(actions.method==method)&(actions.repeat==0)].iloc[0]
                    maximum_gap_error=max(maximum_gap_error,abs(gap-observed.verified_gap))
                    assert abs(gap-observed.verified_gap)<1e-10
                    states_checked+=1
        shifted=shifts[shifts.anchor==key]
        if len(shifted):
            with np.load(OUT/'shift_instances'/(key+'.npz'),allow_pickle=False) as source:
                for row in shifted.itertuples():
                    c=source[row.shock+'_c'];query=cache.query(c,data['anchor_x'])
                    z=features(model,cache,data['c0'],c,data['anchor_lam'],query)
                    decision=bool(query['gap_per_weight']>TARGET and predict(models[row.topology]['model'],z))
                    decisions=replay[(replay.case==row.case)&(replay.method=='learned')].chose_refinement
                    assert (decisions==decision).all()
                    policy_checked+=1
    accepted=replay[replay.converged]
    assert (accepted.verified_gap<=TARGET+1e-10).all()
    assert (accepted.regret_lower<=TARGET+1e-8).all()
    assert (replay.overload<1e-9).all()
    result={'passed':True,'core_cases':576,'shift_cases':192,'action_runs':len(actions),
            'replay_runs':len(replay),'stored_action_states_recomputed':states_checked,
            'held_out_policy_choices_recomputed':policy_checked,
            'maximum_saved_gap_error':maximum_gap_error,'maximum_feature_recomputation_error':maximum_feature_error,
            'maximum_overload':float(replay.overload.max()),'failed_replay_runs':int((~replay.converged).sum()),
            'all_outer_topologies_and_anchors_disjoint':True,'threadpools_verified_one':True,
            'source_hashes_match_reported_execution':True,
            'scope':'Float64 consistency, saved-state and split checks; no interval arithmetic, external replication or population-wide statistical guarantee'}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
