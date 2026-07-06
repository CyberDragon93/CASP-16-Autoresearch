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
- To compare against CASP16 server groups, build
  `casp16_server_protein_v1` instead of rewriting `casp16_protein_v1`.

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
- `docs/STRATEGY_TEMPLATE.md`: template for each new strategy record
- `benchmarks/casp16_protein_v1/`: current locked local benchmark
- `runs/`: append-only run specs, scripts, logs, and manifests
- `leaderboards/`: generated leaderboard artifacts

## Current Method Baseline

The best current OpenDDE local run is an engineering baseline on
`casp16_protein_v1`. It improves local coverage and score, but it does not beat
the CASP16 official or server baselines. Treat it as a launch point for
strategy iteration, not as an official-server result.

## Work Queue

1. Build `casp16_server_protein_v1` from official protein score-table target
   sets.
2. Add official-compatible domain `GDT_TS` scoring.
3. Add official-compatible oligo `QSglob` scoring and assembly mapping.
4. Re-score current OpenDDE and Protenix-style baselines on the server
   benchmark.
5. Implement strategy experiments inspired by CASP16 winners:
   disorder trimming, domain decomposition, MSA/template optimization,
   assembly-aware multimer handling, and model ranking.

## Run Discipline

- Use CLI-generated run specs.
- Keep fixed benchmark rules fixed.
- Record hypotheses and knobs before scoring.
- Never use official scores or references to tune target-specific prediction
  behavior.
- Prefer full-benchmark effects over one-off rescue scores.

