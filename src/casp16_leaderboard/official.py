from __future__ import annotations

import csv
import json
import re
import statistics
import urllib.request
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence


TARGET_LIST_URL = "https://predictioncenter.org/casp16/targetlist.cgi?type=csv"
BASE_DOWNLOAD_URL = "https://predictioncenter.org/download_area/CASP16"

SEQUENCE_FILES = {
    "T": "casp16.T1.seq.txt",
    "H": "casp16.H1.seq.txt",
    "RDM": "casp16.RDM1.seq.txt",
}

SCORE_TABLES = {
    "prot_domains": "CASP16_prot_domains.scores.csv",
    "prot_oligo": "CASP16_prot_oligo.scores.csv",
    "rna_mono": "CASP16_rna_mono.scores.csv",
    "rna_oligo": "CASP16_rna_oligo.scores.csv",
    "hybrid": "CASP16_hybrid.scores.csv",
}

TARGET_TOKEN_RE = re.compile(r"\b([THRDML]\d{4}(?:s\d+|v\d+)?)\b", re.IGNORECASE)
MODEL_TARGET_RE = re.compile(r"\b([A-Z]\d{4}(?:v\d+)?)TS", re.IGNORECASE)
FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")

PRIMARY_METRIC_CANDIDATES = {
    "prot_domains": ("GDT_TS", "LDDT", "TMscore"),
    "prot_oligo": ("QSglob", "QSbest", "DockQ_Avg", "TMscore", "lDDT"),
    "rna_mono": ("GDT_TS", "lDDT", "LDDT", "TMscore", "RMSD"),
    "rna_oligo": ("QSglob", "QSbest", "lDDT", "DockQ_Avg", "TMscore"),
    "hybrid": ("QSglob", "QSbest", "DockQ_Avg", "lDDT", "TMscore"),
}


