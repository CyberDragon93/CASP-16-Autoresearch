# yang_sequence_recovery_v1

This strategy repairs obvious CASP16 protein-domain input coverage failures
without mutating the locked benchmark.

Base input:

- `strategies/yang_terminal_tag_cleanup_v1/casp16_server_protein_v1/inputs.json`

Rules:

1. Keep existing terminal-tag-cleaned jobs.
2. For protein-domain jobs whose generated input is missing or uses a
   non-protein entity type, recover official sequence records that are
   protein-like by alphabet/header.
3. Support conservative aliases used by CASP16 metadata:
   - `V2` can reuse matching `V1` sequence records when the V2 sequence is
     absent.
   - `T2xxx` can reuse matching `T1xxx`/`T0xxx` sequence records.
4. Emit recovered jobs as `proteinChain` and record source records in the
   manifest.

This does not read native/reference structures, official scores, or previous
target scores. It is intended to recover target coverage where the official
sequence archive contains protein sequences that were locally parsed or aliased
incorrectly.

High-value recovered examples:

- `T1212`: protein sequence was duplicated in the RDM archive and previously
  collided with a misclassified RNA record.
- `T1239V1`: protein-like sequence was previously parsed as `dnaSequence`.
- `T1239V2`: V2 reuses the available V1 protein sequence.
- `T2280`: reuses the earlier `T1280` protein sequence for the same gp155
  domain description.

