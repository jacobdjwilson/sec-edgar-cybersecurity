#!/usr/bin/env python3
"""
Backfill historical SEC cybersecurity filings for a given year range.
Downloads and parses 8-K and/or 10-K filings for the specified period.
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill historical SEC cybersecurity filings")
    parser.add_argument("--start-year", type=int, required=True, help="Start year (e.g. 2023)")
    parser.add_argument("--end-year", type=int, required=True, help="End year (e.g. 2024)")
    parser.add_argument(
        "--filing-type",
        type=str,
        default="both",
        choices=["8-K", "10-K", "both"],
        help="Filing type to backfill",
    )
    parser.add_argument(
        "--use-provider",
        action="store_true",
        help="Use datamule provider for faster downloads (costs $1/100k downloads)",
    )
    return parser.parse_args()


def run_script(script: str, extra_args: list[str] = None):
    cmd = [sys.executable, script] + (extra_args or [])
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"ERROR: Script failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main():
    args = parse_args()

    scripts_dir = Path(__file__).parent

    for year in range(args.start_year, args.end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        # Cap end date to today if it's in the future
        today = date.today()
        if date.fromisoformat(end_date) > today:
            end_date = today.isoformat()

        print(f"\n{'='*60}")
        print(f"Processing year {year}: {start_date} → {end_date}")
        print(f"{'='*60}")

        do_8k = args.filing_type in ("8-K", "both")
        do_10k = args.filing_type in ("10-K", "both")

        provider_flag = ["--use-provider"] if args.use_provider else []

        if do_8k:
            print(f"\n--- Downloading 8-K filings for {year} ---")
            run_script(
                str(scripts_dir / "download_8k_filings.py"),
                [
                    "--start-date", start_date,
                    "--end-date", end_date,
                    "--output-dir", f"raw_filings/8K/{year}",
                ] + provider_flag,
            )
            print(f"\n--- Parsing 8-K filings for {year} ---")
            run_script(
                str(scripts_dir / "parse_8k_disclosures.py"),
                [
                    "--input-dir", f"raw_filings/8K/{year}",
                    "--output-dir", "data/8K",
                ],
            )

        if do_10k:
            print(f"\n--- Downloading 10-K filings for {year} ---")
            run_script(
                str(scripts_dir / "download_10k_filings.py"),
                [
                    "--start-date", start_date,
                    "--end-date", end_date,
                    "--output-dir", f"raw_filings/10K/{year}",
                ] + provider_flag,
            )
            print(f"\n--- Parsing 10-K filings for {year} ---")
            run_script(
                str(scripts_dir / "parse_10k_disclosures.py"),
                [
                    "--input-dir", f"raw_filings/10K/{year}",
                    "--output-dir", "data/10K",
                ],
            )

    print("\n--- Generating statistics ---")
    run_script(str(scripts_dir / "generate_statistics.py"))

    print("\nBackfill complete!")


if __name__ == "__main__":
    main()
