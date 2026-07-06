# CASP16 Autoresearch Experiments

This is the append-only working log for CASP16 score-chasing experiments.
Strategy changes should be recorded here before they are interpreted as
leaderboard progress.

## Active Baselines

| Run | Benchmark | Status | Purpose | Rank eligible |
| --- | --- | --- | --- | --- |
| `server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1` | `casp16_server_protein_v1` | scored diagnostic | reuse 35 existing OpenDDE local-v1 predictions to expose server coverage gap | no |
| `server_protenix_full_msa_template_seed101` | `casp16_server_protein_v1` | scored | full server-target Protenix baseline with real MSA/template settings | yes for domain track |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | `casp16_server_protein_v1` | scored | target-agnostic Yang-style terminal tag cleanup rerun | yes for domain track |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `casp16_server_protein_v1` | scored | single-entity oversize domain fallback recovered `T1295` inference but not score, because `T1295` lacks local reference mapping | yes for domain track |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | scored negative | full-set antibody Fv constant-region cleanup rerun | yes for domain track |
| `server_attack_protenix_terminal_tag_seed101_105` | `casp16_server_protein_v1` | Slurm job `810719` running; 98/98/67/0/0 CIFs by seed at `2026-07-06 18:25 CDT`; still hitting the known `n_token > 2560` jobs | five-seed terminal-tag cleanup attack run with predeclared confidence-only model selection | attack tier only |
| `server_protenix_yang_large_target_split_or_fallback_seed101` | `casp16_server_protein_v1` | pending behind attack job | predeclared token-budget fallback for all eight Protenix `n_token > 2560` failures | yes for domain track, coverage-recovery caveat |
| `server_protenix_yang_sequence_recovery_seed101` | `casp16_server_protein_v1` | pending behind active jobs | recover missing/misparsed protein-domain sequences on top of terminal-tag cleanup | yes for domain track, coverage-recovery caveat |
| `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `casp16_server_protein_v1` | pending behind active jobs | stack sequence recovery with token-budget fallback before larger attack budgets | yes for domain track, coverage-recovery caveat |
| `yang_oligo_stoichiometry_recovery_v1` | `casp16_server_protein_v1` | artifacts generated, not queued | restore official oligo copy counts that collapsed to one copy per entity | not queued until token-safe/windowed derivative exists |
| `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `casp16_server_protein_v1` | pending behind active jobs | exact stoichiometry for under-budget oligo jobs on top of stacked coverage recovery | yes for domain track; oligo diagnostic until QSglob mapping is validated |
| `server_attack_protenix_coverage_stoich_seed101_105` | `casp16_server_protein_v1` | superseded:msa_reuse_successor | non-reuse five-seed attack run on stacked sequence-recovery, token-fallback, token-safe stoichiometry inputs | keep only as ablation |
| `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` | `casp16_server_protein_v1` | pending behind active v1 jobs; MSA preflight 180/196 chains reused, 16 missing, 0 stale | five-seed coverage+stoich attack successor using exact-sequence MSA reuse | attack tier only; lower priority than v2 scoreable nofail |
| `server_v2_protenix_yang_coverage_stoich_seed101` | `casp16_server_protein_v2_aliasfix` | superseded; Slurm wrapper job `810938` is running the current nofail dev row | older alias-fixed v2 baseline using coverage + token-safe stoichiometry inputs | keep only as ablation |
| `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` | `casp16_server_protein_v2_aliasfix` | superseded | older v2 coverage/stoich input plus Yang-style terminal low-complexity cleanup | keep only as ablation |
| `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101` | `casp16_server_protein_v2_aliasfix` | superseded | older v2 stack plus large-target fallback for the 11 remaining over-token jobs | keep only as ablation |
| `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101` | `casp16_server_protein_v2_aliasfix` | cancelled:scoreable_subset_attack; 39/165 CIFs, stopped on no-reference `T1295` | current strongest v2 no-over-token input stack with protein-oligo sequence recovery; keep partial artifacts/MSA cache only | not a complete dev row |
| `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | Slurm job `811751` running on `c636-072`; MSA update skipped, and 20/74 seed-101 CIFs exist at `2026-07-06 18:25 CDT` | five-seed attack on the current strongest v2 nofail stack, filtered to 74 locally scoreable jobs with 141/141 exact-sequence MSA paths reused | attack tier only; skipped no-reference targets still score 0 locally |
| `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:scoreable_subset_attack; former wrapper job `811751` is now running the scoreable-subset run selected by `run-next` | full 165-job MSA-reuse predecessor that repeats no-reference heavy jobs before reference recovery | attack tier only; run only as ablation |
| `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101` | `casp16_server_protein_v2_aliasfix` | deferred:slurm_wrapper_cancelled; Slurm job `811754` is `CANCELLED+` and no longer queued | narrow hydrophobic-leader construct cleanup on top of the v2 nofail stack, with MSA reuse | re-enable only after scoreable attack/full v2 score |
| `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | superseded:msa_reuse_attack | non-reuse predecessor of the current five-seed v2 no-over-token attack | attack tier only; run only as ablation |
| `server_v2_attack_nofail_protenix5_seed101_105` | `casp16_server_protein_v2_aliasfix` | pending; superseded candidate | older five-seed no-over-token attack that lacks protein-oligo sequence recovery | attack tier only; run only as ablation |
| `target_lab/h1258_interaction_window_v1` | target_lab only | artifact generated; standalone run skipped because the same H1258 window job completed inside `small_complex_stoich_batch_v1` | public LRRK2 interaction-window reproduction for H1258 | not rank eligible |
| `target_lab/small_complex_stoich_batch_v1` | target_lab only | complete; 6/6 structures, diagnostic DockQ regenerated | compact exact-stoich and H1258-window learning batch | not rank eligible |
| `targetlab_protenix_yang_antibody_fv_seed101` | target_lab only | complete; Slurm job `811918` produced 8/8 CIFs, confidence summaries, and DockQ diagnostics | eight Fv-only antibody-antigen target-lab jobs from `yang_antibody_fv_fragment_inputs_v1`; H0233/H1233 strongest DockQ positives | not rank eligible |
| `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | deferred | combined terminal-tag plus antibody-Fv cleanup rerun | do not launch before QSglob mapping or a positive antibody signal |
| `server_protenix_yang_epitope_tag_cleanup_seed101` | `casp16_server_protein_v1` | deferred | broader epitope/His/TEV tag cleanup rerun | do not launch before a predeclared large-target split policy |

## Current Score Truth

- Server domain comparator to beat: `110s`, fixed mean `0.923321`, metric
  `GDT_TS`, 71 targets.
- Server oligo comparator to beat: `456s`, fixed mean `0.582615`, metric
  `QSglob`, 104 targets.
- Current local server diagnostic reuse: domain `0.036428`, oligo `0.000000`.
  The main deficit is coverage and QSglob mapping/scoring, not just model
  quality.
- Current full Protenix server baseline: domain `0.063962`, with 15 ok, 30
  missing predictions, and 26 missing references over the fixed 71-domain
  target set. Oligo needs a rescore after OpenStructure QSglob mapping
  validation.
- QSglob signal probe, not a full leaderboard: on six oligo targets from the
  completed server-v1 Protenix dev runs, `H0222` and `T1249V1O` produced
  nonzero QSglob values while `H0220` remained unmapped. This makes QSglob
  useful for triage, but mapping false zeros still block official oligo claims.
- Current best local server-domain run:
  `server_protenix_yang_terminal_tag_cleanup_seed101`, domain `0.066908`,
  with 15 ok, 30 missing predictions, and 26 missing references over the fixed
  71-domain target set. This is a small improvement over baseline, not a
  winner-level result.
- The oversize-domain fallback produced 99/106 CIFs and rescued `T1295`
  inference, but its ranked domain mean is `0.065114`; `T1295` still scores
  `0` as `missing_reference`. It is a coverage fix, not the current best
  score.
