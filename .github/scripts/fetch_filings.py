import os
import sys
import datetime
import pandas as pd
from datamule import Downloader, Parser # Assuming standard datamule usage patterns
from pathlib import Path

# Configuration
API_KEY = os.getenv("DATAMULE_API_KEY")
DATA_DIR = Path("data")

# Mapping rules to file types and item codes
TARGETS = [
    {"type": "8-K", "item": "1.05"},
    {"type": "10-K", "item": "106"},   # Regulation S-K Item 106
    {"type": "10-K", "item": "407"}    # Regulation S-K Item 407(j)
]

def get_quarter(date_obj):
    return f"Q{(date_obj.month - 1) // 3 + 1}"

def ensure_directory(filing_type, date_str):
    """Creates directory path: data/TYPE/YEAR/QTR/"""
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    year = str(date_obj.year)
    quarter = get_quarter(date_obj)
    
    path = DATA_DIR / filing_type / year / quarter
    path.mkdir(parents=True, exist_ok=True)
    return path

def format_markdown(metadata, content):
    """Generates the Markdown content with YAML frontmatter."""
    # Fallback if ticker is missing
    ticker = metadata.get('ticker', 'UNKNOWN')
    if isinstance(ticker, float): ticker = 'UNKNOWN' # Handle NaN
    
    md_content = f"""---
ticker: {ticker}
cik: {metadata.get('cik', '')}
date: {metadata.get('filing_date', '')}
filing_type: {metadata.get('form_type', '')}
source_link: {metadata.get('url', '')}
---

## {metadata.get('item_name', 'Cybersecurity Disclosure')}

{content}
"""
    return md_content

def main():
    if not API_KEY:
        print("Error: DATAMULE_API_KEY not found.")
        sys.exit(1)

    print("Initializing DataMule...")
    downloader = Downloader(api_key=API_KEY)
    
    # Calculate date range (Yesterday to capture the full previous day's filings)
    # In a production run, you might check the last 24h or a specific state file.
    # For this script, we look back 1 day.
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    
    print(f"Fetching filings for date: {date_str}")

    for target in TARGETS:
        print(f"Checking {target['type']} for Item {target['item']}...")
        
        try:
            # Note: actual datamule syntax may vary slightly based on version.
            # This logic assumes a method to filter by form, date, and items.
            filings = downloader.download(
                form=target['type'],
                date=date_str,
                items=[target['item']],
                return_type='pandas' # or dict
            )
            
            if filings.empty:
                print(f"No findings for {target['type']} Item {target['item']}")
                continue

            # Iterate through results
            for _, row in filings.iterrows():
                # Prepare metadata
                meta = {
                    'ticker': row.get('ticker'),
                    'cik': row.get('cik'),
                    'filing_date': row.get('filing_date', date_str),
                    'form_type': target['type'],
                    'url': row.get('filing_url'),
                    'item_name': f"Item {target['item']}"
                }
                
                # Extract text content
                content = row.get(f'item_{target["item"]}_text', '')
                
                if not content:
                    continue

                # Prepare file path
                save_dir = ensure_directory(target['type'], meta['filing_date'])
                filename = f"{meta['cik']}_{meta['filing_date']}_{target['type'].replace('-', '')}.md"
                file_path = save_dir / filename
                
                # Write to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(format_markdown(meta, content))
                
                print(f"Saved: {file_path}")

        except Exception as e:
            print(f"Error processing {target['type']}: {e}")

if __name__ == "__main__":
    main()