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
- v2 alias-fixed scoring now resolves prediction artifacts through
  `sequence_lookup_id` as well as `target_id`. This matters for official oligo
  rows such as `T0206O` and `T1249V1O`, whose Protenix jobs are named `T0206`
  and `T1249V1`. Without this alias path, valid oligo predictions are falsely
  counted as missing.
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
- A scoreable-target no-over-token larger planned attack tier now exists as
  `attack_budgets/casp16_server_attack_protenix25_scoreable_nofail.json`: same
  25 seeds and selector, but only the 74 jobs that currently have at least one
  locally available reference alias. It preserves the fixed 175-target scoring
  set through the benchmark `input_manifest.tsv` and requires complete
  exact-sequence MSA reuse from `data/msa_cache/index.tsv`. It is not queued
  yet; use it only if the running scoreable `protenix5` row is worth scaling.
- MSA cache infra now has a read-only `check-msa-cache` preflight,
  materialized local A3M storage under ignored `data/msa_cache/store/`, and
  `run-next` stale-path auditing. The scoreable v2 attack input checks at
  141/141 reusable protein chains, 0 missing sources, and 0 stale cached paths
  against `data/msa_cache/index.tsv`; future MSA-heavy shards should pass this
  check before Slurm submission.
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
  is running. The `2026-07-06 18:25 CDT` check found seed CIF counts
  `98/98/67/0/0`; the log still hits the known `n_token > 2560` classes, so it
  is incomplete and must not be scored as a five-candidate result.
- Superseded second attack run spec:
  `server_attack_protenix_coverage_stoich_seed101_105`, using the stacked
  sequence-recovery + large-target fallback + token-safe stoichiometry inputs
  with the same five-candidate `protenix5` budget. It has been replaced by
  `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` to avoid
  repeating MSA search, but that successor only reuses 180/196 exact-sequence
  protein-chain paths and remains lower priority than the v2 scoreable nofail
  path.
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
- Superseded full-input MSA-reused v2 no-over-token attack run spec:
  `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
  uses the same 165-job input stack plus exact-sequence MSA paths from the
  current v2 dev row's `inputs-update-msa.json`. The reuse report has 268
  protein chains reused, 0 missing sources, and 0 kept-existing rows. It is now
  superseded by the scoreable-subset attack below because the full 165-job input
  repeats no-reference heavy jobs such as `T1295/T1295O` before those targets
  can improve the local score.
- Queued scoreable-subset MSA-reused v2 attack run spec:
  `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`
  keeps the same five-candidate `server_attack` budget and selector, but filters
  prediction inputs to 74/165 jobs that have at least one locally available
  reference alias. Its run-spec injects exact-sequence MSA paths from
  `data/msa_cache/index.tsv` for 141/141 protein chains and requires complete
  reuse before launch. The fixed 175-target server benchmark scoring set is not
  changed: skipped no-reference targets still score 0 locally. `run-next
  --dry-run` selected this row. Slurm job `811751` is now running on
  `c636-072`; the Protenix log confirms `inputs.msa-reuse.json` and skips MSA
  update. The `2026-07-06 18:25 CDT` check found 20/74 seed-101 CIFs; no
  later seeds have started, so it remains incomplete and unranked.
- Cancelled full-input v2 no-over-token dev row:
  `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
  produced 39/165 CIFs and then spent extended GPU time on `T1295`, which is
  `no_reference_pdb` in the local benchmark. It is append-only marked
  `cancelled:scoreable_subset_attack`; keep its partial predictions/MSA cache
  only, and do not resume full-input v2 dev before reference recovery.
- Early v2 oligo probe:
  `diagnostics/qsglob_probes/server_v2_partial_early_oligo_probe.csv` scored
  the eight completed oligo targets that already had references
  (`T0206O/T0234O/T0235O/T1201O/T1206O/T1234O/T1235O/T1249V1O`). All eight
  rows were scorer-ok, but only `T1249V1O` was nonzero (`QSglob=0.096`). This
  is a weak early signal: wait for the full v2 dev row before spending the
  larger `protenix25` budget.
- Filtered scoring is now available through `./casp16 score --run-id <run_id>`.
  Use it with an explicit `--output-dir diagnostics/...` for the first readout
  of completed runs while attack rows are still pending or partial. The first
  partial v2 diagnostic is
  `diagnostics/score_probes/server_v2_partial_filtered/target_scores.csv`;
  it is not a leaderboard artifact.