- The antibody-Fv cleanup run produced 98/106 CIFs and scored domain
  `0.060677`, below both the baseline `0.063962` and terminal-tag cleanup
  `0.066908`. It predicted the main antibody oligo targets, but QSglob
  assembly mapping is not yet validated, so this is not evidence to spend
  additional multi-seed attack compute.
- Baseline inference generated 98/106 CIFs. The 8 failed Protenix jobs were all
  `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`,
  `H1272`, and `T1295O`. The fallback fixed only the `T1295` inference
  failure; `T1295O` and the six `H*` complex failures remain.

## Next Experiment Queue

1. Completed and scored `server_protenix_full_msa_template_seed101` on GH200
   node `c610-032` for the 106 server benchmark Protenix jobs.
   - Started by `./casp16 run-next --benchmark casp16_server_protein_v1` inside
     active Vista allocation `797582` at `2026-07-06T01:02:31Z`.
   - Finished at `2026-07-06T03:54:43Z`.
   - Scored with `./casp16 score --benchmark casp16_server_protein_v1` and
     `./casp16 leaderboard --benchmark casp16_server_protein_v1`.
2. Completed and scored `server_protenix_yang_terminal_tag_cleanup_seed101` as
   the first full optimized-input reproduction attempt. It trims only obvious
   terminal His/expression tags and keeps seed `101`, sample `1`,
   MSA/templates, and `first_output_only`. Cache, fusion, and TF32 are enabled
   to match the baseline engine flags.
   - First launch failed quickly because CUDA was not visible in the run
     script environment.
   - Run scripts now load or infer CUDA and math libraries before Protenix
     import; the relaunch reached Protenix MSA search at `2026-07-06T05:15Z`.
   - The successful run produced 98/106 CIFs and failed the same 8 hard
     `n_token > 2560` jobs as the baseline: `T1295`, `H0217`, `H0258`,
     `H0272`, `H1217`, `H1258`, `H1272`, and `T1295O`.
   - The domain mean improved from `0.063962` to `0.066908`. Main positive
     deltas were `T1234` `+0.1122`, `T1298` `+0.0863`, and `T1210`
     `+0.0519`; the main regressions were `T0234`, `T1249V1`, and `T1299`.
3. Completed and scored
   `server_protenix_yang_oversize_domain_monomer_fallback_seed101` to recover
   the known `T1295` server-domain token-limit failure. The strategy preserved
   all 106 server jobs, changed only `T1295` from `A8` to one representative
   chain, and kept MSA/templates/default params/seed/sample fixed.
   - It produced 99/106 CIFs, one more than baseline and terminal-tag cleanup.
   - `T1295` reached inference successfully as a 469-token job.
   - Domain mean was `0.065114`, above baseline but below terminal-tag cleanup.
   - The result did not improve the current best because `T1295` still lacks a
     local reference mapping and scores `0`.
4. Completed and scored `server_protenix_yang_antibody_fv_cleanup_seed101` as
   the first full-set antibody construct attempt after the lower-risk terminal
   cleanup.
   - It preserved all 106 server jobs and produced 98 CIFs.
   - The same 8 Protenix jobs failed with `n_token > 2560`.
   - Domain mean dropped to `0.060677`. Major regressions were `T0234`
     `-0.2288` versus baseline, `T1234` `-0.0012` versus baseline and
     `-0.1134` versus terminal-tag cleanup, and `T1298` `-0.0870` versus
     terminal-tag cleanup.
   - The antibody oligo targets `H0222`, `H0223`, `H0225`, `H1222`, `H1223`,
     and `H1225` produced predictions, but their old rows remain
     `metric_unavailable` until the run is rescored after QSglob mapping
     validation.
5. Defer `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101`.
   There is no reason to spend another full benchmark on the stacked run before
   either QSglob can evaluate antibody oligos or antibody cleanup shows a
   positive signal.
6. Defer `server_protenix_yang_epitope_tag_cleanup_seed101`. The current hard
   zeros are dominated by token-limit failures; a predeclared large-target
   split/fallback policy is higher priority than another ad hoc construct
   cleanup.
7. Installed OpenStructure `ost` as the default QSglob-compatible scorer, then
   found that H0220 completes with `status=ok` but maps no model chains and
   returns `QSglob=0`. Next step is assembly/chain mapping before oligo scores
   are treated as final.
8. Created `server_attack_protenix_terminal_tag_seed101_105`, the first
   multi-candidate attack run. It keeps terminal-tag cleanup inputs, uses seeds
   `101,102,103,104,105`, one sample each, and selects by
   `protenix_confidence_v1`. It is attack-tier only.
   - Submitted to Vista GH200 as Slurm job `810719` at `2026-07-06T15:29Z`;
     initial queue state was `PENDING (Priority)`.
   - `2026-07-06 16:32 CDT` live check: seed CIF counts are `98`, `89`, `0`,
     `0`, and `0`; the run is incomplete and must not be scored as a full
     five-candidate attack.
9. Start target_lab loops on H1258 and H1232 only as diagnostics for
   stoichiometry/construct tricks; promotion requires a target-agnostic full
   benchmark rerun.
10. Add domain cropping and chain/residue mapping before drawing conclusions
   from hard multi-domain domain targets.
