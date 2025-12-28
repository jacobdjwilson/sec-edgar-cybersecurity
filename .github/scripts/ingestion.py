import datetime
from ingestion import downloader, parser, saver

def main():
    """
    Main function to run the daily ingestion process.
    """
    # Define date range (last 24 hours)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=1)

    # Download submissions
    filings_meta = downloader.download_submissions(start_date, end_date)

    # Process each filing
    for filing_meta in filings_meta:
        # Get the full submission details
        filing = downloader.get_submission(accession_number=filing_meta['accession_number'])
        
        # Parse the filing to get relevant sections in Markdown format
        parsed_sections = parser.parse_filing(filing)
        
        # Save the parsed sections to files
        if parsed_sections:
            saver.save_filing(filing, parsed_sections)

if __name__ == "__main__":
    main()