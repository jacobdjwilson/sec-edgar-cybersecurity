"""
fetch_10k.py
------------
Fetches 10-K annual cybersecurity disclosures from SEC EDGAR.

Targets Item 1C (Regulation S-K Item 106):
  - Cybersecurity risk management processes
  - Board and management governance disclosures
  - Strategy descriptions

Effective for fiscal years ending on or after December 15, 2023.
XBRL tagging required for fiscal years ending on or after December 15, 2024.

For each new submission:
  - Saves metadata.json  (filing metadata)
  - Saves cybersecurity.md  (extracted Item 1C text in markdown)

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
OUTPUT_DIR = BASE_DIR / "10K"
STATS_DIR = BASE_DIR / "stats"
STATE_FILE = STATS_DIR / "last_run_10k.txt"

DATAMULE_API_KEY = os.environ.get("DATAMULE_API_KEY")
FORM_TYPE = "10-K"

# First run lookback: go back to when rule became effective
DEFAULT_LOOKBACK_DAYS = 365 * 2
RULE_START_DATE = date(2024, 1, 1)  # fiscal years ending ≥ Dec 15 2023 → filed Q1 2024

# Section title patterns for Item 1C / cybersecurity
ITEM_1C_TITLES = [
    "item1c",
    "item 1c",
    "item1.c",
    "cybersecurity",
    "item 1c. cybersecurity",
]

CYBER_CONTENT_PATTERNS = [
    re.compile(r"item\s*1c", re.I),
    re.compile(r"cybersecurity\s+risk\s+management", re.I),
    re.compile(r"cybersecurity\s+strategy", re.I),
    re.compile(r"cybersecurity\s+governance", re.I),
    re.compile(r"material\s+effect.*cyber", re.I),
    re.compile(r"cyber.*board.*oversight", re.I),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_start_date() -> str:
    if STATE_FILE.exists():
        last = STATE_FILE.read_text().strip()
        try:
            dt = datetime.strptime(last, "%Y-%m-%d").date() + timedelta(days=1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    start = date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    return max(start, RULE_START_DATE).strftime("%Y-%m-%d")


def save_state(run_date: str):
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(run_date)


def accession_exists(accession: str) -> bool:
    folder = OUTPUT_DIR / accession.replace("-", "")
    return folder.exists() and (folder / "metadata.json").exists()


def extract_item_1c(document) -> str | None:
    """
    Attempt to extract Item 1C cybersecurity section from a 10-K document.
    Falls back to full text if the section extractor can't isolate it.
    Returns markdown or None.
    """
    # Try direct section extraction
    for title in ITEM_1C_TITLES:
        try:
            section = document.get_section(title=title, title_class="item", format="markdown")
            if section:
                text = section[0] if isinstance(section, list) else section
                if text and len(text.strip()) > 100:
                    return text.strip()
        except Exception:
            pass

    # Fall back: check full markdown/text for cyber content
    try:
        full_text = document.markdown or document.text or ""
    except Exception:
        return None

    if not full_text:
        return None

    if any(p.search(full_text) for p in CYBER_CONTENT_PATTERNS):
        # Try to slice out just the cybersecurity portion via regex
        cyber_match = re.search(
            r"(item\s*1c[.\s]*cybersecurity.*?)(?=item\s*[12]\w?\b|\Z)",
            full_text,
            re.I | re.S,
        )
        if cyber_match:
            extracted = cyber_match.group(1).strip()
            if len(extracted) > 100:
                return extracted

        # Last resort: return the full document if it's cyber-relevant
        # (only for short-ish docs to avoid noise)
        if len(full_text) < 50_000:
            return full_text

    return None


def build_metadata(sub, document) -> dict:
    accession = getattr(sub, "accession_number", "") or ""
    accession = accession.replace("/", "-").strip()

    return {
        "accession_number": accession,
        "ticker": getattr(sub, "ticker", "") or "",
        "cik": str(getattr(sub, "cik", "") or ""),
        "company_name": getattr(sub, "company_name", "") or "",
        "filing_date": str(getattr(sub, "filing_date", "") or ""),
        "form_type": FORM_TYPE,
        "item": "1C",
        "filing_url": getattr(sub, "filing_url", "") or "",
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
    }


def save_filing(accession: str, metadata: dict, cyber_text: str):
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
    print(f"Fetching 10-K cybersecurity disclosures: {start_date} → {end_date}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = Config()
    if DATAMULE_API_KEY:
        cfg.set_default_source("datamule")

    portfolio = Portfolio(str(OUTPUT_DIR / "_tmp_10k"))

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
            skip_existing=False,
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

        for document in sub:
            doc_type = getattr(document, "type", "") or ""
            ext = getattr(document, "extension", "") or ""

            if doc_type != "10-K":
                continue
            if ext not in (".htm", ".html", ".txt"):
                continue

            try:
                cyber_text = extract_item_1c(document)
            except Exception as e:
                print(f"  [WARN] extract failed for {accession}: {e}")
                error_count += 1
                continue

            if not cyber_text:
                continue

            metadata = build_metadata(sub, document)
            try:
                save_filing(acc_clean, metadata, cyber_text)
                new_count += 1
            except Exception as e:
                print(f"  [ERROR] save failed for {accession}: {e}", file=sys.stderr)
                error_count += 1
            break

    print(f"\nDone. New: {new_count}  Skipped: {skip_count}  Errors: {error_count}")
    save_state(end_date)
    return new_count


if __name__ == "__main__":
    main()
