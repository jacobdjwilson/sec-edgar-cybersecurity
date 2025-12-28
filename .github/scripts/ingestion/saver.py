import os
import datetime
from .utils import get_quarter

def save_filing(filing, parsed_sections):
    """
    Saves the parsed sections of a filing to Markdown files.

    Args:
        filing (dict): The filing metadata.
        parsed_sections (list): A list of parsed sections to save.
    """
    filing_date = datetime.datetime.strptime(filing["filing_date"], "%Y-%m-%d")
    year = filing_date.year
    quarter = get_quarter(filing_date.month)
    filing_type_dir = filing["filing_type"].replace("-", "")

    output_dir = os.path.join("data", filing_type_dir, str(year), quarter)
    os.makedirs(output_dir, exist_ok=True)

    for section in parsed_sections:
        section_item = section["section_item"]
        content = section["content"]
        file_name = f"{filing['cik']}_{filing['filing_date'].replace('-', '')}_{filing_type_dir}_{section_item}.md"
        file_path = os.path.join(output_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved: {file_path}")
