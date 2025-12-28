import os
import datetime
import json
import re

from datamule import Portfolio
from markitdown import MarkItDown

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
        "ticker": filing.get("ticker", "N/A"),
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

    file_name = f"{filing['cik']}_{filing['filing_date'].replace('-', '')}_{filing_type_dir}_{section_item}.md"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved: {file_path}")

def main():
    # Initialize clients
    api_key = os.environ.get("DATAMULE_API_KEY")
    if not api_key:
        raise ValueError("DATAMULE_API_KEY environment variable not set.")
    
    portfolio = Portfolio(api_key=api_key)
    markitdown_parser = Markitdown()

    # Define date range (last 24 hours)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=1)

    filings = portfolio.download_submissions(
        start_date=start_date.isoformat(), 
        end_date=end_date.isoformat()
    )

    for filing_meta in filings:
        filing = portfolio.get_submission(accession_number=filing_meta['accession_number'])
        filing_type = filing["filing_type"]
        
        # This part is a bit of a guess, assuming get_submission returns a dict with sections
        sections = filing.get("sections", {})

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
