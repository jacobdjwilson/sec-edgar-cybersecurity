"""
fetch_8k.py
-----------
Fetches 8-K cybersecurity incident disclosures from SEC EDGAR.

Targets:
  - Item 1.05  (material cybersecurity incidents, mandatory since Dec 18 2023)
  - Item 8.01  (voluntary/non-material cyber filings per SEC May 2024 guidance)

For each new submission:
  - Saves metadata.json  (filing metadata)
  - Saves cybersecurity.md  (extracted Item 1.05 / cyber text in markdown)

Skips accession numbers that already exist on disk (idempotent).
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from datamule import Portfolio
from datamule.config import Config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "8K"
STATS_DIR = BASE_DIR / "stats"
STATE_FILE = STATS_DIR / "last_run_8k.txt"

DATAMULE_API_KEY = os.environ.get("DATAMULE_API_KEY")
FORM_TYPE = "8-K"

# How many days back to look on the very first run (before STATE_FILE exists)
DEFAULT_LOOKBACK_DAYS = 365 * 2  # capture full history since rule adoption

# Regex patterns to identify cybersecurity sections
CYBER_ITEM_PATTERNS = [
    re.compile(r"item\s*1[\.\s]*05", re.I),     # Item 1.05
    re.compile(r"cybersecurity\s+incident", re.I),
    re.compile(r"material\s+cybersecurity", re.I),
]

ITEM_801_CYBER_PATTERNS = [
    re.compile(r"cybersecurity", re.I),
    re.compile(r"cyber\s+incident", re.I),
    re.compile(r"data\s+breach", re.I),
    re.compile(r"ransomware", re.I),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_start_date() -> str:
    """Return the date to start fetching from (day after last run, or default)."""
    if STATE_FILE.exists():
        last = STATE_FILE.read_text().strip()
        try:
            dt = datetime.strptime(last, "%Y-%m-%d").date() + timedelta(days=1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # First run: go back far enough to capture full rule history
    start = date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    # Rule was effective December 18, 2023 — don't go earlier
    rule_start = date(2023, 12, 18)
    return max(start, rule_start).strftime("%Y-%m-%d")


def save_state(run_date: str):
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(run_date)


def accession_exists(accession: str) -> bool:
    folder = OUTPUT_DIR / accession.replace("-", "")
    return folder.exists() and (folder / "metadata.json").exists()


def extract_cyber_section(document) -> str | None:
    """
    Extract the cybersecurity-relevant text from an 8-K document.
    Returns markdown string or None if no cyber content found.
    """
    try:
        text = document.markdown or document.text or ""
    except Exception:
        return None

    if not text:
        return None

    # Check if this document contains cyber content
    has_cyber = any(p.search(text) for p in CYBER_ITEM_PATTERNS + ITEM_801_CYBER_PATTERNS)
    if not has_cyber:
        return None

    # Try to extract just Item 1.05 section
    try:
        section = document.get_section(title="item1.05", title_class="item", format="markdown")
        if section:
            return section[0] if isinstance(section, list) else section
    except Exception:
        pass

    # Fall back to full document text (it's already filtered for cyber relevance)
    return text


def build_metadata(sub, document, item: str) -> dict:
    """Build a metadata dict from a datamule Submission/Document."""
    accession = getattr(sub, "accession_number", "") or ""
    # Normalize accession number format
    accession = accession.replace("/", "-").strip()

    return {
        "accession_number": accession,
        "ticker": getattr(sub, "ticker", "") or "",
        "cik": str(getattr(sub, "cik", "") or ""),
        "company_name": getattr(sub, "company_name", "") or "",
        "filing_date": str(getattr(sub, "filing_date", "") or ""),
        "form_type": FORM_TYPE,
        "item": item,
        "filing_url": getattr(sub, "filing_url", "") or "",
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
    }


def save_filing(accession: str, metadata: dict, cyber_text: str):
    """Persist metadata.json and cybersecurity.md for a single filing."""
    folder = OUTPUT_DIR / accession.replace("-", "")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (folder / "cybersecurity.md").write_text(cyber_text, encoding="utf-8")
    print(f"  ✓ Saved {accession}  [{metadata.get('ticker','?')}]  {metadata.get('filing_date','')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_date = get_start_date()
    end_date = date.today().strftime("%Y-%m-%d")
    print(f"Fetching 8-K cybersecurity filings: {start_date} → {end_date}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Configure datamule provider
    cfg = Config()
    if DATAMULE_API_KEY:
        cfg.set_default_source("datamule")

    portfolio = Portfolio(str(OUTPUT_DIR / "_tmp_8k"))

    if DATAMULE_API_KEY:
        portfolio.set_api_key(DATAMULE_API_KEY)

    provider = "datamule" if DATAMULE_API_KEY else None

    new_count = 0
    skip_count = 0
    error_count = 0

    try:
        portfolio.download_submissions(
            submission_type=FORM_TYPE,
            filing_date=(start_date, end_date),
            provider=provider,
            quiet=False,
            skip_existing=False,  # we handle dedup ourselves per-accession
        )
    except Exception as e:
        print(f"[ERROR] download_submissions failed: {e}", file=sys.stderr)
        sys.exit(1)

    for sub in portfolio:
        accession = getattr(sub, "accession_number", "") or ""
        if not accession:
            continue

        acc_clean = accession.replace("-", "")

        if accession_exists(acc_clean):
            skip_count += 1
            continue

        # Iterate documents looking for cyber content
        for document in sub:
            doc_type = getattr(document, "type", "") or ""
            ext = getattr(document, "extension", "") or ""

            # Only parse the primary 8-K document
            if doc_type != "8-K":
                continue
            if ext not in (".htm", ".html", ".txt"):
                continue

            try:
                cyber_text = extract_cyber_section(document)
            except Exception as e:
                print(f"  [WARN] extract failed for {accession}: {e}")
                error_count += 1
                continue

            if not cyber_text:
                continue

            # Determine which item this is
            item = "1.05" if any(p.search(cyber_text) for p in CYBER_ITEM_PATTERNS) else "8.01"

            metadata = build_metadata(sub, document, item)
            try:
                save_filing(acc_clean, metadata, cyber_text)
                new_count += 1
            except Exception as e:
                print(f"  [ERROR] save failed for {accession}: {e}", file=sys.stderr)
                error_count += 1
            break  # one primary document per submission

    print(
        f"\nDone. New: {new_count}  Skipped: {skip_count}  Errors: {error_count}"
    )
    save_state(end_date)
    return new_count


if __name__ == "__main__":
    main()
