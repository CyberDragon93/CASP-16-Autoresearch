# CASP16 Server Benchmark Plan

This document defines the CASP16 benchmark whose purpose is to compare local
methods against the CASP16 server-track protein results. It is a new benchmark
version, not a mutation of `casp16_protein_v1`.

## Why A New Benchmark

`casp16_protein_v1` is a local development leaderboard. It is intentionally
conservative: targets are ranked only when the local repo has explicit
sequence, reference, and mapping coverage. That makes it useful for stable
agent iteration, but it is not the CASP16 server leaderboard.

To ask "can this beat the CASP16 server results?", the benchmark must align to
the official score tables:

- protein domains: official `prot_domains` score table target/domain set
- protein oligos: official `prot_oligo` score table target set
- server comparison: compare only against server submissions in the downloaded
  tables, represented locally by group ids ending in `s`
- metrics: reproduce the official primary metric as closely as possible
  (`GDT_TS` for domains, `QSglob` for oligos)

## Proposed Identity

- Benchmark name: `casp16_server_protein_v1`
- Ranked tracks: `protein_domain`, `protein_oligo`
- Domain target count: 71 official `prot_domains` targets in the current parsed
  score-table aggregate
- Oligo target count: 104 official `prot_oligo` targets in the current parsed
  score-table aggregate
- Ranked comparison set: local runs plus server groups only
- Reference policy: every rank-eligible local target needs explicit reference,
  chain, residue, domain, and assembly mapping

Generated skeleton command:

```bash
./casp16 server-benchmark
./casp16 leaderboard --benchmark casp16_server_protein_v1
```

## Budget Tiers

`casp16_server_protein_v1` starts with a fixed single-seed development budget:
backend `protenix`, seed `101`, sample `1`, and selected model policy
`first_output_only`. This tier is for stable agent iteration and failure
localization. It should not be described as a CASP16 winner-compute
reproduction.

A realistic server-attack tier should be added as a separate predeclared
benchmark/run policy, not by mutating completed single-seed results. CASP16
server submissions were automated under a 72-hour deadline and could include
multiple submitted models; official analyses distinguish model-1 rankings from
best-model analyses. A practical local attack budget should therefore allow
fixed multi-seed or multi-sample generation, while keeping a locked model
selection rule that does not inspect references or official scores.

Current server-attack policy:

- backend: `protenix`
- seeds: fixed list `101,102,103,104,105`
- samples: `1` per seed
- prediction inputs: identical target set and strategy transform for every seed
- selection policy: `protenix_confidence_v1`, documented in
  `docs/SERVER_ATTACK_POLICY.md`
- forbidden selection signals: native/reference structures, official score
  tables, previous target scores, or per-target manual intervention

The machine-readable budget is
`attack_budgets/casp16_server_attack_protenix5.json`.

This keeps two questions separate: "did the strategy improve under a fair
single-seed development budget?" and "how close can a realistic automated
server budget get to the CASP16 server winners?"

The current five-candidate policy is only the first realistic attack tier. It
should not be read as an estimate of the true winner budget. If later work uses
more seeds, more samples, multiple engines, MSA/template variants, or a stronger
predeclared selector, that becomes a new attack-budget version with its own
artifact manifest and leaderboard tier.

Existing prediction directories can be registered for diagnostic reuse without
creating a runnable job:

```bash
./casp16 register-existing-run --benchmark casp16_server_protein_v1 \
  --run-id <diagnostic_run_id> --output-dir <prediction_dir> --no-rank-eligible
./casp16 leaderboard --benchmark casp16_server_protein_v1
```

This is for coverage and scorer-gap accounting only. It does not replace a
full fixed-budget server-target run.

Current generated artifacts live under
`benchmarks/casp16_server_protein_v1/`. The first skeleton has 175 fixed
official targets, 106 generated Protenix jobs, 54 currently cached references,
and 45 unresolved parsed domain-subtarget diagnostics. Missing references or
unresolved mappings remain in the fixed denominator and score `0` for local
runs until the reference registry is improved.

`docs/REFERENCE_GAP_AUDIT.md` records a high-impact alias issue: CASP phase
ids such as `T2201` and `H2202` should be allowed to inherit metadata and PDB
references from matching `T1201`/`H1202` rows. A temporary rebuild with
`0xxx/1xxx/2xxx` aliasing raises the skeleton to 163 generated Protenix jobs
and 79 available references. Because this changes reference mapping and input
coverage, it should become a new benchmark version rather than an in-place
rewrite of v1.

The scoring gate now enforces official metric identity: server protein domains
must parse `GDT_TS`, and server protein oligos must parse `QSglob`. TM-score and
DockQ can still be collected as diagnostics for other benchmarks, but they are
not ranked substitutes for the server metrics.

Static leaderboard artifacts live under
`leaderboards/casp16_server_protein_v1/`. In that directory,
`official_groups.csv` and `official_server_groups.csv` are server-only
baselines; `official_all_groups.csv` is retained as a diagnostic all-group
comparison.

The target counts above come from the local parse of the official CASP16 score
tables under `leaderboards/*/official_groups.csv`; the official score-table
source directory is:

https://predictioncenter.org/download_area/CASP16/results/tables/

## Difference From `casp16_protein_v1`

