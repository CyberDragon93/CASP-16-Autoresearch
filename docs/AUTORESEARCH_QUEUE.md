# CASP16 Autoresearch Queue

This queue turns winner-recipe notes into executable full-benchmark attempts.
The queue is allowed to change quickly; benchmark definitions are not.

## Next To Run

| Priority | Run | Benchmark | Status | Why It Matters | Next Gate |
| --- | --- | --- | --- | --- | --- |
| P0 | Validate OpenStructure `ost` QSglob mapping | `casp16_server_protein_v2_aliasfix` | scorer installed; six-target probe has nonzero signal plus H0220 false-zero risk | Required to compare the 104 official server oligo targets and judge antibody-complex strategies | Add or validate assembly/chain mapping for false-zero classes, then rerun `./casp16 score` and `./casp16 leaderboard` after active runs finish |
| P1 | Run `server_attack_protenix_terminal_tag_seed101_105` | separate from `dev_fixed` | Slurm job `810719` running; currently serial seed loop on `seed_101` | Winner-level server comparison should not pretend one seed/sample is enough | Monitor GH200 job, then score with `protenix_confidence_v1` only after all declared seeds are present; partial rows stay unranked |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `casp16_server_protein_v1` | pending behind attack job | Extra seeds cannot fix `n_token > 2560` hard failures | Submit after attack job `810719` completes if coverage recovery remains highest leverage |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Several domain hard zeros are local sequence parsing/alias failures, not model failures | Submit after attack and large-target fallback jobs; expect more jobs but better domain coverage |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Combine the two coverage fixes before spending larger attack budgets | Submit after the attack and component coverage runs unless their results make the stack unnecessary |
| P5 | `yang_oligo_stoichiometry_recovery_v1` derivative | `casp16_server_protein_v1` | artifacts generated, not queued | Several oligo inputs silently use one copy per entity despite official A/B copy counts | Build token-safe or windowed derivative before queuing a full run |
| P6 | `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Restores exact stoichiometry for 5 under-budget oligo jobs without reintroducing token-limit failures | Submit after active pending jobs if exact stoichiometry remains the next oligo signal |
| P7 | `server_attack_protenix_coverage_stoich_seed101_105` | separate from `dev_fixed` | queued, not submitted | Same five-candidate attack budget as terminal-tag attack, but spent on inputs with sequence recovery, token fallback, and token-safe stoichiometry | Submit only when `run-next --dry-run` selects it, or supersede after component single-seed evidence |
| done | `casp16_server_protein_v2_aliasfix` | new benchmark version | generated | `2xxx` score-table rows inherit references/sequences from matching metadata; refs improved 54 -> 79 and jobs 106 -> 163 | Use for future winner-comparison runs; do not rewrite v1 |
| P9 | `server_v2_protenix_yang_coverage_stoich_seed101` | `casp16_server_protein_v2_aliasfix` | Slurm job `810938` pending on dependency `810719` | First alias-fixed full benchmark run using the current strongest coverage + token-safe stoichiometry input | Score before launching larger v2 attack budgets |
| P10 | `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` | `casp16_server_protein_v2_aliasfix` | pending behind v2 baseline | Reproduce a Yang-style construct cleanup on top of alias-fixed coverage and token-safe stoichiometry; 27 sequence edits across 21 targets | Run only after the v2 coverage/stoich baseline is scored |
| P11 | `target_lab/h1258_interaction_window_v1` | target_lab only | artifact generated, not submitted | Public CASP16 complex clue says top Yang H1258 models used LRRK2 interaction-domain window | Run manually in a small slot; promote only as a target-agnostic window rule |
| P12 | `target_lab/small_complex_stoich_batch_v1` | target_lab only | Slurm job `810824` failed; resubmitted as `811114` pending | Compact batch for exact stoichiometry plus H1258 window learning | Monitor resubmitted job; do not register as ranked |
| P13 | `target_lab/domain_fragment_batch_v1` | target_lab only | Slurm job `810862` pending | Compact domain-decomposition reproduction for D2 winner recipe | Monitor job; promote only target-agnostic segmentation, not CASP-domain hand crops |
| P14 | `casp16_server_attack_protenix25` | `casp16_server_protein_v2_aliasfix` | planned, not queued | Winner-like compute is likely more than five candidates; this declares a 25-seed Protenix tier without pretending it is comparable to `dev_fixed` or `protenix5` | Launch only after the active `protenix5` attack and v2 dev baseline are scored; execute as five seed shards |

## Latest Baseline Result

| Run | Status | Domain mean | Domain coverage | Oligo status | Key failure signal |
| --- | --- | --- | --- | --- | --- |
| `server_protenix_full_msa_template_seed101` | complete and scored | `0.063962` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | 8 Protenix jobs failed with `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, `T1295O` |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | complete and scored | `0.066908` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Same 8 Protenix token-limit failures as baseline; small net domain gain from `T1234`, `T1298`, and `T1210` |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | complete and scored | `0.065114` | 15 ok / 29 missing prediction / 27 failed or missing-reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Produced 99/106 CIFs and rescued `T1295` inference, but `T1295` still scores `0` because the local server benchmark lacks a reference mapping |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | complete and scored | `0.060677` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | needs QSglob rescore after mapping validation | Produced 98/106 CIFs; antibody oligo predictions exist for H0222/H0223/H0225/H1222/H1223/H1225 but need assembly mapping before ranked QSglob claims |

