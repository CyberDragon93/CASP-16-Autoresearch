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
- To compare against CASP16 server groups going forward, use
  `casp16_server_protein_v2_aliasfix` instead of rewriting
  `casp16_protein_v1` or the already-used v1 server artifacts.
- `casp16_server_protein_v1` now has a generated skeleton: 175 fixed official
  targets, 106 Protenix jobs, 54 cached references, and 45 unresolved parsed
  domain-subtarget diagnostics.
- `casp16_server_protein_v2_aliasfix` is now generated: 175 fixed official
  targets, 163 Protenix jobs, 79 cached references, 67/71 domain inputs ok,
  and 96/104 oligo inputs ok. It is the default benchmark for future
  winner-comparison claims.
- `leaderboards/casp16_server_protein_v1/official_groups.csv` is server-only;
  `leaderboards/casp16_server_protein_v2_aliasfix/official_groups.csv` is the
  alias-fixed server-only baseline; each version keeps `official_all_groups.csv`
  as a diagnostic.
- Server scoring now enforces metric identity: `GDT_TS` for domains and
  `QSglob` for oligos. DockQ cannot rank server oligo targets.
- Current metric-tool probe: `TMscore` and `USalign` are present in the protein
  conda env; OpenStructure `ost` is installed at
  `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost` and is the
  default QSglob-compatible scorer. The first H0220 probe returned
  `status=ok` but `QSglob=0` because automatic chain/chem mapping failed, so
  assembly mapping is now the bottleneck for affected targets. The scorer now
  records OpenStructure mapping diagnostics in `target_scores.csv` `message`,
  making false-zero classes visible without changing official-compatible
  scores.
- A six-target QSglob signal probe across the four completed server-v1
  Protenix dev runs produced nonzero scores on `H0222` and `T1249V1O`; QSglob
  is useful for strategy triage, but `H0220` remains a clear unmapped false-zero
  risk.
- Current best local server-domain `dev_fixed` run:
  `server_protenix_yang_terminal_tag_cleanup_seed101`, mean `0.066908`.
- `server_protenix_yang_antibody_fv_cleanup_seed101` is a negative
  `dev_fixed` result on domains (`0.060677`) and remains unranked on oligos
  in the checked-in artifacts generated before QSglob scorer installation.
- Multi-candidate work now has a separate policy:
  `docs/SERVER_ATTACK_POLICY.md` and
  `attack_budgets/casp16_server_attack_protenix5.json`.
- A larger planned attack tier now exists as
  `attack_budgets/casp16_server_attack_protenix25.json`: v2 alias-fixed
  benchmark, seeds `101..125`, one sample per seed, confidence-only selector,
  and five predeclared seed shards. Shard run ids and seed ranges are locked in
  `attack_budgets/casp16_server_attack_protenix25_shards.tsv`. It is not queued
  yet.
- A no-over-token larger planned attack tier now exists as
  `attack_budgets/casp16_server_attack_protenix25_nofail.json`: same 25 seeds
  and selector, but using the v2 coverage/stoich/low-complexity/large-fallback
  input with 0 jobs above Protenix's token limit. Shards are locked in
  `attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`. It is
  not queued yet.
- Single-seed `dev_fixed` rows are for debugging and ablations only. Any claim
  about chasing CASP16 server winners must report the attack budget, candidates
  per target, selector, and GPU cost. Run specs and manifests expose
  `budget_tier` plus `candidate_count` so multi-candidate rows stay separate
  from single-seed rankings.
- First attack run spec:
  `server_attack_protenix_terminal_tag_seed101_105`, using terminal-tag cleanup
  inputs with seeds `101..105` and `protenix_confidence_v1`. Slurm job `810719`
  is running; the latest recorded check found only `seed_101` outputs, so it
  is still incomplete and must not be scored as a five-candidate result.
- Queued second attack run spec:
  `server_attack_protenix_coverage_stoich_seed101_105`, using the stacked
  sequence-recovery + large-target fallback + token-safe stoichiometry inputs
  with the same five-candidate `protenix5` budget. It is not submitted yet.
- Queued v2 no-over-token attack run spec:
  `server_v2_attack_nofail_protenix5_seed101_105`, using the v2
  coverage/stoich/low-complexity/large-fallback input with 0 over-token jobs
  and the same five-candidate `protenix5` budget. It is not submitted yet and
  waits behind the three v2 `dev_fixed` rows.
- New coverage-recovery strategy:
  `yang_large_target_split_or_fallback_v1`, which predeclares a token-budget
  fallback for the eight known Protenix `n_token > 2560` failures.
- New sequence-recovery strategy:
  `yang_sequence_recovery_v1`, generated on top of terminal-tag cleanup, repairs
  protein-domain inputs that were missing or locally misparsed as DNA/RNA.