11. Generated `yang_large_target_split_or_fallback_v1` after the conservative
    `T1295` fallback showed that coverage recovery is useful but incomplete.
    It changes exactly
    `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, and
    `T1295O`, reducing each optimized job below 2560 tokens by epitope cleanup
    and original-order chain/copy budget fallback.
12. Generated and queued `server_protenix_yang_sequence_recovery_seed101` on
    top of terminal-tag cleanup. It repairs 32 protein-domain inputs, including
    high-value local failures `T1212`, `T1239V1`, `T1239V2`, and `T2280`.
13. Generated and queued
    `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` on
    top of terminal-tag cleanup. It first repairs the same 32 protein-domain
    sequence coverage failures, then applies large-target fallback. The
    combined artifacts change 40 unique targets and keep the largest optimized
    job at 2535 tokens, below the Protenix 2560-token limit.
14. Generated `yang_oligo_stoichiometry_recovery_v1` on top of terminal-tag
    cleanup. It restores official parsed `Oligo.State` counts for 9 existing
    protein-oligo jobs. `H1232`, `H1233`, `H1236`, `H1244`, and `H1267` remain
    under the 2560-token limit; `H1217`, `H1227`, `H1258`, and `H1265` become
    realistic but oversized assemblies, so they need construct/domain-window
    handling before a ranked full run.
15. Generated and queued
    `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` on top of
    stacked coverage recovery. It restores exact copy counts for `H1232`,
    `H1233`, `H1236`, `H1244`, and `H1267`, skips exact recovery for oversize
    or upstream-reduced assemblies, preserves 135 Protenix jobs, and keeps the
    largest optimized job at 2535 tokens.
16. Generated `target_lab/h1258_interaction_window_v1` from the public CASP16
    complex-assessment clue that top Yang H1258 models used the LRRK2
    interacting region. The artifact uses LRRK2 residues 861-1014 after tag
    cleanup plus 14-3-3 A1B2, total length 648. It is target_lab-only and not
    a ranked run.
17. Generated and submitted `target_lab/small_complex_stoich_batch_v1`, a
    six-job target-lab batch with `H1232`, `H1233`, `H1236`, `H1244`, `H1267`,
    and the H1258 interaction-window job. The max job is 1929 tokens. Submitted
    as Slurm job `810824`, initially pending with reason `Priority`.
    - Job `810824` started on `c641-002` and failed before inference because
      `runner.batch_inference` resolved to the OpenDDE checkout instead of
      `Protenix-Insta`.
    - The target_lab Protenix scripts now prepend `Protenix-Insta` to
      `PYTHONPATH`, add the protein conda env to `PATH` so `ninja` is visible,
      and reuse the full benchmark CUDA/math library bootstrap.
    - Import preflight now resolves
      `/scratch/10992/liaorunlong93/Protenix-Insta/runner/batch_inference.py`
      with `protenix_cli=True`.
    - Resubmitted as Slurm job `811114`, initially pending with reason
      `Priority`.
    - Job `811114` completed on `c639-081` with 6/6 structures and confidence
      files. The regenerated diagnostic DockQ report shows H1233 as a strong
      exact-stoichiometry positive, H1236 moderate, H1232 weak, and H1258
      still blocked by chain mapping.
18. Generated `server_attack_protenix_coverage_stoich_seed101_105`, the second
    `protenix5` attack-tier run spec. It uses the stacked
    `yang_oligo_stoichiometry_token_safe_v1` inputs, seeds
    `101,102,103,104,105`, one sample each, and `protenix_confidence_v1`
    selection.
    - It is queued but not submitted.
    - `run-next --dry-run` remains blocked by the running terminal-tag attack,
      and the first pending dev run remains
      `server_protenix_yang_large_target_split_or_fallback_seed101`.
    - Submit only when this run is selected by `run-next --dry-run`, or
      intentionally supersede it after the component coverage runs finish.
19. Audited server-benchmark reference gaps while the attack job was running.
    The checked-in v1 benchmark has 54 available references and 106 Protenix
    jobs. A temporary rebuild with `0xxx/1xxx/2xxx` target aliasing produces 79
    available references and 163 Protenix jobs. This should become a new
    benchmark version, not an in-place v1 rewrite.
20. Generated `casp16_server_protein_v2_aliasfix` and its static leaderboard
    artifacts. The benchmark keeps the same 71 domain and 104 oligo official
    target sets, but improves Protenix input coverage to 163 jobs and cached
    references to 79 through target-phase aliasing. No prediction run is
    registered on v2 yet.
21. Generated v2 strategy inputs and run spec
    `server_v2_protenix_yang_coverage_stoich_seed101`.
    `yang_oligo_stoichiometry_token_safe_v1` changes 10 targets on v2, keeps
    all recovered jobs under 2560 tokens, and is pending as the first
    alias-fixed `dev_fixed` baseline.
    - Submitted as Slurm job `810938` with dependency `afterany:810719`.
    - Later superseded by
      `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`;
      the dependency was later cleared and the wrapper job is now running the
      newer oligo-recovery nofail dev row through `run-next`.
    - `2026-07-06 16:32 CDT` live check: the active nofail dev row has 18/165
      CIFs. MSA/template preprocessing completed and inference is progressing,
      so wait for completion before scoring or launching the dependent
      `protenix5` MSA-reuse attack.
    - `2026-07-06 16:36 CDT`: submitted Slurm job `811751` with dependency
      `afterany:810938` using
      `runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/run_gh200.slurm`.
      The wrapper calls `./casp16 run-next --benchmark
      casp16_server_protein_v2_aliasfix`, so it should start the MSA-reuse
      `protenix5` attack only after the current v2 dev job exits and the run
      queue is clear.
    - `2026-07-06 16:39 CDT`: submitted Slurm job `811754` with dependency
      `afterany:811751` using the hydrophobic-leader ablation wrapper. It also
      calls `run-next`, so it should run only after the attack clears and the
      next pending v2 row is the hydrophobic-leader `dev_fixed` ablation.
    - `2026-07-06 17:56 CDT`: cancelled pending wrapper `811754` after
      `run-next --dry-run` returned `no_pending_runs` for
      `casp16_server_protein_v2_aliasfix`; the hydrophobic-leader row remains a
      deferred ablation, not queued compute.
    - `2026-07-06 17:11 CDT` live check: the active nofail dev row has 39/165
      CIFs; the v1 terminal-tag attack seed counts are `98/98/13/0/0`. A
      bounded v2 QSglob probe on the eight completed oligo targets with
      references produced 8 scorer-ok rows but only one nonzero target
      (`T1249V1O=0.096`). This is not enough evidence to launch the planned
      25-seed budget before the full v2 dev row is scored.
    - `2026-07-06 17:16 CDT`: added and exercised filtered scoring with
      `./casp16 score --run-id ... --output-dir diagnostics/...` so the active
      v2 dev row can be read without mixing in pending attack rows. The partial
      filtered output at
      `diagnostics/score_probes/server_v2_partial_filtered/target_scores.csv`
      has domain `13 ok / 32 missing_prediction / 26 missing_reference`,
      partial fixed mean `0.049685`, and oligo `8 ok / 82 missing_prediction /
      14 missing_reference`, with only `T1249V1O=0.096` nonzero. This remains
      diagnostic only until the 165-job run completes.
    - `2026-07-06 17:25 CDT`: added the scoreable-subset MSA attack and
      append-only superseded the old full-input attack row. The existing Slurm
      wrapper job `811751` still calls `run-next`, but `run-next --dry-run`
      now selects
      `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`
      after the active v2 dev row clears. The hydrophobic-leader row is
      append-only deferred.
    - `2026-07-06 17:36 CDT`: cancelled the active full-input v2 dev Slurm job
      `810938` after it spent extended GPU time on `T1295`, which is
      `no_reference_pdb` locally. The row is append-only marked
      `cancelled:scoreable_subset_attack`, and dependency was cleared from
      wrapper job `811751`; it is now pending on normal Slurm priority and will
      launch the scoreable attack through `run-next`.
    - `2026-07-06 17:37 CDT`: wrapper job `811751` started on `c636-072` and
      selected the scoreable attack. The Protenix log confirms
      `inputs.msa-reuse.json`, reports that MSA results do not need updating,
      and starts inference at `T0206` as job `1/74`.
    - `2026-07-06 18:25 CDT` live check: terminal-tag attack seed counts are
      `98/98/67/0/0`; scoreable v2 attack has 20/74 seed-101 CIFs and no later
      seeds have started. The hydrophobic-leader wrapper job `811754` was
      cancelled before launch because v2 `run-next --dry-run` now returns
      `no_pending_runs`.
22. Installed OpenStructure 2.11.1 in the isolated conda env
    `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob` and configured
    `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost` as the
    default QSglob-compatible scorer.
    - `ost compare-structures --qs-score` is available and writes parseable
      JSON.
    - A real H0220 probe against reference `9h1g.cif` returned `status=ok`,
      `metric=QSglob`, and `score=0.000000` because model chains `A/B` did not
      map to the reference chem groups.
    - Interpretation: the scorer is no longer missing; assembly/chain mapping
      is the next blocker for trustworthy server-oligo ranking.
23. Ran a bounded QSglob signal probe on six oligo targets across the four
    completed `casp16_server_protein_v1` Protenix dev runs, without overwriting
    checked-in leaderboard artifacts.
    - Baseline: `H0222=0.075`, `T1249V1O=0.090`; `H0220=0.000` with chains
      `A/B` unmapped.
    - Terminal-tag cleanup: `H0222=0.076`, `H1232=0.013`,
      `T1249V1O=0.122`.
    - Oversize fallback: `H0222=0.080`, `H1232=0.032`,
      `T1249V1O=0.099`.
    - Antibody Fv cleanup: `H0222=0.037`, `T1249V1O=0.125`.
    - Interpretation: QSglob can produce nonzero strategy deltas, so it is
      useful for triage. Do not regenerate the official oligo leaderboard while
      `server_attack_protenix_terminal_tag_seed101_105` is partial, and do not
      treat zeros with empty chem mappings as model-quality evidence.
24. Audited the active `protenix5` attack budget execution. The run spec passes
    `-s 101,102,103,104,105`, and Protenix source confirms this is parsed as a
    comma-separated seed list. The runner then loops serially over seeds and
    targets, so the live output can remain partial for a long time while each
    seed pass finishes.
    - Live observation: Slurm job `810719` is running on `c639-072`; the latest
      count had 98 `seed_101` CIFs and 79 `seed_102` CIFs.
    - Guard: do not score `server_attack_protenix_terminal_tag_seed101_105` as
      a complete attack row until candidates for all declared seeds are present,
      or explicitly mark the row partial/unranked.
    - If the job approaches the 48-hour Vista wall-time limit before completing
      all seeds, create a predeclared seed-sharded continuation rather than
      rerunning the monolithic command and overwriting existing candidates.
25. Audited the multi-seed selector path against the live Protenix output
    layout. Real outputs use
    `protenix-v2/<target>/seed_<seed>/predictions/<target>_sample_0.cif` plus
    `<target>_summary_confidence_sample_0.json`, matching the scorer's
    confidence lookup. Added a regression test that builds this layout across
    multiple seeds and verifies that `prediction_candidate_index` plus
    `protenix_confidence_v1` selects the highest confidence candidate for the
    requested target only.
    - This changes no score and does not make the partial attack run ranked.
    - The current `protenix5` budget remains a starter attack tier; if we need
      winner-scale compute, create a separate locked budget such as
      `protenix25` or an ensemble tier before scoring.
26. Created the planned `casp16_server_attack_protenix25` budget as the next
    winner-scale candidate tier, without queuing a run. It targets
    `casp16_server_protein_v2_aliasfix`, declares seeds `101..125`, keeps one
    sample per seed, and uses the same `protenix_confidence_v1` selector.
    - Execution policy: five predeclared five-seed shards, merged only after
      all 25 candidates per target exist.
    - Gate: score the active `protenix5` attack and the v2 alias-fixed
      `dev_fixed` baseline first, then decide whether the 25-seed GPU spend is
      justified.
    - This is not a new leaderboard score and does not change any completed
      run's budget tier.
27. Added the concrete `protenix25` shard manifest
    `attack_budgets/casp16_server_attack_protenix25_shards.tsv`. It fixes five
    planned shard run ids, each shard's seed range, the v2 coverage/stoich input
    artifact, and `protenix_confidence_v1` as the selector.
    - The shard rows are not registered in `runs/manifest.tsv`, so they cannot
      be accidentally selected by `run-next` or scored as missing predictions.
    - When the launch gate opens, create run specs from the shard TSV rather
      than inventing seeds or input artifacts on the fly.
28. Generated, then later superseded,
    `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` as the
    next v2 `dev_fixed` construct-cleanup ablation. It starts from
    `yang_oligo_stoichiometry_token_safe_v1` v2 inputs and applies the existing
    sequence-only low-complexity terminal cleanup.
    - Generation summary: 163 jobs, 264 protein sequences audited, 27 changed
      sequences across 21 targets.
    - Notable edited classes: terminal His/expression tags on `T1201/T1266`
      phase aliases, low-complexity complex segments on
      `H0217/H0272/H1217/H1272` phase aliases, and H1258/H0258/H2258 tag
      cleanup.
    - Supersession: the current queue should prefer the oligo-recovery nofail
      stack because this older row lacks protein-oligo sequence recovery.
29. Hardened target_lab Protenix launch scripts for
    `small_complex_stoich_batch_v1`, `domain_fragment_batch_v1`, and
    `h1258_interaction_window_v1` after the small-complex job exposed an
    import-path collision. The scripts now set `PROTENIX_ROOT_DIR`,
    `PROTENIX_DATA_ROOT`, protein-env `PATH`, `PYTHONNOUSERSITE`,
    `Protenix-Insta` `PYTHONPATH`, and CUDA/math-library paths before invoking
    Protenix.
    - This changes no benchmark score and keeps all target_lab outputs
      unranked.
    - It prevents target_lab diagnostics from silently importing OpenDDE's
      `runner.batch_inference` while the ranked Protenix workflows use
      `Protenix-Insta`.
    - Live validation: `target_lab/domain_fragment_batch_v1` job `810862`
      completed on `c622-022` with 12/12 structures and confidence files.
      `SUMMARY.md` and `summary.tsv` are regenerated; keep the result
      target-lab-only until a target-agnostic segmentation rule exists.
30. Generated, then later superseded,
    `server_v2_protenix_yang_coverage_stoich_low_complexity_large_fallback_seed101`
    as the next v2 coverage-recovery ablation. It starts from the v2
    coverage/stoich/low-complexity input and applies the existing
    target-agnostic large-target fallback to all remaining over-token jobs.
    - Before fallback, the v2 stack still had 11 jobs above the Protenix
      2560-token limit: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`,
      `H1272`, `H2217`, `H2258`, `H2272`, and `T1295O`.
    - After fallback, all 163 generated jobs are at or below 2560 tokens.
    - Changed targets: the 11 over-token jobs above.
    - Supersession: keep this older no-over-token row only as an ablation; the
      current queue should spend compute on the oligo-recovery nofail stack.
    - Interpretation: this is a coverage-recovery candidate, not a claim that
      cropped assemblies preserve official oligo fidelity.
