# CASP16 Local Leaderboard

Nanochat-style local CASP16 leaderboard infrastructure. It ingests official
CASP16 data, builds a locked protein-first benchmark, records reproducible run
specs, scores available local predictions against references, and emits static
CSV/Markdown leaderboard artifacts.

The repository intentionally keeps large official score-table downloads and
per-model prediction outputs out of git. They are reproducible with the CLI
commands below.

## Quick Start

```bash
cd /scratch/10992/liaorunlong93/casp16-leaderboard
./casp16 ingest
./casp16 benchmark --download-references
./casp16 run-spec --run-id baseline_no_msa --benchmark casp16_protein_v1
./casp16 list-runs --benchmark casp16_protein_v1
./casp16 run-next --benchmark casp16_protein_v1 --dry-run
./casp16 score --benchmark casp16_protein_v1
./casp16 leaderboard --benchmark casp16_protein_v1
```

## Agent Workflow

Agents and humans making leaderboard-facing strategy changes must start with
`AGENTS.md`. The detailed fairness contract is in
`docs/LEADERBOARD_RULES.md`, and new strategy notes should use
`docs/STRATEGY_TEMPLATE.md`.

Generated files are written under:

- `data/official/` for cached official CASP16 files and parsed TSVs
- `benchmarks/casp16_protein_v1/` for locked benchmark inputs, targets,
  references, and scoring policy
- `runs/` for run specs, append-only status, manifest, command scripts, and
  stdout/stderr paths
- `leaderboards/casp16_protein_v1/` for `RESULTS.md`, `runs.csv`,
  `target_scores.csv`, `coverage.md`, `official_groups.csv`, and
  `artifacts_manifest.json`

The default Protenix and DockQ executables are:

- `/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix`
- `/scratch/10992/liaorunlong93/conda/envs/protein/bin/DockQ`

TMscore/TMscore64/USalign is required for ranked protein-domain scoring, and
DockQ is required for ranked protein-oligo scoring. Missing predictions, failed
metrics, and unavailable metric tools score `0`; confidence files are collected
only as diagnostics and are never used as quality scores.

## Current Protein V1 Coverage

The ranked benchmark is deliberately conservative. Protein domain and protein
oligo targets enter ranking only when sequence input, reference structure, and
the current v1 mapping rules are explicit. RNA, hybrid, ligand, cancelled,
missing-sequence, no-reference, and unmapped targets remain visible in coverage
reports with skip reasons.

Validated locally:

- official targets parsed: 301
- official target references parsed from targetlist HTML: 88
- official domain definitions parsed: 85
- official scored records parsed: 95,268 raw / 95,236 usable scored rows
- benchmark Protenix jobs generated: 128
- benchmark rank-eligible targets: 31
- tests: `23 passed`

The legacy commands still work:

```bash
./casp16 make-inputs
./casp16 collect
./casp16 leaderboard
```
