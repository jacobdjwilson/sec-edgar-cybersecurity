import os
import sys
import yaml
import logging
import datetime
from ingestor import EdgarIngestor
from parser import CyberParser

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Orchestrator")

# Constants
CONTENT_ROOT = "content/filings"
DATA_MULE_API_KEY = os.environ.get("DATA_MULE_API_KEY")

def generate_frontmatter(metadata: dict) -> str:
    """
    Constructs the YAML Frontmatter block for Hugo compatibility.
    """
    frontmatter = {
        "title": f"{metadata['ticker']} {metadata['form']} - {metadata['date']}",
        "date": metadata['date'],
        "ticker": metadata['ticker'],
        "cik": metadata['cik'],
        "filing_type": metadata['form'],
        "source_url": metadata.get('url', ''),
        "tags": ["cybersecurity", metadata['form'], "SEC"]
    }
    
    # Tagging specific rules for easier filtering in Hugo
    if metadata['form'] == '8-K':
        frontmatter['tags'].append("Item 1.05")
    elif metadata['form'] == '10-K':
        frontmatter['tags'].append("Item 106")
        
    return f"---\n{yaml.dump(frontmatter)}---\n"

def main():
    logger.info("Starting Daily SEC Cybersecurity Ingest...")

    if not DATA_MULE_API_KEY:
        logger.critical("DATA_MULE_API_KEY environment variable is missing.")
        sys.exit(1)

    # Initialize Components
    ingestor = EdgarIngestor(api_key=DATA_MULE_API_KEY)
    parser = CyberParser()

    try:
        # Phase 1: Acquisition
        # Fetch filings from the last 24 hours
        filings_meta = ingestor.fetch_recent_filings()
        
        if not filings_meta:
            logger.info("No filings found in the last 24h window.")
            return

        # Phase 2: Processing
        for meta in filings_meta:
            file_path = meta['path']
            form_type = meta['form']
            
            # Parse CIK and Ticker from filename or metadata
            # Assuming datamule filename format: {CIK}_{Accession}.txt
            # Ticker might need a separate lookup if not provided. 
            # For this implementation, we default Ticker to CIK if unknown,
            # or rely on datamule's metadata if available.
            filename = os.path.basename(file_path)
            cik = filename.split('_') if '_' in filename else "UNKNOWN"
            meta['cik'] = cik
            meta['ticker'] = cik # Placeholder if Ticker mapping not available in this scope
            meta['url'] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{filename}"

            logger.info(f"Inspecting {filename} ({form_type})...")

            # Phase 3: Intelligence & Transformation
            markdown_content = parser.process_filing(file_path, form_type)
            
            if markdown_content:
                # Phase 4: Persistence
                # Organize by Year/Quarter/Filename
                date_obj = datetime.datetime.strptime(meta['date'], '%Y-%m-%d')
                year = date_obj.strftime('%Y')
                quarter = f"Q{(date_obj.month-1)//3 + 1}"
                
                output_dir = os.path.join(CONTENT_ROOT, year, quarter)
                os.makedirs(output_dir, exist_ok=True)
                
                # Ensure section _index.md files exist for Hugo [20]
                # We can create them lazily if they don't exist.
                
                output_filename = f"{cik}_{form_type}_{meta['date']}.md"
                output_path = os.path.join(output_dir, output_filename)
                
                full_doc = generate_frontmatter(meta) + "\n" + markdown_content
                
                with open(output_path, "w", encoding='utf-8') as out_f:
                    out_f.write(full_doc)
                    
                logger.info(f"SUCCESS: Generated report at {output_path}")
            else:
                logger.debug(f"Discarded {filename} (No relevant items found).")

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup temp files
        ingestor.cleanup()

if __name__ == "__main__":
    main()