31. Added the planned `casp16_server_attack_protenix25_nofail` budget as a
    separate 25-seed attack tier. It uses the same seeds `101..125`, one sample
    per seed, and `protenix_confidence_v1` selector as the existing
    `protenix25` plan, but now points to the MSA-reused no-over-token v2
    fallback input.
    - Shards are locked in
      `attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`.
    - This does not queue or submit any run specs.
    - Launch gate: score the active `protenix5` attack and the current
      oligo-recovery nofail v2 dev row first, unless a recorded supersession
      decision says otherwise.
32. Generated, then later superseded,
    `server_v2_attack_nofail_protenix5_seed101_105`, the first
    five-candidate attack run spec for the v2 no-over-token stack. It uses
    seeds `101,102,103,104,105`, one sample each, and
    `protenix_confidence_v1` selection.
    - Input: `yang_coverage_stoich_low_complexity_large_fallback_v1`, 163 jobs
      and 0 jobs above the Protenix 2560-token limit.
    - Supersession: this older attack input lacks protein-oligo sequence
      recovery. Prefer
      `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`
      unless an explicit ablation requires the older row.
33. Added exact-sequence MSA reuse infrastructure and retargeted the next v2
    attack to it.
    - New CLI: `./casp16 reuse-msa`, which copies only existing Protenix
      `pairedMsaPath` and `unpairedMsaPath` records when the protein sequence
      SHA256 matches exactly.
    - Generated artifact:
      `strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs_msa_reuse_from_dev_seed101.json`,
      SHA256
      `27c60079563457caada08e2b053b5507783a98841206ae2a8c8f83265c7c8316`.
    - Reuse report:
      `msa_reuse_from_dev_seed101.tsv`, SHA256
      `1433b2b6d612289378e9de1b5a7cd90b9eb34e28201d7c014df86d412090e06b`,
      with 268/268 protein-chain MSA paths reused and 0 missing sources.
    - New pending attack:
      `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`;
      the non-reuse predecessor is append-only superseded in `runs/status.tsv`.
    - Planned `casp16_server_attack_protenix25_nofail` shard rows now point to
      the MSA-reuse input so future seed shards do not each repeat the same MSA
      search.
34. Generated and queued the v2 nofail hydrophobic-leader derivative
    `server_v2_protenix_yang_oligo_sequence_stoich_hydrophobic_leader_nofail_msa_reuse_seed101`.
    - Strategy artifact:
      `strategies/yang_oligo_sequence_stoich_low_complexity_hydrophobic_leader_large_fallback_v1/casp16_server_protein_v2_aliasfix/`.
    - It changes exactly 8 protein sequences in 8 jobs:
      `T0240`, `T1210`, `T1240`, `T2210`, `T2240`, `T0240O`, `T1240O`, and
      `T2240O`.
    - Rules are only `trim_n_hydrophobic_leader:29` for the T0240/T1240/T2240
      family and `trim_n_hydrophobic_leader:15` for the T1210/T2210 family.
    - The 165-job input remains nofail under Protenix's token guard: max total
      length 2535, 0 jobs above 2560.
    - MSA reuse report: 260/268 protein chains reused; the 8 changed sequences
      intentionally miss and will run fresh MSA search.
    - This is a queued `dev_fixed` ablation, not an attack-budget result.
