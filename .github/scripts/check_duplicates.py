#!/usr/bin/env python3
"""
Check for duplicate filings in the dataset.
A duplicate is defined as two files sharing the same accession_number,
or the same (cik + filing_date + filing_type) combination.
"""

import sys
from collections import defaultdict
from pathlib import Path

import yaml


def parse_frontmatter(md_path: Path) -> dict | None:
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        return yaml.safe_load(parts[1])
    except Exception:
        return None


def main():
    data_dir = Path("data")
    if not data_dir.exists():
        print("No data/ directory. Nothing to check.")
        sys.exit(0)

    md_files = [f for f in data_dir.glob("**/*.md") if f.name != "README.md"]
    print(f"Checking {len(md_files)} files for duplicates...")

    by_accession = defaultdict(list)
    by_compound_key = defaultdict(list)

    for md_file in md_files:
        fm = parse_frontmatter(md_file)
        if not fm:
            continue

        accession = fm.get("accession_number", "").strip()
        if accession:
            by_accession[accession].append(str(md_file))

        cik = str(fm.get("cik", "")).strip()
        filing_date = str(fm.get("filing_date", "")).strip()
        filing_type = str(fm.get("filing_type", "")).strip()
        if cik and filing_date and filing_type:
            key = f"{cik}|{filing_date}|{filing_type}"
            by_compound_key[key].append(str(md_file))

    duplicates_found = False

    accession_dupes = {acc: paths for acc, paths in by_accession.items() if len(paths) > 1}
    if accession_dupes:
        duplicates_found = True
        print(f"\n❌ Duplicate accession numbers ({len(accession_dupes)}):")
        for acc, paths in sorted(accession_dupes.items()):
            print(f"  {acc}:")
            for p in paths:
                print(f"    - {p}")

    compound_dupes = {key: paths for key, paths in by_compound_key.items() if len(paths) > 1}
    if compound_dupes:
        duplicates_found = True
        print(f"\n❌ Duplicate CIK+date+type combinations ({len(compound_dupes)}):")
        for key, paths in sorted(compound_dupes.items()):
            print(f"  {key}:")
            for p in paths:
                print(f"    - {p}")

    if not duplicates_found:
        print("✅ No duplicates found.")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
