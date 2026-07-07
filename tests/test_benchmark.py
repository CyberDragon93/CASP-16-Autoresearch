from __future__ import annotations

import csv
import json

import pytest

from casp16_leaderboard import benchmark as benchmark_module
from casp16_leaderboard.benchmark import (
    SERVER_ALIASFIX_BENCHMARK_NAME,
    SERVER_ALIASFIX_BENCHMARK_VERSION,
    SERVER_REFMAP_BENCHMARK_NAME,
    SERVER_REFMAP_BENCHMARK_VERSION,
    audit_reference_candidate_chains,
    audit_reference_candidate_oligo_assemblies,
    build_casp16_protein_benchmark,
    build_casp16_server_protein_benchmark,
    generate_reference_gap_report,
    generate_reference_map_audit_report,
    generate_reference_map_review,
    generate_rcsb_exact_sequence_probe,
    materialize_reference_map_candidates,
)
from casp16_leaderboard.leaderboard import generate_benchmark_leaderboard
from casp16_leaderboard.official import OfficialPaths, read_tsv, write_tsv


def write_fixture_official(root) -> None:
    paths = OfficialPaths(root)
    write_tsv(
        paths.targets_tsv,
        [
            {
                "target_id": "T1201",
                "target_prefix": "T",
                "Target": "T1201",
                "Type": "All groups",
                "Res": "210",
                "Oligo.State": "A2",
                "Entry Date": "",
                "Server Exp.": "",
                "Human Exp.": "",
                "QA Exp.": "",
                "Cancellation Date": "-",
                "Description": "protein 8bwd",
            },
            {
                "target_id": "H1202",
                "target_prefix": "H",
                "Target": "H1202",
                "Type": "All groups",
                "Res": "190",
                "Oligo.State": "A2B2",
                "Entry Date": "",
                "Server Exp.": "",
                "Human Exp.": "",
                "QA Exp.": "",
                "Cancellation Date": "-",
                "Description": "complex 8bwl",
            },
            {
                "target_id": "R1203",
                "target_prefix": "R",
                "Target": "R1203",
                "Type": "NucA",
                "Res": "134",
                "Oligo.State": "R1",
                "Entry Date": "",
                "Server Exp.": "",
                "Human Exp.": "",
                "QA Exp.": "",
                "Cancellation Date": "-",
                "Description": "rna",
            },
            {
                "target_id": "H0222",
                "target_prefix": "H",
                "Target": "H0222",
                "Type": "All groups",
                "Res": "485",
                "Oligo.State": "UNK",
                "Entry Date": "",
                "Server Exp.": "",
                "Human Exp.": "",
                "QA Exp.": "",
                "Cancellation Date": "-",
                "Description": "RSV G - Fab 2B11 complex",
            },
            {
                "target_id": "H1222",
                "target_prefix": "H",
                "Target": "H1222",
                "Type": "All groups",
                "Res": "485",
                "Oligo.State": "A1B1C1",
                "Entry Date": "",
                "Server Exp.": "",
                "Human Exp.": "",
                "QA Exp.": "",
                "Cancellation Date": "-",
                "Description": "RSV G - Fab 2B11 complex 9cqd",
            },
        ],
        ["target_id", "target_prefix", "Target", "Type", "Res", "Oligo.State", "Entry Date", "Server Exp.", "Human Exp.", "QA Exp.", "Cancellation Date", "Description"],
    )
    write_tsv(
        paths.sequences_tsv,
        [
            {"record_id": "T1201", "target_ids": "T1201", "sequence_family": "T", "sequence_kind": "proteinChain", "length": "3", "sequence": "ACD", "header": "", "source_file": ""},
            {"record_id": "H1202A", "target_ids": "H1202", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "ACD", "header": "", "source_file": ""},
            {"record_id": "H1202B", "target_ids": "H1202", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "EFG", "header": "", "source_file": ""},
            {"record_id": "H1222A", "target_ids": "H1222", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "AAA", "header": "", "source_file": ""},
            {"record_id": "H1222B", "target_ids": "H1222", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "BBB", "header": "", "source_file": ""},
            {"record_id": "H1222C", "target_ids": "H1222", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "CCC", "header": "", "source_file": ""},
        ],
        ["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"],
    )
    write_tsv(
        paths.domains_tsv,
        [{"target_id": "T1201", "target_len": "210", "domain_id": "T1201-D1", "residue_ranges": "1-3", "domain_len": "3", "difficulty": "easy", "pdb_ids": "8bwd", "source": ""}],
        ["target_id", "target_len", "domain_id", "residue_ranges", "domain_len", "difficulty", "pdb_ids", "source"],
    )
    (paths.references_dir / "mmcif").mkdir(parents=True)
    (paths.references_dir / "mmcif" / "8bwd.cif").write_text("data_8bwd\n", encoding="utf-8")
    (paths.references_dir / "mmcif" / "8bwl.cif").write_text("data_8bwl\n", encoding="utf-8")
    (paths.references_dir / "mmcif" / "9cqd.cif").write_text("data_9cqd\n", encoding="utf-8")
    write_tsv(
        paths.target_references_tsv,
        [{"target_id": "H1222", "pdb_ids": "9cqd", "source": "targetlist.cgi"}],
        ["target_id", "pdb_ids", "source"],
    )
    write_tsv(
        paths.scores_tsv,
        [
            {
                "category": "prot_domains",
                "table": "domains.csv",
                "target_id": "T1201",
                "model": "T1201TS022_1-D1",
                "group": "022",
                "submitted_model_rank": "1",
                "primary_metric": "GDT_TS",
                "primary_score": "95.000000",
                "metric_json": "{}",
                "source_path": "domains.csv",
            },
            {
                "category": "prot_domains",
                "table": "domains.csv",
                "target_id": "T1201",
                "model": "T1201TS110_1-D1",
                "group": "110s",
                "submitted_model_rank": "2",
                "primary_metric": "GDT_TS",
                "primary_score": "90.000000",
                "metric_json": "{}",
                "source_path": "domains.csv",
            },
            {
                "category": "prot_domains",
                "table": "domains.csv",
                "target_id": "",
                "model": "T0208s1TS147_4-D1",
                "group": "147s",
                "submitted_model_rank": "3",
                "primary_metric": "GDT_TS",
                "primary_score": "96.000000",
                "metric_json": "{}",
                "source_path": "domains.csv",
            },
            {
                "category": "prot_oligo",
                "table": "oligo.csv",
                "target_id": "H1202",
                "model": "H1202TS051_1",
                "group": "051",
                "submitted_model_rank": "1",
                "primary_metric": "QSglob",
                "primary_score": "0.700000",
                "metric_json": "{}",
                "source_path": "oligo.csv",
            },
            {
                "category": "prot_oligo",
                "table": "oligo.csv",
                "target_id": "H1202",
                "model": "H1202TS456_1",
                "group": "456s",
                "submitted_model_rank": "2",
                "primary_metric": "QSglob",
                "primary_score": "0.500000",
                "metric_json": "{}",
                "source_path": "oligo.csv",
            },
            {
                "category": "prot_oligo",
                "table": "oligo.csv",
                "target_id": "T1201o",
                "model": "T1201TS456_1o",
                "group": "456s",
                "submitted_model_rank": "1",
                "primary_metric": "QSglob",
                "primary_score": "0.600000",
                "metric_json": "{}",
                "source_path": "oligo.csv",
            },
            {
                "category": "prot_oligo",
                "table": "oligo.csv",
                "target_id": "H1222",
                "model": "H1222TS051_1",
                "group": "051",
                "submitted_model_rank": "1",
                "primary_metric": "QSglob",
                "primary_score": "0.800000",
                "metric_json": "{}",
                "source_path": "oligo.csv",
            },
        ],
        ["category", "table", "target_id", "model", "group", "submitted_model_rank", "primary_metric", "primary_score", "metric_json", "source_path"],
    )


