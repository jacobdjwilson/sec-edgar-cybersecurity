import os
import yaml
import datetime
from datamule import Edgar

# Initialize the Edgar class from datamule
try:
    edgar = Edgar()
except Exception as e:
    print(f"Failed to initialize Edgar: {e}")
    exit(1)

def create_markdown_file(filing_data, filing_type):
    """Creates a markdown file for a given filing."""

    # Extract relevant data from the filing
    company_name = filing_data.get("name")
    ticker = filing_data.get("ticker")
    website = filing_data.get("website")
    cik = filing_data.get("CIK")
    sic_description = filing_data.get("SIC")
    filing_number = filing_data.get("filing_number")
    filing_date = filing_data.get("date")
    source_link = filing_data.get("source_link")

    # Determine the directory path
    date_obj = datetime.datetime.strptime(filing_date, "%Y-%m-%d")
    year = date_obj.year
    quarter = (date_obj.month - 1) // 3 + 1
    directory = f"data/{filing_type}/{year}/Q{quarter}/"

    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Define the markdown file structure
    file_path = f"{directory}/{cik}_{filing_date}_{filing_type}.md"
    frontmatter = {
        "name": company_name,
        "ticker": ticker,
        "website": website,
        "category": "Cybersecurity Disclosure",
        "CIK": cik,
        "SIC": sic_description,
        "filing_number": filing_number,
        "date": filing_date,
        "filing_type": filing_type,
        "filling_quarter": f"Q{quarter}",
        "filling_year": year,
        "source_link": source_link,
    }

    # Extract the relevant section from the filing
    content = ""
    if filing_type == "8-K":
        content = filing_data.get("item_1_05_material_cybersecurity_incidents", "")
    elif filing_type == "10-K":
        item_106 = filing_data.get("item_106_risk_management_and_strategy", "")
        item_407j = filing_data.get("item_407j_governance", "")
        content = f"## Item 106. Risk Management and Strategy\n\n{item_106}\n\n## Item 407(j). Governance\n\n{item_407j}"


    # Write the content to the markdown file
    with open(file_path, "w") as f:
        f.write("---")
        yaml.dump(frontmatter, f)
        f.write("---")
        f.write(content)

    print(f"Successfully created markdown file: {file_path}")

def main():
    """Main function to fetch and process SEC filings."""

    # Get today's date
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Fetch 8-K filings for material cybersecurity incidents
    try:
        new_8k_filings = edgar.get_filings(
            filing_type="8-K",
            item="1.05",
            start_date=yesterday.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d")
        )
        for filing in new_8k_filings:
            create_markdown_file(filing, "8-K")
    except Exception as e:
        print(f"Failed to get 8-K filings: {e}")


    # Fetch 10-K filings for risk management and governance
    try:
        new_10k_filings = edgar.get_filings(
            filing_type="10-K",
            item=["106", "407j"],
            start_date=yesterday.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d")
        )
        for filing in new_10k_filings:
            create_markdown_file(filing, "10-K")
    except Exception as e:
        print(f"Failed to get 10-K filings: {e}")

if __name__ == "__main__":
    main()
