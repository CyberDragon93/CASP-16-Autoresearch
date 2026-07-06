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

## Active Score Gates

1. Score the running v2 nofail `dev_fixed` row:
   `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`.
   It must first produce CIFs for the 165-job oligo-recovery nofail input.
   The partial `2026-07-06 17:11 CDT` QSglob probe had 8 scorer-ok oligo rows
   but only one nonzero score, so it is not evidence to launch the planned
   25-candidate budget before the full v2 row is complete.
   If other v2 rows are pending or partially running, use
   `./casp16 score --benchmark casp16_server_protein_v2_aliasfix --run-id <run_id> --output-dir diagnostics/...`
   for the first readout so pending attack rows do not contaminate a diagnostic
   score table.
2. Compare only `dev_fixed` to `dev_fixed`. A single-seed row can prove that an
   input strategy is worth more compute, but it is not winner-comparable.
3. Score `server_attack` rows only after every declared candidate is present.
   Partial target candidates score `0`; seed shards must be merged with
   `./casp16 merge-shards` before a 25-candidate row can be scored.
4. For official server comparison, domains use `GDT_TS`; oligos use `QSglob`.
   DockQ and confidence are diagnostics only.

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