def test_build_benchmark_protein_first(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)

    summary = build_casp16_protein_benchmark(project_root=project_root, official_root=official_root)
    assert summary["input_jobs"] == 4
    assert summary["rank_eligible"] == 4

    benchmark_dir = project_root / "benchmarks" / "casp16_protein_v1"
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["T1201"]["rank_eligible"] == "true"
    assert targets["H1202"]["rank_eligible"] == "true"
    assert targets["H0222"]["selected_pdb_id"] == "9cqd"
    assert targets["H1222"]["selected_pdb_id"] == "9cqd"
    assert targets["H0222"]["reference_path"].endswith("9cqd.cif")
    assert targets["H1222"]["reference_path"].endswith("9cqd.cif")
    assert targets["R1203"]["skip_reason"] == "unsupported_category"

    inputs = json.loads((benchmark_dir / "inputs.json").read_text(encoding="utf-8"))
    h_job = next(job for job in inputs if job["name"] == "H1202")
    assert h_job["sequences"][0]["proteinChain"]["count"] == 2
    assert h_job["sequences"][1]["proteinChain"]["id"] == ["C", "D"]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_build_server_benchmark_from_official_scores(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)

    summary = build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)
    assert summary["benchmark"] == "casp16_server_protein_v1"
    assert summary["target_sets"] == {"prot_domains": 1, "prot_oligo": 3}
    assert summary["input_jobs"] == 4
    assert summary["unresolved_official_targets"] == 1

    benchmark_dir = project_root / "benchmarks" / "casp16_server_protein_v1"
    payload = json.loads((benchmark_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert payload["official_target_sets"] == {"prot_domains": 1, "prot_oligo": 3}
    assert payload["official_metrics"] == {"prot_domains": "GDT_TS", "prot_oligo": "QSglob"}

    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert set(targets) == {"T1201", "H1202", "H1222", "T1201O"}
    assert targets["T1201O"]["track"] == "protein_oligo"
    assert targets["T1201O"]["sequence_lookup_id"] == "T1201"
    assert targets["T1201O"]["rank_eligible"] == "true"

    server_groups = read_csv(benchmark_dir / "official_server_groups.tsv")
    domain_top = next(row for row in server_groups if row["category"] == "prot_domains" and row["rank"] == "1")
    oligo_top = next(row for row in server_groups if row["category"] == "prot_oligo" and row["rank"] == "1")
    assert domain_top["group"] == "110s"
    assert domain_top["mean_fixed_score"] == "0.900000"
    assert oligo_top["group"] == "456s"
    assert oligo_top["eligible_target_count"] == "3"
    assert oligo_top["missing_target_count"] == "1"
    assert oligo_top["mean_fixed_score"] == "0.366667"


def test_build_aliasfix_server_benchmark_version(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)

    summary = build_casp16_server_protein_benchmark(
        project_root=project_root,
        official_root=official_root,
        benchmark_name=SERVER_ALIASFIX_BENCHMARK_NAME,
        benchmark_version=SERVER_ALIASFIX_BENCHMARK_VERSION,
    )

    assert summary["benchmark"] == SERVER_ALIASFIX_BENCHMARK_NAME
    assert summary["version"] == SERVER_ALIASFIX_BENCHMARK_VERSION
    benchmark_dir = project_root / "benchmarks" / SERVER_ALIASFIX_BENCHMARK_NAME
    payload = json.loads((benchmark_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert payload["name"] == SERVER_ALIASFIX_BENCHMARK_NAME
    assert payload["version"] == SERVER_ALIASFIX_BENCHMARK_VERSION

    output_dir = project_root / "leaderboards" / SERVER_ALIASFIX_BENCHMARK_NAME
    generate_benchmark_leaderboard(project_root=project_root, benchmark=SERVER_ALIASFIX_BENCHMARK_NAME, output_dir=output_dir, official_root=official_root)
    assert (output_dir / "official_server_groups.csv").exists()
    assert (output_dir / "official_all_groups.csv").exists()


def test_server_benchmark_exact_metadata_beats_early_phase_alias(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)

    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)

    benchmark_dir = project_root / "benchmarks" / "casp16_server_protein_v1"
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["H1222"]["oligo_state"] == "A1B1C1"
    assert targets["H1222"]["chain_count"] == "3"


def test_server_benchmark_can_inherit_later_phase_oligo_state(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    paths = OfficialPaths(official_root)
    score_rows = read_tsv(paths.scores_tsv)
    score_rows.append(
        {
            "category": "prot_oligo",
            "table": "oligo.csv",
            "target_id": "H0222",
            "model": "H0222TS456_1",
            "group": "456s",
            "submitted_model_rank": "1",
            "primary_metric": "QSglob",
            "primary_score": "0.500000",
            "metric_json": "{}",
            "source_path": "oligo.csv",
        }
    )
    write_tsv(
        paths.scores_tsv,
        score_rows,
        ["category", "table", "target_id", "model", "group", "submitted_model_rank", "primary_metric", "primary_score", "metric_json", "source_path"],
    )

    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)

    benchmark_dir = project_root / "benchmarks" / "casp16_server_protein_v1"
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["H0222"]["oligo_state"] == "A1B1C1"
    assert targets["H0222"]["chain_count"] == "3"


def test_server_benchmark_uses_phase_2_reference_aliases(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    paths = OfficialPaths(official_root)
    score_rows = read_tsv(paths.scores_tsv)
    score_rows.extend(
        [
            {
                "category": "prot_domains",
                "table": "domains.csv",
                "target_id": "T2201",
                "model": "T2201TS110_1-D1",
                "group": "110s",
                "submitted_model_rank": "1",
                "primary_metric": "GDT_TS",
                "primary_score": "91.000000",
                "metric_json": "{}",
                "source_path": "domains.csv",
            },
            {
                "category": "prot_oligo",
                "table": "oligo.csv",
                "target_id": "H2202",
                "model": "H2202TS456_1",
                "group": "456s",
                "submitted_model_rank": "1",
                "primary_metric": "QSglob",
                "primary_score": "0.600000",
                "metric_json": "{}",
                "source_path": "oligo.csv",
            },
        ]
    )
    write_tsv(
        paths.scores_tsv,
        score_rows,
        ["category", "table", "target_id", "model", "group", "submitted_model_rank", "primary_metric", "primary_score", "metric_json", "source_path"],
    )

    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)

    benchmark_dir = project_root / "benchmarks" / "casp16_server_protein_v1"
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["T2201"]["sequence_lookup_id"] == "T2201"
    assert targets["T2201"]["selected_pdb_id"] == "8bwd"
    assert targets["T2201"]["reference_path"].endswith("8bwd.cif")
    assert targets["H2202"]["sequence_lookup_id"] == "H2202"
    assert targets["H2202"]["selected_pdb_id"] == "8bwl"
    assert targets["H2202"]["reference_path"].endswith("8bwl.cif")


def test_server_benchmark_reference_map_overlay_requires_new_version(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    refmap = tmp_path / "reference_map.tsv"
    write_tsv(
        refmap,
        [
            {
                "target_id": "T1226",
                "pdb_ids": "9abc",
                "status": "accepted",
                "source": "manual_audit",
                "native_provenance": "native release audited",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "target_entity_1:chain_A",
                "scoring_mapping": "domain T1226-D1 residues 1-3 chain A",
                "notes": "",
            }
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes"],
    )

    with pytest.raises(ValueError, match="require a new server benchmark name"):
        build_casp16_server_protein_benchmark(
            project_root=project_root,
            official_root=official_root,
            benchmark_name=SERVER_ALIASFIX_BENCHMARK_NAME,
            benchmark_version=SERVER_ALIASFIX_BENCHMARK_VERSION,
            reference_map_paths=[refmap],
        )


def test_server_refmap_benchmark_applies_accepted_reference_overlay(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    paths = OfficialPaths(official_root)

    target_rows = read_tsv(paths.targets_tsv)
    target_rows.append(
        {
            "target_id": "T1226",
            "target_prefix": "T",
            "Target": "T1226",
            "Type": "All groups",
            "Res": "123",
            "Oligo.State": "A1",
            "Entry Date": "",
            "Server Exp.": "",
            "Human Exp.": "",
            "QA Exp.": "",
            "Cancellation Date": "-",
            "Description": "unreleased native",
        }
    )
    write_tsv(
        paths.targets_tsv,
        target_rows,
        ["target_id", "target_prefix", "Target", "Type", "Res", "Oligo.State", "Entry Date", "Server Exp.", "Human Exp.", "QA Exp.", "Cancellation Date", "Description"],
    )
    sequence_rows = read_tsv(paths.sequences_tsv)
    sequence_rows.append({"record_id": "T1226", "target_ids": "T1226", "sequence_family": "T", "sequence_kind": "proteinChain", "length": "3", "sequence": "XYZ", "header": "", "source_file": ""})
    write_tsv(paths.sequences_tsv, sequence_rows, ["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"])
    domain_rows = read_tsv(paths.domains_tsv)
    domain_rows.append({"target_id": "T1226", "target_len": "123", "domain_id": "T1226-D1", "residue_ranges": "1-3", "domain_len": "3", "difficulty": "hard", "pdb_ids": "", "source": ""})
    write_tsv(paths.domains_tsv, domain_rows, ["target_id", "target_len", "domain_id", "residue_ranges", "domain_len", "difficulty", "pdb_ids", "source"])
    score_rows = read_tsv(paths.scores_tsv)
    score_rows.append(
        {
            "category": "prot_domains",
            "table": "domains.csv",
            "target_id": "T1226",
            "model": "T1226TS110_1-D1",
            "group": "110s",
            "submitted_model_rank": "1",
            "primary_metric": "GDT_TS",
            "primary_score": "88.000000",
            "metric_json": "{}",
            "source_path": "domains.csv",
        }
    )
    write_tsv(
        paths.scores_tsv,
        score_rows,
        ["category", "table", "target_id", "model", "group", "submitted_model_rank", "primary_metric", "primary_score", "metric_json", "source_path"],
    )
    (paths.references_dir / "mmcif" / "9abc.cif").write_text("data_9abc\n", encoding="utf-8")
    refmap = tmp_path / "reference_map.tsv"
    write_tsv(
        refmap,
        [
            {
                "target_id": "T1226",
                "pdb_ids": "9abc",
                "status": "accepted",
                "source": "manual_audit",
                "native_provenance": "native release audited",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "target_entity_1:chain_A",
                "scoring_mapping": "domain T1226-D1 residues 1-3 chain A",
                "notes": "",
            },
            {
                "target_id": "T1231",
                "pdb_ids": "9def",
                "status": "candidate",
                "source": "sequence_search",
                "native_provenance": "",
                "construct_coverage": "",
                "chain_mapping": "",
                "scoring_mapping": "",
                "notes": "audit only",
            },
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes"],
    )

    summary = build_casp16_server_protein_benchmark(
        project_root=project_root,
        official_root=official_root,
        benchmark_name=SERVER_REFMAP_BENCHMARK_NAME,
        benchmark_version=SERVER_REFMAP_BENCHMARK_VERSION,
        reference_map_paths=[refmap],
    )

    assert summary["benchmark"] == SERVER_REFMAP_BENCHMARK_NAME
    assert summary["reference_map_rows"] == 2
    assert summary["reference_map_accepted"] == 1
    benchmark_dir = project_root / "benchmarks" / SERVER_REFMAP_BENCHMARK_NAME
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["T1226"]["selected_pdb_id"] == "9abc"
    assert targets["T1226"]["reference_status"] == "available"
    assert targets["T1226"]["reference_path"].endswith("9abc.cif")
    payload = json.loads((benchmark_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert "reference_map" in payload["files"]
    assert (benchmark_dir / "reference_map.tsv").exists()


def test_generate_reference_map_review_from_rcsb_candidates(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)
    candidate_tsv = tmp_path / "candidates.tsv"
    write_tsv(
        candidate_tsv,
        [
            {
                "target_id": "T1201",
                "track": "protein_domain",
                "sequence_lookup_id": "T1201",
                "hit": "9abc_1",
                "pdb_id": "9ABC",
                "entity_id": "1",
                "entry_title": "exact candidate",
                "release_date": "2026-01-01",
                "experimental_method": "X-RAY DIFFRACTION",
                "asym_ids": "A,B",
                "auth_asym_ids": "A,B",
                "target_sequence_equals_entity": "true",
                "target_sequence_contained_in_entity": "true",
                "entity_sequence_contained_in_target": "true",
                "candidate_status": "full_construct_exact_candidate_needs_native_provenance_and_mapping",
            },
            {
                "target_id": "T1201",
                "track": "protein_domain",
                "sequence_lookup_id": "T1201",
                "hit": "9def_1",
                "pdb_id": "9DEF",
                "entity_id": "1",
                "entry_title": "partial candidate",
                "release_date": "2026-01-01",
                "experimental_method": "X-RAY DIFFRACTION",
                "asym_ids": "A",
                "auth_asym_ids": "A",
                "target_sequence_equals_entity": "false",
                "target_sequence_contained_in_entity": "false",
                "entity_sequence_contained_in_target": "false",
                "candidate_status": "local_sequence_hit_not_full_construct_do_not_promote",
            },
        ],
        [
            "target_id",
            "track",
            "sequence_lookup_id",
            "hit",
            "pdb_id",
            "entity_id",
            "entry_title",
            "release_date",
            "experimental_method",
            "asym_ids",
            "auth_asym_ids",
            "target_sequence_equals_entity",
            "target_sequence_contained_in_entity",
            "entity_sequence_contained_in_target",
            "candidate_status",
        ],
    )
    output_tsv = tmp_path / "review.tsv"

    summary = generate_reference_map_review(project_root=project_root, benchmark="casp16_server_protein_v1", candidate_tsv=candidate_tsv, output_tsv=output_tsv)

    assert summary["rows"] == 2
    assert summary["candidate"] == 1
    assert summary["rejected"] == 1
    rows = read_tsv(output_tsv)
    assert rows[0]["status"] == "candidate"
    assert rows[0]["pdb_ids"] == "9abc"
    assert rows[0]["construct_coverage"] == "full_construct_exact_sequence"
    assert "candidate_domain=T1201-D1" in rows[0]["scoring_mapping"]
    assert rows[0]["native_provenance"] == ""
    assert rows[1]["status"] == "rejected"


def test_generate_reference_map_review_uses_domain_aliases(tmp_path) -> None:
    project_root = tmp_path / "project"
    benchmark_dir = project_root / "benchmarks" / "casp16_server_protein_v1"
    benchmark_dir.mkdir(parents=True)
    write_tsv(
        benchmark_dir / "targets.tsv",
        [{"target_id": "T2201", "track": "protein_domain"}],
        ["target_id", "track"],
    )
    write_tsv(
        benchmark_dir / "domain_definitions.tsv",
        [{"target_id": "T1201", "domain_id": "T1201-D1", "residue_ranges": "34-370"}],
        ["target_id", "domain_id", "residue_ranges"],
    )
    candidate_tsv = tmp_path / "candidates.tsv"
    write_tsv(
        candidate_tsv,
        [
            {
                "target_id": "T2201",
                "track": "protein_domain",
                "sequence_lookup_id": "T2201",
                "hit": "9abc_1",
                "pdb_id": "9ABC",
                "entity_id": "1",
                "entry_title": "phase alias candidate",
                "release_date": "2026-01-01",
                "experimental_method": "X-RAY DIFFRACTION",
                "asym_ids": "A",
                "auth_asym_ids": "A",
                "target_sequence_equals_entity": "true",
                "target_sequence_contained_in_entity": "true",
                "entity_sequence_contained_in_target": "true",
                "candidate_status": "full_construct_exact_candidate_needs_native_provenance_and_mapping",
            }
        ],
        [
            "target_id",
            "track",
            "sequence_lookup_id",
            "hit",
            "pdb_id",
            "entity_id",
            "entry_title",
            "release_date",
            "experimental_method",
            "asym_ids",
            "auth_asym_ids",
            "target_sequence_equals_entity",
            "target_sequence_contained_in_entity",
            "entity_sequence_contained_in_target",
            "candidate_status",
        ],
    )
    output_tsv = tmp_path / "review.tsv"

    generate_reference_map_review(project_root=project_root, benchmark="casp16_server_protein_v1", candidate_tsv=candidate_tsv, output_tsv=output_tsv)

    rows = read_tsv(output_tsv)
    assert rows[0]["status"] == "candidate"
    assert rows[0]["scoring_mapping"] == "candidate_domain=T1201-D1; residue_ranges=34-370; verify_chain_and_crop"


def test_generate_rcsb_exact_sequence_probe_writes_full_construct_candidates(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    official_root = project_root / "data" / "official"
    write_tsv(
        OfficialPaths(official_root).sequences_tsv,
        [
            {
                "record_id": "T1228v1",
                "target_ids": "T1228V1",
                "sequence_family": "T",
                "sequence_kind": "dnaSequence",
                "length": "6",
                "sequence": "MELKQW",
                "header": "misclassified protein-like CASP sequence",
                "source_file": "fixture.seq.txt",
            }
        ],
        ["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"],
    )
    worklist = tmp_path / "missing.tsv"
    write_tsv(
        worklist,
        [
            {
                "priority": "1",
                "target_id": "T1228V1",
                "track": "protein_domain",
                "blocker_class": "prediction_waiting_on_reference",
                "sequence_lookup_id": "T1228V1",
            }
        ],
        ["priority", "target_id", "track", "blocker_class", "sequence_lookup_id"],
    )

    def fake_rcsb_json(url: str, *, payload=None):
        if payload is not None:
            assert payload["query"]["parameters"]["identity_cutoff"] == 1.0
            assert payload["query"]["parameters"]["value"] == "MELKQW"
            return {"result_set": [{"identifier": "9ABC_1"}]}
        if "/entry/" in url:
            return {
                "struct": {"title": "native candidate"},
                "rcsb_accession_info": {"initial_release_date": "2025-11-19T00:00:00.000+00:00"},
                "exptl": [{"method": "X-RAY DIFFRACTION"}],
            }
        if "/polymer_entity/" in url:
            return {
                "entity_poly": {"pdbx_seq_one_letter_code_can": "MELKQW"},
                "rcsb_polymer_entity": {"pdbx_description": "candidate protein"},
                "rcsb_polymer_entity_container_identifiers": {"asym_ids": ["A"], "auth_asym_ids": ["A"]},
            }
        raise AssertionError(url)

    monkeypatch.setattr(benchmark_module, "_rcsb_json_request", fake_rcsb_json)
    output_targets = tmp_path / "targets.tsv"
    output_candidates = tmp_path / "candidates.tsv"

    summary = generate_rcsb_exact_sequence_probe(
        project_root=project_root,
        official_root=official_root,
        worklist_tsv=worklist,
        output_targets_tsv=output_targets,
        output_candidates_tsv=output_candidates,
    )

    assert summary["rows"] == 1
    assert summary["targets_with_hits"] == 1
    assert summary["candidate_rows"] == 1
    assert summary["full_construct_exact_candidates"] == 1
    target_rows = read_tsv(output_targets)
    assert target_rows[0]["hit_count"] == "1"
    candidate_rows = read_tsv(output_candidates)
    assert candidate_rows[0]["sequence_kind"] == "dnaSequence"
    assert candidate_rows[0]["target_sequence_equals_entity"] == "true"
    assert candidate_rows[0]["candidate_status"] == "full_construct_exact_candidate_needs_native_provenance_and_mapping"


def test_generate_rcsb_exact_sequence_probe_skips_true_nucleic_acid(tmp_path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    official_root = project_root / "data" / "official"
    write_tsv(
        OfficialPaths(official_root).sequences_tsv,
        [
            {
                "record_id": "R1203",
                "target_ids": "R1203",
                "sequence_family": "R",
                "sequence_kind": "dnaSequence",
                "length": "8",
                "sequence": "ACGTACGT",
                "header": "true nucleic acid",
                "source_file": "fixture.seq.txt",
            }
        ],
        ["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"],
    )
    worklist = tmp_path / "missing.tsv"
    write_tsv(
        worklist,
        [{"priority": "1", "target_id": "R1203", "track": "protein_domain", "blocker_class": "prediction_waiting_on_reference", "sequence_lookup_id": "R1203"}],
        ["priority", "target_id", "track", "blocker_class", "sequence_lookup_id"],
    )
    monkeypatch.setattr(benchmark_module, "_rcsb_json_request", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("RCSB should not be called")))

    output_targets = tmp_path / "targets.tsv"
    output_candidates = tmp_path / "candidates.tsv"
    summary = generate_rcsb_exact_sequence_probe(
        project_root=project_root,
        official_root=official_root,
        worklist_tsv=worklist,
        output_targets_tsv=output_targets,
        output_candidates_tsv=output_candidates,
    )

    assert summary["targets_with_hits"] == 0
    assert summary["candidate_rows"] == 0
    target_rows = read_tsv(output_targets)
    assert target_rows[0]["hits"] == "no_protein_like_sequence"
    assert read_tsv(output_candidates) == []


def test_materialize_reference_map_candidates_uses_cached_files(tmp_path) -> None:
    reference_map = tmp_path / "review.tsv"
    output_dir = tmp_path / "mmcif"
    output_dir.mkdir()
    (output_dir / "9abc.cif").write_text("data_9abc\n", encoding="utf-8")
    write_tsv(
        reference_map,
        [
            {
                "target_id": "T1201",
                "pdb_ids": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "",
                "scoring_mapping": "",
                "notes": "candidate row",
                "source_path": "",
            },
            {
                "target_id": "T1202",
                "pdb_ids": "9def",
                "status": "rejected",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "partial",
                "chain_mapping": "",
                "scoring_mapping": "",
                "notes": "rejected row",
                "source_path": "",
            },
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes", "source_path"],
    )
    manifest = tmp_path / "manifest.tsv"

    summary = materialize_reference_map_candidates(reference_map_tsv=reference_map, output_dir=output_dir, manifest_tsv=manifest)

    assert summary["rows"] == 1
    assert summary["cached"] == 1
    rows = read_tsv(manifest)
    assert rows[0]["target_id"] == "T1201"
    assert rows[0]["pdb_id"] == "9abc"
    assert rows[0]["download_status"] == "cached"
    assert rows[0]["sha256"]
    assert rows[0]["bytes"] == str(len("data_9abc\n"))


def test_audit_reference_candidate_chains_reports_domain_coverage(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)
    review = tmp_path / "review.tsv"
    write_tsv(
        review,
        [
            {
                "target_id": "T1201",
                "pdb_ids": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "candidate_entity=1",
                "scoring_mapping": "candidate_domain=T1201-D1; residue_ranges=1-3; verify_chain_and_crop",
                "notes": "candidate row",
                "source_path": "",
            }
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes", "source_path"],
    )
    mmcif_dir = tmp_path / "mmcif"
    mmcif_dir.mkdir()
    mmcif = mmcif_dir / "9abc.cif"
    mmcif.write_text(
        """data_9abc
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.auth_asym_id
ATOM 1 A 1 1 X
ATOM 2 A 1 2 X
ATOM 3 A 1 3 X
ATOM 4 B 1 1 Y
ATOM 5 B 1 3 Y
#
""",
        encoding="utf-8",
    )
    structures = tmp_path / "structures.tsv"
    write_tsv(
        structures,
        [
            {
                "target_id": "T1201",
                "pdb_id": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "reference_path": str(mmcif),
                "download_status": "cached",
                "sha256": "0123456789abcdef",
                "bytes": str(mmcif.stat().st_size),
                "notes": "candidate row",
            }
        ],
        ["target_id", "pdb_id", "status", "source", "reference_path", "download_status", "sha256", "bytes", "notes"],
    )
    output = tmp_path / "chain_audit.tsv"

    summary = audit_reference_candidate_chains(
        project_root=project_root,
        benchmark="casp16_server_protein_v1",
        review_tsv=review,
        structures_tsv=structures,
        output_tsv=output,
    )

    rows = read_tsv(output)
    assert summary["rows"] == 2
    chain_a = next(row for row in rows if row["chain_id"] == "A")
    chain_b = next(row for row in rows if row["chain_id"] == "B")
    assert chain_a["domain_residue_ranges"] == "1-3"
    assert chain_a["observed_label_seq_ranges"] == "1-3"
    assert chain_a["domain_residue_coverage"] == "1.000000"
    assert chain_a["chain_supports_domain"] == "true"
    assert chain_b["domain_residue_coverage"] == "0.666667"
    assert chain_b["domain_missing_count"] == "1"


def test_audit_reference_candidate_oligo_assemblies_reports_assembly_support(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)
    review = tmp_path / "review.tsv"
    write_tsv(
        review,
        [
            {
                "target_id": "H1202",
                "pdb_ids": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "candidate_entity=2; asym_ids=B,D; auth_asym_ids=B,D; verify_native_chain_choice",
                "scoring_mapping": "protein_oligo_requires_biological_assembly_chain_stoichiometry_and_interface_mapping",
                "notes": "candidate row",
                "source_path": "",
            }
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes", "source_path"],
    )
    mmcif_dir = tmp_path / "mmcif"
    mmcif_dir.mkdir()
    mmcif = mmcif_dir / "9abc.cif"
    mmcif.write_text(
        """data_9abc
_pdbx_struct_assembly.id 1
_pdbx_struct_assembly.details author_defined_assembly
_pdbx_struct_assembly.oligomeric_details tetrameric
_pdbx_struct_assembly.oligomeric_count 4
#
_pdbx_struct_assembly_gen.assembly_id 1
_pdbx_struct_assembly_gen.oper_expression 1
_pdbx_struct_assembly_gen.asym_id_list A,B,C,D
#
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.auth_asym_id
ATOM 1 A 1 1 A
ATOM 2 B 2 1 B
ATOM 3 C 1 1 C
ATOM 4 D 2 1 D
#
""",
        encoding="utf-8",
    )
    structures = tmp_path / "structures.tsv"
    write_tsv(
        structures,
        [
            {
                "target_id": "H1202",
                "pdb_id": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "reference_path": str(mmcif),
                "download_status": "cached",
                "sha256": "0123456789abcdef",
                "bytes": str(mmcif.stat().st_size),
                "notes": "candidate row",
            }
        ],
        ["target_id", "pdb_id", "status", "source", "reference_path", "download_status", "sha256", "bytes", "notes"],
    )
    output = tmp_path / "oligo_audit.tsv"

    summary = audit_reference_candidate_oligo_assemblies(
        project_root=project_root,
        benchmark="casp16_server_protein_v1",
        review_tsv=review,
        structures_tsv=structures,
        output_tsv=output,
    )

    rows = read_tsv(output)
    assert summary["rows"] == 1
    assert summary["assemblies_containing_all_candidate_asym_ids"] == 1
    assert rows[0]["candidate_atom_chains"] == "B,D"
    assert rows[0]["assembly_contains_all_candidate_asym_ids"] == "true"
    assert rows[0]["assembly_entity_ids"] == "1,2"
    assert rows[0]["assembly_oligomeric_details"] == "tetrameric"


def test_generate_reference_map_audit_report(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)
    build_casp16_server_protein_benchmark(project_root=project_root, official_root=official_root)
    review = tmp_path / "review.tsv"
    write_tsv(
        review,
        [
            {
                "target_id": "T1201",
                "pdb_ids": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "full_construct_exact_sequence",
                "chain_mapping": "candidate_entity=1",
                "scoring_mapping": "candidate_domain=T1201-D1; residue_ranges=1-3; verify_chain_and_crop",
                "notes": "candidate row",
                "source_path": "",
            },
            {
                "target_id": "T1201",
                "pdb_ids": "9def",
                "status": "rejected",
                "source": "rcsb_exact_sequence_probe",
                "native_provenance": "",
                "construct_coverage": "local_sequence_hit_not_full_construct_do_not_promote",
                "chain_mapping": "",
                "scoring_mapping": "",
                "notes": "rejected row",
                "source_path": "",
            },
        ],
        ["target_id", "pdb_ids", "status", "source", "native_provenance", "construct_coverage", "chain_mapping", "scoring_mapping", "notes", "source_path"],
    )
    structures = tmp_path / "structures.tsv"
    write_tsv(
        structures,
        [
            {
                "target_id": "T1201",
                "pdb_id": "9abc",
                "status": "candidate",
                "source": "rcsb_exact_sequence_probe",
                "reference_path": "/tmp/9abc.cif",
                "download_status": "cached",
                "sha256": "0123456789abcdef",
                "bytes": "10",
                "notes": "candidate row",
            }
        ],
        ["target_id", "pdb_id", "status", "source", "reference_path", "download_status", "sha256", "bytes", "notes"],
    )
    output = tmp_path / "audit.md"

    summary = generate_reference_map_audit_report(project_root=project_root, benchmark="casp16_server_protein_v1", review_tsv=review, structures_tsv=structures, output_md=output)

    text = output.read_text(encoding="utf-8")
    assert summary["targets"] == 1
    assert "## T1201" in text
    assert "verify_native_provenance_then_chain_and_domain_crop_mapping" in text
    assert "`0123456789ab`" in text
    assert "rejected row" in text


def test_generate_reference_gap_report(tmp_path) -> None:
    project_root = tmp_path / "project"
    benchmark = "casp16_server_test_refmap"
    benchmark_dir = project_root / "benchmarks" / benchmark
    benchmark_dir.mkdir(parents=True)
    write_tsv(
        benchmark_dir / "targets.tsv",
        [
            {
                "target_id": "T1201",
                "track": "protein_domain",
                "reference_status": "available",
                "rank_eligible": "true",
                "input_status": "ok",
                "skip_reason": "",
                "total_len": "100",
                "domain_count": "1",
                "domain_ids": "T1201-D1",
                "oligo_state": "A1",
                "server_best_score": "0.900000",
            },
            {
                "target_id": "T1202",
                "track": "protein_domain",
                "reference_status": "no_reference_pdb",
                "rank_eligible": "true",
                "input_status": "ok",
                "skip_reason": "no_reference_pdb",
                "total_len": "120",
                "domain_count": "2",
                "domain_ids": "T1202-D1,T1202-D2",
                "oligo_state": "A1",
                "server_best_score": "0.950000",
            },
            {
                "target_id": "H1203",
                "track": "protein_oligo",
                "reference_status": "no_reference_pdb",
                "rank_eligible": "true",
                "input_status": "ok",
                "skip_reason": "no_reference_pdb",
                "total_len": "300",
                "domain_count": "0",
                "domain_ids": "",
                "oligo_state": "A1B1",
                "server_best_score": "0.700000",
            },
            {
                "target_id": "T1204",
                "track": "protein_domain",
                "reference_status": "no_reference_pdb",
                "rank_eligible": "true",
                "input_status": "ok",
                "skip_reason": "no_reference_pdb",
                "total_len": "204",
                "domain_count": "1",
                "domain_ids": "T1204-D1",
                "oligo_state": "A1",
                "server_best_score": "0.800000",
            },
        ],
        ["target_id", "track", "reference_status", "rank_eligible", "input_status", "skip_reason", "total_len", "domain_count", "domain_ids", "oligo_state", "server_best_score"],
    )
    write_tsv(
        benchmark_dir / "official_server_groups.tsv",
        [
            {"category": "prot_domains", "rank": "1", "group": "110s", "mean_fixed_score": "0.923321"},
            {"category": "prot_oligo", "rank": "1", "group": "456s", "mean_fixed_score": "0.582615"},
        ],
        ["category", "rank", "group", "mean_fixed_score"],
    )
    write_tsv(
        benchmark_dir / "reference_map.tsv",
        [{"target_id": "T1201", "pdb_ids": "9aaa", "status": "accepted"}],
        ["target_id", "pdb_ids", "status"],
    )
    review = tmp_path / "review.tsv"
    write_tsv(
        review,
        [
            {
                "target_id": "T1202",
                "pdb_ids": "9abc",
                "status": "candidate",
                "scoring_mapping": "multi_domain_target=T1202-D1,T1202-D2; requires_explicit_domain_crop_mapping",
            },
            {
                "target_id": "H1203",
                "pdb_ids": "9def",
                "status": "candidate",
                "scoring_mapping": "protein_oligo; requires_qsglob_interface_mapping",
            },
            {
                "target_id": "T1204",
                "pdb_ids": "10br",
                "status": "deferred",
                "scoring_mapping": "",
            },
        ],
        ["target_id", "pdb_ids", "status", "scoring_mapping"],
    )
    oligo_audit = tmp_path / "oligo.tsv"
    write_tsv(
        oligo_audit,
        [{"target_id": "H1203", "pdb_id": "9def", "assembly_matches_target_chain_count": "false"}],
        ["target_id", "pdb_id", "assembly_matches_target_chain_count"],
    )
    output_md = tmp_path / "report.md"
    output_tsv = tmp_path / "report.tsv"

    summary = generate_reference_gap_report(
        project_root=project_root,
        benchmark=benchmark,
        review_tsv=review,
        oligo_audit_tsv=oligo_audit,
        output_md=output_md,
        output_tsv=output_tsv,
    )

    rows = {row["target_id"]: row for row in read_tsv(output_tsv)}
    text = output_md.read_text(encoding="utf-8")
    assert summary["missing_references"] == 3
    assert summary["available_references"] == 1
    assert summary["targets_with_candidates"] == 3
    assert "1/3" in text
    assert "`110s`" in text
    assert rows["T1202"]["next_action"] == "verify_native_provenance_plus_explicit_domain_crop_mapping"
    assert rows["H1203"]["next_action"] == "resolve_biological_assembly_stoichiometry_before_accepting"
    assert rows["T1204"]["candidate_rows"] == "1"
    assert rows["T1204"]["candidate_statuses"] == "deferred"
    assert rows["T1204"]["next_action"] == "review_deferred_sequence_hits_or_continue_native_search"
