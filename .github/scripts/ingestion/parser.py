from markitdown import MarkItDown

def _generate_markdown_content(filing, section_item, markdown_content):
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

def parse_filing(filing):
    """
    Parses a filing, converts relevant sections to Markdown, and generates final content.

    Args:
        filing (dict): The filing data.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              'section_item' and 'content' for a parsed section.
    """
    markitdown_parser = MarkItDown()
    filing_type = filing["filing_type"]
    sections = filing.get("sections", {})
    parsed_sections = []

    if filing_type == "8-K":
        if "1.05" in sections:
            html_content = sections["1.05"]
            markdown_content = markitdown_parser.convert_html_to_md(html_content)
            full_markdown = _generate_markdown_content(filing, "1.05", markdown_content)
            parsed_sections.append({"section_item": "1.05", "content": full_markdown})

    elif filing_type == "10-K":
        relevant_10k_sections = {}
        if "106" in sections:
            relevant_10k_sections["106"] = sections["106"]
        if "407j" in sections:
            relevant_10k_sections["407j"] = sections["407j"]
        
        for section_item, html_content in relevant_10k_sections.items():
            markdown_content = markitdown_parser.convert_html_to_md(html_content)
            full_markdown = _generate_markdown_content(filing, section_item, markdown_content)
            parsed_sections.append({"section_item": section_item, "content": full_markdown})
            
    return parsed_sections