35. Added `scoreable_target_subset_v1` to avoid spending repeated MSA/inference
    time on locally unscorable v2 jobs before reference recovery.
    - Source input:
      `strategies/yang_oligo_sequence_stoich_low_complexity_large_fallback_v1/casp16_server_protein_v2_aliasfix/inputs.json`,
      165 jobs.
    - New strategy artifact:
      `strategies/scoreable_target_subset_v1/casp16_server_protein_v2_aliasfix/`,
      74 kept jobs and 91 skipped jobs. A job is kept only if one of its target
      aliases has `reference_status=available` in the fixed benchmark metadata.
    - New run:
      `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`,
      same five-candidate `server_attack` budget and confidence-only selector,
      with 141/141 protein-chain MSA paths reused from `data/msa_cache/index.tsv`.
    - Queue update: the older full-input MSA attack is
      `superseded:scoreable_subset_attack`, and the hydrophobic-leader ablation
      is `deferred:slurm_wrapper_cancelled`. `run-next --dry-run` now reports
      no pending v2 rows while the scoreable-subset attack is running.
    - Follow-up: the full-input v2 dev row reached `T1295`, a local
      `no_reference_pdb` target, and was cancelled after 39/165 CIFs so the
      pending Slurm wrapper can spend the next GH200 slot on the 74-job
      scoreable attack instead.
    - Guardrail: this does not change benchmark scoring. The fixed 175 server
      targets remain in scoring, and skipped no-reference targets score 0
      locally. This is a compute-saving local-measurement tactic, not an
      official server-comparable shortcut.
36. Added the planned scoreable nofail 25-candidate budget:
    `attack_budgets/casp16_server_attack_protenix25_scoreable_nofail.json`.
    - It is not queued. It is the explicit winner-scale successor only if the
      running scoreable `protenix5` row is positive.
    - It predicts the same 74 scoreable jobs, keeps the fixed 175-target
      benchmark scoring set through
      `benchmarks/casp16_server_protein_v2_aliasfix/input_manifest.tsv`, and
      requires complete exact-sequence MSA reuse from `data/msa_cache/index.tsv`.
    - The shard manifest is
      `attack_budgets/casp16_server_attack_protenix25_scoreable_nofail_shards.tsv`,
      with five planned five-seed shards covering seeds `101..125`.
    - The older 165-job `protenix25_nofail` budget remains a full-input
      ablation until local references are recovered.

## Strategy Decision Log

### 2026-07-06 Scoreable-Subset MSA Attack

Decision: for the next v2 `protenix5` attack, run only Protenix jobs that can
currently affect the local score, while keeping the benchmark target set fixed.

Rationale: the active v2 dev run spent substantial time on `T1295`, but
`T1295/T1295O` are `no_reference_pdb` in the local server benchmark. Predicting
such jobs before reference recovery cannot improve the local leaderboard because
missing-reference targets score 0 either way. Exact-sequence MSA reuse removes
the repeated MSA cost for unchanged scoreable jobs; scoreable-subset filtering
removes local no-op prediction cost.

Implementation: `scoreable_target_subset_v1` maps job names through CASP target
aliases and keeps a job only when at least one alias has
`reference_status=available`. The generated v2 artifact keeps 74/165 jobs and
the new run-spec requires complete MSA reuse, with 141/141 protein-chain paths
injected from `data/msa_cache/index.tsv`.

Guardrail: do not interpret this as official server-track completeness. The
fixed benchmark scoring set stays at 175 targets, and skipped no-reference
targets remain 0 locally. Recovering references is still required before a
full official-compatible server claim.

### 2026-07-06 Hydrophobic Leader Nofail Derivative

Decision: create a narrow signal/hydrophobic-leader cleanup branch on top of
the current v2 nofail stack, but keep it behind the active nofail run and the
main MSA-reuse attack decision.

Rationale: CASP16 winner recipes emphasize construct refinement. The current
sequence-only detector finds only T0240/T1210/T1240-style N-terminal leaders
and phase/oligo aliases, so the blast radius is small enough for a full-set
ablation. It does not use references, score tables, or target-score feedback.

Artifact: `inputs.json` hash
`eb7a88498fbf856120b01aaf39d7b8f7f7264d26e31606dff50472f350dc93ee`;
MSA-reuse input hash
`85b452c36b454846c94f781fac43f036aef2484b4699adfff468e27b344500f8`.

Interpretation: this is a real recipe iteration, but it is risky because
leader/signal removal can hurt if CASP's scored construct includes the segment.
Score only by fixed-set means after the full run finishes; do not promote from
a single target.

### 2026-07-06 Attack Budget Execution Audit

Decision: keep `server_attack_protenix_terminal_tag_seed101_105` running, but
treat its current outputs as partial until all declared seeds are present.

Evidence: `run_spec.json` passes `-s 101,102,103,104,105`; Protenix CLI accepts
comma-separated seeds; `runner/inference.py` loops over `for seed in seeds`
outside the target loop. Current output contains complete `seed_101` and
partial `seed_102` directories, which is expected for the serial seed pass and
not evidence that the attack budget failed.

Next action: monitor completion. If wall-time risk becomes real, use an
explicit seed-sharded continuation so the `protenix5` budget remains honest and
resume-safe.

### 2026-07-06 QSglob Signal Probe

Decision: use targeted QSglob probes to guide oligo strategy while avoiding a
checked-in leaderboard rewrite during partial attack inference.

Evidence: six target probes showed nonzero QSglob for `H0222` and `T1249V1O`.
Terminal-tag cleanup improved `T1249V1O` from `0.090` to `0.122`; oversize
fallback improved `H1232` from `0.000` to `0.032`. `H0220` remained a mapping
false-zero risk with model chains `A/B` unmapped.

Next action: let the queued token-safe stoichiometry and v2 coverage runs
finish before spending larger attack compute. In parallel, fix only the
assembly mapping classes that create false zeros; do not sink a long detour
into exhaustive mapping before the current runs report.

### 2026-07-06 QSglob Mapping Diagnostics

Decision: keep OpenStructure QSglob scores official-compatible, but preserve
automatic mapping failures in `target_scores.csv` `message` so false-zero
classes can be triaged.

Implementation: `parse_ost_qs_json` now records unmapped model chains, empty
chain mapping, empty chem mapping, and missing mapped interfaces. `score_target`
keeps `status=ok` and the reported `QSglob` score, including zero, while adding
diagnostic messages such as
`ost_unmapped_model_chains:A,B;ost_empty_chain_mapping`.

Next action: after active jobs finish, rescore server oligo rows and group the
`message` diagnostics to choose target-agnostic mapping fixes. Do not hand-map
individual targets in response to scores.

### 2026-07-06 QSglob Scorer Installed, Mapping Still Open

Decision: use OpenStructure `ost compare-structures --qs-score` as the default
local QSglob-compatible scorer for server protein-oligo targets, but do not
promote oligo claims until assembly/chain mapping has been validated.

Rationale: server oligo ranking must use `QSglob`, not DockQ. Installing the
tool removes the `metric_unavailable` blocker, but a successful H0220 probe
still returned zero because automatic chem/chain mapping failed. That is a
mapping problem, not proof that the model has zero assembly quality.

Budget implication: do not spend larger attack budgets to chase oligo scores
until the scorer maps predicted assemblies correctly. Extra seeds or samples
cannot fix a scoring pipeline that assigns false zeros.

### 2026-07-06 Winner-Budget Reality

Decision: keep single-seed `dev_fixed` runs and multi-candidate `server_attack`
runs as separate leaderboard tiers. The current `protenix5` budget is a
minimal realism check, not an estimate of the true CASP16 winner budget.

