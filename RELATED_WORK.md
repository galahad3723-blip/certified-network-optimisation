# Related work and novelty audit

Prepared 22 October 2026. This is a targeted primary-source review, not an
exhaustive systematic review or proof that an unobserved result is new.

| Primary source | What it already establishes or studies | Consequence for this project |
| --- | --- | --- |
| Tian et al. Centralized Network Utility Maximization with Accelerated Gradient Method. ICNP 2022; author preprint arXiv:2408.08034v2, 2024. https://arxiv.org/abs/2408.08034 | Smooth-penalty NUM with accelerated gradient iterations. | A comparison only with plain gradient descent does not establish a new competitive solver. The present study changes to hard-capacity adaptation and does not inherit its rate theorem. |
| Borst, Walton and Zwart. Network iso-elasticity and weighted alpha-fairness. arXiv:1201.2292, 2012. https://arxiv.org/abs/1201.2292 | Network allocations with proportional scaling properties and their relationship to weighted alpha-fair utilities. | Exact uniform scaling for unshifted log utility is known. It must be a sanity check, not a claimed new contribution. |
| Boyd and Vandenberghe. Convex Optimization. 2004. https://web.stanford.edu/~boyd/cvxbook/ | Lagrangian duality, coordinate conjugates, KKT conditions and water-filling examples. | A feasible primal allocation plus a dual upper bound is standard. A reported certificate needs explicit assumptions and a valid finite bound. |
| Palomar and Fonollosa. Practical Algorithms for a Family of Waterfilling Solutions. IEEE TSP 53(2), 686-695, 2005. https://doi.org/10.1109/TSP.2004.840816 | Algorithms for water-filling solution families. | Sorted active-set scalar water filling is not claimed as new machinery. The specialised ray equation is derived in this project. Bibliographic metadata and the author publication page were verified; the linked repository PDF was access-blocked. |
| Criado, Martinez-Rubio and Pokutta. Fast Algorithms for Packing Proportional Fairness and its Dual. arXiv:2109.03678v2, 2022. https://arxiv.org/abs/2109.03678 | Accelerated width-independent methods for the proportional-fair packing problem and its dual. | A claim of the best first-order NUM method would require comparison with this literature. It is not made here. |
| Hou. Network Optimization in Dynamic Systems Fast Adaptation via Zero-Shot Lagrangian Update. arXiv:2412.07865v1, 2024; author record states accepted for IEEE INFOCOM 2025. https://arxiv.org/abs/2412.07865 | Capacity-change adaptation through first-order multiplier updates, including a single-resource rate-control formulation with different information assumptions. | Reusing prices after a capacity change is not new. A claim of distinction must concern exact certificates, the multi-link setting and the shifted-log result, not merely a zero-shot label. |
| Sreekumar, Degleris and Rajagopal. Large-Scale Network Utility Maximization via GPU-Accelerated Proximal Message Passing. IEEE Control Systems Letters 9, 2807-2812, 2025; related author version arXiv:2509.10722v2 revised September 2026. https://arxiv.org/abs/2509.10722 | GPU-compatible NUM, heterogeneous utilities and warm starting after capacity degradation, with very large synthetic problems. | CPU pilot timings cannot establish superiority over this implementation. Matched-model GPU comparisons remain absent. |
| Bothra et al. GATE GPU-Accelerated Traffic Engineering for the WAN. arXiv:2605.01748v2, 29 September 2026. https://arxiv.org/abs/2605.01748 | GPU-compatible traffic engineering, multiple fairness objectives, warm starts, feasibility repair and evaluation with production traces. | Feasibility repair and practical adaptation are not new by themselves. Its richer multipath and demand model is not interchangeable with this fixed-route benchmark. |
| Ndiaye, Fercoq, Gramfort and Salmon. Gap Safe Screening Rules for Sparsity Enforcing Penalties. JMLR 18(128), 1-33, 2017. https://jmlr.org/papers/v18/16-577.html | Duality-gap-based safe screening and dual scaling in sparse learning. | Computing a stronger dual point to certify a cheap decision has broad prior art. This is conceptual context rather than a direct NUM benchmark. |
| Knight et al. The Internet Topology Zoo. IEEE JSAC 29(9), 1765-1775, 2011. https://doi.org/10.1109/JSAC.2011.111002 | A curated collection of public network topology maps. | It supplies the six graph structures, not the experiment's capacities, traffic or error traces. Data attribution and preprocessing must be explicit. |

## Claims classified by status

| Claim | Current status |
| --- | --- |
| Uniform scaling is exact for unshifted logarithmic utility | Known iso-elasticity property, rederived as a check. |
| A dual bound can certify feasible allocation utility | Standard weak duality. |
| A price-ray minimisation becomes scalar weighted water filling | Derived for the stated model; uses standard optimisation machinery. No priority claim. |
| Shifted-log uniform-scaling regret has a sharp weighted Jensen bound and variance control | Proof supplied, numerical sharpness examples verified. A specialised candidate result requiring expert novelty review. |
| The construction extends to shifted alpha-fair utilities through a weighted-power Jensen expression | Separate proof and validation supplied; no transferred large-scale runtime claim or established priority. |
| A fixed ray can have an arbitrarily loose certificate despite exact repaired primal optimality | Explicit two-link counterexample and proof supplied. A structural limitation, not a performance guarantee. |
| Certified reuse is a practically better general update algorithm | Empirical question. Warm and ray-warm baselines, overhead, missed certificates and failed runs must be included. |
| The work is ready for a Q1 journal | Not established. New derivations and experiments are research progress; they do not establish priority, practical impact or journal acceptance. |

## Search scope and limits

The review used combinations of network utility maximisation, proportional
fairness, capacity scaling, iso-elasticity, warm starts, reoptimisation,
duality-gap certificates, Jensen gaps, water filling, zero-shot Lagrangian
updates and GPU NUM. Recent related work through the retrieval date was
checked. Search coverage can miss terminology and non-indexed material;
absence of an exact keyword match is not evidence of originality. The most
important remaining novelty check is the shifted-log Jensen bound and its
relationship to sensitivity and homothetic allocation theory.

## What would be needed before a journal submission

The mathematical contribution needs review against complete prior work by a
domain researcher. The CPU study needs extension to a current, matched-model
solver and hardware comparison. Actual capacity or traffic measurements, or a
clearly justified theoretical application, are needed to support claims about
operational value. Independent code/proof review and venue-specific formatting
remain outstanding. No journal has been contacted and no manuscript has been
submitted.
