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
`server_attack_protenix_terminal_tag_seed101_105`. It was submitted as Slurm
job `810719` and later cancelled after a weak partial diagnostic so GPU time
could move to the v2 target-sharded scoreable attack. The partial row remains
an incomplete attack-budget diagnostic, not a `dev_fixed` row. Protenix ran the
declared seeds as a serial outer loop: all targets for `seed_101` were produced
before `seed_102` began. The last recorded CIF counts were `98/98/98/81/0` for
seeds `101..105`; it must not be scored as a full five-candidate attack row.

The second queued run spec using the same budget is
`server_attack_protenix_coverage_stoich_msa_reuse_seed101_105`. It uses the
stacked sequence-recovery, large-target fallback, and token-safe stoichiometry
input, but injects exact-sequence MSA cache paths before launch. The non-reuse
predecessor `server_attack_protenix_coverage_stoich_seed101_105` is
append-only superseded. The MSA-reuse row currently covers 180/196 protein
chains, misses 16 changed/new chains, has 0 stale covered paths, and uses a
minimum reuse guard of 0.90.

Future winner-comparison attack runs should target
`casp16_server_protein_v2_aliasfix` or a newer explicit server benchmark. The
existing `protenix5` v1 runs remain valid only for the fixed v1 protocol they
were generated against.

## Budget Reality

Treat `protenix5` as the first local attack tier, not as a claim about the
actual CASP16 winner compute. Strong CASP16 server systems likely generated
multiple internal candidates per target through some mix of stochastic seeds,
sampling, engines, MSA/template variants, refinement, submitted models, and
model ranking. Do not translate that hidden compute into an assumed literal
Protenix seed count. In this repo, `seed`, `sample`, engine choice, input/MSA
variant, refinement/ranking pass, and selection policy are all part of the
candidate budget and must be declared before scoring.
Run specs and manifests expose this as `budget_tier` plus `candidate_count`.
By default, `candidate_count = seed_count * sample`; if a run uses additional
model/backend variants, input/MSA variants, refinement/ranking passes, or
submitted-model selection, it must predeclare a larger total with
`./casp16 run-spec --candidate-count <n>`. Declared `candidate_count` may be
larger than `seed_count * sample`, but never smaller. Extra hidden candidates,
or target-specific manual candidate selection, invalidate the row.

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
`inputs_msa_reuse_from_dev_seed101.json`, with 165 jobs, protein-oligo sequence
recovery, token-safe stoichiometry, exact-sequence MSA paths reused for 268/268
protein chains, and 0 jobs above 2560 tokens. Its shard manifest is
`attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`. Do not
spend winner-scale compute on the older nofail artifact unless the run is
explicitly labeled as an ablation.

`attack_budgets/casp16_server_attack_protenix25_scoreable_nofail.json` is the
current scoreable-target winner-scale plan. It keeps the same 25-seed
candidate budget and selector, but predicts only the 74 jobs that currently
have at least one locally available reference alias. It points at the
size-first phase-alias scoreable artifact, so `H0220/H1220/H2220` use recovered
protein `A1B4` and the exact-oligo block is ordered from small to large before
the 2515-2535 token jobs. The fixed benchmark scoring set remains 175 targets;
skipped no-reference targets stay local zeros. Each shard must inject
`data/msa_cache/index.tsv` with `--msa-reuse-require-complete`. Launch it only
after the running scoreable `protenix5` attack is scored or explicitly
superseded.

Because Protenix loops serially over seeds and large assemblies can block a
whole serial run, this budget is prepared as a target-shard x seed-block grid:
six target-balanced shards times five 5-seed blocks. The first seed block
(`101..105`) is the already submitted P14 `protenix5` target-sharded attack,
so the 25-candidate plan reuses those six run specs instead of spending that
compute twice. The remaining 24 run specs for seeds `106..125` are prepared as
`deferred:await_protenix5_score` and must not be submitted before P14 is
merged/scored or explicitly superseded. A partial 25-seed attempt is unranked
unless it is explicitly reported as partial.

For very large scoreable inputs, target-size sharding is allowed as an
execution-only optimization when every shard uses the same declared budget and
strategy. A target-sharded merge must be explicit:

```bash
./casp16 merge-shards \
  --allow-target-shards \
  --merged-input-json <full_strategy_input_json> \
  --run-id <merged_run_id> \
  --benchmark casp16_server_protein_v2_aliasfix \
  --candidate-count <declared_candidates> \
  --shard-run-id <target_shard_1> \
  --shard-run-id <target_shard_2>
```

The merged input JSON must be the full predeclared strategy input, not a shard
subset. This keeps exact-target accounting and candidate selection tied to the
complete strategy while allowing small/medium/large target batches to run
without one 2500-token assembly blocking every other target.

