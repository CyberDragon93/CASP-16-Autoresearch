# CASP16 Winner Recipes

This file records public CASP16 method clues that are useful for future local
strategy iteration. It is not a license to use official references or scores as
per-target oracles.

## Sources

- CASP16 home and category description:
  https://predictioncenter.org/casp16/
- CASP16 official score tables:
  https://predictioncenter.org/download_area/CASP16/results/tables/
- CASP16 domain z-score ranking:
  https://predictioncenter.org/casp16/zscores_final.cgi
- Yang Lab CASP16 optimized-input paper:
  https://yanglab.qd.sdu.edu.cn/papers/Wang_Proteins_2026.pdf
- CASP16 single-protein assessment:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12157625/
- CASP16 protein-complex assessment preprint:
  https://www.biorxiv.org/content/10.1101/2025.05.29.656875v1.full.pdf
- AlphaFold3 CASP16 preprint:
  https://www.biorxiv.org/content/10.1101/2025.04.10.648174v1.full-text

## Protein Domains

Public reports and the CASP16 domain z-score page indicate that Yang-lab
systems were at or near the top of CASP16 protein-domain performance. The
public recipe is not a single new architecture; it is careful input and target
handling around strong predictors.

Useful strategy hypotheses:

- trim or mask intrinsically disordered regions before prediction when the
  structured core is the scoring target
- decompose multi-domain targets when domain boundaries are clear
- run multiple strong engines where available, such as AF2-style, AF3-style,
  and trRosettaX-style systems
- optimize MSA and template inputs instead of accepting default shallow inputs
- improve model ranking; CASP assessments repeatedly flag ranking/selection as
  a weakness even when at least one generated model is good

For local work, these ideas should become strategy scripts that transform
inputs or select allowed outputs under a fixed budget. They must not change the
benchmark target set or inspect references.

### Recipe Cards

| ID | Recipe | CASP16 clue | Local implementation | Promotion gate |
| --- | --- | --- | --- | --- |
| D1 | Construct trimming | Yang-lab reports removed intrinsically disordered regions and CASP16 monomer assessment highlights fragment/construct design | create target-agnostic sequence-window variants from disorder/low-complexity predictors; never choose windows from reference scores | improves full `protein_domain` mean, not only a handpicked target |
| D1a | Terminal tag cleanup | Yang-style optimized inputs are a low-risk place to remove non-native expression artifacts before harder construct work | `./casp16 strategy-inputs --strategy yang_terminal_tag_cleanup_v1` removes obvious terminal His/expression tags without changing benchmark files | improves or does not regress full server-domain mean after the full baseline |
| D1b | Epitope/TEV tag cleanup | some server inputs visibly include longer N-terminal epitope/His/TEV expression artifacts | `./casp16 strategy-inputs --strategy yang_epitope_tag_cleanup_v1` extends D1a to FLAG-like and His-TEV prefixes while staying sequence-only | queue only after the baseline or after deciding to skip the conservative D1a ablation |
| D1c | Terminal low-complexity cleanup | Yang-style construct refinement often removes disordered terminal noise; CASP monomer assessment highlights construct design | `./casp16 strategy-inputs --strategy yang_low_complexity_terminal_cleanup_v1` trims only 40-aa terminal low-complexity windows after tag cleanup | queue only after conservative tag cleanup helps or baseline failures justify the extra risk |
| D1d | Hydrophobic leader cleanup | construct refinement can remove signal-like N-terminal leaders that are not part of the scored folded core | `./casp16 strategy-inputs --strategy yang_hydrophobic_leader_cleanup_v1` trims a small set of sequence-only hydrophobic-leader candidates after D1c | risky branch; queue only after baseline or tag-cleanup evidence justifies it |
| D2 | Domain decomposition | top monomer pipelines refined constructs and handled domains separately | `./casp16 strategy-inputs --strategy yang_domain_fragment_inputs_v1` creates post hoc CASP-domain fragment inputs for target-lab learning | not server-ranked; promotion needs a new benchmark version or predeclared segmentation rule |
| D3 | MSA/template depth | Yang/trRosetta workflows emphasize optimized MSA/template inputs | full MSA/template Protenix/OpenDDE server run; record MSA source, template mode, cache paths | higher full-set coverage and no regression on positive controls |
| D4 | AF3-style model selection | assessment says AF3 adoption improved confidence/model selection | compare Protenix/OpenDDE first-model policy against allowed diagnostic confidence/consensus only after all predictions exist | confidence remains diagnostic until quality metric validates it on full benchmark |

