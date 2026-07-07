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
  --output-tsv data/msa_cache/index.tsv \
  --materialize-cache \
  --incremental

./casp16 msa-cache-report \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json <new_inputs.json>

./casp16 check-msa-cache \
  --input-json <new_inputs.json> \
  --require-complete

./casp16 run-spec \
  --run-id <run_id> \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json <new_inputs.json> \
  --strategy <strategy_name> \
  --use-msa --use-template --use-default-params \
  --refresh-global-msa-cache \
  --msa-reuse-require-complete
```

`run-spec` copies the source input into `runs/<run_id>/inputs/`, writes
`inputs.msa-reuse.json`, writes `msa_reuse.tsv`, points the Protenix command at
the cache-reused input, and stores the reuse summary plus source/index hashes in
`run_spec.json`. This is the default path for queued attack runs because it
fails before GPU allocation if cache coverage is lower than declared.
`--refresh-global-msa-cache` first rebuilds `data/msa_cache/index.tsv`
incrementally, materializes any newly discovered A3M files into
`data/msa_cache/store/`, writes `data/msa_cache/manifest.json`, and then uses
that refreshed global index for the run spec.

`check-msa-cache` is the read-only preflight for planning and queue notes. It
uses the same exact-sequence matcher as `run-spec`, writes a diagnostics TSV,
and can fail with `--require-complete` or `--min-reuse-fraction` before any
run directory is created.

`msa-cache-report` is the higher-level planning view. It summarizes global cache
health, per-input chain and residue coverage, stale index rows ignored, and the
longest target chains that would need fresh MSA search. Use it before deciding
whether a strategy input is ready for an attack shard or should first wait for a
cache-refresh/dev row. Its Markdown and TSV outputs live under
`diagnostics/msa_cache/`.

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

When `--materialize-cache` is passed, the command also copies paired/unpaired
MSA files into an ignored content-addressed local store under
`data/msa_cache/store/` and points `data/msa_cache/index.tsv` at those stable
paths. The index then survives cleanup of old source run prediction directories.
When `--incremental` is passed, usable rows from the existing index are merged
before newly discovered source JSONs are added. This prevents a refresh from
dropping older materialized sequences just because their original run directory
was cleaned or is no longer part of the discovery filter.
The cache manifest is written to `data/msa_cache/manifest.json` with the index
hash and materialization summary; both files are derived local artifacts and
remain ignored by Git.

The reuse command injects MSA paths only by exact protein sequence SHA256. If
the sequence was trimmed, windowed, recovered, or otherwise changed, it misses
and Protenix will search MSA normally. Existing valid MSA paths in the input are
kept unless `--overwrite-existing` is set.

Use `--msa-source-run-id` on `run-spec` or `--source-run-id` on `reuse-msa` for
normal repo workflows; it resolves
`runs/<run_id>/inputs/inputs-update-msa.json` and falls back to
`inputs-final-updated.json` when present. Use `--msa-cache-index` on
`run-spec` or `--cache-index` on `reuse-msa` for multi-run reuse across attack
shards and strategy variants. `run-spec --reuse-global-msa-cache` is the
preferred shorthand for explicitly using `data/msa_cache/index.tsv`.
`check-msa-cache` and `reuse-msa` default to that global index when no explicit
source/index is supplied and the file exists. Use `--msa-source-json` only when
the source is outside the repo's `runs/` tree.

For attack shards that are expected to reuse every unchanged chain, use
`--require-complete`. For ablations where some sequences intentionally change,
use `--min-reuse-fraction <fraction>` and inspect the TSV report before launch.
The JSON summary reports `reused`, `kept_existing`, `covered`,
`coverage_fraction`, and `missing_source`. The TSV report also records whether
each paired/unpaired MSA path exists and its current file size.

`run-next --dry-run` and `run-next` now audit `runs/<run_id>/inputs/msa_reuse.tsv`
before launch. If a path that was recorded as reused or kept-existing has gone
stale, the run is blocked as `blocked:msa_preflight` instead of silently letting
Protenix redo MSA search. Rebuild the index and recreate the run spec after
moving or deleting source run directories.

## Rules

- Reuse MSA only for exact sequence matches.
- Do not reuse by target id alone; construct changes can share a target id but
  require a new MSA.
- Missing or stale MSA path means no reuse.
- A cache-reused run must pass `run-next --dry-run` before Slurm submission.
- Treat MSA source JSON and reuse report as run artifacts, not benchmark files.
- Treat `data/msa_cache/index.tsv`, `data/msa_cache/manifest.json`, and
  `data/msa_cache/store/` as derived local cache artifacts; rebuild them from
  run artifacts when source runs change.
- Run `msa-cache-report` on any new MSA-heavy strategy input before creating
  multi-seed or sharded run specs; if it reports fresh MSA chains, explicitly
  decide whether the new sequences are intended strategy changes or avoidable
  duplicate search.
- Prefer `run-spec --refresh-global-msa-cache` for attack runs so the global
  exact-sequence index is refreshed from completed/running MSA artifacts before
  reuse is locked into `runs/<run_id>/inputs/msa_reuse.tsv`.
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
2. If the current scoreable `protenix5` row is superseded or needs a faster
   oligo signal, use
   `scoreable_target_subset_oligo_first_v1` as the successor input. It is
   derived from the same 74-job scoreable artifact, moves all 50 exact
   `protein_oligo` jobs to the front, and still preflights at 141/141
   exact-sequence protein-chain MSA paths with 0 fresh-MSA chains.
3. The domain-sequence-recovery nofail ablation,
   `server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_seed101`, is the
   exception that intentionally allows fresh MSA. It reuses 269/276 chains from
   the global cache and sets `--msa-reuse-min-fraction 0.97` so only the 7
   repaired protein-domain chains pay new MSA cost.
4. The older v1 coverage/stoich attack has a cache-reuse successor,
   `server_attack_protenix_coverage_stoich_msa_reuse_seed101_105`, but its
   preflight reuses only 180/196 exact-sequence protein-chain paths and misses
   16. Keep it behind the v2 scoreable nofail path unless a specific ablation
   needs the v1 stack.
5. Keep the older full-input MSA-reuse attack as an ablation only until the
   missing references are recovered. Its 165-job input repeats expensive
   no-reference jobs such as `T1295/T1295O`, which cannot improve current local
   score because missing references score 0.
6. For planned `protenix25_nofail` seed shards, build every shard input from
   the same MSA cache index or the same MSA-reused artifact. The five shards
   should not each repeat MSA search for the same 165 jobs.
7. For strategy ablations, reuse only unchanged chains. The TSV report should
   show which changed chains will force fresh MSA search.

## Next Upgrade Path

1. Keep the current index as the default while source run directories are stable.
   It is cheap, exact-sequence safe, and avoids copying large MSA artifacts.
2. Keep the preflight gate in every Slurm wrapper: rebuild the index when
   sources change, run `check-msa-cache`, create the run spec with
   `--msa-reuse-require-complete` or a declared `--msa-reuse-min-fraction`, and
   include the JSON summary in the job notes.
3. Use `--materialize-cache --incremental` before launching multi-shard attack
   budgets, or use `run-spec --refresh-global-msa-cache` when creating the run.
   This promotes the cache to a content-addressed local store under ignored
   scratch storage, keyed by sequence SHA256 and MSA file SHA256, while keeping
   older materialized rows available for later strategy variants.
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
