# CASP16 Autoresearch Notes

This is the working index for agent-driven CASP16 strategy iteration. The
benchmark is the protocol; strategy code and run directories are the only place
where methods should change.

For the short branch-selection control board, start with
`docs/WINNER_REPRODUCTION_BOARD.md`; this file remains the longer append-only
truth log.

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
- `casp16_server_protein_v3_refmap` is a versioned reference-map expansion of
  v2, not a new prediction strategy. It currently adds one accepted
  provenance-backed reference row, `T1278 -> 9hav` chain `A` with domain crop
  `34-370`, raising local reference coverage from 79 to 80 of the fixed 175
  server-protein targets. Keep v2 as the locked alias-fix baseline and use v3
  only when explicitly testing reference-map coverage recovery.
- `casp16_server_protein_v4_refmap` extends v3 with one extra
  phase-alias-inherited row, `T2278 -> 9hav`, because `T2278` is the later
  380-residue A1 Dehydrogenase target, has a sequence-identical benchmark input
  to `T1278`, and uses the same `T1278-D1` domain definition. It raises local
  reference coverage to 81/175. This is still reference-coverage discipline,
  not a prediction-strategy change.
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
- `2026-07-07` oligo reference audit update: the all-gap RCSB probe produced
  many full-construct candidates for `H0217/H1217/H2217` and
  `H0267/H1267/H2267`, but `./casp16 refmap-oligo-audit` found 0 candidate
  biological assemblies whose polymer-chain count matches the current target
  metadata. These rows remain useful reference-map candidates, not accepted
  benchmark references. Do not promote them without native assembly provenance
  plus explicit QSglob chain/interface mapping.
- `./casp16 reference-gap-report --benchmark casp16_server_protein_v4_refmap`
  writes the current score-cap and refmap-priority diagnostic to
  `diagnostics/reference_gap/casp16_server_protein_v4_refmap_reference_gap_report.md`
  and `.tsv`. Current v4 cap is still severe: domain `28/71` references
  available, oligo `53/104` references available, and 18 missing-reference
  targets have visible candidate or deferred-review rows from the latest
  all-gap review.
- Missing-reference repair is necessary for a full CASP16 server comparison,
  but it must stay versioned and non-oracular. The next accepted reference
  expansion should become a new benchmark such as `casp16_server_protein_v5_refmap`;
  do not hand-edit v2/v4 TSVs, do not fill scores from official tables, and do
  not use partial P14 `target_scores.csv` to choose which target to repair.
  Prioritize accepted-native provenance plus explicit domain crop or oligo
  biological-assembly/QSglob mapping over broader sequence-search-only probes.
- `2026-07-07` expanded RCSB exact-sequence probe: raising the all-gap search
  cap from `--max-hits 25` to `--max-hits 50` returned 304 candidate rows and
  156 deferred rows, but still only 81 full-construct exact candidates. It did
  not add any new promotable target class beyond `T1228V1`, already accepted
  `T1278/T2278`, and the unresolved H0217/H0267 oligo alias groups. Do not
  spend another loop on search-depth-only refmap probing unless the worklist or
  acceptance rule changes.
- `2026-07-07` v5 reference-recovery plan:
  `docs/REFERENCE_RECOVERY_V5_PLAN.md` splits missing-reference repair into
  strict work lanes. `T1228V1` is the only near-term unaccepted domain
  candidate class, but it still needs native provenance plus explicit
  `T1228V1-D1..D4` crop mapping. `H0217/H1217/H2217` and
  `H0267/H1267/H2267` remain oligo candidates blocked by biological assembly
  and QSglob mapping. Five rows are input/alias repair before reference work.
  The rest are manual native-search targets, grouped by phase alias. Any
  accepted expansion must become `casp16_server_protein_v5_refmap`; do not
  mutate v2/v4 in place.
- `2026-07-07 12:35 CDT` v5 reference-recovery queue:
  `diagnostics/reference_gap/casp16_server_protein_v5_refmap_recovery_queue.tsv`
  groups the 94 current v4 missing-reference rows into 42 target-family tasks.
  The first lane is `T1228V1` provenance/mapping; a new deferred-hit review
  lane makes non-promotable sequence hits such as `T0270/T1270/T2270 -> 10br`
  visible without accepting them as references. The highest-gain zero-candidate
  manual domain families are now `T0240/T1240/T2240`,
  `T0259/T1259/T2259`, `T0246/T1246/T2246`,
  `T0218/T1218/T2218`, and `T0237/T1237/T2237`. Treat the queue as
  scoring-infrastructure triage only: it must not be joined with local
  prediction `target_scores.csv` to tune target-specific prediction behavior.
- `2026-07-07 14:08 CDT` Lane E relaxed RCSB probe:
  `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_e_high_value_domain_targets.tsv`
  checked 17 high-value domain rows from the `T0240/T1240/T2240`,
  `T0259/T1259/T2259`, `T0246/T1246/T2246`,
  `T0218/T1218/T2218`, `T0237/T1237/T2237`, and `T1279/T2279`
  families at identity cutoff `0.90`, `max_hits=25`. It found 0 hits and
  wrote an empty candidate TSV apart from the header. These families remain
  manual native/provenance work; do not repeat search-depth-only RCSB probing
  or promote template-like structures without native/reference evidence.
- `2026-07-07` latest all-gap chain audit:
  `diagnostics/reference_gap/casp16_server_protein_latest_all_chain_audit.tsv`
  audits 81 candidate structures and 1021 chain rows. It confirms that
  `T1228V1` has domain-covering chains in `9DXK` and `9Y66`, while
  `9DXH/9DXJ` miss two N-terminal domain positions. This is not an accepted
  refmap row: `T1228V1` still needs D6a input-kind repair plus native-state
  provenance before a future v5 benchmark can promote it.
- `2026-07-07` post-P14 score readout: the merged five-candidate scoreable
  attack
  `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105`
  completed 370/370 candidates and scored, but still exposed 5 available-
  reference targets as `missing_prediction` (`T1212`, `T1239V2`, `T1249V2O`,
  `T1269V1O`, `T2249V2O`). Fixed-set means are still far below server leaders:
  domain `0.102777` and oligo `0.116923`. The P16 consensus replay did not
  improve the row (`0.102218` domain, `0.115250` oligo), so the next branch is
  pipeline/input coverage, not selector tuning or a 25-seed scale-up.
- `2026-07-07` P17 input-repair branch:
  `scoreable_target_subset_input_repair_v1` adds exactly those 5 scoreable
  targets without mutating the locked benchmark. It recovers explicit
  `proteinChain` records when sequence-kind is ambiguous, falls back
  target-agnostically through `O`, `Vn -> V1/base`, and phase aliases, and
  records every fallback in
  `strategies/scoreable_target_subset_input_repair_v1/casp16_server_protein_v2_aliasfix/manifest.tsv`.
  The repaired input is 79/79 covered, `skipped_targets=0`, and exact-sequence
  MSA reuse is complete (`146/146` protein chains, 0 missing, 0 stale).
  The initial six full P17 GH200 shards
  `server_v2_attack_scoreable_input_repair_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105`
  were submitted as Slurm jobs `812765..812770`, then cancelled after early
  wall time repeated old large H-oligo targets already covered by P14. The
  accepted closeout is the P14 plus added-only overlay
  `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105`,
  which is complete and scored.
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
  Those 7 chains are only 4 unique protein sequences, so the rank-ineligible
  warmup spec `server_v2_domain_sequence_recovery_msa_warmup_seed101` now
  isolates `T1239V1`, `T1228V1`, `T1276`, and `T1212` for one-time MSA
  materialization before a full D6a launch.
  The warmup has since materialized the missing sequences, and
  `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101`
  has complete MSA reuse. It is explicitly `deferred:await_p14_score`, so it
  cannot be selected by `run-next` before the P14 target-sharded attack is
  merged/scored and the decision matrix is applied.
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
- The repaired-input scoreable 25-candidate successor is
  `attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair.json`.
  P17 scored as a `candidate_limited_signal`, so the 24 seed106-125 target-seed
  jobs are now submitted as Slurm jobs `812935..812958`; seeds101-105 come from
  the P14 plus added-only P17 overlay.
- A v4 refmap scoreable successor is prepared at
  `strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v4_refmap/`.
  It uses the same no-over-token phase-alias/low-complexity/large-fallback
  recipe, but the accepted `T1278/T2278 -> 9hav` refmap rows raise the
  scoreable subset from 74 to 76 jobs. Its MSA preflight is clean at 143/143
  reusable protein chains against `data/msa_cache/index.tsv`. Treat it as the
  next P15-style input after the running v2 P14 row is scored; do not mix its
  result into v2 leaderboards without naming the v4 benchmark.
- P15 v4 scoreable target shards are prepared but deliberately deferred in
  `attack_budgets/casp16_server_attack_protenix5_v4_scoreable_target_shards.tsv`.
  They split the 76-job v4 scoreable subset into 6 target-balanced GH200 shards
  using seeds `101..105`, `sample=1`, `candidate_count=5`, and
  `protenix_confidence_v1`. All six run specs preflight clean with complete
  MSA reuse. They must remain `deferred:await_p14_score` until the live v2 P14
  row has been merged/scored.
- `2026-07-07 01:57 CDT` P14 gate: the live v2 target-sharded scoreable
  Protenix5 attack remains healthy but not merge-ready. `check-shards` sees
  189/370 expected candidate CIFs, all six Slurm jobs `812239..812244` are
  still running, and shard plus Slurm log error scans found no
  traceback/OOM/CUDA/killed signatures. Do not launch P15/P25/O5 before P14 is
  merged/scored or explicitly abandoned.
- `2026-07-07 02:05 CDT` P14 recheck: readiness is still `189/370`, but stderr
  tails show active seed103 forward passes on large 2285-2535 token complexes
  (`H0258/H1258/H2258` and `H0272/H1272/H2272` class). Treat this as slow
  healthy inference, not a stalled job.
- `2026-07-07 03:15 CDT` P14 recheck: all six Slurm jobs `812239..812244`
  remain running, and replay-safe `finish-shards` now observes `239/370`
  expected candidate CIFs with `131` still missing. The row is still
  `ready=false`, but progress is monotonic and there are no shard-closeout
  actions to take yet.