QSglob signal probe on six oligo targets: baseline `H0222=0.075`,
`T1249V1O=0.090`; terminal-tag cleanup `T1249V1O=0.122`; oversize fallback
`H1232=0.032`; antibody-Fv cleanup `H0222=0.037`, `T1249V1O=0.125`. This is
not a full oligo leaderboard, but it shows QSglob can guide strategy triage
once mapping false zeros are isolated.

## Queued Next

| Priority | Run | Strategy | Artifact | Benchmark | Status | Hypothesis |
| --- | --- | --- | --- | --- | --- | --- |
| done | `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `yang_oversize_domain_monomer_fallback_v1` | `strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored | Rescue the known `T1295` server-domain zero caused by Protenix `n_token > 2560` by replacing only a single-entity domain `A8` job with one representative chain |
| done | `server_protenix_yang_antibody_fv_cleanup_seed101` | `yang_antibody_fv_cleanup_v1` | `strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored negative | Antibody-Fv cleanup lowered the ranked domain mean and cannot yet be judged on oligos until QSglob assembly mapping is validated |
| deferred | `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `yang_terminal_tag_antibody_fv_cleanup_v1` | `strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Do not launch the stacked run before QSglob mapping or a positive antibody-complex signal exists |
| deferred | `server_protenix_yang_epitope_tag_cleanup_seed101` | `yang_epitope_tag_cleanup_v1` | `strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Token-limit hard failures need a predeclared split/fallback policy before another construct-cleanup full run |
| P1 | `server_attack_protenix_terminal_tag_seed101_105` | `yang_terminal_tag_cleanup_v1_server_attack` | `runs/server_attack_protenix_terminal_tag_seed101_105/` | `casp16_server_protein_v1` | Slurm job `810719` running | Five fixed seeds on the current best terminal-tag cleanup strategy, selected by predeclared confidence-only policy |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `yang_large_target_split_or_fallback_v1` | `runs/server_protenix_yang_large_target_split_or_fallback_seed101/` | `casp16_server_protein_v1` | pending behind attack job | Convert the eight `n_token > 2560` failures into under-budget jobs by predeclared chain/copy fallback |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `yang_sequence_recovery_v1` | `runs/server_protenix_yang_sequence_recovery_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Recover protein-domain inputs that were missing or misparsed as nucleic-acid records |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `yang_sequence_recovery_large_target_fallback_v1` | `runs/server_protenix_yang_sequence_recovery_large_target_fallback_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Stack sequence recovery with token-budget fallback; 40 unique changed targets and max optimized job 2535 tokens |
| generated | not queued | `yang_oligo_stoichiometry_recovery_v1` | `strategies/yang_oligo_stoichiometry_recovery_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | artifacts generated | Restore official oligo copy counts for 9 existing jobs; 5 remain under token limit and 4 need construct/window handling |
| P6 | `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | `yang_oligo_stoichiometry_token_safe_v1` | `runs/server_protenix_yang_oligo_stoichiometry_token_safe_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Apply exact stoichiometry only for under-budget oligo jobs on top of stacked coverage recovery |
| P7 | `server_attack_protenix_coverage_stoich_seed101_105` | `yang_coverage_stoich_token_safe_v1_server_attack` | `runs/server_attack_protenix_coverage_stoich_seed101_105/` | `casp16_server_protein_v1` | queued, not submitted | Five fixed seeds on the stacked coverage + token-safe stoichiometry input, selected by confidence-only policy |
| P8 | `server_v2_protenix_yang_coverage_stoich_seed101` | `yang_oligo_stoichiometry_token_safe_v1` | `runs/server_v2_protenix_yang_coverage_stoich_seed101/` | `casp16_server_protein_v2_aliasfix` | Slurm job `810938` pending on dependency `810719` | First v2 alias-fixed dev baseline; 163 Protenix jobs, 10 changed targets |
| P9 | `server_v2_protenix_yang_coverage_stoich_low_complexity_seed101` | `yang_coverage_stoich_low_complexity_v1` | `runs/server_v2_protenix_yang_coverage_stoich_low_complexity_seed101/` | `casp16_server_protein_v2_aliasfix` | pending behind v2 baseline | Same v2 coverage/stoich input plus low-complexity terminal cleanup, 27 sequence edits across 21 targets |
| target_lab | not queued | `h1258_interaction_window_v1` | `target_lab/h1258_interaction_window_v1/` | target_lab only | artifact generated | LRRK2 residues 861-1014 plus 14-3-3 A1B2, total 648 tokens |
| target_lab | `811114` | `small_complex_stoich_batch_v1` | `target_lab/small_complex_stoich_batch_v1/` | target_lab only | resubmitted after env fix | Six-job batch: H1232/H1233/H1236/H1244/H1267 exact stoich plus H1258 window |
| target_lab | `810862` | `domain_fragment_batch_v1` | `target_lab/domain_fragment_batch_v1/` | target_lab only | Slurm job pending | Twelve domain-fragment jobs testing whether CASP-domain decomposition is worth a future target-agnostic rule |

The terminal-tag, oversize-domain fallback, and antibody-Fv runs are complete
and scored. The next valuable work is scorer mapping and benchmark capability,
not another single-seed construct rerun. `run-next` should not be used again until the
deferred statuses are intentional or new run specs are created for the next
predeclared policy.

Generation commands used:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_oversize_domain_monomer_fallback_v1
./casp16 run-spec \
  --run-id server_protenix_yang_oversize_domain_monomer_fallback_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_oversize_domain_monomer_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_antibody_fv_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_antibody_fv_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_antibody_fv_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_epitope_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_epitope_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_epitope_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion
```

