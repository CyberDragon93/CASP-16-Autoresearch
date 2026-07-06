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
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `casp16_server_protein_v1` | pending behind terminal-tag cleanup | single-entity oversize domain fallback to recover the known `T1295` token-limit zero | yes, after predictions and scoring |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | pending behind terminal-tag cleanup | full-set antibody Fv constant-region cleanup rerun | yes, after lower-risk cleanup ablation |
| `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | pending behind individual ablations | combined terminal-tag plus antibody-Fv cleanup rerun | yes, after individual ablations |
| `server_protenix_yang_epitope_tag_cleanup_seed101` | `casp16_server_protein_v1` | pending behind combined cleanup | broader epitope/His/TEV tag cleanup rerun | yes, after lower-risk construct ablations |

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
- Baseline inference generated 98/106 CIFs. The 8 failed Protenix jobs were
  all `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`,
  `H1258`, `H1272`, and `T1295O`.

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
3. Run queued `server_protenix_yang_oversize_domain_monomer_fallback_seed101`
   to recover the known `T1295` server-domain token-limit failure. The strategy
   preserves all 106 server jobs, changes only `T1295` from `A8` to one
   representative chain, and keeps MSA/templates/default params/seed/sample
   fixed. This is the first coverage-recovery run after terminal-tag cleanup
   because missing predictions score as zero.
4. Run queued `server_protenix_yang_antibody_fv_cleanup_seed101` as the first
   full-set antibody construct attempt after the lower-risk terminal cleanup.
   It preserves all 106 server jobs while trimming 16 antibody constant-region
   chains across 8 antibody-antigen targets. Cache, fusion, and TF32 are
   enabled to match the baseline engine flags.
5. Run queued `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101`
   after the two individual ablations to test whether their non-overlapping
   construct changes compose on the full server target set.
6. Run queued `server_protenix_yang_epitope_tag_cleanup_seed101` after the
   lower-risk construct ablations. It changes 11 sequences across 9 targets,
   including H1258/H0258-style epitope/His/TEV prefixes, while matching the
   baseline MSA/template/cache/fusion/seed/sample budget.
7. Install OpenStructure `ost` or an equivalent `QSglob` scorer, then rescore
   the oligo track.
8. Start target_lab loops on H1258 and H1232 only as diagnostics for
   stoichiometry/construct tricks; promotion requires a target-agnostic full
   benchmark rerun.
9. Add domain cropping and chain/residue mapping before drawing conclusions
   from hard multi-domain domain targets.
10. Design a broader `yang_large_target_split_or_fallback_v1` only after the
    conservative `T1295` fallback is scored. Multi-entity oligo/domain failures
    still need a separate predeclared split rule or a new benchmark version.

## Strategy Decision Log

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
budget after the individual terminal-tag and antibody-Fv ablations.

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
