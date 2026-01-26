#!/usr/bin/env python3
"""Parse 10-K filings to extract Item 106 and Item 407(j) cybersecurity disclosures."""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from datamule import Portfolio
from bs4 import BeautifulSoup
import html2text

def extract_filing_metadata(submission):
    """Extract metadata from submission."""
    try:
        return {
            'cik': getattr(submission, 'cik', 'unknown'),
            'ticker': getattr(submission, 'ticker', 'unknown'),
            'company_name': getattr(submission, 'company_name', 'Unknown Company'),
            'filing_date': getattr(submission, 'filing_date', 'unknown'),
            'accession_number': getattr(submission, 'accession', 'unknown'),
            'fiscal_year_end': getattr(submission, 'period_of_report', 'unknown'),
        }
    except Exception as e:
        print(f"Warning: Could not extract metadata: {e}")
        return None

def extract_item_106(filing_text):
    """Extract Item 106 (Cybersecurity Risk Management) content."""
    patterns = [
        r'Item\s+106[^\n]*Cybersecurity[^\n]*(.*?)(?=Item\s+\d+|ITEM\s+\d+|SIGNATURE|$)',
        r'Item\s+1C[^\n]*Cybersecurity[^\n]*(.*?)(?=Item\s+\d+|ITEM\s+\d+|SIGNATURE|$)',  # Alternative numbering
        r'<ITEM>106</ITEM>(.*?)(?=<ITEM>|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            if len(content) > 100:
                return content
    
    return None

def extract_item_407j(filing_text):
    """Extract Item 407(j) (Cybersecurity Governance) content."""
    patterns = [
        r'Item\s+407\(j\)[^\n]*[^\n]*(.*?)(?=Item\s+\d+|ITEM\s+\d+|SIGNATURE|$)',
        r'Item\s+407\s*\(j\)[^\n]*Cybersecurity[^\n]*(.*?)(?=Item\s+\d+|ITEM\s+\d+|SIGNATURE|$)',
        r'<ITEM>407\(j\)</ITEM>(.*?)(?=<ITEM>|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            if len(content) > 100:
                return content
    
    return None

def html_to_markdown(html_content):
    """Convert HTML to clean markdown."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    for tag in soup(['script', 'style']):
        tag.decompose()
    
    markdown = h.handle(str(soup))
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = markdown.strip()
    
    return markdown

def create_markdown_file(metadata, item_106_content, item_407j_content, output_dir):
    """Create markdown file with both Item 106 and Item 407(j)."""
    # Determine year and quarter from fiscal year end
    fiscal_year_end = metadata.get('fiscal_year_end', metadata['filing_date'])
    try:
        date_obj = datetime.strptime(fiscal_year_end, '%Y-%m-%d')
        year = date_obj.year
        quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
    except:
        try:
            date_obj = datetime.strptime(metadata['filing_date'], '%Y-%m-%d')
            year = date_obj.year
            quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
        except:
            year = 'unknown'
            quarter = 'unknown'
    
    # Create directory structure
    dir_path = Path(output_dir) / str(year) / quarter
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    filename = f"{metadata['cik']}_{metadata['filing_date']}_10K.md"
    filepath = dir_path / filename
    
    # Create YAML frontmatter
    frontmatter = {
        'ticker': metadata['ticker'],
        'company_name': metadata['company_name'],
        'cik': metadata['cik'],
        'filing_date': metadata['filing_date'],
        'fiscal_year_end': metadata['fiscal_year_end'],
        'filing_type': '10-K',
        'items': [],
        'accession_number': metadata['accession_number'],
        'source_link': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={metadata['cik']}&type=10-K&dateb=&owner=exclude&count=100",
    }
    
    if item_106_content:
        frontmatter['items'].append('106')
    if item_407j_content:
        frontmatter['items'].append('407j')
    
    # Write markdown file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n')
        
        if item_106_content:
            f.write('## Item 106. Cybersecurity Risk Management, Strategy, and Governance\n\n')
            f.write(item_106_content)
            f.write('\n\n')
        
        if item_407j_content:
            f.write('## Item 407(j). Board Oversight of Cybersecurity Risk\n\n')
            f.write(item_407j_content)
            f.write('\n')
    
    print(f"✓ Created: {filepath}")
    return filepath

def main():
    """Parse 10-K filings for cybersecurity disclosures."""
    # Read download metadata
    metadata_file = '.github/outputs/download_metadata_10k.txt'
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            lines = f.readlines()
            portfolio_dir = [l.split('=')[1].strip() for l in lines if l.startswith('portfolio_dir=')][0]
    else:
        portfolio_dir = 'sec_10k_downloads'
    
    print(f"Processing portfolio: {portfolio_dir}")
    
    # Initialize portfolio
    portfolio = Portfolio(portfolio_dir)
    
    # Track statistics
    total_filings = 0
    item_106_found = 0
    item_407j_found = 0
    both_found = 0
    
    # Process each submission
    for submission in portfolio:
        total_filings += 1
        
        try:
            # Extract metadata
            metadata = extract_filing_metadata(submission)
            if not metadata:
                continue
            
            print(f"Processing: {metadata['ticker']} ({metadata['filing_date']})")
            
            # Get primary document
            primary_doc = None
            for document in submission:
                if hasattr(document, 'extension') and document.extension in ['.htm', '.html', '.txt']:
                    primary_doc = document
                    break
            
            if not primary_doc:
                print(f"  ✗ No 10-K document found")
                continue
            
            # Read filing content
            try:
                filing_text = primary_doc.content
                if isinstance(filing_text, bytes):
                    filing_text = filing_text.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  ✗ Error reading document: {e}")
                continue
            
            # Extract Items 106 and 407(j)
            item_106_content = extract_item_106(filing_text)
            item_407j_content = extract_item_407j(filing_text)
            
            # Convert to markdown if HTML
            if item_106_content:
                if '<' in item_106_content and '>' in item_106_content:
                    item_106_content = html_to_markdown(item_106_content)
                item_106_found += 1
                print(f"  ✓ Found Item 106")
            
            if item_407j_content:
                if '<' in item_407j_content and '>' in item_407j_content:
                    item_407j_content = html_to_markdown(item_407j_content)
                item_407j_found += 1
                print(f"  ✓ Found Item 407(j)")
            
            # Only create file if we found at least one item
            if item_106_content or item_407j_content:
                create_markdown_file(metadata, item_106_content, item_407j_content, 'data/10K')
                if item_106_content and item_407j_content:
                    both_found += 1
            else:
                print(f"  - No cybersecurity disclosures found")
                
        except Exception as e:
            print(f"  ✗ Error processing submission: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Write summary
    print(f"\n{'='*60}")
    print(f"Total 10-K filings processed: {total_filings}")
    print(f"Item 106 disclosures found: {item_106_found}")
    print(f"Item 407(j) disclosures found: {item_407j_found}")
    print(f"Both items found: {both_found}")
    print(f"{'='*60}")
    
    os.makedirs('.github/outputs', exist_ok=True)
    with open('.github/outputs/parse_10k_summary.txt', 'w') as f:
        f.write(f"total_filings={total_filings}\n")
        f.write(f"item_106_found={item_106_found}\n")
        f.write(f"item_407j_found={item_407j_found}\n")
        f.write(f"both_found={both_found}\n")

if __name__ == '__main__':
    main()