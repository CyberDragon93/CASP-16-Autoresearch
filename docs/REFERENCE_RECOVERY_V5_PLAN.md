# CASP16 Server Reference Recovery V5 Plan

This is an evaluation-infrastructure plan, not a prediction strategy. It
exists to raise the local measurement ceiling for CASP16 server-track
comparison while keeping benchmark rules stable and non-oracular.

## Current State

Source artifacts:

- `benchmarks/casp16_server_protein_v4_refmap/targets.tsv`
- `diagnostics/reference_gap/casp16_server_protein_v4_refmap_reference_gap_report.md`
- `diagnostics/reference_gap/casp16_server_protein_v4_refmap_reference_gap_report.tsv`
- `diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv`
- `diagnostics/reference_gap/casp16_server_protein_latest_oligo_assembly_audit.tsv`

`casp16_server_protein_v4_refmap` has severe reference-limited score caps:

| Track | Available refs | Missing refs | Local cap with missing refs scored 0 | Server winner mean |
| --- | ---: | ---: | ---: | ---: |
| `protein_domain` | 28/71 | 43 | 0.394366 | 0.923321 |
| `protein_oligo` | 53/104 | 51 | 0.509615 | 0.582615 |

So reference recovery is necessary for a full server-track comparison. It is
not a substitute for better predictions, and it must not change v2/v4 in
place.

## V5 Rule

Create a new benchmark version only after accepted rows exist:

```bash
./casp16 server-benchmark \
  --benchmark casp16_server_protein_v5_refmap \
  --benchmark-version 5 \
  --reference-map diagnostics/reference_gap/casp16_server_protein_v5_refmap_accepted_reference_map.tsv \
  --download-references
```

Do not hand-edit locked benchmark TSVs. Do not promote a row from sequence
search alone. Do not use P14 or earlier `target_scores.csv` rows to choose
target-specific reference fixes.

An accepted domain row needs:

- native/reference provenance
- full construct or explicit construct-variant rationale
- chain mapping
- domain crop residue mapping
- cached mmCIF hash

An accepted oligo row additionally needs:

- biological assembly provenance
- target stoichiometry and assembly stoichiometry agreement, or explicit
  scorer mapping that justifies the difference
- QSglob chain/interface mapping

## Work Lanes

### Lane A: Near-Term Candidate, But Not Accepted Yet

`T1228V1` is the only unaccepted domain target with exact-sequence full
construct candidates in the current review:

| Target | Candidates | Current blocker | Required next proof |
| --- | --- | --- | --- |
| `T1228V1` | `9dxh,9dxj,9dxk,9y66` | needs input-kind repair, native-state provenance, and explicit 4-domain crop mapping | use D6a-style 545-residue protein input first; identify whether the native M1228v1 state maps to pre/post-rotation or attP-bound candidate structures; select the correct reference chain; map `T1228V1-D1..D4` residue ranges to that chain; then regenerate a versioned refmap |

Latest chain evidence:
`diagnostics/reference_gap/casp16_server_protein_latest_all_chain_audit.tsv`
audits the current all-gap candidate set. For `T1228V1`, four `9dxk` chains
and one `9y66` chain cover the union of domain ranges exactly, while `9dxh`
and `9dxj` miss two N-terminal domain positions. That is still not enough to
accept a row: the current v4 benchmark input is the wrong 121-token local
record, and coverage alone does not prove the correct native M1228v1
conformational state.

This lane can plausibly produce a future accepted row, but only after input
repair plus native-state/domain-crop mapping are explicit. Do not promote all
four PDB IDs, and do not choose the one with the best local prediction score or
best residue coverage.

### Lane B: Oligo Candidates Blocked By Assembly

The all-gap sequence probe found full-construct candidates for these oligo
families, but `refmap-oligo-audit` found zero biological assemblies matching
the current target polymer-chain counts:

| Target family | Candidates | Current blocker |
| --- | --- | --- |
| `H0217/H1217/H2217` | `6ezo,6k71,6k72,6o85,7d43,7d44,7d45,7d46,7f64,7f66,7f67,7kmf,7rlo,7trj,7vlk,9hvd,9hve,9y3v,9y4b,9y4w` | resolve biological assembly stoichiometry before accepting |
| `H0267/H1267/H2267` | `9qbl,9qbq,9qcc` | resolve biological assembly stoichiometry before accepting |

These are not low-priority forever; they can unlock high-value QSglob rows.
But they are unsafe to accept until assembly and QSglob chain mapping are
audited.

### Lane C: Input Or Alias Repair Before Reference

These rows are not primarily reference-map work yet:

| Track | Target | Current blocker |
| --- | --- | --- |
| `protein_domain` | `T1294V2` | `no_sequence_record` |
| `protein_domain` | `T1228V2` | `no_sequence_record` |
| `protein_oligo` | `H1265_V1` | `no_sequence_record` |
| `protein_oligo` | `H1265_V2` | `no_sequence_record` |
| `protein_oligo` | `H1265_V3` | `no_sequence_record` |

Fix sequence/alias representation first. Reference promotion before input
repair would make the benchmark look more complete without making the
prediction pipeline more real.

### Lane D: Manual Native Search Targets

Most missing-reference rows still have zero usable sequence-search candidates.
Start with high-value domain rows because they affect the domain score cap and
have simpler single-chain/domain mapping than oligo assemblies:

| Priority | Target | Server best score | Next action |
| ---: | --- | ---: | --- |
| 1 | `T1292` | 1.000000 | manual native/reference search |
| 2 | `T0240/T1240/T2240` | 0.997600 | search as one phase-alias family |
| 3 | `T1274/T2274` | 0.997200 | search as one phase-alias family |
| 4 | `T1294V1` | 0.994000 | manual native/reference search |
| 5 | `T1279/T2279` | 0.991700 | search as one phase-alias family |
| 6 | `T1231/T2231` | 0.982400 | search as one phase-alias family |
| 7 | `T1276/T2276` | 0.982000 | verify input repair state, then search |
| 8 | `T1259/T2259/T0259` | 0.979200 | search as one phase-alias family |
| 9 | `T0246/T1246/T2246` | 0.976200 | search as one phase-alias family |
| 10 | `T0218/T1218/T2218` | 0.975800 | long multidomain, search plus domain mapping |

Keep searches grouped by phase aliases so one accepted mapping can explain
multiple fixed-set rows only when sequence, construct, and domain definitions
really match.

## Execution Order

1. Do not interrupt P14/P16 closeout for this.
2. While GPU runs continue, keep `T1228V1` as an audit target, but do not
   accept it until the 545-residue protein input and native-state mapping are
   both fixed.
3. If `T1228V1` eventually passes, create
   `diagnostics/reference_gap/casp16_server_protein_v5_refmap_accepted_reference_map.tsv`
   by copying the v4 accepted rows and adding only the audited row.
4. Generate `casp16_server_protein_v5_refmap` with `server-benchmark`.
5. Run `reference-gap-report` on v5 and compare caps.
6. Keep oligo families in Lane B as audit work until biological assembly and
   QSglob mapping are explicit.

This plan raises evaluation coverage without changing the prediction strategy
or letting reference data leak into candidate generation.
