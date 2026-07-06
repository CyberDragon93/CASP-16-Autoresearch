# QSglob Scorer

This repository uses OpenStructure `ost compare-structures --qs-score` as the
default local QSglob-compatible scorer for CASP16 server protein-oligo tracks.

## Installed Tool

- Env: `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob`
- Binary: `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost`
- Version: `OpenStructure 2.11.1`
- Source package: `bioconda::openstructure=2.11.1`
- OpenStructure install docs: https://openstructure.org/install
- OpenStructure action docs: https://openstructure.org/docs/2.11/actions/
- Bioconda package page: https://anaconda.org/bioconda/openstructure

The default scorer path is configured in `src/casp16_leaderboard/runs.py` as
`DEFAULT_QSGLOB_BIN`.

## Validation Probe

Command:

```bash
/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost compare-structures \
  -m runs/server_protenix_full_msa_template_seed101/predictions/protenix-v2/H0220/seed_101/predictions/H0220_sample_0.cif \
  -r data/official/references/mmcif/9h1g.cif \
  --qs-score \
  -o /tmp/h0220_qs.json
```

Result:

- `ost` completed successfully.
- Project scoring returned `status=ok`, `metric=QSglob`, `score=0.000000`.
- The JSON reported no chain mapping for model chains `A/B` against the
  reference chem groups, so the zero is an assembly/chain-mapping signal, not a
  missing-tool failure.

## Oligo Signal Probe

Do not run a full `./casp16 score` while a large run is still producing partial
predictions; it will mix incomplete attack rows into the temporary score table.
Instead, the first QSglob signal probe sampled six oligo targets from the four
completed `casp16_server_protein_v1` Protenix dev runs.

| run | H0220 | H0222 | H1232 | T0206O | T0234O | T1249V1O |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.000 | 0.075 | 0.000 | 0.000 | 0.000 | 0.090 |
| terminal tag cleanup | 0.000 | 0.076 | 0.013 | 0.000 | 0.000 | 0.122 |
| oversize fallback | 0.000 | 0.080 | 0.032 | 0.000 | 0.000 | 0.099 |
| antibody Fv cleanup | 0.000 | 0.037 | 0.000 | 0.000 | 0.000 | 0.125 |

Interpretation:

- QSglob is producing nonzero values and can distinguish strategies; it is not
  merely returning universal zeros.
- `H0220` still has no model-chain mapping (`A/B` unmapped), so that target is
  a likely false-zero mapping case.
- `T0234O` and `T1249V1O` have empty chem-group mappings for some groups, so
  full oligo ranking still needs assembly mapping diagnostics.
- The signal supports continuing token-safe stoichiometry/coverage runs before
  spending a larger attack budget; more seeds will not fix wrong assembly
  mapping.

## Next Work

- Score server oligo targets with `ost` once the active run is complete, so
  partial attack rows are not written into checked-in leaderboard artifacts.
- Add explicit assembly/chain mapping for target classes where automatic
  OpenStructure mapping gives false zeros.
- Keep DockQ as an interface diagnostic only; do not use it as a ranked QSglob
  replacement.
