# Reproducing the final study

## Environment and data

Use Python 3.12 and install the pinned dependencies:

```bash
python -m pip install -r requirements-learning.txt
python download_data.py
```

For offline use:

```bash
python download_data.py --archive /path/to/Certified_Network_Optimisation_Data.zip
```

Add `--verify-only` to check the archive without installing it. The downloader verifies the archive digest, every manifest entry and the complete archive inventory. Existing different observations are rejected rather than overwritten.

## Audit the recorded results

```bash
python audit_saved_results.py
cd dis_extension
python audit_extension.py
python transfer_study.py audit
```

The checks recompute stored certificates, feasible allocations, data splits and policy decisions. They retain failures and verify source identities. Their scope is Float64 consistency, rather than interval arithmetic or independent external replication.

## Recompute summaries and figures

From the repository root:

```bash
python analyse_benchmark.py
cd dis_extension
python analyse_extension.py
python transfer_study.py analyse
```

These analyse saved measurements. Timings cannot be reproduced identically on a different machine.

## Collect new measurements

Use a separate checkout and keep the released data intact. `run_benchmark.py` writes to `results/`. The learning stage uses the original instance arrays; its stage order is documented in `dis_extension/README.md`. The transfer study provides `freeze`, `prepare`, `replay`, `analyse` and `audit` stages; run its `--help` for arguments.

The recorded NUM experiment uses one BLAS thread. The new-graph validation compares one and four threads on the same CPU. Analysis reports full online costs, including features, prediction, correction, certificates and fallback.

## Final manuscript

The final ten-page manuscript is in `paper/`. PDF and Word contain the same abstract and numerical findings. Earlier standalone NUM and DIS manuscript builders are not part of this release. Execution checkpoints and interrupted runs are retained only as numerical evidence in the data archive; they are excluded from the reported comparisons as specified in the protocols.
