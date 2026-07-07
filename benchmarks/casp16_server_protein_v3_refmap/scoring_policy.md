# CASP16 Server Protein V3 Refmap Scoring Policy

This benchmark is intended for CASP16 protein server-track comparison.

- Ranked tracks are `protein_domain` and `protein_oligo`.
- The fixed target sets are derived from the official CASP16 protein score tables.
- Protein domains use official-compatible `GDT_TS`, normalized to `0..1`.
- Protein oligos use official-compatible `QSglob`.
- Server baselines include only group ids ending in `s`.
- Missing predictions, failed metrics, unavailable metric tools, missing references, and unresolved mappings score `0`.
- Confidence files are diagnostics only and never contribute to ranking.
- DockQ is an interface diagnostic for oligos; it is not a replacement for `QSglob`.
- Any change to target-set membership, budget, or ranked metric requires a new benchmark version.
