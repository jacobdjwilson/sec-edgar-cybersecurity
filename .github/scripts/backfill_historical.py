#!/usr/bin/env python3
"""Backfill historical SEC filings."""

import os
import argparse
from datetime import datetime
from datamule import Portfolio

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Backfill historical data')
    parser.add_argument('--start-year', required=True, type=int)
    parser.add_argument('--end-year', required=True, type=int)
    parser.add_argument('--filing-type', required=True, choices=['8-K', '10-K', 'both'])
    parser.add_argument('--use-datamule-provider', type=bool, default=False)
    return parser.parse_args()

def backfill_filings(start_year, end_year, filing_type, use_datamule):
    """Backfill filings for date range."""
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    
    provider = 'datamule-tar' if use_datamule else 'sec'
    
    print(f"Backfilling {filing_type} from {start_date} to {end_date}")
    print(f"Using provider: {provider}")
    
    # Configure API key if using datamule
    api_key = os.environ.get('DATAMULE_API_KEY')
    if use_datamule and not api_key:
        raise ValueError("DATAMULE_API_KEY required when using datamule provider")
    
    # Process 8-K filings
    if filing_type in ['8-K', 'both']:
        print("\n" + "="*60)
        print("Processing 8-K filings...")
        print("="*60)
        
        portfolio = Portfolio(f'backfill_8k_{start_year}_{end_year}')
        if api_key:
            portfolio.set_api_key(api_key)
        
        portfolio.download_submissions(
            submission_type='8-K',
            filing_date=(start_date, end_date),
            provider=provider,
            requests_per_second=7 if provider == 'sec' else None,
            skip_existing=True
        )
        
        print(f"✓ 8-K download complete")
        
        # Parse 8-K filings
        os.system(f'python .github/scripts/parse_8k_disclosures.py')
    
    # Process 10-K filings
    if filing_type in ['10-K', 'both']:
        print("\n" + "="*60)
        print("Processing 10-K filings...")
        print("="*60)
        
        portfolio = Portfolio(f'backfill_10k_{start_year}_{end_year}')
        if api_key:
            portfolio.set_api_key(api_key)
        
        portfolio.download_submissions(
            submission_type='10-K',
            filing_date=(start_date, end_date),
            provider=provider,
            requests_per_second=7 if provider == 'sec' else None,
            skip_existing=True
        )
        
        print(f"✓ 10-K download complete")
        
        # Parse 10-K filings
        os.system(f'python .github/scripts/parse_10k_disclosures.py')

def main():
    """Run backfill."""
    args = parse_args()
    
    backfill_filings(
        args.start_year,
        args.end_year,
        args.filing_type,
        args.use_datamule_provider
    )
    
    print("\n" + "="*60)
    print("✓ Backfill complete!")
    print("="*60)

if __name__ == '__main__':
    main()