- `2026-07-07 03:21 CDT` P14 health check: all six shard jobs are still
  running and replay-safe `finish-shards` observes `255/370` candidates with
  `115` missing. Error scan across shard logs found no traceback/OOM/CUDA
  failure signatures. The active stderr tails show seed104 forward passes on
  the expected 1304-2535 token protein-complex targets, so this is still slow
  healthy inference rather than a stalled run.
- `2026-07-07 04:04 CDT` P14 health check: all six shard jobs `812239..812244`
  remain running, and replay-safe `finish-shards` observes `277/370`
  candidates with `93` missing, `5/74` target tasks complete, and
  `ready=false`. Error scans remain clean. A short monitor window confirmed
  monotonic output growth from the large-target seed104 forwards; one measured
  bottleneck was `H2258 [seed:104]`, which needed `2660.01s` of model forward
  time. The active bottleneck is Protenix forward on 1304-2535 token targets,
  not repeated MSA search. Keep P15/P18/P25/P27a/O5/D6a gated until P14 is
  merged/scored or explicitly abandoned.
- `2026-07-07 04:30 CDT` P14 health check: all six shard jobs remain running,
  and replay-safe `finish-shards` observes `299/370` candidates with `71`
  missing, `17/74` target tasks complete, `0/6` shards complete, and
  `ready=false`. The latest error scan again found no
  traceback/OOM/CUDA/killed signatures. Progress is still monotonic, so do not
  launch P15/P18/P25/P27a/O5/D6a or score partial shard outputs.
- `2026-07-07 04:34 CDT` post-P14 readiness refresh: all deferred next-branch
  preflights remain launch-clean without opening a GPU branch. P15 v4 target
  shards are `6/6 ok`, P18/P25 scoreable 25-candidate target+seed grid is
  `30/30 ok`, P27a default-params model/config shards are `6/6 ok`, D6a domain
  sequence recovery is `1/1 ok`, and O5 antibody-Fv target shards are `6/6 ok`.
  Every refreshed preflight reports complete MSA reuse and 0 stale paths. The
  exact branch is still gated on the P14/P16 score readout in
  `docs/SERVER_SCORE_TARGETS.md`.
- `2026-07-07 04:51 CDT` P14 health check: all six shard jobs remain running,
  and replay-safe `finish-shards` observes `311/370` candidates with `59`
  missing, `21/74` target tasks complete, `0/6` shards complete, and
  `ready=false`. The latest error scan again found no
  traceback/OOM/CUDA/killed signatures. Shards 5 and 6 advanced since the
  previous check; the remaining wait is still Protenix forward on large
  targets, not repeated MSA search or a cache failure. Keep P15/P18/P25/P27a/O5
  and D6a gated until P14/P16 closeout finishes.
- `2026-07-07 05:18 CDT` P14 health check: all six shard jobs
  `812239..812244` are still RUNNING at about 6h58m. Replay-safe
  `finish-shards` observes `337/370` candidates, `33` missing candidates,
  `41/74` complete target tasks, `0/6` complete shards, and `ready=false`.
  Error scans remain clean. This continues to look like slow Protenix forward
  on the last large targets, not repeated MSA work. Do not launch the deferred
  P15/P18/P25/P27a/O5/D6a branches or inspect partial target scores.
- `2026-07-07 05:27 CDT` P14 health check: shard03 completed and appended
  `ok/run_one_finished` to `runs/status.tsv`, while the other five GH200 shard
  jobs remain running. Replay-safe `finish-shards` observes `342/370`
  candidates, `28` missing candidates, `46/74` complete target tasks, `1/6`
  complete shards, and `ready=false`. This is the first complete P14 execution
  shard, but the merged P14/P16 readout is still gated until all shards reach
  the declared five candidates for every task.
- Post-P14 winner-recipe branch `casp16_server_attack_msa_model_diversity_v1`
  is now documented as a design gate in `docs/CASP16_WINNER_RECIPES.md`. It
  captures the MULTICOM4/QA4-style lesson: if P14 is complete and valid but
  weak, build target-agnostic MSA/model-diversity plus QA with real MSA/template
  settings instead of disabling MSA or blindly scaling one Protenix input. Its
  non-executable budget design is recorded in
  `attack_budgets/casp16_server_attack_msa_model_diversity_v1.json`.
- First concrete post-P14 model/config diversity branch P27a is prepared as
  `attack_budgets/casp16_server_attack_protenix5_defaultparams_model_variant.json`
  plus six deferred target shards
  `server_v2_attack_scoreable_defaultparams_shard01..06_msa_reuse_protenix5_seed101_105`.
  It reuses the exact P14 benchmark, scoreable target shards, seeds
  `101..105`, MSA/template settings, and selector, but flips only
  `use_default_params:false -> true`. Batch preflight is `6/6 ok` with
  complete MSA reuse and 0 stale paths. Do not submit it before P14 is
  merged/scored and the post-P14 decision matrix selects model/config
  diversity over seed scaling, reference recovery, or input repair.
- The repaired-input successor P27b is now prepared as
  `attack_budgets/casp16_server_attack_protenix5_input_repair_defaultparams_model_variant.json`
  plus six deferred target shards
  `server_v2_attack_scoreable_input_repair_defaultparams_shard01..06_msa_reuse_protenix5_seed101_105`.
  It retargets the same default-params model/config probe onto the P17/P25
  79-job repaired scoreable input, keeps seeds `101..105`, real MSA/template
  settings, and `protenix_confidence_v1`, and flips only
  `use_default_params:false -> true`. Batch preflight is `6/6 ok` with
  `146/146` reusable protein chains and 0 stale paths. It is explicitly
  `deferred:await_p25_score`; do not submit it while P25 is running or unscored.
- The repaired-input O5b antibody/Fv successor is now prepared as
  `attack_budgets/casp16_server_attack_protenix5_input_repair_antibody_fv.json`
  plus six deferred target shards
  `server_v2_attack_scoreable_input_repair_antibody_fv_shard01..06_msa_reuse_protenix5_seed101_105`.
  It retargets the sequence-only antibody constant-region cleanup onto the
  P17/P25 79-job repaired scoreable input, changing 24 protein sequences across
  12 antibody-like targets while preserving all 79 job names. Batch preflight is
  `6/6 ok` with `146/146` reusable protein chains and 0 stale paths. It is
  explicitly `deferred:await_p25_score`; launch only if the complete P25 readout
  shows antibody/Fv oligos remain the next recoverable weakness.
- `diversity_confidence_consensus_v1` is now wired as a prediction-only
  selector for future diversity budgets. It extends `protenix_confidence_v1`
  with optional consensus/cluster-support fields from run-local confidence or
  QA JSON and still fails closed without confidence data. `./casp16
  selection-qa` can now generate those sidecar QA fields by running
  prediction-vs-prediction TMscore/USalign only, with no reference access.
- `./casp16 finish-shards` can now register a predeclared selector replay with
  `--replay-run-id` after shard merge but before scoring. This is the preferred
  closeout path for P14/P16: it writes prediction-only `selection-qa` sidecars,
  registers the `diversity_confidence_consensus_v1` replay row, and only then
  runs `score` and `leaderboard`.
- `scripts/finish_p25_scoreable_input_repair.sh` now uses the same replay-safe
  closeout path for P25. After the 25-candidate repaired-input pool is complete
  it will register
  `server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125_consensus_replay`
  from the merged predictions, write prediction-only QA sidecars, and score the
  confidence selector plus consensus selector together before any new GPU branch
  is selected.
- MSA cache infra now has a read-only `check-msa-cache` preflight,
  incremental materialized local A3M storage under ignored
  `data/msa_cache/store/`, `run-spec --refresh-global-msa-cache`, and
  `run-next` stale-path auditing. It also has `preflight-runs` for batch
  auditing target-shard or seed-shard manifests before submission. The
  scoreable v2 attack input checks at 141/141 reusable protein chains, 0
  missing sources, and 0 stale cached paths against `data/msa_cache/index.tsv`;
  future MSA-heavy shards should pass this check before Slurm submission.
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
- `2026-07-06 23:21 CDT` v3 refmap materialization: accepted the first audited
  reference-map row for `T1278`, using `9hav` chain `A` and the official
  domain crop `34-370`. The generated benchmark
  `benchmarks/casp16_server_protein_v3_refmap/` now has 80 available local
  references and 95 remaining reference gaps across the same fixed 175
  server-protein targets. This improves scoreability for future diagnostics but
  does not change the active v2 scoreable attack or any prediction recipe.
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
- `./casp16 refmap-probe`: targeted RCSB exact-sequence diagnostic command that
  writes `diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_*.tsv`
  without accepting references or touching benchmark/leaderboard artifacts
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
28. Use `casp16_server_attack_protenix25_scoreable_nofail` as the prepared
    winner-scale successor if the running scoreable `protenix5` row is
    positive. It now reuses the P14 seed101-105 target shards and has 24
    deferred seed106-125 specs ready. Keep the older 165-job `protenix25_nofail`
    as a full-input ablation until references are recovered.
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
32. `2026-07-06 21:02 CDT` GPU reallocation: cancelled monolithic P13 Slurm job
    `811751` after it stayed at 36/74 seed101 CIFs on `H1220`, and cancelled
    old v1 terminal-tag attack job `810719` after a weak partial diagnostic
    (`domain=0.044437`, `oligo=0.000000`, latest seed counts
    `98/98/98/81/0`). Both partial artifacts remain useful diagnostics, but
    neither should occupy GH200 time ahead of the six v2 target-sharded
    scoreable jobs `812239..812244`.
33. `2026-07-06 21:12 CDT` shard readiness automation: added
    `./casp16 check-shards` for target-sharded attacks. It verifies run-spec
    compatibility, counts observed prediction candidates per Protenix task, can
    write a readiness TSV, and emits the exact target-shard merge command only
    when every shard has the declared candidate count. Current scoreable
    target-shard status is compatible but not ready: `0/370` candidates across
    74 tasks, recorded in
    `diagnostics/score_probes/target_shards_scoreable_size_balanced_readiness.tsv`.
