# Correctness of data guided certified updates

## Mathematical problem

The extension uses the same fixed-route hard-capacity problem as the main
study: maximise the weighted shifted-log utility U(x), subject to x >= 0 and
Ax <= c. Weights and capacities are positive, utility shifts are nonnegative,
and every route is nonempty. All updated capacities in this experiment remain
strictly positive. Topology structures are public; workload parameters and
capacity changes are synthetic.

## A learned policy does not provide the certificate

For any feasible x and any nonnegative link price vector lambda with positive
route prices, weak duality gives

    0 <= V(c) - U(x) <= B(c, lambda) - U(x).

A policy may select either the original price-ray update or the lightweight
refinement. Its prediction does not enter this inequality. Each action repairs
its candidate against the actual updated capacities and constructs an actual
dual value. An output is accepted only when the gap divided by total utility
weight is at most 0.001. If the inexpensive action does not meet the target,
the same L-BFGS-B fallback is invoked. A failed fallback is recorded as a
failure, rather than accepted on the policy's prediction.

The selector can therefore make an expensive computational choice without
changing the mathematical validity of an accepted output. This is a standard
weak-duality consequence, not a new general learning guarantee. The code uses
Float64 and feasibility guards; it does not establish interval arithmetic or
machine-checked numerical guarantees.

## Independent primal and dual incumbents

Let x_j be any repaired candidates and lambda_j any valid prices examined so
far. Retain the candidate with maximal utility and the price vector with
minimal dual value. Their pair still satisfies weak duality, even when the
two incumbents came from different update steps. The retained gap cannot
increase as more candidates are examined. No claim is made that actual
iteration time decreases when more candidates are examined.

## Lightweight refinement

First propose componentwise capacity-ratio prices

    lambda_ratio[e] = max(1e-12, lambda0[e] * c0[e] / c[e]).

This predictor is a heuristic on coupled networks. On independent links with
unshifted log utility and an exact nominal solution, it produces exact updated
prices: x_i = c_i, lambda_i = w_i/c_i. In particular it resolves the two-link
ray-restriction counterexample in the original study. This special case is
elementary and does not establish novelty or a coupled-network approximation
bound.

If certification still fails, attempt at most two local Newton corrections.
At prices lambda, write q = A^T lambda and g = c - A x(q). Within a fixed
positive-rate active set, the dual Hessian is

    H = A diag(w_i/q_i^2 * 1[q_i*xi_i < w_i]) A^T.

Select at most eight eligible coordinates by |g_e|/sqrt(H_ee + ridge).
Coordinates at the positive price floor are eligible only when their gradient
points towards increasing price. Solve the eight-dimensional regularised
Newton system, project prices to the positive floor, and safeguard with an
Armijo line search of at most eight trials. Only valid primal and dual
incumbents are retained. The Hessian formula is local, and rate activity can
change; no global two-step convergence theorem is asserted.

## Learning target and independence of evaluation

For historical cases rejected by the initial certificate, the target is
log(T_refine / T_reuse), where each T is a median of three measured complete
action runtimes. Ridge regression and shallow regression trees predict this
cost ratio. The decision threshold and model specification are selected by
inner leave-one-topology-out validation. Evaluation then uses an outer
topology that was excluded from all fitting and inner model selection.

Training targets may use historical measured runtimes. Online features may
not use the current case's measured action runtimes, updated reference prices,
updated reference allocations or optimal values. Topology names, case IDs and
shock labels are also excluded. Preprocessing statistics are fitted using
training features only. The policy predicts computational value, not solution
quality, and its held-out accuracy is not a probabilistic safety certificate.
