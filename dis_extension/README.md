# Learning to refine certified network allocations

This extension studies cost-sensitive algorithm selection for the main
certified NUM project. A fitted policy chooses whether to spend a small amount
of computation improving primal candidates and dual prices. Actual utility
certificates determine acceptance; predictions never certify a solution.

## Reproduction

Run from this directory with Python 3.12, the parent project's numerical
dependencies, scikit-learn 1.8.0 and threadpoolctl 3.6.0. Numerical-library
thread limits are set before NumPy imports and asserted during measurements.

The supplied result files are measured observations. Preserve them in another
directory before a complete rerun. Scripts intentionally reject accidental
overwriting of action timings, fitted fold models and replay timings.

    python pilot_check.py
    python experiment.py freeze
    python experiment.py collect
    python train_policy.py
    python experiment.py shift
    python experiment.py replay
    python analyse_extension.py
    python audit_extension.py

## Frozen policy follow up

The next study uses four previously unused public graph structures, fresh
nominal anchors and the original exported deployment model without refitting.
It compares one and four configured BLAS threads on the same CPU; this is not
cross-hardware replication. The primary comparator is the simple capacity rule.

    python transfer_study.py freeze
    python transfer_study.py prepare
    python transfer_study.py replay
    python transfer_study.py analyse
    python transfer_study.py audit

Its supplied observations are under `transfer_results`, with a frozen protocol,
model snapshot, source hashes, all 9,216 timings and first-repetition primal/dual
states for independent recomputation. A fresh rerun needs an empty
`transfer_results` folder, the unchanged historical training observations and
the four exact graph files under `data_external`. The source manifest records
Git blob identities, SHA256 digests, preprocessing and the original CC BY 4.0
licence location. Graph identities are disjoint from fitting, but the new graphs
still come from the same collection and are not random population samples.

The hindsight action-budget analysis uses held-out timings only for retrospective
diagnosis. It never supplies test timings to the online selector and is not a
deployable oracle or a guarantee of attainable expected runtime.

For a clean rerun of the first phase, use a copy of this project with an empty `results` directory.
The parent `results/instances` and public topology sources must be retained.
The frozen raw observations are supplied in the repository release asset.

## Data flow

The original 576 core capacity cases supply retrospective action observations.
Each of the two actions is measured three times. Models are fitted only to
the 360 cases rejected by the initial certificate. A complete outer topology
is held out, with an inner topology-held-out loop for model and threshold
selection. Outer training and test sets share no topology or anchor.

A separate 192-case evaluation changes capacity-shock distributions. It uses
48 nominal anchors from the original test settings, both flow counts and both
utility shifts. Consequently it tests new shock distributions on held-out
topologies; it is not a test on 192 independent networks or fresh nominal
anchors. No shift-test outcomes are used for fitting or selecting models.

Fresh paired replays measure six policies three times on all 768 cases.
All online feature extraction, prediction, refinement and fallback costs are
included. Data loading and model fitting are separate. Timing repetitions
measure execution variation and are reduced to one median per case.

## Files

- `certified_updates.py`: capacity-ratio predictor, bounded coordinate Newton
  correction, certificate checks, features and portable policy inference.
- `experiment.py`: fixed protocol, action collection, new capacity cases and
  paired policy replay.
- `train_policy.py`: nested group validation and fitted JSON policy records.
- `analyse_extension.py`: paired summaries, topology-block intervals and figures.
- `audit_extension.py`: saved-state, source-identity and split checks.
- `results/protocol.json`: specifications fixed before the reported collection.
- `results/action_runs.csv`: historical measured action costs.
- `results/features.csv`: online-accessible descriptors, identified by case.
- `results/fold_models.json`: outer-fold fitted policies for evaluation.
- `results/deployment_model.json`: all-core-data fit for future use; held-out
  performance is never attributed to this all-data fit.
- `results/split_manifest.json`: explicit topology and anchor partitions.
- `results/shift_instances`: updated capacities and tight reference arrays.
- `results/replay_runs.csv`: fresh end-to-end paired measurements, including
  outcomes that fail the target if any.
- `results/action_states`: one saved primal/dual pair per historical action
  and case, for numerical checks independently of timing records.
- `results/excluded_initial_run`: observations from an interrupted collection
  with inconsistent BLAS thread limits. They are excluded from training,
  selection, evaluation and figures; the execution correction is documented.

## Interpretation

Algorithm selection, warm starts, dual certificates and Newton updates are
established tools. The extension evaluates their particular combination under
explicit feature-access and grouped-validation constraints. Six convenience
topology families give a limited transfer experiment. Statistical intervals
describe this collection and do not establish population-wide performance,
first-in-literature priority, production readiness or journal suitability.

Primary methodological sources include Bischl et al., *ASlib: A Benchmark
Library for Algorithm Selection*, arXiv:1506.02465v3; the scikit-learn 1.8
cross-validation and common-pitfalls documentation; and the primary NUM sources
listed in the parent manuscript. 