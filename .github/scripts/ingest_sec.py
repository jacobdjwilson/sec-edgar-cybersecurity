#!/usr/bin/env python3
"""
SEC Cybersecurity Filings Ingestion Script
Fetches, parses, and stores SEC 8-K and 10-K cybersecurity disclosures
"""

import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    from datamule import DataMule
    from markitdown import MarkItDown
    from bs4 import BeautifulSoup
    import yaml
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class SECCybersecurityIngest:
    """Main ingestion engine for SEC cybersecurity filings"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DATA_MULE_API_KEY')
        if not self.api_key:
            raise ValueError("DATA_MULE_API_KEY environment variable must be set")
        
        self.mule = DataMule(api_key=self.api_key)
        self.md_converter = MarkItDown()
        self.base_path = Path("data")
        self.base_path.mkdir(exist_ok=True)
        
        # Stats tracking
        self.stats = {
            'processed': 0,
            'saved': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def get_quarter(self, date_obj):
        """Determine quarter from date"""
        month = date_obj.month
        if month <= 3:
            return 'Q1'
        elif month <= 6:
            return 'Q2'
        elif month <= 9:
            return 'Q3'
        else:
            return 'Q4'
    
    def get_output_path(self, ticker, filing_type, filing_date):
        """Generate output file path"""
        date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
        year = date_obj.year
        quarter = self.get_quarter(date_obj)
        
        # Create directory structure
        dir_path = self.base_path / str(year) / quarter
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"{ticker}_{filing_type}_{filing_date}.md"
        return dir_path / filename
    
    def extract_relevant_section(self, html_content, filing_type):
        """Extract cybersecurity-relevant sections from HTML"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        if filing_type == '8-K':
            # Look for Item 1.05 sections
            relevant_text = []
            
            # Try to find Item 1.05 header and content
            text = soup.get_text()
            
            # Pattern to find Item 1.05 section
            patterns = [
                r'Item\s+1\.05[^\n]*Material\s+Cybersecurity',
                r'Item\s+1\.05',
                r'ITEM\s+1\.05'
            ]
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Found Item 1.05, try to extract section
                    # Look for the section between Item 1.05 and next Item
                    match = re.search(
                        r'(Item\s+1\.05.*?)(?=Item\s+\d|ITEM\s+\d|Item\s+[2-9]|$)',
                        text,
                        re.DOTALL | re.IGNORECASE
                    )
                    if match:
                        relevant_text.append(match.group(1))
                    break
            
            if relevant_text:
                return '\n'.join(relevant_text)
            
            # Fallback: if Item 1.05 mentioned, return full text
            if 'item 1.05' in text.lower():
                return text
                
            return None
        
        elif filing_type == '10-K':
            # Look for Item 1C (Risk Management) or Item 407(j) (Governance)
            text = soup.get_text()
            
            patterns = [
                r'Item\s+1C.*?Cybersecurity',
                r'Item\s+106',
                r'Item\s+407.*?\(j\)',
                r'Cybersecurity\s+Risk\s+Management',
                r'ITEM\s+1C'
            ]
            
            relevant_sections = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Extract context around the match
                    start = max(0, match.start() - 500)
                    end = min(len(text), match.end() + 5000)
                    section = text[start:end]
                    relevant_sections.append(section)
            
            if relevant_sections:
                return '\n\n---\n\n'.join(relevant_sections)
            
            # Fallback: search for cybersecurity keyword
            if 'cybersecurity' in text.lower():
                # Extract paragraphs containing cybersecurity
                cyber_paras = []
                paragraphs = text.split('\n\n')
                for para in paragraphs:
                    if 'cybersecurity' in para.lower():
                        cyber_paras.append(para)
                
                if cyber_paras:
                    return '\n\n'.join(cyber_paras[:10])  # Limit to first 10 paragraphs
            
            return None
        
        return None
    
    def create_frontmatter(self, filing_data, item_type):
        """Generate YAML frontmatter"""
        frontmatter = {
            'ticker': filing_data.get('ticker', 'UNKNOWN'),
            'company_name': filing_data.get('company_name', 'Unknown Company'),
            'cik': filing_data.get('cik', 'Unknown'),
            'filing_type': filing_data.get('form', 'Unknown'),
            'filing_date': filing_data.get('filing_date', 'Unknown'),
            'item_type': item_type,
            'sec_link': filing_data.get('filing_url', ''),
            'accession_number': filing_data.get('accession_number', 'Unknown')
        }
        
        return f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n"
    
    def create_markdown_document(self, filing_data, markdown_content, filing_type):
        """Create final formatted markdown document"""
        company_name = filing_data.get('company_name', 'Unknown Company')
        filing_date = filing_data.get('filing_date', 'Unknown')
        ticker = filing_data.get('ticker', 'UNKNOWN')
        cik = filing_data.get('cik', 'Unknown')
        accession = filing_data.get('accession_number', 'Unknown')
        filing_url = filing_data.get('filing_url', '#')
        
        if filing_type == '8-K':
            item_type = '1.05'
            doc = f"""# {company_name} Cybersecurity Incident

**Last updated:** {datetime.now().strftime('%Y-%m-%d')}

{company_name} disclosed a material cybersecurity incident in an SEC 8-K filing on {filing_date}.

## Filing Details

- **Filing Type:** 8-K (Item 1.05)
- **Filing Date:** {filing_date}
- **Accession Number:** {accession}
- **SEC Link:** [{filing_url}]({filing_url})

## Incident Disclosure

{markdown_content}

## Company Information

| Field | Value |
|-------|-------|
| Company Name | {company_name} |
| CIK | {cik} |
| Ticker | {ticker} |

---

*This document was automatically generated from SEC EDGAR filings.*
"""
        else:  # 10-K
            item_type = '1C/106'
            doc = f"""# {company_name} Cybersecurity Risk Management (10-K)

**Last updated:** {datetime.now().strftime('%Y-%m-%d')}

{company_name} reported their cybersecurity risk management and governance processes in a 10-K filing on {filing_date}.

## Filing Details

- **Filing Type:** 10-K
- **Filing Date:** {filing_date}
- **Accession Number:** {accession}
- **SEC Link:** [{filing_url}]({filing_url})

## Cybersecurity Risk Management & Governance

{markdown_content}

## Company Information

| Field | Value |
|-------|-------|
| Company Name | {company_name} |
| CIK | {cik} |
| Ticker | {ticker} |

---

*This document was automatically generated from SEC EDGAR filings.*
"""
        
        return doc, item_type
    
    def process_filing(self, filing_data):
        """Process a single filing"""
        try:
            ticker = filing_data.get('ticker', 'UNKNOWN')
            form = filing_data.get('form', 'Unknown')
            filing_date = filing_data.get('filing_date', 'Unknown')
            
            print(f"Processing {ticker} {form} from {filing_date}...")
            
            # Get the HTML content
            html_content = filing_data.get('html_content')
            if not html_content:
                print(f"  ⚠️  No HTML content available for {ticker} {form}")
                self.stats['skipped'] += 1
                return False
            
            # Extract relevant section
            relevant_section = self.extract_relevant_section(html_content, form)
            if not relevant_section:
                print(f"  ⚠️  No cybersecurity content found in {ticker} {form}")
                self.stats['skipped'] += 1
                return False
            
            # Convert to markdown
            try:
                md_result = self.md_converter.convert(relevant_section)
                markdown_content = md_result.text_content if hasattr(md_result, 'text_content') else str(md_result)
            except Exception as e:
                print(f"  ❌ Markdown conversion failed: {e}")
                # Fallback to plain text
                markdown_content = relevant_section
            
            # Create document
            final_doc, item_type = self.create_markdown_document(
                filing_data, 
                markdown_content, 
                form
            )
            
            # Add frontmatter
            frontmatter = self.create_frontmatter(filing_data, item_type)
            final_content = frontmatter + final_doc
            
            # Save to file
            output_path = self.get_output_path(ticker, form, filing_date)
            
            # Check if file already exists
            if output_path.exists():
                print(f"  ℹ️  File already exists: {output_path}")
                self.stats['skipped'] += 1
                return False
            
            output_path.write_text(final_content, encoding='utf-8')
            print(f"  ✅ Saved: {output_path}")
            self.stats['saved'] += 1
            return True
            
        except Exception as e:
            print(f"  ❌ Error processing filing: {e}")
            self.stats['errors'] += 1
            return False
    
    def fetch_recent_filings(self, days_back=1):
        """Fetch recent filings from the past N days"""
        print(f"\n🔍 Fetching filings from the past {days_back} day(s)...")
        
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"Date range: {start_date} to {end_date}")
        
        all_filings = []
        
        # Fetch 8-K filings (Item 1.05)
        print("\n📄 Fetching 8-K filings...")
        try:
            filings_8k = self.mule.search_filings(
                form_types=['8-K'],
                start_date=start_date,
                end_date=end_date,
                fetch_content=True
            )
            
            # Filter for Item 1.05
            for filing in filings_8k:
                html = filing.get('html_content', '')
                if html and 'item 1.05' in html.lower():
                    all_filings.append(filing)
                    print(f"  Found: {filing.get('ticker', 'N/A')} - {filing.get('filing_date', 'N/A')}")
        except Exception as e:
            print(f"  ⚠️  Error fetching 8-K filings: {e}")
        
        # Fetch 10-K filings
        print("\n📄 Fetching 10-K filings...")
        try:
            filings_10k = self.mule.search_filings(
                form_types=['10-K'],
                start_date=start_date,
                end_date=end_date,
                fetch_content=True
            )
            
            # Filter for cybersecurity content
            for filing in filings_10k:
                html = filing.get('html_content', '')
                if html:
                    html_lower = html.lower()
                    if 'item 1c' in html_lower or 'item 106' in html_lower or \
                       'cybersecurity risk' in html_lower or 'item 407' in html_lower:
                        all_filings.append(filing)
                        print(f"  Found: {filing.get('ticker', 'N/A')} - {filing.get('filing_date', 'N/A')}")
        except Exception as e:
            print(f"  ⚠️  Error fetching 10-K filings: {e}")
        
        return all_filings
    
    def run(self, days_back=1):
        """Main execution flow"""
        print("=" * 60)
        print("SEC CYBERSECURITY FILINGS INGESTION")
        print("=" * 60)
        
        # Fetch recent filings
        filings = self.fetch_recent_filings(days_back)
        print(f"\n📊 Total filings to process: {len(filings)}")
        
        if not filings:
            print("\n✅ No new cybersecurity filings found.")
            return
        
        # Process each filing
        print("\n⚙️  Processing filings...\n")
        for filing in filings:
            self.stats['processed'] += 1
            self.process_filing(filing)
        
        # Print summary
        print("\n" + "=" * 60)
        print("INGESTION SUMMARY")
        print("=" * 60)
        print(f"Processed:  {self.stats['processed']}")
        print(f"Saved:      {self.stats['saved']}")
        print(f"Skipped:    {self.stats['skipped']}")
        print(f"Errors:     {self.stats['errors']}")
        print("=" * 60)


def main():
    """Entry point"""
    try:
        ingest = SECCybersecurityIngest()
        ingest.run(days_back=1)
        
        # Exit with error code if there were errors
        if ingest.stats['errors'] > 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()