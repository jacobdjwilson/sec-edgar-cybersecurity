#!/usr/bin/env python3
"""
Convert parsed SEC filings to Markdown format for Hugo v0.146.0.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarkdownConverter:
    """Convert parsed filings to Markdown with Hugo frontmatter."""
    
    def __init__(self):
        self.parsed_data_dir = Path('parsed_data')
        self.output_dir = Path('data')
        self.output_dir.mkdir(exist_ok=True)
    
    def clean_text(self, text: str) -> str:
        """Clean and format text for Markdown."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove page numbers and headers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Clean up common artifacts
        text = text.replace('', "'")
        text = text.replace('', '"')
        text = text.replace('', '"')
        text = text.replace('', '--')
        
        return text.strip()
    
    def create_hugo_frontmatter(self, section: Dict) -> str:
        """Create Hugo v0.146.0 compatible frontmatter."""
        info = section['filing_info']
        
        # Parse date
        filing_date = datetime.strptime(info['filing_date'], '%Y-%m-%d')
        
        # Create frontmatter
        frontmatter = f"""---
title: "{info['company_name']} - {section['title']}"
date: {info['filing_date']}
ticker: {info['ticker']}
cik: "{info['cik']}"
filing_type: {info['filing_type']}
section: "{section['section']}"
accession_number: "{info['accession_number']}"
source_link: "{info['source_url']}"
draft: false
tags:
  - cybersecurity
  - sec-filing
  - {info['filing_type'].lower()}
categories:
  - SEC Disclosures
---
"""
        return frontmatter
    
    def format_content(self, content: str, section_title: str) -> str:
        """Format content as Markdown."""
        content = self.clean_text(content)
        
        # Add section header
        markdown = f"## {section_title}\n\n"
        markdown += content
        
        return markdown
    
    def convert_to_markdown(self, section: Dict) -> str:
        """Convert a parsed section to Markdown with Hugo frontmatter."""
        frontmatter = self.create_hugo_frontmatter(section)
        content = self.format_content(section['content'], section['title'])
        
        return frontmatter + '\n' + content
    
    def save_markdown(self, markdown: str, section: Dict):
        """Save Markdown file to data directory."""
        info = section['filing_info']
        filing_type = info['filing_type']
        filing_date = datetime.strptime(info['filing_date'], '%Y-%m-%d')
        
        year = filing_date.year
        quarter = f"Q{(filing_date.month - 1) // 3 + 1}"
        
        # Create directory structure
        save_dir = self.output_dir / filing_type / str(year) / quarter
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        section_name = section['section'].replace('(', '').replace(')', '').replace(' ', '_')
        filename = f"{info['cik']}_{info['filing_date']}_{filing_type}_{section_name}.md"
        filepath = save_dir / filename
        
        # Save markdown
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        logger.info(f"Saved Markdown to {filepath}")
    
    def run(self):
        """Convert all parsed filings to Markdown."""
        logger.info("Starting Markdown conversion")
        
        # Find all JSON files in parsed_data
        json_files = list(self.parsed_data_dir.rglob('*.json'))
        
        logger.info(f"Found {len(json_files)} parsed sections to convert")
        
        for filepath in json_files:
            try:
                with open(filepath, 'r') as f:
                    section = json.load(f)
                
                markdown = self.convert_to_markdown(section)
                self.save_markdown(markdown, section)
                
            except Exception as e:
                logger.error(f"Error converting {filepath}: {e}")
        
        logger.info("Markdown conversion complete")


def main():
    converter = MarkdownConverter()
    converter.run()


if __name__ == '__main__':
    main()