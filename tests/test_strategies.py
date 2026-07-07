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


def test_domain_sequence_recovery_oligo_nofail_alias_restores_only_domains(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "domain_sequence_recovery" / "inputs.json"
    manifest = tmp_path / "domain_sequence_recovery" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequences = tmp_path / "sequences.tsv"
    domain_sequence = "MELKNIVNSYNITNILGYLRRSRQDMEREKRTGEDTLTEQELMNKILTAIEIPYELKMEIGSGESIDGRP"
    oligo_sequence = "ACDEFGHIKLMNPQRSTVWY" * 4
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T1239V1",
                    "sequences": [{"dnaSequence": {"sequence": "NNNTNGTGTTNTAGGGCGAATGAGNTNATTGATAAGGAG", "count": 1, "id": ["A"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "H1239",
                    "sequences": [{"dnaSequence": {"sequence": "NNNTNGTGTTNTAGGGCGAATGAG", "count": 1, "id": ["A"]}}],
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
                "\t".join(["H1239", "protein_oligo", "A1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequences.write_text(
        "\n".join(
            [
                "\t".join(["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"]),
                "\t".join(["T1239v1", "T1239V1", "T", "dnaSequence", str(len(domain_sequence)), domain_sequence, "T1239v1 protein subunit", "seq"]),
                "\t".join(["H1239p", "H1239", "H", "dnaSequence", str(len(oligo_sequence)), oligo_sequence, "H1239 protein-looking oligo", "seq"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_domain_sequence_recovery_oligo_nofail_v1",
        targets_path=targets,
        official_sequences_path=sequences,
    )

    assert summary["strategy"] == "yang_domain_sequence_recovery_oligo_nofail_v1"
    assert summary["changed_targets"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    assert optimized["T1239V1"]["sequences"][0]["proteinChain"]["sequence"] == domain_sequence
    assert "dnaSequence" in optimized["H1239"]["sequences"][0]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["target_id"] for row in rows] == ["T1239V1"]


def test_protein_oligo_sequence_recovery_restores_alias_protein_inputs(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "oligo_sequence_recovery" / "inputs.json"
    manifest = tmp_path / "oligo_sequence_recovery" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequences = tmp_path / "sequences.tsv"
    protein_a = "MSFHASLLREEETPRPVAGINRTDQSLKNPLLGTEVSFCLKSSSLPHHVRALGQIKARNL"
    protein_b = "MATRPSSLVDSLEDEEDPQTLRRERPGSPRPRKVPRNALTQPVDQLLKDLRKNPSMISD"

    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H0220",
                    "sequences": [
                        {"rnaSequence": {"sequence": "AUAGCUGAUGCUAUGCUAUGCUAUGC", "count": 1, "id": ["A"]}},
                        {"rnaSequence": {"sequence": "AUGCUAUGCUAUGCUAUGC", "count": 1, "id": ["B"]}},
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
                "\t".join(["H0220", "protein_oligo", "UNK"]),
                "\t".join(["H2220", "protein_oligo", "A1B4"]),
                "\t".join(["T1220", "protein_domain", "A1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequences.write_text(
        "\n".join(
            [
                "\t".join(["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"]),
                "\t".join(["H1220_A", "H1220", "H", "rnaSequence", str(len(protein_a)), protein_a, "H1220 protein subunit 1", "seq"]),
                "\t".join(["H1220_B", "H1220", "H", "rnaSequence", str(len(protein_b)), protein_b, "H1220 protein subunit 2", "seq"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_protein_oligo_sequence_recovery_v1",
        targets_path=targets,
        official_sequences_path=sequences,
    )

    assert summary["changed_targets"] == 2
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    h0220 = optimized["H0220"]["sequences"]
    h2220 = optimized["H2220"]["sequences"]
    assert h0220[0]["proteinChain"]["sequence"] == protein_a
    assert h0220[1]["proteinChain"]["sequence"] == protein_b
    assert [entity["proteinChain"]["count"] for entity in h2220] == [1, 4]
    assert "T1220" not in optimized
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["target_id"] for row in rows] == ["H0220", "H2220"]
    assert rows[0]["source_target_id"] == "H1220"
    assert rows[1]["optimized_total_len"] == str(len(protein_a) + 4 * len(protein_b))
    assert rows[1]["rules"] == "protein_sequence_recovery"


def test_protein_oligo_sequence_stoich_token_safe_composes_recovery_and_counts(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "oligo_sequence_stoich" / "inputs.json"
    manifest = tmp_path / "oligo_sequence_stoich" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    sequences = tmp_path / "sequences.tsv"
    official_targets = tmp_path / "official_targets.tsv"
    protein_a = "MSFHASLLREEETPRPVAGINRTDQSLKNPLLGTEVSFCLKSSSLPHHVRALGQIKARNL"
    protein_b = "MATRPSSLVDSLEDEEDPQTLRRERPGSPRPRKVPRNALTQPVDQLLKDLRKNPSMISD"

    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H2220",
                    "sequences": [
                        {"rnaSequence": {"sequence": "AUAGCUGAUGCUAUGCUAUGCUAUGC", "count": 1, "id": ["A"]}},
                        {"rnaSequence": {"sequence": "AUGCUAUGCUAUGCUAUGC", "count": 1, "id": ["B"]}},
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
                "\t".join(["H2220", "protein_oligo", "UNK"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    sequences.write_text(
        "\n".join(
            [
                "\t".join(["record_id", "target_ids", "sequence_family", "sequence_kind", "length", "sequence", "header", "source_file"]),
                "\t".join(["H1220_A", "H1220", "H", "rnaSequence", str(len(protein_a)), protein_a, "H1220 protein subunit 1", "seq"]),
                "\t".join(["H1220_B", "H1220", "H", "rnaSequence", str(len(protein_b)), protein_b, "H1220 protein subunit 2", "seq"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    official_targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "Oligo.State"]),
                "\t".join(["H2220", "A1B4"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_protein_oligo_sequence_stoich_token_safe_v1",
        targets_path=targets,
        official_sequences_path=sequences,
        official_targets_path=official_targets,
    )

    assert summary["changed_targets"] == 1
    assert summary["sequence_recovery_changed_targets"] == 1
    assert summary["oligo_stoich_changed_targets"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    proteins = [entity["proteinChain"] for entity in optimized["H2220"]["sequences"]]
    assert [protein["sequence"] for protein in proteins] == [protein_a, protein_b]
    assert [protein["count"] for protein in proteins] == [1, 4]
    assert proteins[1]["id"] == ["B", "C", "D", "E"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    changed = [(row["phase"], row["target_id"], row["status"], row["rules"]) for row in rows if row["status"] == "changed"]
    assert changed == [
        ("protein_oligo_sequence_recovery", "H2220", "changed", "protein_sequence_recovery"),
        ("oligo_stoich_token_safe", "H2220", "changed", "recover_official_oligo_state,benchmark_state_was_unknown"),
    ]


def test_oligo_stoich_token_safe_inherits_phase_alias_state(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "oligo_phase_alias" / "inputs.json"
    manifest = tmp_path / "oligo_phase_alias" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    official_targets = tmp_path / "official_targets.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H0220",
                    "sequences": [
                        {"proteinChain": {"sequence": "A" * 100, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": "B" * 50, "count": 1, "id": ["B"]}},
                    ],
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
                "\t".join(["H0220", "protein_oligo", "UNK"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    official_targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "Oligo.State"]),
                "\t".join(["H0220", "UNK"]),
                "\t".join(["H1220", "A1B4"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_oligo_stoichiometry_token_safe_v1",
        targets_path=targets,
        official_targets_path=official_targets,
    )

    assert summary["changed_targets"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    proteins = [entity["proteinChain"] for entity in optimized["H0220"]["sequences"]]
    assert [protein["count"] for protein in proteins] == [1, 4]
    assert proteins[1]["id"] == ["B", "C", "D", "E"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    h0220 = next(row for row in rows if row["target_id"] == "H0220")
    assert h0220["status"] == "changed"
    assert h0220["official_oligo_state"] == "A1B4"
    assert h0220["rules"] == "recover_official_oligo_state,benchmark_state_was_unknown"


def test_scoreable_target_subset_keeps_only_jobs_with_available_reference_aliases(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "scoreable" / "inputs.json"
    manifest = tmp_path / "scoreable" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T0206",
                    "sequences": [{"proteinChain": {"sequence": "A" * 80, "count": 1, "id": ["A"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "T1295",
                    "sequences": [{"proteinChain": {"sequence": "C" * 400, "count": 1, "id": ["A"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "T1295O",
                    "sequences": [{"proteinChain": {"sequence": "D" * 400, "count": 8, "id": list("ABCDEFGH")}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "H0208",
                    "sequences": [{"proteinChain": {"sequence": "E" * 100, "count": 1, "id": ["A"]}}],
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
                "\t".join(["target_id", "official_target_id", "sequence_lookup_id", "track", "reference_status"]),
                "\t".join(["T0206O", "T0206O", "T0206", "protein_oligo", "available"]),
                "\t".join(["T1295", "T1295", "T1295", "protein_domain", "no_reference_pdb"]),
                "\t".join(["T1295O", "T1295O", "T1295", "protein_oligo", "no_reference_pdb"]),
                "\t".join(["H0208", "H0208", "H0208", "protein_domain", "no_reference_pdb"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="scoreable_target_subset_v1",
        targets_path=targets,
    )

    assert summary["original_jobs"] == 4
    assert summary["kept_jobs"] == 1
    assert summary["skipped_jobs"] == 3
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert [job["name"] for job in optimized] == ["T0206"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = {row["job_name"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert rows["T0206"]["status"] == "kept"
    assert rows["T0206"]["kept_for_targets"] == "T0206O"
    assert rows["T1295"]["status"] == "skipped"
    assert rows["T1295O"]["status"] == "skipped"
    assert rows["T1295O"]["rules"] == "no_available_reference_for_job_aliases"


def test_scoreable_target_subset_oligo_first_prioritizes_exact_oligo_jobs(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "scoreable_oligo_first" / "inputs.json"
    manifest = tmp_path / "scoreable_oligo_first" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "T0206",
                    "sequences": [{"proteinChain": {"sequence": "A" * 80, "count": 1, "id": ["A"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "H0220",
                    "sequences": [{"proteinChain": {"sequence": "B" * 100, "count": 1, "id": ["A"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "T0206O",
                    "sequences": [{"proteinChain": {"sequence": "C" * 100, "count": 2, "id": ["A", "B"]}}],
                    "covalent_bonds": [],
                },
                {
                    "name": "T0234O",
                    "sequences": [{"proteinChain": {"sequence": "D" * 100, "count": 2, "id": ["A", "B"]}}],
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
                "\t".join(["target_id", "official_target_id", "sequence_lookup_id", "track", "reference_status"]),
                "\t".join(["T0206", "T0206", "T0206", "protein_domain", "available"]),
                "\t".join(["H0220", "H0220", "H0220", "protein_oligo", "available"]),
                "\t".join(["T0206O", "T0206O", "T0206", "protein_oligo", "available"]),
                "\t".join(["T0234O", "T0234O", "T0234", "protein_oligo", "available"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="scoreable_target_subset_oligo_first_v1",
        targets_path=targets,
    )

    assert summary["kept_jobs"] == 4
    assert summary["prioritized_jobs"] == 3
    optimized = json.loads(output_json.read_text(encoding="utf-8"))
    assert [job["name"] for job in optimized] == ["H0220", "T0206O", "T0234O", "T0206"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = {row["job_name"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert rows["T0206O"]["rules"] == "has_available_reference,priority:exact_oligo_target_first"
    assert rows["H0220"]["rules"] == "has_available_reference,priority:exact_oligo_target_first"
    assert rows["T0206"]["rules"] == "has_available_reference,priority:original_order_after_exact_oligo_targets"


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


def test_oligo_stoichiometry_recovery_restores_official_counts(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "stoich" / "inputs.json"
    manifest = tmp_path / "stoich" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    official_targets = tmp_path / "official_targets.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1258",
                    "sequences": [
                        {"proteinChain": {"sequence": "A" * 2000, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": "C" * 300, "count": 1, "id": ["B"]}},
                    ],
                    "covalent_bonds": [],
                },
                {
                    "name": "T1201",
                    "sequences": [{"proteinChain": {"sequence": "D" * 50, "count": 1, "id": ["A"]}}],
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
                "\t".join(["H1258", "protein_oligo", "UNK"]),
                "\t".join(["T1201", "protein_domain", "A1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    official_targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "Oligo.State"]),
                "\t".join(["H1258", "A1B2"]),
                "\t".join(["T1201", "A1"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_oligo_stoichiometry_recovery_v1",
        targets_path=targets,
        official_targets_path=official_targets,
    )

    assert summary["changed_targets"] == 1
    assert summary["oversize_after_recovery"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    h1258_entities = optimized["H1258"]["sequences"]
    assert h1258_entities[0]["proteinChain"]["count"] == 1
    assert h1258_entities[0]["proteinChain"]["id"] == ["A"]
    assert h1258_entities[1]["proteinChain"]["count"] == 2
    assert h1258_entities[1]["proteinChain"]["id"] == ["B", "C"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    h1258 = next(row for row in rows if row["target_id"] == "H1258")
    assert h1258["status"] == "changed"
    assert h1258["official_oligo_state"] == "A1B2"
    assert h1258["optimized_counts"] == "1,2"
    assert h1258["optimized_total_len"] == "2600"
    assert h1258["rules"] == "recover_official_oligo_state,benchmark_state_was_unknown,oversize_after_recovery:2560"
    t1201 = next(row for row in rows if row["target_id"] == "T1201")
    assert t1201["status"] == "unchanged"
    assert t1201["skip_reason"] == "not_protein_oligo"


def test_oligo_stoichiometry_token_safe_skips_oversize_recovery(tmp_path) -> None:
    input_json = tmp_path / "inputs.json"
    output_json = tmp_path / "stoich_safe" / "inputs.json"
    manifest = tmp_path / "stoich_safe" / "manifest.tsv"
    targets = tmp_path / "targets.tsv"
    official_targets = tmp_path / "official_targets.tsv"
    input_json.write_text(
        json.dumps(
            [
                {
                    "name": "H1258",
                    "sequences": [
                        {"proteinChain": {"sequence": "A" * 2000, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": "C" * 300, "count": 1, "id": ["B"]}},
                    ],
                },
                {
                    "name": "H1232",
                    "sequences": [
                        {"proteinChain": {"sequence": "D" * 100, "count": 1, "id": ["A"]}},
                        {"proteinChain": {"sequence": "E" * 200, "count": 1, "id": ["B"]}},
                    ],
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
                "\t".join(["H1258", "protein_oligo", "UNK"]),
                "\t".join(["H1232", "protein_oligo", "UNK"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    official_targets.write_text(
        "\n".join(
            [
                "\t".join(["target_id", "Oligo.State"]),
                "\t".join(["H1258", "A1B2"]),
                "\t".join(["H1232", "A2B2"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = derive_strategy_inputs(
        input_json=input_json,
        output_json=output_json,
        manifest_path=manifest,
        strategy="yang_oligo_stoichiometry_token_safe_v1",
        targets_path=targets,
        official_targets_path=official_targets,
    )

    assert summary["changed_targets"] == 1
    assert summary["oversize_after_recovery"] == 0
    assert summary["skipped_oversize_after_recovery"] == 1
    optimized = {job["name"]: job for job in json.loads(output_json.read_text(encoding="utf-8"))}
    assert optimized["H1258"]["sequences"][1]["proteinChain"]["count"] == 1
    assert optimized["H1258"]["sequences"][1]["proteinChain"]["id"] == ["B"]
    assert optimized["H1232"]["sequences"][0]["proteinChain"]["count"] == 2
    assert optimized["H1232"]["sequences"][0]["proteinChain"]["id"] == ["A", "B"]
    assert optimized["H1232"]["sequences"][1]["proteinChain"]["count"] == 2
    assert optimized["H1232"]["sequences"][1]["proteinChain"]["id"] == ["C", "D"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    h1258 = next(row for row in rows if row["target_id"] == "H1258")
    assert h1258["status"] == "unchanged"
    assert h1258["skip_reason"] == "oversize_after_recovery"
    assert h1258["rules"] == "would_recover_official_oligo_state,benchmark_state_was_unknown,skip_oversize_after_recovery:2560"
