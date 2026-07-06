# H1258 Interaction Window Target Lab

This is a target-lab artifact for the H1258 LRRK2/14-3-3 complex. It is not a
ranked leaderboard strategy.

## Rationale

The CASP16 protein-complex assessment preprint notes that top Yang H1258 models
used the interacting LRRK2 region rather than the full-length LRRK2 chain. This
artifact turns that public clue into a small, reproducible Protenix input:

- LRRK2 chain A: residues 861-1014 after removing the N-terminal epitope tag.
- 14-3-3 chain: epitope/His/TEV tag removed.
- Stoichiometry: A1B2.
- Total token length: 648.

This target-specific window must remain in `target_lab/` unless it is later
converted into a target-agnostic rule and rerun across the full benchmark.

## Files

- `inputs.json`: one Protenix job named
  `H1258_target_lab_lrrk2_861_1014_A1B2`.
- `manifest.tsv`: source input, residue window, lengths, rules, and SHA256.
- `run_protenix.sh`: manual target-lab command using the same Protenix engine
  flags as full benchmark runs.

## Run

```bash
bash target_lab/h1258_interaction_window_v1/run_protenix.sh
```

Outputs are written under:

```text
target_lab/h1258_interaction_window_v1/predictions/protenix-v2/
```

Do not register this as a ranked `casp16_server_protein_v1` run. Use it to
learn whether the public interaction-window trick is worth promoting into a
predeclared, target-agnostic construct/window strategy.
