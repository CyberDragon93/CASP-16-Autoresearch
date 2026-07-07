# CASP16 Server Reference Gap Audit

This audit tracks why local `casp16_server_protein_v1` scores still understate
coverage. It is a scoring/measurement issue, not a prediction strategy.

## Current State

Current checked-in `casp16_server_protein_v1` artifacts:

- ranked targets: 175
- local references available: 54
- ranked targets without an available reference: 121
- generated Protenix jobs: 106

The active attack run still uses these checked-in v1 artifacts. Do not rewrite
them in place while runs are in flight.

## Alias-Fix Probe

CASP16 official score tables include phase-style ids such as `T2201`,
`H2202`, and `T2201O`. The local target metadata and PDB references often live
under the matching `T1201`, `H1202`, or `T1201` ids. The existing lookup only
connected `0xxx` and `1xxx` aliases; it missed `2xxx`.

A temporary rebuild outside the repo after extending alias lookup to
`0xxx/1xxx/2xxx` produced:

- ranked targets: 175
- local references available: 79
- generated Protenix jobs: 163

Examples recovered by aliasing:

| target | inherited PDB | status |
| --- | --- | --- |
| `T2201` | `8bwd` | available |
| `T2206` | `9cp0` | available |
| `T2210` | `9enr` | available |
| `T2234` | `8qpq` | available |
| `H2202` | `8bwl` | available |
| `H2204` | `8vyl` | available |
| `H2232` | `9cn2` | available |
| `H2258` | `9ci3` | available |
| `T2201O` | `8bwd` | available |
| `H2225` | `9cqa` | available |

## Decision

Do not mutate `casp16_server_protein_v1` in place. The alias fix changes
reference mapping and input coverage, so it has been created as a new
benchmark version.

Created benchmark:

```text
casp16_server_protein_v2_aliasfix
```

The current v1 attack results remain useful for comparing strategy deltas under
the original fixed protocol. Any winner-comparison claim should use the
alias-fixed benchmark once it is created and rerun.

## Alias-Fixed V2 State

Current checked-in `casp16_server_protein_v2_aliasfix` artifacts:

- ranked targets: 175
- local references available: 79
- ranked targets without an available reference: 96
- domain references: 26 available / 45 missing
- oligo references: 53 available / 51 missing
- generated Protenix jobs: 163

The remaining gaps are not fixed by a simple target-name rewrite. A
reference-only probe that additionally tried to inherit PDB ids through
`TxxxxO -> Txxxx` and `S/V` subtarget-to-base aliases recovered 0 new
references beyond v2.

## V2 Reference-Gap Priority Artifact

`diagnostics/reference_gap/casp16_server_protein_v2_aliasfix_missing_references.tsv`
is the current worklist for reference recovery. It keeps the fixed server
denominator intact and sorts gaps by immediate scoring usefulness rather than
by model strategy. The companion summary is
`diagnostics/reference_gap/README.md`.

Current split:

- 40 targets have an existing v2 diagnostic prediction but score
  `missing_reference`; these are the first reference-registry targets to fix.
- 51 targets are still pure reference-registry gaps.
- 5 targets need sequence/input alias resolution before reference work can
  unlock scoring.

Use this artifact only for evaluation-infrastructure work. It must not be used
to tune target-specific prediction strategies, and accepted references still
need explicit native provenance plus chain/domain/assembly mapping.

## Input-Kind Reclassification

Follow-up triage showed that some apparent `missing_reference` rows should be
handled as input-repair work before native-reference recovery. In particular,
`T1276`, `T1228V1`, and `T2276` were generated locally as short `dnaSequence`
jobs even though the CASP sequence archive contains protein-like records.
`T1239V1` has the same input-modality problem despite already having a local
reference, so it is a prediction-input bug rather than a reference gap.

The generated artifact
`strategies/yang_domain_sequence_recovery_oligo_nofail_v1/casp16_server_protein_v2_aliasfix/`
applies the existing target-agnostic `yang_sequence_recovery_v1` rule on top
of the v2 nofail oligo-recovery stack. It changes 8 domain jobs
(`T1212`, `T1228V1`, `T1228V2`, `T1239V1`, `T1239V2`, `T1276`, `T1294V2`,
`T2276`), keeps all 169 jobs under Protenix's token limit, and leaves
benchmark eligibility unchanged.

