# CASP16 Server V2 Reference Gap Priorities

Generated from `benchmarks/casp16_server_protein_v2_aliasfix/targets.tsv` and the current v2 diagnostic score table. This is evaluation-infrastructure triage only; do not use native/reference data during prediction or strategy selection.

- benchmark: `casp16_server_protein_v2_aliasfix`
- diagnostic probe run: `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101`
- missing-reference ranked targets: 96
- prediction_waiting_on_reference: 40
- reference_registry_gap: 51
- sequence_or_input_gap_before_reference: 5

Audit addendum, `2026-07-06 18:57 CDT`: follow-up inspection found that
`T1276`, `T1228V1`, and `T2276` should be treated as input-kind repair before
reference recovery, because the local v2 inputs represented protein-like CASP
sequence records as short DNA jobs. `T1239V1` has the same input-kind issue
even though its reference is already available. The generated repair artifact
is
`strategies/yang_domain_sequence_recovery_oligo_nofail_v1/casp16_server_protein_v2_aliasfix/`.
Do not remove these targets from the denominator; fix prediction inputs first,
then expand references in a new benchmark version only when native provenance
and chain/domain mapping are explicit.

## Track Counts

| track | blocker class | targets |
| --- | --- | ---: |
| `protein_domain` | `prediction_waiting_on_reference` | 26 |
| `protein_domain` | `reference_registry_gap` | 17 |
| `protein_domain` | `sequence_or_input_gap_before_reference` | 2 |
| `protein_oligo` | `prediction_waiting_on_reference` | 14 |
| `protein_oligo` | `reference_registry_gap` | 34 |
| `protein_oligo` | `sequence_or_input_gap_before_reference` | 3 |

## First 25 Targets To Triage

| priority | target | track | blocker | len | domains | state | probe status | next action |
| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1 | `T1276` | `protein_domain` | `prediction_waiting_on_reference` | 40 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 2 | `T1284` | `protein_domain` | `prediction_waiting_on_reference` | 120 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 3 | `T1228V1` | `protein_domain` | `prediction_waiting_on_reference` | 121 | 4 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 4 | `T1226` | `protein_domain` | `prediction_waiting_on_reference` | 123 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 5 | `T1231` | `protein_domain` | `prediction_waiting_on_reference` | 142 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 6 | `T1207` | `protein_domain` | `prediction_waiting_on_reference` | 144 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 7 | `T1274` | `protein_domain` | `prediction_waiting_on_reference` | 167 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 8 | `T0246` | `protein_domain` | `prediction_waiting_on_reference` | 168 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 9 | `T1246` | `protein_domain` | `prediction_waiting_on_reference` | 168 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 10 | `T1259` | `protein_domain` | `prediction_waiting_on_reference` | 243 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 11 | `T0259` | `protein_domain` | `prediction_waiting_on_reference` | 243 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 12 | `T1243` | `protein_domain` | `prediction_waiting_on_reference` | 293 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 13 | `T1278` | `protein_domain` | `prediction_waiting_on_reference` | 380 | 1 | `A1` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 14 | `T1292` | `protein_domain` | `prediction_waiting_on_reference` | 392 | 1 | `A2` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 15 | `T1294V1` | `protein_domain` | `prediction_waiting_on_reference` | 428 | 1 | `A2` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 16 | `T1279` | `protein_domain` | `prediction_waiting_on_reference` | 428 | 2 | `An` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 17 | `T0270` | `protein_domain` | `prediction_waiting_on_reference` | 437 | 2 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 18 | `T1270` | `protein_domain` | `prediction_waiting_on_reference` | 437 | 2 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 19 | `T0237` | `protein_domain` | `prediction_waiting_on_reference` | 488 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 20 | `T1237` | `protein_domain` | `prediction_waiting_on_reference` | 488 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 21 | `T0240` | `protein_domain` | `prediction_waiting_on_reference` | 653 | 2 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 22 | `T1240` | `protein_domain` | `prediction_waiting_on_reference` | 653 | 2 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 23 | `T1218` | `protein_domain` | `prediction_waiting_on_reference` | 1164 | 3 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 24 | `T0218` | `protein_domain` | `prediction_waiting_on_reference` | 1164 | 3 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |
| 25 | `T1257` | `protein_domain` | `prediction_waiting_on_reference` | 1263 | 1 | `UNK` | `missing_reference` | `find_native_reference_then_score_existing_prediction` |