34. `2026-07-06 21:13 CDT` prepared the O5 antibody-Fv branch as target
    shards without submitting more GPU work. The source strategy
    `scoreable_antibody_fv_oligo_size_first_phase_alias_v1` is now split under
    `strategies/target_shards_scoreable_antibody_fv_size_balanced_v1/casp16_server_protein_v2_aliasfix/`.
    Six run specs
    `server_v2_attack_scoreable_antibody_fv_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105`
    declare the same five-candidate `protenix_confidence_v1` budget, are
    `rank_eligible=false`, have complete MSA reuse (`141/141`, 0 missing), and
    are append-only marked `deferred:base_target_shards_first`. This keeps the
    O5 winner-recipe branch executable while preserving queue priority for the
    base target-sharded scoreable attack.
35. `2026-07-06 21:47 CDT` prepared the P18 scoreable `protenix25` attack as
    an executable target-shard x seed-block grid without submitting more GPU
    work. The manifest
    `attack_budgets/casp16_server_attack_protenix25_scoreable_target_seed_shards.tsv`
    has 30 execution rows: six existing P14 seed101-105 target shards to reuse
    and 24 new deferred seed106-125 run specs. Every new spec has complete MSA
    reuse (`coverage_fraction=1.0`, `missing_source=0`), is
    `rank_eligible=false`, and is append-only marked
    `deferred:await_protenix5_score`. The readiness artifact
    `diagnostics/score_probes/protenix25_scoreable_target_seed_readiness.tsv`
    verifies compatibility and records the full merged budget gate:
    `--candidate-count 5 --merged-candidate-count 25`.
36. `2026-07-06 22:00 CDT` added `./casp16 preflight-runs` and audited the
    same P18 target+seed shard manifest before any seed106-125 submission. The
    launch preflight artifact
    `diagnostics/msa_cache/protenix25_scoreable_target_seed_run_preflight.tsv`
    reports `30/30 ok`, complete MSA coverage for every shard, and 0 stale
    covered paths. The current blocker for P18 remains the policy gate
    `await_protenix5_score`, not MSA readiness.
37. `2026-07-06 21:56 CDT` prepared the D6a MSA warmup
    `server_v2_domain_sequence_recovery_msa_warmup_seed101` as a
    rank-ineligible diagnostic run. It contains only four representative
    recovered protein-domain inputs (`T1239V1`, `T1228V1`, `T1276`, `T1212`)
    that cover the seven fresh-MSA chains in the full D6a artifact by exact
    sequence. This is a cache/materialization step for input repair, not a
    leaderboard row, and `run-next --dry-run` still selects the P14 scoreable
    shard first.
38. `2026-07-06 22:10 CDT` launched the D6a MSA warmup in a detached
    `screen` session named `casp16_d6a_warmup` on the current idle GH200
    allocation (`c610-032`). This avoided adding another queued GH job while
    the six P14 scoreable target shards remain pending. The run uses full
    MSA/template/default Protenix settings, is still `rank_eligible=false`, and
    should only be used to refresh `data/msa_cache/index.tsv` after it
    completes.
39. `2026-07-06 22:15 CDT` the D6a warmup completed successfully: 4/4 CIFs,
    full MSA/template search completed, and `inputs-update-msa.json` was
    written. `build-msa-cache --materialize-cache --incremental` added the 4
    missing exact-sequence records, bringing the materialized cache index to
    109 sequence records. The recreated
    `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101`
    run spec now preflights at complete MSA reuse (`276/276` protein chains,
    0 missing, 0 stale), so D6a is no longer blocked on fresh MSA.
40. `2026-07-06 22:18 CDT` the six P14 scoreable target shards
    `812239..812244` started on GH200 nodes. Five shards wrote their
    `running` status concurrently; shard06's status append was recovered from
    Slurm/log evidence after exposing a status-file append race. `append_status`
    now uses a file lock so parallel target-shard starts and finishes do not
    drop lifecycle rows.
41. `2026-07-06 22:37 CDT` added a guarded reference-map overlay path for the
    next server benchmark version. `./casp16 server-benchmark --reference-map`
    now accepts audited `status=accepted` target-to-PDB rows only when the
    caller generates a new benchmark name such as
    `casp16_server_protein_v3_refmap`; it refuses to overwrite locked v1/v2.
    Accepted rows must carry native provenance, construct coverage, chain
    mapping, and scoring mapping. This is the correct route to shrink the
    96-target v2 `missing_reference` cap without using official scores or
    hand-editing benchmark TSVs.
42. `2026-07-06 22:43 CDT` added `./casp16 refmap-review` and generated
    `diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv`.
    The artifact converts the RCSB exact-sequence probe into the guarded
    reference-map schema: 8 full-construct exact rows are still only
    `candidate`, while 14 partial/local hits are `rejected`. This keeps
    reference recovery moving without falsely accepting native structures; the
    next real v3 score unlock is to fill provenance plus mapping for one or
    more candidate rows, then generate `casp16_server_protein_v3_refmap`.
43. `2026-07-06 22:48 CDT` added `./casp16 refmap-materialize` and generated
    `diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv`.
    It downloaded the 8 candidate mmCIF files from the review artifact, wrote
    sha256/byte-size manifest rows, and keeps the 74 MB payload cache ignored
    under `diagnostics/reference_gap/refmap_candidate_mmcif/`. This prepares
    offline native-provenance and chain/domain mapping review without changing
    the locked v2 benchmark or accepting any reference automatically.
44. `2026-07-06 22:52 CDT` added `./casp16 refmap-audit` and generated
    `diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_audit.md`.
    It groups the 22 review rows by target, attaches materialized-structure
    hashes, and assigns next actions. `T1278` was the nearest v3 refmap unlock
    because it is single-domain (`T1278-D1`, residues `34-370`) with four
    full-construct candidates; `T1228V1` remains a harder four-domain crop
    mapping problem. At this point no row had been promoted to `accepted`.
45. `2026-07-06 23:03 CDT` added `./casp16 refmap-chain-audit` and generated
    `diagnostics/reference_gap/casp16_server_protein_v3_refmap_chain_audit.tsv`.
    The pure-Python mmCIF atom-site audit records chain/auth/entity IDs,
    observed `label_seq_id` ranges, and domain-range coverage for materialized
    candidate references. `T1278-D1 34-370` now has concrete crop evidence:
    `9HAV` chain A covers the domain fully, while `9HAW`, `9HAX`, and `9HAY`
    have many fully covering chains. This created the chain/crop evidence used
    by the later accepted `T1278` v3 overlay and `T2278` v4 phase-alias overlay.
46. `2026-07-06 23:12 CDT` added scorer-side server-domain cropping for future
    accepted refmap benchmarks. `score_benchmark_runs` now reads accepted
    `reference_map.tsv` rows, parses `residue_ranges=...`, optionally filters
    the reference by `reference_chain=...`, writes temporary cropped mmCIF
    inputs, and runs GDT_TS/TMscore on the cropped structures. This removed the
    scorer-side blocker for accepted refmap overlays.
47. `2026-07-06 23:21 CDT` generated
    `casp16_server_protein_v3_refmap` from
    `diagnostics/reference_gap/casp16_server_protein_v3_refmap_accepted_reference_map.tsv`.
    The first accepted row is `T1278 -> 9hav`, chain `A`, crop `34-370`; local
    reference coverage becomes 80/175 with 95 gaps remaining.
48. `2026-07-06 23:27 CDT` generated
    `casp16_server_protein_v4_refmap` from
    `diagnostics/reference_gap/casp16_server_protein_v4_refmap_accepted_reference_map.tsv`.
    It adds the phase-alias row `T2278 -> 9hav` by target metadata plus exact
    benchmark-input sequence identity to `T1278`, raising local reference
    coverage to 81/175 with 94 gaps remaining. This is measurement coverage
    only; it does not change the active v2 attack row.
49. `2026-07-06 23:30 CDT` prepared the v4 scoreable-subset successor:
    `strategies/scoreable_target_subset_oligo_size_first_phase_alias_v1/casp16_server_protein_v4_refmap/inputs.json`.
    It keeps 76/165 jobs, adds `T1278` and `T2278` relative to the v2
    scoreable subset, keeps exact oligo jobs size-first, and checks at 143/143
    MSA cache coverage with no stale rows. This is queued-for-decision
    preparation only; the live P14 shards remain v2 and should finish before
    new GPU submission.
50. `2026-07-06 23:41 CDT` prepared P15 v4 target-shard run specs:
    `server_v4_attack_scoreable_size_balanced_shard01..06_msa_reuse_protenix5_seed101_105`.
    The shard split is stored under
    `strategies/target_shards_scoreable_size_balanced_v1/casp16_server_protein_v4_refmap/`;
    the launch manifest is
    `attack_budgets/casp16_server_attack_protenix5_v4_scoreable_target_shards.tsv`.
    `./casp16 preflight-runs` reports 6/6 ok, with per-shard MSA coverage
    `1.0` and zero stale rows. These specs are explicitly marked
    `deferred:await_p14_score` to prevent accidental `run-next` launch before
    P14 has a real score.
51. `2026-07-06 23:49 CDT` P14 readiness check: the live v2 scoreable
    target-sharded attack is still incomplete. `check-shards` sees 63/370
    expected candidate CIFs, 307 missing candidates, 0/6 complete shards, and
    74 incomplete target tasks. The jobs are still running on six GH200 nodes,
    so the correct move is to wait for completion rather than score a partial
    row. Partial artifacts may be inspected only as diagnostics, never as a
    ranked five-candidate result.
52. `2026-07-06 23:49 CDT` launch discipline update: `missing_reference`
    recovery is useful for scoreability, but it is a benchmark-version task,
    not a prediction trick. Continue accepting reference rows only through the
    audited `reference_map.tsv` overlay path with native provenance plus
    chain/domain or assembly mapping. While P14 is running, the highest-value
    ready work is to keep MSA reuse complete for deferred P15/P25 shards and to
    prepare target-agnostic input-repair branches; do not open a new GPU run
    merely because a no-reference target looks tempting.
53. `2026-07-07 00:13 CDT` added `./casp16 refmap-probe`, a guarded RCSB
    exact-sequence diagnostic for missing-reference worklists. It queries RCSB
    with `identity_cutoff=1.0`, writes target and candidate TSVs, treats
    protein-like CASP records safely even when the original parser labeled them
    `dnaSequence`, and skips true nucleic-acid sequences. It only creates
    candidate diagnostics; promotion still requires the existing
    `refmap-review -> refmap-materialize -> refmap-chain-audit -> accepted
    overlay -> new benchmark version` path.