The active five-candidate scoreable attack now uses this execution model. The
source input is
`strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`;
`./casp16 shard-inputs` created six balanced target shards under
`strategies/target_shards_scoreable_size_balanced_v1/casp16_server_protein_v2_aliasfix/`.
Shard runs are named
`server_v2_attack_scoreable_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105`,
declare `candidate_count=5`, use `protenix_confidence_v1`, and are explicitly
`rank_eligible=false` until merged. They were submitted as Slurm jobs
`812239..812244` with `./casp16 run-one --allow-parallel`.

Current launch gate as of `2026-07-07 00:40 CDT`: those six P14 shards are
still running and not merge-ready. `check-shards` observes 115/370 expected
candidate CIFs and reports `ready=false`. Do not submit the deferred v4 P15
shards, the 25-seed scoreable grid, or the antibody-Fv scoreable branch until
P14 is either merged/scored or explicitly abandoned with an append-only status
reason. The next decision should be based on fixed-set server scores, not on a
partial shard snapshot.

The prepared v4 successor uses
`casp16_server_protein_v4_refmap` and 76 scoreable jobs because audited
reference-map rows add `T1278` and `T2278`. It is a different benchmark version
from v2. If launched, report it as v4 reference-coverage recovery plus the same
five-candidate attack budget; do not mix its results into v2 leaderboards.

Use `run-one --allow-parallel` only for target-disjoint shards that will be
merged later. Normal strategy rows should still use `run-next`, which preserves
the benchmark-wide running lock.

Before merging target shards, run the readiness check:

```bash
./casp16 check-shards \
  --benchmark casp16_server_protein_v2_aliasfix \
  --merged-run-id <merged_run_id> \
  --merged-input-json <full_strategy_input_json> \
  --candidate-count <declared_candidates> \
  --shard-run-id <target_shard_1> \
  --shard-run-id <target_shard_2>
```

The check is read-only. It verifies shard compatibility, counts per-task
prediction candidates, writes a per-shard TSV when requested, and emits the
exact `merge-shards --allow-target-shards` command only when every target has
the declared candidate count.

For a larger run that combines target-size shards with seed-block shards, keep
`--candidate-count` equal to the expected candidates in each execution shard
and pass the final per-target budget with `--merged-candidate-count`. For
example, a 25-candidate attack split into five 5-seed blocks should check each
execution shard with `--candidate-count 5 --merged-candidate-count 25`; the
readiness summary then verifies the full merged input has 25 observed
candidates for every target before emitting a `merge-shards --candidate-count
25` command.

When the launch gate opens, generate each shard with the TSV row's fields:

```bash
./casp16 run-spec \
  --run-id <run_id> \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json <input_json_from_shard_tsv> \
  --input-manifest <input_manifest_from_shard_tsv> \
  --strategy <strategy_from_shard_tsv> \
  --seeds <shard_seeds> \
  --sample 1 \
  --selected-model-policy protenix_confidence_v1 \
  --candidate-count <execution_candidate_count_from_shard_tsv> \
  --no-rank-eligible \
  --use-msa --use-template --no-use-default-params \
  --enable-cache --enable-fusion --enable-tf32 \
  --reuse-global-msa-cache \
  --msa-reuse-require-complete
```

For the nofail tier, use the shard TSV rows from
`attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`; do not
reuse the older `protenix25` input artifact by accident.
For the scoreable nofail tier, use
`attack_budgets/casp16_server_attack_protenix25_scoreable_target_seed_shards.tsv`.
It has 30 execution rows: six existing P14 reuse rows for seeds `101..105` and
24 deferred rows for seeds `106..125`.

Before submitting or undefering any execution shard manifest, batch-preflight
the run specs:

```bash
./casp16 preflight-runs \
  --benchmark casp16_server_protein_v2_aliasfix \
  --run-id-tsv attack_budgets/casp16_server_attack_protenix25_scoreable_target_seed_shards.tsv \
  --output-tsv diagnostics/msa_cache/protenix25_scoreable_target_seed_run_preflight.tsv
```

This check is launch hygiene only: it reads run specs and MSA reuse reports, not
references or scores. The current scoreable target+seed grid is `30/30 ok`,
with complete MSA coverage and 0 stale covered paths. The seed106-125 rows stay
`deferred:await_protenix5_score` until P14 is scored or explicitly superseded.

After every shard has completed, register the merged attack row before scoring.
For the scoreable target+seed grid, do not hand-write the final merge command;
first run the readiness check with the full input and final candidate budget:

```bash
./casp16 check-shards \
  --benchmark casp16_server_protein_v2_aliasfix \
  --merged-run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix25_seed101_125 \
  --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --candidate-count 5 \
  --merged-candidate-count 25 \
  --output-tsv diagnostics/score_probes/protenix25_scoreable_target_seed_readiness.tsv \
  --shard-run-id <each row from attack_budgets/casp16_server_attack_protenix25_scoreable_target_seed_shards.tsv>
```

When the readiness result is `ready=true`, use its emitted
`merge-shards --allow-target-shards --candidate-count 25` command. The merge
symlinks completed shard predictions into one registered run directory. It
does not launch predictions, select models, or make a partial shard
rank-eligible as the complete 25-candidate budget.

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
