#!/usr/bin/env python3
"""
Validate data quality of cybersecurity disclosures.
"""

import argparse
from pathlib import Path
import yaml
from datetime import datetime


def validate_data(output_path: str = None):
    """Validate all markdown files in data directory"""
    
    data_dir = Path('data')
    issues = []
    validated = 0
    
    required_fields = [
        'name', 'CIK', 'filing_number', 'date',
        'filing_type', 'filing_quarter', 'filing_year'
    ]
    
    for md_file in data_dir.rglob('*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check frontmatter
                if not content.startswith('---'):
                    issues.append(f"❌ {md_file}: Missing YAML frontmatter")
                    continue
                
                parts = content.split('---', 2)
                if len(parts) < 3:
                    issues.append(f"❌ {md_file}: Invalid YAML frontmatter structure")
                    continue
                
                frontmatter = yaml.safe_load(parts[1])
                
                # Check required fields
                for field in required_fields:
                    if field not in frontmatter or not frontmatter[field]:
                        issues.append(f"❌ {md_file}: Missing required field '{field}'")
                
                # Check date format
                try:
                    datetime.strptime(frontmatter.get('date', ''), '%Y-%m-%d')
                except ValueError:
                    issues.append(f"❌ {md_file}: Invalid date format")
                
                # Check content exists
                markdown_content = parts[2].strip()
                if len(markdown_content) < 100:
                    issues.append(f"⚠️  {md_file}: Content seems too short ({len(markdown_content)} chars)")
                
                validated += 1
                
        except Exception as e:
            issues.append(f"❌ {md_file}: Error reading file - {e}")
    
    # Generate report
    report = f"# Data Validation Report\n\n"
    report += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    report += f"## Summary\n\n"
    report += f"- **Files Validated**: {validated}\n"
    report += f"- **Issues Found**: {len(issues)}\n\n"
    
    if issues:
        report += f"## Issues\n\n"
        for issue in issues:
            report += f"{issue}\n"
    else:
        report += f"✅ All files passed validation!\n"
    
    # Output
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Validation report written to {output_path}")
    else:
        print(report)
    
    return len(issues) == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate cybersecurity disclosure data')
    parser.add_argument('--output', help='Output file for report')
    args = parser.parse_args()
    
    success = validate_data(args.output)
    exit(0 if success else 1)