@dataclass(frozen=True)
class OfficialPaths:
    root: Path

    @property
    def targets_dir(self) -> Path:
        return self.root / "targets"

    @property
    def sequences_dir(self) -> Path:
        return self.root / "sequences"

    @property
    def tables_dir(self) -> Path:
        return self.root / "results" / "tables"

    @property
    def parsed_dir(self) -> Path:
        return self.root / "parsed"

    @property
    def target_csv(self) -> Path:
        return self.targets_dir / "casp16_targets.csv"

    @property
    def targets_tsv(self) -> Path:
        return self.parsed_dir / "targets.tsv"

    @property
    def sequences_tsv(self) -> Path:
        return self.parsed_dir / "sequences.tsv"

    @property
    def scores_tsv(self) -> Path:
        return self.parsed_dir / "official_scores.tsv"

    @property
    def summary_json(self) -> Path:
        return self.parsed_dir / "ingest_summary.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_text(url: str, path: Path, *, force: bool = False) -> str:
    ensure_dir(path.parent)
    if path.exists() and not force:
        return path.read_text(encoding="utf-8", errors="replace")
    request = urllib.request.Request(url, headers={"User-Agent": "casp16-leaderboard/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8", errors="replace")
    path.write_text(text, encoding="utf-8")
    return text


def write_tsv(path: Path, rows: Sequence[dict[str, object]], fieldnames: Sequence[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_targets_text(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(text), delimiter=";")
    rows: list[dict[str, str]] = []
    for row in reader:
        clean = {key.strip(): (value or "").strip() for key, value in row.items() if key is not None}
        target_id = clean.get("Target", "")
        if not target_id:
            continue
        clean["target_id"] = target_id
        clean["target_prefix"] = target_id[0]
        rows.append(clean)
    return rows


def parse_fasta_text(text: str, source_file: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if header is None:
            return
        sequence = "".join(parts).replace(" ", "").strip().upper()
        if not sequence:
            return
        record_id = _record_id_from_header(header)
        target_ids = sorted(_target_ids_for_sequence_record(record_id, header))
        rows.append(
            {
                "record_id": record_id,
                "target_ids": ",".join(target_ids),
                "sequence_kind": classify_sequence(record_id, header, sequence),
                "sequence": sequence,
                "length": str(len(sequence)),
                "header": header,
                "source_file": source_file,
            }
        )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            flush()
            header = line[1:].strip()
            parts = []
        else:
            parts.append(line)
    flush()
    return rows


def _record_id_from_header(header: str) -> str:
    first = header.split(None, 1)[0]
    return first.strip(",;|")


def _target_ids_for_sequence_record(record_id: str, header: str) -> set[str]:
    ids: set[str] = set()
    for token in TARGET_TOKEN_RE.findall(f"{record_id} {header}"):
        token = token.upper()
        ids.add(token)
        ids.add(base_target_id(token))
    return ids


def base_target_id(target_id: str) -> str:
    match = re.match(r"^([A-Z]\d{4})(?:S\d+)?$", target_id.upper())
    if match:
        return match.group(1)
    return target_id.upper()


def classify_sequence(record_id: str, header: str, sequence: str) -> str:
    low = f"{record_id} {header}".lower()
    if "rna" in low:
        return "rnaSequence"
    if "dna" in low or "ssdna" in low:
        return "dnaSequence"
    if "prot" in low or "protein" in low:
        return "proteinChain"
    prefix = record_id[:1].upper()
    if prefix in {"T", "H"}:
        return "proteinChain"
    if prefix == "R":
        return "rnaSequence"
    if prefix == "D":
        return "dnaSequence"
    alphabet = set(sequence.upper())
    if alphabet <= set("ACGUN"):
        return "rnaSequence" if "U" in alphabet else "dnaSequence"
    return "proteinChain"


def parse_score_table_text(text: str, category: str, source_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_target = ""
    headers: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Target:"):
            current_target = line.split(":", 1)[1].strip().split()[0]
            continue
        if line.startswith("#"):
            candidate = _split_header(line)
            if "Model" in candidate:
                headers = candidate
            continue
        parts = line.split()
        if not parts or not headers:
            continue
        if parts[0].isdigit():
            submitted_rank = parts[0]
            values = parts[1:]
        elif "TS" in parts[0]:
            submitted_rank = ""
            values = parts
        else:
            continue
        if len(values) < len(headers):
            values = values + [""] * (len(headers) - len(values))
        metrics = dict(zip(headers, values[: len(headers)]))
        model = metrics.get("Model", "")
        target_id = current_target or infer_target_from_model(model)
        primary_metric, primary_score = choose_primary_score(category, metrics)
        rows.append(
            {
                "category": category,
                "table": source_name,
                "target_id": target_id,
                "model": model,
                "group": metrics.get("GR#", "") or metrics.get("Gr.Code", "") or metrics.get("GR.Code", ""),
                "submitted_model_rank": submitted_rank,
                "primary_metric": primary_metric,
                "primary_score": "" if primary_score is None else f"{primary_score:.6f}",
                "metric_json": json.dumps(metrics, sort_keys=True),
                "source_path": source_name,
            }
        )
    return rows


def _split_header(line: str) -> list[str]:
    return line.lstrip("#").strip().split()


def infer_target_from_model(model: str) -> str:
    match = MODEL_TARGET_RE.search(model)
    if match:
        return match.group(1).upper()
    match = TARGET_TOKEN_RE.search(model)
    return match.group(1).upper() if match else ""


def choose_primary_score(category: str, metrics: dict[str, str]) -> tuple[str, float | None]:
    for key in PRIMARY_METRIC_CANDIDATES.get(category, ()):
        if key in metrics:
            value = parse_float(metrics[key])
            if value is not None:
                return key, value
    return "", None


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return None
    match = FLOAT_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def ingest_official_data(root: Path, *, force: bool = False) -> dict[str, object]:
    paths = OfficialPaths(root)
    ensure_dir(paths.parsed_dir)

    target_text = download_text(TARGET_LIST_URL, paths.target_csv, force=force)
    targets = parse_targets_text(target_text)
    write_tsv(
        paths.targets_tsv,
        targets,
        [
            "target_id",
            "target_prefix",
            "Target",
            "Type",
            "Res",
            "Oligo.State",
            "Entry Date",
            "Server Exp.",
            "Human Exp.",
            "QA Exp.",
            "Cancellation Date",
            "Description",
        ],
    )

    sequence_rows: list[dict[str, str]] = []
    for family, filename in SEQUENCE_FILES.items():
        url = f"{BASE_DOWNLOAD_URL}/sequences/{filename}"
        text = download_text(url, paths.sequences_dir / filename, force=force)
        for row in parse_fasta_text(text, filename):
            row["sequence_family"] = family
            sequence_rows.append(row)
    write_tsv(
        paths.sequences_tsv,
        sequence_rows,
        [
            "record_id",
            "target_ids",
            "sequence_family",
            "sequence_kind",
            "length",
            "sequence",
            "header",
            "source_file",
        ],
    )

    score_rows: list[dict[str, str]] = []
    table_counts: dict[str, int] = {}
    for category, filename in SCORE_TABLES.items():
        url = f"{BASE_DOWNLOAD_URL}/results/tables/{filename}"
        text = download_text(url, paths.tables_dir / filename, force=force)
        parsed = parse_score_table_text(text, category, filename)
        table_counts[category] = len(parsed)
        score_rows.extend(parsed)
    write_tsv(
        paths.scores_tsv,
        score_rows,
        [
            "category",
            "table",
            "target_id",
            "model",
            "group",
            "submitted_model_rank",
            "primary_metric",
            "primary_score",
            "metric_json",
            "source_path",
        ],
    )

    summary = {
        "target_count": len(targets),
        "target_prefix_counts": _count(row["target_prefix"] for row in targets),
        "sequence_record_count": len(sequence_rows),
        "sequence_kind_counts": _count(row["sequence_kind"] for row in sequence_rows),
        "score_record_count": len(score_rows),
        "score_table_counts": table_counts,
        "official_root": str(root),
    }
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _count(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0
