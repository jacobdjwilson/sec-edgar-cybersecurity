#!/usr/bin/env python3
"""
Parse 10-K filings and extract:
  - Item 106: Cybersecurity Risk Management, Strategy, and Governance
  - Item 407(j): Board Oversight of Cybersecurity Risk

Outputs individual Markdown files with YAML frontmatter to data/10K/<YEAR>/<QUARTER>/.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


# Patterns for Item 106
ITEM_106_PATTERNS = [
    re.compile(r"item\s+1[0o]6[\s\.\:—–-]+cybersecurity", re.I),
    re.compile(r"item\s+1[0o]6\b", re.I),
]

# Patterns for Item 407(j)
ITEM_407J_PATTERNS = [
    re.compile(r"item\s+407\s*\(j\)", re.I),
    re.compile(r"item\s+407j\b", re.I),
]

# Pattern to detect "next" major item (to bound extraction)
NEXT_MAJOR_ITEM_PATTERN = re.compile(
    r"^item\s+\d{3,}", re.I
)


def parse_args():
    parser = argparse.ArgumentParser(description="Parse Items 106 & 407(j) from 10-K filings")
    parser.add_argument("--input-dir", type=str, default="raw_filings/10K")
    parser.add_argument("--output-dir", type=str, default="data/10K")
    return parser.parse_args()


def date_to_quarter(filing_date: str) -> str:
    dt = datetime.strptime(filing_date, "%Y-%m-%d")
    q = (dt.month - 1) // 3 + 1
    return f"Q{q}"


def extract_filing_metadata(filing_dir: Path) -> dict:
    meta = {
        "ticker": "",
        "company_name": "",
        "cik": "",
        "filing_date": "",
        "fiscal_year_end": "",
        "accession_number": "",
        "source_link": "",
    }

    parts = filing_dir.parts
    if len(parts) >= 2:
        possible_accession = parts[-1]
        possible_cik = parts[-2]
        if re.match(r"^\d{10}-\d{2}-\d{6}$", possible_accession):
            meta["accession_number"] = possible_accession
        if re.match(r"^\d+$", possible_cik):
            meta["cik"] = possible_cik
            meta["source_link"] = (
                f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                f"&CIK={possible_cik}&type=10-K&dateb=&owner=exclude&count=100"
            )

    for meta_file in filing_dir.glob("*.json"):
        try:
            with open(meta_file) as f:
                data = json.load(f)
            meta["ticker"] = data.get("ticker", meta["ticker"])
            meta["company_name"] = data.get("company_name", data.get("entityName", meta["company_name"]))
            meta["cik"] = str(data.get("cik", meta["cik"]))
            meta["filing_date"] = data.get("filing_date", data.get("filingDate", meta["filing_date"]))
            meta["fiscal_year_end"] = data.get("fiscal_year_end", data.get("periodOfReport", meta["fiscal_year_end"]))
            meta["accession_number"] = data.get("accession_number", data.get("accessionNumber", meta["accession_number"]))
            break
        except Exception:
            continue

    return meta


def extract_section(lines: list[str], start_patterns: list, end_patterns: list = None) -> str | None:
    """
    Extract a section from line-split plain text given start/end regex patterns.
    """
    start_idx = None
    for i, line in enumerate(lines):
        for pattern in start_patterns:
            if pattern.search(line):
                start_idx = i
                break
        if start_idx is not None:
            break

    if start_idx is None:
        return None

    # Find end: next major item heading
    end_idx = len(lines)
    if end_patterns:
        for i in range(start_idx + 1, len(lines)):
            for ep in end_patterns:
                if ep.search(lines[i]):
                    end_idx = i
                    break
            if end_idx != len(lines):
                break

    text = "\n".join(lines[start_idx:end_idx]).strip()
    return text if len(text) > 100 else None


def build_frontmatter(meta: dict, items_found: list) -> str:
    fm = {
        "ticker": meta.get("ticker", ""),
        "company_name": meta.get("company_name", ""),
        "cik": meta.get("cik", ""),
        "filing_date": meta.get("filing_date", ""),
        "fiscal_year_end": meta.get("fiscal_year_end", ""),
        "filing_type": "10-K",
        "items": items_found,
        "accession_number": meta.get("accession_number", ""),
        "source_link": meta.get("source_link", ""),
    }
    return "---\n" + yaml.dump(fm, default_flow_style=False, allow_unicode=True) + "---\n"


def write_markdown(output_dir: Path, meta: dict, item106_text: str | None, item407j_text: str | None):
    filing_date = meta.get("filing_date", "unknown")
    try:
        year = filing_date[:4]
        quarter = date_to_quarter(filing_date)
    except Exception:
        year = "unknown"
        quarter = "unknown"

    out_subdir = output_dir / year / quarter
    out_subdir.mkdir(parents=True, exist_ok=True)

    cik = meta.get("cik", "unknown")
    filename = f"{cik}_{filing_date}_10K.md"
    out_path = out_subdir / filename

    items_found = []
    body_parts = []

    if item106_text:
        items_found.append(106)
        body_parts.append(f"## Item 106. Cybersecurity Risk Management, Strategy, and Governance\n\n{item106_text}\n")

    if item407j_text:
        items_found.append("407j")
        body_parts.append(f"## Item 407(j). Board Oversight of Cybersecurity Risk\n\n{item407j_text}\n")

    if not items_found:
        return None

    frontmatter = build_frontmatter(meta, items_found)
    body = "\n".join(body_parts)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + "\n" + body)

    return out_path


def process_filing(filing_path: Path, output_dir: Path) -> bool:
    try:
        with open(filing_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()
    except Exception as e:
        print(f"  ERROR reading {filing_path}: {e}")
        return False

    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    full_text = soup.get_text(separator="\n")
    lines = full_text.splitlines()

    # End-of-section patterns: next numbered item heading
    end_patterns = [
        re.compile(r"^item\s+\d{3}\b", re.I),
        re.compile(r"^part\s+[IVX]+\b", re.I),
    ]

    item106_text = extract_section(lines, ITEM_106_PATTERNS, end_patterns)
    item407j_text = extract_section(lines, ITEM_407J_PATTERNS, end_patterns)

    if item106_text is None and item407j_text is None:
        return False

    meta = extract_filing_metadata(filing_path.parent)
    out_path = write_markdown(output_dir, meta, item106_text, item407j_text)
    if out_path:
        print(f"  Parsed: {out_path}")
        return True
    return False


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(input_dir.glob("**/*.htm")) + list(input_dir.glob("**/*.html"))
    print(f"Found {len(html_files)} HTML filing files in {input_dir}")

    parsed_count = 0
    skipped_count = 0

    for html_file in html_files:
        result = process_filing(html_file, output_dir)
        if result:
            parsed_count += 1
        else:
            skipped_count += 1

    print(f"\nParsing complete.")
    print(f"  Filings with cybersecurity items: {parsed_count}")
    print(f"  Filings without cybersecurity items: {skipped_count}")

    summary = {
        "parsed_at": datetime.utcnow().isoformat(),
        "total_files_scanned": len(html_files),
        "disclosures_extracted": parsed_count,
        "skipped_no_cyber_items": skipped_count,
    }
    summary_path = output_dir / "parse_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
