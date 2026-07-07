# Domain Sequence Recovery MSA Warmup V1

This is a rank-ineligible warmup for the D6a domain input-repair branch.

The full `yang_domain_sequence_recovery_oligo_nofail_v1` artifact has 7
fresh-MSA chains, but those collapse to 4 unique recovered protein sequences:

- `T1239V1` also covers `T1239V2`
- `T1228V1` also covers `T1228V2`
- `T1276` also covers `T2276`
- `T1212`

The warmup input keeps only those first-alias representatives. Its purpose is
to let Protenix generate real full-MSA/template artifacts once, so a later full
D6a ablation can rebuild the global MSA cache and avoid repeating those four
fresh searches across the 169-job input.

The exact missing-sequence collapse is recorded in:

```text
diagnostics/msa_cache/domain_sequence_recovery_msa_warmup_unique_missing.tsv
```

Rules:

- rank eligible: false
- benchmark files: unchanged
- references and official scores: not read during prediction
- use MSA/templates/default Protenix settings; this is not a no-MSA toy run
- do not treat warmup predictions as a server leaderboard result

Prepared run:

```bash
ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && \
  RUN_ID=server_v2_domain_sequence_recovery_msa_warmup_seed101 \
  sbatch slurm/casp16_run_one_gh200.slurm'
```

Submit only after the active P14 scoreable target shards are handled, or when a
compute slot is explicitly allocated to D6a input repair.

After the warmup completes, refresh the materialized global cache and recreate
the full D6a run spec with a complete-MSA guard:

```bash
./casp16 build-msa-cache \
  --benchmark casp16_server_protein_v2_aliasfix \
  --run-id server_v2_domain_sequence_recovery_msa_warmup_seed101 \
  --output-tsv data/msa_cache/index.tsv \
  --materialize-cache \
  --incremental

./casp16 run-spec \
  --run-id server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101 \
  --benchmark casp16_server_protein_v2_aliasfix \
  --input-json strategies/yang_domain_sequence_recovery_oligo_nofail_v1/casp16_server_protein_v2_aliasfix/inputs.json \
  --input-manifest benchmarks/casp16_server_protein_v2_aliasfix/input_manifest.tsv \
  --strategy yang_domain_sequence_recovery_oligo_nofail_v1_after_warmup \
  --seeds 101 \
  --sample 1 \
  --use-msa --use-template --use-default-params \
  --enable-cache --enable-fusion --enable-tf32 \
  --reuse-global-msa-cache \
  --msa-reuse-require-complete
```

Only score the recreated full D6a run, not this warmup.
