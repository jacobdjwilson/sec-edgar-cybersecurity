# SEC EDGAR Cybersecurity Disclosure Tracker

This repository contains a serverless, automated data pipeline that continuously monitors, downloads, and parses SEC filings to generate a clean, open-source dataset of corporate cybersecurity disclosures.

The system is built to specifically track and extract information related to the SEC's 2023 cybersecurity rules, making critical disclosure data accessible for researchers, investors, and security professionals.

## Project Mission

The goal of this project is to provide a continuously updated, open-source dataset of corporate cybersecurity disclosures. By leveraging GitHub Actions for automation and the `datamule` and `markitdown` Python packages for data processing, we aim to create a reliable and transparent resource for monitoring corporate cyber readiness and incident reporting.

## SEC Rules Tracked

This dataset specifically targets disclosures filed under the following items as mandated by the SEC's 2023 cybersecurity rules:

| Filing | Item      | Description                          |
|--------|-----------|--------------------------------------|
| **8-K**  | Item 1.05 | Material Cybersecurity Incidents     |
| **10-K** | Item 106  | Risk Management & Strategy         |
| **10-K** | Item 407j | Governance (Board Oversight)         |

## How It Works

A GitHub Actions workflow runs daily to perform the following steps:

1.  **Fetch Filings:** Queries the SEC EDGAR database via the `datamule` package for all 8-K and 10-K filings from the previous 24 hours.
2.  **Filter & Process:** The pipeline intelligently filters the filings:
    *   An **8-K** is processed only if it explicitly contains **Item 1.05**.
    *   A **10-K** is processed only if it contains the new cybersecurity **Item 106** or **Item 407j** sections.
3.  **Parse & Convert:** For relevant filings, the specific cybersecurity disclosure sections are extracted and converted from their raw HTML/text format into clean Markdown using the `markitdown` package.
4.  **Generate Dataset:** Each processed disclosure is saved as a separate Markdown file in the `content/filings` directory, organized by year and quarter.
5.  **Commit & Update:** The newly generated files are automatically committed back to this repository, ensuring the dataset is always up-to-date.

## Navigating the Dataset

The cybersecurity disclosures are stored as individual Markdown files in the `content/filings/` directory. The structure is as follows:

```
content/
└── filings/
    └── YYYY/
        └── Q#/
            └── {CIK}_{FilingType}_{Date}.md
```

Each file contains YAML frontmatter with essential metadata for easy analysis:

```yaml
---
Ticker: "AAPL"
CIK: "320193"
Date: "2025-10-28"
Filing Type: "10-K"
Source Link: "https://www.sec.gov/Archives/edgar/data/..."
---

... Markdown content of the disclosure ...
```