54. `2026-07-07 00:13 CDT` live `refmap-probe` on the 40
    `prediction_waiting_on_reference` rows wrote
    `diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_prediction_waiting.tsv`
    and
    `diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_candidates.tsv`.
    It found hits for 6 targets and 37 candidate rows, but still only 8
    full-construct exact entity candidates: the same `T1228V1` and `T1278`
    classes as before. The extra new `T1278` hits are alignment-unverified
    local/partial sequence hits, not immediate refmap promotions.
55. `2026-07-07 01:57 CDT` P14 readiness check: all six shard jobs are still
    RUNNING on GH200 nodes. `check-shards` sees 189/370 candidates, 181 missing
    candidates, 0/6 complete shards, and 74 incomplete target tasks. Error
    scans across shard and Slurm logs remain clean. Keep waiting for full
    readiness before merge/score; do not launch P15/P25/O5 while P14 is still
    unscored.
56. `2026-07-07 01:57 CDT` post-P14 launch hygiene was refreshed without
    opening any GPU branch: P15 v4 target shards preflight `6/6 ok`, P18/P25
    scoreable 25-seed target+seed grid preflights `30/30 ok`, and the D6a
    domain-sequence-recovery ablation preflights `1/1 ok` with 276/276 MSA
    chains reusable and 0 stale paths. The refreshed D6a report is
    `diagnostics/msa_cache/domain_sequence_recovery_after_warmup_preflight.tsv`.
57. `2026-07-07 00:23 CDT` live `refmap-probe` was expanded from the 40
    `prediction_waiting_on_reference` rows to all 96 v2 missing-reference rows.
    It wrote
    `diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_all_missing_references.tsv`
    and
    `diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_all_candidates.tsv`.
    The all-gap scan found 20 targets with hits, 204 candidate rows, and 81
    full-construct exact candidate rows. Newly useful exact candidates are
    mostly oligo reference-registry gaps: `H0217/H1217/H2217` and
    `H0267/H1267/H2267`; these need biological assembly, chain stoichiometry,
    and QSglob interface mapping before any benchmark version can accept them.
58. `2026-07-07 00:23 CDT` generated
    `diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv`
    from the all-gap candidate TSV. It now keeps 81 `candidate`, 94 `deferred`,
    and 29 `rejected` rows. `refmap-review` was also made phase-alias aware for
    domain definitions, so `T2278` review rows inherit the audited `T1278-D1`
    crop mapping instead of falling back to `protein_domain_requires_domain_definition`.
59. `2026-07-07 02:28 CDT` reference-gap decision checkpoint:
    `missing_reference` must be fixed before claiming full CASP16 server-track
    local evaluation, because `casp16_server_protein_v4_refmap` still has only
    28/71 domain references and 53/104 oligo references. With missing targets
    scored as zero, the local score caps are `0.394366` domain and `0.509615`
    oligo, below the server winners `110s=0.923321` and `456s=0.582615`.
    The fix remains benchmark-versioned reference registry work, not a
    prediction strategy knob: accepted rows need native provenance plus
    chain/domain crop mapping or biological-assembly/QSglob mapping, followed
    by a new `server-benchmark --reference-map` version.
60. `2026-07-07 02:28 CDT` P14 live status: Slurm jobs `812239..812244` are
    still RUNNING on six GH200 nodes at roughly 4h09m. `check-shards` sees
    191/370 candidates, 179 missing candidates, 0/6 complete shards, and 74
    incomplete target tasks. Error scans across shard and Slurm logs remain
    clean. Continue waiting for readiness before merge/score.
61. `2026-07-07 02:28 CDT` tightened the future diversity attack workflow:
    `./casp16 selection-qa --run-id <run_id>` can infer prediction output,
    target names, and default diagnostic CSV path from the run spec/input JSON,
    so a full multi-target diversity run can generate prediction-only consensus
    sidecars without manually enumerating targets. The MSA/model-diversity
    budget now records this run-id based command.
62. `2026-07-07 02:31 CDT` P14/P-next readiness checkpoint: P14 remains live
    and not merge-ready at 194/370 observed candidates, 176 missing candidates,
    0/6 complete shards, and 74 incomplete target tasks. All six jobs
    `812239..812244` are still RUNNING at about 4h12m on GH200 nodes, with no
    error-scan hits. The next wave is mechanically ready but still gated on
    P14 scoring: P18/P25 target+seed shards preflight `30/30 ok`, P15 v4
    target shards preflight `6/6 ok`, and D6a domain-sequence recovery
    preflight `1/1 ok`, all with complete MSA reuse and 0 stale paths. Do not
    launch them until P14 is merged/scored or explicitly abandoned.
63. `2026-07-07 02:37 CDT` added `./casp16 finish-shards`, a safe closeout
    command for target/seed shard attacks. It first runs the same readiness
    checks as `check-shards`; when not ready it returns
    `finish_status=not_ready` without merging or scoring, and when ready it
    performs `merge_prediction_shards`, full benchmark scoring refresh, and
    leaderboard refresh. A live P14 dry-run with this command reports 203/370
    candidates, 167 missing, 0/6 complete shards, and `ready=false`, so the
    correct action remains to wait rather than score partial output.
64. `2026-07-07 02:44 CDT` predeclared P16 consensus-selector replay before
    seeing P14 scores:
    `attack_budgets/casp16_server_attack_protenix5_consensus_selector_replay.json`.
    It uses the exact same completed P14 five-candidate prediction pool, no
    new GPU work, and a separate registered run id with
    `diversity_confidence_consensus_v1` after `selection-qa`. This tests the
    CASP16 winner clue that QA/model selection matters, while forbidding
    references, official score tables, prior `target_scores.csv`, leaderboard
    rows, or manual per-target intervention. It must be registered and
    sidecar-QA generated after P14 merge but before inspecting P14 target
    scores, then scored as a separate `server_attack` row.
65. `2026-07-07 02:46 CDT` P14 live closeout check: `finish-shards` still
    returns `finish_status=not_ready`, with 212/370 observed candidates, 158
    missing candidates, 0/6 complete shards, and all six jobs `812239..812244`
    still RUNNING at about 4h28m. Error scans across shard and Slurm logs are
    clean. Continue waiting for full readiness; do not score partial output.
66. `2026-07-07 03:00 CDT` added replay-safe shard closeout. `finish-shards`
    now accepts `--replay-run-id`, registers that row against the merged P14
    prediction directory, generates prediction-only `selection-qa` sidecars,
    and only then runs benchmark `score`/`leaderboard`. Targeted tests plus
    `tests/test_runs.py tests/test_scoring.py` pass in the protein env. A live
    P14 replay-safe closeout check still reports `finish_status=not_ready`,
    now with 225/370 observed candidates and 145 missing candidates; it left
    `merge`, `replay`, `score`, and `leaderboard` empty and did not create the
    P16 replay run spec. The action remains to wait for complete shards before
    using the same replay-safe closeout command.
67. `2026-07-07 04:04 CDT` P14 live status: six Slurm jobs `812239..812244`
    are still RUNNING at about 5h46m. The safe closeout path reports
    `finish_status=not_ready`, now with 277/370 observed candidates, 93
    missing candidates, 0/6 complete shards, and 5/74 target tasks complete.
    No traceback/OOM/CUDA/killed signatures were found. The useful lesson for
    the next agent is that MSA reuse is working; current wall time is dominated
    by Protenix forward on large scoreable targets. Continue waiting for full
    readiness instead of opening another GPU branch from a partial snapshot.
68. `2026-07-07 07:28 CDT` post-P17 scale-up preparation: P17 input-repair
    shards `812765..812770` are still RUNNING, clean of traceback/OOM/killed
    signatures, and the refreshed dry-run closeout reports `38/395` observed
    candidates, `357` missing candidates, and `0/6` complete shards. While
    waiting, the old pre-P17 74-target `protenix25_scoreable_nofail` plan was
    superseded for launches by
    `attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair.json`.
    The repaired 25-candidate plan uses the P17 79-target input, reuses the
    six running seed101-105 target shards, and prepares 24 deferred
    seed106-125 run specs. `preflight-runs` is `30/30 ok` with complete MSA
    reuse and 0 stale covered paths; readiness is correctly `ready=false`
    until P17 finishes and the deferred seed blocks are explicitly launched.
    Do not submit those seed106-125 jobs unless P17 scores as a broad,
    candidate-limited signal.
69. `2026-07-07 07:43 CDT` P17 pivot: the full repaired 79-target rerun was
    cancelled after about 33 minutes, not hours, because the early wall time
    was being spent on old large H-oligo targets that already completed in the
    P14 74-target run. The replacement path is an overlay, not another full
    rerun: reuse
    `server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105`
    for the 74 unchanged scoreable targets and run only the 5 targets added by
    scoreable input repair. The added-only artifact is
    `strategies/scoreable_target_subset_input_repair_added_only_v1/casp16_server_protein_v2_aliasfix/`
    with 5 jobs, 100% exact-sequence MSA cache coverage, and Slurm job
    `812783` (`p17_added_only`) running on one GH200 node. Overlay readiness is
    expected to remain `ready=false` until exactly
    `T1212/T1239V2/T1249V2O/T1269V1O/T2249V2O` each have 5 candidates.
70. `2026-07-07 07:43 CDT` infrastructure hygiene for the overlay path:
    `check-shards` now caches each shard output directory's CIF/PDB file list
    once before per-target matching, which makes readiness checks fast on the
    P14 merged symlink tree. Validation passed with `py_compile` on
    `src/casp16_leaderboard/sharding.py` and the targeted tests
    `test_check_prediction_shards_reports_missing_and_merge_command`,
    `test_check_prediction_shards_validates_merged_candidate_count`, and
    `test_finish_shards_cli_dry_run_checks_without_merging`. The repaired
    25-candidate budget
    `attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair.json`
    is now explicitly gated on the P14 plus added-only overlay score; do not
    launch its seed106-125 grid by replaying the cancelled full P17 shard plan.
