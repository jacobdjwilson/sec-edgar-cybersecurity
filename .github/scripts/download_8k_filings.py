#!/usr/bin/env python3
"""Download 8-K filings with cybersecurity disclosures (Item 1.05)."""

import os
import sys
import argparse
from datetime import datetime, timedelta
from datamule import Portfolio

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download 8-K filings')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)', default='')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)', default='')
    parser.add_argument('--provider', default='datamule', help='Provider (sec or datamule)')
    return parser.parse_args()

def get_date_range(start_date, end_date):
    """Calculate date range for downloads."""
    # Clean up: handle None, empty strings, and whitespace
    start_date = str(start_date).strip() if start_date else ''
    end_date = str(end_date).strip() if end_date else ''
    
    # Also handle 'None' string that might come from workflow
    if start_date.lower() == 'none':
        start_date = ''
    if end_date.lower() == 'none':
        end_date = ''
    
    # If both are empty, use yesterday for daily runs
    if not start_date and not end_date:
        yesterday = datetime.now() - timedelta(days=1)
        result = (yesterday.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d'))
        print(f"Using default date range (yesterday): {result[0]} to {result[1]}")
        return result
    
    # If both are provided and non-empty, use them
    if start_date and end_date:
        print(f"Using provided date range: {start_date} to {end_date}")
        return (start_date, end_date)
    
    # If only one is provided, that's an error
    raise ValueError(f"Both start_date and end_date must be provided, or neither. Got start='{start_date}', end='{end_date}'")

def main():
    """Download 8-K filings."""
    args = parse_args()
    
    try:
        # Set up date range
        start_date, end_date = get_date_range(args.start_date, args.end_date)
        print(f"\nDownloading 8-K filings from {start_date} to {end_date}")
        print(f"Provider: {args.provider}\n")
        
        # Configure API key if available
        api_key = os.environ.get('DATAMULE_API_KEY')
        
        # Initialize portfolio
        portfolio_name = 'sec_8k_downloads'
        portfolio = Portfolio(portfolio_name)
        
        if api_key:
            print("✓ DATAMULE_API_KEY found")
        else:
            print("⚠ DATAMULE_API_KEY not set, using SEC rate limits")
        
        # Download 8-K filings
        # Note: We download all 8-K filings, then filter for Item 1.05 during parsing
        print("Downloading 8-K filings...")
        
        portfolio.download_submissions(
            submission_type='8-K',
            filing_date=(start_date, end_date),
            provider=args.provider,
            skip_existing=True
        )
        
        # Use the portfolio name instead of portfolio_dir attribute
        print(f"✓ Download complete. Files stored in: {portfolio_name}")
        
        # Write metadata for downstream parsing
        os.makedirs('.github/outputs', exist_ok=True)
        with open('.github/outputs/download_metadata.txt', 'w') as f:
            f.write(f"portfolio_dir={portfolio_name}\n")
            f.write(f"start_date={start_date}\n")
            f.write(f"end_date={end_date}\n")
            f.write(f"filing_type=8-K\n")
        
        print("✓ Metadata written successfully")
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()