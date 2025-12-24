
import os
import re
import yaml
import subprocess
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from datamule import Edgar
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

# Keywords for filtering 10-K filings (case-insensitive)
TEN_K_KEYWORDS = ["item 1c", "cybersecurity", "item 407(j)"]


def get_watchlist():
    """Reads tickers from the watchlist file."""
    if not WATCHLIST_PATH.exists():
        raise FileNotFoundError(f"Watchlist not found at: {WATCHLIST_PATH}")
    with open(WATCHLIST_PATH, "r") as f:
        # Read, strip whitespace, and filter out empty lines
        tickers = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(tickers)} tickers from watchlist.")
    return tickers


def find_relevant_section(soup, form_type):
    """
    Finds the relevant HTML section within a filing using BeautifulSoup.
    Returns the HTML content of the section and the identified item type.
    """
    body_text = soup.get_text().lower()
    item_type = None

    if form_type == "8-K":
        if "item 1.05" in body_text:
            item_type = "1.05"
            # Find the element containing "Item 1.05" and get its parent or sibling content
            # This is a heuristic and might need refinement
            tag = soup.find(lambda t: "item 1.05" in t.get_text(strip=True).lower())
            if tag:
                # Heuristic: find the nearest table or series of paragraphs after the item tag
                content_element = tag.find_parent("div") or tag.find_parent("p") or tag
                return str(content_element), item_type
    
    elif form_type == "10-K":
        for keyword in TEN_K_KEYWORDS:
            if keyword in body_text:
                if "item 1c" in keyword:
                    item_type = "106"  # Per prompt instructions
                elif "407(j)" in keyword:
                    item_type = "407(j)"
                else: # cybersecurity
                    item_type = "Risk Management"
                
                tag = soup.find(lambda t: keyword in t.get_text(strip=True).lower())
                if tag:
                    content_element = tag.find_parent("div") or tag.find_parent("p") or tag
                    return str(content_element), item_type

    return None, None


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
        print(f"Error during Markdown conversion: {e}")
        print(f"Stderr: {e.stderr if isinstance(e, subprocess.CalledProcessError) else 'N/A'}")
        return "--- Conversion Failed ---"
    finally:
        # Clean up temporary files
        if os.path.exists("temp_input.html"):
            os.remove("temp_input.html")
        if os.path.exists("temp_output.md"):
            os.remove("temp_output.md")

def process_filing(filing, form_type):
    """
    Processes a single filing: filters, parses, and saves it.
    """
    print(f"Processing {form_type} for {filing['ticker']} filed on {filing['filingDate']}...")
    
    # datamule provides the filing in HTML format
    html_content = filing.get('content')
    if not html_content:
        print("  -> No content found, skipping.")
        return

    soup = BeautifulSoup(html_content, "lxml")
    
    relevant_html, item_type = find_relevant_section(soup, form_type)
    
    if not relevant_html:
        print(f"  -> No relevant sections found in {form_type} for {filing['ticker']}. Discarding.")
        return

    print(f"  -> Found relevant section (Item {item_type}). Converting to Markdown.")
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
        'sec_link': filing.get('linkToFilingDetails', 'N/A')
    }
    yaml_frontmatter = yaml.dump(metadata, sort_keys=False)

    # Construct file content and path
    output_content = f"---\n{yaml_frontmatter}---\n\n{markdown_content}"
    
    filename = f"{metadata['ticker']}_{metadata['filing_type']}_{metadata['filing_date']}.md"
    output_dir = DATA_PATH / str(year) / f"Q{quarter}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    # Save the file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)
    print(f"  -> Successfully saved to {output_path}")


def main():
    """
    Main execution function.
    """
    print("--- Starting SEC Cybersecurity Filing Ingestion ---")
    edgar = Edgar(API_KEY)
    tickers = get_watchlist()

    for ticker in tickers:
        print(f"\nFetching filings for ticker: {ticker}")
        try:
            # Fetch recent 8-K filings
            recent_8ks = edgar.get_filings(ticker=ticker, form_type="8-K", limit=5)
            if recent_8ks:
                for filing in recent_8ks:
                    process_filing(filing, "8-K")
            else:
                print(f"  -> No recent 8-K filings found for {ticker}.")

            # Fetch recent 10-K filings
            recent_10ks = edgar.get_filings(ticker=ticker, form_type="10-K", limit=2)
            if recent_10ks:
                for filing in recent_10ks:
                    process_filing(filing, "10-K")
            else:
                print(f"  -> No recent 10-K filings found for {ticker}.")

        except Exception as e:
            print(f"An error occurred while processing ticker {ticker}: {e}")

    print("\n--- Ingestion Process Complete ---")

if __name__ == "__main__":
    main()
