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
