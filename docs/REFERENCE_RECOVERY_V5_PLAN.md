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
- `diagnostics/reference_gap/casp16_server_protein_v5_refmap_recovery_queue.tsv`
- `diagnostics/reference_gap/casp16_server_protein_v5_input_alias_repair_candidates.tsv`

`casp16_server_protein_v4_refmap` has severe reference-limited score caps:

| Track | Available refs | Missing refs | Local cap with missing refs scored 0 | Server winner mean |
| --- | ---: | ---: | ---: | ---: |
| `protein_domain` | 28/71 | 43 | 0.394366 | 0.923321 |
| `protein_oligo` | 53/104 | 51 | 0.509615 | 0.582615 |

So reference recovery is necessary for a full server-track comparison. It is
not a substitute for better predictions, and it must not change v2/v4 in
place.

## Machine-Readable Queue

`diagnostics/reference_gap/casp16_server_protein_v5_refmap_recovery_queue.tsv`
is the current work queue for v5. It compresses the 94 missing-reference rows
from the v4 report into 42 target-family tasks:

| Lane | Meaning | Groups |
| --- | --- | ---: |
| `A_near_term_domain_candidate` | candidate exists, but provenance/mapping is not accepted | 1 |
| `B_deferred_sequence_hit_review` | sequence-search hit exists, but it is deferred until alignment/provenance review | 5 |
| `D_oligo_assembly_mapping` | oligo candidate exists, but assembly/QSglob mapping is unresolved | 2 |
| `C_input_or_alias_repair_first` | input or alias must be repaired before reference promotion | 5 |
| `E_domain_manual_native_search` | domain target family needs native/reference search | 16 |
| `F_oligo_manual_native_search` | oligo target family needs native/reference search | 13 |

The queue uses official target metadata and reference status only. It must not
be joined with local prediction `target_scores.csv` to choose per-target
prediction behavior. A row marked `audit_first_not_accepted`,
`deferred_hit_not_accepted`, `search_first_not_accepted`, or
`not_reference_ready` is deliberately not an accepted benchmark reference.

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

2026-07-07 follow-up audit:
`diagnostics/reference_gap/t1228v1_v5_refmap_audit.tsv` records the current
candidate decision. CASP target pages for `M1228v1` and `M1228v2` state that
the protein-DNA complex has two distinct conformations and variants should be
submitted separately, but they do not map variant `v1` or `v2` to the later PDB
candidate states. Therefore `9dxk` and `9y66` remain blocked despite exact
domain coverage, while `9dxh/9dxj` remain additionally blocked by the two
missing N-terminal domain positions. The next proof is native-state provenance
plus explicit chain/domain crop mapping, not another sequence-search hit.

### Lane B: Deferred Sequence Hits

These rows now stay visible in the queue because they are useful review work,
but they are not accepted references. A deferred sequence hit must either be
rejected or promoted only after native/reference provenance, alignment review,
and explicit chain/domain or assembly mapping.

Examples include `T0270/T1270/T2270` and `T0270O/T1270O/T2270O` with `10br`,
plus `T1295/T1295O` and `H0215/H1215/H2215`. The first action is review, not
score-table mutation and not prediction tuning.

### Lane D: Oligo Candidates Blocked By Assembly

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

Detailed repair evidence lives in
`diagnostics/reference_gap/casp16_server_protein_v5_input_alias_repair_candidates.tsv`.
The current split is:

- `T1228V2` and `T1294V2` already have non-oracular sequence inheritance in
  the D6a input-repair artifact and exact-sequence MSA cache coverage. They
  should stay in the D6a-style input lane until native-state/reference
  provenance and explicit domain crop mapping exist.
- `H1265_V1`, `H1265_V2`, and `H1265_V3` are score-table variant rows without
  target-list sequence rows. They now have a sequence-level repair in
  `strategies/yang_protein_oligo_sequence_recovery_v1/casp16_server_protein_v2_aliasfix/`
  that maps the variants to the H1265 A/B protein chains, with complete
  exact-sequence MSA-cache coverage. That is still not an accepted reference:
  variant/native assembly provenance and QSglob chain/interface mapping are
  required first.

