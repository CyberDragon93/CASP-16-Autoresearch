# CASP16 Server Reference Gap Report

This is an evaluation-infrastructure report. It does not promote
references, change benchmark eligibility, or score predictions.

- benchmark: `casp16_server_protein_v4_refmap`
- ranked targets: 175
- accepted reference-map rows in benchmark: 2
- review TSV: `/scratch/10992/liaorunlong93/casp16-leaderboard/diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv`
- oligo audit TSV: `/scratch/10992/liaorunlong93/casp16-leaderboard/diagnostics/reference_gap/casp16_server_protein_latest_oligo_assembly_audit.tsv`
- detail TSV: `/scratch/10992/liaorunlong93/casp16-leaderboard/diagnostics/reference_gap/casp16_server_protein_v4_refmap_reference_gap_report.tsv`

## Score Cap

| track | available refs | missing refs | max local mean with missing=0 | official server winner | winner mean |
| --- | ---: | ---: | ---: | --- | ---: |
| `protein_domain` | 28/71 | 43 | 0.394366 | `110s` | 0.923321 |
| `protein_oligo` | 53/104 | 51 | 0.509615 | `456s` | 0.582615 |

## Next Reference Work

### protein_domain

| target | best server score | candidates | oligo assembly matches | next action |
| --- | ---: | ---: | ---: | --- |
| `T1292` | 1.000000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1294V2` | 0.997600 | 0 | 0 | `repair_input_or_sequence_alias_before_reference` |
| `T0240` | 0.997600 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1240` | 0.997600 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2240` | 0.997600 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1274` | 0.997200 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2274` | 0.997200 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1294V1` | 0.994000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1279` | 0.991700 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2279` | 0.991700 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1231` | 0.982400 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2231` | 0.982400 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1276` | 0.982000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1259` | 0.979200 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2259` | 0.979200 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T0259` | 0.976700 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T0246` | 0.976200 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1228V2` | 0.975900 | 0 | 0 | `repair_input_or_sequence_alias_before_reference` |
| `T0218` | 0.975800 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2276` | 0.971700 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1295` | 0.967400 | 17 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `T1246` | 0.965800 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2246` | 0.965800 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1228V1` | 0.964800 | 4 | 0 | `verify_native_provenance_plus_explicit_domain_crop_mapping` |
| `T0270` | 0.961900 | 1 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `T1270` | 0.961900 | 1 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `T2218` | 0.960800 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2270` | 0.960700 | 1 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `T1218` | 0.959000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T0237` | 0.944500 | 0 | 0 | `probe_or_manual_native_reference_search` |

### protein_oligo

| target | best server score | candidates | oligo assembly matches | next action |
| --- | ---: | ---: | ---: | --- |
| `T1292O` | 0.977000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1294V1O` | 0.957000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H1245` | 0.946000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2245` | 0.946000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H0215` | 0.946000 | 4 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `H1215` | 0.946000 | 4 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `H0245` | 0.940000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2215` | 0.939000 | 4 | 0 | `review_deferred_sequence_hits_or_continue_native_search` |
| `T0257O` | 0.937000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1257O` | 0.937000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2257O` | 0.937000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2208` | 0.905000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H0208` | 0.897000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H1208` | 0.894000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H0230` | 0.892000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H1230` | 0.885000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2230` | 0.885000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T1237O` | 0.831000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T0237O` | 0.825000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `T2237O` | 0.821000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2267` | 0.819000 | 3 | 0 | `resolve_biological_assembly_stoichiometry_before_accepting` |
| `H1267` | 0.818000 | 3 | 0 | `resolve_biological_assembly_stoichiometry_before_accepting` |
| `H2217` | 0.818000 | 20 | 0 | `resolve_biological_assembly_stoichiometry_before_accepting` |
| `H0217` | 0.817000 | 20 | 0 | `resolve_biological_assembly_stoichiometry_before_accepting` |
| `H1229` | 0.783000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2229` | 0.783000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H1217` | 0.777000 | 20 | 0 | `resolve_biological_assembly_stoichiometry_before_accepting` |
| `H1244` | 0.768000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H0244` | 0.763000 | 0 | 0 | `probe_or_manual_native_reference_search` |
| `H2244` | 0.745000 | 0 | 0 | `probe_or_manual_native_reference_search` |

## Rule

Accepted rows must go through a new benchmark version. Do not hand-edit
locked benchmark TSVs, and do not use prediction scores or leaderboard
rows to choose per-target references.
