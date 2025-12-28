#!/usr/bin/env python3
"""
Parse SEC filings to extract cybersecurity-related sections.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SECFilingParser:
    """Parse SEC filings to extract relevant sections."""
    
    def __init__(self):
        self.raw_data_dir = Path('raw_data')
        self.parsed_data_dir = Path('parsed_data')
        self.parsed_data_dir.mkdir(exist_ok=True)
    
    def extract_item_105(self, content: str, filing_info: Dict) -> Optional[Dict]:
        """Extract Item 1.05 from 8-K filings."""
        soup = BeautifulSoup(content, 'lxml')
        
        # Try multiple patterns to find Item 1.05
        patterns = [
            r'Item\s+1\.05[:\s]+Material\s+Cybersecurity\s+Incidents?',
            r'ITEM\s+1\.05[:\s]+MATERIAL\s+CYBERSECURITY\s+INCIDENTS?',
            r'Item\s+1\.05',
        ]
        
        for pattern in patterns:
            # Search in text
            text = soup.get_text()
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                start_pos = match.start()
                
                # Find the next item to determine end position
                next_item_match = re.search(
                    r'Item\s+\d+\.\d+',
                    text[start_pos + len(match.group()):],
                    re.IGNORECASE
                )
                
                if next_item_match:
                    end_pos = start_pos + len(match.group()) + next_item_match.start()
                else:
                    # Take next 5000 characters if no next item found
                    end_pos = min(start_pos + 5000, len(text))
                
                section_text = text[start_pos:end_pos].strip()
                
                return {
                    'section': 'Item 1.05',
                    'title': 'Material Cybersecurity Incidents',
                    'content': section_text,
                    'filing_info': filing_info
                }
        
        logger.warning(f"Could not extract Item 1.05 from filing {filing_info['accession_number']}")
        return None
    
    def extract_item_106(self, content: str, filing_info: Dict) -> Optional[Dict]:
        """Extract Item 106 from 10-K filings."""
        soup = BeautifulSoup(content, 'lxml')
        text = soup.get_text()
        
        patterns = [
            r'Item\s+106[:\s]+Cybersecurity',
            r'ITEM\s+106[:\s]+CYBERSECURITY',
            r'Item\s+106',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                start_pos = match.start()
                
                # Find next item or take 10000 characters
                next_item_match = re.search(
                    r'Item\s+\d+[A-Z]?\.',
                    text[start_pos + len(match.group()):],
                    re.IGNORECASE
                )
                
                if next_item_match:
                    end_pos = start_pos + len(match.group()) + next_item_match.start()
                else:
                    end_pos = min(start_pos + 10000, len(text))
                
                section_text = text[start_pos:end_pos].strip()
                
                return {
                    'section': 'Item 106',
                    'title': 'Cybersecurity',
                    'content': section_text,
                    'filing_info': filing_info
                }
        
        return None
    
    def extract_item_407j(self, content: str, filing_info: Dict) -> Optional[Dict]:
        """Extract Item 407(j) from 10-K filings."""
        soup = BeautifulSoup(content, 'lxml')
        text = soup.get_text()
        
        patterns = [
            r'Item\s+407\(j\)',
            r'ITEM\s+407\(J\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                start_pos = match.start()
                
                # Find next item
                next_item_match = re.search(
                    r'Item\s+\d+',
                    text[start_pos + len(match.group()):],
                    re.IGNORECASE
                )
                
                if next_item_match:
                    end_pos = start_pos + len(match.group()) + next_item_match.start()
                else:
                    end_pos = min(start_pos + 8000, len(text))
                
                section_text = text[start_pos:end_pos].strip()
                
                return {
                    'section': 'Item 407(j)',
                    'title': 'Cybersecurity Governance',
                    'content': section_text,
                    'filing_info': filing_info
                }
        
        return None
    
    def parse_filing(self, filepath: Path) -> List[Dict]:
        """Parse a single filing and extract relevant sections."""
        logger.info(f"Parsing {filepath}")
        
        with open(filepath, 'r') as f:
            filing = json.load(f)
        
        sections = []
        
        filing_info = {
            'cik': filing['cik'],
            'company_name': filing['company_name'],
            'ticker': filing['ticker'],
            'filing_date': filing['filing_date'],
            'filing_type': filing['filing_type'],
            'accession_number': filing['accession_number'],
            'source_url': filing['source_url']
        }
        
        if filing['filing_type'] == '8-K':
            section = self.extract_item_105(filing['content'], filing_info)
            if section:
                sections.append(section)
        
        elif filing['filing_type'] == '10-K':
            if filing.get('has_item_106'):
                section = self.extract_item_106(filing['content'], filing_info)
                if section:
                    sections.append(section)
            
            if filing.get('has_item_407j'):
                section = self.extract_item_407j(filing['content'], filing_info)
                if section:
                    sections.append(section)
        
        return sections
    
    def save_parsed_sections(self, sections: List[Dict], original_filepath: Path):
        """Save parsed sections to JSON files."""
        for section in sections:
            filing_type = section['filing_info']['filing_type']
            filing_date = section['filing_info']['filing_date']
            cik = section['filing_info']['cik']
            
            # Determine save path
            relative_path = original_filepath.relative_to(self.raw_data_dir)
            save_dir = self.parsed_data_dir / relative_path.parent
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename
            section_name = section['section'].replace('(', '').replace(')', '').replace(' ', '_')
            filename = f"{cik}_{filing_date}_{filing_type}_{section_name}.json"
            save_path = save_dir / filename
            
            with open(save_path, 'w') as f:
                json.dump(section, f, indent=2)
            
            logger.info(f"Saved parsed section to {save_path}")
    
    def run(self):
        """Parse all raw filings."""
        logger.info("Starting parsing process")
        
        # Find all JSON files in raw_data
        json_files = list(self.raw_data_dir.rglob('*.json'))
        
        # Exclude metadata.json
        json_files = [f for f in json_files if f.name != 'metadata.json']
        
        logger.info(f"Found {len(json_files)} filings to parse")
        
        for filepath in json_files:
            try:
                sections = self.parse_filing(filepath)
                if sections:
                    self.save_parsed_sections(sections, filepath)
            except Exception as e:
                logger.error(f"Error parsing {filepath}: {e}")
        
        logger.info("Parsing complete")


def main():
    parser = SECFilingParser()
    parser.run()


if __name__ == '__main__':
    main()