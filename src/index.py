#!/usr/bin/env python3
"""
expense-categorizer — raw bank transactions → categorized, normalized, enriched
Detects: merchant name, category, recurring payments, anomalies, subscriptions
Exports: clean CSV, JSON, or summary report
"""
import anthropic, csv, io, json, re, sys
from datetime import datetime
from pathlib import Path

SYSTEM = """You are a financial data analyst specializing in transaction categorization.

Process each transaction and return enriched, categorized data.

Categories (use exactly these):
groceries, dining, transport, fuel, utilities, rent_mortgage, salary_income,
transfer, shopping_retail, entertainment, healthcare, education, insurance,
investment_savings, atm_withdrawal, bank_fee, refund, subscription_saas,
travel, home_garden, personal_care, charity, government_tax, other

Rules:
- Normalize merchant names: "AMZN*1A2B3C" → "Amazon", "MCDONALDs #1234" → "McDonald's"
- Detect recurring: same merchant within 28-35 days = recurring
- Flag anomalies: unusually large amounts, duplicate charges, odd hours
- Infer subscription names from billing descriptors when possible

Return ONLY valid JSON:
{
  "transactions": [
    {
      "original_description": "raw text",
      "merchant": "normalized merchant name",
      "category": "from list above",
      "subcategory": "more specific e.g. 'streaming' under subscription_saas",
      "amount": number,
      "date": "YYYY-MM-DD",
      "is_recurring": true,
      "recurring_frequency": "monthly|weekly|annual|null",
      "is_anomaly": false,
      "anomaly_reason": "string or null",
      "is_subscription": false,
      "subscription_name": "Netflix|Spotify|null",
      "confidence": 0.0
    }
  ],
  "summary": {
    "total_transactions": number,
    "total_spent": number,
    "total_income": number,
    "date_range": {"from":"YYYY-MM-DD","to":"YYYY-MM-DD"},
    "top_categories": [{"category":"string","total":number,"count":number}],
    "subscriptions_detected": [{"name":"string","amount":number,"frequency":"string"}],
    "anomalies": [{"date":"string","merchant":"string","amount":number,"reason":"string"}],
    "recurring_payments": number,
    "largest_expense": {"merchant":"string","amount":number,"date":"string"}
  }
}"""

def categorize(transactions_text: str) -> dict:
    """Categorize a block of transaction text (CSV, tab-separated, or natural text)."""
    client = anthropic.Anthropic()
    if len(transactions_text) > 40000:
        transactions_text = transactions_text[:40000] + "\n[truncated]"
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4096, system=SYSTEM,
        messages=[{"role":"user","content":f"Categorize these transactions:\n\n{transactions_text}"}]
    )
    raw = re.sub(r'^```(?:json)?\s*','',resp.content[0].text.strip(),flags=re.MULTILINE)
    raw = re.sub(r'\s*```$','',raw,flags=re.MULTILINE)
    return json.loads(raw)

def categorize_file(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists(): raise FileNotFoundError(f"Not found: {file_path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return categorize(text)

def to_csv_string(result: dict) -> str:
    output = io.StringIO()
    fieldnames = ["date","merchant","original_description","amount","category",
                  "subcategory","is_recurring","is_subscription","subscription_name",
                  "is_anomaly","anomaly_reason","confidence"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for txn in result.get("transactions", []):
        writer.writerow(txn)
    return output.getvalue()

def print_report(result: dict):
    s = result.get("summary", {})
    txns = result.get("transactions", [])
    print(f"\n{'═'*60}")
    print(f"  EXPENSE REPORT — {len(txns)} transactions")
    dr = s.get("date_range", {})
    if dr: print(f"  {dr.get('from','?')} → {dr.get('to','?')}")
    print(f"{'═'*60}")
    print(f"  Total spent:  ${abs(s.get('total_spent',0)):,.2f}")
    print(f"  Total income: ${s.get('total_income',0):,.2f}")
    print(f"  Recurring:    {s.get('recurring_payments',0)} payments")

    cats = s.get("top_categories", [])
    if cats:
        print(f"\n  Top categories:")
        for c in cats[:8]:
            bar_len = int(c.get("total",0) / max(cats[0].get("total",1), 1) * 20)
            bar = "█" * bar_len
            print(f"  {c.get('category','?'):<22} {bar:<20} ${c.get('total',0):>8,.2f} ({c.get('count',0)})")

    subs = s.get("subscriptions_detected", [])
    if subs:
        total_subs = sum(sub.get("amount",0) for sub in subs)
        print(f"\n  Subscriptions (${total_subs:.2f}/mo total):")
        for sub in subs:
            print(f"    • {sub.get('name','?'):<25} ${sub.get('amount',0):.2f}/{sub.get('frequency','mo')}")

    anomalies = s.get("anomalies", [])
    if anomalies:
        print(f"\n  ⚠ Anomalies ({len(anomalies)}):")
        for a in anomalies:
            print(f"    {a.get('date','?')} {a.get('merchant','?'):<25} ${a.get('amount',0):.2f}")
            print(f"    → {a.get('reason','?')}")

    largest = s.get("largest_expense", {})
    if largest:
        print(f"\n  Largest: {largest.get('merchant','?')} — ${largest.get('amount',0):.2f} on {largest.get('date','?')}")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: print("Usage: python -m expense_categorizer <transactions.csv|.txt> [--json] [--csv output.csv]"); sys.exit(0)
    result = categorize_file(args[0]) if args[0] != "-" else categorize(sys.stdin.read())
    csv_idx = args.index("--csv") if "--csv" in args else -1
    if csv_idx >= 0 and len(args) > csv_idx+1:
        Path(args[csv_idx+1]).write_text(to_csv_string(result), encoding="utf-8")
        print(f"Exported to {args[csv_idx+1]}")
    elif "--json" in args: print(json.dumps(result, indent=2, ensure_ascii=False))
    else: print_report(result)
