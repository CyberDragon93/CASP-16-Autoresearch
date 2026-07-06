# CASP16 Autoresearch Queue

This queue turns winner-recipe notes into executable full-benchmark attempts.
The queue is allowed to change quickly; benchmark definitions are not.

## Next To Run

| Priority | Run | Benchmark | Status | Why It Matters | Next Gate |
| --- | --- | --- | --- | --- | --- |
| P0 | Install OpenStructure `ost` / QSglob scorer | `casp16_server_protein_v1` | not started | Required to compare the 104 official server oligo targets and judge antibody-complex strategies | Install or register a QSglob-compatible scorer, then rerun `./casp16 score` and `./casp16 leaderboard` |
| P1 | Run `server_attack_protenix_terminal_tag_seed101_105` | separate from `dev_fixed` | Slurm job `810719` pending | Winner-level server comparison should not pretend one seed/sample is enough | Monitor GH200 job, then score with `protenix_confidence_v1` while keeping attack rows out of `dev_fixed` ranks |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `casp16_server_protein_v1` | pending behind attack job | Extra seeds cannot fix `n_token > 2560` hard failures | Submit after attack job `810719` completes if coverage recovery remains highest leverage |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Several domain hard zeros are local sequence parsing/alias failures, not model failures | Submit after attack and large-target fallback jobs; expect more jobs but better domain coverage |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `casp16_server_protein_v1` | pending behind active jobs | Combine the two coverage fixes before spending larger attack budgets | Submit after the attack and component coverage runs unless their results make the stack unnecessary |

## Latest Baseline Result

