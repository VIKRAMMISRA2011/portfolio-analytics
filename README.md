# Independent Portfolio — Verified Track Record

A static, recruiter-facing analytics dashboard built from raw brokerage data across three Indian brokers (Zerodha, AngelOne, Groww), Sep 2023 – Jun 2026. Every figure on the page is reconciled to broker statements; methodology and open items are disclosed on the dashboard itself.

**Live page:** `docs/index.html` (deployable on GitHub Pages — steps below)

## What it shows
- Net realized P&L (₹3,09,083 incl. dividends, net of all charges), ₹2.76 Cr turnover, 399 orders
- Monthly realized cadence by broker with cumulative curve
- Broker-level comparison with reconciliation notes
- Trade analytics over 270 FIFO-matched lots (win rate 77.8%, profit factor 1.94, holding-period profile)
- Open book at honest marks, separated from the realized record, including pending/disclosure rows
- A methodology panel describing ingestion, reconciliation, corporate-action handling, and what remains pending

## Data lineage
```
raw broker exports (NOT in repo)            derived, published
─ Zerodha tradebook / P&L / ledger   ──►   data/monthly_realized.csv
─ AngelOne trades / P&L statement    ──►   data/trade_lots.csv
─ Groww orders / 2× P&L / balance    ──►   data/instrument_pnl.csv
  statement / dividend report        ──►   data/open_book.csv
                                     ──►   data/summary_metrics.json
```
Raw exports are excluded (`.gitignore`) because they contain client codes, PAN and bank references. The derived files are identifier-free.

Reconciliation checks encoded in the pipeline:
- Independent FIFO engine reproduces Zerodha's stated realized P&L to ₹0.00
- Groww fund ledger ↔ order history closes within ₹40 after corporate-action adjustment
- +₹59,234 OLA IPO gain recovered from a ₹1.85L settlement-ledger gap (absent from broker P&L)

## Repo structure
```
├── README.md
├── requirements.txt
├── .gitignore
├── data/                  # derived, published datasets (no identifiers)
├── scripts/
│   ├── prep_data.py       # rebuilds data/ from cleaned working sets
│   └── build_dashboard.py # renders docs/index.html from data/
└── docs/
    └── index.html         # the dashboard (GitHub Pages serves this folder)
```

## Regenerate locally
```bash
pip install -r requirements.txt
python scripts/build_dashboard.py     # data/ -> docs/index.html
```
(`scripts/prep_data.py` documents how data/ was derived; it requires the private working sets and is kept for transparency/reproducibility.)

## Deploy on GitHub Pages
1. Create a new public repo (e.g. `portfolio-analytics`), push these files to `main`.
2. Repo **Settings → Pages → Build and deployment**: Source = *Deploy from a branch*, Branch = `main`, Folder = `/docs`. Save.
3. The dashboard goes live at `https://<username>.github.io/portfolio-analytics/` within ~a minute.
4. Resume line: `Built and published a reconciled 3-broker portfolio analytics dashboard (Python, pandas, Plotly) — <link>`

## Updating with new data
1. Replace/extend the derived files in `data/` (or re-run `prep_data.py` against updated working sets).
2. `python scripts/build_dashboard.py`
3. Commit and push — Pages redeploys automatically.

## Disclosed pending items
- Combined money-weighted return (XIRR): requires the AngelOne fund ledger and a current mark on one pledged holding; withheld until computable across all accounts rather than shown partially.
- NIFTY 50 TRI benchmark overlay: to be added with a market-data feed.
- One Zerodha exit (LODHA, 26 sh) falls in a period not covered by provided statements; excluded from all totals and disclosed on the dashboard.

## Disclaimer
Personal investment record presented as analytical proof-of-work. Not investment advice. All figures derived from broker statements; marks as of the dates shown per row.
