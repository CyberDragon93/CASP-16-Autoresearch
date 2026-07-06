#!/bin/bash
#SBATCH -J casp16_tlab_domain
#SBATCH -p gh
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 18:00:00
#SBATCH -o target_lab/domain_fragment_batch_v1/logs/%x-%j.out
#SBATCH -e target_lab/domain_fragment_batch_v1/logs/%x-%j.err

set -euo pipefail

module load cuda/12.5

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p target_lab/domain_fragment_batch_v1/logs

hostname
bash target_lab/domain_fragment_batch_v1/run_protenix.sh
