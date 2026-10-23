# Certified reuse for weighted logarithmic network allocation

Research derivations for the personal project of Kai Chi, 22 October 2026.
The arguments below are supplied with proofs and numerical checks. Their
originality relative to the full literature has not been established. Standard
weak duality, water filling and iso-elasticity are explicitly not claimed as new.

## Model and assumptions

Let A be a nonnegative link-route matrix with no empty column, c > 0,
w_i > 0 and xi_i >= 0. Consider

    V(c) = max U(x) = sum_i w_i log(x_i + xi_i)
           subject to x >= 0 and A x <= c.

Only positive capacities and fixed routes and utilities are considered. When
xi_i = 0, finite utility requires x_i > 0. Positive feasible rates exist because
capacities are positive and the finite routing matrix has nonempty columns.
Each variable is bounded above by some capacity divided by a positive routing
entry. A finite optimum exists; strict concavity gives a unique primal optimum.
Write W = sum_i w_i. Natural logarithms are used. A gap divided by W is a
weighted utility difference, not a maximum per-flow throughput guarantee.

## Proposition 1 A reusable upper bound

For lambda >= 0 with q = A^T lambda > 0, define

    phi_i(q_i) = sup_{u >= 0} [w_i log(u + xi_i) - q_i u]
    x_i(q_i) = max(0, w_i/q_i - xi_i).

If q_i xi_i < w_i then

    phi_i(q_i) = w_i[log(w_i/q_i) - 1] + xi_i q_i.

Otherwise xi_i > 0 and phi_i(q_i) = w_i log xi_i. For any new positive capacity
vector c', set B(c',lambda) = c'^T lambda + sum_i phi_i(q_i). For any x feasible
at c',

    0 <= V(c') - U(x) <= B(c',lambda) - U(x).

Proof. The coordinate supremum is obtained by differentiating the strictly
concave scalar objective, then enforcing u >= 0. For feasible x, nonnegative
lambda gives U(x) <= U(x) + lambda^T(c' - Ax) <= B(c',lambda). Maximising the
left over feasible x proves the statement. This is standard weak duality.
The anchor need not be optimal: feasibility of x and validity of lambda are
sufficient. Floating-point implementation checks supplement, rather than
replace, this analytical statement.

## Proposition 2 Exact minimisation along a cached price ray

