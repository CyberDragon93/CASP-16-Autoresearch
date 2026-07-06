#!/usr/bin/env bash
set -euo pipefail
export PROTENIX_ROOT_DIR=/scratch/10992/liaorunlong93/protenix_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
export PYTHONPATH=/scratch/10992/liaorunlong93/Protenix-Insta:${PYTHONPATH:-}
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
mkdir -p logs
exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)
/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix pred -i /scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_protenix_yang_antibody_fv_cleanup_seed101/inputs/inputs.json -o /scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_protenix_yang_antibody_fv_cleanup_seed101/predictions/protenix-v2 -s 101 -e 1 -d bf16 -n protenix-v2 --use_msa true --use_template true --use_default_params true --trimul_kernel torch --triatt_kernel torch --enable_cache true --enable_fusion true --enable_tf32 true
