# CASP16 Server Score Targets

This file pins the score target for the autoresearch loop. It should be read
with `docs/AUTORESEARCH.md` and `docs/SERVER_ATTACK_POLICY.md`.

## Official Server Targets To Beat

Source: `leaderboards/casp16_server_protein_v2_aliasfix/official_groups.csv`,
server-only groups, fixed eligible target sets.

| Track | Metric | Eligible targets | Server leader | Fixed mean to beat | Coverage |
| --- | --- | ---: | --- | ---: | --- |
| protein domains | GDT_TS | 71 | `110s` | `0.923321` | 71/71 |
| protein oligos | QSglob | 104 | `456s` | `0.582615` | 102/104 |

Top nearby server baselines:

| Track | Rank | Group | Fixed mean |
| --- | ---: | --- | ---: |
| protein domains | 2 | `019s` | `0.908993` |
| protein domains | 3 | `147s` | `0.907055` |
| protein oligos | 2 | `052s` | `0.581712` |
| protein oligos | 3 | `110s` | `0.543327` |

## Current Local Floor

Source: `leaderboards/casp16_server_protein_v1/runs.csv`.

| Track | Best current local full Protenix row | Budget tier | Fixed mean | OK targets | Missing predictions | Gap to leader |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| protein domains | `server_protenix_yang_terminal_tag_cleanup_seed101` | `dev_fixed` | `0.066908` | 15 | 30 | `+0.856413` |
| protein oligos | `server_protenix_yang_terminal_tag_cleanup_seed101` | `dev_fixed` | `0.045865` | 27 | 47 | `+0.536750` |

Interpretation: the local baseline is still failure-level relative to official
server leaders. The immediate useful signals are coverage recovery, correct
metric mapping, and full-set mean increases. A few impressive target-lab or
partial-run examples do not count as server progress.

## Current V2 Diagnostic Floor

Source: `leaderboards/casp16_server_protein_v2_aliasfix/target_scores.csv`,
generated from the current alias-fixed diagnostics.

The best v2 diagnostic row,
`server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`,
is still dominated by coverage and mapping failures:

| Track | Mean | OK | Missing prediction | Missing reference | Nonzero targets |
| --- | ---: | ---: | ---: | ---: | ---: |
| protein domains | `0.049685` | 13/71 | 32/71 | 26/71 | 9 |
| protein oligos | `0.000923` | 8/104 | 82/104 | 14/104 | 1 |

The only nonzero v2 oligo diagnostic is `T1249V1O` with QSglob `0.096`.
After adding scorer alias diagnostics, all eight current oligo `ok` rows are
`sequence_lookup` matches rather than exact `*O` prediction matches. These rows
are useful for detecting alias/assembly false-zero classes, but they are not a
strong exact-oligo quality signal yet.
The nonranked seed-101 scoreable-attack probe improves the partial domain
picture: 24 exact domain predictions score 17 nonzero targets, with fixed-set
domain mean `0.099576`. After the scorer exact-artifact gate, its oligo rows are
104/104 `missing_prediction`: the previous `sequence_lookup` fallback positives
are not counted when the run input declares exact `TxxxxO`/`Hxxxx` jobs. The
next oligo gate is exact `*O` prediction/assembly scoring, not blindly
increasing the seed count.
Before spending another winner-scale budget, the high-leverage work is still
reference recovery, prediction coverage, and QSglob assembly mapping. More
seeds cannot rescue targets that are missing predictions, missing references,
or mapped to QSglob false zeros.
The concrete reference-recovery worklist is
`diagnostics/reference_gap/casp16_server_protein_v2_aliasfix_missing_references.tsv`;
its first block is 40 existing v2 diagnostic predictions that are currently
scored as `missing_reference`.

## Active Score Gates

