#!/bin/bash
#SBATCH -J casp16_tlab_fv
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o runs/targetlab_protenix_yang_antibody_fv_seed101/logs/%x-%j.out
#SBATCH -e runs/targetlab_protenix_yang_antibody_fv_seed101/logs/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p runs/targetlab_protenix_yang_antibody_fv_seed101/logs
mkdir -p runs/targetlab_protenix_yang_antibody_fv_seed101/torch_extensions

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/runs/targetlab_protenix_yang_antibody_fv_seed101/torch_extensions

hostname
./casp16 run-next --benchmark target_lab
