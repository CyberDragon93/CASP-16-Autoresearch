# Coverage + Stoichiometry Attack Status

- Run ID: `server_attack_protenix_coverage_stoich_seed101_105`
- Benchmark: `casp16_server_protein_v1`
- Tier: `server_attack`, `protenix5`
- Status: queued, not submitted
- Budget: seeds `101,102,103,104,105`, sample `1`, MSA/templates/default params enabled
- Selector: `protenix_confidence_v1`
- Input strategy:
  `yang_oligo_stoichiometry_token_safe_v1`, which starts from sequence
  recovery + large-target fallback and restores token-safe oligo stoichiometry.

Purpose: spend the same five-candidate attack budget on inputs that remove
known hard zeros before sampling, rather than repeating the terminal-tag-only
attack forever.

Launch only after the current running attack and earlier queued coverage
single-seed runs have either completed or been intentionally superseded. Check:

```bash
./casp16 run-next --benchmark casp16_server_protein_v1 --dry-run
```

Submit `run_gh200.slurm` only when this run is the selected pending run.
