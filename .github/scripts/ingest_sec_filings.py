#!/usr/bin/env python3
"""
Ingest SEC cybersecurity disclosure filings using datamule API.
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

from datamule import Portfolio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SECFilingIngestor:
    """Ingest SEC filings related to cybersecurity disclosures."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the ingestor with datamule API key."""
        self.api_key = api_key or os.getenv('DATAMULE_API_KEY')
        
        # Use datamule provider if API key is available, otherwise use SEC
        self.provider = 'datamule' if self.api_key else 'sec'
        
        # Initialize downloader
        self.downloader = Portfolio('sec-edgar-cybersecurity')
        if self.api_key:
            self.downloader.set_api_key(self.api_key)
        else:
            logger.warning("No API key provided. Using SEC provider with rate limits.")
        
        # Create directories
        self.raw_data_dir = Path('raw_data')
        self.raw_data_dir.mkdir(exist_ok=True)
        
        self.metadata_file = Path('raw_data/metadata.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load existing metadata or create new."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'processed_filings': [], 'last_run': None}
    
    def _save_metadata(self):
        """Save metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_date_range(self, manual: bool = False) -> tuple:
        """Determine the date range for filing search."""
        if manual:
            # Use environment variables for manual runs
            start_date = os.getenv('START_DATE')
            end_date = os.getenv('END_DATE')
            
            if start_date and end_date:
                return start_date, end_date
            elif start_date:
                return start_date, datetime.now().strftime('%Y-%m-%d')
        
        # For daily runs, check last 2 days to catch any delayed filings
        last_run = self.metadata.get('last_run')
        if last_run:
            start_date = datetime.fromisoformat(last_run) - timedelta(days=2)
        else:
            # First run - get filings from when rules took effect (2023-12-18)
            start_date = datetime(2023, 12, 15)
        
        end_date = datetime.now()
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def search_8k_item_105(self, start_date: str, end_date: str, 
                           ticker: Optional[str] = None) -> List[Dict]:
        """Search for 8-K filings with Item 1.05 (Material Cybersecurity Incidents)."""
        logger.info(f"Searching for 8-K Item 1.05 filings from {start_date} to {end_date}")
        
        try:
            # Download 8-K filings
            params = {
                'submission_type': '8-K',
                'start_date': start_date,
                'end_date': end_date,
            }
            
            if ticker:
                params['ticker'] = ticker
            
            filings = self.downloader.download_submissions(**params)
            
            # Filter for Item 1.05
            item_105_filings = []
            for filing in filings:
                # Download the filing content to check for Item 1.05
                content = self.downloader.get_submission_content(
                    filing['accession_number']
                )
                
                # Check if Item 1.05 is present
                if 'Item 1.05' in content or 'item 1.05' in content.lower():
                    item_105_filings.append({
                        'cik': filing['cik'],
                        'company_name': filing['company_name'],
                        'ticker': filing.get('ticker', 'N/A'),
                        'accession_number': filing['accession_number'],
                        'filing_date': filing['filing_date'],
                        'filing_type': '8-K',
                        'content': content,
                        'source_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing['cik']}&type=8-K&dateb=&owner=exclude&count=100"
                    })
                    logger.info(f"Found 8-K Item 1.05 filing for {filing.get('ticker', filing['cik'])}")
            
            return item_105_filings
        
        except Exception as e:
            logger.error(f"Error searching 8-K filings: {e}")
            return []
    
    def search_10k_cybersecurity(self, start_date: str, end_date: str,
                                 ticker: Optional[str] = None) -> List[Dict]:
        """Search for 10-K filings with cybersecurity disclosures (Item 106, 407j)."""
        logger.info(f"Searching for 10-K cybersecurity filings from {start_date} to {end_date}")
        
        try:
            params = {
                'submission_type': '10-K',
                'start_date': start_date,
                'end_date': end_date,
            }
            
            if ticker:
                params['ticker'] = ticker
            
            filings = self.downloader.download_submissions(**params)
            
            cyber_filings = []
            for filing in filings:
                content = self.downloader.get_submission_content(
                    filing['accession_number']
                )
                
                # Check for Item 106 (Risk Management) or Item 407(j) (Governance)
                has_item_106 = 'Item 106' in content or 'item 106' in content.lower()
                has_item_407j = 'Item 407(j)' in content or 'item 407(j)' in content.lower()
                
                if has_item_106 or has_item_407j:
                    cyber_filings.append({
                        'cik': filing['cik'],
                        'company_name': filing['company_name'],
                        'ticker': filing.get('ticker', 'N/A'),
                        'accession_number': filing['accession_number'],
                        'filing_date': filing['filing_date'],
                        'filing_type': '10-K',
                        'content': content,
                        'has_item_106': has_item_106,
                        'has_item_407j': has_item_407j,
                        'source_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing['cik']}&type=10-K&dateb=&owner=exclude&count=100"
                    })
                    logger.info(f"Found 10-K cybersecurity filing for {filing.get('ticker', filing['cik'])}")
            
            return cyber_filings
        
        except Exception as e:
            logger.error(f"Error searching 10-K filings: {e}")
            return []
    
    def save_filing(self, filing: Dict):
        """Save filing to raw data directory."""
        filing_type = filing['filing_type']
        filing_date = datetime.strptime(filing['filing_date'], '%Y-%m-%d')
        year = filing_date.year
        quarter = f"Q{(filing_date.month - 1) // 3 + 1}"
        
        # Create directory structure
        save_dir = self.raw_data_dir / filing_type / str(year) / quarter
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{filing['cik']}_{filing['filing_date']}_{filing_type}.json"
        filepath = save_dir / filename
        
        # Save filing
        with open(filepath, 'w') as f:
            json.dump(filing, f, indent=2)
        
        logger.info(f"Saved filing to {filepath}")
        
        # Update metadata
        filing_id = f"{filing['cik']}_{filing['accession_number']}"
        if filing_id not in self.metadata['processed_filings']:
            self.metadata['processed_filings'].append(filing_id)
    
    def run(self, manual: bool = False):
        """Run the ingestion process."""
        logger.info("Starting SEC cybersecurity disclosure ingest")
        
        start_date, end_date = self.get_date_range(manual)
        logger.info(f"Date range: {start_date} to {end_date}")
        
        ticker = os.getenv('TICKER') if manual else None
        filing_type = os.getenv('FILING_TYPE', 'ALL') if manual else 'ALL'
        
        new_filings = 0
        
        # Search for 8-K filings
        if filing_type in ['8-K', 'ALL']:
            filings_8k = self.search_8k_item_105(start_date, end_date, ticker)
            for filing in filings_8k:
                filing_id = f"{filing['cik']}_{filing['accession_number']}"
                if filing_id not in self.metadata['processed_filings']:
                    self.save_filing(filing)
                    new_filings += 1
        
        # Search for 10-K filings
        if filing_type in ['10-K', 'ALL']:
            filings_10k = self.search_10k_cybersecurity(start_date, end_date, ticker)
            for filing in filings_10k:
                filing_id = f"{filing['cik']}_{filing['accession_number']}"
                if filing_id not in self.metadata['processed_filings']:
                    self.save_filing(filing)
                    new_filings += 1
        
        # Update last run time
        self.metadata['last_run'] = datetime.now().isoformat()
        self._save_metadata()
        
        logger.info(f"Ingest complete. New filings: {new_filings}")


def main():
    parser = argparse.ArgumentParser(description='Ingest SEC cybersecurity disclosures')
    parser.add_argument('--manual', action='store_true', help='Manual run with environment variables')
    args = parser.parse_args()
    
    ingestor = SECFilingIngestor()
    ingestor.run(manual=args.manual)


if __name__ == '__main__':
    main()