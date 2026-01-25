#!/usr/bin/env python3
"""Download 8-K filings with cybersecurity disclosures (Item 1.05)."""

import os
import argparse
from datetime import datetime, timedelta
from datamule import Portfolio

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download 8-K filings')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--provider', default='sec', help='Provider (sec or datamule-tar)')
    return parser.parse_args()

def get_date_range(start_date, end_date):
    """Calculate date range for downloads."""
    if not start_date and not end_date:
        # Default: yesterday only for daily runs
        yesterday = datetime.now() - timedelta(days=1)
        return (yesterday.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d'))
    elif start_date and end_date:
        return (start_date, end_date)
    else:
        raise ValueError("Both start_date and end_date must be provided, or neither")

def main():
    """Download 8-K filings."""
    args = parse_args()
    
    # Set up date range
    start_date, end_date = get_date_range(args.start_date, args.end_date)
    print(f"Downloading 8-K filings from {start_date} to {end_date}")
    
    # Configure API key if available
    api_key = os.environ.get('DATAMULE_API_KEY')
    
    # Initialize portfolio
    portfolio = Portfolio('sec_8k_downloads')
    
    if api_key:
        portfolio.set_api_key(api_key)
        print("✓ Using datamule API key")
    
    # Download 8-K filings
    # Note: We download all 8-K filings, then filter for Item 1.05 during parsing
    print("Downloading 8-K filings...")
    portfolio.download_submissions(
        submission_type='8-K',
        filing_date=(start_date, end_date),
        provider=args.provider,
        requests_per_second=7 if args.provider == 'sec' else None,
        skip_existing=True
    )
    
    print(f"✓ Download complete. Files stored in: {portfolio.portfolio_dir}")
    
    # Write metadata for downstream parsing
    with open('.github/outputs/download_metadata.txt', 'w') as f:
        f.write(f"portfolio_dir={portfolio.portfolio_dir}\n")
        f.write(f"start_date={start_date}\n")
        f.write(f"end_date={end_date}\n")
        f.write(f"filing_type=8-K\n")

if __name__ == '__main__':
    os.makedirs('.github/outputs', exist_ok=True)
    main()