Rationale: strong server systems almost certainly generated more than one
internal candidate per target, and official server submissions could include
multiple models. This does not mean the hidden compute is literally a Protenix
seed count; count seeds, samples, backend/model variants, MSA/template variants,
refinement/ranking passes, and submitted models as candidate-budget dimensions.
A real attack row must declare seed list, sample count, backend/model variants,
MSA/template policy, selection rule, and allowed selection signals before
prediction starts.

Next action: compare `dev_fixed` only to `dev_fixed`; compare `server_attack`
only to attack rows and official server groups, with candidate count and GPU
cost displayed.

### 2026-07-06 Phase-2 Alias Reference Gap

Decision: extend target lookup aliases to cover CASP phase ids `0xxx`, `1xxx`,
and `2xxx`, and document the resulting reference/input coverage gain. Do not
regenerate checked-in `casp16_server_protein_v1` artifacts in place.

Rationale: many official server score rows use ids such as `T2201`, `H2202`,
and `T2201O`, while local metadata, sequence records, and PDB references often
live under `T1201`, `H1202`, or `T1201`. Treating these as disconnected makes
local scores artificially sparse.

Evidence: a temporary rebuild outside the repo recovered examples such as
`T2201 -> 8bwd`, `T2206 -> 9cp0`, `H2202 -> 8bwl`, `H2232 -> 9cn2`, and
`H2258 -> 9ci3`. Available references increased from 54 to 79 and generated
Protenix jobs increased from 106 to 163.

Next action: create `casp16_server_protein_v2_aliasfix` or an equivalent
explicit benchmark version before making any serious winner-comparison claim.

Update: `casp16_server_protein_v2_aliasfix` has been generated under
`benchmarks/` and `leaderboards/`. Future winner-comparison runs should target
v2 or a newer explicit server benchmark; in-flight v1 runs remain on v1.

Historical next v2 run:
`server_v2_protenix_yang_coverage_stoich_seed101`, using the v2-regenerated
token-safe stoichiometry strategy, was submitted as Slurm job `810938`.
Current queue state supersedes that run row with the oligo-recovery nofail dev
row, and the `run-next` wrapper is now running the newer input after the Slurm
dependency was cleared.

### 2026-07-06 Coverage + Stoichiometry Attack Candidate

Decision: generate `server_attack_protenix_coverage_stoich_seed101_105` as the
next `protenix5` attack candidate, then supersede it with
`server_attack_protenix_coverage_stoich_msa_reuse_seed101_105` before launch so
the same attack budget does not repeat MSA search. Do not submit it while
`server_attack_protenix_terminal_tag_seed101_105` is still pending/running and
component single-seed coverage runs are still queued.

Hypothesis: multi-seed attack compute should be spent on inputs that remove
known hard zeros first. The stacked input combines sequence recovery,
large-target token fallback, and token-safe oligo stoichiometry, while keeping
the same Protenix model, MSA/template/default-param settings, seeds, sample
count, and confidence-only selector as the first attack.

No-oracle boundary: the input strategy reads benchmark metadata and official
target stoichiometry, but not native structures, official score rows, previous
per-target scores, or reference-derived target tuning. Selection remains
`protenix_confidence_v1` and cannot inspect structure metrics.

Launch gate: submit only after `run-next --dry-run` selects this run, or after
an explicit decision to supersede the earlier single-seed coverage queue. Keep
results in the `server_attack` tier and compare only against other attack rows
and official server groups with the candidate budget displayed.

MSA-reuse successor: the launched candidate should be
`server_attack_protenix_coverage_stoich_msa_reuse_seed101_105`, not the older
non-reuse row. Its run spec keeps the same seeds, sample count, candidate
count, selector, Protenix settings, and input strategy, but injects exact
sequence MSA paths from `data/msa_cache/index.tsv`. Preflight records 180/196
protein-chain MSA paths reused, 16 missing exact-sequence sources, 91.84%
coverage, and 0 stale covered paths; the minimum launch guard is 0.90.

### 2026-07-05 Antibody Fv Target-Lab Branch

Decision: generate `yang_antibody_fv_fragment_inputs_v1` as a target-lab
artifact, not as a ranked server run.

Rationale: the broad dynamic-IDR scan found antibody constant-like C-terminal
regions, but trimming all such regions in a ranked strategy would be too broad
without evidence. The narrower Fv branch uses antibody heavy/light prefixes and
variable-domain terminal motifs to trim only obvious constant regions. It
changes 8 antibody-antigen jobs and 16 antibody chains while preserving antigen
chains unchanged.

Use this branch to test whether Fv-only constructs improve antibody-antigen
assembly behavior. Any leaderboard-facing promotion must become a predeclared
target-agnostic antibody-complex rule and run across the full eligible set.

Result: target-lab run `targetlab_protenix_yang_antibody_fv_seed101` completed
as Slurm job `811918` with 8/8 CIFs in 6 minutes 22 seconds. Confidence is not a
quality score, but it gives useful triage: `H0233__fv` and `H1233__fv` show the
clearest antigen-to-antibody pair ipTM signal, while the H0222/H0223/H0225
family mostly has strong heavy-light confidence and weaker antigen-antibody
pair confidence. Keep this as O5 target-lab evidence only.

Diagnostic DockQ then succeeded for all 8 Fv jobs. Total DockQ mean was
`0.497250`, with strong positives on `H0233__fv=0.916000` and
`H1233__fv=0.891000`, a moderate `H1225__fv=0.538000`, and mixed weaker cases
on the H0222/H0223/H0225 families. This upgrades O5 from confidence-only
evidence to real target-lab interface evidence, but it still cannot be used as
a server leaderboard score because official oligo ranking requires QSglob and a
target-agnostic full-benchmark rule.

### 2026-07-05 Antibody Fv Full-Set Candidate

Decision: generate and queue `yang_antibody_fv_cleanup_v1` as a full-set,
sequence-only server benchmark candidate behind the baseline and lower-risk
terminal-tag cleanup.

Rationale: O5 needs a leaderboard-compatible path, not only changed-target
diagnostics. The full-set candidate preserves all 106 server jobs and original
target IDs, audits 172 protein chains, and trims 16 antibody heavy/light
constant regions across 8 antibody-antigen targets. This keeps the benchmark
coverage fixed while testing the Fv construct hypothesis.

Launch gate: run with the same Protenix/MSA/template/seed/sample budget only
after the current baseline frees the GH200 and the conservative tag-cleanup
ablation has either run or been intentionally skipped.

Result: `server_protenix_yang_antibody_fv_cleanup_seed101` finished the full
106-job server Protenix benchmark with 98 CIFs. The same 8 jobs hit the
`n_token > 2560` guard as the baseline. Ranked domain mean was `0.060677`,
below the baseline `0.063962` and below the terminal-tag cleanup `0.066908`.
The main regressions were `T0234`, `T1234`, and `T1298`; small gains over the
terminal-tag run on `T1249V1` and `T1299` did not offset them.

Interpretation: this is a negative `dev_fixed` result for the ranked domain
track. It does not prove antibody Fv cleanup is bad for oligos, because the
main antibody targets produced predictions but the old rows were
`metric_unavailable` before QSglob installation. Do not promote this strategy
to a multi-seed `server_attack` budget until QSglob mapping, or another locked
official-compatible oligo scorer, is validated.

### 2026-07-05 Terminal Tag + Antibody Fv Stack

Decision: generate and queue `yang_terminal_tag_antibody_fv_cleanup_v1` as a
full-set sequence-only combined construct-cleanup run behind the individual
ablations.

Rationale: terminal expression tags and antibody constant-region cleanup touch
non-overlapping target groups in `casp16_server_protein_v1`. The combined input
preserves all 106 server jobs, audits 172 protein chains, and changes 23
protein sequences across 15 targets. This is a cheap way to test whether two
winner-style construct adjustments compose without changing benchmark
eligibility.