1. Finish and score the live P14 target-sharded five-candidate attack:
   `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105`.
   The six execution shards are rank-ineligible until every one has all five
   declared candidates for its target subset and has been merged with
   `./casp16 merge-shards --allow-target-shards`. Do not use a partial shard
   score to launch the planned 25-candidate budget.
   Required readout sequence:

   ```bash
   ./casp16 check-shards \
     --benchmark casp16_server_protein_v2_aliasfix \
     --merged-run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
     --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
     --candidate-count 5 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105

   ./casp16 merge-shards \
     --benchmark casp16_server_protein_v2_aliasfix \
     --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
     --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
     --allow-target-shards \
     --candidate-count 5 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
     --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105

   ./casp16 score --benchmark casp16_server_protein_v2_aliasfix \
     --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105
   ./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix
   ```
2. Compare only `dev_fixed` to `dev_fixed`. A single-seed row can prove that an
   input strategy is worth more compute, but it is not winner-comparable.
3. Score `server_attack` rows only after every declared candidate is present.
   Partial target candidates score `0`; seed shards must be merged with
   `./casp16 merge-shards` before a 25-candidate row can be scored.
4. For official server comparison, domains use `GDT_TS`; oligos use `QSglob`.
   DockQ and confidence are diagnostics only.

The preferred shard closeout command is `finish-shards`. It is intentionally
safe to run while shards are still live: if readiness is false, it only writes
the readiness report and returns `finish_status=not_ready`. Once readiness is
true, it performs the merge, full benchmark scoring refresh, and leaderboard
refresh in one audited step.

```bash
./casp16 finish-shards \
  --benchmark casp16_server_protein_v2_aliasfix \
  --run-id server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105 \
  --merged-input-json strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --allow-target-shards \
  --candidate-count 5 \
  --output-tsv diagnostics/score_probes/target_shards_scoreable_size_balanced_readiness.tsv \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard01_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard02_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard03_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard04_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard05_msa_reuse_protenix5_seed101_105 \
  --shard-run-id server_v2_attack_scoreable_size_balanced_shard06_msa_reuse_protenix5_seed101_105
```

## Post-P14 Decision Matrix

After P14 is merged and scored, inspect `runs.csv`, `target_scores.csv`, and
`coverage.md` for the merged run. The next branch should be selected by the
failure mode, not by impatience to spend more GPU time.

| P14 observation | Interpretation | Next branch |
| --- | --- | --- |
| Broad fixed-set improvement, more nonzero domain targets, and several exact protein-oligo QSglob positives | Five candidates plus the scoreable input stack have real signal; candidate budget and selector are plausible bottlenecks | Launch the deferred 25-candidate scoreable target+seed grid |
| Good v2 signal, but the useful scoreable set is still capped by reference availability | Reference recovery can unlock a little more local measurement without changing the prediction recipe | Launch P15 on `casp16_server_protein_v4_refmap`, and keep broader refmap work versioned |
| Many scoreable rows are still `missing_prediction`, `metric_failed`, or exact oligo rows are not found | This is a pipeline/input/scorer failure, not a sampling failure | Fix the failure class before launching P25 |
| Domain score is weak because input-kind or sequence-alias repairs are missing | More seeds will repeat bad inputs | Run D6a single-seed domain sequence recovery after MSA warmup |
| Exact QSglob remains weak mainly on antibody/Fv rows after phase-alias stoichiometry is fixed | Oligo branch may need Fv/docking-inspired input handling | Launch the prepared O5 antibody-Fv target shards |
| Predictions and metrics are valid but the five-candidate attack is broadly weak | Current Protenix recipe is not enough; scaling seeds alone is low leverage | Design a new MSA/model-variant budget before spending winner-scale compute |

## What Counts As Progress

- More scoreable domain targets without lowering the full-set mean.
- Higher fixed-set domain mean on the 71 official domain targets.
- Nonzero, correctly mapped QSglob on more of the 104 official oligo targets.
- Reduced hard failures: missing prediction, token-limit failure, metric
  unavailable, metric failed, and missing reference.
- A predeclared multi-candidate attack row that improves over its matching
  `dev_fixed` parent without hidden candidate selection.

## What Does Not Count

- A target-lab improvement that has not become a target-agnostic full benchmark
  rule.
- A single-seed score described as winner-comparable.
- A partial multi-seed run scored as if all candidates exist.
- Confidence-only quality claims.
- A DockQ-only oligo claim against the official server QSglob leaderboard.
