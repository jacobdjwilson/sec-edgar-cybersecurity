#!/usr/bin/env python3
"""Generate statistics about the dataset."""

import os
import yaml
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate dataset statistics')
    parser.add_argument('--filing-type', default='ALL', choices=['8K', '10K', 'ALL'])
    return parser.parse_args()

def read_markdown_frontmatter(filepath):
    """Read YAML frontmatter from markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1])
            except:
                return None
    return None

def analyze_directory(data_dir, filing_type):
    """Analyze all markdown files in directory."""
    stats = {
        'total_filings': 0,
        'by_year': defaultdict(int),
        'by_quarter': defaultdict(int),
        'by_ticker': defaultdict(int),
        'by_company': defaultdict(int),
        'tickers': set(),
        'companies': set(),
        'date_range': {'earliest': None, 'latest': None},
    }
    
    if filing_type == '10K':
        stats['by_item'] = defaultdict(int)
    
    # Walk through directory
    for filepath in Path(data_dir).rglob('*.md'):
        frontmatter = read_markdown_frontmatter(filepath)
        
        if not frontmatter:
            continue
        
        stats['total_filings'] += 1
        
        # Extract data
        ticker = frontmatter.get('ticker', 'unknown')
        company = frontmatter.get('company_name', 'Unknown')
        filing_date = frontmatter.get('filing_date', '')
        
        # Track tickers and companies
        stats['tickers'].add(ticker)
        stats['companies'].add(company)
        stats['by_ticker'][ticker] += 1
        stats['by_company'][company] += 1
        
        # Track by year/quarter
        try:
            date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
            year = date_obj.year
            quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
            
            stats['by_year'][year] += 1
            stats['by_quarter'][f"{year}-{quarter}"] += 1
            
            # Track date range
            if not stats['date_range']['earliest'] or date_obj < stats['date_range']['earliest']:
                stats['date_range']['earliest'] = date_obj
            if not stats['date_range']['latest'] or date_obj > stats['date_range']['latest']:
                stats['date_range']['latest'] = date_obj
        except:
            pass
        
        # For 10-K, track items
        if filing_type == '10K':
            items = frontmatter.get('items', [])
            for item in items:
                stats['by_item'][item] += 1
    
    return stats

def generate_summary(stats_8k, stats_10k):
    """Generate summary statistics."""
    summary = {
        'generated_at': datetime.now().isoformat(),
        '8K': {
            'total': stats_8k['total_filings'],
            'unique_companies': len(stats_8k['companies']),
            'unique_tickers': len(stats_8k['tickers']),
            'by_year': dict(stats_8k['by_year']),
            'top_10_companies': dict(Counter(stats_8k['by_ticker']).most_common(10)),
        },
        '10K': {
            'total': stats_10k['total_filings'],
            'unique_companies': len(stats_10k['companies']),
            'unique_tickers': len(stats_10k['tickers']),
            'by_year': dict(stats_10k['by_year']),
            'by_item': dict(stats_10k.get('by_item', {})),
            'top_10_companies': dict(Counter(stats_10k['by_ticker']).most_common(10)),
        },
        'overall': {
            'total_filings': stats_8k['total_filings'] + stats_10k['total_filings'],
            'total_unique_companies': len(stats_8k['companies'] | stats_10k['companies']),
            'total_unique_tickers': len(stats_8k['tickers'] | stats_10k['tickers']),
        }
    }
    
    return summary

def main():
    """Generate statistics."""
    args = parse_args()
    
    # Analyze datasets
    stats_8k = analyze_directory('data/8K', '8K') if args.filing_type in ['8K', 'ALL'] else defaultdict(int)
    stats_10k = analyze_directory('data/10K', '10K') if args.filing_type in ['10K', 'ALL'] else defaultdict(int)
    
    # Generate summary
    summary = generate_summary(stats_8k, stats_10k)
    
    # Create stats directory
    os.makedirs('stats', exist_ok=True)
    
    # Write JSON
    with open('stats/summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Write markdown report
    with open('stats/README.md', 'w') as f:
        f.write('# Dataset Statistics\n\n')
        f.write(f"**Generated:** {summary['generated_at']}\n\n")
        
        f.write('## Overall Statistics\n\n')
        f.write(f"- **Total Filings:** {summary['overall']['total_filings']}\n")
        f.write(f"- **Unique Companies:** {summary['overall']['total_unique_companies']}\n")
        f.write(f"- **Unique Tickers:** {summary['overall']['total_unique_tickers']}\n\n")
        
        f.write('## 8-K Filings (Item 1.05 - Material Cybersecurity Incidents)\n\n')
        f.write(f"- **Total 8-K Filings:** {summary['8K']['total']}\n")
        f.write(f"- **Unique Companies:** {summary['8K']['unique_companies']}\n")
        f.write(f"- **Unique Tickers:** {summary['8K']['unique_tickers']}\n\n")
        
        if summary['8K']['by_year']:
            f.write('### By Year\n\n')
            for year in sorted(summary['8K']['by_year'].keys()):
                f.write(f"- **{year}:** {summary['8K']['by_year'][year]} filings\n")
            f.write('\n')
        
        if summary['8K']['top_10_companies']:
            f.write('### Top 10 Companies by Filing Count\n\n')
            for ticker, count in summary['8K']['top_10_companies'].items():
                f.write(f"- **{ticker}:** {count} filings\n")
            f.write('\n')
        
        f.write('## 10-K Filings (Items 106 & 407j - Risk Management & Governance)\n\n')
        f.write(f"- **Total 10-K Filings:** {summary['10K']['total']}\n")
        f.write(f"- **Unique Companies:** {summary['10K']['unique_companies']}\n")
        f.write(f"- **Unique Tickers:** {summary['10K']['unique_tickers']}\n\n")
        
        if summary['10K'].get('by_item'):
            f.write('### By Item\n\n')
            for item, count in summary['10K']['by_item'].items():
                f.write(f"- **Item {item}:** {count} filings\n")
            f.write('\n')
        
        if summary['10K']['by_year']:
            f.write('### By Year\n\n')
            for year in sorted(summary['10K']['by_year'].keys()):
                f.write(f"- **{year}:** {summary['10K']['by_year'][year]} filings\n")
            f.write('\n')
        
        if summary['10K']['top_10_companies']:
            f.write('### Top 10 Companies by Filing Count\n\n')
            for ticker, count in summary['10K']['top_10_companies'].items():
                f.write(f"- **{ticker}:** {count} filings\n")
    
    print(f"✓ Statistics generated")
    print(f"  - Total filings: {summary['overall']['total_filings']}")
    print(f"  - 8-K filings: {summary['8K']['total']}")
    print(f"  - 10-K filings: {summary['10K']['total']}")

if __name__ == '__main__':
    main()