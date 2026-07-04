# CASP16 Local Leaderboard

Static, local CASP16 leaderboard infrastructure. It ingests official CASP16
metadata and score tables, generates Protenix input JSON, records reproducible
run specs, and emits CSV/Markdown leaderboards.

The repository intentionally keeps large official score-table downloads and
per-model prediction outputs out of git. They are reproducible with the CLI
commands below.

## Quick Start

```bash
cd /scratch/10992/liaorunlong93/casp16-leaderboard
./casp16 ingest
./casp16 make-inputs
./casp16 run-spec --run-id baseline_no_msa
./casp16 collect
./casp16 leaderboard
```

Generated files are written under:

- `data/official/` for cached official CASP16 files and parsed TSVs
- `data/inputs/` for generated Protenix JSON inputs and manifests
- `runs/` for run specs and command scripts
- `leaderboards/` for Markdown/CSV summaries

The default Protenix and DockQ executables are:

- `/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix`
- `/scratch/10992/liaorunlong93/conda/envs/protein/bin/DockQ`

USalign, TMscore, and lDDT are optional. If missing, local structure-quality
metrics are marked as `metric_unavailable` while official score-table
leaderboards still work.

## Current V1 Coverage

The implemented path fully regenerates the official-compatible CASP16 static
leaderboards from official score tables and generates Protenix-ready inputs for
all CASP16 targets with available sequence records. Local prediction collection
is wired through `runs/*/run_spec.json`; native-reference structural scoring is
explicitly marked unavailable until native target/reference mapping and optional
metric tools are installed.

Validated locally:

- official targets parsed: 301
- official scored records parsed: 95,268 raw / 95,236 usable scored rows
- Protenix jobs generated: 202
- tests: `12 passed`
