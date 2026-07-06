# CASP16 Protein V1 Scoring Policy

This benchmark is protein-first and rank-stable.

- Ranked tracks are `protein_domain` and `protein_oligo`.
- The fixed budget is backend `protenix`, seed `101`, sample `1`, and selected model policy `first_output_only`.
- Missing predictions, failed predictions, unavailable metric tools, and unparseable metric output score `0`.
- Confidence files are collected as diagnostics only and never used as quality score.
- Protein domain targets use a normalized GDT-TS/TM-like score when a single-domain reference mapping is available.
- Protein oligo targets use DockQ-derived scores with `--allowed_mismatches 5` when reference complexes are available.
- Targets without a sequence, reference, or explicit mapping stay visible as coverage rows but are not rank-eligible.
