# c:\Users\jacob\Documents\GitHub\sec-edgar-cybersecurity\.github\scripts\ingest_filings.py
import os
import re
import yaml
from datetime import datetime, timedelta, timezone

# Assuming markitdown and datamule are installed
# You may need to install them: pip install markitdown datamule
import markitdown
from datamule import Edgar

# Load environment variables for local development
from dotenv import load_dotenv
load_dotenv()

# --- Constants ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'content', 'filings')
# Regex to find Item 1.05 in 8-K filings. This looks for "Item 1.05" and captures content 
# until the next "Item", "Signatures", or "Exhibit Index". It handles various whitespace and HTML tags.
# It is designed to be non-greedy.
REGEX_8K_ITEM_105 = re.compile(
    r'(<B>Item 1.05. Material Cybersecurity Incidents.</B>|Item 1.05. Material Cybersecurity Incidents.)(.*?)(<B>Item|SIGNATURES|EXHIBIT INDEX)',
    re.IGNORECASE | re.DOTALL
)

# Regex for 10-K Item 106 (Risk Management and Strategy)
REGEX_10K_ITEM_106 = re.compile(
    r'(<B>Item 106. Risk Management and Strategy</B>|Item 106. Risk Management and Strategy)(.*?)(<B>Item|SIGNATURES|EXHIBIT INDEX)',
    re.IGNORECASE | re.DOTALL
)

# Regex for 10-K Item 407(j) (Governance)
# This is more complex as it's a subsection. We'll look for "Item 407" and then "j".
REGEX_10K_ITEM_407J = re.compile(
    r'(<B>Item 407. Corporate Governance.</B>|Item 407. Corporate Governance.)(.*?)(<B>Item|SIGNATURES|EXHIBIT INDEX)',
    re.IGNORECASE | re.DOTALL
)


def get_quarter_from_date(date_obj):
    """Calculates the quarter (Q1, Q2, Q3, Q4) from a datetime object."""
    return f"Q{(date_obj.month - 1) // 3 + 1}"


def write_markdown_file(metadata, content):
    """
    Writes the disclosure content to a Markdown file with YAML frontmatter.
    """
    try:
        filing_date = datetime.strptime(metadata['Date'], '%Y-%m-%d')
        year = filing_date.year
        quarter = get_quarter_from_date(filing_date)

        # Create directory structure: YYYY/Q#
        target_dir = os.path.join(OUTPUT_DIR, str(year), quarter)
        os.makedirs(target_dir, exist_ok=True)

        # Create filename
        filename = f"{metadata['CIK']}_{metadata['Filing Type']}_{metadata['Date']}.md"
        filepath = os.path.join(target_dir, filename)

        # Combine frontmatter and content
        yaml_frontmatter = yaml.dump(metadata, sort_keys=False)
        full_content = f"---\n{yaml_frontmatter}---\n\n{content}"

        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"Successfully generated: {filepath}")

    except Exception as e:
        print(f"Error writing file for CIK {metadata.get('CIK', 'N/A')}: {e}")


def process_filing_content(filing_html, regex):
    """
    Uses regex to find a specific item in the filing's HTML content.
    """
    match = regex.search(filing_html)
    if not match:
        return None
    
    # Extract the content of the item
    content = match.group(2)
    if not content.strip():
        return None
        
    # Use markitdown to convert the extracted HTML/text to Markdown
    try:
        markdown_content = markitdown.convert(content)
        return markdown_content
    except Exception as e:
        print(f"markitdown conversion failed: {e}")
        return None


def main():
    """
    Main function to orchestrate the fetching, parsing, and storing of SEC filings.
    """
    print("Starting SEC Edgar Cybersecurity Disclosure Ingestion...")

    # 1. Initialize Edgar client from datamule
    api_key = os.getenv("DATA_MULE_API_KEY")
    if not api_key:
        print("Error: DATA_MULE_API_KEY environment variable not set.")
        return

    try:
        edgar = Edgar(api_key)
    except Exception as e:
        print(f"Failed to initialize Edgar client: {e}")
        return

    # 2. Define date range (last 24 hours)
    # Using timezone-aware datetime objects
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=1)
    
    print(f"Fetching filings from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # 3. Fetch recent 8-K and 10-K filings
    try:
        # Note: datamule might return a list of dicts. Adjust as per actual package behavior.
        recent_filings = edgar.get_filings(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            form_types=['8-K', '10-K']
        )
        print(f"Found {len(recent_filings)} filings to evaluate.")
    except Exception as e:
        print(f"Failed to fetch filings from datamule: {e}")
        return

    # 4. Process each filing
    for filing in recent_filings:
        try:
            filing_type = filing.get('form_type')
            filing_html = filing.get('document_html') # Assuming this is the key for the content

            if not filing_html:
                print(f"Skipping filing {filing.get('accession_number')} due to missing HTML content.")
                continue

            metadata = {
                'Ticker': filing.get('ticker', 'N/A'),
                'CIK': str(filing.get('cik')),
                'Date': filing.get('filing_date'),
                'Filing Type': filing_type,
                'Source Link': filing.get('url')
            }

            if filing_type == '8-K':
                content = process_filing_content(filing_html, REGEX_8K_ITEM_105)
                if content:
                    print(f"Found Item 1.05 in 8-K for CIK {metadata['CIK']}.")
                    write_markdown_file(metadata, content)

            elif filing_type == '10-K':
                # Check for Item 106
                content_106 = process_filing_content(filing_html, REGEX_10K_ITEM_106)
                if content_106:
                    print(f"Found Item 106 in 10-K for CIK {metadata['CIK']}.")
                    # Modify metadata for specificity if needed
                    meta_106 = metadata.copy()
                    meta_106['Tracked Item'] = '106'
                    write_markdown_file(meta_106, content_106)

                # Check for Item 407(j)
                content_407 = process_filing_content(filing_html, REGEX_10K_ITEM_407J)
                if content_407:
                    # Further refinement to find "(j)" within the Item 407 content
                    if re.search(r'\(j\)', content_407, re.IGNORECASE):
                         print(f"Found Item 407(j) in 10-K for CIK {metadata['CIK']}.")
                         meta_407 = metadata.copy()
                         meta_407['Tracked Item'] = '407(j)'
                         write_markdown_file(meta_407, content_407)

        except Exception as e:
            print(f"An error occurred processing filing {filing.get('accession_number', 'N/A')}: {e}")

    print("Ingestion process finished.")


if __name__ == "__main__":
    main()
