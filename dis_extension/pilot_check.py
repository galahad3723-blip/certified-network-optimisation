"""Small independent development checks; no core benchmark outcome is inspected."""
from pathlib import Path
import json
import numpy as np
from scipy import sparse
from certified_updates import NUM, make_cache, lightweight_refinement, run_action, solve


def main():
    checks = []
    for ratio in [.01, .1, .7]:
        model = NUM(sparse.eye(2, format='csr'), np.ones(2), np.zeros(2))
        c0 = np.ones(2); x0 = np.ones(2); lam0 = np.ones(2)
        c = np.array([ratio, 1.])
        cache = make_cache(model, c0, x0, lam0)
        query = cache.query(c, x0)
        refined = lightweight_refinement(model, cache, c0, c, lam0, query)
        assert query['gap_per_weight'] > 1e-3
        assert refined['gap_per_weight'] < 1e-12
        assert np.allclose(refined['x'], c)
        checks.append({'case':'two independent links', 'ratio':ratio,
                       'original_gap':query['gap_per_weight'], 'refined_gap':refined['gap_per_weight']})
    rng = np.random.default_rng(20261023)
    for shift in [0., .5]:
        A = sparse.csr_matrix((rng.uniform(size=(5, 40)) < .45).astype(float))
        for j in range(A.shape[1]):
            if A[:,j].nnz == 0:
                A[0,j] = 1
        model = NUM(A, np.exp(rng.normal(0, .3, 40)), np.full(40, shift))
        c0 = np.asarray(A @ np.ones(40)).ravel()
        old = solve(model, c0, np.ones(5), 1e-8, refine=True)
        cache = make_cache(model, c0, old['x'], old['lam'])
        for _ in range(8):
            c = c0*rng.uniform(.5, 1.2, 5)
            q = cache.query(c, old['x'])
            r = lightweight_refinement(model, cache, c0, c, old['lam'], q)
            ref = solve(model, c, old['lam'], 1e-8, old['x'], refine=True)
            assert np.all(np.diff(r['refinement_trace']) <= 1e-10)
            assert model.overload(r['x'], c) < 1e-9
            assert r['upper'] >= ref['lower']-1e-8*model.W
            assert r['lower'] <= ref['upper']+1e-8*model.W
            final = run_action(model, cache, c0, c, old['x'], old['lam'], 'always_refine')
            assert final['converged']
            checks.append({'case':'random small network','shift':shift,
                           'before_gap':q['gap_per_weight'], 'after_gap':r['gap_per_weight']})
    target = Path(__file__).resolve().parents[1]/'tmp/dis_pilot/checks.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'passed':True,'checks':checks}, indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':len(checks)}))


if __name__ == '__main__':
    main()
