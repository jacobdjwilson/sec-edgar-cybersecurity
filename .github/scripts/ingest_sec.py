
import logging
import time
import os
import re
import yaml
import subprocess
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from datamule import Portfolio
from datetime import datetime, timedelta

# --- Configuration ---
# Get API key from environment variable
API_KEY = os.getenv("DATA_MULE_API_KEY")
if not API_KEY:
    raise ValueError("DATA_MULE_API_KEY environment variable not set.")

# Base paths
# The script is in .github/scripts, so we need to go up two levels for the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "data"

PROCESSED_FILINGS_PATH = REPO_ROOT / ".github" / "processed_filings.txt"

# --- Logging Configuration ---
LOG_DIR = REPO_ROOT / ".github" / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "ingestion.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Keywords for filtering 10-K filings (case-insensitive)
TEN_K_KEYWORDS = ["item 1c", "cybersecurity", "item 407(j)"]


def find_relevant_section(soup, form_type):
    """
    Finds the relevant HTML section within a filing using BeautifulSoup.
    Traverses sibling elements to accurately capture the entire section.
    """
    body_text = soup.get_text().lower()
    item_type = None
    start_tag = None
    
    # Define patterns to find the start of the relevant section
    patterns = {
        "8-K": ("item 1.05", "1.05"),
        "10-K": ("item 1c", "106"),
        "10-K_alt1": ("cybersecurity", "Risk Management"),
        "10-K_alt2": ("item 407(j)", "407(j)"),
    }
    
    current_pattern_key = None
    if form_type == "8-K":
        if patterns["8-K"][0] in body_text:
            current_pattern_key = "8-K"
    elif form_type == "10-K":
        if patterns["10-K"][0] in body_text:
            current_pattern_key = "10-K"
        elif patterns["10-K_alt1"][0] in body_text:
            current_pattern_key = "10-K_alt1"
        elif patterns["10-K_alt2"][0] in body_text:
            current_pattern_key = "10-K_alt2"

    if not current_pattern_key:
        return None, None
        
    pattern, item_type = patterns[current_pattern_key]
    start_tag = soup.find(lambda tag: pattern in tag.get_text(strip=True).lower())

    if not start_tag:
        return None, None

    # --- New Sibling Traversal Logic ---
    content_html = []
    # Regex to stop at the next "Item X.XX"
    next_item_regex = re.compile(r"item\s+\d+\.\d+", re.IGNORECASE)

    # Find the parent that is a direct child of 'body' if possible, to get a good starting point.
    # This avoids grabbing siblings from a deeply nested table cell.
    start_point = start_tag
    while start_point.parent and start_point.parent.name != 'body':
        start_point = start_point.parent

    # Traverse through siblings from this starting point
    for sibling in start_point.find_next_siblings():
        # If the sibling is a tag and contains the next item, stop.
        if sibling.name and next_item_regex.search(sibling.get_text(strip=True)):
            break
        content_html.append(str(sibling))

    if not content_html:
         # Fallback to the old method if sibling traversal yields nothing
        content_element = start_tag.find_parent("div") or start_tag.find_parent("p") or start_tag
        return str(content_element), item_type

    return "".join(content_html), item_type


def convert_html_to_markdown(html_content):
    """
    Converts an HTML string to Markdown using the markitdown CLI tool.
    """
    # markitdown works with files, so we use temporary files
    try:
        with open("temp_input.html", "w", encoding="utf-8") as f_in:
            f_in.write(html_content)

        # Execute markitdown, telling it to output to a file
        result = subprocess.run(
            ["markitdown", "temp_input.html", "-o", "temp_output.md"],
            capture_output=True, text=True, check=True
        )
        
        with open("temp_output.md", "r", encoding="utf-8") as f_out:
            markdown_content = f_out.read()
            
        return markdown_content

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Error during Markdown conversion: {e}")
        logging.error(f"Stderr: {e.stderr if isinstance(e, subprocess.CalledProcessError) else 'N/A'}")
        return "--- Conversion Failed ---"
    finally:
        # Clean up temporary files
        if os.path.exists("temp_input.html"):
            os.remove("temp_input.html")
        if os.path.exists("temp_output.md"):
            os.remove("temp_output.md")

