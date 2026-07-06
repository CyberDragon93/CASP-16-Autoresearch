#!/usr/bin/env bash
set -uo pipefail
export OPENDDE_ROOT_DIR=/scratch/10992/liaorunlong93/opendde_data
export PATH=/scratch/10992/liaorunlong93/conda/envs/protein/bin:$PATH
export LAYERNORM_TYPE=torch
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
RUN_DIR=/scratch/10992/liaorunlong93/casp16-leaderboard/runs/opendde_v1_full_msa_template_bf16_cacheoff
OUT_DIR="$RUN_DIR/predictions/opendde_v1"
: > "$RUN_DIR/logs/stdout.log"
: > "$RUN_DIR/logs/stderr.log"
: > "$RUN_DIR/logs/cacheoff_status.tsv"
printf 'target	status	exit_code	started_at	finished_at
' >> "$RUN_DIR/logs/cacheoff_status.tsv"
for target in H1258 H1236 T1210 H0272 H1272 H1227; do
  started=$(date -Iseconds)
  echo "===== $target START $started =====" | tee -a "$RUN_DIR/logs/stdout.log"
  /scratch/10992/liaorunlong93/conda/envs/protein/bin/opendde pred     -i "$RUN_DIR/tmp_inputs/$target/$target.json"     -o "$OUT_DIR"     -n opendde_v1     --seeds 101     --use_msa true     --use_template true     --use_rna_msa false     --sample 1     --step 200     --cycle 10     --dtype bf16     --trimul_kernel auto     --triatt_kernel auto     --enable_cache false     --enable_fusion true     --enable_tf32 true     >> "$RUN_DIR/logs/stdout.log"     2>> "$RUN_DIR/logs/stderr.log"
  code=$?
  finished=$(date -Iseconds)
  status=failed
  if grep -q "\[Rank 0\] $target \[seed:101\] succeeded" "$RUN_DIR/logs/stderr.log"; then status=ok; fi
  printf '%s	%s	%s	%s	%s
' "$target" "$status" "$code" "$started" "$finished" >> "$RUN_DIR/logs/cacheoff_status.tsv"
  echo "===== $target END code=$code status=$status $finished =====" | tee -a "$RUN_DIR/logs/stdout.log"
done
