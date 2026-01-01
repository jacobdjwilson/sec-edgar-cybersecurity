#!/usr/bin/env python3
"""
Monitor SEC EDGAR for new cybersecurity disclosures.
Focuses on 8-K Item 1.05 and 10-K Items 106/407j per 2023 SEC rules.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import logging
from dataclasses import dataclass

from datamule import Downloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    """Company metadata"""
    name: str
    cik: str
    ticker: Optional[str]
    website: Optional[str]
    sic: Optional[str]
    sic_description: Optional[str]


class CybersecurityMonitor:
    """Monitor and parse SEC cybersecurity disclosures"""
    
    # Target SEC items per 2023 cybersecurity rules
    TARGET_ITEMS_8K = ['1.05']  # Material Cybersecurity Incidents
    TARGET_ITEMS_10K = ['106', '407j']  # Risk Management & Governance
    
    def __init__(self, output_dir: str = 'data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize datamule downloader
        self.downloader = Downloader()
        
        # Set SEC-compliant headers
        user_agent = os.getenv('SEC_USER_AGENT', 'SEC-Monitor github-actions@example.com')
        self.downloader.set_headers(user_agent)
        
        logger.info("Initialized CybersecurityMonitor")
    
    def get_company_info(self, cik: str) -> CompanyInfo:
        """Fetch company information from SEC"""
        try:
            # Datamule provides company info via submissions
            submission = self.downloader.get_company_submissions(cik=cik)
            
            return CompanyInfo(
                name=submission.get('name', 'Unknown'),
                cik=cik,
                ticker=submission.get('tickers', [''])[0] if submission.get('tickers') else None,
                website=submission.get('website'),
                sic=submission.get('sicCode'),
                sic_description=submission.get('sicDescription')
            )
        except Exception as e:
            logger.warning(f"Could not fetch company info for CIK {cik}: {e}")
            return CompanyInfo(name='Unknown', cik=cik, ticker=None, website=None, sic=None, sic_description=None)
    
    def parse_8k_cybersecurity(self, filing_content: str, filing_url: str) -> Optional[Dict]:
        """Parse 8-K for Item 1.05 cybersecurity incidents"""
        try:
            from datamule import Filing
            
            filing = Filing(filing_content, filing_type='8-K')
            parsed = filing.parse()
            
            # Look for Item 1.05
            if 'item105' in parsed or 'item1.05' in parsed:
                item_key = 'item105' if 'item105' in parsed else 'item1.05'
                return {
                    'section_title': 'Item 1.05. Material Cybersecurity Incidents',
                    'content': parsed[item_key],
                    'category': '8-K Material Incident'
                }
            
            logger.debug(f"No Item 1.05 found in 8-K: {filing_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing 8-K: {e}")
            return None
    
    def parse_10k_cybersecurity(self, filing_content: str, filing_url: str) -> Optional[Dict]:
        """Parse 10-K for Items 106 and 407j cybersecurity disclosures"""
        try:
            from datamule import Filing
            
            filing = Filing(filing_content, filing_type='10-K')
            parsed = filing.parse()
            
            results = {}
            
            # Item 106 - Risk Management & Strategy
            if 'item106' in parsed:
                results['item106'] = {
                    'section_title': 'Item 106. Cybersecurity Risk Management & Strategy',
                    'content': parsed['item106'],
                    'category': '10-K Risk Management'
                }
            
            # Item 407j - Governance
            if 'item407j' in parsed:
                results['item407j'] = {
                    'section_title': 'Item 407(j). Cybersecurity Governance',
                    'content': parsed['item407j'],
                    'category': '10-K Governance'
                }
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Error parsing 10-K: {e}")
            return None
    
    def create_markdown_file(
        self,
        company_info: CompanyInfo,
        filing_metadata: Dict,
        parsed_content: Dict,
        filing_type: str
    ):
        """Create markdown file with YAML frontmatter"""
        
        filing_date = filing_metadata['filingDate']
        date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
        year = date_obj.year
        quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
        
        # Determine output path
        output_path = self.output_dir / filing_type / str(year) / quarter
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{company_info.cik}_{filing_date}_{filing_type}.md"
        filepath = output_path / filename
        
        # Prepare YAML frontmatter
        frontmatter = {
            'name': company_info.name,
            'ticker': company_info.ticker or 'N/A',
            'website': company_info.website or 'N/A',
            'category': parsed_content.get('category', filing_type),
            'CIK': company_info.cik,
            'SIC': company_info.sic_description or 'N/A',
            'filing_number': filing_metadata.get('accessionNumber'),
            'date': filing_date,
            'filing_type': filing_type,
            'filing_quarter': quarter,
            'filing_year': year,
            'source_link': filing_metadata.get('primaryDocument', 'N/A')
        }
        
        # Write markdown file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(frontmatter, f, default_flow_style=False, sort_keys=False)
            f.write('---\n\n')
            f.write(f"## {parsed_content['section_title']}\n\n")
            f.write(parsed_content['content'])
            f.write('\n')
        
        logger.info(f"Created: {filepath}")
        return filepath
    
    def monitor(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Monitor for new cybersecurity filings"""
        
        # Default to yesterday if no dates provided
        if not start_date:
            yesterday = datetime.now() - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')
        
        if not end_date:
            end_date = start_date
        
        logger.info(f"Monitoring SEC filings from {start_date} to {end_date}")
        
        processed_count = 0
        
        # Monitor 8-K filings for Item 1.05
        logger.info("Checking 8-K filings for Item 1.05...")
        try:
            filings_8k = self.downloader.download(
                form='8-K',
                date=start_date,
                return_urls=True
            )
            
            for filing_url in filings_8k:
                try:
                    # Download filing content
                    filing_content = self.downloader.download_filing(filing_url)
                    
                    # Get filing metadata
                    cik = self.extract_cik_from_url(filing_url)
                    company_info = self.get_company_info(cik)
                    
                    # Parse for cybersecurity content
                    parsed = self.parse_8k_cybersecurity(filing_content, filing_url)
                    
                    if parsed:
                        filing_metadata = {
                            'filingDate': start_date,
                            'accessionNumber': self.extract_accession_from_url(filing_url),
                            'primaryDocument': filing_url
                        }
                        
                        self.create_markdown_file(
                            company_info,
                            filing_metadata,
                            parsed,
                            '8K'
                        )
                        processed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing 8-K {filing_url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error downloading 8-K filings: {e}")
        
        # Monitor 10-K filings for Items 106 and 407j
        logger.info("Checking 10-K filings for Items 106 and 407j...")
        try:
            filings_10k = self.downloader.download(
                form='10-K',
                date=start_date,
                return_urls=True
            )
            
            for filing_url in filings_10k:
                try:
                    filing_content = self.downloader.download_filing(filing_url)
                    
                    cik = self.extract_cik_from_url(filing_url)
                    company_info = self.get_company_info(cik)
                    
                    parsed = self.parse_10k_cybersecurity(filing_content, filing_url)
                    
                    if parsed:
                        filing_metadata = {
                            'filingDate': start_date,
                            'accessionNumber': self.extract_accession_from_url(filing_url),
                            'primaryDocument': filing_url
                        }
                        
                        # Create separate files for each item
                        for item_key, item_content in parsed.items():
                            self.create_markdown_file(
                                company_info,
                                filing_metadata,
                                item_content,
                                '10K'
                            )
                            processed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing 10-K {filing_url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error downloading 10-K filings: {e}")
        
        logger.info(f"Monitoring complete. Processed {processed_count} cybersecurity disclosures.")
        return processed_count
    
    @staticmethod
    def extract_cik_from_url(url: str) -> str:
        """Extract CIK from SEC filing URL"""
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'data' and i + 1 < len(parts):
                return parts[i + 1]
        return ''
    
    @staticmethod
    def extract_accession_from_url(url: str) -> str:
        """Extract accession number from SEC filing URL"""
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'data' and i + 2 < len(parts):
                return parts[i + 2]
        return ''


def main():
    parser = argparse.ArgumentParser(description='Monitor SEC cybersecurity disclosures')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', default='data', help='Output directory')
    
    args = parser.parse_args()
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    monitor = CybersecurityMonitor(output_dir=args.output_dir)
    monitor.monitor(start_date=args.start_date, end_date=args.end_date)


if __name__ == '__main__':
    main()