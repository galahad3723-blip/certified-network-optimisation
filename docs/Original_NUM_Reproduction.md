# Certified reuse for network utility maximisation

A personal research project of Kai Chi, dated 22 October 2026. The
question is whether a feasible allocation and a computable dual upper bound
can avoid unnecessary optimisation after capacities change. The study includes
proofs, a sharp shifted-log error bound, an explicit limitation counterexample,
public topology structures, controlled CPU comparisons and all measured
failures. Publication priority and journal readiness have not been established.

## Data guided update extension

`dis_extension/` adds a cost-sensitive choice between the original reuse
action and a bounded numerical correction. It includes nested validation
with complete topologies held out, 192 additional capacity-shock cases,
fresh timing of six pipelines, fitted portable policies and saved-state audits.
An explicit primal/dual certificate still determines solution acceptance.
Read `dis_extension/README.md` for the separate reproduction pipeline and
`dis_extension/RESEARCH_GUIDE_ZH.md` for the scientific interpretation.
The companion report is *Learning to Refine Certified Network Allocations*.
The frozen-policy follow-up adds four unused graph structures, fresh nominal
anchors and a one/four-thread configuration comparison on the same CPU; it
measures net selection value relative to the inexpensive capacity rule.

## Reproduce the numerical study

Use Python 3.12 and the versions in `requirements.txt`. Run each command in a
fresh process from this folder. The scripts set numerical-library threads to
one before importing NumPy. An otherwise idle CPU gives more useful timings.

```bash
python -m venv .venv
# Activate the environment with the command appropriate to your operating system.
python -m pip install -r requirements.txt
python validate_theory.py
python validate_finite_anchor.py
python validate_alpha_extension.py
python validate_primal.py
python run_benchmark.py
python ablate_certificate.py
python analyse_benchmark.py
python audit_saved_results.py
```

`run_benchmark.py` overwrites `results/` with a complete rerun and can take tens
of minutes or longer. Preserve the supplied observations in another folder
before rerunning. No partial-run option is used for the reported results.
`results/environment.json` records source hashes and execution metadata.
Those hashes identify the execution-time files. Subsequent source-header and
status-description edits are recorded in `results/source_text_revision.json`;
the numerical AST was checked to be unchanged. The audit accepts either exact
execution hashes or these documented text revisions.
`results/hardware.json` records the completion-session CPU and resource limits;
processor metadata for the pre-resume segment were not recorded.
Timing variation across machines and operating-system activity is expected.

The supplied execution stopped after 154 complete anchors and was continued
with `python resume_benchmark.py`. The last two scaling anchors were measured
in a later process. Existing within-case timings were retained exactly. The
original full wall time is unavailable; only the resumed segment wall time
is recorded. `results/preresume_checkpoint/` and `results/resume_history.json`
preserve the checkpoint and resume instrumentation. A complete fresh run
of `run_benchmark.py` does not require resumption.

The protocol is fixed in `results/protocol.json`: 144 core nominal anchors,
576 core capacity cases, 12 scaling anchors and 24 scaling cases. Four methods
are measured three times per capacity case, producing 7,200 raw timing runs.
The timing repetitions are not independent networks. Inference is limited to
six convenience-selected topology families; bootstrap intervals resample those
families and preserve the settings within each family.
The 144 core anchors share 36 route matrices; the scaling extension has six
additional route matrices. Anchor counts are not counts of independent graphs.

## Read the evidence

- `THEORY.md`: model, scalar conjugate, exact price-ray minimisation, a sharp
  shifted-log Jensen bound, a divergent-gap counterexample and feasibility.
- `FINITE_ANCHOR_EXTENSION.md`: a computable bound for any finite-utility
  feasible anchor, approximate prices and arbitrary uniform capacity factors.
- `ALPHA_FAIR_EXTENSION.md`: a sharp weighted-power Jensen bound and exact
  ray reduction for shifted alpha-fair utilities. This is a separate
  theoretical supplement; the large benchmark still uses log utility only.
