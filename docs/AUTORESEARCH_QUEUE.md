# CASP16 Autoresearch Queue

This queue turns winner-recipe notes into executable full-benchmark attempts.
The queue is allowed to change quickly; benchmark definitions are not.

## Now Running

| Priority | Run | Benchmark | Status | Why It Matters | Next Gate |
| --- | --- | --- | --- | --- | --- |
| P0 | `server_protenix_full_msa_template_seed101` | `casp16_server_protein_v1` | running | First full server-target Protenix baseline with real MSA/templates, seed `101`, sample `1` | Score domains as soon as CIFs finish; oligos need QSglob scorer |

## Queued Next

| Priority | Run | Strategy | Artifact | Benchmark | Status | Hypothesis |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | `server_protenix_yang_terminal_tag_cleanup_seed101` | `yang_terminal_tag_cleanup_v1` | `strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/` | `casp16_server_protein_v1` | pending, blocked while baseline is running | Obvious terminal expression tags can distract AF3-like predictors; target-agnostic cleanup may improve domain/complex placement without using references |

The run spec already exists. `./casp16 run-next --benchmark
casp16_server_protein_v1 --dry-run` will intentionally report
`blocked_by_running_run` until `server_protenix_full_msa_template_seed101`
finishes. After that, the same command should select the queued cleanup run.

Generation commands used:

```bash
./casp16 strategy-inputs --benchmark casp16_server_protein_v1 --strategy yang_terminal_tag_cleanup_v1
./casp16 run-spec \
  --run-id server_protenix_yang_terminal_tag_cleanup_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_terminal_tag_cleanup_v1 \
  --use-msa --use-template --use-default-params
```

## Backlog

| Priority | Strategy | Status | Reason To Try | Stop Condition |
| --- | --- | --- | --- | --- |
| P2 | Install OpenStructure `ost` for QSglob | not started | Oligo server scores are not rank-comparable without QSglob | If install becomes a build rabbit hole, keep oligos diagnostic and score domains first |
| P3 | Domain crop/chain mapping | not started | Domain GDT_TS can be noisy or wrong without explicit CASP domain crops | Stop after target classes with clear mapping; do not hand-map every hard outlier |
| P4 | Domain segmentation inputs | design only | MULTICOM-style domain segmentation is a plausible hard-target gain | Promote only if generated from target metadata/sequence features before scoring |
| P5 | Extra sampling/ranking lab | diagnostic only | CASP16 reports show sampling helps, but ranking is fragile | Never use best-of-N for ranked v1 without a new benchmark version |

## Evidence Links

- CASP16 official z-score page: https://predictioncenter.org/casp16/zscores_final.cgi
- CASP16 monomer assessment: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- Yang Lab optimized-input paper: https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- MULTICOM4 CASP16 paper: https://www.nature.com/articles/s42003-025-08960-6