Fix lambda_0 with q_0 = A^T lambda_0 > 0. Put gamma = c'^T lambda_0 > 0 and

    h(t) = B(c',t lambda_0), t > 0.

The function h is convex, differentiable, and has the unique stationary point
determined by

    gamma = sum_i w_i (b - alpha_i)_+,
    b = 1/t, alpha_i = xi_i q_0i / w_i.

Proof. Differentiating each supremum by its unique maximiser gives

    h'(t) = gamma - sum_i (w_i/t - xi_i q_0i)_+.

The sum is continuous and strictly decreasing wherever positive. It tends to
infinity at t down to zero and to zero at t up to infinity. Thus h' has a unique
zero, which minimises convex h. Substitute b = 1/t to obtain the weighted
water-filling equation. The formula remains valid when some updated rates are
zero; replacing the positive-part expression with its all-active formula would
not generally be correct.

Sort alpha increasingly. Cache W_k = sum_{i<=k} w_i and
H_k = sum_{i<=k} w_i alpha_i, with W_0 = H_0 = 0. Define

    Gamma_k = alpha_k W_(k-1) - H_(k-1).

These breakpoints are nondecreasing, because
Gamma_(k+1) - Gamma_k = (alpha_(k+1) - alpha_k) W_k >= 0.
The active prefix k is identified from gamma between successive breakpoints,
and b = (gamma + H_k)/W_k. Ties may be assigned to either adjacent prefix since
the added term then has zero rate. A binary search identifies k once gamma is
available. Preparing q_0 and the sorted cache costs O(nnz(A) + d log d).
Computing gamma costs O(m); evaluating the full bound and constructing a
feasible allocation are not logarithmic-time operations.

This is an application of standard water-filling machinery. A cache that makes
repeated scalar queries cheap is an implementation choice, not an established
new algorithmic contribution.

## Proposition 3 A sharp Jensen bound for shifted-log scaling

Assume x_0 is the exact nominal optimum, every x_0i > 0, and a nominal optimal
dual lambda_0 satisfies KKT. Let 0 < s <= 1 and define

    theta_i = xi_i/(x_0i + xi_i), p_i = w_i/W,
    z_i = s + (1-s) theta_i, zbar = sum_i p_i z_i.

Then s x_0 is feasible at s c and

    [V(s c) - U(s x_0)] / W
       <= log(zbar) - sum_i p_i log(z_i)
       <= (1-s)^2 Var_p(theta) / (2 s^2).

Proof. Stationarity and complementary slackness imply
q_0i = w_i/(x_0i+xi_i), c^T lambda_0 = W(1-E_p theta), and
sum_i xi_i q_0i = W E_p theta. Ignore the nonnegativity lower bound in each
scalar conjugate, allowing u > -xi_i. This relaxation gives an upper bound
even if the relaxed scalar maximiser is negative. For t > 0,

    B_relaxed(s c,t lambda_0)
       = t W zbar + U(x_0) - W - W log t.

It is minimised at t = 1/zbar, yielding U(x_0) + W log zbar. On the primal side,
U(s x_0) = U(x_0) + sum_i w_i log z_i. Subtract to obtain the first inequality.
Since z_i >= s, the second derivative of -log z is at most 1/s^2 on the
interval. Taylor's inequality about zbar and averaging remove the linear term,
giving Var_p(z)/(2s^2) = (1-s)^2 Var_p(theta)/(2s^2).

If every xi_i = 0, the bound is zero. Exact scaling in that case is the familiar
iso-elasticity of proportional fairness, not a new result. More generally,
constant theta_i gives zero regret. This explains why similar rates and shifts
can make scaling particularly effective without attributing that behaviour
solely to the topology.

Sharpness of the first bound. Consider one link, choose positive w and
0 < theta_i < 1, set xi_i = w_i theta_i and x_0i = w_i - xi_i. With
c = sum_i x_0i, lambda_0 = 1 is nominal optimal. Choose s so that
max_i theta_i < zbar. All updated optimal rates remain positive and the
one-dimensional dual is the full dual. The first inequality is then equality.
The saved validation gives nine such cases, with agreement within 1e-12.

The exact-optimum and positive-rate assumptions matter. The generic numerical
certificate in Proposition 1 is used in experiments with approximate anchors
and zero nominal rates; the Jensen expression is not silently applied outside
its stated assumptions.

Small-change interpretation. With delta = 1-s, Taylor's theorem also gives

    delta^2 Var_p(theta)/2 <= Jensen(z)
        <= delta^2 Var_p(theta)/(2s^2).

The lower inequality bounds the Jensen expression, not actual regret on an
arbitrary network. Thus Jensen(z) = delta^2 Var_p(theta)/2 + O(delta^3) as
delta tends to zero. The sharp one-link family realises that leading term as
actual regret. For a fixed exact anchor, actual uniform-contraction regret is
therefore at most second order in delta. When Var_p(theta) > 0, a sufficient
condition for regret per total weight at most epsilon is

    delta <= a/(1+a), a = sqrt(2 epsilon/Var_p(theta)).

This is a sufficient aggregate utility condition under the stated exact KKT
assumptions, not a guarantee on an individual flow and not an empirical claim
about real failure sizes. The finite-anchor supplement removes the exactness
assumption with additional computable terms.

## Proposition 4 A price ray can reject an optimal repaired allocation

Take two disjoint unit-route links, w = (1,1), xi = (0,0), c = (1,1),
x_0 = (1,1), lambda_0 = (1,1). Change capacities to c' = (r,1), 0 < r < 1.
Routewise repair yields x = (r,1), the exact new optimum. Nevertheless the best
dual bound restricted to t lambda_0 has normalised gap

    [min_t B(c',t lambda_0) - U(x)]/2
      = (1/2) log[(1+r)^2/(4r)] > 0.

Proof. gamma = 1+r and the ray minimiser is t = 2/(1+r). Substitution into
the unshifted log dual gives B = 2 log[(1+r)/2], while U(x) = log r.
The expression follows and diverges as r down to zero. Thus no uniformly tight
gap estimate is available from a single fixed price direction under arbitrary
heterogeneous capacity changes. A failed certificate is not proof that its
primal allocation is poor. The certificate remains safe when it accepts.

## Proposition 5 A one-pass feasible candidate

Given v >= 0, let l = Av. For each used link with l_e > 0 put
r_e = min(1,c'_e/l_e); put r_e = 1 when l_e = 0. Set

    x_i = v_i min_{e: A_ei > 0} r_e.

Then x >= 0 and Ax <= c'. Indeed every term using link e is scaled by at most
r_e, so its new total load is at most r_e l_e <= c'_e. The procedure is a
feasibility repair, not the Euclidean projection or an optimal fairness-aware
repair. It is standard downscaling machinery. Comparing repaired anchor rates
and repaired ray-stationary rates improves the primal lower bound without
invalidating the certificate.

## Decision rule

For a feasible candidate x and the best cached ray bound, accept reuse only when
(B-U(x))/W <= epsilon. Otherwise invoke the common numerical solver at the
updated capacities, warm-started with the ray price. The fallback is not
guaranteed faster than a direct warm start. Its runtime, certificate coverage,
false-negative certification and preparation cost all require measurement.

The saved benchmark uses exactly the analytical upper bound and a feasible
primal candidate for every method. It does not turn small stationarity residuals
into unproved utility guarantees, claim interval-arithmetic certification or
infer a new paper's novelty from an unsuccessful keyword search.
