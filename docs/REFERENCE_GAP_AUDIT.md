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
  --reference-map diagnostics/reference_gap/accepted_reference_map.tsv \
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
the first concrete worklist for a possible `casp16_server_protein_v3_refmap`.

A small TMscore probe against existing predictions is recorded in
`diagnostics/reference_gap/candidate_ref_tmscore_probe.tsv`. It confirms the
candidate references can be used by the local metric tooling, but the current
models are weak on these targets: best observed `GDT_TS_norm` is `0.012100` for
`T1228V1` and `0.106100` for `T1278`. Reference recovery remains important for
fair measurement, but these two target classes do not look like hidden
near-winner predictions.
