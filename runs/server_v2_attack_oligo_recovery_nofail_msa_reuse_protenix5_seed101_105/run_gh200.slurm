#!/bin/bash
#SBATCH -J casp16_v2_att5
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 48:00:00
#SBATCH -o runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/logs/%x-%j.out
#SBATCH -e runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/logs/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/logs
mkdir -p runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/torch_extensions

export PYTHONNOUSERSITE=1
export TORCH_EXTENSIONS_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/runs/server_v2_attack_oligo_recovery_nofail_msa_reuse_protenix5_seed101_105/torch_extensions

hostname
./casp16 run-next --benchmark casp16_server_protein_v2_aliasfix
