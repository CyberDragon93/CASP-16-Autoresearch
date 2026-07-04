#!/usr/bin/env bash
set -euo pipefail
export OPENDDE_ROOT_DIR=/scratch/10992/liaorunlong93/opendde_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
mkdir -p logs
exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)
'/scratch/10992/liaorunlong93/conda/envs/protein/bin/opendde' 'pred' '-i' '/scratch/10992/liaorunlong93/casp16-leaderboard/runs/opendde_v1_t1299_msa/inputs/T1299.json' '-o' '/scratch/10992/liaorunlong93/casp16-leaderboard/runs/opendde_v1_t1299_msa/predictions/opendde_v1' '-n' 'opendde_v1' '--seeds' '101' '--use_msa' 'true' '--use_template' 'false' '--use_rna_msa' 'false' '--sample' '1' '--step' '200' '--cycle' '10' '--dtype' 'fp32' '--trimul_kernel' 'auto' '--triatt_kernel' 'auto' '--enable_cache' 'true' '--enable_fusion' 'true' '--enable_tf32' 'true'