- `RELATED_WORK.md`: primary-source positioning and explicit limits on novelty.
- `certified_num.py`: actual solver, feasibility repair, price cache and measured
  method wrappers. It is not copied from the starting paper.
- `run_benchmark.py`: full deterministic experiment and saved instances.
- `analyse_benchmark.py`: paired summaries, clustered intervals and six figures.
- `ablate_certificate.py`: untimed two-by-two controls for price and primal
  candidate improvements; these controls do not replace measured methods.
- `validate_theory.py`, `validate_finite_anchor.py`, `validate_primal.py` and
  `audit_saved_results.py`: independent numerical and saved-result checks.
- `results/anchors.csv`, `cases.csv`, `runs.csv`: raw observations, including
  unsolved runs. `per_case_methods.csv` contains timing medians, not new samples.
- `results/instances/`: all anchor and updated problem arrays, primal candidates
  and dual reference vectors. These allow certificate recomputation.
- `results/failures.json`: nominal and updated reference misses, even if empty.
- `results/summary.json`: all headline values used in the manuscript.
- `figures/`: PNG and vector PDF exports of the six scientific figures.
- `RESEARCH_GUIDE_ZH.md`: Chinese explanation of the research and its limits.
- `PROVENANCE.md`: experiment records, data sources and licence information.

## Data and methods

Only the graph structures are public observations. Routes, utility weights,
capacities, nominal workloads and capacity shocks are generated. The six
Internet Topology Zoo files are pinned to commit
`51118849b99534f01010d885d66321433a7eef9e` of
https://github.com/mroughan/InternetTopologyZoo . The exact source manifest and
CC BY 4.0 licence are in `data/InternetTopologyZoo/`. Historical topology maps
are not evidence of current network operation or measured failures.

All four measured methods use the same L-BFGS-B implementation and the same
feasible-primal/dual stopping target. Their distinction is how they initialise
prices and whether the reusable bound skips optimisation. The strong ray-warm
baseline shares the exact scalar price adjustment. The reuse method pays its
precheck overhead even when certification fails. Preparation cost and nominal
anchor solve cost are recorded separately, and amortised comparisons are
provided. Tight references may use additional safeguarded Newton steps; those
steps are not included in the measured methods or presented as free deployment
information. Updated reference bounds define intervals for candidate regret,
rather than treating an approximate reference value as the exact optimum.

No GPU solver, current state-of-the-art conic solver, production traffic trace,
online sequence, multipath route optimisation or maximum individual-flow loss
guarantee is part of this experiment. A gap per total utility weight controls
aggregate log utility. It does not promise a per-user throughput floor.

## Starting paper and research independence

The starting reference was Ying Tian, Zhiliang Wang, Xia Yin, Xingang Shi,
Jiahai Yang and Han Zhang, *Centralized Network Utility Maximization with
Accelerated Gradient Method*, IEEE ICNP 2022, author preprint
https://arxiv.org/abs/2408.08034 . The present hard-capacity adaptation study
changes the problem and does not reproduce that paper's algorithm or inherit
its convergence theorem.

## Manuscript reproduction and reuse

`build_manuscript.py` and `native_equations.py` generate the DOCX using
`python-docx` and Pandoc. Display equations are native editable Word math.
The numerical study does not require Pandoc or document libraries. The
delivered PDF is a rendered export of the DOCX;
all pages were visually inspected. No unexecuted notebook is represented as a
research execution log. `SHA256SUMS.txt` records the packaged files.
The companion Markdown manuscript retains the display equations as TeX for
copying and further mathematical editing.

To rebuild the manuscript outside the original environment, install Pandoc
and the document libraries listed in `requirements.txt`, then run
`python build_manuscript.py` after the analyses and audits. The equation
renderer uses Node from PATH unless the original runtime variable is set.
Export the resulting DOCX with Word or LibreOffice. The supplied rendered
manuscript does not require those tools to read.

The code appendix contains extracts from the actual executed source. The full
code package is supplied separately. The original numerical archive predates this public repository. Retain provenance and third-party attribution if sharing this
work. The package supports verification and further research.