- New stacked coverage strategy:
  `yang_sequence_recovery_large_target_fallback_v1`, generated on top of
  terminal-tag cleanup, combines sequence recovery with token-budget fallback.
  It is queued as
  `server_protenix_yang_sequence_recovery_large_target_fallback_seed101`,
  changes 40 unique targets, and keeps every optimized job under the 2560
  Protenix token limit.
- New exact-stoichiometry artifact:
  `yang_oligo_stoichiometry_recovery_v1` restores official parsed
  `Oligo.State` for protein-only oligo jobs where server inputs collapsed to
  one copy per entity. It changes 9 existing jobs; 5 stay under the Protenix
  limit and 4 require construct/domain-window handling.
- New token-safe stoichiometry strategy:
  `yang_oligo_stoichiometry_token_safe_v1`, generated on top of stacked
  coverage recovery and queued as
  `server_protenix_yang_oligo_stoichiometry_token_safe_seed101`, restores exact
  copy counts for 5 under-budget oligo jobs while keeping the largest
  optimized job at 2535 tokens.
- New v2 baseline candidate:
  `server_v2_protenix_yang_coverage_stoich_seed101` is submitted as Slurm job
  `810938` with dependency on v1 attack job `810719`. It targets
  `casp16_server_protein_v2_aliasfix` and uses the same
  `yang_oligo_stoichiometry_token_safe_v1` transform regenerated on v2,
  producing 163 jobs with 10 changed targets and no recovered job above the
  2560-token limit.
- New v2 construct-cleanup candidate:
  `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` is queued
  behind the v2 baseline. It starts from the v2 coverage/stoich input and adds
  sequence-only low-complexity terminal cleanup, changing 27 sequences across
  21 targets under the same seed-101 `dev_fixed` budget.
- New v2 coverage-recovery candidate:
  `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`
  is queued behind the v2 low-complexity ablation. It starts from that input
  and applies the target-agnostic large-target fallback to the 11 jobs still
  above Protenix's 2560-token limit, leaving 0 oversize jobs under the same
  seed-101 `dev_fixed` budget.
- New H1258 target-lab artifact:
  `target_lab/h1258_interaction_window_v1/` builds the public
  LRRK2-interaction-window clue as LRRK2 residues 861-1014 plus 14-3-3 A1B2.
  It is 648 tokens and must stay out of ranked workflows until generalized.
- New small-complex target-lab batch:
  `target_lab/small_complex_stoich_batch_v1/` combines 5 under-budget exact
  stoichiometry complexes with the H1258 interaction-window job for faster
  learning before full-benchmark promotion. It has been submitted as Slurm job
  `810824`, failed quickly due an OpenDDE/Protenix import-path collision, and
  was resubmitted as job `811114` after the target_lab Protenix environment was
  aligned with the full benchmark run scripts. Job `811114` is now running on
  `c639-081` and has started producing CIF files. It has `summarize_outputs.py`
  plus `score_dockq.py` for post-run diagnostics.
- New domain-fragment target-lab batch:
  `target_lab/domain_fragment_batch_v1/` turns the domain-decomposition recipe
  into 12 runnable Protenix fragment jobs. It has been submitted as Slurm job
  `810862`, is running on `c622-022`, and must stay out of ranked server
  comparisons.

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
- `docs/QSGLOB_SCORER.md`: installed OpenStructure QSglob scorer, mapping
  diagnostics, and validation notes
- `docs/REFERENCE_GAP_AUDIT.md`: server benchmark reference/input coverage gaps
- `attack_budgets/`: JSON attack-budget definitions
- `docs/AUTORESEARCH_QUEUE.md`: current execution queue for strategy attempts
- `docs/EXPERIMENTS.md`: append-only autoresearch experiment log
- `docs/TARGET_LAB_PROMOTION.md`: promotion gates from target_lab diagnostics
  to full-benchmark strategy runs
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
  predictions and 19 `metric_unavailable` rows in the checked-in
  pre-OpenStructure artifacts.

The server baselines remain far ahead: domain server top `110s` has fixed mean
`0.923321` on GDT_TS, and oligo server top `456s` has fixed mean `0.582615` on
QSglob.

The best current local full Protenix server-domain run is
`server_protenix_yang_terminal_tag_cleanup_seed101`, with fixed-set mean
`0.066908`. This is still a failure-level score relative to the official
server top group and should be treated as a baseline for iteration, not as a
competitive result.

## Work Queue

1. Validate OpenStructure `ost` QSglob assembly/chain mapping on server oligos
   where the signal probe found false-zero risk (`H0220`, partial empty chem
   mapping cases such as `T0234O`/`T1249V1O`). Use the scorer `message`
   diagnostics to identify target-agnostic false-zero classes.
