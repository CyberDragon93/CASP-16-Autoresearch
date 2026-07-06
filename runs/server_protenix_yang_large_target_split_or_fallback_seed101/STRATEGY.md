# Strategy Record: server_protenix_yang_large_target_split_or_fallback_seed101

## Run

- Run ID: `server_protenix_yang_large_target_split_or_fallback_seed101`
- Strategy name: `yang_large_target_split_or_fallback_v1`
- Parent run: `server_protenix_yang_oversize_domain_monomer_fallback_seed101`
- Benchmark: `casp16_server_protein_v1`
- Budget tier: `dev_fixed`

## Hypothesis

The current full Protenix runs lose eight server-benchmark jobs before
prediction because Protenix rejects `n_token > 2560`. Extra seeds will not fix
hard input-size failures. A target-agnostic chain/copy fallback should convert
those hard zeros into predictions while leaving all under-budget jobs unchanged.

This is a coverage-recovery run, not an assembly-quality claim. Some complex
targets drop chains to fit the budget, so oligo quality may regress even if
prediction coverage improves.

## Changed Knobs

- Input strategy: `yang_large_target_split_or_fallback_v1`
- Only oversized protein-only jobs are changed.
- Oversized jobs first receive conservative epitope/His/TEV cleanup.
- If still oversized, the original-order prefix of chains or chain copies that
  fits within 2560 tokens is kept.

Changed targets in the generated manifest:

- `T1295`: keep chains `A,B,C,D,E`; drop `F,G,H`.
- `H0217`: keep `A,B,C,D,E`; drop `F`.
- `H0258`: clean tags, keep `A`; drop `B`.
- `H0272`: keep `B,C,D,E,F,G,I`; drop `A,H`.
- `H1217`: keep `A,B,C,D,E`; drop `F`.
- `H1258`: clean tags, keep `A`; drop `B`.
- `H1272`: keep `B,C,D,E,F,G,I`; drop `A,H`.
- `T1295O`: keep chains `A,B,C,D,E`; drop `F,G,H`.

## Unchanged Fixed Budget

- Backend: `protenix`
- Model: `protenix-v2`
- Seed: `101`
- Sample: `1`
- Selected model policy: `first_output_only`
- MSA: enabled
- Template: enabled
- Default params: enabled
- Cache/fusion/TF32: enabled
- dtype: `bf16`

## Commands

```bash
./casp16 strategy-inputs \
  --benchmark casp16_server_protein_v1 \
  --strategy yang_large_target_split_or_fallback_v1
```

```bash
./casp16 run-spec \
  --run-id server_protenix_yang_large_target_split_or_fallback_seed101 \
  --benchmark casp16_server_protein_v1 \
  --input-json strategies/yang_large_target_split_or_fallback_v1/casp16_server_protein_v1/inputs.json \
  --input-manifest strategies/yang_large_target_split_or_fallback_v1/casp16_server_protein_v1/manifest.tsv \
  --strategy yang_large_target_split_or_fallback_v1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32
```

After the active attack job completes:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && sbatch runs/server_protenix_yang_large_target_split_or_fallback_seed101/run_gh200.slurm'
```

## Result Summary

- Run status: pending; not submitted while attack job `810719` is pending.
- Rank status: pending until predictions finish and scoring is regenerated.
- Expected target jobs: 106.
- Expected coverage effect: the eight known token-limit failures should reach
  Protenix inference, though some will still score `0` until references or
  QSglob are available.

## No Oracle Checklist

- [x] No native/reference structures are read during prediction.
- [x] No official score tables are read during prediction.
- [x] No previous `target_scores.csv` rows are used for per-target tuning.
- [x] The fallback rule is generated from input size and sequence-only cleanup.
- [x] Dropped chains are recorded before scoring.