71. `2026-07-07 09:37 CDT` P17 overlay closeout finished. The merged
    `server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105`
    run is complete for 79 scoreable jobs and 395 prediction CIFs, with no
    partial candidates and no metric-unavailable rows. It improves over P14:
    protein domain mean `0.107690` vs `0.102777`, and protein oligo mean
    `0.118933` vs `0.116923`. The consensus replay is lower
    (`0.107230` domain, `0.117260` oligo), so keep `protenix_confidence_v1` as
    the current selector for this branch. Added target contributions are mixed:
    `T1239V2=0.348600`, `T1249V2O=0.104000`, `T2249V2O=0.105000`, while
    `T1212` and `T1269V1O` score zero. The post-P17 readout is
    `candidate_limited_signal` and recommends launching the repaired
    25-candidate scoreable grid, while the 96 no-reference targets still cap
    official-server comparability.
72. `2026-07-07 09:55 CDT` P25 launch: the repaired-input 25-candidate
    scoreable grid was submitted after `preflight-runs` reported `24/24 ok`
    for the seed106-125 target-seed shards, with complete exact-sequence MSA
    reuse and 0 stale covered paths. Slurm jobs `812935..812958` now cover
    target shards `01..06` across seed blocks `106_110`, `111_115`,
    `116_120`, and `121_125`. Seeds `101..105` are not rerun; they come from
    the P14 plus added-only P17 overlay. The full 25-candidate row remains
    unscoreable/rank-ineligible until the 24 submitted jobs finish, all
    target-seed shards are merged with the overlay, and the leaderboard is
    regenerated.
73. `2026-07-07 10:08 CDT` P25 live readiness check: 19 P25 jobs were running
    and 5 were pending behind `QOSMaxJobsPerUserLimit`. Early outputs show
    `521` observed candidates total, including the completed P17 overlay,
    with `1529` shard-level candidates still missing; full 25-candidate
    readiness remains `ready=false`. A merge blocker was fixed before it could
    bite later: the P17 overlay run spec had inherited the benchmark
    `input_manifest.tsv` hash, while the P25 shards correctly use the repaired
    strategy manifest. Updating the overlay run spec to the repaired manifest
    makes the next `check-shards` report `compatible=true`.
74. `2026-07-07 10:14 CDT` P25 follow-up: `check-shards` remains
    `ready=false` and `compatible=true`, now with `574` observed candidates,
    `1476` shard-level candidates missing, and `1401` full 25-candidate slots
    still missing across the fixed 79 scoreable tasks. Slurm still reports
    19 running and 5 pending behind `QOSMaxJobsPerUserLimit`; log scanning is
    clean for traceback/OOM/killed/disk/timeout signatures. A global
    `build-msa-cache --materialize-cache --incremental` refresh found
    109 existing records, 0 stale rows, and 0 newly added records, confirming
    this wait is inference/shard completion, not repeated MSA work. The
    readiness TSV is now generated with `missing_tasks=none` for complete
    shards, so polling no longer needs hand cleanup.
75. `2026-07-07 10:45 CDT` P25/P27b checkpoint: live Slurm status still shows the
    repaired P25 seed106-125 grid incomplete, with 19 GH jobs running and 5
    pending behind `QOSMaxJobsPerUserLimit`; do not merge or score it yet. A
    refreshed `check-shards` pass reports `ready=false`, `compatible=true`,
    `604` observed candidates, `1446` shard-level candidates still missing,
    and `1371` full 25-candidate slots still missing. This readiness check must
    keep the execution shard budget at `--candidate-count 5` and the merged row
    budget at `--merged-candidate-count 25`; otherwise target+seed shards are
    falsely treated as incomplete 25-candidate execution shards. A repaired-input
    default-params model/config branch, P27b, is now fully documented but still
    deferred:
    `attack_budgets/casp16_server_attack_protenix5_input_repair_defaultparams_model_variant.json`
    and its shard TSV point to six run specs on the P17/P25 79-job repaired
    scoreable input. Preflight is `6/6 ok`, complete MSA reuse is `146/146`,
    and all rows remain `deferred:await_p25_score`. Use P27b only if the
    complete P25 score shows that extra seed scaling is weak and
    target-agnostic model/config diversity is the next best compute spend.
76. `2026-07-07` O5b repaired-input branch: the old 74-job antibody/Fv scoreable
    branch is now superseded for future launch decisions by
    `casp16_server_attack_protenix5_input_repair_antibody_fv`. The new O5b
    artifact applies the same sequence-only Fv constant-region trimming to the
    P17/P25 79-job repaired input, preserves the repaired five added jobs
    (`T1212/T1239V2/T1249V2O/T1269V1O/T2249V2O`), changes 24 sequences across
    12 antibody-like targets, and shards into six target-balanced run specs.
    Preflight is `6/6 ok` with complete MSA reuse (`146/146`, 0 stale), and all
    six rows are `deferred:await_p25_score`. Do not submit O5b before P25 is
    complete and scored.
77. `2026-07-07 10:53 CDT` P25 live gate: the seed106-125 target-seed grid is
    still not merge-ready, but it is progressing rather than stalled. Slurm
    still shows 19 P25 jobs running and 5 pending behind
    `QOSMaxJobsPerUserLimit`; refreshed readiness is `ready=false`,
    `compatible=true`, `607` observed candidates, `1443` shard-level candidates
    missing, and `1368` full 25-candidate slots missing. Log tails show the
    running jobs are spending time on expected slow, large scoreable complexes
    such as `H0258`, `H2258`, `H1220`, and `H1272`; error scanning remains
    clean for traceback/OOM/killed/disk/timeout signatures. Keep waiting for
    complete P25 readiness; do not launch O5b/P27b or score partial outputs.
78. `2026-07-07 11:15 CDT` P25 live gate: the repaired P25 grid remains healthy
    but incomplete. Slurm reports the same launch shape: 19 P25 GH jobs running
    and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`. `check-shards`
    reports `ready=false`, `compatible=true`, `639` observed candidates,
    `1411` shard-level candidates missing, `1336` full 25-candidate slots
    missing, and `0` full target tasks complete. New artifacts appeared from
    shard01/shard02, including repaired/scoreable rows such as `H0258`,
    `T0234`, `T0235`, `H1258`, `T0206`, `T1239V1`, and `T1266`; error scanning
    still finds no traceback/OOM/CUDA killed/disk/timeout signatures. This
    confirms the blocker is slow Protenix forward plus queued shard06 jobs, not
    MSA-cache reuse. The only valid next gate is full P25 merge and scoring
    after every declared candidate exists; keep O5b/P27b deferred.
79. `2026-07-07 11:20 CDT` P25 live gate: progress is monotonic but still far
    from merge-ready. Four new shard02 candidates appeared for `T1269`
    (`seed_106`, `111`, `116`, and `121`), raising readiness to
    `observed_candidate_count=643`, `missing_candidate_count=1407`, and
    `full_missing_candidate_count=1332`. Slurm still shows 19 P25 jobs running
    and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; error scanning
    remains clean. Do not score partial P25 or launch O5b/P27b from this
    incremental progress.
80. `2026-07-07 11:25 CDT` P25 live gate: the same gate remains active and
    still blocks scoring. Fresh shard03 seed106 artifacts appeared for
    `H2258`, `T1234`, and `T1280`, plus one shard01 seed106 `T1210` artifact,
    raising readiness to `observed_candidate_count=647`,
    `missing_candidate_count=1403`, and `full_missing_candidate_count=1328`.
    Slurm still shows 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`; shard06 has not started producing candidates yet.
    Error scanning remains clean for traceback/OOM/CUDA killed/disk/timeout
    signatures. Keep waiting for complete P25 readiness; do not partial-score,
    merge, or launch O5b/P27b.
81. `2026-07-07 11:27 CDT` P25 live gate: still `ready=false` and
    `compatible=true`, but shard01 continues to produce candidates. New
    seed106/121 artifacts appeared for `T1210`, `T1298`, `T2201`, and `T2206`
    classes, raising readiness to `observed_candidate_count=656`,
    `missing_candidate_count=1394`, and `full_missing_candidate_count=1319`.
    Slurm state is unchanged at 19 P25 jobs running and 5 P25 jobs pending
    behind `QOSMaxJobsPerUserLimit`; shard06 remains queued with zero observed
    candidates. This is progress, not a scoring point. Keep O5b/P27b deferred
    and do not use a partial P25 row.
82. `2026-07-07 11:29 CDT` P25 live gate: still `ready=false` and
    `compatible=true`. Shard01 now has 13 observed candidates in each seed
    block, and shard03 has started adding `H2258` candidates beyond seed106.
    Readiness is now `observed_candidate_count=665`,
    `missing_candidate_count=1385`, and `full_missing_candidate_count=1310`.
    Slurm remains at 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`; shard05 seed121-125 and all shard06 seed blocks
    are still queued with zero observed candidates. No runtime error signatures
    were found. Keep waiting for full P25 readiness before merge/score.
83. `2026-07-07 11:30 CDT` P25 live gate: still not merge-ready. Shard03 added
    the remaining visible `H2258/T1234/T1280` seed blocks, bringing readiness
    to `observed_candidate_count=672`, `missing_candidate_count=1378`, and
    `full_missing_candidate_count=1303`. Slurm still reports 19 P25 jobs
    running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; shard05
    seed121-125 and all shard06 seed blocks remain at zero observed candidates.
    Error scanning remains clean. Do not merge, score, or launch the deferred
    O5b/P27b branches from this partial row.
84. `2026-07-07 11:36 CDT` P25 live gate: the repaired-input target-seed grid
    continues to produce artifacts but remains far from a valid score point.
    Readiness is `ready=false`, `compatible=true`, with `724` observed
    candidates, `1326` shard-level candidates missing, and `1251` full
    25-candidate slots missing. Slurm still shows 19 P25 jobs running and 5 P25
    jobs pending behind `QOSMaxJobsPerUserLimit`; shard05 seed121-125 and all
    shard06 seed blocks are still at zero observed candidates. New outputs in
    the last window include shard01/02/03/05 rows such as `H2204`, `H0222`,
    `H0223`, `T1201O`, `T1212`, `T2210`, `H1220`, `T1235`, `T1206O`,
    `T1249V2O`, and `T2235O`. Error scanning over recent logs found no
    traceback/OOM/CUDA killed/disk/timeout signatures. Keep waiting for full
    P25 readiness; no partial score, merge, O5b, or P27b launch yet.
85. `2026-07-07 11:38 CDT` P25 live gate: still healthy and incomplete.
    `check-shards` reports `ready=false`, `compatible=true`, `746` observed
    candidates, `1304` shard-level candidates missing, and `1229` full
    25-candidate slots missing. Slurm state is unchanged at 19 P25 jobs
    running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; the
    pending rows are shard05 seed121-125 and all shard06 seed blocks, which
    explains the five zero-output readiness rows. Recent log scanning again
    found no traceback/OOM/CUDA killed/disk/timeout signatures. This is still
    a waiting gate, not a score gate.
86. `2026-07-07 11:42 CDT` P25 live gate: still `ready=false` and
    `compatible=true`, with `751` observed candidates, `1299` shard-level
    candidates missing, and `1224` full 25-candidate slots missing. Slurm is
    unchanged at 19 P25 jobs running plus 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`; the same five pending rows have zero outputs.
    Recent new artifacts include `H1227` and `T1249V1` from running shards.
    Error scanning remains clean. Keep waiting for the complete merged row.