All queued Protenix reruns intentionally match the baseline engine flags:
MSA, templates, default params, cache, fusion, and TF32 are enabled.

## Budget Discipline

The current queue is the `dev_fixed` tier: one seed (`101`), one sample, and
`first_output_only`. It is deliberately strict so agents can compare strategy
changes without compute-budget noise. It is not a claim that CASP16 winner
servers used only one seed or one internal candidate.

After single-seed failures and wins are scored, promote promising strategies to
a separate `server_attack` tier with a fixed multi-seed or multi-sample budget
and a predeclared confidence-only model selection rule. Do not mix
`server_attack` rows into `dev_fixed` rankings, and do not choose the submitted
model using references, official scores, or target-score feedback.

The first `server_attack` budget uses five candidates per target because it is
the smallest useful realism check, not because CASP16 winners are assumed to
have used only five candidates. Any larger candidate budget must be a new
predeclared attack-budget version and should report candidates per target,
expected GPU-hours, actual wall time, and selection policy.

The first larger planned tier is
`attack_budgets/casp16_server_attack_protenix25.json`: 25 fixed seeds
(`101..125`), one sample per seed, the same `protenix_confidence_v1` selector,
and five predeclared seed shards. The exact shard run ids, seed ranges, input
artifact, and selector live in
`attack_budgets/casp16_server_attack_protenix25_shards.tsv`. It is not queued
until the active `protenix5` run and the v2 alias-fixed development baseline
justify the spend.

The oversize-domain fallback result is a reminder to spend realistic attack
compute carefully: extra seeds will not fix hard Protenix token-limit failures,
missing references, or unvalidated QSglob mapping. Clean coverage, reference
mapping, and scorer validation should come before a costly multi-candidate
push.
The same applies after installation: extra candidates cannot fix a scorer that
maps the predicted assembly to the wrong reference chains.

The antibody-Fv result reinforces the same rule. A strategy that is negative on
the ranked domain track and unmeasurable on oligos should not be promoted to a
multi-seed attack tier merely because CASP16 winners likely used more than one
internal candidate.

## Backlog

