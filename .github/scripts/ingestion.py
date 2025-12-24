import os
import datetime
import json
import re

# Assuming datamule and markitdown are installed
# from datamule import Client # Placeholder for actual datamule import
# from markitdown import Markitdown # Placeholder for actual markitdown import

# Mock classes for datamule and markitdown for initial scaffolding
class MockDatamuleClient:
    def __init__(self, api_key):
        self.api_key = api_key
        print(f"Datamule client initialized with API key: {api_key[:4]}...")

    def get_filings(self, start_date, end_date):
        print(f"Fetching filings from {start_date} to {end_date}")
        # Mock data for demonstration
        mock_filings = [
            {
                "cik": "0000100000",
                "ticker": "EXAMPLEA",
                "filing_type": "8-K",
                "filing_date": "2023-10-26",
                "accession_number": "0000100000-23-000001",
                "html_url": "https://www.sec.gov/Archives/edgar/data/100000/000010000023000001/examplea-20231025.htm",
                "sections": {
                    "1.05": "<p>This is a <strong>mock</strong> Item 1.05 disclosure about a material cybersecurity incident.</p><p>More details here.</p>"
                }
            },
            {
                "cik": "0000200000",
                "ticker": "EXAMPLEB",
                "filing_type": "10-K",
                "filing_date": "2023-10-25",
                "accession_number": "0000200000-23-000002",
                "html_url": "https://www.sec.gov/Archives/edgar/data/200000/000020000023000002/exampleb-20230930.htm",
                "sections": {
                    "1A": "<p>Risk Factors content</p>",
                    "106": "<p>This is a <strong>mock</strong> Item 106 disclosure about risk management and strategy.</p><p>Cybersecurity risks are managed effectively.</p>",
                    "407j": "<p>This is a <strong>mock</strong> Item 407j disclosure about governance.</p><p>The board oversees cybersecurity risks.</p>"
                }
            },
            {
                "cik": "0000300000",
                "ticker": "EXAMPLEC",
                "filing_type": "8-K",
                "filing_date": "2023-10-24",
                "accession_number": "0000300000-23-000003",
                "html_url": "https://www.sec.gov/Archives/edgar/data/300000/000030000023000003/examplec-20231023.htm",
                "sections": {
                    "2.02": "<p>Results of Operations</p>" # No Item 1.05
                }
            }
        ]
        return mock_filings

class MockMarkitdown:
    def convert_html_to_md(self, html_content):
        print("Converting HTML to Markdown...")
        # Simple mock conversion, in a real scenario this would use markitdown's logic
        return html_content.replace("<p>", "").replace("</p>", "\n\n").replace("<strong>", "**").replace("</strong>", "**")

def get_quarter(month):
    if 1 <= month <= 3:
        return "Q1"
    elif 4 <= month <= 6:
        return "Q2"
    elif 7 <= month <= 9:
        return "Q3"
    else:
        return "Q4"

def generate_markdown_content(filing, section_item, markdown_content):
    frontmatter = {
        "ticker": filing["ticker"],
        "cik": filing["cik"],
        "date": filing["filing_date"],
        "filing_type": filing["filing_type"],
        "source_link": filing["html_url"],
    }
    frontmatter_str = "---\n" + "\n".join([f"{key}: {value}" for key, value in frontmatter.items()]) + "\n---\n\n"
    
    section_title_map = {
        "1.05": "Item 1.05. Material Cybersecurity Incidents",
        "106": "Item 106. Risk Management & Strategy",
        "407j": "Item 407j. Governance"
    }
    section_title = section_title_map.get(section_item, f"Item {section_item}")

    return f"{frontmatter_str}## {section_title}\n\n{markdown_content}"

def save_markdown_file(filing, section_item, content):
    filing_date = datetime.datetime.strptime(filing["filing_date"], "%Y-%m-%d")
    year = filing_date.year
    quarter = get_quarter(filing_date.month)
    filing_type_dir = filing["filing_type"].replace("-", "") # e.g., 8K or 10K

    output_dir = os.path.join("data", filing_type_dir, str(year), quarter)
    os.makedirs(output_dir, exist_ok=True)

    file_name = f"{filing["cik"]}_{filing["filing_date"].replace("-", "")}_{filing_type_dir}_{section_item}.md"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved: {file_path}")

def main():
    # Load API Key
    data_mule_api_key = os.environ.get("DATA_MULE_API_KEY")
    if not data_mule_api_key:
        raise ValueError("DATA_MULE_API_KEY environment variable not set.")

    # Initialize clients
    datamule_client = MockDatamuleClient(data_mule_api_key) # Replace with actual Client(data_mule_api_key)
    markitdown_parser = MockMarkitdown() # Replace with actual Markitdown()

    # Define date range (last 24 hours)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=1)

    filings = datamule_client.get_filings(start_date.isoformat(), end_date.isoformat())

    for filing in filings:
        filing_type = filing["filing_type"]
        sections = filing.get("sections", {}) # Ensure sections key exists

        if filing_type == "8-K":
            if "1.05" in sections:
                html_content = sections["1.05"]
                markdown_content = markitdown_parser.convert_html_to_md(html_content)
                full_markdown = generate_markdown_content(filing, "1.05", markdown_content)
                save_markdown_file(filing, "1.05", full_markdown)

        elif filing_type == "10-K":
            relevant_10k_sections = {}
            if "106" in sections:
                relevant_10k_sections["106"] = sections["106"]
            if "407j" in sections:
                relevant_10k_sections["407j"] = sections["407j"]
            
            if relevant_10k_sections:
                for section_item, html_content in relevant_10k_sections.items():
                    markdown_content = markitdown_parser.convert_html_to_md(html_content)
                    full_markdown = generate_markdown_content(filing, section_item, markdown_content)
                    save_markdown_file(filing, section_item, full_markdown)

if __name__ == "__main__":
    main()