| Run | Status | Domain mean | Domain coverage | Oligo status | Key failure signal |
| --- | --- | --- | --- | --- | --- |
| `server_protenix_full_msa_template_seed101` | complete and scored | `0.063962` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | unranked until QSglob exists | 8 Protenix jobs failed with `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, `T1295O` |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | complete and scored | `0.066908` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | unranked until QSglob exists | Same 8 Protenix token-limit failures as baseline; small net domain gain from `T1234`, `T1298`, and `T1210` |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | complete and scored | `0.065114` | 15 ok / 29 missing prediction / 27 failed or missing-reference over 71 official server-domain targets | unranked until QSglob exists | Produced 99/106 CIFs and rescued `T1295` inference, but `T1295` still scores `0` because the local server benchmark lacks a reference mapping |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | complete and scored | `0.060677` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | unranked until QSglob exists | Produced 98/106 CIFs; antibody oligo predictions exist for H0222/H0223/H0225/H1222/H1223/H1225 but cannot be ranked without QSglob |

## Queued Next

| Priority | Run | Strategy | Artifact | Benchmark | Status | Hypothesis |
| --- | --- | --- | --- | --- | --- | --- |
| done | `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `yang_oversize_domain_monomer_fallback_v1` | `strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored | Rescue the known `T1295` server-domain zero caused by Protenix `n_token > 2560` by replacing only a single-entity domain `A8` job with one representative chain |
| done | `server_protenix_yang_antibody_fv_cleanup_seed101` | `yang_antibody_fv_cleanup_v1` | `strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored negative | Antibody-Fv cleanup lowered the ranked domain mean and cannot yet be judged on oligos because QSglob is unavailable |
| deferred | `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `yang_terminal_tag_antibody_fv_cleanup_v1` | `strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Do not launch the stacked run before QSglob or a positive antibody-complex signal exists |
| deferred | `server_protenix_yang_epitope_tag_cleanup_seed101` | `yang_epitope_tag_cleanup_v1` | `strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | deferred | Token-limit hard failures need a predeclared split/fallback policy before another construct-cleanup full run |
| P1 | `server_attack_protenix_terminal_tag_seed101_105` | `yang_terminal_tag_cleanup_v1_server_attack` | `runs/server_attack_protenix_terminal_tag_seed101_105/` | `casp16_server_protein_v1` | Slurm job `810719` pending | Five fixed seeds on the current best terminal-tag cleanup strategy, selected by predeclared confidence-only policy |
| P2 | `server_protenix_yang_large_target_split_or_fallback_seed101` | `yang_large_target_split_or_fallback_v1` | `runs/server_protenix_yang_large_target_split_or_fallback_seed101/` | `casp16_server_protein_v1` | pending behind attack job | Convert the eight `n_token > 2560` failures into under-budget jobs by predeclared chain/copy fallback |
| P3 | `server_protenix_yang_sequence_recovery_seed101` | `yang_sequence_recovery_v1` | `runs/server_protenix_yang_sequence_recovery_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Recover protein-domain inputs that were missing or misparsed as nucleic-acid records |
| P4 | `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | `yang_sequence_recovery_large_target_fallback_v1` | `runs/server_protenix_yang_sequence_recovery_large_target_fallback_seed101/` | `casp16_server_protein_v1` | pending behind active jobs | Stack sequence recovery with token-budget fallback; 40 unique changed targets and max optimized job 2535 tokens |

The terminal-tag, oversize-domain fallback, and antibody-Fv runs are complete
and scored. The next valuable work is scorer/benchmark capability, not another
single-seed construct rerun. `run-next` should not be used again until the
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

The oversize-domain fallback result is a reminder to spend realistic attack
compute carefully: extra seeds will not fix hard Protenix token-limit failures,
missing references, or missing QSglob. Clean coverage, reference mapping, and
scorer availability should come before a costly multi-candidate push.

The antibody-Fv result reinforces the same rule. A strategy that is negative on
the ranked domain track and unmeasurable on oligos should not be promoted to a
multi-seed attack tier merely because CASP16 winners likely used more than one
internal candidate.

## Backlog

| Priority | Strategy | Status | Reason To Try | Stop Condition |
| --- | --- | --- | --- | --- |
| P5 | Install OpenStructure `ost` for QSglob | not started | Oligo server scores are not rank-comparable without QSglob | If install becomes a build rabbit hole, keep oligos diagnostic and score domains first |
| P6 | `yang_low_complexity_terminal_cleanup_v1` | artifacts generated, not queued | H0217/H0272/H1217/H1272 have short terminal low-complexity regions that match Yang-style construct cleanup | Queue only after tag cleanup helps or baseline failures justify more aggressive trimming |
| P7 | `yang_hydrophobic_leader_cleanup_v1` | artifacts generated, not queued | T0240/T1210/T1240-style N termini contain signal-like hydrophobic leaders; construct cleanup may improve folded-core prediction | Risky branch; queue only after baseline or conservative cleanup evidence |
| P8 | `yang_domain_fragment_inputs_v1` | target-lab artifacts generated, not queued | Domain decomposition is a major winner recipe; CASP domain-summary fragments give a fast diagnostic upper bound | Not server-ranked; promote only via new benchmark version or predeclared segmentation rule |
| P9 | `yang_antibody_fv_fragment_inputs_v1` | target-lab artifacts generated, not queued | Fv-only changed-target jobs are useful for fast antibody assembly diagnosis | Not server-ranked; keep separate from full-set claims |
| P10 | Domain crop/chain mapping | not started | Domain GDT_TS can be noisy or wrong without explicit CASP domain crops | Stop after target classes with clear mapping; do not hand-map every hard outlier |
| P11 | Validate `server_attack` budget | first run spec pending | Winner-like server runs almost certainly use more than one internal candidate; local attack runs need fixed multi-seed/multi-sample rules | Score `server_attack_protenix_terminal_tag_seed101_105` and compare only as attack-tier evidence |
| P12 | `yang_large_target_split_or_fallback_v1` | artifacts generated | The new fallback changes exactly the 8 known token-limit failures and brings each optimized job under 2560 tokens | Queue only after the active attack job, then judge as coverage recovery rather than full assembly quality |
| P13 | Extra sampling/ranking lab | diagnostic only | CASP16 reports show sampling helps, but ranking is fragile | Never use best-of-N for ranked v1 without a new benchmark version |
| P14 | `yang_sequence_recovery_large_target_fallback_v1` | queued as `server_protenix_yang_sequence_recovery_large_target_fallback_seed101` | Sequence recovery exposes two additional oversized domain jobs, so the fixes should be tested together before larger attack budgets | Run only after active pending jobs unless component results make the stack unnecessary |

## Evidence Links

- CASP16 official z-score page: https://predictioncenter.org/casp16/zscores_final.cgi
- CASP16 monomer assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- Yang Lab optimized-input paper: https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- MULTICOM4 CASP16 paper: https://www.nature.com/articles/s42003-025-08960-6
