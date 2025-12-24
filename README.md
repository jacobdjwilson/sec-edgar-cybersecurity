# SEC EDGAR Cybersecurity Tracker

![Daily SEC Watchdog](https://github.com/jacobdjwilson/sec-edgar-cybersecurity/workflows/Daily%20SEC%20Watchdog/badge.svg)

## 🎯 Mission

An open-source, automated tracking system for SEC cybersecurity disclosures mandated by the SEC's 2023 cybersecurity rules. This repository serves as a serverless, flat-file database that monitors and parses:

- **Material Cybersecurity Incidents** (8-K Item 1.05)
- **Cybersecurity Risk Management** (10-K Item 1C/Item 106)
- **Cybersecurity Governance** (10-K Item 407(j))

## 📋 Background

In July 2023, the SEC adopted new rules requiring public companies to:

1. **Disclose material cybersecurity incidents** within 4 business days via 8-K filings (Item 1.05)
2. **Describe cybersecurity risk management processes** in annual 10-K filings (Item 1C)
3. **Disclose board oversight of cybersecurity risks** in annual reports (Item 407(j))

This repository automatically fetches, parses, and organizes these disclosures into clean, searchable Markdown files.

## 🗂️ Repository Structure

```
sec-edgar-cybersecurity/
├── data/
│   ├── 2024/
│   │   ├── Q1/
│   │   ├── Q2/
│   │   ├── Q3/
│   │   └── Q4/
│   └── 2025/
│       └── Q1/
├── .github/
│   ├── scripts/
│   │   └── ingest_sec.py
│   └── workflows/
│       └── daily-sec-watchdog.yml
├── requirements.txt
└── README.md
```

## 🔍 Navigation Guide

### Finding Recent Incidents

1. Navigate to `data/YYYY/QX/` where YYYY is the year and QX is the quarter
2. Look for files matching `*_8-K_*.md` - these contain incident disclosures
3. Files are named: `{TICKER}_{FILING_TYPE}_{DATE}.md`

**Example:** `data/2024/Q4/UNH_8-K_2024-02-22.md`

### Finding Risk Management Programs

1. Navigate to the same quarterly folders
2. Look for files matching `*_10-K_*.md`
3. These contain annual cybersecurity program descriptions

## 🚀 How It Works

### Automated Daily Ingestion

Every day at **6:00 AM ET** (11:00 UTC), a GitHub Action:

1. Checks for new 8-K and 10-K filings from all public companies
2. Filters for cybersecurity-relevant content:
   - 8-K filings containing "Item 1.05"
   - 10-K filings containing "Item 1C" or cybersecurity-related sections
3. Extracts relevant HTML sections using BeautifulSoup
4. Converts to clean Markdown using Microsoft's `markitdown`
5. Adds structured YAML frontmatter with metadata
6. Commits new files to the repository

### File Format

Each disclosure file contains:

```yaml
---
ticker: "TICKER"
filing_type: "8-K"
filing_date: "YYYY-MM-DD"
item_type: "1.05"
sec_link: "https://www.sec.gov/..."
---
```

Followed by the parsed Markdown content and a company information table.

## 🛠️ Technology Stack

- **Data Fetching:** `datamule` - SEC EDGAR API wrapper
- **HTML Parsing:** `BeautifulSoup4` - Extract relevant sections
- **Markdown Conversion:** `markitdown` (Microsoft) - Clean HTML-to-Markdown
- **Automation:** GitHub Actions - Serverless daily execution
- **Storage:** Git-based flat-file database

## 📊 Data Coverage

- **Start Date:** January 2024 (when SEC rules took effect)
- **Update Frequency:** Daily at 6:00 AM ET
- **Companies Tracked:** All SEC-registered public companies
- **Filing Types:** 8-K (Item 1.05), 10-K (Item 1C, Item 407j)

## 🤝 Contributing

### Adding Companies to Watch

While the system automatically monitors all public companies, you can prioritize specific tickers by:

1. Creating a pull request
2. Adding discussion in Issues about specific sectors or companies

### Manual Trigger

You can manually trigger the ingestion workflow:

1. Go to the "Actions" tab
2. Select "Daily SEC Watchdog"
3. Click "Run workflow"

## 📖 Use Cases

- **Security Researchers:** Track incident patterns and disclosure timelines
- **Investors:** Monitor cybersecurity risks in portfolio companies
- **Compliance Teams:** Benchmark disclosure practices
- **Journalists:** Investigate cybersecurity trends
- **Academics:** Research corporate cyber incident response

## ⚖️ Legal

All data is sourced from public SEC EDGAR filings. This repository does not provide legal, financial, or investment advice. Always verify information with original SEC filings.

## 🔗 Resources

- [SEC Cybersecurity Rules (2023)](https://www.sec.gov/news/press-release/2023-139)
- [SEC EDGAR Database](https://www.sec.gov/edgar)
- [Form 8-K Instructions](https://www.sec.gov/files/form8-k.pdf)
- [Form 10-K Instructions](https://www.sec.gov/files/form10-k.pdf)

## 📜 License

MIT License - Free to use, modify, and distribute.

---

**Last Updated:** Auto-generated daily by GitHub Actions