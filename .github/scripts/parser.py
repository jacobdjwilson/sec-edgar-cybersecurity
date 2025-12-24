import re
import os
import logging
from typing import Optional, List
from bs4 import BeautifulSoup
from markitdown import MarkItDown

logger = logging.getLogger("CyberParser")
logger.setLevel(logging.INFO)

class CyberParser:
    """
    Responsible for parsing raw SEC filing HTML/SGML.
    Identifies specific cybersecurity Items and converts them to Markdown.
    """

    def __init__(self):
        # Initialize the MarkItDown converter 
        self.md = MarkItDown()
        
        # Compile Regex patterns for performance
        # Item 1.05: Material Cybersecurity Incidents (8-K)
        # We look for "Item" followed by "1.05" with flexible spacing/punctuation.
        self.regex_8k_item = re.compile(
            r'Item\s+1\.05\.?\s+Material\s+Cybersecurity\s+Incidents', 
            re.IGNORECASE
        )
        
        # Item 106: Cybersecurity (10-K)
        # Usually listed as "Item 1C. Cybersecurity" in the Table of Contents 
        # and the body. We target the body header.
        self.regex_10k_item = re.compile(
            r'Item\s+1C\.?\s+Cybersecurity', 
            re.IGNORECASE
        )

    def process_filing(self, file_path: str, form_type: str) -> Optional[str]:
        """
        Main entry point for parsing.
        
        Args:
            file_path: Path to the raw downloaded file.
            form_type: '8-K' or '10-K'.
            
        Returns:
            str: The converted Markdown content if the Item is found.
            None: If the Item is not present (Noise filtering).
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                raw_content = f.read()

            if form_type == '8-K':
                return self._parse_8k(raw_content)
            elif form_type == '10-K':
                return self._parse_10k(raw_content)
            else:
                return None

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _parse_8k(self, content: str) -> Optional[str]:
        """
        Filters 8-K filings for Item 1.05.
        """
        # Step 1: Detection
        match = self.regex_8k_item.search(content)
        if not match:
            logger.debug("8-K skipped: Item 1.05 not found.")
            return None
        
        logger.info("8-K HIT: Found Item 1.05.")
        
        # Step 2: Extraction Strategy
        # 8-Ks are relatively short. We can often convert the whole document 
        # and then extract, OR slice HTML.
        # Given the "Material" nature, context is key. We will attempt to
        # convert the whole document to Markdown, but verify the Item 1.05 presence.
        # This preserves the full context of the disclosure which is often brief.
        
        # To use MarkItDown on a string, we might need a temp file helper
        # or check if the library supports string input. 
        # The snippets show `md.convert(file_path)`. 
        # We already have the file on disk (file_path in process_filing), 
        # but here we have the content string. 
        # It's better to pass the original file path to MarkItDown if possible,
        # but we need to ensure we only return the RELEVANT section if requested.
        
        # For 8-K Item 1.05, it is best to provide the specific section.
        # We will slice the HTML from the Item 1.05 header to the next Item or Signature.
        
        sliced_html = self._slice_html_section(
            content, 
            self.regex_8k_item, 
           
        )
        
        return self._convert_to_markdown(sliced_html)

    def _parse_10k(self, content: str) -> Optional[str]:
        """
        Filters 10-K filings for Item 1C (Risk/Governance).
        """
        # Step 1: Detection
        match = self.regex_10k_item.search(content)
        if not match:
            logger.debug("10-K skipped: Item 1C not found.")
            return None
            
        logger.info("10-K HIT: Found Item 1C.")
        
        # Step 2: Extraction
        # 10-Ks are huge. We MUST slice the HTML before conversion to Markdown
        # to ensure MarkItDown processes it efficiently and the output is readable.
        # Start: Item 1C
        # End: Item 2 (Properties) or Item 1B (Unresolved Staff Comments)
        
        sliced_html = self._slice_html_section(
            content,
            self.regex_10k_item,
           
        )
        
        return self._convert_to_markdown(sliced_html)

    def _slice_html_section(self, html: str, start_regex, end_patterns: List[str]) -> str:
        """
        Advanced slicing logic using BeautifulSoup and Regex.
        Finds the start node matching the regex, and collects siblings until
        a node matches one of the end patterns.
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # This is a simplified heuristic. EDGAR HTML is notoriously messy.
        # A robust production version would iterate through text nodes.
        # For this implementation, we will use a text-based find in the soup text
        # to locate the approximate position, or use a naive string slice fallback
        # if the DOM parsing is too complex for the structure.
        
        # Fallback Strategy: String Slicing (More robust for messy EDGAR HTML)
        # We use the regex to find the start index in the raw string.
        match = start_regex.search(html)
        if not match:
            return html # Should not happen given Detection step
            
        start_idx = match.start()
        
        # Find the earliest occurrence of any end pattern AFTER the start
        end_idx = len(html)
        for pattern in end_patterns:
            end_regex = re.compile(pattern, re.IGNORECASE)
            end_match = end_regex.search(html, pos=start_idx + 100) # Offset to avoid self-match
            if end_match:
                if end_match.start() < end_idx:
                    end_idx = end_match.start()
                    
        return html[start_idx:end_idx]

    def _convert_to_markdown(self, html_content: str) -> str:
        """
        Wraps Microsoft MarkItDown interaction.
        Writes the HTML slice to a temp file, converts it, then reads it back.
        """
        temp_input = "temp_slice.html"
        try:
            with open(temp_input, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Use MarkItDown to convert the temp file
            result = self.md.convert(temp_input)
            
            # Clean up
            if os.path.exists(temp_input):
                os.remove(temp_input)
                
            return result.text_content
            
        except Exception as e:
            logger.error(f"MarkItDown conversion failed: {e}")
            # Fallback: simple text extraction if MarkItDown fails
            return BeautifulSoup(html_content, "lxml").get_text()