2. Add explicit domain cropping and chain/residue mapping for
   `casp16_server_protein_v2_aliasfix` domain `GDT_TS` scoring.
3. Improve the reference/domain registry for the remaining 96 alias-fixed
   server-benchmark targets that currently lack a cached reference mapping.
4. Add oligo assembly mapping.
5. Queue and score the generated large-target split/fallback policy for the
   eight `n_token > 2560` failures after the active attack job.
6. Re-score current OpenDDE and Protenix-style baselines on the server
   benchmark after the QSglob mapping check, with complete prediction coverage
   rather than local-v1 reuse.
7. Monitor and score `server_attack_protenix_terminal_tag_seed101_105`, the
   first fixed 5-candidate attack run. Keep it separate from `dev_fixed`.
8. Submit `server_protenix_yang_large_target_split_or_fallback_seed101` after
   the active attack job if coverage recovery remains the highest-leverage next
   move.
9. Submit `server_protenix_yang_sequence_recovery_seed101` after the active
   pending jobs if recovering `T1212`, `T1239V1/V2`, and `T2280` looks higher
   leverage than another construct-only run.
10. Submit the stacked
    `server_protenix_yang_sequence_recovery_large_target_fallback_seed101`
    candidate after the active pending jobs if the component coverage fixes
    still look complementary.
11. Submit the token-safe
    `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` candidate
    after the current coverage jobs if exact stoichiometry remains the next
    useful oligo signal.
12. Build public/domain-window experiments for oversize exact-stoichiometry
    systems such as H1258.
13. Run the H1258 target-lab interaction-window job when a small GH200 slot is
    available, then decide whether a target-agnostic window rule is worth a
    full benchmark candidate.
14. Monitor target_lab job `811114` for
    `target_lab/small_complex_stoich_batch_v1`, then inspect predictions for
    exact-stoichiometry and H1258-window behavior before spending full
    benchmark compute. Regenerate `SUMMARY.md` with
    `python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py` and
    diagnostic `DOCKQ.md` with
    `python target_lab/small_complex_stoich_batch_v1/score_dockq.py`.
15. Implement strategy experiments inspired by CASP16 winners: disorder
    trimming, domain decomposition, MSA/template optimization, assembly-aware
    multimer handling, and model ranking.
16. Monitor target_lab job `810862` for
    `target_lab/domain_fragment_batch_v1`. It is running on `c622-022` and has
    passed the Protenix import/env bootstrap. After completion, inspect
    fragment coverage and confidence diagnostics. Promote only a
    target-agnostic segmentation rule, not CASP-domain-summary hand crops.
17. Keep `server_attack_protenix_coverage_stoich_seed101_105` queued as the
    next realistic attack-budget candidate. Submit it only when
    `./casp16 run-next --benchmark casp16_server_protein_v1 --dry-run` selects
    it, or intentionally supersede it after the component single-seed coverage
    runs report negative evidence.
18. Done: created `casp16_server_protein_v2_aliasfix`; future serious
    winner-comparison runs should target it or a newer explicit server
    benchmark version.
19. Monitor and score Slurm job `810938`
    (`server_v2_protenix_yang_coverage_stoich_seed101`) after the active v1
    attack job finishes. This is the first v2 `dev_fixed` baseline and should
    be scored before launching larger v2 attack budgets.
20. Keep `casp16_server_attack_protenix25` as the planned winner-scale upgrade
    path: execute only after `protenix5` and the v2 dev baseline are scored,
    and only as predeclared seed shards.
21. After `server_v2_protenix_yang_coverage_stoich_seed101` is scored, run
    `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` as the
    next v2 `dev_fixed` construct-cleanup ablation if queue state permits.
22. After the v2 low-complexity ablation is scored, run
    `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`
    to test whether removing the remaining 11 token-limit hard failures is
    worth the assembly simplification.
23. Keep `casp16_server_attack_protenix25_nofail` as the stronger planned
    winner-scale budget if the no-over-token v2 stack scores well enough to
    justify 25-seed compute. Do not launch it before the active `protenix5`
    and v2 dev rows give evidence, unless a supersession decision is recorded.
24. Keep `server_v2_attack_nofail_protenix5_seed101_105` queued behind the
    three v2 `dev_fixed` rows as the first five-candidate no-over-token attack
    check.

## Run Discipline

- Use CLI-generated run specs.
- Keep fixed benchmark rules fixed.
- Record hypotheses and knobs before scoring.
- Never use official scores or references to tune target-specific prediction
  behavior.
- Prefer full-benchmark effects over one-off rescue scores.
- Keep `dev_fixed` and `server_attack` results in separate comparisons.
- When reporting progress, always name the budget tier. Do not describe a
  one-seed/one-sample result as winner-comparable.
