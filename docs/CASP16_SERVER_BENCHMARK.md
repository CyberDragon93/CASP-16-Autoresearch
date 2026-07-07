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

## Current Identity

- Current benchmark name: `casp16_server_protein_v2_aliasfix`
- Legacy benchmark name: `casp16_server_protein_v1`, retained for already
  generated/running runs
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
./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix
```

## Budget Tiers

Server protein benchmark versions start with a fixed single-seed development budget:
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

The next planned larger tier is
`attack_budgets/casp16_server_attack_protenix25.json`: 25 fixed Protenix seeds
(`101..125`), one sample per seed, and the same confidence-only selector. It is
planned for `casp16_server_protein_v2_aliasfix` and must run as predeclared
seed shards before any complete row can be scored. The shard manifest is
`attack_budgets/casp16_server_attack_protenix25_shards.tsv`.

`attack_budgets/casp16_server_attack_protenix25_nofail.json` is a separate
planned 25-seed tier for the v2 no-over-token fallback stack. It keeps the same
seeds and selector but uses
`inputs_msa_reuse_from_dev_seed101.json`, whose 165-job input includes
protein-oligo sequence recovery, exact-sequence MSA paths reused for 268/268
protein chains, and 0 jobs above the Protenix 2560-token limit. The shard
manifest is
`attack_budgets/casp16_server_attack_protenix25_nofail_shards.tsv`.

For seed-sharded attack budgets, a single shard remains partial by design. Use
`./casp16 merge-shards` only after every predeclared shard has completed; then
score the merged run with the full declared `candidate_count`.

Existing prediction directories can be registered for diagnostic reuse without
creating a runnable job:

```bash
./casp16 register-existing-run --benchmark casp16_server_protein_v2_aliasfix \
  --run-id <diagnostic_run_id> --output-dir <prediction_dir> --no-rank-eligible
./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix
```

This is for coverage and scorer-gap accounting only. It does not replace a
full fixed-budget server-target run.

Current generated artifacts live under
`benchmarks/casp16_server_protein_v2_aliasfix/`. This alias-fixed skeleton has
175 fixed official targets, 163 generated Protenix jobs, 79 currently cached
references, 67/71 domain inputs ok, 96/104 oligo inputs ok, and 45 unresolved
parsed domain-subtarget diagnostics. Missing references or unresolved mappings
remain in the fixed denominator and score `0` for local runs until the
reference registry is improved.

Reference recovery must create a new benchmark version rather than rewriting
the alias-fixed v2 artifacts. The supported path is an audited reference-map
overlay:

```bash
./casp16 server-benchmark \
  --benchmark casp16_server_protein_v3_refmap \
  --benchmark-version 3 \
  --reference-map diagnostics/reference_gap/accepted_reference_map.tsv \
  --download-references
```

Only `status=accepted` reference-map rows with native provenance, construct
coverage, chain mapping, and scoring mapping are applied. Candidate rows may be
kept in the overlay for audit history, but they do not affect generated
references. Passing `--reference-map` with `casp16_server_protein_v1` or
`casp16_server_protein_v2_aliasfix` is rejected by the CLI.

The review input can be bootstrapped from the existing RCSB exact-sequence
probe:

```bash
./casp16 refmap-review
```

This writes
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_review.tsv`.
The generated rows remain `candidate` or `rejected`; no row becomes accepted
until provenance and mapping are supplied.

Candidate structures can be cached for mapping review with:

```bash
./casp16 refmap-materialize
```

This writes
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_structures.tsv`
and stores ignored mmCIF files under
`diagnostics/reference_gap/refmap_candidate_mmcif/`.

The current candidate worklist can be rendered with:

```bash
./casp16 refmap-audit
```

This writes
`diagnostics/reference_gap/casp16_server_protein_v3_refmap_candidate_audit.md`
and should be read before changing any reference-map row to `accepted`.

`docs/REFERENCE_GAP_AUDIT.md` records a high-impact alias issue: CASP phase
ids such as `T2201` and `H2202` should be allowed to inherit metadata and PDB
references from matching `T1201`/`H1202` rows. A temporary rebuild with
`0xxx/1xxx/2xxx` aliasing raises the skeleton to 163 generated Protenix jobs
and 79 available references. This changes reference mapping and input coverage,
so it was created as `casp16_server_protein_v2_aliasfix` rather than an
in-place rewrite of v1.

The scoring gate now enforces official metric identity: server protein domains
must parse `GDT_TS`, and server protein oligos must parse `QSglob`. TM-score and
DockQ can still be collected as diagnostics for other benchmarks, but they are
not ranked substitutes for the server metrics.

Static leaderboard artifacts live under
`leaderboards/casp16_server_protein_v2_aliasfix/`. In that directory,
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
3. Partial: domain scoring now requires parsed `GDT_TS`, uses the configured
   TMscore/USalign path by default, and applies temporary mmCIF domain crops
   when an accepted refmap row supplies `residue_ranges=...` plus optional
   `reference_chain=...`. Next, promote only provenance-backed reference-map
   rows in a new benchmark version; do not hand-edit v1/v2.
4. Partial: oligo scoring now requires a `QSglob` scorer, refuses DockQ as a
   ranked substitute, and can parse OpenStructure `ost compare-structures
   --qs-score` JSON. OpenStructure 2.11.1 is installed in
   `/scratch/10992/liaorunlong93/conda/envs/ost-qsglob/`; next, validate and
   add explicit assembly/chain mapping where automatic mapping gives false
   zeros. Keep DockQ as a diagnostic column.
5. Done: add `leaderboards/casp16_server_protein_v1/` artifacts:
   `RESULTS.md`, `runs.csv`, `target_scores.csv`, `coverage.md`,
   `official_server_groups.csv`, `official_all_groups.csv`, and
   `artifacts_manifest.json`.
6. Done: validate with a fixture proving that server-only missing coverage cannot
   outrank broad coverage.

## First Experiments After The Benchmark Exists

- Re-score the best current OpenDDE run on the official-compatible target set.
- Validate OpenStructure `ost` assembly/chain mapping before treating any
  server oligo run as rank-eligible.
- Separate automatic full-target runs from manual rescue runs.
- Add Yang-Server-style input optimization as strategy code, not benchmark
  edits: disorder trimming, domain decomposition, MSA/template breadth, and
  model ranking.
- For oligos, prioritize stoichiometry/assembly correctness before interface
  polishing.
- Done: create alias-fixed `casp16_server_protein_v2_aliasfix` before making
  winner-comparison claims from local scores.
