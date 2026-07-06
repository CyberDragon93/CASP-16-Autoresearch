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
  and selector, but now using the MSA-reused v2 oligo-recovery nofail stack with
  protein-oligo sequence recovery, token-safe stoichiometry, low-complexity
  cleanup, large-target fallback, 165 jobs, and 0 jobs above Protenix's token
  limit. Its input pre-fills exact-sequence MSA paths for 268/268 protein
  chains from the current v2 dev row. Shards are locked in
  `attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`. It is
  not queued yet.
- Single-seed `dev_fixed` rows are for debugging and ablations only. Any claim
  about chasing CASP16 server winners must report the attack budget, candidates
  per target, selector, and GPU cost. Run specs and manifests expose
  `budget_tier` plus `candidate_count` so multi-candidate rows stay separate
  from single-seed rankings.
- Budget realism is mandatory: the public winner recipes almost certainly used
  more than one internal candidate, but the hidden budget should be modeled as
  total candidates per target, not just literal Protenix seed count. Seeds,
  samples, MSA/template variants, model/backend variants, refinement passes,
  ranking passes, and submitted models all count and must be declared before
  scoring.
- First attack run spec:
  `server_attack_protenix_terminal_tag_seed101_105`, using terminal-tag cleanup
  inputs with seeds `101..105` and `protenix_confidence_v1`. Slurm job `810719`
  is running; the latest recorded check found 98 `seed_101` CIFs and 79
  `seed_102` CIFs, so it is still incomplete and must not be scored as a
  five-candidate result.
- Queued second attack run spec:
  `server_attack_protenix_coverage_stoich_seed101_105`, using the stacked
  sequence-recovery + large-target fallback + token-safe stoichiometry inputs
  with the same five-candidate `protenix5` budget. It is not submitted yet.
- Superseded v2 no-over-token attack run spec:
  `server_v2_attack_nofail_protenix5_seed101_105`, using the v2
  coverage/stoich/low-complexity/large-fallback input with 0 over-token jobs
  and the same five-candidate `protenix5` budget. It lacks protein-oligo
  sequence recovery and must stay an ablation unless explicitly relaunched.
- Superseded stronger v2 no-over-token attack run spec:
  `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105`, using the
  new protein-oligo sequence recovery + token-safe stoichiometry +
  low-complexity cleanup + large-target fallback input. It has 165 jobs, 0 jobs
  above the Protenix token limit, and candidate_count `5`, but is now
  superseded by the exact-sequence MSA-reuse successor.
