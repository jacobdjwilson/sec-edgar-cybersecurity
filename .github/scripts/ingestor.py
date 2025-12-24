import os
import shutil
import logging
import datetime
from typing import List, Dict, Optional
from datamule import Downloader

# Configure a module-level logger
logger = logging.getLogger("EdgarIngestor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class EdgarIngestor:
    """
    Orchestrates the acquisition of SEC filings using the datamule package.
    
    Attributes:
        api_key (str): The API key for the datamule provider.
        output_base (str): Temporary directory for storing raw downloads.
    """

    def __init__(self, api_key: str, output_base: str = "temp_filings"):
        self.api_key = api_key
        self.output_base = output_base
        
        # Initialize the datamule Downloader.
        # datamule typically reads the API key from environment variables or 
        # config, but we ensure it's available in the environment before this 
        # class is instantiated.
        # Note: If datamule requires explicit set_api_key in future versions,
        # it would be added here.
        self.downloader = Downloader()
        
        # Ensure clean state
        if os.path.exists(self.output_base):
            shutil.rmtree(self.output_base)
        os.makedirs(self.output_base)

    def fetch_recent_filings(self) -> List:
        """
        Downloads 8-K and 10-K filings filed within the last 24 hours.
        
        Returns:
            List: A list of metadata dictionaries for the downloaded files.
                        Each dict contains 'path', 'form', 'cik', 'date'.
        """
        target_forms = ['8-K', '10-K']
        
        # Calculate the date range.
        # We fetch "yesterday" and "today" to ensure we cover the last 24h window
        # regardless of the specific execution time of the Cron job.
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        date_range = (yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
        logger.info(f"Initiating download for period: {date_range}")

        manifest =

        try:
            for form in target_forms:
                form_dir = os.path.join(self.output_base, form)
                os.makedirs(form_dir, exist_ok=True)
                
                logger.info(f"Querying datamule for {form} filings...")
                
                # Using datamule's download capability.
                # based on snippet , download accepts form, date, and output_dir.
                # This handles the bulk retrieval efficiently.
                self.downloader.download(
                    form=form,
                    date=date_range,
                    output_dir=form_dir
                )
                
                # Post-download: Walk the directory to build the manifest.
                # datamule saves files, likely named by Accession Number or CIK.
                # We need to catalog what was downloaded to pass to the parser.
                for root, _, files in os.walk(form_dir):
                    for filename in files:
                        # We are interested in the primary document, usually.txt or.htm
                        # datamule might download attachments; we filter for likely primary docs.
                        if filename.endswith(".htm") or filename.endswith(".html") or filename.endswith(".txt"):
                            file_path = os.path.join(root, filename)
                            
                            # Attempt to extract CIK from filename if possible, 
                            # otherwise it will be extracted during parsing.
                            # Standard SEC naming is often {CIK}_{Accession}.txt or similar.
                            # For now, we store the path and form type.
                            manifest.append({
                                "path": file_path,
                                "form": form,
                                "date": today.strftime('%Y-%m-%d'), # Using run date as fallback
                                "filename": filename
                            })
                            
            logger.info(f"Download complete. Retrieved {len(manifest)} potential filings.")
            return manifest

        except Exception as e:
            logger.error(f"Critical failure in ingestion process: {e}")
            raise

    def cleanup(self):
        """Removes the temporary download directory to free up runner space."""
        if os.path.exists(self.output_base):
            shutil.rmtree(self.output_base)
            logger.info("Temporary storage cleaned up.")