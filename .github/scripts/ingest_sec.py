
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
from datetime import datetime

# --- Configuration ---
# Get API key from environment variable
API_KEY = os.getenv("DATA_MULE_API_KEY")
if not API_KEY:
    raise ValueError("DATA_MULE_API_KEY environment variable not set.")

# Base paths
# The script is in .github/scripts, so we need to go up two levels for the repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "data"
WATCHLIST_PATH = REPO_ROOT / ".github" / "scripts" / "watchlist.txt"

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


def get_watchlist():
    """Reads tickers from the watchlist file."""
    if not WATCHLIST_PATH.exists():
        logging.error(f"Watchlist not found at: {WATCHLIST_PATH}")
        raise FileNotFoundError(f"Watchlist not found at: {WATCHLIST_PATH}")
    with open(WATCHLIST_PATH, "r") as f:
        # Read, strip whitespace, and filter out empty lines
        tickers = [line.strip() for line in f if line.strip()]
    logging.info(f"Loaded {len(tickers)} tickers from watchlist.")
    return tickers


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

    logging.info(f"Processing {form_type} for {filing['ticker']} filed on {filing['filingDate']}...")
    
    # datamule provides the filing in HTML format
    html_content = filing.get('content')
    if not html_content:
        logging.warning("  -> No content found, skipping.")
        return

    soup = BeautifulSoup(html_content, "lxml")
    
    relevant_html, item_type = find_relevant_section(soup, form_type)
    
    if not relevant_html:
        logging.info(f"  -> No relevant sections found in {form_type} for {filing['ticker']}. Discarding.")
        return

    logging.info(f"  -> Found relevant section (Item {item_type}). Converting to Markdown.")
    markdown_content = convert_html_to_markdown(relevant_html)

    # Prepare YAML frontmatter
    filing_date = pd.to_datetime(filing['filingDate']).strftime('%Y-%m-%d')
    year = pd.to_datetime(filing['filingDate']).year
    quarter = pd.to_datetime(filing['filingDate']).quarter

    metadata = {
        'ticker': filing['ticker'],
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


def get_filings_with_retry(portfolio, ticker, form_type, retries=3, backoff_factor=2):
    """
    Fetches filings with a retry mechanism for handling transient errors.
    """
    for attempt in range(retries):
        try:
            logging.info(f"Fetching {form_type} for {ticker} (Attempt {attempt + 1}/{retries})...")
            filings = portfolio.get_filings(ticker=ticker, form_type=form_type, limit=5 if form_type == "8-K" else 2)
            return filings
        except Exception as e:
            logging.warning(f"  -> Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                sleep_time = backoff_factor * (2 ** attempt)
                logging.info(f"  -> Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logging.error(f"Failed to fetch filings for {ticker} after {retries} attempts.")
                return None


def main():
    """
    Main execution function.
    """
    logging.info("--- Starting SEC Cybersecurity Filing Ingestion ---")
    portfolio = Portfolio(API_KEY)
    tickers = get_watchlist()
    processed_filings = get_processed_filings()

    for ticker in tickers:
        logging.info(f"\nFetching filings for ticker: {ticker}")
        try:
            # Fetch recent 8-K filings
            recent_8ks = get_filings_with_retry(portfolio, ticker, "8-K")
            if recent_8ks:
                for filing in recent_8ks:
                    process_filing(filing, "8-K", processed_filings)
            else:
                logging.info(f"  -> No recent 8-K filings found for {ticker}.")

            # Fetch recent 10-K filings
            recent_10ks = get_filings_with_retry(portfolio, ticker, "10-K")
            if recent_10ks:
                for filing in recent_10ks:
                    process_filing(filing, "10-K", processed_filings)
            else:
                logging.info(f"  -> No recent 10-K filings found for {ticker}.")

        except Exception as e:
            logging.error(f"An error occurred while processing ticker {ticker}: {e}")

    logging.info("\n--- Ingestion Process Complete ---")

if __name__ == "__main__":
    main()
