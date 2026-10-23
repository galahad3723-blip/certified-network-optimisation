# Extension to shifted alpha fair utility

This analytical supplement was derived after the log-utility benchmark was
fixed, without changing its methods or inspecting comparative outcomes. It
does not turn the log-utility timing results into a benchmark for other
utilities. Its specialised priority remains unestablished.

For alpha > 0, alpha != 1, consider

    U_alpha(x) = sum_i w_i (x_i + xi_i)^(1-alpha)/(1-alpha).

The alpha = 1 limit is weighted shifted-log utility up to an allocation-
independent constant. The constraints are unchanged.

## Proposition A Uniform scaling has a sharp weighted Jensen bound

Assume the nominal optimum x0 has strictly positive rates and satisfies KKT.
Write y0_i = x0_i + xi_i, and define

    v_i = w_i y0_i^(1-alpha), M = sum_i v_i, p_i = v_i/M,
    theta_i = xi_i/y0_i, z_i = s + (1-s)theta_i, zbar = E_p z_i.

For 0 < s <= 1,

    0 <= [V_alpha(s c) - U_alpha(s x0)]/M
       <= [zbar^(1-alpha) - E_p z_i^(1-alpha)]/(1-alpha)
       <= alpha (1-s)^2 Var_p(theta)/(2 s^(alpha+1)).

The displayed first upper bound is nonnegative for both alpha < 1 and
alpha > 1. For alpha > 1 the power is negative and convex, and the
denominator is negative; ignoring that sign would reverse the argument.

Proof. Nominal stationarity gives q0_i = w_i y0_i^(-alpha).
Complementary slackness gives c^T lambda0 = M(1-E_p theta).
Relax each coordinate supremum to y_i > 0, removing x_i >= 0. Its conjugate is

    phi_rel(q) = alpha/(1-alpha) w_i^(1/alpha)
                q^((alpha-1)/alpha) + xi_i q.

Along the ray t lambda0, at capacities s c the relaxed dual is

    h_rel(t) = [alpha/(1-alpha)] M t^((alpha-1)/alpha)
               + t M zbar.

Its derivative is M[zbar - t^(-1/alpha)], so the minimiser is
t = zbar^(-alpha) and the minimum is
M zbar^(1-alpha)/(1-alpha). Scaling the primal gives
U_alpha(s x0) = M E_p z_i^(1-alpha)/(1-alpha).
Subtract to obtain the first bound. For
f(z) = z^(1-alpha)/(1-alpha), f''(z) = -alpha z^(-alpha-1).
Taylor's inequality on [s,1] gives the variance upper bound.

Sharpness. Take one link, choose positive y0 and 0 < theta_i < 1,
set w_i = y0_i^alpha, xi_i = y0_i theta_i and
x0_i = y0_i(1-theta_i), and let c = sum_i x0_i.
Nominal lambda0 = 1 satisfies KKT and v_i = y0_i.
If max theta_i < zbar, every updated rate is positive, the relaxed dual
is the true dual and the ray is the full one-link dual. Equality holds
in the first upper bound.

The bounds on the Jensen expression itself are

    alpha (1-s)^2 Var_p(theta)/2
      <= Jensen_alpha(z)
      <= alpha (1-s)^2 Var_p(theta)/(2 s^(alpha+1)).

As in the logarithmic case, the lower expression is not a lower bound on
regret for an arbitrary network. It is attained asymptotically in the sharp
family. Capacity expansions s > 1 use min(s,1)^(alpha+1) in the variance
denominator. Vanishing shifts give zero regret, in agreement with known
alpha-fair iso-elasticity. The result reduces continuously to the log bound
as alpha tends to one.

## Proposition B The exact alpha fair price ray is also water filling

For arbitrary nonnegative nominal prices with q0 > 0, define

    a_i = (w_i/q0_i)^(1/alpha), g_i = q0_i a_i,
    beta_i = xi_i/a_i, gamma = cnew^T lambda0.

The stationary nonnegative rate at price t q0 is

    x_i(t) = max(0, a_i b - xi_i), b = t^(-1/alpha).

The exact ray optimum solves

    gamma = sum_i g_i (b-beta_i)_+, t = b^(-alpha).

This follows by differentiating the true coordinate supremum, whose
maximiser is the displayed rate. The same sorted weighted prefix cache
therefore applies after replacing log-case weights and breakpoints by
g and beta. Nonnegativity is respected, including inactive flows. This
is a model-specific reduction to standard water filling, not a claim
that water filling or shifted alpha fair utilities are new.

## Numerical checks and limits

The supplement supplies a separate validation for alpha = 0.2, 0.5, 1, 2, 4.
It compares the active-set ray bound with an independent scalar optimiser,
checks one-link sharpness for multiple weights and contraction factors,
and checks continuity close to alpha = 1. The main six-topology runtime
study still uses alpha = 1 only. No runtime superiority or general
deployment claim for the extended family is made.
