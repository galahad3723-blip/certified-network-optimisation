# A computable extension for an inexact nominal allocation

Derived after the core benchmark was fixed and started, before inspecting its
comparative outcomes. This supplement does not change the benchmark methods or
thresholds. It is a mathematical extension, not an established priority claim.

Let x0 be any nominal feasible allocation with finite utility, and let lambda0
be any nonnegative price vector with q0 = A^T lambda0 > 0. An exact optimum and
strictly positive nominal rates are not required. Define

    p_i = w_i/W,
    theta_i = xi_i/(x0_i + xi_i),
    r_i = q0_i (x0_i + xi_i)/w_i,
    sigma = lambda0^T(c - A x0)/W >= 0.

For every uniform capacity factor s > 0, put

    z_i = s + (1-s) theta_i,
    a_i = r_i z_i,
    abar = E_p a_i.

Then s x0 is feasible at s c, every a_i is positive, and

    0 <= [V(s c) - U(s x0)]/W
       <= log(abar + s sigma) - E_p log a_i
        = [log abar - E_p log a_i] + log(1 + s sigma/abar)
       <= Var_p(a)/(2 min_i(a_i)^2) + log(1 + s sigma/abar).

Proof. Relax each scalar conjugate to u > -xi_i. For t > 0 its value is
w_i[log(w_i/(t q0_i)) - 1] + t xi_i q0_i. Therefore the relaxed dual minus
U(s x0), divided by W, is

    t D/W - 1 - log t - E_p log r_i - E_p log z_i,
    D = s c^T lambda0 + sum_i xi_i q0_i
      = W(abar + s sigma) > 0.

The minimum over t is at t = W/D, yielding the stated middle expression.
The true coordinate conjugate is no larger than the relaxed conjugate, so
minimising the true dual on the same ray can only improve this bound. The
identity separates a weighted Jensen gap from nonnegative capacity slack.
Taylor's theorem for -log on [min a_i,max a_i] gives the final inequality.

At an exact nominal KKT solution with every x0_i > 0, stationarity implies
r_i = 1 and complementary slackness gives sigma = 0. The bound becomes
the shifted-log Jensen expression in Proposition 3 of THEORY.md. Its variance
bound extends to s > 1 by replacing s^2 in the denominator with min(s,1)^2.
Under contractions, 0 < s <= 1, it reduces to the original statement.

The three sources of a large upper bound are now explicit: variability of
stationarity ratios r_i, variability of shift fractions theta_i, and weighted
unused capacity sigma. A loose variance upper bound does not imply large
actual regret. This remains a scalar-ray dual construction; it does not remove
the heterogeneous-change counterexample.

There is also an information-geometric interpretation. Define a probability
distribution ptilde_i = p_i a_i/abar. Then

    log abar - E_p log a_i = D_KL(p || ptilde),

so the finite-anchor bound is this relative entropy plus the nonnegative
slack term log(1+s sigma/abar). This identity follows immediately by
substituting ptilde into sum_i p_i log(p_i/ptilde_i). It is an interpretation
of the Jensen expression, not a new general relation between arithmetic
and geometric means or a lower bound on general-network regret.

When xi = 0, z_i = s, and the finite-anchor bound is independent of s. This is
consistent with the known identity V(s c) = V(c) + W log s: uniform scaling
preserves the absolute utility regret of any finite-utility feasible nominal
allocation, even if that allocation is inexact. Neither this identity nor
weak-duality certification is claimed as new.

The saved validation includes positive and zero nominal rates, contractions
and expansions, noncomplementary slack, and nonstationary prices. It checks
the displayed formula against the explicitly evaluated relaxed dual and checks
that the exact price-ray certificate never exceeds it. These are numerical
checks of the derivation, not a substitute for its proof or an originality
review.
