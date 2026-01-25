#!/usr/bin/env python3
"""Generate validation report for PR."""

import os
from pathlib import Path

def main():
    """Generate validation report."""
    print("# Validation Report\n")
    
    # Check if validation passed
    validation_passed = os.path.exists('.github/outputs/validation_passed')
    duplicates_found = os.path.exists('.github/outputs/duplicates_found')
    
    if validation_passed and not duplicates_found:
        print("## ✅ All Checks Passed\n")
        print("- Frontmatter validation: ✅ Passed")
        print("- Duplicate check: ✅ No duplicates found")
    else:
        print("## ❌ Validation Failed\n")
        
        if not validation_passed:
            print("- Frontmatter validation: ❌ Failed")
        
        if duplicates_found:
            print("- Duplicate check: ❌ Duplicates found")
    
    # Count files
    num_8k = len(list(Path('data/8K').rglob('*.md')))
    num_10k = len(list(Path('data/10K').rglob('*.md')))
    
    print(f"\n## Dataset Summary\n")
    print(f"- 8-K filings: {num_8k}")
    print(f"- 10-K filings: {num_10k}")
    print(f"- Total: {num_8k + num_10k}")

if __name__ == '__main__':
    main()