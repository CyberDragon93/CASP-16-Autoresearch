# MSA Cache And Reuse Plan

Goal: stop paying repeated MSA-search cost when a later run uses the exact same
protein sequence as an earlier Protenix run. This is infrastructure for faster
iteration; it does not change scoring rules or benchmark eligibility.

## Current Finding

Protenix writes MSA paths into `inputs-update-msa.json` as
`pairedMsaPath` and `unpairedMsaPath`. Its MSA updater skips search when those
paths already exist. `--enable_cache true` helps model/runtime caching, but it
does not automatically make a new run reuse another run's per-target MSA files.

Multi-seed runs inside one Protenix command already reuse the MSA generated in
that run directory. The repeated cost we need to remove is across separate run
specs, attack shards, and strategy variants that keep some sequences identical.

## Implemented Minimal Path

Use:

```bash
./casp16 reuse-msa \
  --input-json <new_inputs.json> \
  --source-run-id <completed_or_stable_source_run> \
  --output-json <new_inputs.with_msa.json> \
  --report-tsv <msa_reuse.tsv> \
  --require-complete
```

The command injects MSA paths only by exact protein sequence SHA256. If the
sequence was trimmed, windowed, recovered, or otherwise changed, it misses and
Protenix will search MSA normally. Existing valid MSA paths in the input are
kept unless `--overwrite-existing` is set.

Use `--source-run-id` for normal repo workflows; it resolves
`runs/<run_id>/inputs/inputs-update-msa.json` and falls back to
`inputs-final-updated.json` when present. Use `--msa-source-json` only when the
source is outside the repo's `runs/` tree.

For attack shards that are expected to reuse every unchanged chain, use
`--require-complete`. For ablations where some sequences intentionally change,
use `--min-reuse-fraction <fraction>` and inspect the TSV report before launch.
The JSON summary reports `reused`, `kept_existing`, `covered`,
`coverage_fraction`, and `missing_source`.

## Rules

- Reuse MSA only for exact sequence matches.
- Do not reuse by target id alone; construct changes can share a target id but
  require a new MSA.
- Missing or stale MSA path means no reuse.
- Treat MSA source JSON and reuse report as run artifacts, not benchmark files.
- Report `reused`, `kept_existing`, and `missing_source` counts in strategy
  notes before launching a cache-reused run.
- Use a coverage guard (`--require-complete` or `--min-reuse-fraction`) for
  queued attack runs so a typo in the cache source cannot silently trigger a
  full MSA rerun.

## Priority Use Cases

1. Reuse the current v2 no-over-token dev row's validated
   `inputs-update-msa.json` for the next attack run. The generated artifact
   `inputs_msa_reuse_from_dev_seed101.json` reused 268/268 protein-chain MSA
   records and now backs
   `server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105`.
2. For planned `protenix25_nofail` seed shards, build every shard input from
   the same MSA-reused artifact. The five shards should not each repeat MSA
   search for the same 165 jobs.
3. For strategy ablations, reuse only unchanged chains. The TSV report should
   show which changed chains will force fresh MSA search.

## Non-Goals

- Do not hand-edit `benchmarks/*` or `leaderboards/*`.
- Do not disable MSA for speed when measuring real performance.
- Do not copy large MSA directories into git. Reuse absolute paths in scratch
  run artifacts and keep reports small.
