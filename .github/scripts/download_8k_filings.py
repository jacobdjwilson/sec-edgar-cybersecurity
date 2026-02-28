#!/usr/bin/env python3
"""
Download 8-K filings from SEC EDGAR using datamule.
Targets filings containing Item 1.05 (Material Cybersecurity Incidents).
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Download 8-K filings from SEC EDGAR")
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date in YYYY-MM-DD format (default: yesterday)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format (default: yesterday)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="raw_filings/8K",
        help="Directory to save downloaded filings",
    )
    parser.add_argument(
        "--use-provider",
        action="store_true",
        help="Use datamule provider (requires API key, faster)",
    )
    return parser.parse_args()


def get_default_dates():
    yesterday = date.today() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")


def download_8k_filings(start_date: str, end_date: str, output_dir: str, use_provider: bool):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading 8-K filings from {start_date} to {end_date}")
    print(f"Output directory: {output_path.resolve()}")
    print(f"Using datamule provider: {use_provider}")

    try:
        import datamule as dm

        # Track downloaded filings metadata
        metadata_path = output_path / "download_metadata.json"
        metadata = {
            "start_date": start_date,
            "end_date": end_date,
            "downloaded_at": datetime.utcnow().isoformat(),
            "filing_type": "8-K",
            "files": [],
        }

        # Use datamule to download 8-K filings
        # datamule filters for 8-K filings; we'll parse for Item 1.05 in the parse step
        downloader = dm.Downloader()

        kwargs = {
            "form_type": "8-K",
            "start_date": start_date,
            "end_date": end_date,
            "output_dir": str(output_path),
        }
        if use_provider:
            kwargs["provider"] = "datamule"

        downloader.download(**kwargs)

        # Collect file list
        files = list(output_path.glob("**/*.htm")) + list(output_path.glob("**/*.html"))
        metadata["files"] = [str(f.relative_to(output_path)) for f in files]
        metadata["total_downloaded"] = len(files)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Downloaded {len(files)} 8-K filing files.")
        return len(files)

    except ImportError:
        print("ERROR: datamule package not installed. Run: pip install datamule")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR downloading 8-K filings: {e}")
        raise


def main():
    args = parse_args()

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        start_date, end_date = get_default_dates()

    count = download_8k_filings(
        start_date=start_date,
        end_date=end_date,
        output_dir=args.output_dir,
        use_provider=args.use_provider,
    )
    print(f"Done. Total filings downloaded: {count}")


if __name__ == "__main__":
    main()
