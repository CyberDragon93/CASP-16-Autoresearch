# MSA Cache Report

Generated: 2026-07-07T00:18:00.406325+00:00

## Cache Health

- index paths: /scratch/10992/liaorunlong93/casp16-leaderboard/data/msa_cache/index.tsv
- usable sequence records: 105
- stale index rows ignored: 0
- paired/unpaired records: 105 / 105
- total indexed MSA bytes: 319657188
- sequence length range: 41-3696

Top source runs:

| source run | records |
| --- | ---: |
| `server_v2_protenix_yang_oligo_sequence_stoich_low_complexity_large_fallback_seed101` | 84 |
| `server_protenix_yang_antibody_fv_cleanup_seed101` | 8 |
| `server_protenix_yang_terminal_tag_cleanup_seed101` | 8 |
| `server_protenix_yang_oversize_domain_monomer_fallback_seed101` | 5 |

## Input Coverage

| input | chains | residues | covered | chain coverage | residue coverage | fresh chains | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `casp16_server_protein_v2_aliasfix` | 264 | 114316 | 264 | 1.000 | 1.000 | 0 | complete |
| `strategies_scoreable_target_subset_v1_casp16_server_protein_v2_aliasfix_inputs` | 141 | 53062 | 141 | 1.000 | 1.000 | 0 | complete |
| `strategies_scoreable_target_subset_oligo_first_v1_casp16_server_protein_v2_aliasfix_inputs` | 141 | 53062 | 141 | 1.000 | 1.000 | 0 | complete |
| `strategies_yang_domain_sequence_recovery_oligo_nofail_v1_casp16_server_protein_v2_aliasfix_inputs` | 276 | 109533 | 269 | 0.975 | 0.971 | 7 | fresh_msa_needed |

## Fresh MSA Needed: strategies_yang_domain_sequence_recovery_oligo_nofail_v1_casp16_server_protein_v2_aliasfix_inputs

| task | chain | residues | sequence sha256 |
| --- | ---: | ---: | --- |
| `T1239V1` | 0 | 620 | `f945ee17b797` |
| `T1239V2` | 0 | 620 | `f945ee17b797` |
| `T1228V1` | 0 | 545 | `f3c6f67c0ca1` |
| `T1228V2` | 0 | 545 | `f3c6f67c0ca1` |
| `T1212` | 0 | 466 | `cadaaf5c2f3f` |
| `T1276` | 0 | 196 | `72bbf972e35b` |
| `T2276` | 0 | 196 | `72bbf972e35b` |