87. `2026-07-07 11:51 CDT` P25 live gate: still `ready=false` and
    `compatible=true`, with `808` observed candidates, `1242` shard-level
    candidates missing, and `1167` full 25-candidate slots missing. Slurm still
    shows 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`; no merge or partial score is allowed. While
    waiting, a focused reference-recovery probe checked the high-value domain
    gaps `T1292`, `T1294V1`, `T1274`, and `T1231`: exact search, T1292
    C-terminal His-tag trimming, and relaxed identity cutoffs down to 0.90
    returned no RCSB hits. Template-like public hits such as `6N63` for T1292
    remain non-promotable without native/provider provenance and construct
    mapping.
88. `2026-07-07 11:54 CDT` P25 live gate: still `ready=false` and
    `compatible=true`, now with `828` observed candidates, `1222` shard-level
    candidates missing, and `1147` full 25-candidate slots missing. Slurm state
    is unchanged at 19 P25 jobs running plus 5 pending behind
    `QOSMaxJobsPerUserLimit`, so no merge/score or O5b/P27b launch is allowed.
    While waiting, D6 domain sequence recovery was rechecked: the warmup run has
    real full-MSA/template predictions for repaired `T1228V1`, `T1239V1`, and
    `T1276`; the follow-up full benchmark run has complete exact-sequence MSA
    reuse (`276/276` protein chains, 0 stale) but no predictions yet. Keep D6
    as a post-P25 branch if the complete P25 score still shows domain zeros
    from input-kind or alias repair classes.
89. `2026-07-07` Reference-gap hygiene: fixed the official FASTA sequence
    classifier so protein-like records with misleading `DNA` text in the record
    id or header are parsed as `proteinChain` by sequence content. This keeps
    future regenerated inputs from repeating the `T1228V1`/`T1276`-class
    input-kind bug. It does not promote any native reference, does not change
    locked benchmark eligibility in place, and does not make current
    `missing_reference` rows scoreable without a versioned refmap benchmark.
90. `2026-07-07 12:04 CDT` P25 live gate: still not merge-ready. Shard
    readiness is `ready=false`, `compatible=true`, with `847` observed
    candidates, `1203` shard-level candidates missing, and `1128` full
    25-candidate slots missing. Slurm still has 19 P25 jobs running and 5 P25
    jobs pending behind `QOSMaxJobsPerUserLimit`; shard05 seed121-125 and all
    shard06 seed blocks remain zero-output. While waiting, MSA cache reporting
    was upgraded to show fresh-MSA cost by task, then run on the next attack
    inputs. The current scoreable input-repair P25 input has `146/146` protein
    chains covered from exact-sequence cache, and the D6 full input has
    `276/276` covered, both with 0 stale index rows. The next bottleneck is
    GPU inference completion and scoring, not fresh MSA generation for these
    two branches.
91. `2026-07-07 12:09 CDT` P25 live gate: still `ready=false` and
    `compatible=true`, now with `852` observed candidates, `1198` shard-level
    candidates missing, and `1123` full 25-candidate slots missing. Queue state
    is unchanged: 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`. No partial merge or score was run. While waiting,
    `docs/CASP16_WINNER_RECIPES.md` was refreshed with an official
    server-only fingerprint from
    `leaderboards/casp16_server_protein_v2_aliasfix/official_server_groups.csv`:
    domain winner `110s` has fixed mean `0.923321` over 71/71 targets, and
    oligo winner `456s` has fixed mean `0.582615` over 102/104 submitted
    targets. The local repaired five-candidate overlay remains much lower
    (`0.107690` domain, `0.118933` oligo), so P25 remains a
    scoreable-subset candidate-budget probe rather than a server-winner claim.
92. `2026-07-07 12:12 CDT` P25 live gate: unchanged at `ready=false`,
    `compatible=true`, `852` observed candidates, `1198` shard-level missing,
    and `1123` full candidate slots missing. The post-P25 execution queue was
    tightened in `docs/AUTORESEARCH_QUEUE.md`: after P25 completes, choose
    exactly one branch by failure mode: P27b for flat valid predictions, D6a
    for domain input-kind/alias zeros, O5b for antibody/Fv oligo weakness, or
    versioned refmap work for reference caps. No new Slurm jobs were submitted.
93. `2026-07-07 12:19 CDT` P25 live gate: still `ready=false` and
    `compatible=true`; the safe finish wrapper reports `855` observed
    candidates, `1195` shard-level missing candidates, and `1120` full
    25-candidate slots missing. Slurm still has 19 P25 jobs running and 5 P25
    jobs pending behind `QOSMaxJobsPerUserLimit`. Added
    `scripts/finish_p25_scoreable_input_repair.sh` so the eventual closeout is
    one audited command wrapping `finish-shards` with the seed101-105 overlay
    plus all submitted seed106-125 target shards. The wrapper returns
    `finish_status=not_ready` while incomplete, so it can be dry-run safely
    without producing a partial score.
94. `2026-07-07 12:22 CDT` P25 runtime diagnostic: readiness is unchanged
    (`ready=false`, `compatible=true`, `855` observed, `1195` shard-level
    missing, `1120` full-slot missing) and Slurm still shows 19 P25 jobs
    running plus 5 pending. Log tails show the running jobs are alive and
    spending time on large complex targets, not redoing MSA: shard01 is on
    `H0258`, shard02 on `H1258`, shard03 on `H2258`, shard04 on `H0272`, and
    shard05 on `H1272`; shard05 seed121-125 and all shard06 blocks remain
    pending. `run-next --dry-run` still reports no pending runs, and P27b/O5b
    stay deferred with clean MSA preflight. Do not submit another branch while
    these large target inferences are still consuming the active GH slots.
95. `2026-07-07 12:26 CDT` P25 gate: still not ready with the same
    `855/1195/1120` candidate counts and the same 19 running plus 5 pending
    P25 jobs. While waiting, the v5 reference-recovery audit for `T1228V1` was
    tightened in `diagnostics/reference_gap/t1228v1_v5_refmap_audit.tsv`.
    The D6a-style input repair is real (`T1228V1` is now representable as a
    545-residue `proteinChain`), but the refmap row is still blocked:
    official CASP M1228v1/M1228v2 pages say the complex has two distinct
    conformations without mapping variant `v1` to a later PDB state. Therefore
    `9dxk` and `9y66` remain blocked despite full domain chain support, and
    `9dxh/9dxj` remain blocked by both native-state ambiguity and two missing
    N-terminal positions. Do not promote `T1228V1` into v5 until native-state
    provenance plus explicit chain/domain crop mapping are available.
96. `2026-07-07 12:35 CDT` P25 gate and reference queue refresh: P25 remains
    incomplete (`ready=false`, `compatible=true`) with `858` observed
    candidates, `1192` shard-level missing candidates, and `1117` full
    25-candidate slots missing. Slurm still shows 19 P25 jobs running and 5
    P25 jobs pending, so no partial scoring or new branch launch is allowed.
    The v4 reference-gap report now exposes deferred sequence hits instead of
    hiding them; the v5 queue still has 42 target-family tasks, now split into
    1 near-term candidate, 5 deferred-hit review rows, 16 domain manual-search
    rows, 2 oligo assembly-mapping rows, 5 input/alias repair rows, and 13
    oligo manual-search rows. Deferred hits are review work only and remain
    non-promotable until provenance and mapping are explicit.
97. `2026-07-07 12:47 CDT` P25 gate: still incomplete but moving. The safe
    finish dry-run reports `ready=false`, `compatible=true`, `886` observed
    candidates, `1164` shard-level missing candidates, and `1089` full
    25-candidate slots missing. Slurm still shows 19 P25 jobs running and 5
    P25 jobs pending behind `QOSMaxJobsPerUserLimit`. `docs/CASP16_WINNER_RECIPES.md`
    now treats P25, not P14/P17, as the active branch-selection gate: after the
    complete P25 score exists, choose exactly one next branch by evidence
    (P27b for flat valid predictions, D6a for domain input-kind/alias zeros,
    O5b for antibody/Fv oligo weakness, or versioned refmap work for reference
    caps). Do not score partial P25 or launch those deferred branches early.
