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

Preferred run creation path:

```bash
./casp16 build-msa-cache \
  --benchmark casp16_server_protein_v2_aliasfix \
  --output-tsv data/msa_cache/index.tsv

./casp16 run-spec \
  --run-id <run_id> \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json <new_inputs.json> \
  --strategy <strategy_name> \
  --use-msa --use-template --use-default-params \
  --msa-cache-index data/msa_cache/index.tsv \
  --msa-reuse-require-complete
```

`run-spec` copies the source input into `runs/<run_id>/inputs/`, writes
`inputs.msa-reuse.json`, writes `msa_reuse.tsv`, points the Protenix command at
the cache-reused input, and stores the reuse summary plus source/index hashes in
`run_spec.json`. This is the default path for queued attack runs because it
fails before GPU allocation if cache coverage is lower than declared.

Manual input rewriting remains available for debugging or strategy artifact
generation:

```bash
./casp16 reuse-msa \
  --input-json <new_inputs.json> \
  --cache-index data/msa_cache/index.tsv \
  --output-json <new_inputs.with_msa.json> \
  --report-tsv <msa_reuse.tsv> \
  --require-complete
```

The index command scans existing Protenix runs with `use_msa=true`, reads their
run-local `inputs-update-msa.json` or `inputs-final-updated.json`, and writes a
small TSV keyed by exact protein sequence SHA256. It records source run, source
task, source JSON hash, paired/unpaired MSA paths, and file sizes. Large MSA
files stay in the original run directories.

The reuse command injects MSA paths only by exact protein sequence SHA256. If
the sequence was trimmed, windowed, recovered, or otherwise changed, it misses
and Protenix will search MSA normally. Existing valid MSA paths in the input are
kept unless `--overwrite-existing` is set.

Use `--msa-source-run-id` on `run-spec` or `--source-run-id` on `reuse-msa` for
normal repo workflows; it resolves
`runs/<run_id>/inputs/inputs-update-msa.json` and falls back to
`inputs-final-updated.json` when present. Use `--msa-cache-index` on
`run-spec` or `--cache-index` on `reuse-msa` for multi-run reuse across attack
shards and strategy variants. Use `--msa-source-json` only when the source is
outside the repo's `runs/` tree.

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
- Treat `data/msa_cache/index.tsv` as a derived local cache manifest; rebuild it
  from run artifacts when source runs change.
- Report `reused`, `kept_existing`, and `missing_source` counts in strategy
  notes before launching a cache-reused run.
- Use a coverage guard (`--require-complete` or `--min-reuse-fraction`) for
  queued attack runs so a typo in the cache source cannot silently trigger a
  full MSA rerun.

## Priority Use Cases

1. Reuse the current v2 no-over-token dev row's validated
   `inputs-update-msa.json` for the next attack run, and filter prediction
   inputs to jobs that have at least one locally scoreable benchmark alias.
   The scoreable-subset artifact keeps 74/165 jobs and the run-spec reuses
   141/141 protein-chain MSA paths via `data/msa_cache/index.tsv`. It now backs
   `server_v2_attack_scoreable_oligo_recovery_msa_reuse_protenix5_seed101_105`.
2. Keep the older full-input MSA-reuse attack as an ablation only until the
   missing references are recovered. Its 165-job input repeats expensive
   no-reference jobs such as `T1295/T1295O`, which cannot improve current local
   score because missing references score 0.
3. For planned `protenix25_nofail` seed shards, build every shard input from
   the same MSA cache index or the same MSA-reused artifact. The five shards
   should not each repeat MSA search for the same 165 jobs.
4. For strategy ablations, reuse only unchanged chains. The TSV report should
   show which changed chains will force fresh MSA search.

## Next Upgrade Path

1. Keep the current index as the default while source run directories are stable.
   It is cheap, exact-sequence safe, and avoids copying large MSA artifacts.
2. Add a preflight gate before submitting new Slurm attack jobs: rebuild the
   index, run `run-spec` with `--msa-reuse-require-complete` or a declared
   `--msa-reuse-min-fraction`, and include the JSON summary in the job notes.
3. If run directories start getting deleted or moved, promote the cache to a
   content-addressed local store under ignored scratch storage, keyed by
   sequence SHA256 and MSA file SHA256. The index should then point at stable
   cache paths instead of source run paths.
4. If Protenix exposes a clean MSA-only mode, split expensive MSA generation
   from model inference. Until then, `inputs-update-msa.json` remains the
   practical boundary between search cost and inference cost.
5. Do not broaden matching beyond exact protein sequence without a new rule and
   tests. Target-id, subsequence, or homology-based reuse can easily leak wrong
   alignments into modified constructs.

## Non-Goals

- Do not hand-edit `benchmarks/*` or `leaderboards/*`.
- Do not disable MSA for speed when measuring real performance.
- Do not copy large MSA directories into git. Reuse absolute paths in scratch
  run artifacts and keep reports small.
