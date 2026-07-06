#!/bin/bash
set -euo pipefail

cd /scratch/10992/liaorunlong93/casp16-leaderboard

export PROTENIX_DATA_ROOT=/scratch/10992/liaorunlong93/protenix_data
export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/target_lab/h1258_interaction_window_v1/torch_extensions

mkdir -p target_lab/h1258_interaction_window_v1/predictions/protenix-v2
mkdir -p "$TORCH_EXTENSIONS_DIR"

/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix pred \
  -i target_lab/h1258_interaction_window_v1/inputs.json \
  -o target_lab/h1258_interaction_window_v1/predictions/protenix-v2 \
  -s 101 \
  -e 1 \
  -d bf16 \
  -n protenix-v2 \
  --use_msa true \
  --use_template true \
  --use_default_params true \
  --trimul_kernel torch \
  --triatt_kernel torch \
  --enable_cache true \
  --enable_fusion true \
  --enable_tf32 true
