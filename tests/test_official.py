from __future__ import annotations

from casp16_leaderboard.official import (
    align_score_values,
    base_target_id,
    parse_domain_summary_text,
    parse_fasta_text,
    parse_score_table_text,
    parse_target_reference_text,
    parse_targets_text,
)


def test_parse_targets_text_counts_prefixes() -> None:
    text = """Target;Type;Res;Oligo.State;Entry Date; Server Exp.;Human Exp.;QA Exp.;Cancellation Date;Description
T1201;All groups;210;A2;2024-05-01;2024-05-04;2024-05-15;2024-05-18;-;Q9GZX9
H1202;All groups;190;A2B2;2024-05-02;2024-05-05;2024-05-16;2024-05-19;-;complex
"""
    rows = parse_targets_text(text)
    assert [row["target_id"] for row in rows] == ["T1201", "H1202"]
    assert [row["target_prefix"] for row in rows] == ["T", "H"]


def test_parse_fasta_text_links_hybrid_subunits_to_m_target() -> None:
    text = """>T1212s1, M1212 subunit 1, prot 466 residues
ACDEFGHIK
>R1212, M1212 subunit 2, RNA 247 residues
ACGUACGU
>D1212s3, M1212 subunit 3, DNA 48 residues
ACGTACGT
"""
    rows = parse_fasta_text(text, "fixture.seq.txt")
    by_id = {row["record_id"]: row for row in rows}
    assert by_id["T1212s1"]["sequence_kind"] == "proteinChain"
    assert by_id["R1212"]["sequence_kind"] == "rnaSequence"
    assert by_id["D1212s3"]["sequence_kind"] == "dnaSequence"
    assert "M1212" in by_id["T1212s1"]["target_ids"].split(",")
    assert "M1212" in by_id["R1212"]["target_ids"].split(",")
    assert "M1212" in by_id["D1212s3"]["target_ids"].split(",")


def test_parse_score_table_protein_domain() -> None:
    text = """#    Model               GR#     GDT_TS   NP_P    RANK  LDDT    TMscore
1    T0206TS304_4-D1     304s    99.67    100.00  1     0.942   0.993
2    T0206TS241_5-D1     241     98.00    100.00  2     0.900   0.980
"""
    rows = parse_score_table_text(text, "prot_domains", "prot.csv")
    assert rows[0]["target_id"] == "T0206"
    assert rows[0]["group"] == "304s"
    assert rows[0]["primary_metric"] == "GDT_TS"
    assert rows[0]["primary_score"] == "99.670000"


def test_parse_score_table_sectioned_oligo() -> None:
    text = """
Target: H0208

#   Model              Gr.Code  QSglob   QSbest   lDDT       DockQ_Avg  TMscore
1   H0208TS051_3       051      0.416    0.942    0.909      0.890      0.981
"""
    rows = parse_score_table_text(text, "prot_oligo", "oligo.csv")
    assert rows[0]["target_id"] == "H0208"
    assert rows[0]["group"] == "051"
    assert rows[0]["primary_metric"] == "QSglob"
    assert rows[0]["primary_score"] == "0.416000"


def test_parse_score_table_without_rank_column() -> None:
    text = """#Model         Gr.Code  ICS(F1)   QSglob   lDDT       GDT_TS     TMscore
M0276TS369_1   369      0.847     0.786    0.863      0.915      0.965
"""
    rows = parse_score_table_text(text, "hybrid", "hybrid.csv")
    assert rows[0]["target_id"] == "M0276"
    assert rows[0]["group"] == "369"
    assert rows[0]["submitted_model_rank"] == ""
    assert rows[0]["primary_metric"] == "QSglob"
    assert rows[0]["primary_score"] == "0.786000"


def test_missing_score_does_not_fall_back_to_model_digits() -> None:
    text = """Target: H0227
#   Model              Gr.Code  QSglob   QSbest   lDDT       DockQ_Avg  TMscore
260 H0227TS450_4       450s     -        -        -          -          -
"""
    rows = parse_score_table_text(text, "prot_oligo", "oligo.csv")
    assert rows[0]["primary_metric"] == ""
    assert rows[0]["primary_score"] == ""


def test_base_target_keeps_variants_and_strips_subunits() -> None:
    assert base_target_id("T1208s1") == "T1208"
    assert base_target_id("M1228v1") == "M1228V1"


def test_parse_domain_summary_text() -> None:
    html = """
<table id="table_results">
<tr><th>#</th><th>Target</th><th>Residues</th><th>Domains</th><th>Residues in domain</th><th>Class</th><th>PDB</th></tr>
<tr><td>1.</td><td>T1201</td><td>210</td><td>T1201-D1: 3-203</td><td>201</td><td>easy</td><td><a href="https://www.rcsb.org/structure/8bwd">8bwd</a></td></tr>
</table>
"""
    rows = parse_domain_summary_text(html)
    assert rows == [
        {
            "target_id": "T1201",
            "target_len": "210",
            "domain_id": "T1201-D1",
            "residue_ranges": "3-203",
            "domain_len": "201",
            "difficulty": "easy",
            "pdb_ids": "8bwd",
            "source": "domains_summary.cgi",
        }
    ]


def test_align_score_values_keeps_variable_tail_together() -> None:
    metrics = align_score_values(["Model", "GR#", "GDT_TS", "Notes"], ["T1TS001_1", "001", "99.1", "a", "b"])
    assert metrics["GDT_TS"] == "99.1"
    assert metrics["Notes"] == "a b"


def test_parse_target_reference_text() -> None:
    html = '<tr><td><a href="target.cgi?id=1">H1202</a></td><td>2024-05-16 to 2024-05-19<br>complex<br>PDB code <a href="https://www.rcsb.org/structure/8bwl">8bwl</a></td></tr>'
    assert parse_target_reference_text(html) == [{"target_id": "H1202", "pdb_ids": "8bwl", "source": "targetlist.cgi"}]
