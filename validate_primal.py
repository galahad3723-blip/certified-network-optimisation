"""Small independent primal SLSQP checks of the dual reference implementation."""
from pathlib import Path
import json
from certified_num import NUM, solve, topology, routing
import numpy as np
from scipy.optimize import minimize


def main():
    root = Path(__file__).resolve().parent
    records = []
    for name in ['Abilene', 'Cernet']:
        n, edges, _ = topology(root/'data'/'InternetTopologyZoo'/(name+'.graphml'))
        A, _ = routing(n, edges, 40, 19)
        dense = A.toarray()
        rng = np.random.default_rng(19)
        w = np.exp(rng.normal(0, .5, 40))
        w /= w.mean()
        offered = A @ np.ones(40)
        c = .8 * offered * rng.uniform(.7, 1.3, A.shape[0])
        for xi in [0., .5]:
            model = NUM(A, w, np.full(40, xi))
            ref = solve(model, c, np.full(A.shape[0], .2), 1e-8, refine=True)
            initial = np.full(40, .5 * np.min(c/offered))
            result = minimize(lambda x: -model.utility(x), initial,
                              jac=lambda x: -w/(x+xi), method='SLSQP',
                              bounds=[(1e-12 if xi == 0 else 0., None)]*40,
                              constraints=[{'type':'ineq', 'fun':lambda x: c-dense@x,
                                            'jac':lambda x: -dense}],
                              options={'maxiter':3000, 'ftol':1e-11})
            overload = model.overload(result.x, c)
            discrepancy = (ref['upper']-model.utility(result.x))/model.W
            assert result.success and ref['converged']
            assert overload < 1e-8 and abs(discrepancy) < 5e-7
            records.append({'topology':name, 'flows':40, 'seed':19, 'xi':xi,
                            'SLSQP_success':bool(result.success),
                            'SLSQP_overload':overload,
                            'dual_vs_primal_gap_per_weight':float(discrepancy),
                            'dual_reference_gap':ref['gap_per_weight']})
    (root/'results'/'independent_primal_checks.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
