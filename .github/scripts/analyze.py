"""
analyze.py
----------
Standalone analysis script for SEC cybersecurity disclosure data.

Produces a summary report to stdout and optionally saves a CSV of all filings.

Usage:
    python analyze.py                     # Print report
    python analyze.py --csv output.csv    # Also export full dataset as CSV
    python analyze.py --json              # Print report as JSON
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all(base: Path) -> list[dict]:
    records = []
    for form in ("8K", "10K"):
        d = base / form
        if not d.exists():
            continue
        for meta_path in sorted(d.rglob("metadata.json")):
            try:
                r = json.loads(meta_path.read_text(encoding="utf-8"))
                cyber_path = meta_path.parent / "cybersecurity.md"
                r["text_length"] = len(cyber_path.read_text(encoding="utf-8")) if cyber_path.exists() else 0
                records.append(r)
            except Exception as e:
                print(f"[WARN] Could not read {meta_path}: {e}", file=sys.stderr)
    return records


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def top_n(counter: Counter, n: int = 10) -> list[tuple]:
    return counter.most_common(n)


def monthly_counts(records: list[dict]) -> dict[str, int]:
    c: Counter = Counter()
    for r in records:
        ym = (r.get("filing_date") or "")[:7]
        if ym:
            c[ym] += 1
    return dict(sorted(c.items()))


def print_report(records: list[dict]):
    total = len(records)
    k8 = [r for r in records if r.get("form_type") == "8-K"]
    k10 = [r for r in records if r.get("form_type") == "10-K"]
    material = [r for r in k8 if r.get("item") == "1.05"]
    voluntary = [r for r in k8 if r.get("item") == "8.01"]

    print("=" * 60)
    print("SEC EDGAR Cybersecurity Disclosures — Analysis Report")
    print("=" * 60)
    print(f"\nTotal filings:          {total:,}")
    print(f"  8-K Item 1.05 (material incident): {len(material):,}")
    print(f"  8-K Item 8.01 (voluntary):          {len(voluntary):,}")
    print(f"  10-K Item 1C  (annual):             {len(k10):,}")

    # Date range
    dates = sorted(r["filing_date"] for r in records if r.get("filing_date"))
    if dates:
        print(f"\nDate range: {dates[0]}  →  {dates[-1]}")

    # Top filers
    print("\nTop 15 most active filers (by disclosure count):")
    ticker_counts: Counter = Counter(r.get("ticker", "?") for r in records)
    for ticker, count in top_n(ticker_counts, 15):
        company = next(
            (r.get("company_name", "") for r in records if r.get("ticker") == ticker), ""
        )
        print(f"  {ticker:10s}  {count:4d}  {company}")

    # Monthly trend (last 24 months)
    print("\nMonthly filing trend (all types):")
    monthly = monthly_counts(records)
    months = sorted(monthly)[-24:]
    if months:
        max_count = max(monthly[m] for m in months)
        bar_width = 40
        for m in months:
            c = monthly[m]
            bar = "█" * int(c / max_count * bar_width)
            print(f"  {m}  {bar:<{bar_width}}  {c:4d}")

    # Average disclosure length
    if records:
        avg_len = sum(r.get("text_length", 0) for r in records) / len(records)
        avg_8k = sum(r.get("text_length", 0) for r in k8) / max(len(k8), 1)
        avg_10k = sum(r.get("text_length", 0) for r in k10) / max(len(k10), 1)
        print(f"\nAverage disclosure length:")
        print(f"  Overall:     {avg_len:,.0f} chars")
        print(f"  8-K filings: {avg_8k:,.0f} chars")
        print(f"  10-K Item 1C:{avg_10k:,.0f} chars")

    print()


def export_csv(records: list[dict], path: str):
    try:
        import csv

        fieldnames = [
            "accession_number", "ticker", "cik", "company_name",
            "filing_date", "form_type", "item", "filing_url",
            "retrieved_at", "text_length",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        print(f"Exported {len(records):,} records → {path}")
    except ImportError:
        print("[ERROR] csv module not available", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze SEC cybersecurity disclosures")
    parser.add_argument("--csv", metavar="PATH", help="Export all records to CSV")
    parser.add_argument("--json", action="store_true", help="Output stats as JSON")
    args = parser.parse_args()

    records = load_all(BASE_DIR)

    if not records:
        print("No filings found. Run fetch_8k.py and fetch_10k.py first.")
        sys.exit(0)

    if args.json:
        from collections import Counter as C

        output = {
            "total": len(records),
            "8K_material": sum(1 for r in records if r.get("form_type") == "8-K" and r.get("item") == "1.05"),
            "8K_voluntary": sum(1 for r in records if r.get("form_type") == "8-K" and r.get("item") == "8.01"),
            "10K": sum(1 for r in records if r.get("form_type") == "10-K"),
            "monthly": monthly_counts(records),
            "top_tickers": dict(C(r.get("ticker", "?") for r in records).most_common(25)),
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(records)

    if args.csv:
        export_csv(records, args.csv)


if __name__ == "__main__":
    main()
