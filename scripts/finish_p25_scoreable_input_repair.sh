#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

SHARD_TABLE="attack_budgets/casp16_server_attack_protenix25_scoreable_input_repair_target_seed_shards.tsv"
BENCHMARK="casp16_server_protein_v2_aliasfix"
RUN_ID="server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125"
MERGED_INPUT_JSON="strategies/scoreable_target_subset_input_repair_v1/casp16_server_protein_v2_aliasfix/inputs.json"
READINESS_TSV="diagnostics/score_probes/protenix25_scoreable_input_repair_target_seed_readiness.tsv"
OVERLAY_RUN_ID="server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105"
TMSCORE_BIN="/scratch/10992/liaorunlong93/conda/envs/protein/bin/TMscore"

if [[ ! -f "${SHARD_TABLE}" ]]; then
  echo "missing shard table: ${SHARD_TABLE}" >&2
  exit 2
fi

args=(
  ./casp16 finish-shards
  --benchmark "${BENCHMARK}"
  --run-id "${RUN_ID}"
  --merged-input-json "${MERGED_INPUT_JSON}"
  --candidate-count 5
  --merged-candidate-count 25
  --allow-target-shards
  --output-tsv "${READINESS_TSV}"
  --tmscore-bin "${TMSCORE_BIN}"
  --shard-run-id "${OVERLAY_RUN_ID}"
)

while IFS=$'\t' read -r target_shard seed_block run_id benchmark strategy input_json input_manifest seeds sample execution_candidate_count merged_candidate_count selected_model_policy status role; do
  if [[ "${role}" == "submitted" ]]; then
    args+=(--shard-run-id "${run_id}")
  fi
done < <(tail -n +2 "${SHARD_TABLE}")

"${args[@]}" "$@"
