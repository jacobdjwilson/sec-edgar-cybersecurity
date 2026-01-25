#!/usr/bin/env python3
"""Check for duplicate filings."""

import yaml
from pathlib import Path
from collections import defaultdict

def get_filing_key(filepath):
    """Extract unique key from filing."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                return (
                    frontmatter.get('cik'),
                    frontmatter.get('filing_date'),
                    frontmatter.get('filing_type')
                )
            except:
                pass
    return None

def main():
    """Check for duplicates."""
    filings = defaultdict(list)
    
    # Collect all filings
    for filepath in Path('data').rglob('*.md'):
        key = get_filing_key(filepath)
        if key:
            filings[key].append(filepath)
    
    # Find duplicates
    duplicates = {k: v for k, v in filings.items() if len(v) > 1}
    
    if duplicates:
        print(f"❌ Found {len(duplicates)} duplicate filings:")
        for key, files in duplicates.items():
            print(f"\n  CIK: {key[0]}, Date: {key[1]}, Type: {key[2]}")
            for f in files:
                print(f"    - {f}")
        exit(1)
    else:
        print("✅ No duplicates found")

if __name__ == '__main__':
    main()