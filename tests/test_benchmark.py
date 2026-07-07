from __future__ import annotations

import csv
import json

from casp16_leaderboard.benchmark import SERVER_ALIASFIX_BENCHMARK_NAME, SERVER_ALIASFIX_BENCHMARK_VERSION, build_casp16_protein_benchmark, build_casp16_server_protein_benchmark
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
