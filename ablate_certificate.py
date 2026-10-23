"""Separate scalar price improvement from improved primal candidates.

Specified while the fixed benchmark was running, before comparative outcomes
were inspected. This supplement does not alter the measured methods.
"""
from pathlib import Path
import json
from certified_num import NUM, PriceRay
import numpy as np
import pandas as pd
from scipy import sparse


def main():
    root=Path(__file__).resolve().parent
    folder=root/'results'
    cases=pd.read_csv(folder/'cases.csv')
    rows=[]
    for anchor,group in cases.groupby('anchor',sort=False):
        with np.load(folder/'instances'/(anchor+'.npz'),allow_pickle=False) as data:
            A=sparse.csr_matrix((data['A_data'],data['A_indices'],data['A_indptr']),shape=tuple(data['A_shape']))
            model=NUM(A,data['w'],data['xi'])
            ray=PriceRay(model,data['anchor_lam'])
            for case in group.itertuples():
                c=data[case.shock+'_c']
                q=ray.query(c,data['anchor_x'])
                fixed=float(c@ray.lam+ray.phi)
                row={'case':case.case,'anchor':anchor,'split':case.split,
                     'topology':case.topology,'shock':case.shock,'xi':case.xi,
                     'capacity_family':case.capacity_family,
                     'fixed_anchor':max(0.,(fixed-q['anchor_lower'])/model.W),
                     'fixed_best':max(0.,(fixed-q['lower'])/model.W),
                     'ray_anchor':max(0.,(q['upper']-q['anchor_lower'])/model.W),
                     'ray_best':q['gap_per_weight']}
                assert row['ray_best']<=min(row['ray_anchor'],row['fixed_best'])+1e-11
                assert max(row['ray_anchor'],row['fixed_best'])<=row['fixed_anchor']+1e-11
                rows.append(row)
    frame=pd.DataFrame(rows)
    frame.to_csv(folder/'certificate_ablation.csv',index=False)
    core=frame[frame.split=='core']
    summary={'core_cases':len(core),'scope':'untimed controlled certificate ablation; no benchmark retuning',
             'acceptances_at_0.001':{key:int((core[key]<=1e-3).sum())
                                    for key in ['fixed_anchor','fixed_best','ray_anchor','ray_best']},
             'by_shock':[]}
    for shock,g in core.groupby('shock'):
        summary['by_shock'].append({'shock':shock,'cases':len(g),
            **{key:int((g[key]<=1e-3).sum()) for key in ['fixed_anchor','fixed_best','ray_anchor','ray_best']}})
    (folder/'certificate_ablation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
