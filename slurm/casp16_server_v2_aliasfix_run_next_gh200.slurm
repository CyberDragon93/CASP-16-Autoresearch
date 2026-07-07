#!/bin/bash
#SBATCH -J casp16_v2_next
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o logs/slurm/%x-%j.out
#SBATCH -e logs/slurm/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p logs/slurm
mkdir -p runs/_torch_extensions/casp16_server_v2_aliasfix_run_next

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/runs/_torch_extensions/casp16_server_v2_aliasfix_run_next

hostname
./casp16 run-next --benchmark casp16_server_protein_v2_aliasfix
