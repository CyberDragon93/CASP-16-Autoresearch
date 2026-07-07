# CASP16 Server V3 Refmap Candidate Audit

This report summarizes reference-map candidates. It does not promote any
candidate to `accepted`; accepted rows still require explicit native
provenance plus chain/domain or assembly mapping.

- benchmark: `casp16_server_protein_v2_aliasfix`
- review TSV: `/scratch/10992/liaorunlong93/casp16-leaderboard/diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv`
- structure manifest: `/scratch/10992/liaorunlong93/casp16-leaderboard/diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv`
- targets with candidates/rejections: 6
- review rows: 22
- candidate rows: 8
- rejected rows: 14

## T0270

- track: `protein_domain`
- sequence lookup: `T0270`
- domains: `T1270-D1,T1270-D2`
- current reference status: `no_reference_pdb`
- server best score: `0.961900`
- next action: `no_promotable_candidate_from_current_probe`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| rejected | `10br` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 10BR_1 \| Crystal structure of B. burgdorferi HtrA PDZ1-2 domains \| 2026-06-17T00:00:00.000+00:00 \| X-RAY DIFFRACTION |

## T0270O

- track: `protein_oligo`
- sequence lookup: `T0270`
- domains: `T1270-D1,T1270-D2`
- current reference status: `no_reference_pdb`
- server best score: `0.621000`
- next action: `no_promotable_candidate_from_current_probe`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| rejected | `10br` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 10BR_1 \| Crystal structure of B. burgdorferi HtrA PDZ1-2 domains \| 2026-06-17T00:00:00.000+00:00 \| X-RAY DIFFRACTION |

## T1228V1

- track: `protein_domain`
- sequence lookup: `T1228V1`
- domains: `T1228V1-D1,T1228V1-D2,T1228V1-D3,T1228V1-D4`
- current reference status: `no_reference_pdb`
- server best score: `0.964800`
- next action: `verify_native_provenance_then_explicit_domain_crop_mapping`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| rejected | `9dxd` | not_materialized | `` | target_sequence_contained_in_candidate_entity |  | partial_or_construct_variant_candidate_do_not_promote_without_mapping \| 9DXD_1 \| attLmm bound serine integrase and RDF complex in the pre-rotation state \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| rejected | `9dxf` | not_materialized | `` | target_sequence_contained_in_candidate_entity |  | partial_or_construct_variant_candidate_do_not_promote_without_mapping \| 9DXF_1 \| attLmm bound serine integrase and RDF complex in the post-rotation state \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| rejected | `9dxg` | not_materialized | `` | target_sequence_contained_in_candidate_entity |  | partial_or_construct_variant_candidate_do_not_promote_without_mapping \| 9DXG_1 \| attP bound large serine integrase and RDF complex in the dimeric state (cleaved) \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| candidate | `9dxh` | downloaded | `c9ec82e7ed6b` | full_construct_exact_sequence | multi_domain_target=T1228V1-D1,T1228V1-D2,T1228V1-D3,T1228V1-D4; requires_explicit_domain_crop_mapping | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9DXH_1 \| attPmm and attBmm bound serine integrase complex in the pre-rotation state \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| candidate | `9dxj` | downloaded | `b3bff78292d6` | full_construct_exact_sequence | multi_domain_target=T1228V1-D1,T1228V1-D2,T1228V1-D3,T1228V1-D4; requires_explicit_domain_crop_mapping | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9DXJ_1 \| attPmm and attBmm bound serine integrase complex in the post-rotation state \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| candidate | `9dxk` | downloaded | `3c026389051c` | full_construct_exact_sequence | multi_domain_target=T1228V1-D1,T1228V1-D2,T1228V1-D3,T1228V1-D4; requires_explicit_domain_crop_mapping | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9DXK_1 \| attPmm bound serine integrase complex in the tetrameric state \| 2026-01-21T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| candidate | `9y66` | downloaded | `b7bb600c5ddf` | full_construct_exact_sequence | multi_domain_target=T1228V1-D1,T1228V1-D2,T1228V1-D3,T1228V1-D4; requires_explicit_domain_crop_mapping | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9Y66_1 \| attLsym bound serine integrase complex in the dimeric state \| 2026-02-04T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |
| rejected | `9y6v` | not_materialized | `` | target_sequence_contained_in_candidate_entity |  | partial_or_construct_variant_candidate_do_not_promote_without_mapping \| 9Y6V_1 \| attPsym bound large serine integrase and RDF complex in the dimeric state \| 2026-02-04T00:00:00.000+00:00 \| ELECTRON MICROSCOPY |

