#!/usr/bin/env python3
"""
Validate all Markdown files in the dataset.
Checks:
  - YAML frontmatter is present and parseable
  - Required fields are present
  - Field values are of expected types
  - Filing dates are valid
"""

import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS_8K = ["ticker", "company_name", "cik", "filing_date", "filing_type", "item", "accession_number"]
REQUIRED_FIELDS_10K = ["ticker", "company_name", "cik", "filing_date", "filing_type", "items", "accession_number"]

VALID_FILING_TYPES = {"8-K", "10-K"}
VALID_8K_ITEMS = {"1.05"}
VALID_10K_ITEMS = {106, "406j", "407j"}


def parse_frontmatter(md_path: Path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None, ["Missing YAML frontmatter (file must start with ---)"]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, ["Malformed YAML frontmatter (could not find closing ---)"]

    try:
        fm = yaml.safe_load(parts[1])
        return fm, []
    except yaml.YAMLError as e:
        return None, [f"Invalid YAML: {e}"]


def validate_file(md_path: Path) -> list[str]:
    errors = []

    fm, parse_errors = parse_frontmatter(md_path)
    if parse_errors:
        return parse_errors
    if fm is None:
        return ["Empty frontmatter"]

    filing_type = fm.get("filing_type", "")
    if filing_type not in VALID_FILING_TYPES:
        errors.append(f"Invalid filing_type: '{filing_type}' (expected 8-K or 10-K)")

    if filing_type == "8-K":
        for field in REQUIRED_FIELDS_8K:
            if not fm.get(field):
                errors.append(f"Missing required field: {field}")
        item = fm.get("item")
        if item and str(item) not in VALID_8K_ITEMS:
            errors.append(f"Unexpected 8-K item value: {item}")

    elif filing_type == "10-K":
        for field in REQUIRED_FIELDS_10K:
            if not fm.get(field):
                errors.append(f"Missing required field: {field}")
        items = fm.get("items", [])
        if not isinstance(items, list):
            errors.append(f"'items' should be a list, got {type(items).__name__}")

    # Validate filing_date format
    filing_date = str(fm.get("filing_date", ""))
    if filing_date and len(filing_date) != 10:
        errors.append(f"filing_date '{filing_date}' does not match YYYY-MM-DD format")

    return errors


def main():
    data_dir = Path("data")
    if not data_dir.exists():
        print("No data/ directory found. Nothing to validate.")
        sys.exit(0)

    md_files = list(data_dir.glob("**/*.md"))
    # Exclude parse_summary.json-adjacent files
    md_files = [f for f in md_files if f.name != "README.md"]

    print(f"Validating {len(md_files)} Markdown files...")

    all_errors = {}
    for md_file in md_files:
        errors = validate_file(md_file)
        if errors:
            all_errors[str(md_file)] = errors

    if all_errors:
        print(f"\n❌ Validation FAILED — {len(all_errors)} file(s) have errors:\n")
        for path, errors in sorted(all_errors.items()):
            print(f"  {path}:")
            for err in errors:
                print(f"    - {err}")
        sys.exit(1)
    else:
        print(f"✅ All {len(md_files)} files passed validation.")
        sys.exit(0)


if __name__ == "__main__":
    main()