### 2026-07-06 Oversize Domain Monomer Fallback

Decision: generate and queue `yang_oversize_domain_monomer_fallback_v1` ahead
of the remaining construct ablations.

Rationale: the full Protenix baseline lost 8 jobs to the Protenix
`n_token > 2560` guard. Seven failures are multi-entity oligo or complex cases
that need a more explicit split policy. One failure, `T1295`, is a
`protein_domain` job with a single protein entity expanded to `A8`, totaling
3752 residues. The fallback preserves the fixed target set and run budget but
changes that one domain job to a single representative chain, reducing it to
469 residues. This is sequence/metadata driven and does not read references,
official score tables, or previous target scores.

Launch gate: queue with the same Protenix/MSA/template/cache/fusion/seed/sample
budget after the terminal-tag ablation, before broader construct cleanup runs.

Result: the run finished the full 106-job server Protenix benchmark with 99 CIF
files. `T1295` was rescued at inference time, but it remains `missing_reference`
in the local server benchmark and therefore contributes `0` to the fixed
71-target domain mean. The scored domain mean was `0.065114`, better than the
baseline `0.063962` but below the terminal-tag cleanup `0.066908`. `T1295O` and
the six large `H*` complex failures still hit the `n_token > 2560` guard.

Interpretation: this is a useful coverage repair and a guardrail for future
large-target handling, but not enough to promote to a realistic server-attack
budget. Before spending multi-seed compute, fix the pieces that more seeds
cannot solve: reference/domain mapping, QSglob availability, and a predeclared
split policy for oversize complexes.

### 2026-07-05 Epitope/TEV Tag Full-Set Candidate

Decision: queue `yang_epitope_tag_cleanup_v1` as a full-set sequence-only
server benchmark candidate behind the lower-risk construct ablations.

Rationale: H1258/H0258-style inputs include obvious epitope/His/TEV expression
prefixes not covered by the conservative terminal-tag cleanup. The strategy
preserves all 106 server jobs, audits 172 protein chains, and changes 11
protein sequences across 9 targets without reading references or scores.

Launch gate: run only after the queued terminal-tag, antibody-Fv, and combined
construct ablations unless the queue is intentionally reprioritized.

### 2026-07-06 Full Protenix Server Baseline

Decision: treat `server_protenix_full_msa_template_seed101` as the first real
server-track baseline, but not as evidence that the model is intrinsically
weak.

Result: the ranked domain mean is `0.063962`, far below the server-domain
champion comparator `110s` at `0.923321`. Only 15/71 domain rows scored
successfully; 30 targets lacked predictions in the fixed official domain set,
and 26 had no local native reference mapping. The oligo track remains unranked
in the checked-in artifacts until QSglob mapping is validated and the run is
rescored.

Interpretation: the largest immediate gaps are coverage and benchmark
compatibility, not only structure quality. Inference produced 98/106 CIFs; the
8 missing jobs all exceeded Protenix's `n_token > 2560` guard. This makes a
large-target split/fallback recipe a priority after the currently running
construct ablations.

### 2026-07-06 Protein-Oligo Sequence Recovery

Decision: generate two v2 alias-fixed protein-oligo input-repair artifacts:
`yang_protein_oligo_sequence_recovery_v1` and
`yang_protein_oligo_sequence_stoich_token_safe_v1`.

Rationale: the QSglob probe made `H0220` look like a pure scorer mapping
false-zero, but the v2 server inputs also exposed a more basic prediction
problem: several `H*220` protein-oligo rows were represented by short
RNA-like records, while the official sequence archive contains protein-like
records through the target aliases. This is not a score-driven rescue; it is a
target-agnostic alias/sequence-family recovery step using official sequence
metadata that is allowed at prediction time.

Artifact summary: protein-oligo sequence recovery changes 5 targets
(`H0220`, `H1213`, `H1220`, `H2213`, `H2220`) and increases the generated
v2 job count from 163 to 165. The composed sequence + token-safe stoichiometry
artifact changes 15 targets total, restores `H1220/H2220` as recovered protein
assemblies with `A1B4` stoichiometry, and skips 8 recovered exact-stoichiometry
cases that would exceed Protenix's 2560-token limit.

Interpretation: this should be queued only as a full-benchmark strategy or
composed with the no-over-token fallback stack. It is not itself a
no-over-token artifact because unrelated existing v2 jobs such as `H0272` still
exceed the Protenix token limit. It is also not winner-comparable on a single
seed; any serious claim still needs a separate predeclared multi-candidate
attack budget.

### 2026-07-06 Oligo-Recovery Nofail V2 Stack

Decision: compose the protein-oligo sequence/stoichiometry fix with
low-complexity cleanup and large-target fallback, then register both a
single-seed `dev_fixed` run and a five-candidate `server_attack` run.

Rationale: the previous no-over-token v2 stack fixed hard Protenix failures
but still used the older input modality for `H0220/H1220/H2220`-style targets.
Spending multi-candidate attack budget on that older stack would answer the
wrong question. The new artifact keeps recovered protein oligo inputs, keeps
token-safe exact stoichiometry, and still avoids every `n_token > 2560` hard
failure.

Artifact summary:

- Intermediate low-complexity artifact:
  `yang_oligo_sequence_stoich_low_complexity_v1`, 165 jobs, 27 changed
  sequences across 21 targets, output SHA256
  `a9c6ab39024c483ec760122e47386f061503d4142320b0e0fa0f9df427d3f74b`.
- Final no-over-token artifact:
  `yang_oligo_sequence_stoich_low_complexity_large_fallback_v1`, 165 jobs,
  11 fallback-changed targets, max job 2535 tokens, 0 jobs above 2560, output
  SHA256 `9ea5de4ffa1f7693de8f7e61374c0e51d0c54760f8efeea9839de9005a21f54e`.
- New `dev_fixed` run spec:
  `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`.
- New `server_attack` run spec:
  `server_v2_attack_oligo_recovery_nofail_protenix5_seed101_105`, seeds
  `101..105`, candidate_count `5`, selector `protenix_confidence_v1`.
- MSA-reuse successor run spec:
  `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`,
  same declared budget and selector, but using
  `inputs_msa_reuse_from_dev_seed101.json` so Protenix can skip MSA search for
  exact sequence matches. This full 165-job row is now superseded by the
  scoreable-subset run until missing references are recovered.
- Scoreable-subset MSA-reuse successor run spec:
  `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`,
  same declared budget and selector, but using only the 74 jobs from the v2
  nofail stack that can currently affect local score. Its run-spec reuses
  141/141 protein-chain MSA paths and requires complete reuse.

Interpretation: this is the current best v2 input stack to spend future attack
compute on. The local-measurement attack should use the scoreable subset while
references are incomplete; the older full-input attack rows should be treated
as ablations unless reference recovery makes them scoreable.

### 2026-07-06 Exact-Sequence MSA Reuse

Decision: optimize repeated MSA cost by reusing only exact protein-sequence MSA
paths across Protenix runs.

Rationale: Protenix already skips MSA search when `pairedMsaPath` or
`unpairedMsaPath` exists in `inputs-update-msa.json`. `--enable_cache true`
does not make a new run reuse another run's MSA artifacts, so attack rows and
seed shards can waste hours on identical searches unless the paths are carried
forward explicitly.

Implementation: `./casp16 reuse-msa` builds a new input JSON plus TSV audit by
sequence SHA256, not target id. `./casp16 build-msa-cache` now writes a reusable
index from completed run-local `inputs-update-msa.json` files, and `run-spec`
can inject that index with a complete-coverage guard. For the scoreable v2
attack subset, the current dev row provides valid MSA paths for 141/141 protein
chains.

Guardrail: this is infrastructure only. It does not disable MSA, does not read
references or scores, and does not change benchmark eligibility or scoring.
Any sequence edit, trim, recovery, or window that changes the SHA256 must miss
the cache and run a fresh MSA search.

