import datetime
from datamule import Portfolio

def download_submissions(start_date, end_date):
    """
    Downloads SEC submissions for a given date range.

    Args:
        start_date (datetime.date): The start date of the range.
        end_date (datetime.date): The end date of the range.

    Returns:
        list: A list of filing metadata dictionaries.
    """
    portfolio = Portfolio(provider='datamule-tar')
    filings = portfolio.download_submissions(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat()
    )
    return filings

def get_submission(accession_number):
    """
    Retrieves a single submission.

    Args:
        accession_number (str): The accession number of the submission.

    Returns:
        dict: The submission data.
    """
    portfolio = Portfolio(provider='datamule-tar')
    return portfolio.get_submission(accession_number=accession_number)