98. `2026-07-07 12:52 CDT` P25 health check: still `ready=false` and
    `compatible=true`, now with `890` observed candidates, `1160` shard-level
    missing candidates, and `1085` full 25-candidate slots missing. Slurm is
    unchanged at 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`. Error keyword scanning across P25 run logs found
    no traceback/OOM/file-missing signatures, sampled stderr tails show normal
    Protenix forward on large scoreable targets, and `run-next --dry-run`
    reports `no_pending_runs`. This is wait-for-completion time, not a branch
    selection point.
99. `2026-07-07 12:57 CDT` P25 gate: still `ready=false` and
    `compatible=true`, now with `897` observed candidates, `1153` shard-level
    missing candidates, and `1078` full 25-candidate slots missing. Slurm still
    has 19 P25 jobs running and 5 P25 jobs pending behind
    `QOSMaxJobsPerUserLimit`. Added `./casp16 post-p25-readout`, a read-only
    aggregate decision gate that compares the eventual P25 row against the P17
    repaired-input baseline without reading native references or official
    per-target score tables. On current artifacts it correctly returns
    `decision_status=not_scored` and `next_branch=finish_or_score_p25`;
    baseline P17 is `79/79` scoreable `ok` with fixed-set mean `0.114371554`
    and 96 no-reference zero rows.
100. `2026-07-07 13:02 CDT` P25 gate: still `ready=false` and
     `compatible=true`, now with `927` observed candidates, `1123`
     shard-level missing candidates, and `1049` full 25-candidate slots
     missing. One target is now complete at the full 25-candidate budget, but
     only the seed101-105 overlay shard is complete as a shard. Slurm remains
     19 P25 jobs running plus 5 P25 jobs pending behind
     `QOSMaxJobsPerUserLimit`; the pending jobs are shard05 seed121-125 and all
     shard06 seed blocks. Error keyword scanning across P25 logs is clean, so
     this is still normal long-target inference and queue waiting. No partial
     scoring and no deferred P27b/O5b/D6a launch.
101. `2026-07-07 13:13 CDT` P25 gate: still `ready=false` and
     `compatible=true`, now with `996` observed candidates, `1054`
     shard-level missing candidates, and `984` full 25-candidate slots missing.
     Slurm still has 19 P25 jobs running and 5 P25 jobs pending behind
     `QOSMaxJobsPerUserLimit`; the pending P25 jobs are still shard05
     seed121-125 plus all shard06 seed blocks. This is monotonic progress but
     not a closeout point. `docs/CASP16_WINNER_RECIPES.md` now records a
     post-P25 winner-trick triage table so the next branch is selected from the
     complete P25 evidence rather than from a partial shard readout.
102. `2026-07-07 13:20 CDT` P25 gate: still `ready=false` and
     `compatible=true`, now with `1013` observed candidates, `1037`
     shard-level missing candidates, and `967` full 25-candidate slots missing.
     Slurm still shows 19 P25 jobs running and 5 P25 jobs pending behind
     `QOSMaxJobsPerUserLimit`, with shard05 seed121-125 and all shard06 seed
     blocks pending. Error keyword scanning across P25 logs remains clean, and
     recent logs show active inference on H2236, T1249V1O, H1236, H0236,
     T1249V1, and H0220. The repaired-input P25 MSA audit is `24/24 ok` with
     `584/584` protein-chain paths covered and `0` stale paths, so the current
     wait is queue plus large-complex inference, not repeated MSA work. Do not
     add more MSA-cache plumbing or launch P27b/O5b/D6a until the complete P25
     row can be merged and scored.
103. `2026-07-07 13:37 CDT` P25 gate: still `ready=false` and
     `compatible=true`, now with `1091` observed candidates, `959`
     shard-level missing candidates, and `889` full 25-candidate slots
     missing. One target is complete at the full 25-candidate budget, but the
     merged P25 row is still absent from `runs.csv` and must not be scored.
     Slurm remains 19 running P25 jobs plus 5 pending P25 jobs behind
     `QOSMaxJobsPerUserLimit`; the pending P25 jobs are shard05 seed121-125
     and all shard06 seed blocks. Error keyword scanning across P25 logs is
     clean. This confirms the bottleneck is still large-complex inference plus
     queue limits, not MSA cache, scorer failure, or a branch-selection point.
104. `2026-07-07 13:51 CDT` P25 gate: still not ready, now with `1105`
     observed candidates, `945` shard-level missing candidates, and `875`
     full 25-candidate slots missing. Slurm still shows 19 P25 jobs running
     and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`, so the correct
     action remains wait-for-complete closeout rather than partial scoring or
     launching P27b/O5b/D6a. While waiting, the Lane C missing-reference
     boundary was made explicit in
     `diagnostics/reference_gap/casp16_server_protein_v5_input_alias_repair_candidates.tsv`:
     `T1228V2` and `T1294V2` already have D6a-style sequence inheritance and
     exact-sequence MSA cache coverage, while `H1265_V1/V2/V3` still need a
     versioned score-table variant input-alias repair. All five remain
     `not_reference_ready`; realistic input coverage can move forward, but
     accepted v5 references still require native-state/domain or
     assembly/QSglob mapping proof.
105. `2026-07-07 13:55 CDT` Lane C executable repair: the strategy resolver
     now handles score-table variant aliases such as `H1265_V2 -> H1265`
     instead of leaving them as `no_sequence_record`. Regenerating
     `strategies/yang_protein_oligo_sequence_recovery_v1/casp16_server_protein_v2_aliasfix/`
     produces `168` jobs and changes `8` oligo targets, including
     `H1265_V1`, `H1265_V2`, and `H1265_V3` as two-chain H1265 protein
     inputs of total length `293`. `./casp16 check-msa-cache` reports the
     repaired artifact is fully cache-covered (`286/286` protein chains,
     `0` stale). This is input realism and MSA readiness only; those three
     targets remain `not_reference_ready` until variant/native assembly and
     QSglob mapping proof exist.
106. `2026-07-07 13:56 CDT` post-P25 readout hardening: while P25 remains
     `decision_status=not_scored`, `./casp16 post-p25-readout` now emits a
     non-executing `launch_plan` object. In the current state it points back
     to the safe closeout sequence: finish dry-run, finish, score, leaderboard,
     and re-readout. After a complete P25 score, the same field carries the
     selected branch run ids, preflight TSV, target-shard flag, and command
     templates for D6a, O5b, P15/v4, or P27b. This keeps the next
     winner-recipe iteration machine-readable without launching anything
     before the P25 gate opens.
107. `2026-07-07 14:01 CDT` v4 input-alias carryover: regenerated
     `yang_protein_oligo_sequence_stoich_token_safe_v1` on
     `casp16_server_protein_v4_refmap` so the H1265 score-table variant alias
     repair is not v2-only. The v4 artifact now has 168 jobs, changes 6
     protein-oligo sequence-recovery targets, and turns `H1265_V1/V2/V3` into
     H1265-derived two-chain protein inputs of total length 293. The read-only
     MSA cache check is complete (`286/286` protein chains, `0` stale) in
     `diagnostics/msa_cache/yang_protein_oligo_sequence_stoich_token_safe_v1_v4_refmap.tsv`.
     `post-p25-readout` also now has a `score_p17_baseline_before_branching`
     launch plan so a missing baseline score produces executable recovery
     steps instead of a dead-end branch label.
108. `2026-07-07 14:09 CDT` P25 gate and recipe-board sync: P25 remains
     incomplete with `ready=false`, `compatible=true`, `1106` observed
     candidates, `944` shard-level missing candidates, and `874` full
     25-candidate slots missing. Slurm still shows 19 P25 jobs running and 5
     P25 jobs pending behind `QOSMaxJobsPerUserLimit`, so the only ranked
     action is still wait-for-declared-candidates followed by the closeout
     wrapper. Added `docs/WINNER_REPRODUCTION_BOARD.md` as the short
     autoresearch control board: it records the official score targets,
     current P17 local baseline, active P25 gate, winner-clue reproduction
     ladder, post-P25 decision order, and the file map an agent should read
     before choosing D6a, O5b, P27b, or refmap work.
109. `2026-07-07 14:16 CDT` post-P25 launch-plan enrichment:
     `./casp16 post-p25-readout` now attaches read-only `run_specs`,
     `alternate_run_specs`, `preflight`, and `alternate_preflight` summaries
     to the selected `launch_plan`. These fields read local `run_spec.json`,
     `runs/status.tsv`, and existing preflight TSVs only; they do not run
     preflight, submit Slurm jobs, or inspect native structures. The goal is to
     make the first post-P25 branch launch auditable: once the complete P25
     row selects D6a/O5b/P27b/P15, the JSON will show whether the selected run
     specs exist, their latest lifecycle status, budget tier, candidate count,
     and whether the prepared MSA preflight artifact is all `ok`.
110. `2026-07-07 14:20 CDT` post-P25 delta digest:
     `./casp16 post-p25-readout` now also emits `target_delta_summary`, a
     scoreable-target-only comparison of the complete P25 row against the P17
     repaired baseline. It reports improved/regressed/unchanged counts,
     nonzero gained/lost counts, status-transition counts, per-track summaries,
     and the largest score deltas for diagnosis. This is intentionally
     post-score analysis only: it returns `status: incomplete` and
     `valid_for_analysis: false` until P25 and the baseline both have complete
     scoreable `target_scores.csv` rows. Use the `status: ok` digest to explain
     why the aggregate branch chooser selected analysis, D6a, O5b, P27b, or
     refmap work, but do not use target deltas for per-target prediction
     tuning.
111. `2026-07-07 14:27 CDT` post-P25 branch readiness audit:
     Added `./casp16 post-p25-branch-readiness`, a read-only audit of the
     prepared P27b, D6a, O5b, and P15/v4 branch artifacts. It summarizes local
     run specs, lifecycle status counts, preflight TSV result counts, and
     whether each branch is launch-ready after complete P25 selection. Current
     audit says all four deferred branches are launch-ready: P27b and O5b have
     `deferred:await_p25_score` lifecycle rows, while D6a and P15/v4 still
     carry older `deferred:await_p14_score` labels but have complete run specs
     and `ok` preflights. This command does not submit jobs or inspect scores.
112. `2026-07-07 14:29 CDT` P25 closeout now includes no-GPU selector replay:
     `scripts/finish_p25_scoreable_input_repair.sh` passes `--replay-run-id`
     for
     `server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125_consensus_replay`.
     Once all declared candidates exist, the wrapper will merge P25, write
     prediction-only `selection-qa` sidecars, register the
     `diversity_confidence_consensus_v1` replay row, and score both selectors
     together. It also writes the post-P25 decision JSON under
     `diagnostics/score_probes/` after the leaderboard refresh, so the selected
     next branch is captured at closeout time. This tests QA/model selection
     before spending another GPU branch.
113. `2026-07-07 14:37 CDT` P25 gate and MSA/model diversity design refresh:
     P25 remains incomplete but moving (`ready=false`, `compatible=true`,
     `1188` observed candidates, `866` shard-level missing candidates, and
     `796` full 25-candidate slots missing). Updated
     `attack_budgets/casp16_server_attack_msa_model_diversity_v1.json` from
     the stale P14-era design to the P17/P25 repaired-input base, recorded the
     configured no-GPU P25 consensus replay, and named P27b as the prepared
     model/config child. True MSA-variant generation stays gated behind
     complete P25 plus P27b evidence, not partial target scores.