- MSA-reused queued v2 no-over-token attack run spec:
  `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
  uses the same 165-job input stack plus exact-sequence MSA paths from the
  current v2 dev row's `inputs-update-msa.json`. The reuse report has 268
  protein chains reused, 0 missing sources, and 0 kept-existing rows. This
  supersedes the non-reuse attack row for the next v2 `protenix5` launch.
- New v2 hydrophobic-leader nofail derivative:
  `yang_oligo_sequence_stoich_low_complexity_hydrophobic_leader_large_fallback_v1`
  starts from the strongest v2 nofail stack and applies the existing
  sequence-only hydrophobic leader rule. It changes 8 sequences in 8 targets
  (`T0240/T1210/T1240` plus phase/oligo aliases), keeps 165 jobs, max length
  2535, and 0 over-token jobs. Its MSA-reuse input reuses 260/268 protein-chain
  MSA paths and intentionally misses the 8 changed sequences. It is registered
  as
  `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101`.
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
  `server_v2_protenix_yang_coverage_stoich_seed101` was submitted as Slurm job
  `810938` with dependency on v1 attack job `810719`, but it is now
  append-only superseded in `runs/status.tsv` by the stronger
  oligo-recovery nofail stack. Because the Slurm wrapper calls
  `./casp16 run-next --benchmark casp16_server_protein_v2_aliasfix`, dry-run
  now selects
  `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`.
  The old dependency was cleared with `scontrol update JobId=810938
  Dependency=` and the job is now running the current v2 nofail row.
- Superseded v2 construct-cleanup candidate:
  `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` is queued
  only as an ablation. It starts from the v2 coverage/stoich input and adds
  sequence-only low-complexity terminal cleanup, changing 27 sequences across
  21 targets under the same seed-101 `dev_fixed` budget, but lacks the
  protein-oligo sequence recovery now used by the main queue.
- Superseded v2 coverage-recovery candidate:
  `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`
  is queued only as an ablation. It starts from that input
  and applies the target-agnostic large-target fallback to the 11 jobs still
  above Protenix's 2560-token limit, leaving 0 oversize jobs under the same
  seed-101 `dev_fixed` budget, but also lacks protein-oligo sequence recovery.
- New v2 protein-oligo sequence recovery artifact:
  `yang_protein_oligo_sequence_recovery_v1` repairs protein-oligo rows whose
  local server inputs were missing or parsed as nucleic-acid records even
  though the official sequence archive contains protein-like records. On
  `casp16_server_protein_v2_aliasfix` it changes 5 targets:
  `H0220`, `H1213`, `H1220`, `H2213`, and `H2220`.
- New v2 protein-oligo sequence + token-safe stoichiometry artifact:
  `yang_protein_oligo_sequence_stoich_token_safe_v1` composes the oligo
  sequence recovery with token-safe stoichiometry recovery. On
  `casp16_server_protein_v2_aliasfix` it changes 15 unique targets, including
  restoring `H1220/H2220` to the recovered protein sequences with `A1B4`
  stoichiometry. It is generated but not queued. It is not a no-over-token
  full-stack artifact: existing v2 jobs such as `H0272` still exceed the
  Protenix token limit, so promotion needs either a fallback stack or a
  deliberate budget decision.
- New strongest v2 no-over-token input stack:
  `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` composes
  protein-oligo sequence recovery, token-safe official stoichiometry,
  low-complexity cleanup, and large-target fallback. It has 165 jobs, max
  optimized length 2535, and 0 jobs above 2560 tokens. It is registered as
  `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
  for `dev_fixed` comparison and
  `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
  for the five-candidate MSA-reused `server_attack` tier.
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
  aligned with the full benchmark run scripts. Job `811114` produced 6/6
  structures and confidence files. Diagnostic DockQ results: `H1233=0.850`
  strong positive, `H1236=0.206` moderate, `H1232=0.023` weak; `H1244/H1267`
  lack cached references and the H1258 window failed DockQ chain mapping
  despite high confidence. This supports exact-stoichiometry as target-lab
  evidence for some complexes, but not H1258 hard-window promotion.
- New domain-fragment target-lab batch:
  `target_lab/domain_fragment_batch_v1/` turns the domain-decomposition recipe
  into 12 runnable Protenix fragment jobs. Slurm job `810862` completed on
  `c622-022` with 12/12 structures and confidence files; `SUMMARY.md` and
  `summary.tsv` have been regenerated. This is useful D2 recipe evidence but
  must stay out of ranked server comparisons unless converted into a
  target-agnostic segmentation rule or a new benchmark version.

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
- `docs/SERVER_SCORE_TARGETS.md`: official server leaders to beat and current
  local gap
- `docs/SERVER_ATTACK_POLICY.md`: fixed multi-seed attack-budget rules
- `docs/MSA_CACHE_PLAN.md`: exact-sequence MSA reuse workflow and guardrails
- `docs/QSGLOB_SCORER.md`: installed OpenStructure QSglob scorer, mapping
  diagnostics, and validation notes
- `docs/REFERENCE_GAP_AUDIT.md`: server benchmark reference/input coverage gaps
- `attack_budgets/`: JSON attack-budget definitions
- `./casp16 merge-shards`: registers completed seed-sharded attack predictions
  as one merged run before scoring
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
QSglob. `docs/SERVER_SCORE_TARGETS.md` is the pinned score target for this
autoresearch loop.

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
5. Done: superseded the older v2 nofail attack rows with
   `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`.
   It keeps the current best runnable input stack and avoids repeated
   cross-run MSA search by exact protein sequence hash.
6. Queue and score the generated large-target split/fallback policy for the
   eight `n_token > 2560` failures after the active attack job.
7. Re-score current OpenDDE and Protenix-style baselines on the server
   benchmark after the QSglob mapping check, with complete prediction coverage
   rather than local-v1 reuse.
8. Monitor and score `server_attack_protenix_terminal_tag_seed101_105`, the
   first fixed 5-candidate attack run. Keep it separate from `dev_fixed`.
9. Submit `server_protenix_yang_large_target_split_or_fallback_seed101` after
   the active attack job if coverage recovery remains the highest-leverage next
   move.
10. Submit `server_protenix_yang_sequence_recovery_seed101` after the active
   pending jobs if recovering `T1212`, `T1239V1/V2`, and `T2280` looks higher
   leverage than another construct-only run.
11. Submit the stacked
    `server_protenix_yang_sequence_recovery_large_target_fallback_seed101`
    candidate after the active pending jobs if the component coverage fixes
    still look complementary.
12. Submit the token-safe
    `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` candidate
    after the current coverage jobs if exact stoichiometry remains the next
    useful oligo signal.
13. Build public/domain-window experiments for oversize exact-stoichiometry
    systems such as H1258.
14. Run the H1258 target-lab interaction-window job when a small GH200 slot is
    available, then decide whether a target-agnostic window rule is worth a
    full benchmark candidate.
15. Completed target_lab job `811114` for
    `target_lab/small_complex_stoich_batch_v1`, then regenerated its summary
    and diagnostic DockQ report. Treat the strong H1233 exact-stoichiometry
    signal as target-lab evidence only; do not promote H1258 hard-windowing
    because DockQ chain mapping failed.
16. Implement strategy experiments inspired by CASP16 winners: disorder
    trimming, domain decomposition, MSA/template optimization, assembly-aware
    multimer handling, and model ranking.
17. Completed target_lab job `810862` for
    `target_lab/domain_fragment_batch_v1`. It produced 12/12 structures and
    confidence files, with high confidence on most fragments. Next, inspect
    fragment quality only as target-lab evidence and promote only a
    target-agnostic segmentation rule, not CASP-domain-summary hand crops.
18. Keep `server_attack_protenix_coverage_stoich_seed101_105` queued as the
    next realistic attack-budget candidate. Submit it only when
    `./casp16 run-next --benchmark casp16_server_protein_v1 --dry-run` selects
    it, or intentionally supersede it after the component single-seed coverage
    runs report negative evidence.
19. Done: created `casp16_server_protein_v2_aliasfix`; future serious
    winner-comparison runs should target it or a newer explicit server
    benchmark version.
20. Monitor Slurm job `810938` after the active v1 attack job finishes. Its
    wrapper was created for the older v2 coverage/stoich run, but current
    `run-next --dry-run` selects
    `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
    because the older v2 rows were superseded.
21. Keep `casp16_server_attack_protenix25` as the planned winner-scale upgrade
    path: execute only after `protenix5` and the v2 dev baseline are scored,
    and only as predeclared seed shards.
22. The older v2 coverage/stoich, low-complexity, and no-over-token rows are
    now superseded by the oligo-recovery nofail stack. Run them only as
    explicit ablations.
23. Keep `casp16_server_attack_protenix25_nofail` as the stronger planned
    winner-scale budget if the no-over-token v2 stack scores well enough to
    justify 25-seed compute. Its JSON and shard manifest now point at the
    MSA-reused
    `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` input.
24. Score
    `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
    before deciding whether to launch the corresponding five-candidate attack
    or jump directly to a larger predeclared budget.
25. Prefer
    `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
    over both older v2 nofail attack rows for the first v2 five-candidate
    no-over-token attack, unless an explicit ablation requires running a
    non-reuse stack.
26. Run the hydrophobic-leader nofail `dev_fixed` derivative only after the
    active v2 nofail row and queued MSA-reuse attack path are handled. It is a
    narrow construct-cleanup ablation, not a replacement for the current main
    queue.

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