## Protein Oligos

Protein-complex performance is driven by more than per-chain fold quality.
Assembly stoichiometry, symmetry, chain placement, and interface correctness
matter. Public CASP16 complex reports highlighted strong multimer groups and
continued room for improvement in complex modeling.

Useful strategy hypotheses:

- preserve exact stoichiometry from CASP target metadata
- build assembly-aware inputs rather than flattening all chains naively
- use symmetry-aware chain assignment in scoring and diagnostics
- keep interface metrics such as DockQ, but optimize for assembly-level
  `QSglob` once the scorer is available
- separate "automatic server-like" runs from manual rescue runs

For the server benchmark, a method that produces good monomer structures but
wrong assemblies should score poorly on the oligo track.

### Recipe Cards

| ID | Recipe | CASP16 clue | Local implementation | Promotion gate |
| --- | --- | --- | --- | --- |
| O1 | Exact stoichiometry | Phase 0 showed stoichiometry is still hard, especially high-order assemblies | preserve `Oligo.State`, validate chain counts, fail fast when input expansion is ambiguous | no silent chain/entity mismatch in `input_manifest.tsv` |
| O2 | Construct refinement | complex assessment highlights partial constructs over full sequences | generate target-agnostic construct variants from sequence/domain annotations for large complexes | improves fixed-set QSglob once scorer exists; DockQ-only wins stay diagnostic |
| O3 | Customized MSA/template | top complex groups beat default AFM/AF3 via customized MSAs, templates, and sampling | full MSA/template baseline first, then compare MSA-cache and template modes | full server target coverage increases before target_lab tuning |
| O4 | Massive sampling + ranking | MULTICOM/Kihara-style gains came from sampling, but ranking stayed weak | keep ranked budget at sample 1; run extra samples only as `target_lab` diagnostics for ranking research | promotion requires a predeclared first-output policy or a new benchmark version |
| O5 | Antibody docking branch | kozakovvajda did especially well on antibody-antigen targets without AFM/AF3 as the core engine | target_lab branch for H1232/H1223/H1225 using docking-style assembly refinement | must become target-agnostic for antibody complexes before leaderboard use |
| O6 | First-model ranking | PEZYFoldings was noted for stronger first-model selection | evaluate confidence/consensus/geometry features after full predictions exist | selection rule fixed before scoring a new full run |

## AF3-Style Systems

AF3-style predictors are strong CASP16 baselines, especially when inputs and
large-target handling are carefully managed. Public AF3 CASP16 reports also
describe manual intervention for some difficult or large targets, which should
be tracked separately from server-like automatic runs.

Useful strategy hypotheses:

- compare OpenDDE/Protenix-style runs against an AF3-style reference strategy
  where licensing and local execution allow it
- record whether a run is automatic or manually adjusted
- collect confidence as diagnostics only; do not rank by confidence

## What To Avoid

- claiming a server-track win from `casp16_protein_v1`
- optimizing target-specific settings after seeing official scores
- rescuing a few targets while ignoring full-set mean score
- treating DockQ as interchangeable with `QSglob`
- treating TM-score as interchangeable with official domain `GDT_TS`

## Active Reproduction Order

1. Full server-target MSA/template baseline with Protenix: increase coverage
   from 35 reused local predictions toward all 106 generated server jobs.
2. `yang_terminal_tag_cleanup_v1`: first automatic optimized-input rerun after
   the full Protenix baseline, targeting obvious terminal expression artifacts.
3. `yang_epitope_tag_cleanup_v1`, `yang_low_complexity_terminal_cleanup_v1`,
   and `yang_hydrophobic_leader_cleanup_v1`: generated as risk-increasing
   construct-cleanup artifacts; promote only after baseline or conservative
   cleanup evidence.
4. QSglob scorer installation/integration: without this, oligo server runs
   remain diagnostic no matter how good the structures look.
5. `yang_domain_fragment_inputs_v1`: generated as a target-lab artifact using
   CASP domain-summary metadata; useful for learning whether domain
   decomposition helps, but not a server-ranked strategy as-is.
6. Domain crop/chain mapping: needed before domain scores can be trusted on
   multi-domain or multi-chain targets.
7. H1258/H1232 target_lab loop: use these as fast learning targets for
   stoichiometry, construct refinement, and antibody-complex behavior, then
   promote only target-agnostic changes.
8. Model-selection research: collect confidence/consensus after predictions,
   but keep ranked `first_output_only` unless a new benchmark version is
   created.
