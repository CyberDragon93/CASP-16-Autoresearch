# Antibody Fv Target-Lab Summary

Run: `targetlab_protenix_yang_antibody_fv_seed101`

Status: complete target_lab diagnostic, not rank eligible.

Scope: eight Fv-only antibody-antigen jobs from
`yang_antibody_fv_fragment_inputs_v1`, run with full Protenix MSA/template
settings, seed `101`, sample `1`.

Result:

- Structures: 8/8 CIFs
- Confidence files: 8/8
- pLDDT range: 85.872139 to 94.151428
- pTM range: 0.865255 to 0.954284
- ipTM range: 0.776553 to 0.942385
- DockQ diagnostic: 8/8 ok
- DockQ total range: 0.258000 to 0.916000
- DockQ total mean: 0.497250
- Strong DockQ positives: `H0233__fv=0.916000`, `H1233__fv=0.891000`
- Moderate DockQ cases: `H1225__fv=0.538000`, `H0222__fv=0.431000`,
  `H1222__fv=0.383000`

Interpretation:

The Fv-only branch produces high-confidence antibody-antigen assemblies and
strong diagnostic DockQ positives on `H0233__fv` and `H1233__fv`. This is useful
O5 evidence, but it is not leaderboard evidence until QSglob/assembly mapping
can evaluate the corresponding server oligo targets without per-target oracle
use.
