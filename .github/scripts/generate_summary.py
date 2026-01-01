#!/usr/bin/env python3
"""
Generate summary reports of cybersecurity disclosures.
"""

import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import yaml


def generate_summary():
    """Generate summary report of all cybersecurity disclosures"""
    
    data_dir = Path('data')
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    stats = {
        '8K': defaultdict(int),
        '10K': defaultdict(int),
        'companies': set(),
        'total': 0
    }
    
    recent_filings = []
    
    # Scan all markdown files
    for filing_type in ['8K', '10K']:
        filing_dir = data_dir / filing_type
        if not filing_dir.exists():
            continue
        
        for md_file in filing_dir.rglob('*.md'):
            try:
                # Parse frontmatter
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = yaml.safe_load(parts[1])
                            
                            year = frontmatter.get('filing_year')
                            quarter = frontmatter.get('filing_quarter')
                            
                            stats[filing_type][f"{year}-{quarter}"] += 1
                            stats['companies'].add(frontmatter.get('CIK'))
                            stats['total'] += 1
                            
                            # Track recent filings
                            filing_date = datetime.strptime(frontmatter.get('date'), '%Y-%m-%d')
                            recent_filings.append({
                                'date': filing_date,
                                'company': frontmatter.get('name'),
                                'ticker': frontmatter.get('ticker'),
                                'type': filing_type,
                                'category': frontmatter.get('category'),
                                'file': str(md_file.relative_to(data_dir))
                            })
                            
            except Exception as e:
                print(f"Error processing {md_file}: {e}")
    
    # Generate report
    report_path = reports_dir / 'summary.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# SEC Cybersecurity Disclosures Summary\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        f.write(f"## Overview\n\n")
        f.write(f"- **Total Disclosures**: {stats['total']}\n")
        f.write(f"- **Unique Companies**: {len(stats['companies'])}\n")
        f.write(f"- **8-K Filings (Item 1.05)**: {sum(stats['8K'].values())}\n")
        f.write(f"- **10-K Filings (Items 106/407j)**: {sum(stats['10K'].values())}\n\n")
        
        # Recent filings
        recent_filings.sort(key=lambda x: x['date'], reverse=True)
        f.write(f"## Recent Filings (Last 10)\n\n")
        f.write("| Date | Company | Ticker | Type | Category |\n")
        f.write("|------|---------|--------|------|----------|\n")
        
        for filing in recent_filings[:10]:
            f.write(f"| {filing['date'].strftime('%Y-%m-%d')} | "
                   f"{filing['company']} | "
                   f"{filing['ticker']} | "
                   f"{filing['type']} | "
                   f"{filing['category']} |\n")
        
        # Quarterly breakdown
        f.write(f"\n## Quarterly Breakdown\n\n")
        f.write("### 8-K Filings\n\n")
        for period in sorted(stats['8K'].keys(), reverse=True)[:8]:
            f.write(f"- {period}: {stats['8K'][period]} filings\n")
        
        f.write("\n### 10-K Filings\n\n")
        for period in sorted(stats['10K'].keys(), reverse=True)[:8]:
            f.write(f"- {period}: {stats['10K'][period]} filings\n")
    
    print(f"Summary report generated: {report_path}")


if __name__ == '__main__':
    generate_summary()