#!/bin/bash
set -euo pipefail

cd /scratch/10992/liaorunlong93/casp16-leaderboard

export PROTENIX_ROOT_DIR=/scratch/10992/liaorunlong93/protenix_data
export PROTENIX_DATA_ROOT=/scratch/10992/liaorunlong93/protenix_data
export PYTHONNOUSERSITE=1
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
export PYTHONPATH=/scratch/10992/liaorunlong93/Protenix-Insta:${PYTHONPATH:-}
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/target_lab/h1258_interaction_window_v1/torch_extensions

if [[ -z "${CUDA_HOME:-}" ]] && command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME="$(cd "$(dirname "$(command -v nvcc)")/.." && pwd)"
fi
if [[ -n "${CUDA_HOME:-}" ]]; then
  _cuda_version="$(basename "$CUDA_HOME")"
  _nvidia_root="$(cd "$CUDA_HOME/../.." && pwd)"
  _math_target="${_nvidia_root}/math_libs/${_cuda_version}/targets/sbsa-linux"
  if [[ -f "${_math_target}/include/cusparse.h" ]]; then
    export CPATH="${_math_target}/include:${CPATH:-}"
    export LIBRARY_PATH="${_math_target}/lib:${LIBRARY_PATH:-}"
    export LD_LIBRARY_PATH="${_math_target}/lib:${LD_LIBRARY_PATH:-}"
  fi
fi

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
