#!/bin/bash
#SBATCH -J casp16_run_one
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o logs/slurm/%x-%j.out
#SBATCH -e logs/slurm/%x-%j.err

set -euo pipefail

: "${RUN_ID:?set RUN_ID to a casp16 run id}"

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p logs/slurm
mkdir -p "runs/_torch_extensions/${RUN_ID}"

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR="/scratch/10992/liaorunlong93/casp16-leaderboard/runs/_torch_extensions/${RUN_ID}"

args=(./casp16 run-one --run-id "${RUN_ID}")
if [[ "${ALLOW_PARALLEL:-0}" == "1" ]]; then
  args+=(--allow-parallel)
fi

hostname
"${args[@]}"