- New v2 hydrophobic-leader nofail derivative:
  `yang_oligo_sequence_stoich_low_complexity_hydrophobic_leader_large_fallback_v1`
  starts from the strongest v2 nofail stack and applies the existing
  sequence-only hydrophobic leader rule. It changes 8 sequences in 8 targets
  (`T0240/T1210/T1240` plus phase/oligo aliases), keeps 165 jobs, max length
  2535, and 0 over-token jobs. Its MSA-reuse input reuses 260/268 protein-chain
  MSA paths and intentionally misses the 8 changed sequences. It is registered
  as
  `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101`.
  The pending Slurm wrapper job `811754` was cancelled after `run-next
  --dry-run` showed no pending v2 row. The run row stays deferred until the
  scoreable-subset attack and full v2 dev score clarify whether this ablation
  deserves a slot.
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
  `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`
  for the current five-candidate scoreable-subset MSA-reused `server_attack`
  tier while local references are incomplete.
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
- New antibody-Fv target-lab run:
  `targetlab_protenix_yang_antibody_fv_seed101` runs the eight Fv-only
  antibody-antigen jobs from `yang_antibody_fv_fragment_inputs_v1` with full
  MSA/template Protenix settings. It is `benchmark_name=target_lab`,
  `budget_tier=diagnostic`, and `rank_eligible=false`; Slurm job `811918`
  completed on `c620-142` with 8/8 CIFs. The confidence-only diagnostic signal
  is strongest on `H0233__fv` and `H1233__fv`, where antigen-to-antibody pair
  ipTM is about `0.91-0.94`. A DockQ diagnostic also succeeded for 8/8 jobs:
  `H0233__fv=0.916`, `H1233__fv=0.891`, `H1225__fv=0.538`,
  `H0222__fv=0.431`, `H1222__fv=0.383`, and weaker mixed cases for
  `H0223/H1223/H0225`. This supports more O5 assembly/scoring work, not direct
  leaderboard promotion.
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
- `./casp16 qsglob-probe`: targeted QSglob diagnostic command that writes
  `diagnostics/qsglob_probes/*.csv` without touching `leaderboards/*`
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
   `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`.
   It keeps the current best runnable input stack for locally scoreable jobs,
   avoids repeated cross-run MSA search by exact protein sequence hash, and
   leaves no-reference targets as fixed-set local zeros.
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
14. H1258 interaction-window standalone is covered by
    `target_lab/small_complex_stoich_batch_v1`; do not spend another GH200 slot
    on the same standalone job unless a new target-agnostic window rule exists.
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
18. Completed target_lab job `811918` for
    `targetlab_protenix_yang_antibody_fv_seed101`. It is a diagnostic O5
    antibody/Fv run with full MSA/template settings and no ranked leaderboard
    eligibility. It produced 8/8 CIFs; `H0233__fv` and `H1233__fv` have the
    strongest antigen-antibody pair-confidence signal. Across the batch,
    pLDDT is `85.872..94.151`, pTM is `0.865..0.954`, and ipTM is
    `0.777..0.942`. DockQ succeeded for 8/8 jobs and found strong positives on
    `H0233__fv=0.916` and `H1233__fv=0.891`, so O5 is now a real target-lab
    signal rather than confidence-only optimism.
19. Do not launch the non-reuse
    `server_attack_protenix_coverage_stoich_seed101_105` row. Its MSA-reuse
    successor
    `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` is pending,
    but the preflight still misses 16/196 exact-sequence protein-chain MSA
    sources. Keep it as a lower-priority v1 ablation while the v2 scoreable
    nofail attack runs with complete 141/141 MSA reuse.
20. Done: created `casp16_server_protein_v2_aliasfix`; future serious
    winner-comparison runs should target it or a newer explicit server
    benchmark version.
21. Done: cancelled Slurm job `810938` after it reached local no-reference
    `T1295`. Keep the partial full-input v2 artifacts as cache evidence only.
22. Keep `casp16_server_attack_protenix25` as the planned winner-scale upgrade
    path for broader full-input ablation. While references are incomplete, the
    preferred scale-up path is the scoreable 25-seed budget below.
23. The older v2 coverage/stoich, low-complexity, and no-over-token rows are
    now superseded by the oligo-recovery nofail stack. Run them only as
    explicit ablations.
24. Keep `casp16_server_attack_protenix25_nofail` as the stronger planned
    winner-scale budget if the no-over-token v2 stack scores well enough to
    justify 25-seed compute. Its JSON and shard manifest now point at the
    MSA-reused
    `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1` input.
25. Do not resume
    `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
    before reference recovery. It was cancelled at `T1295` after producing
    partial artifacts and MSA cache; local score progress now comes from the
    scoreable-subset attack.
26. Prefer
    `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`
    for the first v2 five-candidate no-over-token attack while local references
    are incomplete. It preserves the fixed scoring set but avoids spending GPU
    time on jobs that currently cannot affect local score. This is now running
    as Slurm job `811751`.
27. Run the hydrophobic-leader nofail `dev_fixed` derivative only after the
    active v2 nofail row and scoreable-subset MSA attack are handled. It is a
    narrow construct-cleanup ablation, not a replacement for the current main
    queue.
28. Use `casp16_server_attack_protenix25_scoreable_nofail` as the planned
    winner-scale successor if the running scoreable `protenix5` row is
    positive. Keep the older 165-job `protenix25_nofail` as a full-input
    ablation until references are recovered.

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
