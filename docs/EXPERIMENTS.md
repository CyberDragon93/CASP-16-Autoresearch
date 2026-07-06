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
| `server_attack_protenix_terminal_tag_seed101_105` | `casp16_server_protein_v1` | Slurm job `810719` running | five-seed terminal-tag cleanup attack run with predeclared confidence-only model selection | attack tier only |
| `server_protenix_yang_large_target_split_or_fallback_seed101` | `casp16_server_protein_v1` | pending behind attack job | predeclared token-budget fallback for all eight Protenix `n_token > 2560` failures | yes for domain track, coverage-recovery caveat |
| `server_protenix_yang_sequence_recovery_seed101` | `casp16_server_protein_v1` | pending behind active jobs | recover missing/misparsed protein-domain sequences on top of terminal-tag cleanup | yes for domain track, coverage-recovery caveat |
| `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `casp16_server_protein_v1` | pending behind active jobs | stack sequence recovery with token-budget fallback before larger attack budgets | yes for domain track, coverage-recovery caveat |
| `yang_oligo_stoichiometry_recovery_v1` | `casp16_server_protein_v1` | artifacts generated, not queued | restore official oligo copy counts that collapsed to one copy per entity | not queued until token-safe/windowed derivative exists |
| `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `casp16_server_protein_v1` | pending behind active jobs | exact stoichiometry for under-budget oligo jobs on top of stacked coverage recovery | yes for domain track; oligo diagnostic until QSglob exists |
| `server_attack_protenix_coverage_stoich_seed101_105` | `casp16_server_protein_v1` | queued, not submitted | five-seed attack run on stacked sequence-recovery, token-fallback, token-safe stoichiometry inputs | attack tier only |
| `target_lab/h1258_interaction_window_v1` | target_lab only | artifact generated, not submitted | public LRRK2 interaction-window reproduction for H1258 | not rank eligible |
| `target_lab/small_complex_stoich_batch_v1` | target_lab only | Slurm job `810824` pending | compact exact-stoich and H1258-window learning batch | not rank eligible |
| `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | deferred | combined terminal-tag plus antibody-Fv cleanup rerun | do not launch before QSglob or a positive antibody signal |
| `server_protenix_yang_epitope_tag_cleanup_seed101` | `casp16_server_protein_v1` | deferred | broader epitope/His/TEV tag cleanup rerun | do not launch before a predeclared large-target split policy |

## Current Score Truth

- Server domain comparator to beat: `110s`, fixed mean `0.923321`, metric
  `GDT_TS`, 71 targets.
- Server oligo comparator to beat: `456s`, fixed mean `0.582615`, metric
  `QSglob`, 104 targets.
- Current local server diagnostic reuse: domain `0.036428`, oligo `0.000000`.
  The main deficit is coverage and missing QSglob, not just model quality.
- Current full Protenix server baseline: domain `0.063962`, with 15 ok, 30
  missing predictions, and 26 missing references over the fixed 71-domain
  target set. Oligo is still unranked because QSglob is unavailable.
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
  `0.066908`. It predicted the main antibody oligo targets, but local QSglob
  is unavailable, so this is not evidence to spend multi-seed attack compute.
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
     and `H1225` produced predictions, but all remain `metric_unavailable`
     until QSglob is installed.
5. Defer `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101`.
   There is no reason to spend another full benchmark on the stacked run before
   either QSglob can evaluate antibody oligos or antibody cleanup shows a
   positive signal.
6. Defer `server_protenix_yang_epitope_tag_cleanup_seed101`. The current hard
   zeros are dominated by token-limit failures; a predeclared large-target
   split/fallback policy is higher priority than another ad hoc construct
   cleanup.
7. Install OpenStructure `ost` or an equivalent `QSglob` scorer, then rescore
   the oligo track.
8. Created `server_attack_protenix_terminal_tag_seed101_105`, the first
   multi-candidate attack run. It keeps terminal-tag cleanup inputs, uses seeds
   `101,102,103,104,105`, one sample each, and selects by
   `protenix_confidence_v1`. It is attack-tier only.
   - Submitted to Vista GH200 as Slurm job `810719` at `2026-07-06T15:29Z`;
     initial queue state was `PENDING (Priority)`.
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

## Strategy Decision Log

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

Next v2 run: `server_v2_protenix_yang_coverage_stoich_seed101`, using the
v2-regenerated token-safe stoichiometry strategy, is Slurm job `810938` and
should run after the active v1 attack job `810719`.

### 2026-07-06 Coverage + Stoichiometry Attack Candidate

Decision: generate `server_attack_protenix_coverage_stoich_seed101_105` as the
next `protenix5` attack candidate, but do not submit it while
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
main antibody targets produced predictions but remain `metric_unavailable`
without QSglob. Do not promote this strategy to a multi-seed `server_attack`
budget until QSglob or another locked official-compatible oligo scorer is
available.

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
because QSglob is unavailable.

Interpretation: the largest immediate gaps are coverage and benchmark
compatibility, not only structure quality. Inference produced 98/106 CIFs; the
8 missing jobs all exceeded Protenix's `n_token > 2560` guard. This makes a
large-target split/fallback recipe a priority after the currently running
construct ablations.

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
