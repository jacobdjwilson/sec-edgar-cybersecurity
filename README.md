# SEC EDGAR Cybersecurity Disclosures

## Project Mission

This project aims to build a serverless, automated data pipeline that continuously monitors, downloads, and parses SEC filings to generate a clean, open-source dataset of corporate cybersecurity disclosures. The entire system operates within the GitHub ecosystem.

## SEC Cybersecurity Rules Tracked

This system specifically targets the SEC's 2023 cybersecurity rules, focusing on the following key areas:

*   **Material Cybersecurity Incidents (8-K filings, specifically Item 1.05):** Companies are required to disclose material cybersecurity incidents within four business days of determining materiality.
*   **Risk Management & Strategy (10-K filings, specifically Item 106):** Companies must describe their processes for assessing, identifying, and managing material risks from cybersecurity threats, and the role of the board of directors in overseeing these risks.
*   **Governance (10-K filings, specifically Item 407j):** Companies must describe the board's oversight of cybersecurity risks and management's role and expertise in assessing and managing those risks.

## How to Navigate the Dataset

The generated dataset consists of individual Markdown files, organized logically by filing type, year, and quarter. Each Markdown file represents a specific cybersecurity disclosure and includes YAML Frontmatter for easy integration with static site generators like Hugo.

### Directory Structure

```
data/
├── 8K/
│   ├── <YEAR>/
│   │   ├── <QUARTER>/
│   │   │   └── <CIK>_<DATE>_8K.md
│   │   └── ...
├── 10K/
│   ├── <YEAR>/
│   │   ├── <QUARTER>/
│   │   │   └── <CIK>_<DATE>_10K.md
│   │   └── ...
```

### Markdown File Structure

Each Markdown file will have the following structure:

```yaml
---
name: [Company Name]
ticker: [Company Ticker]
website: [Company Website]
category: [Category of Disclosure]
CIK: [Central Index Key]
SIC: [SIC Description]
filing_number: [Filing Number]
date: [Filing Date YYYY-MM-DD]
filing_type: [Filing Type, e.g., 8-K, 10-K]
filling_quarter: [Filing Quarter]
filling_year: [Filing Year]
source_link: [Link to SEC Filing]
---

## [Section Title (e.g., Item 1.05. Material Cybersecurity Incidents)]

[Parsed Markdown content of the relevant section]
```

## Automation

This project runs inside GitHub and is driven by GitHub Actions. A scheduled workflow executes daily at 6:00 AM ET, automatically monitoring for new cybersecurity disclosures and ingesting them as they appear. The pipeline is built on [datamule](https://github.com/john-friedman/datamule-python), a Python package created by [John Friedman](https://datamule.xyz/about) for working with SEC filings at scale.
