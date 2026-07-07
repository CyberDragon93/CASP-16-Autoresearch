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
  `status=ok` and `QSglob=0`; follow-up probes against the 9h1g assembly and a
  cropped A/B reference showed that this class is not fixed by scorer
  permissiveness alone. The actionable root cause for the current input stack
  was phase-alias stoichiometry: early-phase `H0220` kept local `A1B1` while
  later official aliases `H1220/H2220` expose `A1B4`. The scorer still records
  OpenStructure mapping diagnostics in `target_scores.csv` `message`, but the
  next compute should use the fixed input, not retune QSglob.
- A six-target QSglob signal probe across the four completed server-v1
  Protenix dev runs produced nonzero scores on `H0222` and `T1249V1O`; QSglob
  is useful for strategy triage, but stale `H0220` predictions remain a clear
  input-realism failure until they are regenerated with `A1B4`.
- Current best local server-domain `dev_fixed` run:
  `server_protenix_yang_terminal_tag_cleanup_seed101`, mean `0.066908`.
- `server_protenix_yang_antibody_fv_cleanup_seed101` is a negative
  `dev_fixed` result on domains (`0.060677`) and remains unranked on oligos
  in the checked-in artifacts generated before QSglob scorer installation.
- Current v2 diagnostic floor is still coverage-limited, not winner-close:
  `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
  has domain mean `0.049685` with only 13/71 OK domain targets, and oligo mean
  `0.000923` with only 8/104 OK oligo targets. The only nonzero v2 oligo
  diagnostic is `T1249V1O` at QSglob `0.096`. Reference recovery,
  missing-prediction coverage, and target-agnostic QSglob assembly mapping
  should happen before spending 25-seed shards.
- Reference recovery now has a concrete v2 worklist:
  `diagnostics/reference_gap/casp16_server_protein_v2_aliasfix_missing_references.tsv`.
  It contains 96 ranked missing-reference targets; 40 already have a v2
  diagnostic prediction waiting on native/reference mapping, 51 are pure
  reference-registry gaps, and 5 need sequence/input alias repair first. Treat
  this only as scoring-infrastructure triage, never as target-specific
  prediction guidance.
- `2026-07-06 18:57 CDT` reference-gap audit update: several high-priority
  `missing_reference` rows first need input-kind repair, not native hunting.
  `T1276`, `T1228V1`, and `T2276` were locally represented as short DNA jobs
  even though the official sequence archive has protein-like records; `T1239V1`
  has the same protein/DNA modality bug despite already having a local
  reference. The new artifact
  `strategies/yang_domain_sequence_recovery_oligo_nofail_v1/casp16_server_protein_v2_aliasfix/`
  composes domain sequence recovery onto the strongest v2 nofail stack,
  changes 8 domain jobs, keeps 169 jobs under the Protenix token limit, and
  should be treated as an input-repair candidate rather than a reference-map
  patch.
- MSA cache coverage for that domain-sequence-recovery nofail artifact is
  almost complete but not launch-clean: 269/276 protein chains are covered from
  `data/msa_cache/index.tsv`, with fresh MSA still needed for 7 chains
  (`T1239V1`, `T1239V2`, `T1228V1`, `T1228V2`, `T1212`, `T1276`, `T2276`).
  A pending single-seed run spec,
  `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_seed101`,
  explicitly allows this 97.46% cache reuse floor. Do not promote it to
  multi-seed compute until the single-seed coverage score proves the repair is
  worth the fresh-MSA cost.
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
  locally available reference alias. It now points at the size-first
  phase-alias artifact
  `strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`,
  preserves the fixed 175-target scoring set through the benchmark
  `input_manifest.tsv`, and requires complete exact-sequence MSA reuse from
  `data/msa_cache/index.tsv`. It is not queued yet; use it only if the running
  scoreable `protenix5` row is worth scaling.
- MSA cache infra now has a read-only `check-msa-cache` preflight,
  incremental materialized local A3M storage under ignored
  `data/msa_cache/store/`, `run-spec --refresh-global-msa-cache`, and
  `run-next` stale-path auditing. The scoreable v2 attack input checks at
  141/141 reusable protein chains, 0 missing sources, and 0 stale cached paths
  against `data/msa_cache/index.tsv`; future MSA-heavy shards should pass this
  check before Slurm submission.
- `2026-07-06 19:21 CDT` MSA-cache implementation status: commit `09ff0e4`
  adds incremental cache-index refresh, `run-spec --refresh-global-msa-cache`,
  path-specific `check-msa-cache` report labels, and tests proving that
  materialized cache rows survive source-run cleanup. Verified with
  `pytest tests/test_msa_cache.py` and
  `pytest tests/test_runs.py tests/test_strategies.py tests/test_benchmark.py`.
- `2026-07-06 19:38 CDT` phase-alias stoichiometry fix: generated a new
  no-over-token stack rooted at
  `strategies/yang_protein_oligo_sequence_stoich_phase_alias_v1/`. It changes
  20 targets, including `H0220/H1220/H2220` as recovered protein `A1B4`
  assemblies of total length 2515, still under Protenix's 2560-token limit.
  The final scoreable oligo-first artifact
  `strategies/scoreable_target_subset_oligo_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`
  keeps 74 jobs and preflights at 141/141 reusable protein chains, 0 missing,
  0 stale.
- Superseded stale scoreable oligo-first successor:
  `server_v2_attack_scoreable_oligo_first_msa_reuse_protenix5_seed101_105`.
  Its source input kept `H0220` as `A1B1`, so it should not be launched.
- Superseded phase-alias scoreable oligo-first successor:
  `server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105`.
  It fixed `H0220/H1220/H2220` to `A1B4`, but still started with 2515-token
  `H0220` and hit 2535-token `H0258` early.
- Pending size-first phase-alias scoreable successor:
  `server_v2_attack_scoreable_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105`.
  It keeps the same five-candidate server-attack budget and confidence-only
  selector, exact oligo jobs first, but sorts those exact oligo jobs by total
  protein tokens. This moves 2515-2535 token blockers (`H0220/H1220/H2220`,
  `H0258/H1258/H2258`) behind 44 smaller exact-oligo jobs while preserving
  run-local `A1B4` stoichiometry and 141/141 complete MSA reuse. `run-next
  --dry-run` correctly blocks it behind the running scoreable `protenix5` row.
- Pending antibody-Fv scoreable successor:
  `server_v2_attack_scoreable_antibody_fv_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105`.
  It is queued behind the size-first phase-alias row, keeps the same 74
  scoreable jobs and five-candidate budget, trims only sequence-detected
  antibody constant regions on 12 H targets, re-sorts exact oligos after
  cleanup, and preflights at 141/141 MSA reuse using the target-lab Fv MSA
  source plus the global cache. Treat it as a risky O5 branch, not as a
  replacement for the safer phase-alias scheduler.
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
  is running. The `2026-07-06 19:21 CDT` check found seed CIF counts
  `98/98/98/13/0`; the log still hits the known `n_token > 2560` classes, so
  it is incomplete and must not be scored as a five-candidate result.
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
  update. The `2026-07-06 19:03 CDT` diagnostic registered the 32 available
  seed-101 CIFs as rank-ineligible
  `server_v2_scoreable_attack_seed101_partial_diagnostic_20260707`: domain
  fixed mean is `0.099576`, and exact H-oligo QSglob is already nonzero for
  H0223 `0.591`, H0225 `0.270`, H0233 `0.221`, H0222 `0.074`, and H0227
  `0.024`. The full five-candidate attack remains incomplete and unranked, but
  the running job is now producing useful exact oligo signal.
- `2026-07-06 19:44 CDT` status check: P13 is still alive on Slurm job
  `811751`, with 32 seed-101 CIFs. The log shows it is on `H0258`
  (`N_token=2535`) as item 33/74. This is a slow large-target blocker rather
  than an MSA-cache miss; the size-first successor exists to avoid repeating
  this early-blocker schedule on the retry.
- `2026-07-06 19:54 CDT` partial diagnostic refresh: P13 now has 33 seed-101
  CIFs. The added `H0258` row is scorer-ok but `QSglob=0.000`, so it did not
  improve the fixed-set oligo mean. Domain mean remains `0.099576`; oligo mean
  remains `0.011346`; nonzero exact H-oligo targets remain `H0223`, `H0225`,
  `H0233`, `H0222`, and `H0227`.
- `2026-07-06 20:27 CDT` partial diagnostic refresh:
  `server_v2_scoreable_attack_seed101_partial_diagnostic_20260706_2027cdt`
  registers the 36 seed-101 CIF snapshot from P13 as a rank-ineligible
  diagnostic. Domain mean is unchanged at `0.099576`, but oligo fixed mean
  jumps to `0.028394` with 12 scorer-ok rows and 8 nonzero rows. New high-signal
  rows are `H1202 QSglob=0.924`, `H0272 QSglob=0.428`, and
  `H1204 QSglob=0.421`. This validates the v2 scoreable-oligo attack direction;
  keep P13 running while productive, and use P14 mainly to get the same exact
  oligo signal with less early large-target latency.
- Superseded oligo-first scoreable-subset successor:
  `server_v2_attack_scoreable_oligo_first_msa_reuse_protenix5_seed101_105`
  uses the same 74 scoreable jobs, fixed five-candidate budget, confidence-only
  selector, and 141/141 exact-sequence MSA reuse as the running scoreable
  attack, but reorders the input so the 50 exact `protein_oligo` jobs run
  first. This is a scheduling/signal-latency optimization only; it does not
  change the 175-target scoring denominator or rank rules. It is now
  superseded because the source input kept stale `H0220` `A1B1` stoichiometry.
- Superseded phase-alias oligo-first scoreable-subset successor:
  `server_v2_attack_scoreable_oligo_first_phase_alias_msa_reuse_protenix5_seed101_105`
  uses
  `strategies/scoreable_target_subset_oligo_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`,
  keeps 74 scoreable jobs, restores `H0220/H1220/H2220` to `A1B4`, and
  preflights at 141/141 MSA reuse. It is now superseded by size-first
  scheduling because it starts on 2515-token `H0220`.
- Queued size-first phase-alias scoreable-subset successor:
  `server_v2_attack_scoreable_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105`
  uses
  `strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`,
  keeps 74 scoreable jobs, restores `H0220/H1220/H2220` to `A1B4`, preflights
  at 141/141 MSA reuse, and is now the next v2 `run-next` candidate after P13
  finishes.
- Queued antibody-Fv scoreable-subset successor:
  `server_v2_attack_scoreable_antibody_fv_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105`
  uses
  `strategies/scoreable_antibody_fv_oligo_size_first_phase_alias_v1/casp16_server_protein_v2_aliasfix/inputs.json`,
  keeps 74 scoreable jobs, trims antibody constant regions on
  `H0222/H0223/H0225/H0233` phase families, preflights at 141/141 MSA reuse,
  and remains behind the size-first phase-alias row.
- Queued auto-advance wrapper: Slurm job `812202` runs
  `slurm/casp16_server_v2_aliasfix_run_next_gh200.slurm` with
  `afterany:811751`. It should call `run-next` only after the running P13
  wrapper exits, so P14 can start without manual queue babysitting. This is
  scheduling glue only; it does not change benchmark eligibility, budget, or
  scoring.
- Terminal-tag attack partial diagnostic:
  `diagnostics/score_probes/server_attack_terminal_tag_partial_latest/target_scores.csv`
  scored the still-running v1 five-seed terminal-tag attack with available
  candidates (`98/98/98/48/0` CIFs by seed at `2026-07-06 20:16 CDT`). Fixed
  domain mean is only `0.044437` with 9 ok and 7 nonzero domain targets; oligo
  remains `0.000000`. This is not a complete ranked attack row, and it argues
  against spending more compute on terminal-tag scaling before the v2
  scoreable line is resolved.
- Reference recovery probe: the RCSB exact-sequence diagnostic on 40
  `prediction_waiting_on_reference` rows found full target/entity candidates
  for `T1228V1` and `T1278` only; partial hits such as `10BR_1` for
  `T1270/T0270` are marked non-promotable. Keep this as
  `casp16_server_protein_v3_refmap` groundwork; it should not block the
  current scoreable attack line or mutate v2.
- Candidate-ref TMscore probe:
  `diagnostics/reference_gap/candidate_ref_tmscore_probe.tsv` tested existing
  predictions for those two candidate target classes against the candidate
  references. The candidates are metric-runnable, but current predictions are
  weak: best `GDT_TS_norm` is `0.012100` for `T1228V1` and `0.106100` for
  `T1278`. Do not expect reference recovery alone to create a hidden large
  score jump on these rows.
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
- `2026-07-06 18:34 CDT` scorer-alias audit: `target_scores.csv` now records
  `prediction_match_type` and `prediction_match_alias`. The eight current v2
  oligo `ok` rows above are all `sequence_lookup` matches (`T0206O -> T0206`,
  `T0234O -> T0234`, etc.), not exact `*O` prediction artifacts. Treat their
  zeros as alias/assembly diagnostics until exact oligo jobs finish; they are
  not enough evidence to launch a larger seed budget.
- `2026-07-06 18:40 CDT` nonranked seed-101 probe, refreshed after the
  exact-artifact gate:
  `diagnostics/score_probes/server_v2_scoreable_attack_seed101_probe_20260706/target_scores.csv`
  temporarily scores the current scoreable-attack seed-101 artifacts as a
  one-candidate diagnostic. It has 24/71 exact domain predictions scored, 17
  nonzero, fixed-set domain mean `0.099576`; strongest domain targets are
  `T2249V1=0.9248`, `T1299=0.9137`, `T1249V1=0.8628`, `T1234=0.8258`, and
  `T2234=0.8095`. The older fallback-only oligo positives were rejected by the
  exact gate: if a run input declares `TxxxxO`/`Hxxxx` then scorer now requires
  that exact artifact before QSglob scoring. Current oligo status is therefore
  104/104 `missing_prediction`, which is correct while Protenix has not yet
  reached the exact oligo tasks.
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
29. `2026-07-06 20:36 CDT` MSA cache audit: both active scoreable attack specs,
    `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`
    and
    `server_v2_attack_scoreable_oligo_size_first_phase_alias_msa_reuse_protenix5_seed101_105`,
    have 141/141 protein chains backed by precomputed MSA paths in their
    `inputs/inputs.msa-reuse.json` files. Do not spend more time trying to
    optimize MSA reuse for these rows; the current wall-time bottleneck is
    large oligo forward passes such as `H1220`/`H0258`, so the useful levers
    are size-first scheduling, scoreable shards, or token/assembly strategy.
30. `2026-07-06 20:42 CDT` pipe upgrade: `./casp16 merge-shards` now has an
    explicit target-shard mode via `--allow-target-shards --merged-input-json`.
    This is for the next scoreable size-sharded attack: run small/medium/large
    target subsets under the same declared budget, then merge them against the
    full strategy input so scoring and exact-target accounting remain honest.
    Default seed-shard behavior is unchanged and still requires identical input
    hashes.
31. `2026-07-06 20:50 CDT` target-sharded attack launch: added
    `./casp16 shard-inputs` and `./casp16 run-one --allow-parallel`, then split
    the 74-job scoreable size-first phase-alias input into six target-disjoint
    balanced shards under
    `strategies/target_shards_scoreable_size_balanced_v1/casp16_server_protein_v2_aliasfix/`.
    Every shard has complete exact-sequence MSA reuse from
    `data/msa_cache/index.tsv`, uses the same five-candidate
    `protenix_confidence_v1` policy, and is rank-ineligible until merged.
    Submitted GH200 jobs `812239..812244` for shard01..shard06 and cancelled
    the stale serial auto-advance job `812202`; this keeps the main path on the
    same scoreable attack budget while avoiding another monolithic H1220/H0258
    block.

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
