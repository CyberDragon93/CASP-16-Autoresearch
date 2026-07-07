# yang_protein_oligo_sequence_stoich_phase_alias_v1

Purpose: repair the v2 protein-oligo input stack after finding that early-phase
targets such as `H0220` kept stale local `UNK`/`A1B1` metadata while later
phase aliases such as `H1220/H2220` expose official `A1B4` stoichiometry.

Base input:

- `benchmarks/casp16_server_protein_v2_aliasfix/inputs.json`

Rules:

1. Recover protein-oligo sequences only from official CASP16 sequence aliases.
2. Prefer exact official `Oligo.State`; when it is uninformative, inherit an
   informative phase-alias state such as `H1220 -> H0220`.
3. Apply exact stoichiometry only when the recovered assembly remains under
   Protenix's 2560-token limit.
4. Do not read native/reference structures, official scores, previous target
   scores, or confidence files during input generation.

Generated artifacts:

- `casp16_server_protein_v2_aliasfix/inputs.json`
- `casp16_server_protein_v2_aliasfix/manifest.tsv`

Generation summary:

- jobs: 165
- changed targets: 20
- sequence-recovery changed targets: 5
- oligo-stoich changed targets: 18
- skipped oversize after recovery: 12
- output SHA256:
  `993e3e1d03b4e461c0aaa5682ac4cc3ca0549d4346db5b9610844d7320484717`

Key check:

- `H0220/H1220/H2220` are recovered protein `A1B4` jobs with total length
  2515, below the Protenix limit.

