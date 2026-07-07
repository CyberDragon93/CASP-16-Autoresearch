from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .runs import latest_status_by_run, load_run_specs, run_row_from_spec, spec_bool


DEFAULT_P14_RUN_ID = "server_v2_attack_scoreable_size_balanced_msa_reuse_protenix5_seed101_105"
DEFAULT_P16_REPLAY_RUN_ID = f"{DEFAULT_P14_RUN_ID}_consensus_replay"
DEFAULT_P17_RUN_ID = "server_v2_attack_scoreable_input_repair_overlay_msa_reuse_protenix5_seed101_105"
DEFAULT_P25_RUN_ID = "server_v2_attack_scoreable_input_repair_size_balanced_msa_reuse_protenix25_seed101_125"

DEFAULT_DOMAIN_FLOOR = 0.049685
DEFAULT_EXACT_DOMAIN_PROBE_FLOOR = 0.099576
DEFAULT_MIN_EXACT_OLIGO_NONZERO = 2
SERVER_WINNER_TRACKS = {
    "protein_domain": "prot_domains",
    "protein_oligo": "prot_oligo",
}

D6A_INPUT_REPAIR_TARGETS = {"T1276", "T1228V1", "T1239V1", "T2276"}
D6A_RUN_IDS = ("server_v2_domain_sequence_recovery_oligo_nofail_msa_reuse_after_warmup_seed101",)
P27B_RUN_IDS = tuple(
    f"server_v2_attack_scoreable_input_repair_defaultparams_shard{shard:02d}_msa_reuse_protenix5_seed101_105"
    for shard in range(1, 7)
)
O5B_RUN_IDS = tuple(
    f"server_v2_attack_scoreable_input_repair_antibody_fv_shard{shard:02d}_msa_reuse_protenix5_seed101_105"
    for shard in range(1, 7)
)
P28A_DESIGN_PATH = Path("attack_budgets/casp16_server_attack_msa_model_diversity_v1.json")
P15_V4_RUN_IDS = tuple(
    f"server_v4_attack_scoreable_size_balanced_shard{shard:02d}_msa_reuse_protenix5_seed101_105"
    for shard in range(1, 7)
)
ANTIBODY_FV_TARGETS = {
    "H0222",
    "H1222",
    "H2222",
    "H0223",
    "H1223",
    "H2223",
    "H0225",
    "H1225",
    "H2225",
    "H0233",
    "H1233",
    "H2233",
}


def post_p25_launch_plan(next_branch: str, decision_status: str) -> dict[str, Any]:
    """Return a non-executing launch plan for the selected post-P25 branch."""

    common_templates = [
        './casp16 mark-run --run-id <run_id> --status pending --message "selected after complete P25 readout: '
        f'{decision_status}"',
        "./casp16 run-one --run-id <run_id> --dry-run",
        "ssh login1 'cd /scratch/10992/liaorunlong93/casp16-leaderboard && "
        "RUN_ID=<run_id> sbatch --export=ALL slurm/casp16_run_one_gh200.slurm'",
    ]
    plans: dict[str, dict[str, Any]] = {
        "finish_or_score_p25": {
            "action": "wait_for_p25_closeout",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": [
                "scripts/finish_p25_scoreable_input_repair.sh --dry-run --output-tsv /tmp/casp16_p25_readiness_live.tsv",
                "scripts/finish_p25_scoreable_input_repair.sh",
                "./casp16 score --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix",
            ],
            "note": "Do not launch another branch until P25 is merged, scored, and re-read.",
        },
        "score_p25_before_decision": {
            "action": "score_existing_p25_outputs",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": [
                "./casp16 score --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix",
            ],
            "note": "P25 has run rows but no target scores yet.",
        },
        "score_p17_baseline_before_branching": {
            "action": "score_p17_baseline",
            "run_ids": [DEFAULT_P17_RUN_ID],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": [
                "./casp16 score --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 leaderboard --benchmark casp16_server_protein_v2_aliasfix",
                "./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix",
            ],
            "note": "Score the P17 repaired-input baseline before selecting a post-P25 branch.",
        },
        "finish_or_repair_p25_candidate_grid": {
            "action": "repair_p25_grid",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": ["scripts/finish_p25_scoreable_input_repair.sh --dry-run"],
            "note": "Fix missing or partial P25 candidates before any new GPU branch.",
        },
        "fix_p25_score_path_before_more_gpu": {
            "action": "repair_scoring_path",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": ["./casp16 score --benchmark casp16_server_protein_v2_aliasfix"],
            "note": "Prediction or scorer failures must be fixed before spending more compute.",
        },
        "analyze_p25_aggregate_deltas_then_pick_model_variant": {
            "action": "analyze_complete_p25",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": ["./casp16 post-p25-readout --benchmark casp16_server_protein_v2_aliasfix"],
            "note": "P25 improved; inspect aggregate deltas before choosing another branch.",
        },
        "launch_d6a_domain_sequence_recovery_after_p25": {
            "action": "launch_d6a_input_repair",
            "run_ids": list(D6A_RUN_IDS),
            "preflight_tsv": "diagnostics/msa_cache/domain_sequence_recovery_after_warmup_preflight.tsv",
            "target_disjoint_shards": False,
            "command_templates": common_templates,
            "note": "Single dev-fixed input-repair ablation; use only for predeclared domain input-kind/alias zeros.",
        },
        "launch_o5b_antibody_fv_after_p25": {
            "action": "launch_o5b_antibody_fv_shards",
            "run_ids": list(O5B_RUN_IDS),
            "preflight_tsv": "diagnostics/msa_cache/protenix5_input_repair_antibody_fv_preflight.tsv",
            "target_disjoint_shards": True,
            "command_templates": common_templates,
            "note": "Submit only the repaired-input antibody/Fv shards selected by aggregate P25 diagnostics.",
        },
        "continue_versioned_refmap_or_score_p15_v4": {
            "action": "continue_refmap_or_launch_p15_v4",
            "run_ids": list(P15_V4_RUN_IDS),
            "preflight_tsv": "diagnostics/msa_cache/protenix5_v4_scoreable_target_run_preflight.tsv",
            "target_disjoint_shards": True,
            "command_templates": common_templates,
            "note": "Use versioned refmap work first if P25 is reference-capped; report P15 as v4, not v2.",
        },
        "launch_oligo_or_antibody_fv_model_config_after_p25": {
            "action": "launch_o5b_or_p27b_after_oligo_regression",
            "run_ids": list(O5B_RUN_IDS),
            "alternate_run_ids": list(P27B_RUN_IDS),
            "preflight_tsv": "diagnostics/msa_cache/protenix5_input_repair_antibody_fv_preflight.tsv",
            "alternate_preflight_tsv": "diagnostics/msa_cache/protenix5_input_repair_defaultparams_model_variant_preflight.tsv",
            "target_disjoint_shards": True,
            "command_templates": common_templates,
            "note": "Default to O5b if antibody/Fv rows explain the oligo regression; otherwise use P27b.",
        },
        "launch_p27b_model_config_diversity_after_p25": {
            "action": "launch_p27b_defaultparams_shards",
            "run_ids": list(P27B_RUN_IDS),
            "preflight_tsv": "diagnostics/msa_cache/protenix5_input_repair_defaultparams_model_variant_preflight.tsv",
            "target_disjoint_shards": True,
            "command_templates": common_templates,
            "note": "Smallest prepared model/config diversity probe on repaired scoreable inputs.",
        },
    }
    return plans.get(
        next_branch,
        {
            "action": "manual_review",
            "run_ids": [],
            "preflight_tsv": "",
            "target_disjoint_shards": False,
            "command_templates": [],
            "note": f"No static launch plan is registered for {next_branch}.",
        },
    )


