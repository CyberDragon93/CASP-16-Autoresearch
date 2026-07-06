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
- The scorer now preserves these OpenStructure mapping diagnostics in the
  `target_scores.csv` `message` column, for example
  `ost_unmapped_model_chains:A,B;ost_empty_chain_mapping;ost_empty_chem_mapping`.
  This keeps the official-compatible score unchanged while making false-zero
  classes visible for triage.
- Follow-up input audit found an additional `H0220/H1220/H2220` class: some
  local v2 protein-oligo inputs were short nucleic-acid records even though the
  official sequence archive has protein-like records through target aliases.
  Those targets need sequence/input recovery before scorer mapping alone can
  give a meaningful QSglob comparison.

## Mapping Parameter Probe

OpenStructure exposes `--chem-map-seqid-thresh`; setting it to `0` should make
chemical mapping maximally permissive. A bounded 2026-07-06 probe compared the
default setting against `--chem-map-seqid-thresh 0` on existing baseline
predictions for representative oligo targets.

| target | default QSglob | forced QSglob | default chain map count | forced chain map count | conclusion |
| --- | ---: | ---: | ---: | ---: | --- |
| `H0220` | 0.000 | 0.000 | 0 | 0 | not fixed by permissive chem mapping; prioritize input sequence/modality recovery |
| `T0234O` | 0.000 | 0.000 | 1 | 1 | mapping parameter does not rescue the zero |
| `T1249V1O` | 0.090 | 0.090 | 3 | 3 | nonzero score is stable under the parameter |
| `H1232` | 0.000 | 0.000 | 2 | 2 | mapping exists, so the zero is not the H0220-style unmapped-chain failure |

Do not change the scorer default to `--chem-map-seqid-thresh 0` based on these
targets. The higher-leverage fix remains better protein-oligo inputs and
target-agnostic assembly handling, especially the v2 oligo-recovery nofail
stack.

## Oligo Signal Probe

Do not run a full `./casp16 score` while a large run is still producing partial
predictions; it will mix incomplete attack rows into the temporary score table.
Use targeted probes instead:

```bash
./casp16 qsglob-probe \
  --benchmark casp16_server_protein_v1 \
  --run-id server_protenix_full_msa_template_seed101 \
  --target H0220,H0222,H1232,T1249V1O \
  --output-csv diagnostics/qsglob_probes/server_v1_baseline_probe.csv
```

`qsglob-probe` writes a diagnostic CSV only. It does not update
`leaderboards/*`, does not change benchmark rules, and keeps the same
fail-closed scoring behavior as the full scorer. It is for isolating
OpenStructure chain/chem mapping classes while long prediction jobs are still
running.

The first QSglob signal probe sampled six oligo targets from the four completed
`casp16_server_protein_v1` Protenix dev runs.

| run | H0220 | H0222 | H1232 | T0206O | T0234O | T1249V1O |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.000 | 0.075 | 0.000 | 0.000 | 0.000 | 0.090 |
| terminal tag cleanup | 0.000 | 0.076 | 0.013 | 0.000 | 0.000 | 0.122 |
| oversize fallback | 0.000 | 0.080 | 0.032 | 0.000 | 0.000 | 0.099 |
| antibody Fv cleanup | 0.000 | 0.037 | 0.000 | 0.000 | 0.000 | 0.125 |

Interpretation:

- QSglob is producing nonzero values and can distinguish strategies; it is not
  merely returning universal zeros.
- `H0220` still has no model-chain mapping (`A/B` unmapped), and permissive
  chemical mapping did not fix it; this reinforces the v2 input-recovery path.
- `T0234O` and `T1249V1O` have empty chem-group mappings for some groups, so
  full oligo ranking still needs assembly mapping diagnostics.
- The signal supports continuing token-safe stoichiometry/coverage runs before
  spending a larger attack budget; more seeds will not fix wrong assembly
  mapping.

The checked diagnostic CSV at
`diagnostics/qsglob_probes/server_v1_baseline_probe.csv` confirms the probe
workflow on four representative baseline targets: `H0222=0.075`,
`T1249V1O=0.090`, `H0220=0` with
`ost_unmapped_model_chains:A,B;ost_empty_chain_mapping;ost_empty_chem_mapping;ost_no_mapped_interfaces`,
and `H1232=0` without the H0220-style unmapped-chain diagnostic.

A second checked diagnostic CSV at
`diagnostics/qsglob_probes/server_v2_partial_alias_probe.csv` confirms the
alias-fixed scorer path on the active v2 nofail run. Official oligo rows such
as `T0206O`, `T0234O`, and `T1249V1O` use `sequence_lookup_id` prediction
artifacts named `T0206`, `T0234`, and `T1249V1`; the scorer now resolves those
aliases instead of marking them as missing predictions. This is required before
any v2 server oligo leaderboard can be trusted.

## Next Work

- Score server oligo targets with `ost` once the active run is complete, so
  partial attack rows are not written into checked-in leaderboard artifacts.
- Use the `message` column diagnostics to isolate target classes where
  automatic OpenStructure mapping gives false zeros, then add explicit
  assembly/chain mapping only for target-agnostic classes.
- Keep DockQ as an interface diagnostic only; do not use it as a ranked QSglob
  replacement.