## T1270

- track: `protein_domain`
- sequence lookup: `T1270`
- domains: `T1270-D1,T1270-D2`
- current reference status: `no_reference_pdb`
- server best score: `0.961900`
- next action: `no_promotable_candidate_from_current_probe`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| rejected | `10br` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 10BR_1 \| Crystal structure of B. burgdorferi HtrA PDZ1-2 domains \| 2026-06-17T00:00:00.000+00:00 \| X-RAY DIFFRACTION |

## T1270O

- track: `protein_oligo`
- sequence lookup: `T1270`
- domains: `T1270-D1,T1270-D2`
- current reference status: `no_reference_pdb`
- server best score: `0.641000`
- next action: `no_promotable_candidate_from_current_probe`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| rejected | `10br` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 10BR_1 \| Crystal structure of B. burgdorferi HtrA PDZ1-2 domains \| 2026-06-17T00:00:00.000+00:00 \| X-RAY DIFFRACTION |

## T1278

- track: `protein_domain`
- sequence lookup: `T1278`
- domains: `T1278-D1`
- current reference status: `no_reference_pdb`
- server best score: `0.995600`
- next action: `verify_native_provenance_then_chain_and_domain_crop_mapping`

| status | pdb | download | sha256 | construct coverage | mapping blocker | notes |
| --- | --- | --- | --- | --- | --- | --- |
| candidate | `9hav` | downloaded | `4883f756bc6d` | full_construct_exact_sequence | candidate_domain=T1278-D1; residue_ranges=34-370; verify_chain_and_crop | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9HAV_1 \| F420-dependent glucose-6-phosphate dehydrogenase from Thermomicrobium roseus with glucose \| 2025-11-19T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| candidate | `9haw` | downloaded | `dc7cd87f5f37` | full_construct_exact_sequence | candidate_domain=T1278-D1; residue_ranges=34-370; verify_chain_and_crop | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9HAW_1 \| F420-dependent glucose-6-phosphate dehydrogenase without ligand \| 2025-11-19T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| candidate | `9hax` | downloaded | `26366f0c5825` | full_construct_exact_sequence | candidate_domain=T1278-D1; residue_ranges=34-370; verify_chain_and_crop | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9HAX_1 \| F420-dependent glucose-6-phosphate dehydrogenase \| 2025-11-19T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| candidate | `9hay` | downloaded | `2b873270844e` | full_construct_exact_sequence | candidate_domain=T1278-D1; residue_ranges=34-370; verify_chain_and_crop | full_construct_exact_candidate_needs_native_provenance_and_mapping \| 9HAY_1 \| F420-dependent glucose-6-phosphate dehydrogenase with glucose-6-phosphate \| 2025-11-19T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13mi` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13MI_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr12860 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13mj` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13MJ_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr13647 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13mk` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13MK_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr12961 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13ml` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13ML_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr13431 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13mm` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13MM_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr13408 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
| rejected | `13mn` | not_materialized | `` | local_sequence_hit_not_full_construct_do_not_promote |  | local_sequence_hit_not_full_construct_do_not_promote \| 13MN_1 \| PanDDA analysis group deposition -- Crystal structure of PLpro-C111S in complex with Fr12338 \| 2026-02-18T00:00:00.000+00:00 \| X-RAY DIFFRACTION |