| Area | `casp16_protein_v1` | `casp16_server_protein_v1` |
| --- | --- | --- |
| Purpose | Local stable agent iteration | Official server-track comparison |
| Ranked target basis | Repo-eligible targets with explicit local mappings | Official protein score-table target sets |
| Current ranked size | 39 targets: 16 domain, 23 oligo | 175 targets: 71 domain, 104 oligo |
| Domain metric | GDT/TM-like local score when available | Official-compatible `GDT_TS` |
| Oligo metric | DockQ-derived local metric | Official-compatible `QSglob` |
| Official comparison | Diagnostic all-group aggregate | Server-only aggregate, group id ends with `s` |
| Missing local prediction | Scores `0` | Scores `0` |
| Main risk | Too small to claim official-server parity | Harder mapping and scorer reproducibility |

## Server Baselines From Current Score-Table Aggregate

These are raw score-table means from the local official aggregate, not the CASP
HTML z-score ranking:

| Track | Comparator | Group | Mean fixed score | Metric | Targets |
| --- | --- | --- | ---: | --- | ---: |
| Protein domains | best all-group | `022` | 0.926510 | `GDT_TS` | 71 |
| Protein domains | best server-group | `110s` | 0.923321 | `GDT_TS` | 71 |
| Protein oligos | best all-group | `051` | 0.606500 | `QSglob` | 104 |
| Protein oligos | best server-group | `456s` | 0.582615 | `QSglob` | 104 |

CASP also publishes z-score based rankings, which are not identical to raw
mean metric rankings. The official domain z-score page states that group
ranking is based on z-scores for `GDT_TS` and separates server groups on all
groups plus server-only targets:

https://predictioncenter.org/casp16/zscores_final.cgi

## Metric Requirements

### Protein Domains

Goal: reproduce `GDT_TS` as used by the official protein-domain score table.

Required pieces:

- domain-level target list from the official score table and domain summary
- residue/domain crop mapping for both reference and prediction
- chain mapping for multi-chain source targets
- a scorer that reports `GDT_TS`, not just TM-score
- normalized leaderboard value in `0..1` (`GDT_TS / 100` if a tool reports
  percentages)

TM-score, lDDT, and confidence are useful diagnostics, but they are not
substitutes for the ranked domain score.

### Protein Oligos

Goal: reproduce `QSglob` as used by the official protein-oligo score table.

Required pieces:

- biological assembly reference, not merely an asymmetric-unit file
- exact target stoichiometry and chain/entity mapping
- symmetry-aware chain assignment
- a scorer that reports `QSglob`
- DockQ retained only as an interface diagnostic unless it is explicitly
  converted into a validated official-compatible proxy

DockQ and `QSglob` answer related but different questions. DockQ is strongest
for interface-level quality; `QSglob` is an assembly-level quaternary-structure
score. A method can have good local DockQ on some interfaces and still lose the
official oligo ranking if assembly stoichiometry or global chain placement is
wrong.

## Anti-Oracle Rules

This benchmark should inherit the existing anti-oracle policy:

- no reference/native structures during strategy design or prediction
- no official score-table rows for per-target tuning
- no previous `target_scores.csv` rows for per-target parameter selection
- no confidence-as-quality replacement
- missing, failed, or metric-unavailable targets score `0`

The server-style benchmark should also record whether a method required human
per-target intervention. A fully server-like run should be automatic across the
whole target set.

## Build Phases

1. Done: add benchmark skeleton:
   `benchmarks/casp16_server_protein_v1/benchmark.json`,
   `targets.tsv`, `references.tsv`, `domain_definitions.tsv`,
   `inputs.json`, `input_manifest.tsv`, and `scoring_policy.md`.
2. Done: derive ranked target sets directly from the official `prot_domains` and
   `prot_oligo` score tables instead of the current local eligibility filter.
3. Partial: domain scoring now requires parsed `GDT_TS` and uses the configured
   TMscore/USalign path by default. Next, add explicit domain cropping and
   chain/residue mapping.
4. Partial: oligo scoring now requires a `QSglob` scorer, refuses DockQ as a
   ranked substitute, and can parse OpenStructure `ost compare-structures
   --qs-score` JSON when an `ost` binary is available. Next, install/vendor a
   real scorer plus assembly mapping. Keep DockQ as a diagnostic column.
5. Done: add `leaderboards/casp16_server_protein_v1/` artifacts:
   `RESULTS.md`, `runs.csv`, `target_scores.csv`, `coverage.md`,
   `official_server_groups.csv`, `official_all_groups.csv`, and
   `artifacts_manifest.json`.
6. Done: validate with a fixture proving that server-only missing coverage cannot
   outrank broad coverage.

## First Experiments After The Benchmark Exists

- Re-score the best current OpenDDE run on the official-compatible target set.
- Install OpenStructure `ost` or another validated `QSglob` scorer before
  treating any server oligo run as rank-eligible.
- Separate automatic full-target runs from manual rescue runs.
- Add Yang-Server-style input optimization as strategy code, not benchmark
  edits: disorder trimming, domain decomposition, MSA/template breadth, and
  model ranking.
- For oligos, prioritize stoichiometry/assembly correctness before interface
  polishing.
- Create an alias-fixed `casp16_server_protein_v2_aliasfix` or equivalent
  before making winner-comparison claims from local scores.
