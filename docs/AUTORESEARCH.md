# CASP16 Autoresearch Notes

This is the working index for agent-driven CASP16 strategy iteration. The
benchmark is the protocol; strategy code and run directories are the only place
where methods should change.

## Current Truth

- `casp16_protein_v1` is a local protein-first leaderboard, not the official
  CASP16 server leaderboard.
- Current local ranked set: 39 targets, split into 16 protein-domain targets
  and 23 protein-oligo targets.
- Current official score-table target sets: 71 protein-domain targets and 104
  protein-oligo targets.
- To compare against CASP16 server groups, use
  `casp16_server_protein_v1` instead of rewriting `casp16_protein_v1`.
- `casp16_server_protein_v1` now has a generated skeleton: 175 fixed official
  targets, 106 Protenix jobs, 54 cached references, and 45 unresolved parsed
  domain-subtarget diagnostics.
- `leaderboards/casp16_server_protein_v1/official_groups.csv` is server-only;
  `official_all_groups.csv` is diagnostic.
- Server scoring now enforces metric identity: `GDT_TS` for domains and
  `QSglob` for oligos. DockQ cannot rank server oligo targets.
- Current best local server-domain `dev_fixed` run:
  `server_protenix_yang_terminal_tag_cleanup_seed101`, mean `0.066908`.
- `server_protenix_yang_antibody_fv_cleanup_seed101` is a negative
  `dev_fixed` result on domains (`0.060677`) and remains unranked on oligos
  because QSglob is missing.
- Multi-candidate work now has a separate policy:
  `docs/SERVER_ATTACK_POLICY.md` and
  `attack_budgets/casp16_server_attack_protenix5.json`.

## Main Objective

Improve automatic CASP16 protein prediction strategies while preserving a
stable, fair leaderboard. The near-term target is not to claim a win from the
small local v1 leaderboard, but to construct a server-compatible benchmark and
then improve methods against that harder target set.

## Key Files

- `AGENTS.md`: operating rules for agents and humans
- `docs/LEADERBOARD_RULES.md`: locked local leaderboard rules
- `docs/CASP16_SERVER_BENCHMARK.md`: plan for server-track comparison
- `docs/CASP16_WINNER_RECIPES.md`: notes on known CASP16 winning approaches
- `docs/SERVER_ATTACK_POLICY.md`: fixed multi-seed attack-budget rules
- `attack_budgets/`: JSON attack-budget definitions
- `docs/AUTORESEARCH_QUEUE.md`: current execution queue for strategy attempts
- `docs/EXPERIMENTS.md`: append-only autoresearch experiment log
- `docs/STRATEGY_TEMPLATE.md`: template for each new strategy record
- `target_lab/TARGET_RECOMMENDATIONS.txt`: target_lab diagnostics and
  non-ranked single-target learning targets
- `benchmarks/casp16_protein_v1/`: current locked local benchmark
- `runs/`: append-only run specs, scripts, logs, and manifests
- `leaderboards/`: generated leaderboard artifacts

## Current Method Baseline

The best current OpenDDE local run is an engineering baseline on
`casp16_protein_v1`. It improves local coverage and score, but it does not beat
the CASP16 official or server baselines. Treat it as a launch point for
strategy iteration, not as an official-server result.

The current server-benchmark diagnostic reuse run is
`server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1`. It reuses 35
existing OpenDDE predictions and is intentionally unranked because it was not
generated as a full fixed-budget server benchmark run. Current
`casp16_server_protein_v1` results:

- protein domain: mean `0.036428` over 71 fixed targets, with 9 scored and 62
  missing predictions.
- protein oligo: mean `0.000000` over 104 fixed targets, with 85 missing
  predictions and 19 `metric_unavailable` rows because QSglob scoring is not
  installed yet.

The server baselines remain far ahead: domain server top `110s` has fixed mean
`0.923321` on GDT_TS, and oligo server top `456s` has fixed mean `0.582615` on
QSglob.

The best current local full Protenix server-domain run is
`server_protenix_yang_terminal_tag_cleanup_seed101`, with fixed-set mean
`0.066908`. This is still a failure-level score relative to the official
server top group and should be treated as a baseline for iteration, not as a
competitive result.

## Work Queue

1. Install or register a real `QSglob` scorer for server oligos.
2. Add explicit domain cropping and chain/residue mapping for
   `casp16_server_protein_v1` domain `GDT_TS` scoring.
3. Improve the reference/domain registry for the 121 server-benchmark targets
   that currently lack a cached reference mapping.
4. Add oligo assembly mapping.
5. Predeclare a large-target split/fallback policy for the eight
   `n_token > 2560` failures before launching another full run.
6. Re-score current OpenDDE and Protenix-style baselines on the server
   benchmark with complete prediction coverage rather than local-v1 reuse.
7. Use `server_attack` only after the budget and selection policy are locked;
   the current defined budget is `casp16_server_attack_protenix5`.
8. Implement strategy experiments inspired by CASP16 winners: disorder
   trimming, domain decomposition, MSA/template optimization, assembly-aware
   multimer handling, and model ranking.

## Run Discipline

- Use CLI-generated run specs.
- Keep fixed benchmark rules fixed.
- Record hypotheses and knobs before scoring.
- Never use official scores or references to tune target-specific prediction
  behavior.
- Prefer full-benchmark effects over one-off rescue scores.
- Keep `dev_fixed` and `server_attack` results in separate comparisons.
