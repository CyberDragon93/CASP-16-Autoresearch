from __future__ import annotations

import json

from casp16_leaderboard.benchmark import build_casp16_protein_benchmark
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
        ],
        ["target_id", "target_prefix", "Target", "Type", "Res", "Oligo.State", "Entry Date", "Server Exp.", "Human Exp.", "QA Exp.", "Cancellation Date", "Description"],
    )
    write_tsv(
        paths.sequences_tsv,
        [
            {"record_id": "T1201", "target_ids": "T1201", "sequence_family": "T", "sequence_kind": "proteinChain", "length": "3", "sequence": "ACD", "header": "", "source_file": ""},
            {"record_id": "H1202A", "target_ids": "H1202", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "ACD", "header": "", "source_file": ""},
            {"record_id": "H1202B", "target_ids": "H1202", "sequence_family": "H", "sequence_kind": "proteinChain", "length": "3", "sequence": "EFG", "header": "", "source_file": ""},
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


def test_build_benchmark_protein_first(tmp_path) -> None:
    official_root = tmp_path / "official"
    project_root = tmp_path / "project"
    write_fixture_official(official_root)

    summary = build_casp16_protein_benchmark(project_root=project_root, official_root=official_root)
    assert summary["input_jobs"] == 2
    assert summary["rank_eligible"] == 2

    benchmark_dir = project_root / "benchmarks" / "casp16_protein_v1"
    targets = {row["target_id"]: row for row in read_tsv(benchmark_dir / "targets.tsv")}
    assert targets["T1201"]["rank_eligible"] == "true"
    assert targets["H1202"]["rank_eligible"] == "true"
    assert targets["R1203"]["skip_reason"] == "unsupported_category"

    inputs = json.loads((benchmark_dir / "inputs.json").read_text(encoding="utf-8"))
    h_job = next(job for job in inputs if job["name"] == "H1202")
    assert h_job["sequences"][0]["proteinChain"]["count"] == 2
    assert h_job["sequences"][1]["proteinChain"]["id"] == ["C", "D"]
