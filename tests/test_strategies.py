from __future__ import annotations

import csv
import json

from casp16_leaderboard.strategies import (
    clean_antibody_fv_chain,
    clean_antibody_fv_constant_regions,
    clean_epitope_expression_tags,
    clean_hydrophobic_leader_regions,
    clean_low_complexity_terminal_regions,
    clean_terminal_expression_tags,
    clean_terminal_tags_then_antibody_fv_regions,
    derive_strategy_inputs,
    parse_residue_ranges,
)


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


def test_clean_epitope_expression_tags_removes_flag_and_tev_his_prefixes() -> None:
    flag_cleaned = clean_epitope_expression_tags("MGSDYKDHDGDYKDHDIDYKDDDDKLG" + "ACDEFGHIKLMNPQRSTVWY" * 3)
    assert flag_cleaned.sequence == "ACDEFGHIKLMNPQRSTVWY" * 3
    assert flag_cleaned.rules == ("trim_n:MGSDYKDHDGDYKDHDIDYKDDDDKLG",)

    tev_cleaned = clean_epitope_expression_tags("MGSHHHHHHSGENLYFQG" + "ACDEFGHIKLMNPQRSTVWY" * 3)
    assert tev_cleaned.sequence == "ACDEFGHIKLMNPQRSTVWY" * 3
    assert tev_cleaned.rules == ("trim_n:MGSHHHHHHSGENLYFQG",)


def test_clean_low_complexity_terminal_regions_trims_obvious_terminal_segments() -> None:
    n_tail = "MAAPVVAPPGVVVSRANKRSGAGPGGSGGGGARGAEEEPP"
    core = "ACDEFGHIKLMNPQRSTVWY" * 6
    c_tail = "EDPNAPPYQPPPPFTAPMEGKGSRPKNMTPYRSPPPYVPP"
    cleaned = clean_low_complexity_terminal_regions(n_tail + core + c_tail)
    assert cleaned.sequence == core
    assert cleaned.removed_n == 40
    assert cleaned.removed_c == 40
    assert cleaned.rules == ("trim_n_low_complexity:40", "trim_c_low_complexity:40")


def test_clean_hydrophobic_leader_regions_trims_signal_like_prefix() -> None:
    leader = "MKNFLLRSRTLGVFVFLFFGALPVAVASP"
    core = "LSLTYQGRILTSDGVPLEHNNVKFLFEIANPTGTCVIYRELVEGINMANSLGVFDVPIGL" + "ACDEFGHIKLMNPQRSTVWY"
    cleaned = clean_hydrophobic_leader_regions(leader + core)
    assert cleaned.sequence == core
    assert cleaned.removed_n == 29
    assert cleaned.rules == ("trim_n_hydrophobic_leader:29",)


def test_clean_hydrophobic_leader_regions_keeps_poly_alanine_prefix() -> None:
    prefix = "MAAAAAAAAEQQSSNGPVKKSMREKAVERRNVNKEHNSNFKAGYIPI"
    core = "ACDEFGHIKLMNPQRSTVWY" * 5
    cleaned = clean_hydrophobic_leader_regions(prefix + core)
    assert cleaned.sequence == prefix + core
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
                        {"proteinChain": {"sequence": "ACDEFGHIKLMNPQRSTVWY" * 2, "count": 1, "id": ["D"]}},
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
    assert optimized[0]["sequences"][1]["proteinChain"]["sequence"] == "ACDEFGHIKLMNPQRSTVWY" * 2
    assert optimized[0]["sequences"][2]["dnaSequence"]["sequence"] == "ACT"
    assert summary["changed_sequences"] == 1
    assert summary["changed_targets"] == 1

    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["target_id"] == "T1"
    assert rows[0]["chain_ids"] == "A,B"
    assert rows[0]["changed"] == "true"
    assert rows[0]["rules"] == "trim_n:MGSSHHHHHHSSGLVPRGSH"
    assert rows[1]["chain_ids"] == "D"
    assert rows[1]["changed"] == "false"
    assert rows[1]["rules"] == "none"


