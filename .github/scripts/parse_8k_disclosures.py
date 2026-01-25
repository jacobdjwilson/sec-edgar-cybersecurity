#!/usr/bin/env python3
"""Parse 8-K filings to extract Item 1.05 cybersecurity disclosures."""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from datamule import Portfolio, Filing
from bs4 import BeautifulSoup
import html2text

def extract_filing_metadata(submission):
    """Extract metadata from submission."""
    try:
        metadata = submission.metadata
        return {
            'cik': metadata.get('cik', '').lstrip('0') or metadata.get('cik', 'unknown'),
            'ticker': metadata.get('ticker', 'unknown').upper(),
            'company_name': metadata.get('name', 'Unknown Company'),
            'filing_date': metadata.get('filing_date', 'unknown'),
            'accession_number': metadata.get('accession_number', 'unknown'),
        }
    except Exception as e:
        print(f"Warning: Could not extract metadata: {e}")
        return None

def extract_item_105(filing_text):
    """Extract Item 1.05 content from 8-K filing."""
    # Try multiple patterns for Item 1.05
    patterns = [
        r'Item\s+1\.05[^\n]*Material\s+Cybersecurity\s+Incidents[^\n]*(.*?)(?=Item\s+\d+\.\d+|Item\s+\d+|$)',
        r'Item\s+1\.05[:\.]?\s*(.*?)(?=Item\s+\d+\.\d+|Item\s+\d+|$)',
        r'<ITEM>1\.05</ITEM>(.*?)(?=<ITEM>|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            if len(content) > 50:  # Ensure we got actual content
                return content
    
    return None

def html_to_markdown(html_content):
    """Convert HTML to clean markdown."""
    # Use html2text for conversion
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    
    # Clean up HTML first
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style tags
    for tag in soup(['script', 'style']):
        tag.decompose()
    
    markdown = h.handle(str(soup))
    
    # Clean up excessive whitespace
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = markdown.strip()
    
    return markdown

def create_markdown_file(metadata, content, output_dir):
    """Create markdown file with YAML frontmatter."""
    # Determine quarter
    filing_date = metadata['filing_date']
    try:
        date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
        year = date_obj.year
        quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
    except:
        year = 'unknown'
        quarter = 'unknown'
    
    # Create directory structure: data/8K/YEAR/QUARTER/
    dir_path = Path(output_dir) / str(year) / quarter
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create filename: CIK_DATE_8K.md
    filename = f"{metadata['cik']}_{filing_date}_8K.md"
    filepath = dir_path / filename
    
    # Create YAML frontmatter
    frontmatter = {
        'ticker': metadata['ticker'],
        'company_name': metadata['company_name'],
        'cik': metadata['cik'],
        'filing_date': filing_date,
        'filing_type': '8-K',
        'item': '1.05',
        'accession_number': metadata['accession_number'],
        'source_link': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={metadata['cik']}&type=8-K&dateb=&owner=exclude&count=100",
    }
    
    # Write markdown file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n')
        f.write('## Item 1.05. Material Cybersecurity Incidents\n\n')
        f.write(content)
        f.write('\n')
    
    print(f"✓ Created: {filepath}")
    return filepath

def main():
    """Parse 8-K filings for Item 1.05 disclosures."""
    # Read download metadata
    metadata_file = '.github/outputs/download_metadata.txt'
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            lines = f.readlines()
            portfolio_dir = [l.split('=')[1].strip() for l in lines if l.startswith('portfolio_dir=')][0]
    else:
        portfolio_dir = 'sec_8k_downloads'
    
    print(f"Processing portfolio: {portfolio_dir}")
    
    # Initialize portfolio
    portfolio = Portfolio(portfolio_dir)
    
    # Track statistics
    total_filings = 0
    item_105_found = 0
    
    # Process each submission
    for submission in portfolio:
        total_filings += 1
        
        try:
            # Extract metadata
            metadata = extract_filing_metadata(submission)
            if not metadata:
                continue
            
            print(f"Processing: {metadata['ticker']} ({metadata['filing_date']})")
            
            # Get filing content
            # Try to get the primary document
            primary_doc = None
            for document in submission.documents:
                if document.document_type == '8-K':
                    primary_doc = document
                    break
            
            if not primary_doc:
                print(f"  ✗ No 8-K document found")
                continue
            
            # Read filing content
            try:
                with open(primary_doc.path, 'r', encoding='utf-8', errors='ignore') as f:
                    filing_text = f.read()
            except Exception as e:
                print(f"  ✗ Error reading file: {e}")
                continue
            
            # Extract Item 1.05
            item_105_content = extract_item_105(filing_text)
            
            if item_105_content:
                # Convert to markdown if it's HTML
                if '<' in item_105_content and '>' in item_105_content:
                    item_105_content = html_to_markdown(item_105_content)
                
                # Create markdown file
                create_markdown_file(metadata, item_105_content, 'data/8K')
                item_105_found += 1
                print(f"  ✓ Found Item 1.05 disclosure")
            else:
                print(f"  - No Item 1.05 content found")
                
        except Exception as e:
            print(f"  ✗ Error processing submission: {e}")
            continue
    
    # Write summary
    print(f"\n{'='*60}")
    print(f"Total 8-K filings processed: {total_filings}")
    print(f"Item 1.05 disclosures found: {item_105_found}")
    print(f"{'='*60}")
    
    with open('.github/outputs/parse_8k_summary.txt', 'w') as f:
        f.write(f"total_filings={total_filings}\n")
        f.write(f"item_105_found={item_105_found}\n")

if __name__ == '__main__':
    os.makedirs('.github/outputs', exist_ok=True)
    main()