| Priority | Strategy | Status | Reason To Try | Stop Condition |
| --- | --- | --- | --- | --- |
| done | Install OpenStructure `ost` for QSglob | installed at `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/bin/ost` | Oligo server scores are not rank-comparable without QSglob | Next bottleneck is assembly/chain mapping, not tool availability |
| P6 | `yang_low_complexity_terminal_cleanup_v1` | artifacts generated, not queued | H0217/H0272/H1217/H1272 have short terminal low-complexity regions that match Yang-style construct cleanup | Queue only after tag cleanup helps or baseline failures justify more aggressive trimming |
| P7 | `yang_hydrophobic_leader_cleanup_v1` | artifacts generated, not queued | T0240/T1210/T1240-style N termini contain signal-like hydrophobic leaders; construct cleanup may improve folded-core prediction | Risky branch; queue only after baseline or conservative cleanup evidence |
| P8 | `yang_domain_fragment_inputs_v1` | target-lab artifacts generated, not queued | Domain decomposition is a major winner recipe; CASP domain-summary fragments give a fast diagnostic upper bound | Not server-ranked; promote only via new benchmark version or predeclared segmentation rule |
| P9 | `yang_antibody_fv_fragment_inputs_v1` | target-lab artifacts generated, not queued | Fv-only changed-target jobs are useful for fast antibody assembly diagnosis | Not server-ranked; keep separate from full-set claims |
| P10 | Domain crop/chain mapping | not started | Domain GDT_TS can be noisy or wrong without explicit CASP domain crops | Stop after target classes with clear mapping; do not hand-map every hard outlier |
| done | Alias-fixed server benchmark version | generated as `casp16_server_protein_v2_aliasfix` | `0xxx/1xxx/2xxx` aliasing recovers many server rows without target-specific tuning | Use v2 for future winner-comparison runs; keep in-flight v1 runs on v1 |
| P11 | Validate `server_attack` budget | first run spec pending | Winner-like server runs almost certainly use more than one internal candidate; local attack runs need fixed multi-seed/multi-sample rules | Score `server_attack_protenix_terminal_tag_seed101_105` and compare only as attack-tier evidence |
| P12 | `yang_large_target_split_or_fallback_v1` | artifacts generated | The new fallback changes exactly the 8 known token-limit failures and brings each optimized job under 2560 tokens | Queue only after the active attack job, then judge as coverage recovery rather than full assembly quality |
| P13 | Extra sampling/ranking lab | diagnostic only | CASP16 reports show sampling helps, but ranking is fragile | Never use best-of-N for ranked v1 without a new benchmark version |
| P14 | `yang_sequence_recovery_large_target_fallback_v1` | queued as `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | Sequence recovery exposes two additional oversized domain jobs, so the fixes should be tested together before larger attack budgets | Run only after active pending jobs unless component results make the stack unnecessary |
| P15 | `yang_oligo_stoichiometry_recovery_v1` | artifacts generated | Exact stoichiometry changes H1232/H1233/H1236/H1244/H1267 safely and exposes H1217/H1227/H1258/H1265 as oversized realistic assemblies | Do not queue exact full assemblies directly; create a token-safe or domain-window derivative first |
| P16 | `yang_oligo_stoichiometry_token_safe_v1` | queued as `server_protenix_yang_oligo_stoichiometry_token_safe_seed101` | This is the token-safe derivative: 5 exact-stoichiometry changes, max job 2535 tokens | Run after active pending jobs; keep oligos diagnostic until QSglob assembly mapping is validated |
| P17 | H1258 interaction-window target_lab | artifact generated | Public assessment says top Yang H1258 models used LRRK2 interacting region instead of full-length LRRK2 | Run as target_lab only; never count it as a ranked server result |
| P18 | Small complex stoich batch | Slurm job `810824` failed on import-path collision; `811114` pending after env fix | Fast learning set for under-budget exact stoich and H1258 public window, max job 1929 tokens | Use only as target_lab evidence; promote only target-agnostic rules |
| P19 | Domain fragment batch | Slurm job `810862` pending | Fast learning set for domain decomposition on long/multidomain protein targets, max fragment 1633 residues | Use only as target_lab evidence; promote only target-agnostic segmentation or new benchmark version |
| P20 | `protenix25` attack tier | budget JSON and shard TSV created, not queued | Winner-scale comparison needs more than the starter five candidates | Wait for `protenix5` and v2 dev baseline evidence; run only as seed-sharded attack budget |

## Evidence Links

- CASP16 official z-score page: https://predictioncenter.org/casp16/zscores_final.cgi
- CASP16 monomer assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- Yang Lab optimized-input paper: https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- MULTICOM4 CASP16 paper: https://www.nature.com/articles/s42003-025-08960-6
