#!/usr/bin/env python3
"""Validate markdown files in dataset."""

import yaml
from pathlib import Path

def validate_frontmatter(filepath, filing_type):
    """Validate YAML frontmatter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not content.startswith('---'):
        return False, "Missing frontmatter"
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return False, "Invalid frontmatter format"
    
    try:
        frontmatter = yaml.safe_load(parts[1])
    except Exception as e:
        return False, f"Invalid YAML: {e}"
    
    # Check required fields
    required_fields = ['ticker', 'cik', 'filing_date', 'filing_type', 'source_link']
    
    for field in required_fields:
        if field not in frontmatter:
            return False, f"Missing required field: {field}"
    
    # Validate filing type specific fields
    if filing_type == '8K':
        if 'item' not in frontmatter or frontmatter['item'] != '1.05':
            return False, "8-K must have item: 1.05"
    
    if filing_type == '10K':
        if 'items' not in frontmatter or not frontmatter['items']:
            return False, "10-K must have items list"
    
    return True, "Valid"

def main():
    """Validate all markdown files."""
    errors = []
    total_files = 0
    
    # Validate 8-K files
    for filepath in Path('data/8K').rglob('*.md'):
        total_files += 1
        valid, message = validate_frontmatter(filepath, '8K')
        if not valid:
            errors.append(f"{filepath}: {message}")
    
    # Validate 10-K files
    for filepath in Path('data/10K').rglob('*.md'):
        total_files += 1
        valid, message = validate_frontmatter(filepath, '10K')
        if not valid:
            errors.append(f"{filepath}: {message}")
    
    print(f"Validated {total_files} files")
    
    if errors:
        print(f"\n❌ Found {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("✅ All files valid")

if __name__ == '__main__':
    main()