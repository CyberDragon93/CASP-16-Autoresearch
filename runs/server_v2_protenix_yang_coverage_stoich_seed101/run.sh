#!/usr/bin/env bash
set -euo pipefail
export PROTENIX_ROOT_DIR=/scratch/10992/liaorunlong93/protenix_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
export PYTHONPATH=/scratch/10992/liaorunlong93/Protenix-Insta:${PYTHONPATH:-}
if [[ -z "${CUDA_HOME:-}" ]]; then
  if type module >/dev/null 2>&1; then
    module load cuda/12.5 >/dev/null 2>&1 || module load cuda/12.4 >/dev/null 2>&1 || true
  fi
fi
if [[ -z "${CUDA_HOME:-}" && -n "${TACC_CUDA_DIR:-}" ]]; then
  export CUDA_HOME="${TACC_CUDA_DIR}"
fi
if [[ -z "${CUDA_HOME:-}" && -n "${NVHPC_CUDA_HOME:-}" ]]; then
  export CUDA_HOME="${NVHPC_CUDA_HOME}"
fi
if [[ -z "${CUDA_HOME:-}" ]] && command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME="$(cd "$(dirname "$(command -v nvcc)")/.." && pwd)"
fi
if [[ -z "${CUDA_HOME:-}" && -d /home1/apps/nvidia/Linux_aarch64/24.7/cuda/12.5 ]]; then
  export CUDA_HOME=/home1/apps/nvidia/Linux_aarch64/24.7/cuda/12.5
fi
if [[ -z "${CUDA_HOME:-}" && -d /opt/apps/cuda/12.4 ]]; then
  export CUDA_HOME=/opt/apps/cuda/12.4
fi
if [[ -n "${CUDA_HOME:-}" ]]; then
  export PATH="${CUDA_HOME}/bin:${PATH}"
  if [[ -d "${CUDA_HOME}/include" ]]; then
    export CPATH="${CUDA_HOME}/include:${CPATH:-}"
  fi
  if [[ -d "${CUDA_HOME}/lib64" ]]; then
    export LIBRARY_PATH="${CUDA_HOME}/lib64:${LIBRARY_PATH:-}"
    export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
  fi
  if [[ -d "${CUDA_HOME}/targets/sbsa-linux/lib" ]]; then
    export LIBRARY_PATH="${CUDA_HOME}/targets/sbsa-linux/lib:${LIBRARY_PATH:-}"
    export LD_LIBRARY_PATH="${CUDA_HOME}/targets/sbsa-linux/lib:${LD_LIBRARY_PATH:-}"
  fi
  _cuda_version="$(basename "$CUDA_HOME")"
  _nvidia_root="$(cd "$CUDA_HOME/../.." && pwd)"
  for _math_target in "${_nvidia_root}/math_libs/${_cuda_version}/targets/sbsa-linux" "/opt/apps/nvidia_math/${_cuda_version}/targets/sbsa-linux"; do
    if [[ -f "${_math_target}/include/cusparse.h" ]]; then
      export CPATH="${_math_target}/include:${CPATH:-}"
    fi
    if [[ -d "${_math_target}/lib" ]]; then
      export LIBRARY_PATH="${_math_target}/lib:${LIBRARY_PATH:-}"
      export LD_LIBRARY_PATH="${_math_target}/lib:${LD_LIBRARY_PATH:-}"
    fi
  done
fi
mkdir -p logs
exec > >(tee logs/stdout.log) 2> >(tee logs/stderr.log >&2)
/scratch/10992/liaorunlong93/conda/envs/protein/bin/protenix pred -i /scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_v2_protenix_yang_coverage_stoich_seed101/inputs/inputs.json -o /scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_v2_protenix_yang_coverage_stoich_seed101/predictions/protenix-v2 -s 101 -e 1 -d bf16 -n protenix-v2 --use_msa true --use_template true --use_default_params true --trimul_kernel torch --triatt_kernel torch --enable_cache true --enable_fusion true --enable_tf32 true