def preflight_summary(project_root: Path, path_text: object) -> dict[str, Any]:
    """Summarize an existing preflight TSV without running any launch checks."""

    text = str(path_text or "").strip()
    if not text:
        return {"path": "", "exists": False}
    path = Path(text)
    if not path.is_absolute():
        path = project_root / path
    payload: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return payload
    rows = read_tsv_rows(path)
    result_counts = Counter(str(row.get("result", "") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("status", "") or "unknown") for row in rows)
    payload.update(
        {
            "row_count": len(rows),
            "ok_rows": sum(1 for row in rows if row.get("result") == "ok"),
            "blocked_rows": sum(1 for row in rows if str(row.get("result", "")).startswith("blocked")),
            "result_counts": dict(sorted(result_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
        }
    )
    return payload


def enrich_launch_plan(project_root: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Attach local run-spec and preflight summaries to a launch plan.

    This is intentionally read-only. It lets the post-P25 decision output show
    whether the selected branch is already prepared/deferred/pending without
    invoking preflight or touching run lifecycle files.
    """

    root = project_root.resolve()
    enriched = dict(plan)
    status_by_run = latest_status_by_run(root)
    specs_by_id = {
        str(spec.get("run_id", "")): spec for spec in load_run_specs(root / "runs", registered_only=False)
    }

    def summarize_run_ids(run_ids: Sequence[object]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for raw_run_id in run_ids:
            run_id = str(raw_run_id or "").strip()
            if not run_id:
                continue
            spec = specs_by_id.get(run_id)
            if spec is None:
                rows.append({"run_id": run_id, "run_spec_exists": False, "status": "missing_run_spec"})
                continue
            row = run_row_from_spec(spec, status_by_run)
            row.update(
                {
                    "run_spec_exists": True,
                    "input_json": str(spec.get("input_json", "") or ""),
                    "output_dir": str(spec.get("output_dir", "") or ""),
                    "stdout_path": str(spec.get("stdout_path", "") or ""),
                    "stderr_path": str(spec.get("stderr_path", "") or ""),
                }
            )
            rows.append(row)
        return rows

    enriched["run_specs"] = summarize_run_ids(enriched.get("run_ids") or [])
    if "alternate_run_ids" in enriched:
        enriched["alternate_run_specs"] = summarize_run_ids(enriched.get("alternate_run_ids") or [])
    enriched["preflight"] = preflight_summary(root, enriched.get("preflight_tsv"))
    if "alternate_preflight_tsv" in enriched:
        enriched["alternate_preflight"] = preflight_summary(root, enriched.get("alternate_preflight_tsv"))
    return enriched


def _normalized_spec_path(project_root: Path, spec: Mapping[str, Any], key: str) -> str:
    text = str(spec.get(key, "") or "").strip()
    if not text:
        return ""
    path = Path(text)
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve())


def p27b_variant_guard(project_root: Path, specs_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Validate that P27b is a narrow default-params variant of P25 inputs."""

    root = project_root.resolve()
    p25_specs = [
        spec
        for run_id, spec in specs_by_id.items()
        if run_id.startswith("server_v2_attack_scoreable_input_repair_size_balanced_shard")
        and "_msa_reuse_protenix25_seed" in run_id
    ]
    p25_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for spec in p25_specs:
        source = _normalized_spec_path(root, spec, "source_input_json")
        if source:
            p25_by_source.setdefault(source, []).append(spec)

    failures: list[str] = []
    matched_p25_specs = 0
    checked_sources: set[str] = set()
    for run_id in P27B_RUN_IDS:
        spec = specs_by_id.get(run_id)
        if spec is None:
            failures.append(f"{run_id}:missing_run_spec")
            continue
        source = _normalized_spec_path(root, spec, "source_input_json")
        checked_sources.add(source)
        if not source:
            failures.append(f"{run_id}:missing_source_input_json")
        elif not Path(source).exists():
            failures.append(f"{run_id}:source_input_json_missing_on_disk")
        matches = p25_by_source.get(source, [])
        if not matches:
            failures.append(f"{run_id}:no_matching_p25_source_input")
        matched_p25_specs += len(matches)

        if str(spec.get("benchmark_name", "")) != "casp16_server_protein_v2_aliasfix":
            failures.append(f"{run_id}:unexpected_benchmark")
        if str(spec.get("backend", "")) != "protenix":
            failures.append(f"{run_id}:unexpected_backend")
        if str(spec.get("selected_model_policy", "") or "first_output_only") != "protenix_confidence_v1":
            failures.append(f"{run_id}:unexpected_selected_model_policy")
        if not spec_bool(spec.get("use_msa"), default=False):
            failures.append(f"{run_id}:msa_disabled")
        if not spec_bool(spec.get("use_default_params"), default=False):
            failures.append(f"{run_id}:default_params_not_enabled")
        if str(spec.get("seeds", "")) != "101,102,103,104,105":
            failures.append(f"{run_id}:unexpected_seeds")
        if as_int(spec.get("sample"), default=0) != 1:
            failures.append(f"{run_id}:unexpected_sample")
        if as_int(spec.get("candidate_count"), default=0) != 5:
            failures.append(f"{run_id}:unexpected_candidate_count")
        if str(spec.get("budget_tier", "")) != "server_attack":
            failures.append(f"{run_id}:unexpected_budget_tier")

        for match in matches:
            p25_run_id = str(match.get("run_id", "p25_match"))
            if spec_bool(match.get("use_default_params"), default=True):
                failures.append(f"{run_id}:{p25_run_id}:p25_default_params_enabled")
            for key in ("input_manifest_sha256", "references_sha256"):
                if str(spec.get(key, "") or "") != str(match.get(key, "") or ""):
                    failures.append(f"{run_id}:{p25_run_id}:{key}_mismatch")
            for key in ("benchmark_name", "selected_model_policy"):
                if str(spec.get(key, "") or "") != str(match.get(key, "") or ""):
                    failures.append(f"{run_id}:{p25_run_id}:{key}_mismatch")
            if spec_bool(spec.get("use_msa"), default=False) != spec_bool(match.get("use_msa"), default=False):
                failures.append(f"{run_id}:{p25_run_id}:use_msa_mismatch")
            if as_int(spec.get("sample"), default=0) != as_int(match.get("sample"), default=0):
                failures.append(f"{run_id}:{p25_run_id}:sample_mismatch")
            if as_int(match.get("candidate_count"), default=0) != 5:
                failures.append(f"{run_id}:{p25_run_id}:p25_candidate_count_not_five")

    return {
        "status": "ok" if not failures else "blocked",
        "checked_run_ids": len(P27B_RUN_IDS),
        "p25_comparator_specs": len(p25_specs),
        "matched_p25_specs": matched_p25_specs,
        "source_input_count": len({source for source in checked_sources if source}),
        "failures": failures[:25],
        "note": "P27b must stay a repaired-input default-params variant; this guard reads run specs only.",
    }


def _load_input_jobs(path: str) -> dict[str, Any]:
    if not path:
        return {}
    input_path = Path(path)
    if not input_path.exists():
        return {}
    with input_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return {str(row.get("name", "")): row for row in rows if row.get("name")}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def o5b_variant_guard(project_root: Path, specs_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Validate that O5b only changes the predeclared antibody/Fv inputs."""

    root = project_root.resolve()
    p25_specs = [
        spec
        for run_id, spec in specs_by_id.items()
        if run_id.startswith("server_v2_attack_scoreable_input_repair_size_balanced_shard")
        and "_msa_reuse_protenix25_seed" in run_id
    ]
    p25_source_paths = sorted({_normalized_spec_path(root, spec, "source_input_json") for spec in p25_specs})
    p25_reference_hashes = {str(spec.get("references_sha256", "") or "") for spec in p25_specs}
    o5b_source_paths = sorted(
        {
            _normalized_spec_path(root, specs_by_id.get(run_id, {}), "source_input_json")
            for run_id in O5B_RUN_IDS
        }
    )
    p25_jobs: dict[str, Any] = {}
    o5b_jobs: dict[str, Any] = {}
    failures: list[str] = []
    for source in p25_source_paths:
        if not source:
            continue
        if not Path(source).exists():
            failures.append(f"p25_source_missing:{source}")
        p25_jobs.update(_load_input_jobs(source))
    for source in o5b_source_paths:
        if not source:
            continue
        if not Path(source).exists():
            failures.append(f"o5b_source_missing:{source}")
        o5b_jobs.update(_load_input_jobs(source))

    for run_id in O5B_RUN_IDS:
        spec = specs_by_id.get(run_id)
        if spec is None:
            failures.append(f"{run_id}:missing_run_spec")
            continue
        if str(spec.get("benchmark_name", "")) != "casp16_server_protein_v2_aliasfix":
            failures.append(f"{run_id}:unexpected_benchmark")
        if str(spec.get("backend", "")) != "protenix":
            failures.append(f"{run_id}:unexpected_backend")
        if str(spec.get("selected_model_policy", "") or "first_output_only") != "protenix_confidence_v1":
            failures.append(f"{run_id}:unexpected_selected_model_policy")
        if not spec_bool(spec.get("use_msa"), default=False):
            failures.append(f"{run_id}:msa_disabled")
        if spec_bool(spec.get("use_default_params"), default=False):
            failures.append(f"{run_id}:default_params_enabled")
        if str(spec.get("seeds", "")) != "101,102,103,104,105":
            failures.append(f"{run_id}:unexpected_seeds")
        if as_int(spec.get("sample"), default=0) != 1:
            failures.append(f"{run_id}:unexpected_sample")
        if as_int(spec.get("candidate_count"), default=0) != 5:
            failures.append(f"{run_id}:unexpected_candidate_count")
        if str(spec.get("budget_tier", "")) != "server_attack":
            failures.append(f"{run_id}:unexpected_budget_tier")
        if str(spec.get("references_sha256", "") or "") not in p25_reference_hashes:
            failures.append(f"{run_id}:references_sha256_not_in_p25_comparators")

    p25_targets = set(p25_jobs)
    o5b_targets = set(o5b_jobs)
    if p25_targets != o5b_targets:
        failures.append(
            f"target_set_mismatch:missing={len(p25_targets - o5b_targets)} extra={len(o5b_targets - p25_targets)}"
        )
    changed_targets = sorted(
        target_id
        for target_id in p25_targets & o5b_targets
        if _canonical_json(p25_jobs[target_id]) != _canonical_json(o5b_jobs[target_id])
    )
    unexpected_changed_targets = sorted(set(changed_targets) - ANTIBODY_FV_TARGETS)
    missing_changed_targets = sorted(ANTIBODY_FV_TARGETS - set(changed_targets))
    if unexpected_changed_targets:
        failures.append(f"unexpected_changed_targets:{','.join(unexpected_changed_targets[:12])}")
    if missing_changed_targets:
        failures.append(f"missing_antibody_fv_changes:{','.join(missing_changed_targets[:12])}")

    return {
        "status": "ok" if not failures else "blocked",
        "checked_run_ids": len(O5B_RUN_IDS),
        "p25_comparator_specs": len(p25_specs),
        "p25_source_count": len([source for source in p25_source_paths if source]),
        "o5b_source_count": len([source for source in o5b_source_paths if source]),
        "target_count": len(o5b_targets),
        "changed_target_count": len(changed_targets),
        "changed_targets": changed_targets,
        "failures": failures[:25],
        "note": "O5b must keep the P25 target set and change only predeclared antibody/Fv inputs; this guard reads run specs and inputs only.",
    }


def d6a_variant_guard(project_root: Path, specs_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Validate that D6a stays a single-seed domain input-repair ablation."""

    root = project_root.resolve()
    failures: list[str] = []
    run_id = D6A_RUN_IDS[0]
    spec = specs_by_id.get(run_id)
    source_jobs: dict[str, Any] = {}
    if spec is None:
        failures.append(f"{run_id}:missing_run_spec")
    else:
        source = _normalized_spec_path(root, spec, "source_input_json")
        if not source:
            failures.append(f"{run_id}:missing_source_input_json")
        elif not Path(source).exists():
            failures.append(f"{run_id}:source_input_json_missing_on_disk")
        source_jobs = _load_input_jobs(source)

        if str(spec.get("benchmark_name", "")) != "casp16_server_protein_v2_aliasfix":
            failures.append(f"{run_id}:unexpected_benchmark")
        if str(spec.get("backend", "")) != "protenix":
            failures.append(f"{run_id}:unexpected_backend")
        if "yang_domain_sequence_recovery_oligo_nofail_v1" not in str(spec.get("strategy", "")):
            failures.append(f"{run_id}:unexpected_strategy")
        if str(spec.get("selected_model_policy", "") or "first_output_only") != "first_output_only":
            failures.append(f"{run_id}:unexpected_selected_model_policy")
        if not spec_bool(spec.get("use_msa"), default=False):
            failures.append(f"{run_id}:msa_disabled")
        if not spec_bool(spec.get("use_default_params"), default=False):
            failures.append(f"{run_id}:default_params_not_enabled")
        if str(spec.get("seeds", "")) != "101":
            failures.append(f"{run_id}:unexpected_seeds")
        if as_int(spec.get("sample"), default=0) != 1:
            failures.append(f"{run_id}:unexpected_sample")
        if as_int(spec.get("candidate_count"), default=0) != 1:
            failures.append(f"{run_id}:unexpected_candidate_count")
        if str(spec.get("budget_tier", "")) != "dev_fixed":
            failures.append(f"{run_id}:unexpected_budget_tier")
        if not spec_bool(spec.get("rank_eligible"), default=False):
            failures.append(f"{run_id}:rank_eligible_not_true")
        if not str(spec.get("references_sha256", "") or ""):
            failures.append(f"{run_id}:missing_references_sha256")

    missing_targets = sorted(D6A_INPUT_REPAIR_TARGETS - set(source_jobs))
    if missing_targets:
        failures.append(f"missing_d6a_input_repair_targets:{','.join(missing_targets)}")

    return {
        "status": "ok" if not failures else "blocked",
        "checked_run_ids": len(D6A_RUN_IDS),
        "target_count": len(source_jobs),
        "required_input_repair_targets": sorted(D6A_INPUT_REPAIR_TARGETS),
        "failures": failures[:25],
        "note": "D6a must stay a single-seed dev-fixed domain input-repair ablation; this guard reads run specs and inputs only.",
    }


def p28a_design_guard(project_root: Path) -> dict[str, Any]:
    """Validate that the future P28a MSA-diversity branch remains real-MSA only."""

    root = project_root.resolve()
    path = root / P28A_DESIGN_PATH
    failures: list[str] = []
    payload: dict[str, Any] = {}
    if not path.exists():
        failures.append("missing_design_json")
    else:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            payload = loaded
        else:
            failures.append("design_json_not_object")

    prediction_policy = payload.get("prediction_policy", {}) if isinstance(payload.get("prediction_policy"), dict) else {}
    candidate_budget = payload.get("candidate_budget", {}) if isinstance(payload.get("candidate_budget"), dict) else {}
    forbidden_toy_settings = {
        str(item) for item in prediction_policy.get("forbidden_toy_settings", []) if str(item)
    }
    if payload and str(payload.get("status", "")) not in {"design_with_prepared_child", "design_only"}:
        failures.append("unexpected_design_status")
    if bool(prediction_policy.get("use_msa")) is not True:
        failures.append("use_msa_not_true")
    if bool(prediction_policy.get("use_template")) is not True:
        failures.append("use_template_not_true")
    if "no_msa_for_speed" not in forbidden_toy_settings:
        failures.append("missing_no_msa_for_speed_forbidden_rule")
    if as_int(candidate_budget.get("variant_count")) != 4:
        failures.append("unexpected_variant_count")
    if as_int(candidate_budget.get("seeds_per_variant")) != 5:
        failures.append("unexpected_seeds_per_variant")
    if as_int(candidate_budget.get("sample_per_seed")) != 1:
        failures.append("unexpected_sample_per_seed")
    if as_int(candidate_budget.get("total_candidates_per_target")) != 20:
        failures.append("unexpected_total_candidates_per_target")

    prepared_children = payload.get("prepared_children", []) if isinstance(payload.get("prepared_children"), list) else []
    p28a_rows = [row for row in prepared_children if isinstance(row, dict) and row.get("name") == "p28a_colabfold_msa_server_mode_probe"]
    p28a = p28a_rows[0] if p28a_rows else {}
    entrypoint = str(p28a.get("entrypoint", ""))
    budget = str(p28a.get("budget", ""))
    if not p28a:
        failures.append("missing_p28a_design_child")
    elif str(p28a.get("status", "")) != "design_only_after_p25_p27b":
        failures.append("p28a_not_design_only_after_p25_p27b")
    if "--msa-server-mode colabfold" not in entrypoint:
        failures.append("entrypoint_missing_colabfold_msa_mode")
    if "--use-msa" not in entrypoint:
        failures.append("entrypoint_missing_use_msa")
    if "--use-template" not in entrypoint:
        failures.append("entrypoint_missing_use_template")
    if "real MSA/template" not in budget:
        failures.append("budget_missing_real_msa_template_rule")

    launch_gate = [str(item) for item in payload.get("launch_gate", []) if str(item)]
    launch_gate_text = "\n".join(launch_gate)
    if "Launch prepared P27b before building true MSA variants" not in launch_gate_text:
        failures.append("missing_p27b_before_p28a_gate")
    if "records msa_server_mode=colabfold" not in launch_gate_text:
        failures.append("missing_colabfold_recording_gate")

    return {
        "name": "p28a_colabfold_msa_server_mode_probe",
        "status": "ok" if not failures else "blocked",
        "design_json": str(path),
        "launch_ready_after_p25_selection": False,
        "requires": [
            "complete scored P25",
            "P27b selected/launched/scored first if P25 is flat but valid",
            "real use_msa=true and use_template=true",
            "global msa_server_mode=colabfold or equivalent precomputed ColabFold/MMseqs A3M paths",
            "complete MSA path preflight before any GPU launch",
        ],
        "failures": failures[:25],
        "note": "Future design guard only; P28a must not become a no-MSA shortcut or launch before P25/P27b evidence.",
    }


POST_P25_BRANCH_READINESS = (
    {
        "branch": "p27b_model_config_diversity",
        "next_branch": "launch_p27b_model_config_diversity_after_p25",
        "trigger": "complete P25 is valid but flat; candidate count alone is not the next lever",
    },
    {
        "branch": "d6a_domain_sequence_recovery",
        "next_branch": "launch_d6a_domain_sequence_recovery_after_p25",
        "trigger": "complete P25 leaves predeclared domain input-kind or alias targets missing or zero",
    },
    {
        "branch": "o5b_antibody_fv",
        "next_branch": "launch_o5b_antibody_fv_after_p25",
        "trigger": "complete P25 has non-antibody oligo signal while antibody/Fv rows remain zero",
    },
    {
        "branch": "p15_v4_scoreable_refmap",
        "next_branch": "continue_versioned_refmap_or_score_p15_v4",
        "trigger": "complete P25 is mostly reference-capped and v4 comparison is explicitly chosen",
    },
)


def post_p25_branch_readiness(project_root: Path) -> dict[str, Any]:
    """Return a read-only readiness audit for all prepared post-P25 branches."""

    root = project_root.resolve()
    specs_by_id = {
        str(spec.get("run_id", "")): spec for spec in load_run_specs(root / "runs", registered_only=False)
    }
    branches: list[dict[str, Any]] = []
    for config in POST_P25_BRANCH_READINESS:
        plan = enrich_launch_plan(root, post_p25_launch_plan(config["next_branch"], "post_p25_branch_readiness"))
        run_specs = plan.get("run_specs") or []
        alternate_run_specs = plan.get("alternate_run_specs") or []
        all_specs = list(run_specs) + list(alternate_run_specs)
        preflight = plan.get("preflight") or {}
        alternate_preflight = plan.get("alternate_preflight") or {}
        preflight_ok = bool(preflight.get("exists")) and int(preflight.get("row_count", 0) or 0) > 0 and int(
            preflight.get("blocked_rows", 0) or 0
        ) == 0 and preflight.get("result_counts") == {"ok": int(preflight.get("row_count", 0) or 0)}
        alternate_preflight_ok = True
        if "alternate_preflight" in plan:
            alternate_preflight_ok = bool(alternate_preflight.get("exists")) and int(
                alternate_preflight.get("row_count", 0) or 0
            ) > 0 and int(alternate_preflight.get("blocked_rows", 0) or 0) == 0 and alternate_preflight.get(
                "result_counts"
            ) == {"ok": int(alternate_preflight.get("row_count", 0) or 0)}
        missing_run_specs = [row.get("run_id", "") for row in all_specs if not row.get("run_spec_exists")]
        status_counts = Counter(str(row.get("status", "") or "unknown") for row in all_specs)
        variant_guard: dict[str, Any] = {}
        if config["branch"] == "p27b_model_config_diversity":
            variant_guard = p27b_variant_guard(root, specs_by_id)
        elif config["branch"] == "d6a_domain_sequence_recovery":
            variant_guard = d6a_variant_guard(root, specs_by_id)
        elif config["branch"] == "o5b_antibody_fv":
            variant_guard = o5b_variant_guard(root, specs_by_id)
        variant_guard_ok = not variant_guard or variant_guard.get("status") == "ok"
        launch_ready = not missing_run_specs and preflight_ok and alternate_preflight_ok and variant_guard_ok
        branches.append(
            {
                "branch": config["branch"],
                "next_branch": config["next_branch"],
                "trigger": config["trigger"],
                "action": plan.get("action", ""),
                "launch_ready_after_p25_selection": launch_ready,
                "run_spec_count": len(run_specs),
                "alternate_run_spec_count": len(alternate_run_specs),
                "missing_run_specs": missing_run_specs,
                "status_counts": dict(sorted(status_counts.items())),
                "preflight": preflight,
                "alternate_preflight": alternate_preflight if "alternate_preflight" in plan else {},
                "variant_guard": variant_guard,
                "target_disjoint_shards": bool(plan.get("target_disjoint_shards")),
                "note": plan.get("note", ""),
            }
        )

    return {
        "status": "ok",
        "note": "Read-only audit; launch only after complete scored P25 selects the branch.",
        "branches": branches,
        "future_designs": [p28a_design_guard(root)],
        "summary": {
            "branch_count": len(branches),
            "launch_ready_count": sum(1 for branch in branches if branch["launch_ready_after_p25_selection"]),
            "not_ready_count": sum(1 for branch in branches if not branch["launch_ready_after_p25_selection"]),
        },
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return default


def winner_gap_readout(
    *,
    project_root: Path,
    benchmark: str,
    leaderboard_dir: Path | None = None,
) -> dict[str, Any]:
    """Compare the best local rows with official server winners.

    This is a read-only scoreboard diagnostic. It reads only generated
    leaderboard CSVs, and it must not be used for target-specific tuning.
    """

    root = project_root.resolve()
    output_dir = (leaderboard_dir or (root / "leaderboards" / benchmark)).resolve()
    runs_csv = output_dir / "runs.csv"
    official_csv = output_dir / "official_server_groups.csv"
    for path in (runs_csv, official_csv):
        if not path.exists():
            raise FileNotFoundError(f"required winner-gap input is missing: {path}")

    run_rows = read_csv_rows(runs_csv)
    official_rows = read_csv_rows(official_csv)
    tracks: dict[str, dict[str, Any]] = {}
    combined_local_weighted = 0.0
    combined_winner_weighted = 0.0
    combined_target_count = 0

    for track, official_category in SERVER_WINNER_TRACKS.items():
        server_rows = [
            row
            for row in official_rows
            if row.get("category") == official_category and row.get("group_type") == "server"
        ]
        server_rows.sort(key=lambda row: (as_int(row.get("rank"), default=10**9), -as_float(row.get("mean_fixed_score"))))
        winner = server_rows[0] if server_rows else {}
        local_rows = [row for row in run_rows if row.get("track") == track and str(row.get("run_id", "")).strip()]
        local_rows.sort(key=lambda row: (-as_float(row.get("mean_score")), str(row.get("run_id", ""))))
        best_local = local_rows[0] if local_rows else {}

        winner_mean = as_float(winner.get("mean_fixed_score"))
        local_mean = as_float(best_local.get("mean_score"))
        eligible_targets = as_int(winner.get("eligible_target_count") or best_local.get("eligible_targets"))
        absolute_gap = winner_mean - local_mean
        relative_level = local_mean / winner_mean if winner_mean > 0.0 else 0.0
        multiplier_needed = winner_mean / local_mean if local_mean > 0.0 else None

        combined_local_weighted += local_mean * eligible_targets
        combined_winner_weighted += winner_mean * eligible_targets
        combined_target_count += eligible_targets
        tracks[track] = {
            "official_category": official_category,
            "winner_group": winner.get("group", ""),
            "winner_mean": winner_mean,
            "winner_metric": winner.get("primary_metric", ""),
            "winner_eligible_targets": eligible_targets,
            "best_local_run_id": best_local.get("run_id", ""),
            "best_local_mean": local_mean,
            "best_local_rank_status": best_local.get("rank_status", ""),
            "best_local_budget_tier": best_local.get("budget_tier", ""),
            "best_local_candidate_count": as_int(best_local.get("candidate_count")),
            "best_local_policy": best_local.get("selected_model_policy", ""),
            "best_local_ok_targets": as_int(best_local.get("ok_targets")),
            "best_local_missing_targets": as_int(best_local.get("missing_targets")),
            "best_local_failed_targets": as_int(best_local.get("failed_targets")),
            "best_local_partial_candidate_targets": as_int(best_local.get("partial_candidate_targets")),
            "best_local_metric_unavailable_targets": as_int(best_local.get("metric_unavailable_targets")),
            "absolute_gap": absolute_gap,
            "relative_level": relative_level,
            "multiplier_needed": multiplier_needed,
            "matched": local_mean >= winner_mean and winner_mean > 0.0,
        }

    combined_local_mean = combined_local_weighted / combined_target_count if combined_target_count else 0.0
    combined_winner_mean = combined_winner_weighted / combined_target_count if combined_target_count else 0.0
    return {
        "benchmark": benchmark,
        "status": "matched" if tracks and all(row["matched"] for row in tracks.values()) else "not_matched",
        "tracks": tracks,
        "combined": {
            "target_weighted_local_mean": combined_local_mean,
            "target_weighted_winner_mean": combined_winner_mean,
            "absolute_gap": combined_winner_mean - combined_local_mean,
            "relative_level": combined_local_mean / combined_winner_mean if combined_winner_mean > 0.0 else 0.0,
            "target_count": combined_target_count,
            "note": "Weighted over the two official server protein target sets; each track still has its own winner.",
        },
        "inputs": {
            "runs_csv": str(runs_csv),
            "official_server_groups_csv": str(official_csv),
        },
        "note": "Read-only global comparison; do not use this for target-specific prediction tuning.",
    }


def status_counts(rows: Sequence[Mapping[str, str]]) -> dict[str, int]:
    counts = Counter(str(row.get("status", "") or "unknown") for row in rows)
    return dict(sorted(counts.items()))


def scoreable_target_sets(target_rows: Sequence[Mapping[str, str]]) -> tuple[set[str], set[str]]:
    scoreable_target_ids = {
        row.get("target_id", "")
        for row in target_rows
        if str(row.get("rank_eligible", "")).lower() == "true" and row.get("reference_status", "") == "available"
    }
    no_reference_target_ids = {
        row.get("target_id", "")
        for row in target_rows
        if str(row.get("rank_eligible", "")).lower() == "true" and row.get("reference_status", "") != "available"
    }
    return scoreable_target_ids, no_reference_target_ids


def run_readout_summary(
    *,
    run_id: str,
    run_rows: Sequence[Mapping[str, str]],
    score_rows: Sequence[Mapping[str, str]],
    scoreable_target_ids: set[str],
    no_reference_target_ids: set[str],
) -> dict[str, Any]:
    selected_run_rows = [row for row in run_rows if row.get("run_id") == run_id]
    selected_scores = [row for row in score_rows if row.get("run_id") == run_id]
    scoreable_scores = [row for row in selected_scores if row.get("target_id", "") in scoreable_target_ids]
    no_reference_scores = [row for row in selected_scores if row.get("target_id", "") in no_reference_target_ids]
    track_rows = {row.get("track", ""): row for row in selected_run_rows}
    exact_nonzero_oligo = [
        row
        for row in scoreable_scores
        if row.get("track") == "protein_oligo"
        and row.get("status") == "ok"
        and row.get("prediction_match_type") == "exact"
        and as_float(row.get("qsglob") or row.get("score")) > 0.0
    ]
    d6a_problem_rows = [
        row
        for row in scoreable_scores
        if row.get("target_id") in D6A_INPUT_REPAIR_TARGETS
        and (row.get("status") != "ok" or as_float(row.get("score")) <= 0.0)
    ]
    antibody_rows = [row for row in scoreable_scores if row.get("target_id") in ANTIBODY_FV_TARGETS]
    antibody_nonzero = [
        row for row in antibody_rows if row.get("status") == "ok" and as_float(row.get("qsglob") or row.get("score")) > 0.0
    ]
    non_antibody_exact_oligo_nonzero = [
        row for row in exact_nonzero_oligo if row.get("target_id") not in ANTIBODY_FV_TARGETS
    ]

    fixed_numerator = 0.0
    fixed_denominator = 0
    track_payload: dict[str, dict[str, Any]] = {}
    for track in ("protein_domain", "protein_oligo"):
        row = track_rows.get(track, {})
        eligible_targets = as_int(row.get("eligible_targets"))
        mean_score = as_float(row.get("mean_score"))
        fixed_numerator += mean_score * eligible_targets
        fixed_denominator += eligible_targets
        track_scores = [score for score in selected_scores if score.get("track") == track]
        track_scoreable = [score for score in scoreable_scores if score.get("track") == track]
        track_payload[track] = {
            "mean_score": mean_score,
            "eligible_targets": eligible_targets,
            "ok_targets": as_int(row.get("ok_targets")),
            "scoreable_targets": len(track_scoreable),
            "scoreable_ok_targets": sum(1 for score in track_scoreable if score.get("status") == "ok"),
            "scoreable_nonzero_targets": sum(
                1 for score in track_scoreable if score.get("status") == "ok" and as_float(score.get("score")) > 0.0
            ),
            "status_counts": status_counts(track_scores),
            "scoreable_status_counts": status_counts(track_scoreable),
        }

    scoreable_actionable_failures = [
        row
        for row in scoreable_scores
        if row.get("status") in {"missing_prediction", "metric_failed", "metric_unavailable", "partial_candidates"}
    ]
    partial_candidate_targets = sum(as_int(row.get("partial_candidate_targets")) for row in selected_run_rows)
    metric_unavailable_targets = sum(as_int(row.get("metric_unavailable_targets")) for row in selected_run_rows)
    missing_scoreable_score_rows = max(0, len(scoreable_target_ids) - len(scoreable_scores))

    return {
        "run_id": run_id,
        "run_row_count": len(selected_run_rows),
        "target_score_rows": len(selected_scores),
        "fixed_set_mean": fixed_numerator / fixed_denominator if fixed_denominator else 0.0,
        "tracks": track_payload,
        "integrity": {
            "partial_candidate_targets": partial_candidate_targets,
            "metric_unavailable_targets": metric_unavailable_targets,
            "scoreable_actionable_failures": len(scoreable_actionable_failures),
            "missing_scoreable_score_rows": missing_scoreable_score_rows,
        },
        "status_counts": {
            "all": status_counts(selected_scores),
            "scoreable": status_counts(scoreable_scores),
            "no_reference": status_counts(no_reference_scores),
        },
        "target_sets": {
            "scoreable_score_rows": len(scoreable_scores),
            "no_reference_score_rows": len(no_reference_scores),
            "scoreable_nonzero_targets": sum(
                1 for row in scoreable_scores if row.get("status") == "ok" and as_float(row.get("score")) > 0.0
            ),
        },
        "diagnostics": {
            "d6a_problem_targets": sorted({row.get("target_id", "") for row in d6a_problem_rows}),
            "exact_nonzero_oligo_targets": sorted({row.get("target_id", "") for row in exact_nonzero_oligo}),
            "non_antibody_exact_nonzero_oligo_targets": sorted(
                {row.get("target_id", "") for row in non_antibody_exact_oligo_nonzero}
            ),
            "antibody_score_rows": len(antibody_rows),
            "antibody_nonzero_targets": sorted({row.get("target_id", "") for row in antibody_nonzero}),
        },
    }


def target_delta_summary(
    *,
    run_id: str,
    baseline_run_id: str,
    score_rows: Sequence[Mapping[str, str]],
    scoreable_target_ids: set[str],
    top_n: int = 10,
) -> dict[str, Any]:
    """Summarize scoreable-target deltas between two complete scored runs."""

    baseline_rows: dict[tuple[str, str], Mapping[str, str]] = {}
    run_rows: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in score_rows:
        target_id = row.get("target_id", "")
        if target_id not in scoreable_target_ids:
            continue
        key = (row.get("track", ""), target_id)
        if row.get("run_id") == baseline_run_id:
            baseline_rows[key] = row
        elif row.get("run_id") == run_id:
            run_rows[key] = row

    baseline_target_ids = {target_id for _, target_id in baseline_rows}
    run_target_ids = {target_id for _, target_id in run_rows}
    missing_baseline_targets = sorted(scoreable_target_ids - baseline_target_ids)
    missing_run_targets = sorted(scoreable_target_ids - run_target_ids)
    if missing_baseline_targets or missing_run_targets:
        return {
            "status": "incomplete",
            "valid_for_analysis": False,
            "run_id": run_id,
            "baseline_run_id": baseline_run_id,
            "scoreable_targets": len(scoreable_target_ids),
            "baseline_score_rows": len(baseline_target_ids),
            "run_score_rows": len(run_target_ids),
            "missing_baseline_score_rows": len(missing_baseline_targets),
            "missing_run_score_rows": len(missing_run_targets),
            "missing_baseline_targets": missing_baseline_targets[:top_n],
            "missing_run_targets": missing_run_targets[:top_n],
            "biggest_gains": [],
            "biggest_losses": [],
            "reason": "target score rows are incomplete; finish scoring before reading target deltas",
            "note": "For post-score diagnosis only; do not use target deltas for per-target prediction tuning.",
        }

    delta_rows: list[dict[str, Any]] = []
    for track, target_id in sorted(set(baseline_rows) | set(run_rows)):
        baseline_row = baseline_rows.get((track, target_id), {})
        run_row = run_rows.get((track, target_id), {})
        baseline_score = as_float(baseline_row.get("score"))
        run_score = as_float(run_row.get("score"))
        delta = run_score - baseline_score
        baseline_status = baseline_row.get("status") or "missing_score_row"
        run_status = run_row.get("status") or "missing_score_row"
        delta_rows.append(
            {
                "target_id": target_id,
                "track": track,
                "baseline_status": baseline_status,
                "run_status": run_status,
                "baseline_score": baseline_score,
                "run_score": run_score,
                "delta": delta,
            }
        )

    def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        transition_counts = Counter(
            f"{row.get('baseline_status', 'missing_score_row')}->{row.get('run_status', 'missing_score_row')}"
            for row in rows
        )
        total_delta = sum(float(row.get("delta", 0.0) or 0.0) for row in rows)
        comparable = sum(
            1
            for row in rows
            if row.get("baseline_status") != "missing_score_row" and row.get("run_status") != "missing_score_row"
        )
        return {
            "targets": len(rows),
            "comparable_targets": comparable,
            "mean_delta": total_delta / len(rows) if rows else 0.0,
            "improved_targets": sum(1 for row in rows if float(row.get("delta", 0.0) or 0.0) > 0.0),
            "regressed_targets": sum(1 for row in rows if float(row.get("delta", 0.0) or 0.0) < 0.0),
            "unchanged_targets": sum(1 for row in rows if float(row.get("delta", 0.0) or 0.0) == 0.0),
            "nonzero_gained_targets": sum(
                1
                for row in rows
                if float(row.get("baseline_score", 0.0) or 0.0) <= 0.0
                and float(row.get("run_score", 0.0) or 0.0) > 0.0
            ),
            "nonzero_lost_targets": sum(
                1
                for row in rows
                if float(row.get("baseline_score", 0.0) or 0.0) > 0.0
                and float(row.get("run_score", 0.0) or 0.0) <= 0.0
            ),
            "status_transition_counts": dict(sorted(transition_counts.items())),
        }

    biggest_gains = sorted(delta_rows, key=lambda row: float(row["delta"]), reverse=True)[:top_n]
    biggest_losses = sorted(delta_rows, key=lambda row: float(row["delta"]))[:top_n]
    by_track = {
        track: summarize([row for row in delta_rows if row.get("track") == track])
        for track in ("protein_domain", "protein_oligo")
    }
    return {
        "status": "ok",
        "valid_for_analysis": True,
        "run_id": run_id,
        "baseline_run_id": baseline_run_id,
        "scoreable_targets": len(scoreable_target_ids),
        "overall": summarize(delta_rows),
        "by_track": by_track,
        "biggest_gains": biggest_gains,
        "biggest_losses": biggest_losses,
        "note": "For post-score diagnosis only; do not use target deltas for per-target prediction tuning.",
    }


def post_p14_readout(
    *,
    project_root: Path,
    benchmark: str,
    run_id: str = DEFAULT_P14_RUN_ID,
    replay_run_id: str = DEFAULT_P16_REPLAY_RUN_ID,
    leaderboard_dir: Path | None = None,
    domain_floor: float = DEFAULT_DOMAIN_FLOOR,
    exact_domain_probe_floor: float = DEFAULT_EXACT_DOMAIN_PROBE_FLOOR,
    min_exact_oligo_nonzero: int = DEFAULT_MIN_EXACT_OLIGO_NONZERO,
) -> dict[str, Any]:
    """Summarize a completed P14-style run and recommend the next gated branch.

    This is intentionally a read-only leaderboard diagnostic. It uses generated
    leaderboard CSVs plus benchmark target metadata, not native structures or
    official per-target score tables.
    """

    root = project_root.resolve()
    output_dir = (leaderboard_dir or (root / "leaderboards" / benchmark)).resolve()
    runs_csv = output_dir / "runs.csv"
    target_scores_csv = output_dir / "target_scores.csv"
    targets_tsv = root / "benchmarks" / benchmark / "targets.tsv"
    for path in (runs_csv, target_scores_csv, targets_tsv):
        if not path.exists():
            raise FileNotFoundError(f"required readout input is missing: {path}")

    run_rows = read_csv_rows(runs_csv)
    score_rows = read_csv_rows(target_scores_csv)
    target_rows = read_tsv_rows(targets_tsv)

    scoreable_target_ids, no_reference_target_ids = scoreable_target_sets(target_rows)

    selected_run_rows = [row for row in run_rows if row.get("run_id") == run_id]
    selected_replay_rows = [row for row in run_rows if replay_run_id and row.get("run_id") == replay_run_id]
    selected_scores = [row for row in score_rows if row.get("run_id") == run_id]
    scoreable_scores = [row for row in selected_scores if row.get("target_id", "") in scoreable_target_ids]
    no_reference_scores = [row for row in selected_scores if row.get("target_id", "") in no_reference_target_ids]

    track_rows = {row.get("track", ""): row for row in selected_run_rows}
    domain_row = track_rows.get("protein_domain", {})
    oligo_row = track_rows.get("protein_oligo", {})
    domain_mean = as_float(domain_row.get("mean_score"))
    oligo_mean = as_float(oligo_row.get("mean_score"))
    partial_candidate_targets = sum(as_int(row.get("partial_candidate_targets")) for row in selected_run_rows)
    metric_unavailable_targets = sum(as_int(row.get("metric_unavailable_targets")) for row in selected_run_rows)

    exact_nonzero_oligo = [
        row
        for row in selected_scores
        if row.get("track") == "protein_oligo"
        and row.get("status") == "ok"
        and row.get("prediction_match_type") == "exact"
        and as_float(row.get("qsglob") or row.get("score")) > 0.0
    ]
    nonzero_domain = [
        row
        for row in selected_scores
        if row.get("track") == "protein_domain" and row.get("status") == "ok" and as_float(row.get("score")) > 0.0
    ]
    scoreable_actionable_failures = [
        row
        for row in scoreable_scores
        if row.get("status") in {"missing_prediction", "metric_failed", "metric_unavailable", "partial_candidates"}
    ]
    d6a_problem_rows = [
        row
        for row in selected_scores
        if row.get("target_id") in D6A_INPUT_REPAIR_TARGETS
        and (row.get("status") != "ok" or as_float(row.get("score")) <= 0.0)
    ]
    antibody_rows = [row for row in selected_scores if row.get("target_id") in ANTIBODY_FV_TARGETS]
    antibody_nonzero = [row for row in antibody_rows if row.get("status") == "ok" and as_float(row.get("qsglob") or row.get("score")) > 0.0]
    non_antibody_exact_oligo_nonzero = [
        row for row in exact_nonzero_oligo if row.get("target_id") not in ANTIBODY_FV_TARGETS
    ]

    integrity = {
        "p14_rows": len(selected_run_rows),
        "p16_replay_rows": len(selected_replay_rows),
        "partial_candidate_targets": partial_candidate_targets,
        "metric_unavailable_targets": metric_unavailable_targets,
        "scoreable_actionable_failures": len(scoreable_actionable_failures),
    }

    if not selected_run_rows:
        next_branch = "finish_or_score_p14"
        decision_status = "not_scored"
        reason = f"run {run_id!r} is absent from runs.csv"
    elif replay_run_id and not selected_replay_rows:
        next_branch = "register_p16_replay_before_inspection"
        decision_status = "needs_replay"
        reason = f"replay run {replay_run_id!r} is absent from runs.csv"
    elif partial_candidate_targets or metric_unavailable_targets or scoreable_actionable_failures:
        next_branch = "fix_pipeline_before_more_gpu"
        decision_status = "blocked_by_score_path"
        reason = "scoreable rows still have partial candidates, unavailable metrics, missing predictions, or metric failures"
    elif domain_mean > exact_domain_probe_floor and len(exact_nonzero_oligo) >= min_exact_oligo_nonzero:
        next_branch = "launch_p18_p25_scoreable_25_candidate_grid"
        decision_status = "candidate_limited_signal"
        reason = "domain mean clears the exact-domain probe floor and exact oligo QSglob has multiple nonzero rows"
    elif (domain_mean > exact_domain_probe_floor or exact_nonzero_oligo) and no_reference_scores:
        next_branch = "launch_p15_v4_refmap_or_continue_versioned_refmap"
        decision_status = "reference_limited_signal"
        reason = "scoreable-target signal exists while fixed-set zeros remain dominated by missing references"
    elif d6a_problem_rows:
        next_branch = "launch_d6a_domain_sequence_recovery"
        decision_status = "input_repair_signal"
        reason = "known domain input-repair targets remain missing or zero"
    elif antibody_rows and non_antibody_exact_oligo_nonzero and not antibody_nonzero:
        next_branch = "launch_o5_antibody_fv_target_shards"
        decision_status = "antibody_fv_signal"
        reason = "non-antibody exact oligos have signal but antibody/Fv rows remain zero"
    else:
        next_branch = "launch_p27a_defaultparams_model_variant"
        decision_status = "valid_but_weak"
        reason = "predictions and metrics are valid, but P14 does not justify 25-seed scaling"

    return {
        "benchmark": benchmark,
        "run_id": run_id,
        "replay_run_id": replay_run_id,
        "decision_status": decision_status,
        "next_branch": next_branch,
        "reason": reason,
        "thresholds": {
            "domain_floor": domain_floor,
            "exact_domain_probe_floor": exact_domain_probe_floor,
            "min_exact_oligo_nonzero": min_exact_oligo_nonzero,
        },
        "tracks": {
            "protein_domain": {
                "mean_score": domain_mean,
                "ok_targets": as_int(domain_row.get("ok_targets")),
                "nonzero_targets": len(nonzero_domain),
                "eligible_targets": as_int(domain_row.get("eligible_targets")),
            },
            "protein_oligo": {
                "mean_score": oligo_mean,
                "ok_targets": as_int(oligo_row.get("ok_targets")),
                "exact_nonzero_qsglob_targets": len(exact_nonzero_oligo),
                "eligible_targets": as_int(oligo_row.get("eligible_targets")),
            },
        },
        "integrity": integrity,
        "status_counts": {
            "all": status_counts(selected_scores),
            "scoreable": status_counts(scoreable_scores),
            "no_reference": status_counts(no_reference_scores),
        },
        "target_sets": {
            "scoreable_targets": len(scoreable_target_ids),
            "no_reference_targets": len(no_reference_target_ids),
            "score_rows": len(selected_scores),
        },
        "diagnostics": {
            "d6a_problem_targets": sorted({row.get("target_id", "") for row in d6a_problem_rows}),
            "exact_nonzero_oligo_targets": sorted({row.get("target_id", "") for row in exact_nonzero_oligo}),
            "antibody_rows": len(antibody_rows),
            "antibody_nonzero_targets": sorted({row.get("target_id", "") for row in antibody_nonzero}),
        },
        "inputs": {
            "runs_csv": str(runs_csv),
            "target_scores_csv": str(target_scores_csv),
            "targets_tsv": str(targets_tsv),
        },
    }


def post_p25_readout(
    *,
    project_root: Path,
    benchmark: str,
    run_id: str = DEFAULT_P25_RUN_ID,
    baseline_run_id: str = DEFAULT_P17_RUN_ID,
    leaderboard_dir: Path | None = None,
    min_mean_delta: float = 0.01,
    min_track_delta: float = 0.02,
    strong_scoreable_nonzero_fraction: float = 0.40,
) -> dict[str, Any]:
    """Read a completed P25-style leaderboard and recommend the next branch.

    This readout is deliberately aggregate-level. It compares run summaries and
    score-path status counts; it does not inspect native structures, official
    per-target score tables, or use individual target scores for tuning.
    """

    root = project_root.resolve()
    output_dir = (leaderboard_dir or (root / "leaderboards" / benchmark)).resolve()
    runs_csv = output_dir / "runs.csv"
    target_scores_csv = output_dir / "target_scores.csv"
    targets_tsv = root / "benchmarks" / benchmark / "targets.tsv"
    for path in (runs_csv, target_scores_csv, targets_tsv):
        if not path.exists():
            raise FileNotFoundError(f"required readout input is missing: {path}")

    run_rows = read_csv_rows(runs_csv)
    score_rows = read_csv_rows(target_scores_csv)
    target_rows = read_tsv_rows(targets_tsv)
    scoreable_target_ids, no_reference_target_ids = scoreable_target_sets(target_rows)

    p25 = run_readout_summary(
        run_id=run_id,
        run_rows=run_rows,
        score_rows=score_rows,
        scoreable_target_ids=scoreable_target_ids,
        no_reference_target_ids=no_reference_target_ids,
    )
    baseline = run_readout_summary(
        run_id=baseline_run_id,
        run_rows=run_rows,
        score_rows=score_rows,
        scoreable_target_ids=scoreable_target_ids,
        no_reference_target_ids=no_reference_target_ids,
    )

    domain_delta = p25["tracks"]["protein_domain"]["mean_score"] - baseline["tracks"]["protein_domain"]["mean_score"]
    oligo_delta = p25["tracks"]["protein_oligo"]["mean_score"] - baseline["tracks"]["protein_oligo"]["mean_score"]
    fixed_set_delta = p25["fixed_set_mean"] - baseline["fixed_set_mean"]
    scoreable_nonzero_fraction = (
        p25["target_sets"]["scoreable_nonzero_targets"] / len(scoreable_target_ids) if scoreable_target_ids else 0.0
    )
    p25_integrity = p25["integrity"]

    if not p25["run_row_count"]:
        decision_status = "not_scored"
        next_branch = "finish_or_score_p25"
        reason = f"run {run_id!r} is absent from runs.csv"
    elif not p25["target_score_rows"]:
        decision_status = "not_scored"
        next_branch = "score_p25_before_decision"
        reason = f"run {run_id!r} has run rows but no target_scores.csv rows"
    elif p25_integrity["partial_candidate_targets"] or p25_integrity["missing_scoreable_score_rows"]:
        decision_status = "not_complete"
        next_branch = "finish_or_repair_p25_candidate_grid"
        reason = "P25 still has partial candidates or missing scoreable target-score rows"
    elif p25_integrity["metric_unavailable_targets"] or p25_integrity["scoreable_actionable_failures"]:
        decision_status = "blocked_by_score_path"
        next_branch = "fix_p25_score_path_before_more_gpu"
        reason = "scoreable P25 rows still have missing predictions, metric failures, or unavailable metrics"
    elif not baseline["run_row_count"]:
        decision_status = "baseline_missing"
        next_branch = "score_p17_baseline_before_branching"
        reason = f"baseline run {baseline_run_id!r} is absent from runs.csv"
    elif fixed_set_delta >= min_mean_delta or max(domain_delta, oligo_delta) >= min_track_delta:
        decision_status = "seed_scaling_signal"
        next_branch = "analyze_p25_aggregate_deltas_then_pick_model_variant"
        reason = "P25 improves the fixed-set aggregate or one ranked track over the P17 baseline"
    elif p25["diagnostics"]["d6a_problem_targets"]:
        decision_status = "input_repair_signal"
        next_branch = "launch_d6a_domain_sequence_recovery_after_p25"
        reason = "predeclared scoreable domain input-repair targets remain missing or zero after P25"
    elif (
        p25["diagnostics"]["antibody_score_rows"]
        and p25["diagnostics"]["non_antibody_exact_nonzero_oligo_targets"]
        and not p25["diagnostics"]["antibody_nonzero_targets"]
    ):
        decision_status = "antibody_fv_signal"
        next_branch = "launch_o5b_antibody_fv_after_p25"
        reason = "non-antibody exact oligos have signal while predeclared antibody/Fv scoreable rows remain zero"
    elif no_reference_target_ids and scoreable_nonzero_fraction >= strong_scoreable_nonzero_fraction:
        decision_status = "reference_limited_signal"
        next_branch = "continue_versioned_refmap_or_score_p15_v4"
        reason = "scoreable targets have broad nonzero signal while the fixed server set is still reference-capped"
    elif p25["tracks"]["protein_oligo"]["scoreable_nonzero_targets"] < baseline["tracks"]["protein_oligo"]["scoreable_nonzero_targets"]:
        decision_status = "oligo_regression_signal"
        next_branch = "launch_oligo_or_antibody_fv_model_config_after_p25"
        reason = "P25 does not improve the aggregate and loses nonzero oligo coverage versus baseline"
    else:
        decision_status = "model_config_diversity_signal"
        next_branch = "launch_p27b_model_config_diversity_after_p25"
        reason = "P25 is complete but flat; candidate count alone is not the next best lever"

    delta_summary = target_delta_summary(
        run_id=run_id,
        baseline_run_id=baseline_run_id,
        score_rows=score_rows,
        scoreable_target_ids=scoreable_target_ids,
    )
    if decision_status in {"not_scored", "not_complete", "baseline_missing"}:
        delta_summary = dict(delta_summary)
        delta_summary["valid_for_analysis"] = False
        delta_summary["reason"] = (
            f"target deltas are diagnostic only after a complete scored P25 row; current status is {decision_status}."
        )

    return {
        "benchmark": benchmark,
        "run_id": run_id,
        "baseline_run_id": baseline_run_id,
        "decision_status": decision_status,
        "next_branch": next_branch,
        "reason": reason,
        "thresholds": {
            "min_mean_delta": min_mean_delta,
            "min_track_delta": min_track_delta,
            "strong_scoreable_nonzero_fraction": strong_scoreable_nonzero_fraction,
        },
        "comparison": {
            "fixed_set_delta": fixed_set_delta,
            "domain_delta": domain_delta,
            "oligo_delta": oligo_delta,
            "scoreable_nonzero_fraction": scoreable_nonzero_fraction,
        },
        "target_delta_summary": delta_summary,
        "launch_plan": enrich_launch_plan(root, post_p25_launch_plan(next_branch, decision_status)),
        "p25": p25,
        "baseline": baseline,
        "target_sets": {
            "scoreable_targets": len(scoreable_target_ids),
            "no_reference_targets": len(no_reference_target_ids),
        },
        "inputs": {
            "runs_csv": str(runs_csv),
            "target_scores_csv": str(target_scores_csv),
            "targets_tsv": str(targets_tsv),
        },
    }
