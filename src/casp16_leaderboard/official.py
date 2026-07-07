from __future__ import annotations

import csv
import json
import re
import statistics
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence


TARGET_LIST_URL = "https://predictioncenter.org/casp16/targetlist.cgi?type=csv"
TARGET_LIST_HTML_URL = "https://predictioncenter.org/casp16/targetlist.cgi"
DOMAINS_SUMMARY_URL = "https://predictioncenter.org/casp16/domains_summary.cgi"
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
DOMAIN_DEF_RE = re.compile(r"\b([A-Z]\d{4}(?:S\d+|V\d+)?-D\d+)\s*:\s*(.+)$", re.IGNORECASE)
PDB_ID_RE = re.compile(r"\b([0-9](?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{3})\b")
NUCLEIC_SEQUENCE_ALPHABET = set("ACGTUN")
PROTEIN_SEQUENCE_ALPHABET = set("ABCDEFGHIKLMNPQRSTVWXYZ")

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
    def domains_dir(self) -> Path:
        return self.root / "domains"

    @property
    def references_dir(self) -> Path:
        return self.root / "references"

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
    def target_html(self) -> Path:
        return self.targets_dir / "casp16_targetlist.html"

    @property
    def domain_summary_html(self) -> Path:
        return self.domains_dir / "casp16_domains_summary.html"

    @property
    def targets_tsv(self) -> Path:
        return self.parsed_dir / "targets.tsv"

    @property
    def target_references_tsv(self) -> Path:
        return self.parsed_dir / "target_references.tsv"

    @property
    def sequences_tsv(self) -> Path:
        return self.parsed_dir / "sequences.tsv"

    @property
    def domains_tsv(self) -> Path:
        return self.parsed_dir / "domain_definitions.tsv"

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


class _DomainSummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, list[str]]]] = []
        self._in_row = False
        self._in_cell = False
        self._current_cells: list[tuple[str, list[str]]] = []
        self._current_text: list[str] = []
        self._current_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._in_row = True
            self._current_cells = []
        elif tag in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._current_text = []
            self._current_links = []
        elif tag == "a" and self._in_cell:
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self._current_links.append(value)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            text = " ".join("".join(self._current_text).split())
            self._current_cells.append((text, list(self._current_links)))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._current_cells:
                self.rows.append(self._current_cells)
            self._in_row = False


def parse_domain_summary_text(text: str) -> list[dict[str, str]]:
    parser = _DomainSummaryParser()
    parser.feed(text)
    rows: list[dict[str, str]] = []
    for cells in parser.rows:
        values = [text for text, _ in cells]
        if len(values) < 6:
            continue
        if not values[0].rstrip(".").isdigit():
            continue
        domain_text = values[3]
        match = DOMAIN_DEF_RE.search(domain_text)
        if not match:
            continue
        domain_id = match.group(1).upper()
        target_id = domain_id.split("-D", 1)[0]
        pdb_ids = sorted(_pdb_ids_from_cells(cells))
        rows.append(
            {
                "target_id": target_id,
                "target_len": values[2],
                "domain_id": domain_id,
                "residue_ranges": match.group(2).strip(),
                "domain_len": values[4],
                "difficulty": values[5],
                "pdb_ids": ",".join(pdb_ids),
                "source": "domains_summary.cgi",
            }
        )
    return rows


def parse_target_reference_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    target_anchor_re = re.compile(r'<a[^>]+href="target\.cgi[^"]*"[^>]*>\s*([THRDML]\d{4}(?:s\d+|v\d+)?)\s*</a>', re.IGNORECASE)
    matches = list(target_anchor_re.finditer(text))
    for index, match in enumerate(matches):
        target_id = match.group(1).upper()
        if target_id in seen:
            continue
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[match.start() : next_start]
        pdb_ids = sorted(_pdb_ids_from_target_chunk(chunk))
        if not pdb_ids:
            continue
        seen.add(target_id)
        rows.append({"target_id": target_id, "pdb_ids": ",".join(pdb_ids), "source": "targetlist.cgi"})
    return rows


def _pdb_ids_from_cells(cells: Sequence[tuple[str, list[str]]]) -> set[str]:
    ids: set[str] = set()
    for text, links in cells:
        for match in PDB_ID_RE.findall(text):
            ids.add(match.lower())
        for href in links:
            for match in re.findall(r"(?:structureId=|/structure/)([0-9][A-Za-z0-9]{3})", href, re.IGNORECASE):
                ids.add(match.lower())
    return ids


def _pdb_ids_from_target_chunk(chunk: str) -> set[str]:
    ids = {
        match.lower()
        for match in re.findall(r"(?:structureId=|/structure/)([0-9][A-Za-z0-9]{3})", chunk, re.IGNORECASE)
        if PDB_ID_RE.fullmatch(match)
    }
    if ids:
        return ids
    text = re.sub(r"<[^>]+>", " ", chunk)
    match = re.search(r"PDB codes?:?\s*([0-9A-Za-z,\s]+)", text, re.IGNORECASE)
    if match:
        for pdb_id in PDB_ID_RE.findall(match.group(1)):
            ids.add(pdb_id.lower())
    return ids


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
    content_kind = classify_sequence_content(sequence)
    if content_kind == "proteinChain":
        return content_kind

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
    if alphabet <= NUCLEIC_SEQUENCE_ALPHABET:
        return "rnaSequence" if "U" in alphabet else "dnaSequence"
    return "proteinChain"


def classify_sequence_content(sequence: str) -> str:
    compact = re.sub(r"\s+", "", sequence.upper())
    if not compact:
        return ""
    alphabet = set(compact)
    if alphabet <= NUCLEIC_SEQUENCE_ALPHABET:
        return "rnaSequence" if "U" in alphabet else "dnaSequence"
    if not alphabet <= PROTEIN_SEQUENCE_ALPHABET:
        return ""
    non_nucleic = sum(1 for char in compact if char not in NUCLEIC_SEQUENCE_ALPHABET)
    if len(compact) >= 30 and (non_nucleic / len(compact)) >= 0.10:
        return "proteinChain"
    return ""


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
        metrics = align_score_values(headers, values)
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


def align_score_values(headers: Sequence[str], values: Sequence[str]) -> dict[str, str]:
    if len(values) < len(headers):
        padded = list(values) + [""] * (len(headers) - len(values))
        return dict(zip(headers, padded))
    if len(values) <= len(headers):
        return dict(zip(headers, values))
    head = list(values[: len(headers) - 1])
    tail = " ".join(values[len(headers) - 1 :])
    return dict(zip(headers, [*head, tail]))


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

    target_html = download_text(TARGET_LIST_HTML_URL, paths.target_html, force=force)
    target_reference_rows = parse_target_reference_text(target_html)
    write_tsv(paths.target_references_tsv, target_reference_rows, ["target_id", "pdb_ids", "source"])

    domain_text = download_text(DOMAINS_SUMMARY_URL, paths.domain_summary_html, force=force)
    domain_rows = parse_domain_summary_text(domain_text)
    write_tsv(
        paths.domains_tsv,
        domain_rows,
        [
            "target_id",
            "target_len",
            "domain_id",
            "residue_ranges",
            "domain_len",
            "difficulty",
            "pdb_ids",
            "source",
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
        "target_reference_count": len(target_reference_rows),
        "sequence_record_count": len(sequence_rows),
        "sequence_kind_counts": _count(row["sequence_kind"] for row in sequence_rows),
        "domain_definition_count": len(domain_rows),
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
