#!/usr/bin/env python3
"""
Generate a daily ingestion summary report formatted as a GitHub issue body.
Reads parse_summary.json files produced by the parse scripts and stats/summary.json.
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def main():
    run_date = os.environ.get("RUN_DATE", date.today().isoformat())
    data_dir = Path("data")
    stats_dir = Path("stats")

    summary_8k = load_json(data_dir / "8K" / "parse_summary.json")
    summary_10k = load_json(data_dir / "10K" / "parse_summary.json")
    overall = load_json(stats_dir / "summary.json")

    new_8k = summary_8k.get("disclosures_extracted", 0)
    new_10k = summary_10k.get("disclosures_extracted", 0)
    total = overall.get("total_filings", "N/A")
    unique_companies = overall.get("unique_companies", "N/A")

    issue_title = f"Daily Ingestion Summary — {run_date}"

    issue_body = f"""## 📊 Daily SEC Cybersecurity Disclosure Ingestion — {run_date}

### New Filings Ingested Today

| Filing Type | New Disclosures |
|-------------|----------------|
| 8-K (Item 1.05 — Cybersecurity Incidents) | {new_8k} |
| 10-K (Items 106 & 407j — Risk & Governance) | {new_10k} |
| **Total New** | **{new_8k + new_10k}** |

### Dataset Totals (Cumulative)

| Metric | Value |
|--------|-------|
| Total Filings in Dataset | {total} |
| Unique Companies Covered | {unique_companies} |

### Pipeline Status

- ✅ 8-K download & parse complete
- ✅ 10-K download & parse complete
- ✅ Statistics updated

### Raw Scan Details

**8-K:**
- Files scanned: {summary_8k.get('total_files_scanned', 'N/A')}
- Item 1.05 found: {summary_8k.get('disclosures_extracted', 'N/A')}
- No Item 1.05 (skipped): {summary_8k.get('skipped_no_item_105', 'N/A')}

**10-K:**
- Files scanned: {summary_10k.get('total_files_scanned', 'N/A')}
- Cybersecurity items found: {summary_10k.get('disclosures_extracted', 'N/A')}
- No cybersecurity items (skipped): {summary_10k.get('skipped_no_cyber_items', 'N/A')}

---
*Generated automatically by the SEC EDGAR Cybersecurity pipeline at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""

    # Output for GitHub Actions (set step outputs)
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            # Escape newlines for GitHub Actions multiline output
            escaped_body = issue_body.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
            f.write(f"issue_title={issue_title}\n")
            f.write(f"issue_body={escaped_body}\n")
    else:
        print(f"Title: {issue_title}")
        print("---")
        print(issue_body)


if __name__ == "__main__":
    main()
