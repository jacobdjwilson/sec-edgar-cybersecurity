"""
build_stats.py
--------------
Scans the 8K/ and 10K/ directories and builds stats/summary.json.

Produces:
  - Total filing counts by form type and item
  - Monthly breakdown (filings per year-month)
  - Top 25 companies by total cybersecurity disclosure count
  - Most recent 20 filings per form type
  - Counts of incident vs voluntary 8-K filings
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = BASE_DIR / "stats" / "summary.json"


def collect_metadata(directory: Path) -> list[dict]:
    records = []
    for meta_path in sorted(directory.rglob("metadata.json")):
        try:
            records.append(json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return records


def build_summary(records_8k: list[dict], records_10k: list[dict]) -> dict:
    all_records = records_8k + records_10k

    # --- Counts by form / item ---
    item_counts = Counter(
        f"{r['form_type']} Item {r.get('item', '?')}" for r in all_records
    )

    # 8-K breakdown: material (1.05) vs voluntary (8.01)
    k8_material = sum(1 for r in records_8k if r.get("item") == "1.05")
    k8_voluntary = sum(1 for r in records_8k if r.get("item") == "8.01")

    # --- Monthly trend ---
    monthly: dict[str, dict] = defaultdict(lambda: {"8-K": 0, "10-K": 0})
    for r in all_records:
        date_str = r.get("filing_date", "")
        if len(date_str) >= 7:
            ym = date_str[:7]
            monthly[ym][r.get("form_type", "?")] += 1
    monthly_sorted = dict(sorted(monthly.items()))

    # --- Yearly trend ---
    yearly: dict[str, dict] = defaultdict(lambda: {"8-K": 0, "10-K": 0})
    for r in all_records:
        year = (r.get("filing_date") or "")[:4]
        if year.isdigit():
            yearly[year][r.get("form_type", "?")] += 1
    yearly_sorted = dict(sorted(yearly.items()))

    # --- Top companies (by total disclosures) ---
    company_counts: Counter = Counter()
    for r in all_records:
        key = r.get("ticker") or r.get("cik") or "UNKNOWN"
        company_counts[key] += 1
    top_companies = [
        {"ticker": t, "disclosure_count": c}
        for t, c in company_counts.most_common(25)
    ]

    # --- Most recent filings ---
    def sort_key(r):
        return r.get("filing_date") or ""

    recent_8k = sorted(records_8k, key=sort_key, reverse=True)[:20]
    recent_10k = sorted(records_10k, key=sort_key, reverse=True)[:20]

    def slim(r: dict) -> dict:
        return {
            "accession_number": r.get("accession_number"),
            "ticker": r.get("ticker"),
            "company_name": r.get("company_name"),
            "filing_date": r.get("filing_date"),
            "item": r.get("item"),
        }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "totals": {
            "8K_filings": len(records_8k),
            "10K_filings": len(records_10k),
            "total_filings": len(all_records),
            "8K_material_incident_1_05": k8_material,
            "8K_voluntary_8_01": k8_voluntary,
        },
        "by_item": dict(item_counts),
        "monthly_trend": monthly_sorted,
        "yearly_trend": yearly_sorted,
        "top_25_companies_by_disclosure_count": top_companies,
        "most_recent_8K": [slim(r) for r in recent_8k],
        "most_recent_10K": [slim(r) for r in recent_10k],
    }


def main():
    dir_8k = BASE_DIR / "8K"
    dir_10k = BASE_DIR / "10K"

    records_8k = collect_metadata(dir_8k) if dir_8k.exists() else []
    records_10k = collect_metadata(dir_10k) if dir_10k.exists() else []

    print(f"Found {len(records_8k)} 8-K filings and {len(records_10k)} 10-K filings")

    summary = build_summary(records_8k, records_10k)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")

    # Print a brief human summary
    t = summary["totals"]
    print(
        f"\n  Total:  {t['total_filings']} filings  "
        f"({t['8K_material_incident_1_05']} material incidents, "
        f"{t['8K_voluntary_8_01']} voluntary 8-K, "
        f"{t['10K_filings']} annual 10-K)"
    )


if __name__ == "__main__":
    main()
