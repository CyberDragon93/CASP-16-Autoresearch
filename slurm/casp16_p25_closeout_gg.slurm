#!/bin/bash
#SBATCH -J p25_closeout
#SBATCH -p gg
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 12:00:00
#SBATCH -o logs/slurm/%x-%j.out
#SBATCH -e logs/slurm/%x-%j.err

set -euo pipefail

cd /scratch/10992/liaorunlong93/casp16-leaderboard
mkdir -p logs/slurm

export PYTHONNOUSERSITE=1
export PATH="/scratch/10992/liaorunlong93/conda/envs/protein/bin:${PATH}"

poll_seconds="${POLL_SECONDS:-900}"
max_polls="${MAX_POLLS:-48}"
readiness_json="/tmp/casp16_p25_closeout_${SLURM_JOB_ID:-manual}.json"
readiness_tsv="/tmp/casp16_p25_closeout_${SLURM_JOB_ID:-manual}.tsv"

hostname
date

for ((poll=1; poll<=max_polls; poll++)); do
  echo "[p25-closeout] poll ${poll}/${max_polls}"
  scripts/finish_p25_scoreable_input_repair.sh --dry-run \
    --output-tsv "${readiness_tsv}" > "${readiness_json}"

  python - "${readiness_json}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
summary = payload.get("status_summary", {})
fields = {
    "finish_status": payload.get("finish_status"),
    "action": summary.get("action"),
    "ready": summary.get("ready"),
    "observed": summary.get("observed_candidate_count"),
    "missing": summary.get("missing_candidate_count"),
    "full_missing": summary.get("full_missing_candidate_count"),
    "full_complete": summary.get("full_complete_task_count"),
    "full_task_count": summary.get("full_task_count"),
    "complete_shards": summary.get("complete_shard_count"),
    "zero_output": summary.get("zero_output_shard_count"),
}
print(json.dumps(fields, sort_keys=True))
PY

  action="$(python - "${readiness_json}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload.get("status_summary", {}).get("action", ""))
PY
)"

  if [[ "${action}" == "run_finish_without_dry_run" ]]; then
    echo "[p25-closeout] ready; running closeout"
    scripts/finish_p25_scoreable_input_repair.sh
    ./casp16 winner-gap --benchmark casp16_server_protein_v2_aliasfix
    date
    exit 0
  fi

  if [[ "${action}" != "wait_for_declared_candidates" ]]; then
    echo "[p25-closeout] unexpected action: ${action}" >&2
    exit 2
  fi

  sleep "${poll_seconds}"
done

echo "[p25-closeout] timed out waiting for declared candidates" >&2
exit 3
