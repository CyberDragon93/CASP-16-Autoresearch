from __future__ import annotations

import csv
import json

from casp16_leaderboard.strategies import clean_terminal_expression_tags, derive_strategy_inputs


def test_clean_terminal_expression_tags_removes_obvious_tags() -> None:
    cleaned = clean_terminal_expression_tags("MGSSHHHHHHSSGLVPRGSH" + "ACDEFGHIKLMNPQRSTVWY" * 2 + "HHHHHH")
    assert cleaned.sequence == "ACDEFGHIKLMNPQRSTVWY" * 2
    assert cleaned.removed_n == 20
    assert cleaned.removed_c == 6
    assert cleaned.rules == ("trim_n:MGSSHHHHHHSSGLVPRGSH", "trim_c:HHHHHH")


def test_clean_terminal_expression_tags_keeps_short_peptides() -> None:
    cleaned = clean_terminal_expression_tags("MHHHHHHACDEFG")
    assert cleaned.sequence == "MHHHHHHACDEFG"
    assert cleaned.rules == ()


def test_derive_strategy_inputs_preserves_counts_and_writes_manifest(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "strategy" / "inputs.json"
    manifest = tmp_path / "strategy" / "manifest.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": "MGSSHHHHHHSSGLVPRGSH" + "ACDEFGHIKLMNPQRSTVWY" * 2,
                                "count": 2,
                                "id": ["A", "B"],
                            }
                        },
                        {"dnaSequence": {"sequence": "ACT", "count": 1, "id": ["C"]}},
                    ],
                    "covalent_bonds": [],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(input_json=input_json, output_json=output_json, manifest_path=manifest)

    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    protein = optimized[0]["sequences"][0]["proteinChain"]
    assert protein["sequence"] == "ACDEFGHIKLMNPQRSTVWY" * 2
    assert protein["count"] == 2
    assert protein["id"] == ["A", "B"]
    assert optimized[0]["sequences"][1]["dnaSequence"]["sequence"] == "ACT"
    assert summary["changed_sequences"] == 1
    assert summary["changed_targets"] == 1

    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["target_id"] == "T1"
    assert rows[0]["chain_ids"] == "A,B"
    assert rows[0]["changed"] == "true"
    assert rows[0]["rules"] == "trim_n:MGSSHHHHHHSSGLVPRGSH"
