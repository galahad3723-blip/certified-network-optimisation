"""Report the frozen external-graph test without changing fitted policies."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def results():
    folder=HERE/'transfer_results'
    summary=json.loads((folder/'summary.json').read_text())
    audit=json.loads((folder/'audit.json').read_text())
    assert audit['passed']
    return summary,audit


def abstract():
    summary,audit=results()
    a=summary['by_setting']['1']['methods']['learned']['vs_heuristic']
    b=summary['by_setting']['4']['methods']['learned']['vs_heuristic']
    status=('All follow-up timing runs meet the target. ' if summary['failed_runs']==0 else f"The follow-up records {summary['failed_runs']} failed timing runs. ")
    return ("Repeated optimisation creates a computational decision: when is a lightweight correction worth its cost? "
        "This study combines a capacity-ratio price predictor, two bounded coordinate Newton corrections and cost-sensitive selection between refinement and reuse. "
        "The predictor chooses computation; every accepted allocation must satisfy an actual feasible-primal/dual gap per total utility weight of at most 0.001. "
        "Historical action costs on 576 cases from six public topology structures train ridge and shallow-tree candidates with nested topology-held-out validation. "
        "An initial 768-case evaluation, including new capacity-change distributions, produces 13,824 fresh timing records and finds no consistent advantage over a simple capacity rule. "
        "A follow-up freezes the previously exported all-core model and tests four unused topology structures with 64 fresh nominal anchors and 256 updates. "
        "Six pipelines are measured under one and four configured BLAS threads on the same CPU, adding 9,216 timing records. "
        f"The frozen learner's median paired runtime ratios to the capacity rule are {a['median_ratio']:.3f} and {b['median_ratio']:.3f}; "
        f"corresponding sum-of-case-median ratios are {a['total_time_ratio']:.3f} and {b['total_time_ratio']:.3f}. "
        f"{status}"
        "A hindsight cost-budget diagnostic distinguishes the potential value of action selection from the overhead of using a fitted policy. "
        "All online feature, prediction, correction and fallback costs are charged. Public graph structures, synthetic workloads, few convenience graph families and one machine limit external inference.")


def append_sections(m):
    summary,audit=results()
    policy=json.loads((HERE/'transfer_results/policy_snapshot.json').read_text())
    one=summary['by_setting']['1'];four=summary['by_setting']['4']
    a=one['methods']['learned']['vs_heuristic'];b=four['methods']['learned']['vs_heuristic']
    methods=['ray_warm','ray_reuse','always_refine','heuristic','train_best','learned']
    labels=['Ray warm start','Original reuse','Always refine','Capacity rule','Training fixed','Frozen learner']
    m.heading('9 Frozen policy transfer and computational value',newpage=True)
    m.p('The first phase gives a sharper question than whether a model can beat the original reuse pipeline. A simple capacity rule is already competitive, so the relevant comparison is whether a fitted selector adds net value over that rule on fresh graph structures and nominal problems. The follow-up protocol, graph identities, workload settings, fitted policy snapshot and source hashes were fixed before generating or timing its new action outcomes. The earlier results motivated this test; it is not an externally preregistered or blinded replication.')
    m.sub('Previously unused graphs and fresh nominal problems')
    m.p('DFN, GARR 201201, SURFnet and BT Europe are four additional Topology Zoo structures from the same pinned source commit [7]. After the same deterministic preprocessing, they have respectively 58, 61, 50 and 24 nodes, with 87, 75, 68 and 37 simple undirected edges. Their graph identities are absent from the six training graphs. They are convenience-selected historical structures from the same collection, may share geographical context and do not establish statistical independence of network populations.')
    m.p('Two new route seeds, 1701 and 1907, are crossed with 1,000 and 10,000 flows, the two nominal-capacity laws and shifts 0 and 0.5. This gives 64 new nominal anchors, rather than reusing earlier test anchors. Each produces four capacity changes: uniform 10% reduction; 30% reduction on a random 5% of used links; heterogeneous reductions up to 30%; and factors between 0.8 and 1.2, allowing recovery. The resulting 256 updates share the original workload generator and fixed-route utility family. They do not represent independent production traffic measurements or a new application domain.')
    m.p('The learner is the all-core deployment model exported before this follow-up, fitted only on the earlier six-graph action observations. Its coefficients, preprocessing and decision threshold are unchanged. Test reference solutions, current-case action runtimes and graph names remain unavailable to online inference. The training-fixed comparator is chosen once from the historical rejected-case mean action-time ratio and uses '+('refinement' if policy['training_fixed']['refine'] else 'the original reuse action')+' after an initial certificate fails. No external-case outcome selects that fixed action.')
    m.sub('One CPU under two numerical library limits')
    m.p('Each of the six pipelines is replayed three times on every case under configured BLAS thread limits of one and four, giving 9,216 additional timing records. Both loaded NumPy and SciPy BLAS pools are checked at the requested limit. The same CPU, software and stored instances are used. Not every sparse or Python operation parallelises, so the comparison is sensitivity to numerical-library configuration, not a four-worker algorithm or cross-hardware validation.')
    m.p('Configuration order alternates between cases, and method order rotates within repetitions. Data loading, thread-limit context changes and offline preparation are outside online timers; features, prediction, repair, certificates, corrections and fallback are charged as in the first phase. Each method starts from the same nominal cache rather than inheriting another method\'s solution. All measured failures remain in the primary summaries; a case is counted solved only if all three repetitions meet the target.')
    m.figure('05_new_graph_validation','Figure 5. Fresh graph validation with the previously frozen learner. Points show median paired runtime ratios to the simple capacity rule under one and four configured BLAS threads on the same CPU. These are descriptive measurements from four graph structures; values below one favour the displayed pipeline.')
    rows=[]
    for method,label in zip(methods,labels):
        u=one['methods'][method]['vs_heuristic'];v=four['methods'][method]['vs_heuristic']
        rows.append((label,f"{u['median_ratio']:.3f}",f"{v['median_ratio']:.3f}",f"{u['total_time_ratio']:.3f}",f"{v['total_time_ratio']:.3f}"))
    m.table(['Pipeline','Median one thread','Median four threads','Total one thread','Total four threads'],rows,[1.85,1.25,1.25,1.25,1.25],font=9.0)
    m.p(f"The frozen learner's median ratio to the rule is {a['median_ratio']:.3f} at one thread and {b['median_ratio']:.3f} at four; the corresponding sum-of-case-median ratios are {a['total_time_ratio']:.3f} and {b['total_time_ratio']:.3f}. Its win fractions are {100*a['win_fraction']:.1f}% and {100*b['win_fraction']:.1f}%. At the 90th percentile, the ratios are {a['p90_ratio']:.3f} and {b['p90_ratio']:.3f}. The median, aggregate cost and slower tail should be considered together.")
    m.p('The observed learner-to-rule total-cost ratio exceeds one for every one of the four new graphs under both thread configurations. At four threads, a favourable paired median therefore coexists with a higher aggregate cost. This pattern is not explained by a single unfavourable graph, and a favourable median alone is insufficient evidence that the learning policy reduces the workload\'s total computation.')
    common_one=one['methods']['learned']['common_success_vs_heuristic']
    common_four=four['methods']['learned']['common_success_vs_heuristic']
    m.p(f"All six pipelines certify all repetitions on {one['common_success_cases']} of 256 cases at one thread and {four['common_success_cases']} at four. On those common-success subsets, the learner-to-rule median ratios are {common_one['median_ratio']:.3f} and {common_four['median_ratio']:.3f}. The full follow-up contains {summary['failed_runs']} failed timing runs. These conditional comparisons do not replace the full-workload outcomes.")
    if summary['failed_runs']:
        m.table(['Pipeline','Solved one thread','Solved four threads'],[
            (label,str(one['methods'][method]['solved'])+' / 256',str(four['methods'][method]['solved'])+' / 256')
            for method,label in zip(methods,labels)],[2.75,2.05,2.05],font=9.2)
    graph_rows=[]
    for graph in summary['graphs']:
        u=one['learner_vs_heuristic_by_topology'][graph];v=four['learner_vs_heuristic_by_topology'][graph]
        graph_rows.append((graph,f"{u['median_ratio']:.3f}",f"{v['median_ratio']:.3f}",f"{u['total_time_ratio']:.3f} / {v['total_time_ratio']:.3f}"))
    m.table(['New graph','Median one thread','Median four threads','Total ratio one / four'],graph_rows,[1.45,1.65,1.65,2.1],font=9.1)
    small_one=one['learner_vs_heuristic_by_size']['1000'];small_four=four['learner_vs_heuristic_by_size']['1000']
    large_one=one['learner_vs_heuristic_by_size']['10000'];large_four=four['learner_vs_heuristic_by_size']['10000']
    m.p(f"At 1,000 flows, learner-to-rule median ratios are {small_one['median_ratio']:.3f} and {small_four['median_ratio']:.3f} under one and four configured threads. At 10,000 flows they are {large_one['median_ratio']:.3f} and {large_four['median_ratio']:.3f}. These size strata were specified before evaluation and each contains 128 update cases. The comparison examines whether selection cost is better amortised by larger numerical work; it does not isolate problem size from graph structure, solver behaviour and timing variation.")
    m.p('The unit of structural transfer is a graph identity. The 64 updated cases within each new graph are correlated through the structure and partially shared routes; three timing repetitions add execution observations, not independent networks. No population confidence interval is inferred from these four graph structures. A change in the measured ordering between configurations is evidence about this host and library setup, rather than proof of hardware-independent model quality.')
    m.sub('How much computation could selection be worth')
    m.p('For diagnosis only, each case is assigned the smaller of the measured median times of the two base actions: original reuse or always refine. Subtracting this hindsight best-of-two cost from the measured capacity-rule cost gives an optimistic budget for additional selection work, clipped at zero. The calculation uses held-out runtimes after evaluation and cannot be used by the frozen policy. Noise, the minimum over observed timings and separate replay paths can make it optimistic; it is not a theorem about attainable expected runtime.')
    m.figure('06_selection_budget','Figure 6. Fraction of initially rejected cases with at least the displayed hindsight budget for extra computation, relative to the simple capacity rule. Dashed lines mark the measured median feature-plus-prediction cost of the learner. The budget is a retrospective diagnostic using test timings, not an online oracle or a deployable policy.')
    m.p(f"Among {one['rejected_cases']} initially rejected cases at one thread, the median learner feature-plus-prediction cost is {one['median_gate_overhead_us']:.1f} microseconds and the median hindsight budget is {one['median_hindsight_budget_us']:.1f} microseconds. The observed budget covers that case's measured gate cost in {100*one['budget_covers_measured_gate_fraction']:.1f}% of rejected cases. At four threads the corresponding values are {four['median_gate_overhead_us']:.1f} microseconds, {four['median_hindsight_budget_us']:.1f} microseconds and {100*four['budget_covers_measured_gate_fraction']:.1f}%. Even perfect identification of the observed cheaper action would not make a fixed gate overhead worthwhile on every case.")
    m.p(f"The hindsight best-of-two sum-of-case-median ratios to the capacity rule are {one['hindsight_best_total_vs_heuristic']:.3f} and {four['hindsight_best_total_vs_heuristic']:.3f}. Among rejected cases the learner disagrees with the observed cheaper action on {100*one['hindsight_action_disagreement_fraction']:.1f}% and {100*four['hindsight_action_disagreement_fraction']:.1f}%. These diagnostics separate opportunity, observed action ranking and gate cost. They do not establish that the available online features could recover a hindsight oracle, and no fitting uses these test-derived labels.")
    m.p('The median observed budget exceeds the measured median gate cost under both configurations, and most rejected cases have a budget large enough to cover their measured gate cost. Overhead alone therefore does not describe all of the observed difficulty. Attention should also turn to the transfer of action-cost relationships and the expensive cases that dominate aggregate computation. The present retrospective comparison does not isolate their separate causal contributions or show that a different model can exploit the hindsight opportunity.')
    m.sub('Audit and implications for the next research step')
    m.p(f"The follow-up audit independently recomputes all {audit['stored_states_recomputed']:,} first-repetition primal/dual outputs and {audit['policy_decisions_recomputed']} configuration-specific policy decisions. The maximum saved-gap discrepancy is {audit['maximum_saved_gap_error']:.2g}; the maximum observed relative overload is {summary['maximum_overload']:.2g}. The largest gap of an accepted run is {summary['maximum_accepted_gap']:.6g}. Nominal and updated reference misses number {audit['nominal_reference_misses']} and {audit['updated_reference_misses']}. Policy identity, disjoint training/test graph identities, instance hashes, numerical sources and configured BLAS limits pass the recorded checks.")
    if all(r[k]<1 for r in [a,b] for k in ['median_ratio','total_time_ratio']):
        m.p('The frozen learner improves both the paired median and aggregate observed cost relative to the capacity rule under both configurations in this follow-up. This extends the positive evidence to the specified fresh graph collection. It does not remove the unfavourable shifted-shock comparison from the first phase or establish a general advantage on other machines, workloads or graph populations.')
    else:
        m.p('The follow-up does not show an advantage over the simple rule across both the paired median and aggregate cost under both configurations. Together with the first phase, this makes the cost of selection and transfer of runtime relationships central research questions. A higher-capacity predictor should be justified by net computational value, rather than by prediction complexity or apparent training fit.')
    m.p('The next experiment should prioritise independent workload provenance and a genuinely different machine, while retaining a frozen-policy test and inexpensive rule baselines. Sequential capacity updates with explicit cache-refresh and retraining costs would address amortisation. Training any new policy on these follow-up outcomes would require a further untouched test collection; its future performance could not be attributed to the frozen test reported here.')