Do not promote these five rows by copying H1265/T1228/T1294 references. The
first deliverable is realistic input coverage; accepted references still need
the proof listed in the TSV.

### Lane E: Manual Native Search Targets

Most missing-reference rows still have zero usable sequence-search candidates.
Start with high-value domain rows because they affect the domain score cap and
have simpler single-chain/domain mapping than oligo assemblies:

2026-07-07 follow-up: a focused RCSB sequence probe retried the highest-value
domain gaps `T1292`, `T1294V1`, `T1274`, and `T1231`. Exact search, T1292
C-terminal His-tag trimming, and relaxed identity cutoffs down to 0.90 all
returned no hits. Public search can surface template-like structures such as
`6N63` for T1292, but its sequence is not the CASP target construct and it must
not be promoted as a native reference without separate provider/native
provenance. Keep these rows in manual native search, not automated refmap
promotion.

2026-07-07 14:08 CDT follow-up: a second relaxed RCSB probe covered the next
high-gain Lane E families: `T0240/T1240/T2240`,
`T0259/T1259/T2259`, `T0246/T1246/T2246`,
`T0218/T1218/T2218`, `T0237/T1237/T2237`, and
`T1279/T2279`. It used `identity_cutoff=0.90` and `max_hits=25`, checked 17
domain rows, and found 0 hits. The evidence is in
`diagnostics/reference_gap/rcsb_relaxed90_probe_20260707_lane_e_high_value_domain_targets.tsv`
and the header-only candidate TSV beside it. These rows should now be treated
as native/provenance manual-search work, not as candidates for another
search-depth-only RCSB loop.

| Priority | Target | Server best score | Next action |
| ---: | --- | ---: | --- |
| 1 | `T1292` | 1.000000 | manual native/reference search |
| 2 | `T0240/T1240/T2240` | 0.997600 | manual native/reference search; relaxed RCSB probe exhausted |
| 3 | `T1274/T2274` | 0.997200 | search as one phase-alias family |
| 4 | `T1294V1` | 0.994000 | manual native/reference search |
| 5 | `T1279/T2279` | 0.991700 | manual native/reference search; relaxed RCSB probe exhausted |
| 6 | `T1231/T2231` | 0.982400 | search as one phase-alias family |
| 7 | `T1276/T2276` | 0.982000 | verify input repair state, then search |
| 8 | `T1259/T2259/T0259` | 0.979200 | manual native/reference search; relaxed RCSB probe exhausted |
| 9 | `T0246/T1246/T2246` | 0.976200 | manual native/reference search; relaxed RCSB probe exhausted |
| 10 | `T0218/T1218/T2218` | 0.975800 | manual native/reference search; long multidomain mapping required |

Keep searches grouped by phase aliases so one accepted mapping can explain
multiple fixed-set rows only when sequence, construct, and domain definitions
really match.

## Execution Order

1. Do not interrupt P25 closeout or launch extra GPU branches for this.
2. While GPU runs continue, keep `T1228V1` as an audit target, but do not
   accept it until the 545-residue protein input and native-state mapping are
   both fixed.
3. Use the Lane C input-alias TSV to keep D6a and future input-repair branches
   honest: repaired inputs can be predicted, but the five rows remain
   reference-blocked until their explicit native/domain or assembly/QSglob
   proof exists.
4. If `T1228V1` eventually passes, create
   `diagnostics/reference_gap/casp16_server_protein_v5_refmap_accepted_reference_map.tsv`
   by copying the v4 accepted rows and adding only the audited row.
5. Generate `casp16_server_protein_v5_refmap` with `server-benchmark`.
6. Run `reference-gap-report` on v5 and compare caps.
7. Keep oligo families in Lane D as audit work until biological assembly and
   QSglob mapping are explicit.

This plan raises evaluation coverage without changing the prediction strategy
or letting reference data leak into candidate generation.
