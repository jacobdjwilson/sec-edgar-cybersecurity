#!/usr/bin/env python3
"""
Ingest SEC filings using datamule.
Downloads 8-K and 10-K filings and parses cybersecurity disclosures.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Import from datamule - use Portfolio, not Edgar
from datamule import Portfolio

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Ingest SEC filings')
    parser.add_argument('--filing-type', 
                        choices=['8-K', '10-K', 'both'], 
                        default='both',
                        help='Type of filing to ingest')
    parser.add_argument('--start-date', 
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', 
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--lookback-days', 
                        type=int, 
                        default=1,
                        help='Number of days to look back (if dates not specified)')
    parser.add_argument('--provider',
                        choices=['sec', 'datamule-tar'],
                        default='sec',
                        help='Data provider to use')
    return parser.parse_args()

def get_date_range(start_date, end_date, lookback_days):
    """Calculate date range for downloads."""
    if start_date and end_date:
        return (start_date, end_date)
    else:
        # Use lookback days from today
        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

def setup_api_key():
    """Configure datamule API key if available."""
    api_key = os.environ.get('DATAMULE_API_KEY')
    if api_key:
        print("✓ DATAMULE_API_KEY found")
        return api_key
    else:
        print("⚠ DATAMULE_API_KEY not set. Using SEC rate-limited endpoints.")
        return None

def download_filings(filing_type, start_date, end_date, provider, api_key):
    """Download filings from SEC EDGAR."""
    print(f"\n{'='*60}")
    print(f"Downloading {filing_type} filings")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Provider: {provider}")
    print(f"{'='*60}\n")
    
    # Create portfolio
    portfolio_name = f"sec_{filing_type.lower().replace('-', '')}_downloads"
    portfolio = Portfolio(portfolio_name)
    
    # Set API key if available
    if api_key and hasattr(portfolio, 'set_api_key'):
        portfolio.set_api_key(api_key)
    
    try:
        # Download submissions
        portfolio.download_submissions(
            submission_type=filing_type,
            filing_date=(start_date, end_date),
            provider=provider,
            requests_per_second=7 if provider == 'sec' else None,
            skip_existing=True
        )
        
        print(f"✓ Successfully downloaded {filing_type} filings")
        return portfolio_name
        
    except Exception as e:
        print(f"✗ Error downloading {filing_type} filings: {e}", file=sys.stderr)
        raise

def main():
    """Main ingestion function."""
    args = parse_args()
    
    # Get date range
    start_date, end_date = get_date_range(
        args.start_date, 
        args.end_date, 
        args.lookback_days
    )
    
    print(f"SEC EDGAR Cybersecurity Filings Ingestion")
    print(f"Date Range: {start_date} to {end_date}")
    
    # Setup API key
    api_key = setup_api_key()
    
    # Create outputs directory
    os.makedirs('.github/outputs', exist_ok=True)
    
    # Track what was downloaded
    downloaded = []
    
    try:
        # Download 8-K filings
        if args.filing_type in ['8-K', 'both']:
            portfolio_dir = download_filings('8-K', start_date, end_date, args.provider, api_key)
            downloaded.append(('8-K', portfolio_dir))
            
            # Write metadata for parsing
            with open('.github/outputs/download_metadata_8k.txt', 'w') as f:
                f.write(f"portfolio_dir={portfolio_dir}\n")
                f.write(f"start_date={start_date}\n")
                f.write(f"end_date={end_date}\n")
                f.write(f"filing_type=8-K\n")
        
        # Download 10-K filings
        if args.filing_type in ['10-K', 'both']:
            portfolio_dir = download_filings('10-K', start_date, end_date, args.provider, api_key)
            downloaded.append(('10-K', portfolio_dir))
            
            # Write metadata for parsing
            with open('.github/outputs/download_metadata_10k.txt', 'w') as f:
                f.write(f"portfolio_dir={portfolio_dir}\n")
                f.write(f"start_date={start_date}\n")
                f.write(f"end_date={end_date}\n")
                f.write(f"filing_type=10-K\n")
        
        # Write summary
        print(f"\n{'='*60}")
        print("✓ Ingestion completed successfully")
        print(f"Downloaded: {', '.join([f[0] for f in downloaded])}")
        print(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ Ingestion failed: {e}")
        print(f"{'='*60}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())