def get_processed_filings():
    """Reads the set of processed filing accession numbers."""
    if not PROCESSED_FILINGS_PATH.exists():
        return set()
    with open(PROCESSED_FILINGS_PATH, "r") as f:
        return {line.strip() for line in f if line.strip()}


def process_filing(filing, form_type, processed_filings):
    """
    Processes a single filing: filters, parses, and saves it.
    """
    accession_no = filing.get('accessionNo')
    if not accession_no:
        logging.warning("Filing has no accession number, cannot process.")
        return

    if accession_no in processed_filings:
        logging.info(f"  -> Skipping already processed filing: {accession_no}")
        return

    ticker = filing.get('ticker')
    if not ticker:
        logging.warning(f"  -> Filing {accession_no} has no ticker, skipping.")
        return
        
    logging.info(f"Processing {form_type} for {ticker} filed on {filing['filingDate']}...")
    
    # datamule provides the filing in HTML format
    html_content = filing.get('content')
    if not html_content:
        logging.warning("  -> No content found, skipping.")
        return

    soup = BeautifulSoup(html_content, "lxml")
    
    relevant_html, item_type = find_relevant_section(soup, form_type)
    
    if not relevant_html:
        logging.info(f"  -> No relevant sections found in {form_type} for {ticker}. Discarding.")
        return

    logging.info(f"  -> Found relevant section (Item {item_type}). Converting to Markdown.")
    markdown_content = convert_html_to_markdown(relevant_html)

    # Prepare YAML frontmatter
    filing_date = pd.to_datetime(filing['filingDate']).strftime('%Y-%m-%d')
    year = pd.to_datetime(filing['filingDate']).year
    quarter = pd.to_datetime(filing['filingDate']).quarter

    metadata = {
        'ticker': ticker,
        'filing_type': form_type,
        'filing_date': filing_date,
        'item_type': item_type,
        'sec_link': filing.get('linkToFilingDetails', 'N/A'),
        'accession_no': accession_no
    }
    yaml_frontmatter = yaml.dump(metadata, sort_keys=False)

    # Construct file content and path
    output_content = f"---\n{yaml_frontmatter}---\n\n{markdown_content}"
    
    filename = f"{metadata['ticker']}_{metadata['filing_type']}_{metadata['filing_date']}_{accession_no}.md"
    output_dir = DATA_PATH / str(year) / f"Q{quarter}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    # Save the file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)
    logging.info(f"  -> Successfully saved to {output_path}")

    # Add to processed list
    with open(PROCESSED_FILINGS_PATH, "a") as f:
        f.write(f"{accession_no}\n")
    processed_filings.add(accession_no)


def get_recent_filings_by_date(portfolio, form_type, start_date, end_date, retries=3, backoff_factor=2):
    """
    Fetches all filings of a specific form type within a date range.
    """
    for attempt in range(retries):
        try:
            logging.info(f"Fetching all {form_type} filings from {start_date} to {end_date} (Attempt {attempt + 1}/{retries})...")
            # The portfolio name is just a local identifier, not used for filtering here
            filings = portfolio.download_submissions(
                submission_type=form_type,
                filing_date=(start_date, end_date),
                provider='datamule-sgml' # Use the fast provider
            )
            return filings
        except Exception as e:
            logging.warning(f"  -> Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2 ** attempt)
                logging.info(f"  -> Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logging.error(f"Failed to fetch {form_type} filings after {retries} attempts.")
                return None


def main():
    """
    Main execution function.
    """
    logging.info("--- Starting SEC Cybersecurity Filing Ingestion ---")
    # The name for the portfolio is a local identifier, can be anything.
    portfolio = Portfolio("cybersecurity_filings")
    portfolio.set_api_key(API_KEY)
    processed_filings = get_processed_filings()

    # Define the date range for the query (last 2 days to be safe)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    form_types_to_fetch = ["8-K", "10-K"]

    for form_type in form_types_to_fetch:
        logging.info(f"\nFetching recent {form_type} filings...")
        
        recent_filings = get_recent_filings_by_date(portfolio, form_type, start_date_str, end_date_str)

        if recent_filings:
            logging.info(f"Found {len(recent_filings)} recent {form_type} filings.")
            for filing in recent_filings:
                process_filing(filing, form_type, processed_filings)
        else:
            logging.info(f"  -> No recent {form_type} filings found for the period.")

    logging.info("\n--- Ingestion Process Complete ---")


if __name__ == "__main__":
    main()
