# CASP16 Server Attack Policy

This document defines the realistic attack-budget layer. It is separate from
the `dev_fixed` leaderboard so single-seed strategy ablations and multi-candidate
server-style runs are not compared as if they used the same compute.

## Current Budget

The first locked attack budget is
`attack_budgets/casp16_server_attack_protenix5.json`.

- parent benchmark: `casp16_server_protein_v1`
- backend: `protenix`
- model: `protenix-v2`
- seeds: `101,102,103,104,105`
- sample per seed: `1`
- total candidates per target: `5`
- selected model policy: `protenix_confidence_v1`
- MSA/templates/default params/cache/fusion/TF32: enabled

The first run spec using this budget is
`server_attack_protenix_terminal_tag_seed101_105`. It has been submitted as
Slurm job `810719` and remains an attack row, not a `dev_fixed` row. Live
output shows Protenix running the declared seeds as a serial outer loop: all
targets for `seed_101` are produced before `seed_102` begins.
As of the latest check, the run has produced 67 CIF files, all under
`seed_101`; it is therefore still incomplete and must not be scored as a full
five-candidate attack row.

The second queued run spec using the same budget is
`server_attack_protenix_coverage_stoich_seed101_105`. It uses the stacked
sequence-recovery, large-target fallback, and token-safe stoichiometry input.
It is queued but not submitted; launch it only when it is selected by
`run-next --dry-run` or after an explicit queue supersession decision.

Future winner-comparison attack runs should target
`casp16_server_protein_v2_aliasfix` or a newer explicit server benchmark. The
existing `protenix5` v1 runs remain valid only for the fixed v1 protocol they
were generated against.

## Budget Reality

Treat `protenix5` as the first local attack tier, not as a claim about the
actual CASP16 winner compute. Strong CASP16 server systems likely generated
multiple internal candidates per target through some mix of stochastic seeds,
sampling, engines, MSA/template variants, and model ranking. In this repo,
`seed`, `sample`, engine choice, and selection policy are all part of the
candidate budget and must be declared before scoring.
Run specs and manifests expose this as `budget_tier` plus `candidate_count`,
where `candidate_count = seed_count * sample`. Extra hidden candidates, or
target-specific manual candidate selection, invalidate the row.

Five candidates per target is intentionally a starter attack budget. It is more
realistic than single-seed `dev_fixed`, but it should not be described as
matching a top CASP16 server's hidden compute. Larger winner-chasing attempts
need their own locked budget tier before any predictions are scored.

If a strategy needs more realistic compute, create a new attack-budget JSON
such as `protenix25` or an ensemble budget. Do not mutate
`casp16_server_attack_protenix5.json`, and do not compare the higher-budget
rows against `dev_fixed` or `protenix5` rows as if the compute were identical.

## Planned Larger Budget

`attack_budgets/casp16_server_attack_protenix25.json` is a planned
winner-chasing tier, not a queued run. It targets
`casp16_server_protein_v2_aliasfix`, declares seeds `101..125`, and keeps
`sample_per_seed=1` for 25 candidates per target. The selector is still
`protenix_confidence_v1`, so it remains reference-free and score-free.
Shard run ids, seed ranges, and input artifacts are locked in
`attack_budgets/casp16_server_attack_protenix25_shards.tsv`.

`attack_budgets/casp16_server_attack_protenix25_nofail.json` is a separate
planned tier for the no-over-token v2 stack. It uses the same 25 seeds and
selector, but points every shard at
`yang_coverage_stoich_low_complexity_large_fallback_v1`, whose generated input
has 163 jobs and 0 jobs above Protenix's 2560-token limit. Its shard manifest
is `attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`.

Because Protenix loops serially over seeds, this budget must be executed as
five predeclared five-seed shards and merged only after all shards finish. A
partial 25-seed attempt is unranked unless it is explicitly reported as
partial. Launch this tier only after the current `protenix5` attack and the
v2 alias-fixed `dev_fixed` baseline have produced evidence that the extra
candidate spend is worth the GPU-hours. For the nofail tier, also score the
v2 no-over-token fallback ablation first, or explicitly record why the attack
supersedes it.

When the launch gate opens, generate each shard with the TSV row's fields:

```bash
./casp16 run-spec \
  --run-id <run_id> \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest strategies/yang_oligo_stoichiometry_token_safe_v1/casp16_server_protein_v2_aliasfix/manifest.tsv \
  --strategy yang_coverage_stoich_token_safe_v1_server_attack_protenix25 \
  --seeds <shard_seeds> \
  --sample 1 \
  --selected-model-policy protenix_confidence_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

For the nofail tier, use the shard TSV rows from
`attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`; do not
reuse the older `protenix25` input artifact by accident.

## Execution Semantics

Protenix accepts comma-separated seeds, but the runner iterates as:

```text
for seed in seeds:
    for target in benchmark_inputs:
        predict(target, seed)
```

This means an in-flight multi-seed run can look like a single-seed run for a
long time. Do not score a `server_attack` row as a complete five-candidate run
until every declared seed has produced candidates, or the row is explicitly
reported as partial/unranked. If a run approaches the Vista 48-hour wall-time
limit, prefer a predeclared seed-sharded continuation over restarting the same
monolithic command and silently overwriting existing candidates.
The scorer enforces this fail-closed: a target with fewer observed candidate
files than the declared `candidate_count` is marked `partial_candidates` and
scores `0`.

## Selection Rule

`protenix_confidence_v1` is a pre-scoring confidence-only model selector:

```text
0.20 * plddt_norm + 0.50 * ptm + 0.30 * iptm
- 0.10 * disorder - 0.20 * has_clash
```

`plddt_norm` is `plddt / 100` when pLDDT is reported on a 0..100 scale. The
selector may read only the confidence JSON files generated by the same
prediction run. It may not read native/reference structures, official score
tables, previous target scores, or any per-target manual feedback.

The scoring code now fails closed for this policy: if no confidence JSON can be
found for a candidate target, the target row becomes `selection_failed` and
scores `0` instead of silently falling back to the first model.

## Launch Gate

Do not launch additional `server_attack` runs just because a winner likely used multiple
candidates. Launch only when the run answers a real leaderboard question:

- A `dev_fixed` strategy has a positive full-benchmark signal, or the attack is
  a baseline attack run used to quantify the multi-seed gap.
- QSglob scoring and assembly mapping are validated for protein oligos, or the
  run is explicitly marked domain-only/unranked for oligos.
- Any split/fallback for `n_token > 2560` targets is predeclared before
  prediction starts.
- The strategy note records expected GPU-hours and actual wall time.

## Example Run Spec

```bash
./casp16 run-spec \
  --run-id server_attack_protenix_terminal_tag_seed101_105 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --seeds 101,102,103,104,105 \
  --sample 1 \
  --selected-model-policy protenix_confidence_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

This creates an attack-budget run spec. It does not make the result comparable
to `dev_fixed` rows. Compare attack rows only against other attack rows and
against official server groups with the budget clearly displayed.
