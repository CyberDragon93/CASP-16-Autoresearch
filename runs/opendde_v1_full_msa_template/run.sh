#!/usr/bin/env bash
set -euo pipefail
export OPENDDE_ROOT_DIR=/scratch/10992/liaorunlong93/opendde_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
export LAYERNORM_TYPE=torch
mkdir -p logs predictions/opendde_v1
exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)
/scratch/10992/liaorunlong93/conda/envs/protein/bin/opendde pred -i /scratch/10992/liaorunlong93/casp16-leaderboard/runs/opendde_v1_full_msa_template/prepared_ranked_protein_inputs -o /scratch/10992/liaorunlong93/casp16-leaderboard/runs/opendde_v1_full_msa_template/predictions/opendde_v1 -n opendde_v1 --seeds 101 --use_msa true --use_template true --use_rna_msa false --sample 1 --step 200 --cycle 10 --dtype fp32 --trimul_kernel auto --triatt_kernel auto --enable_cache true --enable_fusion true --enable_tf32 true
