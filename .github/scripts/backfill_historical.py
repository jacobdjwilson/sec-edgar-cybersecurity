#!/usr/bin/env python3
"""
Backfill historical SEC cybersecurity disclosures.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from monitor_filings import CybersecurityMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Backfill historical cybersecurity disclosures')
    parser.add_argument('--start-year', required=True, type=int, help='Start year')
    parser.add_argument('--end-year', type=int, help='End year (defaults to start year)')
    parser.add_argument('--filing-types', default='8-K,10-K', help='Comma-separated filing types')
    
    args = parser.parse_args()
    
    end_year = args.end_year or args.start_year
    filing_types = [ft.strip() for ft in args.filing_types.split(',')]
    
    logger.info(f"Starting backfill from {args.start_year} to {end_year}")
    logger.info(f"Filing types: {filing_types}")
    
    monitor = CybersecurityMonitor()
    total_processed = 0
    
    for year in range(args.start_year, end_year + 1):
        for quarter in range(1, 5):
            # Calculate quarter date range
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            
            start_date = f"{year}-{start_month:02d}-01"
            
            # Get last day of quarter
            if end_month == 12:
                end_date = f"{year}-12-31"
            else:
                from calendar import monthrange
                last_day = monthrange(year, end_month)[1]
                end_date = f"{year}-{end_month:02d}-{last_day}"
            
            logger.info(f"Processing {year} Q{quarter}: {start_date} to {end_date}")
            
            count = monitor.monitor(start_date=start_date, end_date=end_date)
            total_processed += count
    
    logger.info(f"Backfill complete. Total processed: {total_processed}")


if __name__ == '__main__':
    main()