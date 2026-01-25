#!/usr/bin/env python3
"""Generate daily summary report."""

import os
from pathlib import Path
from datetime import datetime

def read_summary_file(filepath):
    """Read summary file and parse statistics."""
    if not os.path.exists(filepath):
        return {}
    
    stats = {}
    with open(filepath, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                try:
                    stats[key] = int(value)
                except:
                    stats[key] = value
    return stats

def main():
    """Generate daily summary."""
    # Read summaries
    summary_8k = read_summary_file('.github/outputs/parse_8k_summary.txt')
    summary_10k = read_summary_file('.github/outputs/parse_10k_summary.txt')
    
    # Create markdown summary
    os.makedirs('.github/outputs', exist_ok=True)
    
    with open('.github/outputs/daily_summary.md', 'w') as f:
        f.write(f"# Daily Ingestion Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n")
        
        f.write("## 8-K Filings (Item 1.05)\n\n")
        if summary_8k:
            f.write(f"- Total 8-K filings processed: **{summary_8k.get('total_filings', 0)}**\n")
            f.write(f"- Item 1.05 disclosures found: **{summary_8k.get('item_105_found', 0)}**\n")
            if summary_8k.get('total_filings', 0) > 0:
                rate = (summary_8k.get('item_105_found', 0) / summary_8k.get('total_filings', 1)) * 100
                f.write(f"- Detection rate: **{rate:.1f}%**\n")
        else:
            f.write("- No data available\n")
        
        f.write("\n## 10-K Filings (Items 106 & 407j)\n\n")
        if summary_10k:
            f.write(f"- Total 10-K filings processed: **{summary_10k.get('total_filings', 0)}**\n")
            f.write(f"- Item 106 disclosures found: **{summary_10k.get('item_106_found', 0)}**\n")
            f.write(f"- Item 407(j) disclosures found: **{summary_10k.get('item_407j_found', 0)}**\n")
            f.write(f"- Both items found: **{summary_10k.get('both_found', 0)}**\n")
        else:
            f.write("- No data available\n")
        
        f.write("\n## Status\n\n")
        f.write("✅ Daily ingestion completed successfully\n")
        
        f.write("\n## Next Steps\n\n")
        f.write("- Review new disclosures in the `data/` directory\n")
        f.write("- Check updated statistics in `stats/README.md`\n")
    
    print("✓ Daily summary generated")

if __name__ == '__main__':
    main()