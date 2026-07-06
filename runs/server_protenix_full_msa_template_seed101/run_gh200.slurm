#!/bin/bash
#SBATCH -J casp16_server_protenix
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_protenix_full_msa_template_seed101
mkdir -p logs torch_extensions

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR="$PWD/torch_extensions"
if [[ -z "${CUDA_HOME:-}" ]] && command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME="$(cd "$(dirname "$(command -v nvcc)")/.." && pwd)"
fi

hostname
bash ./run.sh