MSA cache status for this artifact is 269/276 protein chains covered from the
global exact-sequence cache. The 7 fresh-MSA chains are `T1239V1`, `T1239V2`,
`T1228V1`, `T1228V2`, `T1212`, `T1276`, and `T2276`. The pending run spec
`server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_seed101` explicitly
allows that fresh-MSA cost for a single-seed `dev_fixed` ablation, but it must
not become a multi-seed attack row until the ablation improves fixed-set score.

## RCSB Sequence-Search Probe

RCSB sequence search is useful for triage, but it is not safe as an automatic
native-reference source. A probe on missing-reference targets showed that
high-scoring hits can be homologous or partial structures rather than the CASP
native assembly. For example, `T1295` (`TM_Ag`, 469 residues) returned old PDB
polymer entities such as `1KLF_2` and `4XO9_1`; those entities are 279 residues
and match only a component/subregion, so they must not be installed as the
benchmark reference.

Rule for future reference recovery:

- accept a candidate only after exact or explicitly mapped sequence coverage is
  verified against the target construct
- for domain targets, require domain residue/chain crop mapping before the
  target can contribute a ranked `GDT_TS`
- for oligo targets, require biological assembly and chain/entity/stoichiometry
  mapping before ranked `QSglob`
- keep sequence-search hits as `candidate_reference` diagnostics until those
  checks pass
- create a new benchmark version such as `casp16_server_protein_v3_refmap`
  for any accepted reference-registry expansion; do not mutate v2 in place

## Reference-Map Overlay

`./casp16 server-benchmark` now supports a repeatable `--reference-map` TSV
overlay for audited reference recovery. This is the intended path for
`casp16_server_protein_v3_refmap`; it is deliberately rejected for the locked
`casp16_server_protein_v1` and `casp16_server_protein_v2_aliasfix` benchmark
names.

Reference-map rows may keep `candidate`, `rejected`, or `deferred` entries for
audit history, but only `status=accepted` rows affect generated benchmark
references. Accepted rows must include:

- `target_id`
- `pdb_ids`
- `source`
- `native_provenance`
- `construct_coverage`
- `chain_mapping`
- `scoring_mapping`

Example generation command:

```bash
./casp16 server-benchmark \
  --benchmark casp16_server_protein_v3_refmap \
  --benchmark-version 3 \
  --reference-map diagnostics/reference_gap/casp16_server_protein_v3_refmap_accepted_reference_map.tsv \
  --download-references
```

The generated benchmark copies the normalized overlay to
`benchmarks/casp16_server_protein_v3_refmap/reference_map.tsv` and records it in
`benchmark.json`. This keeps native-reference recovery auditable without
allowing a strategy run or an agent to hand-edit locked benchmark TSV files.

Use `refmap-review` to convert RCSB exact-sequence probe output into that
overlay format without promoting anything automatically:

```bash
./casp16 refmap-review
```

The current review artifact is
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv`. It has
8 `candidate` rows and 14 `rejected` rows. Candidate rows still need explicit
native provenance plus chain/domain mapping before changing `status` to
`accepted`; rejected rows are carried only to document why they should not be
promoted.

Use `refmap-materialize` to cache candidate structures for offline chain/domain
mapping review without installing them as official benchmark references:

```bash
./casp16 refmap-materialize
```

The current manifest is
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv`.
It records 8 downloaded candidate mmCIF files, their byte sizes, and sha256
hashes. The mmCIF payloads live under the ignored cache directory
`diagnostics/reference_gap/refmap_candidate_mmcif/`.

Use `refmap-audit` to render the review and materialized-structure manifest
into a compact Markdown worklist:

```bash
./casp16 refmap-audit
```

The current report is
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_audit.md`.
It identified `T1278` as the nearest single-domain candidate class and
`T1228V1` as a harder multi-domain candidate class.

## Accepted T1278 Refmap Row

The first accepted reference-map overlay row promotes `T1278` only. The row is
stored in
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_accepted_reference_map.tsv`
and was generated from target-page provenance, exact-sequence RCSB review, and
the chain/domain coverage audit.

Accepted mapping:

- target: `T1278`
- PDB: `9hav`
- reference chain: `A`
- domain crop: `T1278-D1`, residues `34-370`
- selection rule: deterministic lowest PDB id among full-construct exact
  sequence candidates, not a prediction-score or leaderboard-based choice

Regenerated benchmark:

```text
casp16_server_protein_v3_refmap
```

Current generated v3 state:

- ranked targets: 175
- local references available: 80
- ranked targets without an available reference: 95
- generated Protenix jobs: 165
- accepted reference-map rows: 1

The v2 alias-fixed benchmark remains locked at 79 available references and 96
missing references. Continue adding accepted reference-map rows in versioned
benchmarks; do not rewrite v2 or hand-edit generated benchmark TSVs.

