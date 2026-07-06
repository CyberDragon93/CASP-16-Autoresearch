#!/bin/bash
#SBATCH -J casp16_attack_ttag5
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o runs/server_attack_protenix_terminal_tag_seed101_105/logs/%x-%j.out
#SBATCH -e runs/server_attack_protenix_terminal_tag_seed101_105/logs/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p runs/server_attack_protenix_terminal_tag_seed101_105/logs
mkdir -p runs/server_attack_protenix_terminal_tag_seed101_105/torch_extensions

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_attack_protenix_terminal_tag_seed101_105/torch_extensions

hostname
./casp16 run-next --benchmark casp16_server_protein_v1
