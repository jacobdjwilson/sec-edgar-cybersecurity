import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Make sure the script can be imported
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / '.github' / 'scripts'))
from ingest_sec import get_watchlist, find_relevant_section, process_filing

@pytest.fixture
def temp_watchlist(tmp_path):
    """Create a temporary watchlist file for testing."""
    watchlist_content = "AAPL\nMSFT\nGOOG"
    watchlist_file = tmp_path / "watchlist.txt"
    watchlist_file.write_text(watchlist_content)
    return watchlist_file

def test_get_watchlist(temp_watchlist):
    """Test that the watchlist is read correctly."""
    with patch('ingest_sec.WATCHLIST_PATH', temp_watchlist):
        tickers = get_watchlist()
        assert tickers == ["AAPL", "MSFT", "GOOG"]

# HTML sample for testing find_relevant_section
SAMPLE_8K_HTML = """
<html>
<body>
    <p>Some preliminary text.</p>
    <p><b>Item 1.05 Material Cybersecurity Incidents.</b></p>
    <p>On December 15, 2025, we detected a breach.</p>
    <p>Here are the details...</p>
    <p><b>Item 1.06 Other Events.</b></p>
    <p>Some other event.</p>
</body>
</html>
"""

def test_find_relevant_section_8k():
    """Test finding the relevant section in an 8-K filing."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(SAMPLE_8K_HTML, 'lxml')
    section, item_type = find_relevant_section(soup, '8-K')
    assert item_type == "1.05"
    assert "On December 15, 2025, we detected a breach." in section
    assert "Item 1.06" not in section # Make sure it stops at the next item

@patch('ingest_sec.subprocess.run')
def test_process_filing_integration(mock_subprocess_run, tmp_path):
    """Integration test for process_filing."""
    # Mock the return value of the markitdown conversion
    mock_subprocess_run.return_value.stdout = "Converted Markdown"
    
    # Load the sample HTML fixture
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "sample_8k.html"
    with open(fixture_path, "r") as f:
        html_content = f.read()

    # Create a mock filing object
    mock_filing = {
        'ticker': 'TEST',
        'filingDate': '2025-12-24',
        'formType': '8-K',
        'content': html_content,
        'linkToFilingDetails': 'http://example.com'
    }

    # Patch the DATA_PATH to use the temporary directory
    with patch('ingest_sec.DATA_PATH', tmp_path):
        process_filing(mock_filing, '8-K')

        # Check that the output file was created
        expected_dir = tmp_path / "2025" / "Q4"
        expected_file = expected_dir / "TEST_8-K_2025-12-24.md"
        assert expected_file.exists()

        # Check the content of the file
        content = expected_file.read_text()
        assert "ticker: TEST" in content
        assert "filing_type: 8-K" in content
        assert "filing_date: 2025-12-24" in content
        assert "item_type: '1.05'" in content
        assert "sec_link: http://example.com" in content
        # This is the mocked output of markitdown
        assert "--- Conversion Failed ---" not in content