## Phase-Alias T2278 Refmap Row

`casp16_server_protein_v4_refmap` extends v3 with one phase-alias row:
`T2278 -> 9hav`. This row is accepted because the official target metadata
records `T2278` as the later-phase 380-residue A1 Dehydrogenase target, the
benchmark inputs for `T1278` and `T2278` are sequence-identical, and the server
domain benchmark maps both rows to `T1278-D1`.

Accepted overlay:

```text
diagnostics/reference_gap/casp16_server_protein_v4_refmap_accepted_reference_map.tsv
```

Current generated v4 state:

- ranked targets: 175
- local references available: 81
- ranked targets without an available reference: 94
- generated Protenix jobs: 165
- accepted reference-map rows: 2

The `T2278` row inherits the already accepted `T1278` chain/crop evidence; no
prediction score, leaderboard row, or official score value was used to choose
the reference.

Use `reference-gap-report` to summarize the current score cap and missing
reference worklist without changing any benchmark artifacts:

```bash
./casp16 reference-gap-report --benchmark casp16_server_protein_v4_refmap
```

The current report is
`diagnostics/reference_gap/casp16_server_protein_v4_refmap_reference_gap_report.md`
with details in the sibling `.tsv`. It records that v4 has 81/175 references
available, with domain capped at 28/71 and oligo capped at 53/104 if missing
references score `0`. This is a triage report only; accepted rows still require
a versioned reference-map overlay.

Use `refmap-chain-audit` to convert cached candidate mmCIF atom-site records
into chain-level domain coverage evidence:

```bash
./casp16 refmap-chain-audit
```

The current output is
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_chain_audit.tsv`.
It audits 8 candidate structures and 94 chains. For `T1278-D1` residues
`34-370`, the complete-covering chains are: `9HAV` chain A only, `9HAW` 18
chains, `9HAX` 12 chains, and `9HAY` 18 chains. This supports the accepted
`T1278` v3 row and the sequence-identical `T2278` phase-alias row in v4.
For `T1228V1`, only `9DXK` 4 chains and `9Y66` 1 chain cover the union of the
current domain ranges in this coarse audit, so it still needs stricter
multi-domain crop review before promotion. This audit is evidence only; it does
not install references or change benchmark eligibility.

The scorer now applies domain crops for server-domain benchmarks when an
accepted benchmark `reference_map.tsv` row supplies explicit scoring mapping.
`score_benchmark_runs` reads accepted `reference_map.tsv` rows, parses
`residue_ranges=...`, optionally filters the reference to explicit
`reference_chain=...`, writes temporary cropped mmCIF files, and runs
GDT_TS/TMscore on those cropped inputs. This does not promote any candidate by
itself; promotion still happens only through accepted reference-map rows in
versioned benchmarks.

## RCSB Exact-Sequence Probe

A follow-up probe on the 40 `prediction_waiting_on_reference` rows queried the
RCSB sequence-search API with `identity_cutoff=1.0`, after resolving
`0xxx/1xxx/2xxx` CASP phase aliases. The generated artifacts are:

- `diagnostics/reference_gap/rcsb_exact_sequence_probe_v2_prediction_waiting.tsv`
- `diagnostics/reference_gap/rcsb_exact_sequence_probe_v2_candidates.tsv`

The probe found sequence-search hits for 6 rows, but only 8 candidate entity
rows are full target/entity sequence exact matches:

- `T1228V1`: `9DXH_1`, `9DXJ_1`, `9DXK_1`, `9Y66_1`
- `T1278`: `9HAV_1`, `9HAW_1`, `9HAX_1`, `9HAY_1`

Other hits are explicitly marked non-promotable without mapping. For example,
`10BR_1` matches only a 204-residue HtrA PDZ construct for `T1270/T0270`, and
the `T1278` `13MI..13MN` rows are local sequence-search hits rather than full
construct matches. None of these candidates should be written into v2. They are
the first concrete worklist for versioned refmap benchmarks; accepted subsets
are now materialized in `casp16_server_protein_v3_refmap` and
`casp16_server_protein_v4_refmap`.

`./casp16 refmap-probe` now makes this discovery step repeatable without
promoting any reference:

```bash
./casp16 refmap-probe \
  --blocker-class prediction_waiting_on_reference \
  --limit 40 \
  --max-hits 25 \
  --output-targets-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_prediction_waiting.tsv \
  --output-candidates-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_candidates.tsv
