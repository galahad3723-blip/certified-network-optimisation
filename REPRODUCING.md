# Reproducing the numerical evidence

The PDF is the combined ten-page report. Historical notes and intermediate
manuscripts inside the evidence archive predate that combined report.

## Verify existing observations

Run from the repository root with Python 3.12:

```bash
python -m pip install -r requirements-learning.txt
python download_data.py
python audit_saved_results.py
cd dis_extension
python audit_extension.py
python transfer_study.py audit
```

For an offline archive:

```bash
python download_data.py --archive /path/to/Certified_Network_Optimisation_Source_and_Data.zip
```

`download_data.py --verify-only --archive ...` checks all archived files without
installing observations. The release preserves the original 1,244-entry package,
including its file manifest, raw timings, failures and saved numerical states.

## Recompute summaries and figures

After loading the observations:

```bash
python analyse_benchmark.py
cd dis_extension
python analyse_extension.py
python transfer_study.py analyse
```

These commands analyse recorded observations rather than collect new timing
samples. Runtime on a different machine will not reproduce identical timings.

## Collect new observations

Use a separate copy of the repository and preserve the released observations.
The original `run_benchmark.py` overwrites its output directory. The learning
drivers reject accidental overwrite of fitted models and measured records.
See `docs/Original_NUM_Reproduction.md` and `dis_extension/README.md` for full
stage order. Learning stages use the unchanged original instance arrays.

The original benchmark uses one configured BLAS thread. The follow-up tests
one and four on the same CPU and asserts NumPy and SciPy thread-pool limits.
Offline training, online feature computation and fallback have different
accounting roles; the paper specifies what each runtime comparison charges.

## Documents

The supplied paper can be read without the document toolchain. Historical
manuscript builders require Pandoc, python-docx and a Word-compatible PDF
renderer. They do not collect numerical measurements. The current combined
paper and editable DOCX are under `paper/`; it has no appendices.
