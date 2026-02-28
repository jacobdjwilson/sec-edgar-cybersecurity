#!/usr/bin/env python3
"""
Parse 8-K filings and extract Item 1.05 (Material Cybersecurity Incidents) disclosures.
Outputs individual Markdown files with YAML frontmatter to data/8K/<YEAR>/<QUARTER>/.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import html2text
import yaml
from bs4 import BeautifulSoup


# Regex patterns to locate Item 1.05 within an 8-K filing
ITEM_105_PATTERNS = [
    re.compile(r"item\s+1\.05[\s\.\:—–-]+material\s+cybersecurity\s+incidents?", re.I),
    re.compile(r"item\s+1\.05", re.I),
]

# Patterns for the NEXT item header (to determine where Item 1.05 ends)
NEXT_ITEM_PATTERN = re.compile(
    r"item\s+(?:[2-9]\.\d+|\d{2})\b", re.I
)


def parse_args():
    parser = argparse.ArgumentParser(description="Parse Item 1.05 from 8-K filings")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="raw_filings/8K",
        help="Directory containing downloaded 8-K filings",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/8K",
        help="Directory to write parsed Markdown files",
    )
    parser.add_argument(
        "--metadata-file",
        type=str,
        default=None,
        help="Path to accession metadata JSON (optional)",
    )
    return parser.parse_args()


def date_to_quarter(filing_date: str) -> str:
    dt = datetime.strptime(filing_date, "%Y-%m-%d")
    q = (dt.month - 1) // 3 + 1
    return f"Q{q}"


def extract_filing_metadata(filing_dir: Path) -> dict:
    """
    Attempt to extract CIK, ticker, company name, accession number, and filing date
    from datamule's directory structure or from an accompanying JSON metadata file.
    """
    meta = {
        "ticker": "",
        "company_name": "",
        "cik": "",
        "filing_date": "",
        "accession_number": "",
        "source_link": "",
    }

    # datamule typically organises downloads as: <output_dir>/<CIK>/<accession>/<files>
    # Try to extract from path parts
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
                f"&CIK={possible_cik}&type=8-K&dateb=&owner=exclude&count=100"
            )

    # Check for companion metadata JSON
    for meta_file in filing_dir.glob("*.json"):
        try:
            with open(meta_file) as f:
                data = json.load(f)
            meta["ticker"] = data.get("ticker", meta["ticker"])
            meta["company_name"] = data.get("company_name", data.get("entityName", meta["company_name"]))
            meta["cik"] = str(data.get("cik", meta["cik"]))
            meta["filing_date"] = data.get("filing_date", data.get("filingDate", meta["filing_date"]))
            meta["accession_number"] = data.get("accession_number", data.get("accessionNumber", meta["accession_number"]))
            break
        except Exception:
            continue

    return meta


def extract_item_105(html_content: str) -> str | None:
    """
    Extract the text of Item 1.05 from an 8-K HTML filing.
    Returns plain Markdown text or None if not found.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script/style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    full_text = soup.get_text(separator="\n")
    lines = full_text.splitlines()

    # Find the line containing Item 1.05
    start_idx = None
    for i, line in enumerate(lines):
        for pattern in ITEM_105_PATTERNS:
            if pattern.search(line):
                start_idx = i
                break
        if start_idx is not None:
            break

    if start_idx is None:
        return None

    # Find where the next item starts
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if NEXT_ITEM_PATTERN.search(lines[i]):
            end_idx = i
            break

    extracted_lines = lines[start_idx:end_idx]
    text = "\n".join(extracted_lines).strip()

    # Convert to markdown-friendly text
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    # text already extracted from soup; clean it up
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text if len(text) > 100 else None


def build_frontmatter(meta: dict) -> str:
    fm = {
        "ticker": meta.get("ticker", ""),
        "company_name": meta.get("company_name", ""),
        "cik": meta.get("cik", ""),
        "filing_date": meta.get("filing_date", ""),
        "filing_type": "8-K",
        "item": "1.05",
        "accession_number": meta.get("accession_number", ""),
        "source_link": meta.get("source_link", ""),
    }
    return "---\n" + yaml.dump(fm, default_flow_style=False, allow_unicode=True) + "---\n"


def write_markdown(output_dir: Path, meta: dict, content: str):
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
    filename = f"{cik}_{filing_date}_8K.md"
    out_path = out_subdir / filename

    frontmatter = build_frontmatter(meta)
    body = f"\n## Item 1.05. Material Cybersecurity Incidents\n\n{content}\n"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + body)

    return out_path


def process_filing(filing_path: Path, output_dir: Path, meta_override: dict = None) -> bool:
    try:
        with open(filing_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()
    except Exception as e:
        print(f"  ERROR reading {filing_path}: {e}")
        return False

    content = extract_item_105(html_content)
    if content is None:
        return False  # No Item 1.05 found — not a cybersecurity 8-K

    meta = extract_filing_metadata(filing_path.parent)
    if meta_override:
        meta.update({k: v for k, v in meta_override.items() if v})

    out_path = write_markdown(output_dir, meta, content)
    print(f"  Parsed: {out_path}")
    return True


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all HTML files
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
    print(f"  Filings with Item 1.05: {parsed_count}")
    print(f"  Filings without Item 1.05: {skipped_count}")

    # Write summary
    summary = {
        "parsed_at": datetime.utcnow().isoformat(),
        "total_files_scanned": len(html_files),
        "disclosures_extracted": parsed_count,
        "skipped_no_item_105": skipped_count,
    }
    summary_path = output_dir / "parse_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
