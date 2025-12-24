# SEC EDGAR Cybersecurity

[![Daily SEC Watchdog](https://github.com/sec-edgar-cybersecurity/sec-edgar-cybersecurity/actions/workflows/daily-sec-watchdog.yml/badge.svg)](https://github.com/sec-edgar-cybersecurity/sec-edgar-cybersecurity/actions/workflows/daily-sec-watchdog.yml)

An open-source project dedicated to tracking material cybersecurity incidents and risk governance disclosures from public companies, as reported to the U.S. Securities and Exchange Commission (SEC).

## Mission

In 2023, the SEC adopted new rules to enhance and standardize disclosures regarding cybersecurity risk management, strategy, governance, and incidents. This repository provides a clean, parsed, and trackable dataset based on these rules, focusing on:

- **Item 1.05 (8-K): Material Cybersecurity Incidents:** Companies must now disclose any cybersecurity incident they determine to be material within four business days.
- **Item 106 (10-K): Risk Management and Strategy:** Companies must describe their processes for assessing, identifying, and managing material risks from cybersecurity threats.
- **Item 407(j) (10-K): Governance:** Companies need to describe the board of directors' oversight of risks from cybersecurity threats and management’s role in assessing and managing material risks.

Our philosophy is **"Compliance is not Intelligence."** By converting these required legal disclosures from raw HTML into structured Markdown with YAML frontmatter, we aim to build a valuable dataset for researchers, investors, and security professionals.

## Triage Guide: How to Find Data

All processed filings are stored in the `data/` directory. The structure is designed for easy navigation:

```
data/
└── {YEAR}/
    └── {QUARTER}/
        ├── {TICKER}_{FILING-TYPE}_{DATE}.md
        └── ...
```

- **YEAR:** The year the filing was made (e.g., `2024`).
- **QUARTER:** The calendar quarter of the filing date (e.g., `Q1`, `Q2`).
- **FILENAME:** A unique identifier for each filing, containing the stock ticker, form type (8-K or 10-K), and filing date.

**Example:** To find a material breach reported by UnitedHealth Group in early 2024, you would navigate to `data/2024/Q1/UNH_8-K_2024-02-22.md`.

## Usage

This repository runs automatically every day at 6:00 AM ET to pull in new filings.

### Adding a Company to the Watchlist

You can track additional companies by adding their stock tickers to the watchlist.

1.  Navigate to the `.github/scripts/watchlist.txt` file.
2.  Click the "Edit" (pencil) icon.
3.  Add one or more new tickers, each on a new line.
4.  Commit the changes.

The daily workflow will automatically pick up the new tickers and begin pulling their relevant cybersecurity filings.