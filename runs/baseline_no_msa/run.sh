#!/usr/bin/env bash
set -euo pipefail
export PROTENIX_ROOT_DIR=/scratch/10992/liaorunlong93/protenix_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
mkdir -p logs
exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)
/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix pred -i /scratch/10992/liaorunlong93/casp16-leaderboard/benchmarks/casp16_protein_v1/inputs.json -o /scratch/10992/liaorunlong93/casp16-leaderboard/runs/baseline_no_msa/predictions/protenix-v2 -s 101 -e 1 -d bf16 -n protenix-v2 --use_msa false --use_template false --use_default_params false --trimul_kernel torch --triatt_kernel torch --enable_cache false --enable_fusion false --enable_tf32 true