114. `2026-07-07 14:41 CDT` P25 queue-cause check: P25 is still incomplete
     but advancing (`ready=false`, `compatible=true`, `1206` observed
     candidates, `850` shard-level missing candidates, and `780` full
     25-candidate slots missing). `qlimits` reports `gh` `MaxJobsPU=20`; Slurm
     currently has 19 P25 jobs running plus one running `tacc-vscode` job, so
     the five remaining P25 jobs are expected to sit behind
     `QOSMaxJobsPerUserLimit` until a running job exits. Error-keyword scans
     over P25 stdout/stderr found no traceback/OOM/killed signatures, and
     `post-p25-branch-readiness` still reports all four deferred branches
     launch-ready. No new GPU branch should be submitted from this state.
115. `2026-07-07 14:52 CDT` P25 live gate refresh and branch-label cleanup:
     P25 is still incomplete but moving (`ready=false`, `compatible=true`,
     `1258` observed candidates, `800` shard-level missing candidates, and
     `730` full 25-candidate slots missing). Slurm still has 19 P25 jobs
     running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`; the same
     zero-output rows are shard05 seed121-125 and all shard06 seed blocks, so
     this remains a queue/forward-time wait rather than an MSA-cache failure.
     Error-keyword scans over the P25 logs are clean. The read-only
     `post-p25-branch-readiness` audit now shows P27b, D6a, O5b, and P15/v4
     all launch-ready with `deferred:await_p25_score` lifecycle rows and `ok`
     preflights. Updated the live control docs to prevent later agents from
     reading stale `await_p14` labels as current launch instructions.
116. `2026-07-07 14:57 CDT` P25 live gate refresh: still not ready to merge or
     score. The replay-safe wrapper reports `finish_status=not_ready`,
     `status_summary.action=wait_for_declared_candidates`, `ready=false`,
     `compatible=true`, `1261` observed candidates, `797` shard-level missing
     candidates, and `727` full 25-candidate slots missing. Complete
     full-budget tasks remain `1/79`, with 5 zero-output rows:
     shard05 seed121-125 plus all four shard06 seed blocks. Slurm still has 19
     P25 jobs running and 5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`;
     `qlimits` confirms `gh` `MaxJobsPU=20`. Error-keyword scanning over P25
     logs remains clean, recent CIF/log writes reached 14:55 CDT, and
     `run-next --dry-run` returns `no_pending_runs`. Continue waiting for
     declared candidates; no partial P25 score or post-P25 GPU branch launch.
117. `2026-07-07 14:58 CDT` Lane F oligo reference probe while P25 waits:
     created
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_high_value_oligo_worklist.tsv`
     and ran `./casp16 refmap-probe` at identity `0.90` over 15 high-value
     oligo rows from Lane F. Outputs are
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_high_value_oligo_targets.tsv`
     and
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_high_value_oligo_candidates.tsv`.
     Only the `T0257O/T1257O/T2257O` family produced hits (`5AQ5`, `4UW7`,
     `4UW8`), and all are shorter bacteriophage T5 tail-fiber domain/template
     hits marked `sequence_search_hit_alignment_unverified`; they are not
     accepted references. The other probed Lane F families returned `no_hits`,
     so the next work is manual native/provenance plus QSglob assembly mapping,
     not another search-depth-only RCSB loop.
118. `2026-07-07 15:00 CDT` P25 live gate refresh: still
     `finish_status=not_ready` with
     `status_summary.action=wait_for_declared_candidates`. The wrapper reports
     `ready=false`, `compatible=true`, `1267` observed candidates, `791`
     shard-level missing candidates, and `721` full 25-candidate slots
     missing. Complete full-budget tasks remain `1/79`; the 5 zero-output rows
     are unchanged: shard05 seed121-125 plus all four shard06 seed blocks.
     Slurm still shows 19 P25 jobs running and 5 P25 jobs pending behind
     `QOSMaxJobsPerUserLimit`. Error-keyword scanning is clean, and recent
     CIF/log writes reached 15:00 CDT on shard05 targets such as `H1220` and
     `T1235`. `post-p25-branch-readiness` reports all four deferred branches
     still launch-ready after complete P25 selection, while
     `post-p25-readout` remains `decision_status=not_scored` and
     `next_branch=finish_or_score_p25`. Do not score or branch from this
     partial state.
119. `2026-07-07 15:03 CDT` Lane F second oligo reference probe:
     created
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_second_oligo_worklist.tsv`
     and ran `./casp16 refmap-probe` at identity `0.90` over 15 additional
     Lane F oligo rows: ORF61/A3A, BJCNb48, Cry26Aa, AZI86_00190, and
     TLR4/MAL families. Outputs are
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_second_oligo_targets.tsv`
     and
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_second_oligo_candidates.tsv`.
     The probe found `0` hits and `0` candidate rows, so these families should
     move to manual native/provenance search plus biological assembly/QSglob
     mapping instead of another search-depth-only RCSB loop.
120. `2026-07-07 15:05 CDT` P25 live gate refresh: still not merge-ready.
     `finish_status=not_ready`, `action=wait_for_declared_candidates`,
     `ready=false`, `compatible=true`, `1269` observed candidates, `789`
     shard-level missing candidates, and `719` full 25-candidate slots
     missing. Complete full-budget tasks remain `1/79`, and the same five
     zero-output rows are pending behind the `gh` `MaxJobsPU=20` limit.
     Error-keyword scanning is clean; recent CIF/log writes reached 15:05 CDT
     on shard01 `H0236`. Continue waiting for declared candidates.
121. `2026-07-07 15:08 CDT` Lane F final oligo reference probe:
     corrected the final worklist to use the detailed
     `casp16_server_protein_v2_aliasfix_missing_references.tsv` rows, then ran
     `./casp16 refmap-probe` at identity `0.90` over the remaining Lane F
     targets `T1292O`, `T1294V1O`, and `T0240O/T1240O/T2240O`. Outputs are
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_final_oligo_targets.tsv`
     and
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_f_final_oligo_candidates.tsv`.
     The corrected probe found `0` hits and `0` candidate rows, completing
     relaxed RCSB sequence-probe coverage for all 13 Lane F families and all
     35 target rows. Lane F should now move to manual native/provenance plus
     QSglob assembly mapping only; do not run another search-depth-only loop.
122. `2026-07-07 15:08 CDT` P25 live gate refresh: still not merge-ready.
     `finish_status=not_ready`, `action=wait_for_declared_candidates`,
     `ready=false`, `compatible=true`, `1278` observed candidates, `780`
     shard-level missing candidates, and `710` full 25-candidate slots
     missing. Complete full-budget tasks remain `1/79`; shard05 seed121-125
     and all four shard06 seed blocks still have zero output because they are
     pending behind the `gh` `MaxJobsPU=20` cap. Slurm has 19 P25 jobs running
     and 5 P25 jobs pending. Keep waiting; do not score P25, launch O5b/P27b,
     or make a winner-comparison claim from this partial state.
123. `2026-07-07 15:14 CDT` P25 live gate plus Lane B deferred-hit review:
     P25 is still not merge-ready but continues to advance:
     `ready=false`, `compatible=true`, `1297` observed candidates, `761`
     shard-level missing candidates, and `691` full 25-candidate slots
     missing. Slurm still has 19 P25 jobs running and 5 P25 jobs pending
     behind `QOSMaxJobsPerUserLimit`; an error-keyword scan over P25 run/log
     files found no traceback/OOM/killed signatures. While waiting, recorded
     `diagnostics/reference_gap/casp16_server_protein_v5_lane_b_deferred_hit_review.tsv`.
     It reviews all five Lane B deferred-hit families and rejects them for
     refmap promotion: `10br` is a short HtrA fragment, the H0215-family hits
     do not establish the mNeonGreen-nanobody target assembly, and the
     T1295/T1295O TM_Ag hits are partial/template structures. No accepted
     references are added; these rows move to manual native/provenance plus
     explicit domain-crop or QSglob assembly mapping.
124. `2026-07-07 15:17 CDT` P25 live gate plus Lane D oligo assembly review:
     P25 is still not merge-ready: `ready=false`, `compatible=true`, `1331`
     observed candidates, `727` shard-level missing candidates, and `657`
     full 25-candidate slots missing. Slurm still has 19 P25 jobs running and
     5 P25 jobs pending behind `QOSMaxJobsPerUserLimit`. While waiting,
     recorded
     `diagnostics/reference_gap/casp16_server_protein_v5_lane_d_oligo_assembly_review.tsv`.
     It condenses the existing oligo assembly audit for H0217/H1217/H2217 and
     H0267/H1267/H2267: the AcP10/eIF2B candidates are 10-18 polymer-chain
     assemblies versus 6-chain target rows, and the XauSPARDA candidates are
     tetrameric or 34-meric assemblies versus 2-chain target rows. No current
     Lane D assembly is accepted for refmap promotion; future progress needs
     native assembly provenance plus explicit QSglob chain/interface mapping.
125. `2026-07-07 15:22 CDT` P25 live gate plus Lane E domain search review:
     P25 is still not merge-ready but continues to advance: `ready=false`,
     `compatible=true`, `1341` observed candidates, `717` shard-level missing
     candidates, and `647` full 25-candidate slots missing. While waiting,
     built
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_e_remaining_domain_worklist.tsv`
     from all Lane E domain families and ran `./casp16 refmap-probe` at
     `identity_cutoff=0.90` / `max_hits=25` over 36 target rows. Outputs are
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_e_all_domain_targets.tsv`,
     `diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_e_all_domain_candidates.tsv`,
     and
     `diagnostics/reference_gap/casp16_server_protein_v5_lane_e_domain_search_review.tsv`.
     The sweep found 9 candidate rows, all for the `T0257/T1257/T2257`
     family (`5AQ5`, `4UW7`, `4UW8`), and rejects them as short tail-fiber
     domain/template structures: 294-427 residues versus the 1263-residue CASP
     target sequences, with no exact or contained sequence relationship. The
     other 15 Lane E families have relaxed90 `no_hits`. No Lane E accepted
     reference is added; future work is manual native/provenance search plus
     explicit domain crop mapping only.

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
