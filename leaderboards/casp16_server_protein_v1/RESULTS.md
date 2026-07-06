# CASP16 Server Protein V1 Results

Runs are ranked over fixed eligible target sets. Missing predictions, failed metrics, and unavailable metrics score 0.

## protein_domain

| rank | run | status | policy | mean | eligible | ok | missing | failed | metric unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | server_protenix_yang_terminal_tag_cleanup_seed101 | ranked | first_output_only | 0.066908 | 71 | 15 | 30 | 26 | 0 |
| 2 | server_protenix_yang_oversize_domain_monomer_fallback_seed101 | ranked | first_output_only | 0.065114 | 71 | 15 | 29 | 27 | 0 |
| 3 | server_protenix_full_msa_template_seed101 | ranked | first_output_only | 0.063962 | 71 | 15 | 30 | 26 | 0 |
| 4 | server_protenix_yang_antibody_fv_cleanup_seed101 | ranked | first_output_only | 0.060677 | 71 | 15 | 30 | 26 | 0 |
|  | server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1 | unranked:run_not_rank_eligible | first_output_only | 0.036428 | 71 | 9 | 62 | 0 | 0 |
|  | server_attack_protenix_terminal_tag_seed101_105 | pending:no_scored_targets | protenix_confidence_v1 | 0.000000 | 71 | 0 | 71 | 0 | 0 |
|  | server_protenix_yang_epitope_tag_cleanup_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 71 | 0 | 71 | 0 | 0 |
|  | server_protenix_yang_large_target_split_or_fallback_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 71 | 0 | 71 | 0 | 0 |
|  | server_protenix_yang_sequence_recovery_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 71 | 0 | 71 | 0 | 0 |
|  | server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 71 | 0 | 71 | 0 | 0 |

## protein_oligo

| rank | run | status | policy | mean | eligible | ok | missing | failed | metric unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | server_attack_protenix_terminal_tag_seed101_105 | pending:no_scored_targets | protenix_confidence_v1 | 0.000000 | 104 | 0 | 104 | 0 | 0 |
|  | server_eval_opendde_v1_full_msa_template_bf16_h1220_t1220s1 | unranked:run_not_rank_eligible | first_output_only | 0.000000 | 104 | 0 | 85 | 0 | 19 |
|  | server_protenix_full_msa_template_seed101 | unranked:metric_unavailable | first_output_only | 0.000000 | 104 | 0 | 47 | 30 | 27 |
|  | server_protenix_yang_antibody_fv_cleanup_seed101 | unranked:metric_unavailable | first_output_only | 0.000000 | 104 | 0 | 47 | 30 | 27 |
|  | server_protenix_yang_epitope_tag_cleanup_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 104 | 0 | 104 | 0 | 0 |
|  | server_protenix_yang_large_target_split_or_fallback_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 104 | 0 | 104 | 0 | 0 |
|  | server_protenix_yang_oversize_domain_monomer_fallback_seed101 | unranked:metric_unavailable | first_output_only | 0.000000 | 104 | 0 | 47 | 30 | 27 |
|  | server_protenix_yang_sequence_recovery_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 104 | 0 | 104 | 0 | 0 |
|  | server_protenix_yang_terminal_tag_antibody_fv_cleanup_seed101 | pending:no_scored_targets | first_output_only | 0.000000 | 104 | 0 | 104 | 0 | 0 |
|  | server_protenix_yang_terminal_tag_cleanup_seed101 | unranked:metric_unavailable | first_output_only | 0.000000 | 104 | 0 | 47 | 30 | 27 |
