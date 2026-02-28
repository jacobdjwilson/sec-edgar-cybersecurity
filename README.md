# SEC EDGAR Cybersecurity Disclosures

## Project Mission

This project aims to build a serverless, automated data pipeline that continuously monitors, downloads, and parses SEC filings to generate a clean, open-source dataset of corporate cybersecurity disclosures. The entire system operates within the GitHub ecosystem using GitHub Actions for automation.

## SEC Cybersecurity Rules Tracked

This system specifically targets the SEC's 2023 cybersecurity rules, focusing on the following key areas:

*   **Material Cybersecurity Incidents (8-K filings, specifically Item 1.05):** Companies are required to disclose material cybersecurity incidents within four business days of determining materiality.
*   **Risk Management & Strategy (10-K filings, specifically Item 106):** Companies must describe their processes for assessing, identifying, and managing material risks from cybersecurity threats, and the role of the board of directors in overseeing these risks.
*   **Governance (10-K filings, specifically Item 407(j)):** Companies must describe the board's oversight of cybersecurity risks and management's role and expertise in assessing and managing those risks.

## Technology Stack

This project leverages:
- **[datamule](https://github.com/john-friedman/datamule-python)** - A Python package for working with SEC filings at scale, developed by [John Friedman](https://datamule.xyz/about)
- **GitHub Actions** - For automated workflows and scheduling
- **Python 3.11+** - Core processing language
- **BeautifulSoup4 & lxml** - HTML/XML parsing
- **html2text** - Converting HTML filings to clean Markdown
- **PyYAML** - YAML frontmatter generation

## Setup Instructions

### Prerequisites

1. **GitHub Repository**: Fork or clone this repository
2. **GitHub Secrets**: Configure the following secret in your repository settings (Settings → Secrets and variables → Actions):
   - `DATAMULE_API_KEY` - Your datamule API key (optional but recommended for faster downloads without rate limits)
   - To get a datamule API key, visit [datamule.xyz](https://datamule.xyz/)

### Installation

The GitHub Actions workflows automatically install all required dependencies. For local development, install:

```bash
pip install -r requirements.txt
```

### Required Dependencies

```
datamule>=0.1.0          # SEC filing access and management
pandas>=2.0.0            # Data manipulation and analysis
pyyaml>=6.0              # YAML frontmatter parsing
lxml>=4.9.0              # XML/HTML parsing
beautifulsoup4>=4.12.0   # HTML parsing and cleaning
requests>=2.31.0         # HTTP requests
html2text>=2020.1.16     # HTML to Markdown conversion
jsonschema>=3.2.0        # JSON schema validation
```

## How the Pipeline Works

### Automated Workflows

#### 1. Daily Ingestion (`daily-ingestion.yml`)
- **Schedule**: Runs daily at 6:00 AM ET (11:00 AM UTC)
- **Trigger**: Automatic via cron schedule, or manual via workflow_dispatch
- **Process**:
  1. Downloads 8-K filings from the previous day
  2. Parses Item 1.05 (Material Cybersecurity Incidents) disclosures
  3. Downloads 10-K filings from the last 7 days
  4. Parses Item 106 and Item 407(j) disclosures
  5. Generates statistics and summaries
  6. Commits new data to the repository
  7. Creates a GitHub issue with daily summary

#### 2. Historical Backfill (`backfill.yml`)
- **Trigger**: Manual via workflow_dispatch only
- **Purpose**: Download and parse historical filings for a specified date range
- **Options**:
  - Start year and end year
  - Filing type (8-K, 10-K, or both)
  - Option to use datamule provider for faster downloads (costs $1/100k downloads)

#### 3. Data Validation (`data-validation.yml`)
- **Trigger**: Runs on pull requests and pushes that modify data files
- **Checks**:
  - YAML frontmatter validation
  - Required fields verification
  - Duplicate detection
  - Data integrity checks

### Pipeline Scripts

All automation scripts are located in `.github/scripts/`:

| Script | Purpose |
|--------|---------|
| `configure_datamule.py` | Configure datamule API key from environment |
| `download_8k_filings.py` | Download 8-K filings using datamule |
| `download_10k_filings.py` | Download 10-K filings using datamule |
| `parse_8k_disclosures.py` | Extract and parse Item 1.05 from 8-K filings |
| `parse_10k_disclosures.py` | Extract and parse Items 106 & 407(j) from 10-K filings |
| `generate_statistics.py` | Generate dataset statistics and summary reports |
| `generate_daily_summary.py` | Create daily ingestion summary for GitHub issues |
| `backfill_historical.py` | Backfill historical data for specified date ranges |
| `validate_dataset.py` | Validate markdown files and frontmatter |
| `check_duplicates.py` | Check for duplicate filings |
| `generate_validation_report.py` | Generate validation reports for PRs |

## How to Navigate the Dataset

The generated dataset consists of individual Markdown files, organized logically by filing type, year, and quarter. Each Markdown file represents a specific cybersecurity disclosure and includes YAML frontmatter for easy integration with static site generators like Hugo or Jekyll.

### Directory Structure

```
sec-edgar-cybersecurity/
├── .github/
│   ├── workflows/
│   │   ├── daily-ingestion.yml           # Daily automated ingestion
│   │   ├── backfill.yml                  # Historical data backfill
│   │   └── data-validation.yml           # Data quality validation
│   ├── scripts/
│   │   ├── configure_datamule.py
│   │   ├── download_8k_filings.py
│   │   ├── download_10k_filings.py
│   │   ├── parse_8k_disclosures.py
│   │   ├── parse_10k_disclosures.py
│   │   ├── generate_statistics.py
│   │   ├── generate_daily_summary.py
│   │   ├── backfill_historical.py
│   │   ├── validate_dataset.py
│   │   ├── check_duplicates.py
│   │   ├── generate_validation_report.py
│   |   └── requirements.txt              # Python dependencies
│   └── outputs/                          # Temporary workflow outputs (gitignored)
├── data/
│   ├── 8K/
│   │   ├── <YEAR>/
│   │   │   ├── <QUARTER>/
│   │   │   │   └── <CIK>_<DATE>_8K.md
│   │   │   └── ...
│   │   └── ...
│   └── 10K/
│       ├── <YEAR>/
│       │   ├── <QUARTER>/
│       │   │   └── <CIK>_<DATE>_10K.md
│       │   └── ...
│       └── ...
├── stats/
│   ├── summary.json                      # Machine-readable statistics
│   └── README.md                         # Human-readable statistics report
└── README.md                             # This file
```

### Markdown File Structure

#### 8-K Filing Example
Each 8-K Markdown file has the following structure:

```yaml
---
ticker: MSFT
company_name: Microsoft Corporation
cik: 789019
filing_date: 2024-03-15
filing_type: 8-K
item: 1.05
accession_number: 0001234567-24-000123
source_link: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=789019&type=8-K&dateb=&owner=exclude&count=100
---

## Item 1.05. Material Cybersecurity Incidents

[Parsed Markdown content of the Item 1.05 disclosure]
```

#### 10-K Filing Example
Each 10-K Markdown file has the following structure:

```yaml
---
ticker: AAPL
company_name: Apple Inc.
cik: 320193
filing_date: 2024-10-31
fiscal_year_end: 2024-09-30
filing_type: 10-K
items:
  - 106
  - 407j
accession_number: 0001234567-24-000456
source_link: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=320193&type=10-K&dateb=&owner=exclude&count=100
---

## Item 106. Cybersecurity Risk Management, Strategy, and Governance

[Parsed Markdown content of the Item 106 disclosure]

## Item 407(j). Board Oversight of Cybersecurity Risk

[Parsed Markdown content of the Item 407(j) disclosure]
```

### YAML Frontmatter Fields

| Field | Description | Example |
|-------|-------------|---------|
| `ticker` | Company stock ticker symbol | `MSFT` |
| `company_name` | Full company name | `Microsoft Corporation` |
| `cik` | SEC Central Index Key | `789019` |
| `filing_date` | Date the filing was submitted | `2024-03-15` |
| `filing_type` | Type of SEC filing | `8-K` or `10-K` |
| `item` | Specific item number (8-K only) | `1.05` |
| `items` | List of item numbers (10-K only) | `[106, 407j]` |
| `fiscal_year_end` | Fiscal year end date (10-K only) | `2024-09-30` |
| `accession_number` | SEC accession number | `0001234567-24-000123` |
| `source_link` | Link to SEC EDGAR filing | Full URL |

## Manual Usage

### Trigger Daily Ingestion Manually

1. Go to the **Actions** tab in your GitHub repository
2. Select **"Daily SEC Cybersecurity Data Ingestion"**
3. Click **"Run workflow"**
4. (Optional) Specify custom date range and filing types
5. Click **"Run workflow"**

### Run Historical Backfill

1. Go to the **Actions** tab in your GitHub repository
2. Select **"Backfill Historical Data"**
3. Click **"Run workflow"**
4. Enter parameters:
   - **Start year**: e.g., `2023`
   - **End year**: e.g., `2024`
   - **Filing type**: `8-K`, `10-K`, or `both`
   - **Use datamule provider**: Check for faster downloads (requires valid API key)
5. Click **"Run workflow"**

⚠️ **Note**: Historical backfills can take several hours depending on the date range. Using the datamule provider significantly speeds up downloads but incurs costs ($1 per 100,000 downloads).

## Statistics and Reporting

The pipeline automatically generates statistics about the dataset:

- **`stats/summary.json`**: Machine-readable JSON with detailed statistics
- **`stats/README.md`**: Human-readable summary including:
  - Total filings by type
  - Unique companies and tickers
  - Filings by year and quarter
  - Top companies by filing count
  - Item-specific breakdowns (for 10-K filings)

Statistics are updated automatically after each ingestion run.

## Data Quality

### Validation
All data goes through automated validation:
- YAML frontmatter structure verification
- Required field presence checks
- Duplicate detection
- Filing type consistency checks

### Rate Limiting
- **Without datamule API key**: 7 requests/second (SEC rate limit)
- **With datamule API key**: No rate limits, significantly faster downloads

## Cost Considerations

### Free Tier (No API Key)
- Uses SEC EDGAR direct API
- Rate limited to 7 requests/second
- Suitable for daily incremental updates
- **Cost**: Free

### Datamule Provider (Requires API Key)
- Uses datamule's cloud archive
- No rate limits
- Recommended for large historical backfills
- **Cost**: $1 per 100,000 downloads
- Example: Backfilling all 2023-2024 8-K and 10-K filings might cost $5-10

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all validation checks pass
5. Submit a pull request

## Troubleshooting

### Workflow Failures

**Issue**: Downloads fail with rate limit errors  
**Solution**: Either reduce frequency or add `DATAMULE_API_KEY` secret

**Issue**: Parser finds no disclosures  
**Solution**: SEC filings may use different formatting; update regex patterns in parser scripts

**Issue**: Out of memory errors during large backfills  
**Solution**: Break backfill into smaller date ranges

### Local Development

To test scripts locally:

```bash
# Set environment variable
export DATAMULE_API_KEY="your-key-here"

# Run individual scripts
python .github/scripts/download_8k_filings.py --start-date 2024-01-01 --end-date 2024-01-31
python .github/scripts/parse_8k_disclosures.py
python .github/scripts/generate_statistics.py --filing-type 8K
```

## License

This project is open source. The data is sourced from public SEC EDGAR filings and is in the public domain.

## Acknowledgments

- **datamule** by [John Friedman](https://datamule.xyz/about) for providing excellent SEC filing access tools
- **SEC EDGAR** for maintaining public access to corporate filings
- The open-source community for the various Python libraries used in this project

## Contact

For questions, issues, or suggestions, please open a GitHub issue or contact the repository maintainer.

---

**Last Updated**: January 2026  
**Pipeline Status**: [![Daily Ingestion](../../actions/workflows/daily-ingestion.yml/badge.svg)](../../actions/workflows/daily-ingestion.yml)