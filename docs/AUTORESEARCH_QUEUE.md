# CASP16 Autoresearch Queue

This queue turns winner-recipe notes into executable full-benchmark attempts.
The queue is allowed to change quickly; benchmark definitions are not.

## Next To Run

| Priority | Run | Benchmark | Status | Why It Matters | Next Gate |
| --- | --- | --- | --- | --- | --- |
| P0 | `server_protenix_yang_antibody_fv_cleanup_seed101` | `casp16_server_protein_v1` | pending, next to launch | Tests whether sequence-only antibody Fv construct cleanup helps the antibody-antigen subset while preserving all 106 server jobs | Run the full fixed-budget benchmark, score immediately, and compare fixed-set domain mean against terminal-tag cleanup |

## Latest Baseline Result

| Run | Status | Domain mean | Domain coverage | Oligo status | Key failure signal |
| --- | --- | --- | --- | --- | --- |
| `server_protenix_full_msa_template_seed101` | complete and scored | `0.063962` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | unranked until QSglob exists | 8 Protenix jobs failed with `n_token > 2560`: `T1295`, `H0217`, `H0258`, `H0272`, `H1217`, `H1258`, `H1272`, `T1295O` |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | complete and scored | `0.066908` | 15 ok / 30 missing prediction / 26 missing reference over 71 official server-domain targets | unranked until QSglob exists | Same 8 Protenix token-limit failures as baseline; small net domain gain from `T1234`, `T1298`, and `T1210` |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | complete and scored | `0.065114` | 15 ok / 29 missing prediction / 27 failed or missing-reference over 71 official server-domain targets | unranked until QSglob exists | Produced 99/106 CIFs and rescued `T1295` inference, but `T1295` still scores `0` because the local server benchmark lacks a reference mapping |

## Queued Next

| Priority | Run | Strategy | Artifact | Benchmark | Status | Hypothesis |
| --- | --- | --- | --- | --- | --- | --- |
| done | `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | `yang_oversize_domain_monomer_fallback_v1` | `strategies/yang_oversize_domain_monomer_fallback_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | complete and scored | Rescue the known `T1295` server-domain zero caused by Protenix `n_token > 2560` by replacing only a single-entity domain `A8` job with one representative chain |
| P1 | `server_protenix_yang_antibody_fv_cleanup_seed101` | `yang_antibody_fv_cleanup_v1` | `strategies/yang_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | pending, next to launch | Antibody-antigen targets may benefit from Fv-style constructs while preserving all 106 server jobs |
| P2 | `server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101` | `yang_terminal_tag_antibody_fv_cleanup_v1` | `strategies/yang_terminal_tag_antibody_fv_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | pending behind individual ablations | Combined terminal-tag plus antibody-Fv cleanup tests whether non-overlapping construct fixes compose |
| P3 | `server_protenix_yang_epitope_tag_cleanup_seed101` | `yang_epitope_tag_cleanup_v1` | `strategies/yang_epitope_tag_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | pending behind combined cleanup | Broader epitope/His/TEV tag cleanup may rescue H1258/H0258-style expression artifacts while staying sequence-only |

The terminal-tag and oversize-domain fallback runs are complete and scored.
The next `./casp16 run-next --benchmark casp16_server_protein_v1 --dry-run`
should select antibody Fv cleanup, followed by the combined cleanup run and
then epitope tag cleanup.

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

The oversize-domain fallback result is a reminder to spend realistic attack
compute carefully: extra seeds will not fix hard Protenix token-limit failures,
missing references, or missing QSglob. Clean coverage, reference mapping, and
scorer availability should come before a costly multi-candidate push.

## Backlog

| Priority | Strategy | Status | Reason To Try | Stop Condition |
| --- | --- | --- | --- | --- |
| P5 | Install OpenStructure `ost` for QSglob | not started | Oligo server scores are not rank-comparable without QSglob | If install becomes a build rabbit hole, keep oligos diagnostic and score domains first |
| P6 | `yang_low_complexity_terminal_cleanup_v1` | artifacts generated, not queued | H0217/H0272/H1217/H1272 have short terminal low-complexity regions that match Yang-style construct cleanup | Queue only after tag cleanup helps or baseline failures justify more aggressive trimming |
| P7 | `yang_hydrophobic_leader_cleanup_v1` | artifacts generated, not queued | T0240/T1210/T1240-style N termini contain signal-like hydrophobic leaders; construct cleanup may improve folded-core prediction | Risky branch; queue only after baseline or conservative cleanup evidence |
| P8 | `yang_domain_fragment_inputs_v1` | target-lab artifacts generated, not queued | Domain decomposition is a major winner recipe; CASP domain-summary fragments give a fast diagnostic upper bound | Not server-ranked; promote only via new benchmark version or predeclared segmentation rule |
| P9 | `yang_antibody_fv_fragment_inputs_v1` | target-lab artifacts generated, not queued | Fv-only changed-target jobs are useful for fast antibody assembly diagnosis | Not server-ranked; keep separate from full-set claims |
| P10 | Domain crop/chain mapping | not started | Domain GDT_TS can be noisy or wrong without explicit CASP domain crops | Stop after target classes with clear mapping; do not hand-map every hard outlier |
| P11 | Define `server_attack` budget | policy documented, implementation not started | Winner-like server runs almost certainly use more than one internal candidate; local attack runs need fixed multi-seed/multi-sample rules | Add a separate leaderboard tier before launching any multi-seed run |
| P12 | Extra sampling/ranking lab | diagnostic only | CASP16 reports show sampling helps, but ranking is fragile | Never use best-of-N for ranked v1 without a new benchmark version |

## Evidence Links

- CASP16 official z-score page: https://predictioncenter.org/casp16/zscores_final.cgi
- CASP16 monomer assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- Yang Lab optimized-input paper: https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- MULTICOM4 CASP16 paper: https://www.nature.com/articles/s42003-025-08960-6