Additional queued v1 reuse: `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105`
is now the MSA-reuse successor for the v1 coverage+stoich `protenix5` attack.
It reuses 180/196 exact-sequence protein-chain MSA paths, has 16 changed/new
chains without cache hits, and supersedes the non-reuse predecessor before any
Slurm submission.

### 2026-07-06 Small Complex Target-Lab Result

Decision: keep exact-stoichiometry promotion alive, but do not promote the
hard-coded H1258 interaction window.

Result: `target_lab/small_complex_stoich_batch_v1` completed 6/6 Protenix jobs
with structure and confidence files. Diagnostic DockQ succeeded for three
cached-reference targets:

- `H1233`: DockQ `0.850`, pLDDT `91.317`, pTM `0.824`, ipTM `0.792`.
- `H1236`: DockQ `0.206`, pLDDT `73.302`, pTM `0.369`, ipTM `0.318`.
- `H1232`: DockQ `0.023`, pLDDT `87.842`, pTM `0.653`, ipTM `0.553`.

`H1244` and `H1267` produced confident structures but lack cached target-lab
references. The H1258 LRRK2-window job produced a structure with high
confidence (pTM `0.781`, ipTM `0.682`) but DockQ failed chain mapping against
the native reference, so it is not a positive scoring result.

Interpretation: exact stoichiometry can produce real complex signal on at
least one compact antibody/complex case (`H1233`), but confidence alone is not
reliable (`H1232` is high-confidence and poor DockQ). The next full-benchmark
move should remain target-agnostic exact-stoich plus QSglob/chain-mapping work,
not a hard-coded H1258 residue window.

### 2026-07-06 Protenix CUDA Bootstrap Fix

Decision: harden generated `run.sh` files to load or infer CUDA before importing
Protenix.

Rationale: the first terminal-tag cleanup launch failed before inference with
`CUDA_HOME environment variable is not set` and `libcudart.so.12` missing. The
run scripts now try `module load cuda/12.5`, fall back to `cuda/12.4`, infer
`CUDA_HOME` from TACC/NVHPC variables or known Vista paths, and add CUDA runtime
and NVIDIA math libraries to `LD_LIBRARY_PATH`, `LIBRARY_PATH`, and `CPATH`.

Outcome: the terminal-tag cleanup relaunch reached Protenix environment
initialization and MSA search under the same fixed inference budget.

### 2026-07-06 V2 Nofail Baseline Launch

Decision: remove the dependency from Slurm job `810938` so the current
alias-fixed v2 no-over-token baseline starts immediately instead of waiting for
the older v1 terminal-tag attack to finish.

Evidence: `run-next --benchmark casp16_server_protein_v2_aliasfix --dry-run`
selected
`server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`.
After `scontrol update JobId=810938 Dependency=`, `squeue` showed job `810938`
running on `c619-011`, and `list-runs` marked that v2 nofail run as `running`.

Interpretation: this keeps the main line aimed at the strongest runnable v2
input stack. The result is still `dev_fixed` only: one seed, one sample, and
`first_output_only`.

### 2026-07-06 Protenix25 Nofail Budget Retarget

Decision: update the planned `casp16_server_attack_protenix25_nofail` budget
to use the current MSA-reused oligo-recovery nofail input artifact.

Change: the JSON and shard TSV now point at
`inputs_msa_reuse_from_dev_seed101.json`, with 165 jobs, input hash
`27c60079563457caada08e2b053b5507783a98841206ae2a8c8f83265c7c8316`,
manifest hash
`3199521f45afdec9127f9728b870b73810faa05eae2e42659e830ac8ffab31c2`, and
25 declared candidates per target across five fixed seed shards. The reuse
report records 268/268 exact-sequence protein-chain MSA paths reused.

Interpretation: if the v2 nofail baseline earns a larger attack budget, the
25-seed path will spend compute on the latest protein-oligo sequence recovery
stack rather than the older coverage/stoich-only nofail artifact, while avoiding
duplicate MSA search across shards. This does not queue or submit the 25-seed
run.

### 2026-07-06 Seed-Shard Merge Path

Decision: add `./casp16 merge-shards` so a future 25-candidate attack can be
scored as one declared budget after all five seed shards finish.

Rationale: individual five-seed shards should remain `partial_candidates`
against a 25-candidate budget. The merge command symlinks completed shard
prediction files into one registered run, preserves per-target confidence JSON
discovery, records `source_run_ids`, and exposes the merged `candidate_count`
for scoring.

Interpretation: this closes the planned `protenix25` execution loop without
launching any extra GPU work or weakening the fail-closed partial-candidate
rule.

### 2026-07-06 Server Score Targets Pinned

Decision: add `docs/SERVER_SCORE_TARGETS.md` as the fixed score target for the
autoresearch loop.

Evidence: the document is derived from
`leaderboards/casp16_server_protein_v2_aliasfix/official_groups.csv` and
`leaderboards/casp16_server_protein_v1/runs.csv`. The official server leaders
to beat are domain group `110s` with fixed GDT_TS mean `0.923321` and oligo
group `456s` with fixed QSglob mean `0.582615`. The best current local full
Protenix row remains `server_protenix_yang_terminal_tag_cleanup_seed101`, with
domain mean `0.066908` and oligo mean `0.045865`.

Interpretation: this makes the gap explicit and keeps future agent iterations
from treating target-lab wins, partial multi-seed outputs, confidence-only
selection, or DockQ-only oligo diagnostics as server-leaderboard progress.

### 2026-07-06 Terminal Tag Cleanup Result

Decision: keep `yang_terminal_tag_cleanup_v1` as a weak positive construct
cleanup signal, but do not promote it to the realistic attack-budget tier yet.

Result: `server_protenix_yang_terminal_tag_cleanup_seed101` finished the full
106-job server Protenix run with 98 CIFs, matching the baseline coverage. The
ranked domain mean increased from `0.063962` to `0.066908`. The largest target
improvements were `T1234` `+0.1122`, `T1298` `+0.0863`, and `T1210`
`+0.0519`; smaller regressions on `T0234`, `T1249V1`, and `T1299` limited the
net gain.

Interpretation: terminal-tag cleanup is not a path to the server champion by
itself. It gives a small positive single-seed signal while leaving the same
8 hard `n_token > 2560` failures. The next priority is coverage recovery for
hard zero targets, starting with the conservative `T1295` domain fallback.

### 2026-07-05 Dynamic Terminal IDR Scan

Decision: do not implement the first dynamic terminal-IDR cleanup heuristic as
a strategy artifact.

Rationale: a sequence-only scan for 60-220 residue terminal disorder-like
segments found 26 candidate protein chains, but the first heuristic was too
broad. It would trim antibody constant-like C-terminal regions in
H0222/H0223/H0225/H1222/H1223/H1225, trim T0240/T1240 C-terminal sequence that
overlaps CASP domain-summary regions, and trim H0272/H1272 poly-alanine/signal
like prefixes. That is too much risk for a ranked server-style rerun.

Useful follow-up:

- split this idea into narrower target-lab branches: antibody/Fv construct
  trimming for the H1222/H1223/H1225 family, and predeclared sequence-only
  terminal-disorder cleanup for long monomers only.
- keep `yang_domain_fragment_inputs_v1` as the safer way to study domain
  decomposition, because it is explicitly marked target-lab and post hoc.
- do not queue a broad dynamic-IDR cleanup run until the rule avoids antibody
  constant regions, avoids known domain-core overlap, and changes only a small
  auditable target set.

## Promotion Rules

- A target_lab improvement is not a leaderboard improvement.
- A manual rescue is not a server-style result unless it becomes an automatic
  target-agnostic rule.
- Confidence can help analyze failures, but it is never a quality score.
- If a trick changes target eligibility, budget, metric identity, or model
  selection policy, create a new benchmark version.
