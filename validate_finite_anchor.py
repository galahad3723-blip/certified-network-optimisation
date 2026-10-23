"""Check the finite-anchor Jensen extension independently of benchmark outcomes."""
from pathlib import Path
import json
from certified_num import NUM, PriceRay
import numpy as np
from scipy import sparse


def main():
    rng = np.random.default_rng(81731)
    maximum_identity_error = 0.
    maximum_ray_excess = 0.
    maximum_variance_violation = 0.
    maximum_kl_identity_error = 0.
    zero_rate_cases = 0
    expansions = 0
    rows = []
    for trial in range(500):
        m, d = 7, 29
        A = rng.uniform(.2, 1., (m, d)) * (rng.random((m, d)) < .25)
        A[rng.integers(m, size=d), np.arange(d)] = 1.
        w = np.exp(rng.normal(0., .5, d))
        xi = rng.uniform(.1, 1., d)
        x0 = rng.uniform(.1, 2., d)
        if trial % 2:
            x0[rng.choice(d, 5, replace=False)] = 0.
            zero_rate_cases += 1
        if trial % 3 == 0:
            xi[x0 > 0] = 0.
        c = A @ x0 + rng.uniform(0., 2., m)
        lam = np.exp(rng.normal(0., .7, m))
        model = NUM(sparse.csr_matrix(A), w, xi)
        q = A.T @ lam
        p = w / w.sum()
        theta = xi / (x0 + xi)
        residual = q * (x0 + xi) / w
        sigma = float(lam @ (c - A @ x0) / w.sum())
        s = float(np.exp(rng.uniform(np.log(.1), np.log(3.))))
        expansions += int(s > 1)
        z = s + (1 - s) * theta
        a = residual * z
        mean = float(p @ a)
        bound = float(np.log(mean + s * sigma) - p @ np.log(a))
        D = float(s * c @ lam + xi @ q)
        t = w.sum() / D
        relaxed = t * s * c @ lam + np.sum(w * (np.log(w / (t * q)) - 1) + t * xi * q)
        direct = float((relaxed - model.utility(s * x0)) / w.sum())
        ray = PriceRay(model, lam)
        tr = ray.scale(s * c)
        exact_ray_upper = model.dual(tr * lam, s * c)[0]
        ray_gap = (exact_ray_upper - model.utility(s * x0)) / w.sum()
        variance = float(p @ (a - mean)**2)
        secondary = variance / (2 * float(a.min())**2) + np.log1p(s * sigma / mean)
        transformed = p*a/mean
        kl = float(p @ np.log(p/transformed))
        kl_error = abs(kl + np.log1p(s*sigma/mean) - bound)
        maximum_kl_identity_error = max(maximum_kl_identity_error, kl_error)
        maximum_identity_error = max(maximum_identity_error, abs(bound - direct))
        maximum_ray_excess = max(maximum_ray_excess, ray_gap - bound)
        maximum_variance_violation = max(maximum_variance_violation, bound - secondary)
        assert model.overload(s * x0, s * c) < 1e-12
        assert bound >= -1e-12
        assert abs(bound - direct) < 1e-11
        assert ray_gap <= bound + 1e-11
        assert bound <= secondary + 1e-11
        assert kl_error < 1e-11
        if trial < 5:
            rows.append({'trial': trial, 'scale': s, 'bound': bound,
                         'ray_gap': float(ray_gap), 'slack_term': sigma})
    result = {'cases': 500, 'zero_nominal_rate_cases': zero_rate_cases,
              'capacity_expansions': expansions, 'capacity_contractions': 500-expansions,
              'maximum_formula_identity_error': maximum_identity_error,
              'maximum_true_ray_excess_over_bound': maximum_ray_excess,
              'maximum_violation_of_variance_upper_bound': maximum_variance_violation,
              'maximum_KL_identity_error': maximum_kl_identity_error,
              'first_five_cases': rows, 'passed': True}
    out = Path(__file__).resolve().parent/'results'/'finite_anchor_validation.json'
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
