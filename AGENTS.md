# Agent Operating Rules

This file is the entry point for any agent or human making leaderboard-facing
changes in this repository. Read it before creating a run, changing a strategy,
or interpreting leaderboard outputs.

## Goal

The goal is to improve local CASP16 prediction strategies while preserving a
stable, fair, reproducible leaderboard. Treat the benchmark as a protocol, not
as a mutable result table.

Use `docs/AUTORESEARCH.md` as the working index for current experiments and
`docs/CASP16_SERVER_BENCHMARK.md` for the planned official-server comparison
benchmark. Do not treat either document as permission to change locked
benchmark files in place.
Use `docs/TARGET_LAB_PROMOTION.md` before turning target-lab diagnostics into
full-benchmark strategy runs.

## Required Workflow

Use the CLI path for every ranked run:

```bash
./casp16 run-spec --run-id <run_id> --benchmark casp16_protein_v1
./casp16 run-next --benchmark casp16_protein_v1
./casp16 score --benchmark casp16_protein_v1
./casp16 leaderboard --benchmark casp16_protein_v1
```

Use this read-only check before launching work:

```bash
./casp16 list-runs --benchmark casp16_protein_v1
./casp16 run-next --benchmark casp16_protein_v1 --dry-run
```

## Allowed Changes

- Add new run specs, logs, manifests, predictions, and notes under
  `runs/<run_id>/`.
- Add strategy code or scripts that create new run specs without changing the
  locked benchmark.
- Add documentation that explains a strategy, failure mode, or result.
- Regenerate leaderboard artifacts only through the documented `./casp16`
  commands.

## Protected Files

Do not hand-edit these paths for a normal strategy iteration:

- `benchmarks/casp16_protein_v1/*`
- `leaderboards/*`
- `data/official/parsed/official_scores.tsv`
- cached reference structures under `data/official/references/`

Changes to benchmark eligibility, reference mapping, metric parsing, fixed
budget, or scoring policy require a new benchmark version. Do not silently
rewrite `casp16_protein_v1`.

## Data Access Rules

Allowed during strategy design and prediction:

- benchmark inputs and target metadata
- run specs and run manifests
- stdout/stderr logs
- coverage summaries and failure summaries
- public method documentation and model documentation

Forbidden during strategy design and prediction:

- native/reference structures for per-target tuning
- official score tables for choosing target-specific behavior
- previous `target_scores.csv` rows for per-target parameter selection
- leaderboard outputs as an oracle for changing individual targets

Scoring may read references and official-derived metadata only inside the
benchmark scoring pipeline.

## Ranking Rules

- Ranked benchmark: `casp16_protein_v1`.
- Ranked tracks: `protein_domain` and `protein_oligo`.
- Fixed budget: backend `protenix`, seed `101`, sample `1`, selected model
  policy `first_output_only`.
- Missing predictions, failed metrics, missing references, and unavailable
  metric tools score `0`.
- Confidence files are diagnostics only. Do not use confidence as a quality
  score or as a replacement for structure metrics.

## Server Attack Budgets

Do not treat a one-seed/one-sample development run as winner-comparable. CASP16
server winners almost certainly used more than one internal candidate, but do
not assume that hidden compute maps to literal Protenix seeds. Count the whole
candidate budget: stochastic seeds, samples, backend/model variants,
MSA/template variants, refinement/ranking passes, and submitted models. Any
server-track attack run must declare that budget before prediction starts:
seed list, sample count, backend/model variants, MSA/template policy, selection
rule, and allowed selection signals.

Run specs, run manifests, collected runs, and leaderboard summaries must expose
`budget_tier` and `candidate_count`. A multi-seed, multi-sample,
multi-variant, or confidence-selected row is `server_attack`, even if the
selected-model policy is `first_output_only`. Single-seed `dev_fixed` rows are
for ablation and pipeline debugging only.
For `server_attack`, a target with fewer observed candidate files than the
declared `candidate_count` is `partial_candidates` and scores `0` until the
declared budget is complete.

The current `server_attack` tier is only a first realism check, not an estimate
of the true winner budget. Larger multi-seed, multi-sample, multi-engine, or
stronger-ranker attempts require a new predeclared attack-budget version and
must be reported separately from `dev_fixed` rows.

## Strategy Notes

Create a short strategy record using `docs/STRATEGY_TEMPLATE.md` when adding a
new run. The record should make it clear what changed, what stayed fixed, which
commands were used, and whether the result is rank-eligible.
