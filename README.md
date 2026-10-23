# Certified Network Optimisation

Certified reuse and cost-sensitive algorithm selection for network utility maximisation.

**[Final paper](paper/Certified_Network_Optimisation.pdf)** · [Word version](paper/Certified_Network_Optimisation.docx) · [Reproduction instructions](REPRODUCING.md) · [Experiment data](https://github.com/galahad3723-blip/certified-network-optimisation/releases/tag/v1.0.0)

The study asks when a previous network allocation can be reused after link capacities change, and whether learning can reduce the cost of further updates. A computable primal–dual bound determines acceptance. The learned policy chooses whether to attempt a bounded price correction.

## Findings

| Evaluation | Result |
|---|---|
| Certified reuse | 216 of 576 core updates are accepted without iterative optimisation at a normalised utility-loss tolerance of 0.001. |
| Nonuniform changes | The median paired runtime ratio to the strong ray warm start is 1.03. |
| Frozen policy on four unseen graphs | Across 256 new updates, learned selection costs 10.8% and 11.5% more than the simple capacity rule under one and four BLAS threads on the same CPU. |

The final paper is ten pages, including references, with no appendices.

## Reproduce

Python 3.12 is recommended.

```bash
python -m venv .venv
# Activate the environment for your operating system.
python -m pip install -r requirements-learning.txt
python download_data.py
python audit_saved_results.py
cd dis_extension
python audit_extension.py
python transfer_study.py audit
```

The data download is verified against a published SHA256 digest and an internal file manifest before installation. It contains the recorded arrays, timings, fitted-policy evidence, failures and execution records required by the audits. It contains no manuscript drafts or document-generation scripts.

## Repository contents

| Path | Contents |
|---|---|
| `paper/` | Final paper in PDF, Word and Markdown formats |
| `certified_num.py` | Model, dual bounds, feasibility repair and shared solver |
| `run_benchmark.py`, `analyse_benchmark.py` | Benchmark collection and analysis |
| `audit_saved_results.py`, `validate_*.py` | Numerical consistency checks |
| `dis_extension/` | Bounded correction, policy training, evaluation and transfer study |
| `results/` | Benchmark protocols, final summaries and numerical checks |
| `data/`, `dis_extension/data_external/` | Attributed public topology sources |
| `media/` | Selected result figures |

## Data and scope

Network structures are from Internet Topology Zoo. Routes, capacities, weights and shocks are generated, rather than production traffic measurements. Execution failures remain in the data. Timing repetitions measure execution variation; they are not independent networks. The thread comparison uses one CPU.

Upstream topology attribution and the CC BY 4.0 licence are retained in `data/InternetTopologyZoo/`. See [PROVENANCE.md](PROVENANCE.md) for data sources and execution-record details.

Author: Kai Chi.
