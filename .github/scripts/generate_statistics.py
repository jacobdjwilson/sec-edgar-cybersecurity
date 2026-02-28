#!/usr/bin/env python3
"""
Generate dataset statistics and summary reports.
Reads all Markdown files in data/ and produces:
  - stats/summary.json
  - stats/README.md
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml


def parse_args():
    parser = argparse.ArgumentParser(description="Generate dataset statistics")
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--output-dir", type=str, default="stats")
    parser.add_argument("--filing-type", type=str, default="both", choices=["8K", "10K", "both"])
    return parser.parse_args()


def parse_frontmatter(md_path: Path) -> dict | None:
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        return yaml.safe_load(parts[1])
    except Exception:
        return None


def collect_filings(data_dir: Path, filing_type: str) -> list[dict]:
    filings = []
    patterns = []

    if filing_type in ("8K", "both"):
        patterns.append(data_dir / "8K")
    if filing_type in ("10K", "both"):
        patterns.append(data_dir / "10K")

    for base_dir in patterns:
        if not base_dir.exists():
            continue
        for md_file in base_dir.glob("**/*.md"):
            fm = parse_frontmatter(md_file)
            if fm:
                fm["_file"] = str(md_file)
                filings.append(fm)

    return filings


def compute_stats(filings: list[dict]) -> dict:
    total = len(filings)
    by_type = Counter(f.get("filing_type", "unknown") for f in filings)
    unique_ciks = len(set(str(f.get("cik", "")) for f in filings if f.get("cik")))
    unique_tickers = len(set(f.get("ticker", "").upper() for f in filings if f.get("ticker")))

    by_year = Counter()
    by_quarter = Counter()
    by_year_quarter = Counter()

    for f in filings:
        filing_date = f.get("filing_date", "")
        if isinstance(filing_date, str) and len(filing_date) >= 4:
            year = filing_date[:4]
            by_year[year] += 1
            # Try to get quarter from directory path
            path_parts = Path(f.get("_file", "")).parts
            for part in path_parts:
                if re.match(r"^Q[1-4]$", part):
                    by_quarter[part] += 1
                    by_year_quarter[f"{year}/{part}"] += 1
                    break

    # Top companies by filing count
    company_counts = Counter()
    for f in filings:
        company = f.get("company_name") or f.get("ticker") or str(f.get("cik", "unknown"))
        company_counts[company] += 1
    top_companies = company_counts.most_common(20)

    # 10-K item breakdown
    item_106_count = sum(1 for f in filings if 106 in (f.get("items") or []))
    item_407j_count = sum(1 for f in filings if "407j" in (f.get("items") or []))

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_filings": total,
        "by_filing_type": dict(by_type),
        "unique_companies": unique_ciks,
        "unique_tickers": unique_tickers,
        "by_year": dict(sorted(by_year.items())),
        "by_quarter": dict(sorted(by_quarter.items())),
        "by_year_quarter": dict(sorted(by_year_quarter.items())),
        "top_companies_by_filing_count": [{"company": c, "count": n} for c, n in top_companies],
        "10k_item_106_count": item_106_count,
        "10k_item_407j_count": item_407j_count,
    }


def render_markdown_report(stats: dict) -> str:
    lines = [
        "# SEC EDGAR Cybersecurity Disclosures — Dataset Statistics",
        "",
        f"*Last updated: {stats['generated_at']}*",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Filings | {stats['total_filings']:,} |",
        f"| Unique Companies | {stats['unique_companies']:,} |",
        f"| Unique Tickers | {stats['unique_tickers']:,} |",
        "",
        "## Filings by Type",
        "",
        "| Filing Type | Count |",
        "|-------------|-------|",
    ]
    for ft, count in sorted(stats["by_filing_type"].items()):
        lines.append(f"| {ft} | {count:,} |")

    lines += [
        "",
        "## Filings by Year",
        "",
        "| Year | Count |",
        "|------|-------|",
    ]
    for year, count in sorted(stats["by_year"].items()):
        lines.append(f"| {year} | {count:,} |")

    lines += [
        "",
        "## Filings by Year and Quarter",
        "",
        "| Period | Count |",
        "|--------|-------|",
    ]
    for yq, count in sorted(stats["by_year_quarter"].items()):
        lines.append(f"| {yq} | {count:,} |")

    lines += [
        "",
        "## Top 20 Companies by Filing Count",
        "",
        "| Company | Count |",
        "|---------|-------|",
    ]
    for entry in stats["top_companies_by_filing_count"]:
        lines.append(f"| {entry['company']} | {entry['count']} |")

    lines += [
        "",
        "## 10-K Item Breakdown",
        "",
        f"| Item | Count |",
        f"|------|-------|",
        f"| Item 106 (Risk Management & Strategy) | {stats['10k_item_106_count']:,} |",
        f"| Item 407(j) (Board Governance) | {stats['10k_item_407j_count']:,} |",
        "",
    ]

    return "\n".join(lines)


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting filings from {data_dir} (type={args.filing_type})...")
    filings = collect_filings(data_dir, args.filing_type)
    print(f"Found {len(filings)} filings with frontmatter.")

    stats = compute_stats(filings)

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Written: {summary_path}")

    readme_path = output_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(render_markdown_report(stats))
    print(f"Written: {readme_path}")


if __name__ == "__main__":
    main()
