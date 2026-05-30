# expense-categorizer

> **Raw bank transactions → categorized, normalized, enriched.** Detects recurring payments, subscriptions, anomalies. Exports clean CSV or JSON. Works on any bank's transaction export.

[![PyPI](https://img.shields.io/pypi/v/expense-categorizer?style=flat)](https://pypi.org/project/expense-categorizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install expense-categorizer
python -m expense_categorizer transactions.csv
python -m expense_categorizer transactions.csv --csv categorized.csv
```

## What it does

- Normalizes merchant names: `AMZN*1A2B3C AMZN.COM` → `Amazon`
- Categorizes into 20 categories: groceries, dining, transport, subscriptions...
- Detects recurring payments and subscription names
- Flags anomalies: duplicate charges, unusually large amounts
- Builds category breakdown with totals and counts
- Detects all active subscriptions with monthly cost

## License
MIT © [Alper Nabil Gabra Zakher](https://github.com/AlperNab)