```

A live rerun on `2026-07-07 00:13 CDT` found hits for the same 6 rows and the
same 8 full-construct exact entity candidates. It also found additional
alignment-unverified `T1278` hits (`13MO..13NC` class), but these are not
accepted references; they remain diagnostics until native provenance and exact
construct/domain mapping are explicit.

The probe was then expanded to all 96 v2 missing-reference rows:

```bash
./casp16 refmap-probe \
  --max-hits 25 \
  --output-targets-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_all_missing_references.tsv \
  --output-candidates-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_all_candidates.tsv

./casp16 refmap-review \
  --candidate-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_latest_all_candidates.tsv \
  --output-tsv diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv
```

The `2026-07-07 00:23 CDT` all-gap scan found:

- 96 probed missing-reference rows
- 20 targets with RCSB hits
- 204 candidate rows
- 81 full-construct exact candidate rows
- 9 candidate target classes after review:
  `T1228V1`, `T1278`, `T2278`, `H0217/H1217/H2217`, and
  `H0267/H1267/H2267`

`T1278/T2278` already have an accepted domain path in v4. The new likely
scoreability unlocks are the H0217 and H0267 oligo alias groups, but they
remain candidate references only: accepted promotion requires biological
assembly provenance, chain/entity stoichiometry, and explicit QSglob interface
mapping. Do not promote these from sequence identity alone.

A follow-up scan on `2026-07-07` raised the RCSB search cap to
`--max-hits 50`:

```bash
./casp16 refmap-probe \
  --benchmark casp16_server_protein_v2_aliasfix \
  --max-hits 50 \
  --output-targets-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_20260707_all_missing_references.tsv \
  --output-candidates-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_20260707_all_candidates.tsv

./casp16 refmap-review \
  --benchmark casp16_server_protein_v2_aliasfix \
  --candidate-tsv diagnostics/reference_gap/rcsb_exact_sequence_probe_20260707_all_candidates.tsv \
  --output-tsv diagnostics/reference_gap/casp16_server_protein_20260707_refmap_review.tsv
```

This returned 304 candidate rows and 156 deferred rows, but still only 81
full-construct exact candidates. It did not add any new promotable target class:
candidate rows remain limited to `T1228V1`, accepted `T1278/T2278`, and the
H0217/H0267 oligo alias groups. The extra rows are therefore search-depth
diagnostics, not a reason to create a new refmap benchmark version.

The oligo candidates are now materialized and audited separately:

```bash
./casp16 refmap-materialize \
  --reference-map-tsv diagnostics/reference_gap/casp16_server_protein_latest_all_refmap_review.tsv \
  --status candidate \
  --output-dir diagnostics/reference_gap/refmap_candidate_mmcif \
  --manifest-tsv diagnostics/reference_gap/casp16_server_protein_latest_all_candidate_structures.tsv

./casp16 refmap-oligo-audit
```

`diagnostics/reference_gap/casp16_server_protein_latest_all_candidate_structures.tsv`
records 81 candidate structure rows. The oligo assembly audit writes
`diagnostics/reference_gap/casp16_server_protein_latest_oligo_assembly_audit.tsv`
and currently covers 69 candidate assembly rows across 6 oligo targets. All
69 assemblies contain the candidate asym ids, but 0 match the current target
polymer-chain count. `H0267/H1267/H2267` have 2-chain target metadata while
candidate assemblies are tetrameric or 34-meric; `H0217/H1217/H2217` have
6-chain target metadata while candidate eIF2B assemblies range from 10 to 18
polymer chains. These rows stay as candidates until native assembly provenance
and QSglob chain/interface mapping are explicit.

A small TMscore probe against existing predictions is recorded in
`diagnostics/reference_gap/candidate_ref_tmscore_probe.tsv`. It confirms the
candidate references can be used by the local metric tooling, but the current
models are weak on these targets: best observed `GDT_TS_norm` is `0.012100` for
`T1228V1` and `0.106100` for `T1278`. Reference recovery remains important for
fair measurement, but these two target classes do not look like hidden
near-winner predictions.

`T1228V1` should stay out of the next refmap promotion despite exact-sequence
candidate chains. The current server benchmark input is a 121-token
misclassified record, while the official T target and domain summary describe a
545-residue protein with four domains. Candidate structures such as `9DXK` and
`9Y66` can cover the domain residue ranges, but accepting them against the
locked v4 input would mix reference recovery with an input-kind repair. Treat
this as D6a input recovery first; only a later benchmark version with the
545-residue protein input and explicit chain/domain mapping should consider
promoting the native reference.
