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

## Next Work

- Score server oligo targets with `ost` once full prediction runs are ready.
- Add explicit assembly/chain mapping for target classes where automatic
  OpenStructure mapping gives false zeros.
- Keep DockQ as an interface diagnostic only; do not use it as a ranked QSglob
  replacement.