def test_derive_oversize_domain_monomer_fallback_caps_domain_copy_count(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "oversize_domain" / "inputs.json"
    manifest = tmp_path / "oversize_domain" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequence = "ACDEFGHIKLMNPQRSTVWY" * 24
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1295",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": sequence,
                                "count": 8,
                                "id": ["A", "B", "C", "D", "E", "F", "G", "H"],
                            }
                        }
                    ],
                },
                {
                    "name": "T1295O",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": sequence,
                                "count": 8,
                                "id": ["A", "B", "C", "D", "E", "F", "G", "H"],
                            }
                        }
                    ],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text(
        "\t".join(["target_id", "track"]) + "\n" + "\t".join(["T1295", "protein_domain"]) + "\n" + "\t".join(["T1295O", "protein_oligo"]) + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_oversize_domain_monomer_fallback_v1",
        targets_path=targets,
    )

    assert summary["changed_targets"] == 1
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert optimized[0]["sequences"][0]["proteinChain"]["count"] == 1
    assert optimized[0]["sequences"][0]["proteinChain"]["id"] == ["A"]
    assert optimized[1]["sequences"][0]["proteinChain"]["count"] == 8
    assert optimized[1]["sequences"][0]["proteinChain"]["id"] == ["A", "B", "C", "D", "E", "F", "G", "H"]

    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "changed"
    assert rows[0]["rules"] == "domain_oversize_count_to_one:count=8"
    assert rows[0]["original_total_len"] == str(len(sequence) * 8)
    assert rows[0]["optimized_total_len"] == str(len(sequence))
    assert rows[1]["status"] == "unchanged"
    assert rows[1]["skip_reason"] == "not_protein_domain"


