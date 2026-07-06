# Small Complex Stoichiometry Target Lab

This target-lab batch collects small and medium protein-complex experiments
that can produce faster learning signals than a full 175-target server run. It
is not a ranked leaderboard strategy.

## Jobs

- `H1232`: exact `A2B2` stoichiometry from
  `yang_oligo_stoichiometry_token_safe_v1`.
- `H1233`: exact `A2B2C2` stoichiometry.
- `H1236`: exact `A3B6` stoichiometry.
- `H1244`: exact `A2B2C2` stoichiometry.
- `H1267`: exact `A2B2` stoichiometry.
- `H1258_target_lab_lrrk2_861_1014_A1B2`: public LRRK2 interaction-window
  target_lab artifact.

The largest job is 1929 tokens, below the 2560-token Protenix budget.

## Purpose

Use this batch to learn whether exact stoichiometry and the H1258 public
interaction-window trick produce better complex predictions before promoting a
target-agnostic rule to the full benchmark queue.

## Run

```bash
bash target_lab/small_complex_stoich_batch_v1/run_protenix.sh
```

Outputs are written under:

```text
target_lab/small_complex_stoich_batch_v1/predictions/protenix-v2/
```

Do not register this as a ranked run. Any promotion must become a predeclared
full-benchmark strategy and must not use target_lab scores as per-target
oracles.

## Summarize

After the job finishes, regenerate the diagnostic summary:

```bash
python target_lab/small_complex_stoich_batch_v1/summarize_outputs.py
```

This writes:

- `summary.tsv`
- `SUMMARY.md`

The summary reports prediction/confidence file coverage and confidence
diagnostics only. It is not a structure-quality score.
