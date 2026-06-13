# Vikram Misra — Portfolio Analytics · Verified 3-Broker Track Record

A static, recruiter-facing analytics dashboard built from raw brokerage data across three Indian brokers (Zerodha, AngelOne, Groww), **Sep 2023 – Jun 2026**. Every figure on the page is reconciled to broker statements; methodology, definitions and open items are disclosed on the dashboard itself. The build **fails** if headline figures stop tying to the published datasets.

**Live:** https://vikrammisra2011.github.io/portfolio-analytics/

## What the dashboard shows

| Section | Content |
|---|---|
| Overview | Net realized ₹3,09,083 (incl. dividends, net of all charges) · ₹2.76 Cr turnover · 399 orders · 77.8% lot win rate · profit factor 1.94 (3.20 ex corp-action pair) |
| Realized record | Monthly cadence by broker, cumulative curve, P&L calendar heatmap, hit-rate stats (22 of 24 active months positive) |
| Risk & drawdown | Max drawdown on the cumulative realized curve (−₹5,903, recovered in 1 month), underwater chart, longest losing streak, and an explicit *deliberately withheld* panel (Sharpe/Sortino/beta await a unified capital base) |
| Attribution | Instrument-level P&L (84 of 107 instruments profitable), concentration Pareto (winners built ₹3.85L gross; losers gave back 16%), P&L by holding period (the edge lives ≤30 days) |
| Trade analytics | 270 FIFO-matched lots: expectancy +₹603/lot, payoff ratio 0.54, per-broker lot stats, distribution views |
| Broker comparison | Window, net, turnover, orders, win rate, reconciliation note per broker |
| Signature exhibits | Election-week deployment (+₹81,015) · OLA IPO flip recovered from ledger forensics (+₹59,234) · Triveni Turbine thesis hold |
| Open book | Current positions at honest marks, separated from the realized record — including the losers |
| Benchmark context | NIFTY 50 TRI (via AMFI-published index-fund NAV, fully cited), rebased, with event markers — regime context, not an alpha claim |
| Methodology | Ingestion → reconciliation → corporate actions → charges bridge → metric definitions → pending items |

## Data lineage

```
raw broker exports (NOT in repo — contain PAN/client codes)     derived, published
─ Zerodha tradebook / P&L / fund ledger              ──►  data/monthly_realized.csv
─ AngelOne trades history / P&L statement            ──►  data/trade_lots.csv
─ Groww orders / 2× P&L / balance stmt / dividends   ──►  data/instrument_pnl.csv
                                                     ──►  data/open_book.csv
                                                     ──►  data/summary_metrics.json
AMFI NAV feed (api.mfapi.in, scheme 120716)          ──►  data/benchmark.csv (+ benchmark_source.json)
```

Reconciliation checks encoded in the pipeline:

- Independent FIFO engine reproduces Zerodha's stated realized P&L to ₹0.00
- Groww fund ledger ↔ order history closes within ₹40 after corporate-action adjustment
- +₹59,234 OLA IPO gain recovered from a ₹1.85L settlement-ledger gap (absent from broker P&L)
- Charges bridge: gross cadence ₹3,23,945 − Zerodha ₹6,305 − Groww ₹20,855 = ₹2,96,785 net ex-div (+₹12,298 dividends = headline)

## Build & validate

```bash
pip install -r requirements.txt
python scripts/build_dashboard.py     # data/ -> docs/index.html
```

The build runs a 15-check validation block (KPI tie-outs, internal consistency, benchmark integrity) and refuses to write the page on any failure — so the published dashboard can never drift from the data layer.

## Repo structure

```
├── README.md
├── requirements.txt
├── .gitignore
├── data/                  # derived, published datasets (no identifiers)
│   ├── monthly_realized.csv   # monthly realized P&L by broker + cumulative
│   ├── trade_lots.csv         # 270 FIFO-matched lots (pnl, hold, broker, symbol)
│   ├── instrument_pnl.csv     # realized P&L by instrument (107 instruments)
│   ├── open_book.csv          # current positions at statement marks
│   ├── summary_metrics.json   # statement-tied headline figures + exhibits
│   ├── benchmark.csv          # NIFTY 50 TRI proxy series (month, date, value)
│   └── benchmark_source.json  # exact benchmark citation + flags
├── scripts/
│   ├── prep_data.py           # documents how data/ was derived from private working sets
│   └── build_dashboard.py     # metrics + charts + page + validation (single entry point)
└── docs/
    └── index.html             # the dashboard (GitHub Pages serves this folder)
```

## Metric definitions (as printed on the page)

Win rate — share of FIFO lots with P&L > 0 · Expectancy — mean P&L per lot · Payoff ratio — avg win ÷ |avg loss| · Profit factor — Σ wins ÷ |Σ losses| (shown with and without the offsetting Reliance bonus legs) · Hit rate (monthly) — share of active months with positive realized P&L · Max drawdown (realized curve) — deepest fall of cumulative realized P&L below its prior peak · Turnover — buy + sell value.

## Benchmark sourcing

NIFTY 50 TRI is tracked via the UTI Nifty 50 Index Fund (Direct, Growth; AMFI scheme 120716) month-end NAV from api.mfapi.in — public-record AMFI data, tracking difference ≈ 0.1–0.2%/yr vs the TRI. Full citation ships with the data (`data/benchmark_source.json`) and on the page. Used for regime context only; no relative-return claim is made without a unified capital base.

## Deploy on GitHub Pages

1. Push to `main` of the `portfolio-analytics` repo.
2. Settings → Pages → Deploy from branch → `main` / `/docs`.
3. Live at `https://<username>.github.io/portfolio-analytics/` within ~a minute.

## Disclosed pending items

- Combined money-weighted return (XIRR): cash-flow set assembled from all three broker ledgers (118 flows; ledgers conserve to the paisa); withheld pending a CDSL/demat transfer statement to resolve inter-account in-kind movements before a single capital base can be struck.

## Resolved (this revision)

Two items previously shown as open/pending were cleared against newly-provided broker P&L (transcribed, identifier-free evidence ships in the dashboard's Verification & methodology section):

- **OLA Electric (Groww)** — the 2,441-sh "pledged" line was an intraday round-trip (buy ₹100.25 → sell ₹100.26, 01-Oct-2024), not an open hold; the broker's stock P&L shows buy value ₹12,48,013.03 = sell value ₹12,51,522.32 (every share round-tripped). Closed, +₹3,509.29 — already in the record. No pledged holding exists; its mark is no longer pending.
- **LODHA (Zerodha)** — the 26-sh exit, previously outside the provided statements, is now covered by the full-period Zerodha Console P&L: fully closed, 52 sh, realised +₹4,888.50 (+6.57%), unrealised ₹0. ₹3,993.50 sits in the dated cadence; the +₹895.00 tail is statement-confirmed but undated, so it is disclosed rather than netted into a cadence month (headline stays conservative).

## Disclaimer

Personal investment record presented as analytical proof-of-work. Not investment advice. All figures derived from broker statements; marks as of the dates shown per row. No account identifiers, client codes, or personal data are published.