## Rules

- Do not remove these targets from the server denominator.
- Do not fill local scores from official score tables.
- Accept a reference only after native structure provenance, sequence/construct coverage, chain mapping, and domain/assembly mapping are explicit.
- Any accepted registry expansion should become a new benchmark version such as `casp16_server_protein_v3_refmap`, not an in-place rewrite of v2.

## Exact-Sequence RCSB Probe

`rcsb_exact_sequence_probe_v2_prediction_waiting.tsv` probes the 40
`prediction_waiting_on_reference` rows against the RCSB sequence-search API
with `identity_cutoff=1.0`. It resolves CASP phase aliases before querying.

Summary:

- probed rows: 40
- rows with sequence-search hits: 6
- full target/entity sequence exact candidates: 8 entity rows across
  `T1228V1` and `T1278`
- partial/local sequence hits that must not be promoted: `T1270/T0270` and
  `T1270O/T0270O` via `10BR_1`, plus the `T1278` `13MI..13MN` rows

Companion metadata lives in
`rcsb_exact_sequence_probe_v2_candidates.tsv`. Treat these as
`candidate_reference` diagnostics only. A future `casp16_server_protein_v3_refmap`
can accept a candidate only after native provenance, full construct coverage,
and domain/assembly chain mapping are explicit.

`rcsb_exact_sequence_probe_latest_prediction_waiting.tsv` and
`rcsb_exact_sequence_probe_latest_candidates.tsv` are generated by
`./casp16 refmap-probe`. The `2026-07-07 00:13 CDT` rerun of the same 40
`prediction_waiting_on_reference` rows found hits for 6 rows and 37 candidate
rows total, but still only 8 full-construct exact candidates across `T1228V1`
and `T1278`. Additional `T1278` hits are alignment-unverified diagnostics, not
reference-map promotions.

`rcsb_exact_sequence_probe_latest_all_missing_references.tsv`,
`rcsb_exact_sequence_probe_latest_all_candidates.tsv`, and
`casp16_server_protein_latest_all_refmap_review.tsv` extend the probe to all 96
v2 missing-reference rows. The `2026-07-07 00:23 CDT` all-gap scan found 20
targets with hits, 204 candidate rows, and 81 full-construct exact candidate
rows. The newly useful exact rows are mostly oligo reference-registry gaps
(`H0217/H1217/H2217` and `H0267/H1267/H2267`), so they require biological
assembly, chain stoichiometry, and interface mapping before a new benchmark
version can accept them.

`casp16_server_protein_latest_all_candidate_structures.tsv` caches the latest
all-gap candidate mmCIF paths and hashes for mapping review. The mmCIF payloads
live under the ignored `refmap_candidate_mmcif/` cache.

`casp16_server_protein_latest_oligo_assembly_audit.tsv` is generated by
`./casp16 refmap-oligo-audit`. It currently audits 69 candidate assembly rows
across `H0217/H1217/H2217` and `H0267/H1267/H2267`: the candidate chains are
present in each biological assembly, but no candidate assembly matches the
current target polymer-chain count. Keep these as candidates until native
assembly provenance and QSglob chain/interface mapping are explicit.

`candidate_ref_tmscore_probe.tsv` scores existing local predictions for the two
full-construct candidate target classes against the candidate references. It
does not install those references into any benchmark. Best observed diagnostic
scores are low:

- `T1228V1`: best `GDT_TS_norm=0.012100`
- `T1278`: best `GDT_TS_norm=0.106100`

So these candidates are useful for refmap validation, but they do not by
themselves reveal hidden winner-level predictions in the current runs.