def test_derive_oversize_domain_monomer_fallback_skips_multi_entity_domains(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "oversize_domain" / "inputs.json"
    manifest = tmp_path / "oversize_domain" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    long_a = "ACDEFGHIKLMNPQRSTVWY" * 70
    long_b = "ACDEFGHIKLMNPQRSTVWY" * 70
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H0217",
                    "sequences": [
                        {"proteinChain": {"sequence": long_a, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": long_b, "count": 1, "id": ["B"]}},
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text("\t".join(["target_id", "track"]) + "\n" + "\t".join(["H0217", "protein_domain"]) + "\n", encoding="utf-8")

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_oversize_domain_monomer_fallback_v1",
        targets_path=targets,
    )

    assert summary["changed_targets"] == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))[0]["sequences"][1]["proteinChain"]["id"] == ["B"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "unchanged"
    assert rows[0]["skip_reason"] == "requires_single_protein_entity"


def test_large_target_fallback_cleans_then_keeps_main_chain(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "large_fallback" / "inputs.json"
    manifest = tmp_path / "large_fallback" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    tagged_main = "MGSDYKDHDGDYKDHDIDYKDDDDKLG" + ("A" * 2535)
    partner = "MGSHHHHHHSGENLYFQG" + ("C" * 247)
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1258",
                    "sequences": [
                        {"proteinChain": {"sequence": tagged_main, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": partner, "count": 1, "id": ["B"]}},
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text("\t".join(["target_id", "track"]) + "\n" + "\t".join(["H1258", "protein_oligo"]) + "\n", encoding="utf-8")

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_large_target_split_or_fallback_v1",
        targets_path=targets,
    )

    assert summary["changed_targets"] == 1
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert len(optimized[0]["sequences"]) == 1
    assert optimized[0]["sequences"][0]["proteinChain"]["id"] == ["A"]
    assert optimized[0]["sequences"][0]["proteinChain"]["sequence"] == "A" * 2535
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "changed"
    assert rows[0]["optimized_total_len"] == "2535"
    assert rows[0]["optimized_chain_ids"] == "A"
    assert rows[0]["dropped_chain_ids"] == "B"
    assert rows[0]["rules"] == "oversize_epitope_cleanup,oversize_prefix_budget:2560,dropped_chains:1"


def test_large_target_fallback_uses_prefix_budget_for_multi_entity_complex(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "large_fallback" / "inputs.json"
    manifest = tmp_path / "large_fallback" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    lengths = [305, 351, 452, 523, 721, 587]
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H0217",
                    "sequences": [
                        {"proteinChain": {"sequence": chr(65 + index) * length, "count": 1, "id": [chr(65 + index)]}}
                        for index, length in enumerate(lengths)
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text("\t".join(["target_id", "track"]) + "\n" + "\t".join(["H0217", "protein_oligo"]) + "\n", encoding="utf-8")

    derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_large_target_split_or_fallback_v1",
        targets_path=targets,
    )

    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert [entity["proteinChain"]["id"][0] for entity in optimized[0]["sequences"]] == ["A", "B", "C", "D", "E"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["optimized_total_len"] == str(sum(lengths[:5]))
    assert rows[0]["dropped_chain_ids"] == "F"
    assert rows[0]["rules"] == "oversize_prefix_budget:2560,dropped_chains:1"


def test_large_target_fallback_caps_single_entity_copy_count(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "large_fallback" / "inputs.json"
    manifest = tmp_path / "large_fallback" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequence = "ACDEFGHIKLMNPQRSTVWY" * 24
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1295O",
                    "sequences": [
                        {
                            "proteinChain": {
                                "sequence": sequence,
                                "count": 8,
                                "id": ["A", "B", "C", "D", "E", "F", "G", "H"],
                            }
                        }
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text("\t".join(["target_id", "track"]) + "\n" + "\t".join(["T1295O", "protein_oligo"]) + "\n", encoding="utf-8")

    derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_large_target_split_or_fallback_v1",
        targets_path=targets,
    )

    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    protein = optimized[0]["sequences"][0]["proteinChain"]
    assert protein["count"] == 5
    assert protein["id"] == ["A", "B", "C", "D", "E"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["optimized_total_len"] == str(len(sequence) * 5)
    assert rows[0]["dropped_chain_ids"] == "F,G,H"


def test_derive_epitope_strategy_uses_extended_rules(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "epitope" / "inputs.json"
    manifest = tmp_path / "epitope" / "manifest.tsv"
    sequence = "MGSHHHHHHSGENLYFQG" + "ACDEFGHIKLMNPQRSTVWY" * 3
    input_json.write_text(
        json.dumps([{"name": "H1258", "sequences": [{"proteinChain": {"sequence": sequence, "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )

    terminal_output = tmp_path / "terminal" / "inputs.json"
    terminal_manifest = tmp_path / "terminal" / "manifest.tsv"
    terminal_summary = derive_strategy_inputs(input_json=input_json, output_json=terminal_output, manifest_path=terminal_manifest)
    epitope_summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_epitope_tag_cleanup_v1",
    )

    assert terminal_summary["changed_sequences"] == 0
    assert epitope_summary["changed_sequences"] == 1
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert optimized[0]["sequences"][0]["proteinChain"]["sequence"] == "ACDEFGHIKLMNPQRSTVWY" * 3


def test_derive_low_complexity_strategy_inherits_epitope_cleanup(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "low_complexity" / "inputs.json"
    manifest = tmp_path / "low_complexity" / "manifest.tsv"
    sequence = "MGSHHHHHHSGENLYFQG" + "ACDEFGHIKLMNPQRSTVWY" * 5
    input_json.write_text(
        json.dumps([{"name": "H1258", "sequences": [{"proteinChain": {"sequence": sequence, "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_low_complexity_terminal_cleanup_v1",
    )

    assert summary["changed_sequences"] == 1
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["rules"] == "trim_n:MGSHHHHHHSGENLYFQG"


def test_derive_hydrophobic_leader_strategy_uses_sequence_only_rule(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "hydrophobic_leader" / "inputs.json"
    manifest = tmp_path / "hydrophobic_leader" / "manifest.tsv"
    leader = "MKNFLLRSRTLGVFVFLFFGALPVAVASP"
    core = "LSLTYQGRILTSDGVPLEHNNVKFLFEIANPTGTCVIYRELVEGINMANSLGVFDVPIGL" + "ACDEFGHIKLMNPQRSTVWY"
    input_json.write_text(
        json.dumps([{"name": "T0240", "sequences": [{"proteinChain": {"sequence": leader + core, "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_hydrophobic_leader_cleanup_v1",
    )

    assert summary["changed_sequences"] == 1
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert optimized[0]["sequences"][0]["proteinChain"]["sequence"] == core
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["rules"] == "trim_n_hydrophobic_leader:29"


def test_parse_residue_ranges_handles_contiguous_and_split_ranges() -> None:
    assert parse_residue_ranges("3-20") == [(3, 20)]
    assert parse_residue_ranges("301-401,468-535") == [(301, 401), (468, 535)]
    assert parse_residue_ranges("bad") == []


def test_derive_domain_fragment_strategy_uses_target_domain_aliases(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "domain_fragments" / "inputs.json"
    manifest = tmp_path / "domain_fragments" / "manifest.tsv"
    domains = tmp_path / "domain_definitions.tsv"
    targets = tmp_path / "targets.tsv"
    input_json.write_text(
        json.dumps([{"name": "T0240", "sequences": [{"proteinChain": {"sequence": "ACDEFGHIKL", "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )
    domains.write_text(
        "\t".join(["target_id", "target_len", "domain_id", "residue_ranges", "domain_len", "difficulty", "pdb_ids", "source"])
        + "\n"
        + "\t".join(["T1240", "10", "T1240-D1", "2-5", "4", "easy", "", "fixture"])
        + "\n",
        encoding="utf-8",
    )
    targets.write_text(
        "\t".join(["target_id", "track", "domain_ids"])
        + "\n"
        + "\t".join(["T0240", "protein_domain", "T1240-D1"])
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_domain_fragment_inputs_v1",
        domain_definitions_path=domains,
        targets_path=targets,
    )

    assert summary["fragment_jobs"] == 1
    assert summary["source_targets"] == 1
    fragment_jobs = json.loads(output_json.read_text(encoding="utf-8"))
    assert fragment_jobs == [{"name": "T0240__T1240-D1", "sequences": [{"proteinChain": {"sequence": "CDEF", "count": 1, "id": ["A"]}}]}]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "ok"
    assert rows[0]["skip_reason"] == "none"


def test_derive_domain_fragment_strategy_skips_non_contiguous_ranges(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "domain_fragments" / "inputs.json"
    manifest = tmp_path / "domain_fragments" / "manifest.tsv"
    domains = tmp_path / "domain_definitions.tsv"
    input_json.write_text(
        json.dumps([{"name": "T1228V1", "sequences": [{"proteinChain": {"sequence": "ACDEFGHIKL", "count": 1, "id": ["A"]}}]}]) + "\n",
        encoding="utf-8",
    )
    domains.write_text(
        "\t".join(["target_id", "target_len", "domain_id", "residue_ranges", "domain_len", "difficulty", "pdb_ids", "source"])
        + "\n"
        + "\t".join(["T1228V1", "10", "T1228V1-D3", "2-4,7-8", "5", "hard", "", "fixture"])
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_domain_fragment_inputs_v1",
        domain_definitions_path=domains,
    )

    assert summary["fragment_jobs"] == 0
    assert summary["skipped_domains"] == 1
    assert json.loads(output_json.read_text(encoding="utf-8")) == []
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "skip"
    assert rows[0]["skip_reason"] == "non_contiguous_domain"


def test_clean_antibody_fv_chain_trims_heavy_and_light_constant_regions() -> None:
    heavy_variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    light_variable = "QSALTQPASVSGSPGQSITISCTGSSSDVGGYSHVSWYQQHPGKVPKLIISEVSNRPSGISNRFSGSKSANTASLTISGLQPEDEADYYCGSYASTNILHYVFGTGTKVTVL"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"

    heavy = clean_antibody_fv_chain(heavy_variable + constant)
    light = clean_antibody_fv_chain(light_variable + constant)

    assert heavy.sequence == heavy_variable
    assert heavy.removed_c == len(constant)
    assert heavy.rules == (f"trim_c_antibody_constant:{len(heavy_variable)}",)
    assert light.sequence == light_variable
    assert light.removed_c == len(constant)


def test_clean_antibody_fv_chain_keeps_short_antigen_like_chain() -> None:
    antigen = "SKPNNDFHFEVFNFVPCSICSNNPTCWAICKRIPNKKPGKK"
    cleaned = clean_antibody_fv_chain(antigen)
    assert cleaned.sequence == antigen
    assert cleaned.rules == ()


def test_clean_antibody_fv_constant_regions_returns_manifest_compatible_cleanup() -> None:
    variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
    cleaned = clean_antibody_fv_constant_regions(variable + constant)
    assert cleaned.sequence == variable
    assert cleaned.removed_n == 0
    assert cleaned.removed_c == len(constant)
    assert cleaned.rules == (f"trim_c_antibody_constant:{len(variable)}",)


def test_clean_terminal_tags_then_antibody_fv_regions_composes_rules() -> None:
    variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
    tagged = "MGSSHHHHHHSSGLVPRGSH" + variable + constant
    cleaned = clean_terminal_tags_then_antibody_fv_regions(tagged)
    assert cleaned.sequence == variable
    assert cleaned.removed_n == len("MGSSHHHHHHSSGLVPRGSH")
    assert cleaned.removed_c == len(constant)
    assert cleaned.rules == (
        "trim_n:MGSSHHHHHHSSGLVPRGSH",
        f"trim_c_antibody_constant:{len(variable)}",
    )


def test_derive_antibody_fv_strategy_generates_target_lab_complex(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "antibody_fv" / "inputs.json"
    manifest = tmp_path / "antibody_fv" / "manifest.tsv"
    antigen = "SKPNNDFHFEVFNFVPCSICSNNPTCWAICKRIPNKKPGKK"
    heavy_variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    light_variable = "QSALTQPASVSGSPGQSITISCTGSSSDVGGYSHVSWYQQHPGKVPKLIISEVSNRPSGISNRFSGSKSANTASLTISGLQPEDEADYYCGSYASTNILHYVFGTGTKVTVL"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1222",
                    "sequences": [
                        {"proteinChain": {"sequence": antigen, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": heavy_variable + constant, "count": 1, "id": ["B"]}},
                        {"proteinChain": {"sequence": light_variable + constant, "count": 1, "id": ["C"]}},
                    ],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_antibody_fv_fragment_inputs_v1",
    )

    assert summary["fv_jobs"] == 1
    assert summary["changed_chains"] == 2
    fv_jobs = json.loads(output_json.read_text(encoding="utf-8"))
    assert fv_jobs[0]["name"] == "H1222__fv"
    assert fv_jobs[0]["sequences"][0]["proteinChain"]["sequence"] == antigen
    assert fv_jobs[0]["sequences"][1]["proteinChain"]["sequence"] == heavy_variable
    assert fv_jobs[0]["sequences"][2]["proteinChain"]["sequence"] == light_variable
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["status"] == "unchanged"
    assert rows[1]["status"] == "trimmed"
    assert rows[2]["status"] == "trimmed"


def test_derive_antibody_fv_cleanup_preserves_full_set_and_job_names(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "antibody_fv_cleanup" / "inputs.json"
    manifest = tmp_path / "antibody_fv_cleanup" / "manifest.tsv"
    antigen = "SKPNNDFHFEVFNFVPCSICSNNPTCWAICKRIPNKKPGKK"
    heavy_variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
    ordinary = "ACDEFGHIKLMNPQRSTVWY" * 6
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1222",
                    "sequences": [
                        {"proteinChain": {"sequence": antigen, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": heavy_variable + constant, "count": 1, "id": ["B"]}},
                    ],
                },
                {"name": "T1201", "sequences": [{"proteinChain": {"sequence": ordinary, "count": 1, "id": ["A"]}}]},
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_antibody_fv_cleanup_v1",
    )

    assert summary["jobs"] == 2
    assert summary["protein_sequences"] == 3
    assert summary["changed_sequences"] == 1
    assert summary["changed_targets"] == 1
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert [job["name"] for job in optimized] == ["H1222", "T1201"]
    assert optimized[0]["sequences"][0]["proteinChain"]["sequence"] == antigen
    assert optimized[0]["sequences"][1]["proteinChain"]["sequence"] == heavy_variable
    assert optimized[1]["sequences"][0]["proteinChain"]["sequence"] == ordinary
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["changed"] for row in rows] == ["false", "true", "false"]
    assert rows[1]["rules"] == f"trim_c_antibody_constant:{len(heavy_variable)}"


def test_derive_terminal_tag_antibody_fv_cleanup_combines_full_set_changes(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "terminal_antibody_fv" / "inputs.json"
    manifest = tmp_path / "terminal_antibody_fv" / "manifest.tsv"
    antigen = "SKPNNDFHFEVFNFVPCSICSNNPTCWAICKRIPNKKPGKK"
    heavy_variable = "QVQLVQSGAEVKKPGSSVKVPCKASGGTFSTYPISWVRQAPGQGLEWMGRIIPDPPMANIAQKFQGRVSFSADKSTTIVYMELSSLRSEDTAVYFCAREILQSPPFAVDVWGQGTMVAVSS"
    constant = "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
    ordinary = "ACDEFGHIKLMNPQRSTVWY" * 4
    tagged_ordinary = ordinary + "HHHHHH"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1222",
                    "sequences": [
                        {"proteinChain": {"sequence": antigen, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": heavy_variable + constant, "count": 1, "id": ["B"]}},
                    ],
                },
                {"name": "T1201", "sequences": [{"proteinChain": {"sequence": tagged_ordinary, "count": 1, "id": ["A"]}}]},
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_terminal_tag_antibody_fv_cleanup_v1",
    )

    assert summary["jobs"] == 2
    assert summary["changed_sequences"] == 2
    assert summary["changed_targets"] == 2
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert [job["name"] for job in optimized] == ["H1222", "T1201"]
    assert optimized[0]["sequences"][0]["proteinChain"]["sequence"] == antigen
    assert optimized[0]["sequences"][1]["proteinChain"]["sequence"] == heavy_variable
    assert optimized[1]["sequences"][0]["proteinChain"]["sequence"] == ordinary
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["changed"] for row in rows] == ["false", "true", "true"]
    assert rows[1]["rules"] == f"trim_c_antibody_constant:{len(heavy_variable)}"
    assert rows[2]["rules"] == "trim_c:HHHHHH"


def test_sequence_recovery_restores_protein_domain_inputs(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "sequence_recovery" / "inputs.json"
    manifest = tmp_path / "sequence_recovery" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequences = tmp_path / "sequences.tsv"
    protein_1212 = "PKSIYVPNKDLKISKWIPTPKKEFTEIETNSWYEHRKFENPNKSPVQTYNKIVPVVPPESIKQQNLANKRKKTN"
    protein_1239 = "MELKNIVNSYNITNILGYLRRSRQDMEREKRTGEDTLTEQKELMNKILTAIEIPYELKMEIGSGESIDGRPVFKEC"
    protein_1280 = "KDFMLIGHRGATGYTDEHTIKGYQMALDKGADYIELDLQLTKDNKLLCMHDSTIDRTTTGTGKVGDMTLSYIQT"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1239V1",
                    "sequences": [
                        {"dnaSequence": {"sequence": "NNNTNGTGTTNTAGGGCGAATGAGNTNATTGATAAGGAGNTANNG", "count": 1, "id": ["A"]}}
                    ],
                    "covalent_bonds": [],
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "track", "oligo_state"]),
                "\t".join(["T1212", "protein_domain", "A1"]),
                "\t".join(["T1239V1", "protein_domain", "A1"]),
                "\t".join(["T1239V2", "protein_domain", "A1"]),
                "\t".join(["T2280", "protein_domain", "A1"]),
                "\t".join(["H1212", "protein_oligo", "A1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequences.write_text(
        "\n".join(
            [
                "\t".join(["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"]),
                "\t".join(["T1212", "T1212", "T", "rnaSequence", str(len(protein_1212)), protein_1212, "T1212 protein-looking mislabeled", "seq"]),
                "\t".join(["T1212s1", "M1212,T1212,T1212S1", "RDM", "proteinChain", str(len(protein_1212)), protein_1212, "T1212s1 prot subunit", "seq"]),
                "\t".join(["T1239v1", "T1239V1", "T", "dnaSequence", str(len(protein_1239)), protein_1239, "T1239v1 protein subunit", "seq"]),
                "\t".join(["T1280", "T1280", "T", "proteinChain", str(len(protein_1280)), protein_1280, "T1280 protein domain", "seq"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_sequence_recovery_v1",
        targets_path=targets,
        official_sequences_path=sequences,
    )

    assert summary["changed_targets"] == 4
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    assert optimized["T1212"]["sequences"][0]["proteinChain"]["sequence"] == protein_1212
    assert optimized["T1239V1"]["sequences"][0]["proteinChain"]["sequence"] == protein_1239
    assert optimized["T1239V2"]["sequences"][0]["proteinChain"]["sequence"] == protein_1239
    assert optimized["T2280"]["sequences"][0]["proteinChain"]["sequence"] == protein_1280
    assert "H1212" not in optimized
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["target_id"] for row in rows] == ["T1212", "T1239V1", "T1239V2", "T2280"]
    assert rows[2]["source_target_id"] == "T1239V1"
    assert rows[3]["source_target_id"] == "T1280"


def test_sequence_recovery_large_target_fallback_composes_recovery_and_token_budget(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "combo" / "inputs.json"
    manifest = tmp_path / "combo" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequences = tmp_path / "sequences.tsv"
    protein_1239 = "MELKNIVNSYNITNILGYLRRSRQDMEREKRTGEDTLTEQKELMNKILTAIEIPYELKMEIGSGESIDGRPVFKEC"
    tagged_main = "MGSDYKDHDGDYKDHDIDYKDDDDKLG" + ("A" * 2535)
    partner = "MGSHHHHHHSGENLYFQG" + ("C" * 247)
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1239V1",
                    "sequences": [
                        {"dnaSequence": {"sequence": "NNNTNGTGTTNTAGGGCGAATGAGNTNATTGATAAGGAGNTANNG", "count": 1, "id": ["A"]}}
                    ],
                    "covalent_bonds": [],
                },
                {
                    "name": "H1258",
                    "sequences": [
                        {"proteinChain": {"sequence": tagged_main, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": partner, "count": 1, "id": ["B"]}},
                    ],
                    "covalent_bonds": [],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "track", "oligo_state"]),
                "\t".join(["T1239V1", "protein_domain", "A1"]),
                "\t".join(["H1258", "protein_oligo", "A1B1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequences.write_text(
        "\n".join(
            [
                "\t".join(["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"]),
                "\t".join(["T1239v1", "T1239V1", "T", "dnaSequence", str(len(protein_1239)), protein_1239, "T1239v1 protein subunit", "seq"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_sequence_recovery_large_target_fallback_v1",
        targets_path=targets,
        official_sequences_path=sequences,
    )

    assert summary["changed_targets"] == 2
    assert summary["sequence_recovery_changed_targets"] == 1
    assert summary["large_target_fallback_changed_targets"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    assert optimized["T1239V1"]["sequences"][0]["proteinChain"]["sequence"] == protein_1239
    assert len(optimized["H1258"]["sequences"]) == 1
    assert optimized["H1258"]["sequences"][0]["proteinChain"]["id"] == ["A"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    rows_by_phase_target = {(row["phase"], row["target_id"]): row for row in rows}
    assert rows_by_phase_target[("sequence_recovery", "T1239V1")]["status"] == "changed"
    assert rows_by_phase_target[("large_target_fallback", "H1258")]["status"] == "changed"
    assert rows_by_phase_target[("large_target_fallback", "H1258")]["dropped_chain_ids"] == "B"
