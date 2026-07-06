#!/usr/bin/env python
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

from runner.batch_inference import preprocess_input


RUN_DIR = Path(__file__).resolve().parent
RAW_INPUT_DIR = RUN_DIR / "inputs"
FEATURE_DIR = RUN_DIR / "features" / "opendde_v1"
PREPARED_INPUT_DIR = RUN_DIR / "prepared_inputs"
SUMMARY_PATH = RUN_DIR / "logs" / "feature_precompute_summary.jsonl"
MAX_ATTEMPTS = 4


def load_priority_order(input_paths: list[Path]) -> list[Path]:
    order_file = os.environ.get("PRECOMPUTE_TARGET_ORDER")
    if not order_file:
        return input_paths

    priority: dict[str, int] = {}
    with Path(order_file).open(encoding="utf-8") as handle:
        for line in handle:
            target = line.strip()
            if target and not target.startswith("#") and target not in priority:
                priority[target] = len(priority)

    return sorted(input_paths, key=lambda path: (priority.get(path.stem, len(priority)), path.stem))


def protein_entity_count(input_json: Path) -> int:
    payload = json.loads(input_json.read_text())
    return sum(1 for seq in payload[0].get("sequences", []) if "proteinChain" in seq)


def validate_precomputed(target: str, updated_json: Path, protein_entities: int) -> list[str]:
    errors: list[str] = []
    feature_root = FEATURE_DIR / target / "msa"
    unpaired_manifest = feature_root / "unpaired" / "out.manifest.json"
    if not unpaired_manifest.exists():
        errors.append(f"missing_unpaired_mmseqs_manifest:{unpaired_manifest}")
    if protein_entities > 1:
        paired_manifest = feature_root / "paired" / "out.manifest.json"
        if not paired_manifest.exists():
            errors.append(f"missing_paired_mmseqs_manifest:{paired_manifest}")

    payload = json.loads(updated_json.read_text())
    for seq_idx, seq in enumerate(payload[0].get("sequences", [])):
        chain = seq.get("proteinChain")
        if not chain:
            continue
        for key in ("unpairedMsaPath", "templatesPath"):
            path = Path(str(chain.get(key, "")))
            if not path.exists() or path.stat().st_size == 0:
                errors.append(f"missing_or_empty_{key}:seq{seq_idx}:{path}")
        if protein_entities > 1:
            paired = Path(str(chain.get("pairedMsaPath", "")))
            if not paired.exists() or paired.stat().st_size == 0:
                errors.append(f"missing_or_empty_pairedMsaPath:seq{seq_idx}:{paired}")
    return errors


def clean_target_artifacts(target: str, *, remove_features: bool = False) -> None:
    if remove_features:
        shutil.rmtree(FEATURE_DIR / target, ignore_errors=True)
    for suffix in ("-update-msa.json", "-final-updated.json"):
        path = RAW_INPUT_DIR / f"{target}{suffix}"
        if path.exists():
            path.unlink()
    prepared = PREPARED_INPUT_DIR / f"{target}.json"
    if prepared.exists():
        prepared.unlink()


def append_summary(row: dict[str, object]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    PREPARED_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_paths = sorted(path for path in RAW_INPUT_DIR.glob("*.json") if "-update-" not in path.name and "-final-" not in path.name)
    input_paths = load_priority_order(input_paths)
    max_new = int(os.environ.get("PRECOMPUTE_MAX_NEW", "0"))
    processed_new = 0
    failures: dict[str, list[str]] = {}
    for index, input_json in enumerate(input_paths, start=1):
        target = input_json.stem
        entities = protein_entity_count(input_json)
        prepared = PREPARED_INPUT_DIR / f"{target}.json"
        if entities == 0:
            if not prepared.exists():
                shutil.copy2(input_json, prepared)
                processed_new += 1
            append_summary({"target": target, "status": "ok_no_protein_entities", "attempt": 0, "updated_json": str(input_json)})
            print(f"[{index}/{len(input_paths)}] skip {target} no_protein_entities", flush=True)
            if max_new and processed_new >= max_new:
                break
            continue
        if prepared.exists():
            errors = validate_precomputed(target, prepared, entities)
            if not errors:
                print(f"[{index}/{len(input_paths)}] skip {target} already_prepared", flush=True)
                continue
        previous_final = RAW_INPUT_DIR / f"{target}-final-updated.json"
        if previous_final.exists():
            errors = validate_precomputed(target, previous_final, entities)
            if not errors:
                shutil.copy2(previous_final, prepared)
                append_summary({"target": target, "status": "ok", "attempt": 0, "updated_json": str(previous_final), "resumed": True})
                print(f"[{index}/{len(input_paths)}] resume {target} previous_final", flush=True)
                processed_new += 1
                if max_new and processed_new >= max_new:
                    break
                continue
        print(f"[{index}/{len(input_paths)}] precompute {target} entities={entities}", flush=True)
        last_errors: list[str] = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            clean_target_artifacts(target, remove_features=False)
            try:
                updated = Path(
                    preprocess_input(
                        str(input_json),
                        out_dir=str(FEATURE_DIR),
                        use_msa=True,
                        use_template=True,
                        use_rna_msa=False,
                    )
                )
                last_errors = validate_precomputed(target, updated, entities)
                if not last_errors:
                    shutil.copy2(updated, PREPARED_INPUT_DIR / f"{target}.json")
                    append_summary({"target": target, "status": "ok", "attempt": attempt, "updated_json": str(updated)})
                    processed_new += 1
                    break
            except Exception as exc:
                last_errors = [f"exception:{type(exc).__name__}:{exc}"]
            append_summary({"target": target, "status": "retry", "attempt": attempt, "errors": last_errors})
            print(f"  attempt {attempt} failed: {last_errors}", flush=True)
            if any("missing_unpaired_mmseqs_manifest" in error for error in last_errors):
                clean_target_artifacts(target, remove_features=True)
            time.sleep(min(60, 5 * attempt))
        else:
            failures[target] = last_errors
            append_summary({"target": target, "status": "failed", "errors": last_errors})

        if max_new and processed_new >= max_new:
            break

    if failures:
        print(json.dumps({"failed_targets": failures}, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps({"prepared_inputs": len(list(PREPARED_INPUT_DIR.glob("*.json"))), "status": "ok"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
