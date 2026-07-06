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
