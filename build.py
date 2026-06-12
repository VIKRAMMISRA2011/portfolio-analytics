#!/usr/bin/env python3
"""
build.py — regenerates docs/index.html from data/.
Every figure on the page is read from data/ or computed here, transparently.
Usage: python build.py
"""
import json, datetime as dt
from pathlib import Path
from string import Template
import pandas as pd

ROOT = Path(__file__).parent
D = ROOT / "data"
OUT = ROOT / "docs" / "index.html"

# ---------- load ----------
S = json.load(open(D / "summary.json"))
monthly = pd.read_csv(D / "monthly_pnl.csv")
holds = pd.read_csv(D / "holding_periods.csv")["days"].dropna()
losses = pd.read_csv(D / "realized_losses.csv")["loss"].dropna()
contrib = pd.read_csv(D / "top_contributors.csv")
openpos = json.load(open(D / "open_positions.json"))
gcf = pd.read_csv(D / "cashflows_groww.csv", parse_dates=["date"])

# ---------- Groww XIRR from cash flows (regenerated each build) ----------
def xirr(flows):  # flows: list[(date, amount)]
    d0 = min(d for d, _ in flows)
    def npv(r):
        return sum(a / (1 + r) ** ((d - d0).days / 365.25) for d, a in flows)
    lo, hi = -0.95, 5.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0: return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2

HELD_EX_OLA = 30880.0          # Groww non-OLA holdings, Jun-1-26 broker marks
OLA_QTY = 2441
AS_OF = dt.date(2026, 6, 10)
flows_base = list(zip(gcf["date"].dt.date, gcf["amount"]))
xirr_lo = xirr(flows_base + [(AS_OF, HELD_EX_OLA + OLA_QTY * 35)])
xirr_hi = xirr(flows_base + [(AS_OF, HELD_EX_OLA + OLA_QTY * 65)])

# ---------- chart payloads ----------
months = monthly["month"].tolist()
series = {b: monthly[b].tolist() for b in ["Zerodha", "AngelOne", "Groww", "Dividends"]}
cum = monthly[["Zerodha", "AngelOne", "Groww", "Dividends"]].sum(axis=1).cumsum().round(0).tolist()
hold_vals = holds.clip(upper=120).tolist()
loss_vals = losses.tolist()
contrib_sorted = contrib.sort_values("pnl")
payload = dict(
    months=months, series=series, cum=cum, holds=hold_vals, losses=loss_vals,
    contrib_syms=contrib_sorted["symbol"].tolist(), contrib_pnl=contrib_sorted["pnl"].tolist(),
)

def inr(x):
    if x is None: return "—"
    a = abs(x); s = "−" if x < 0 else ""
    if a >= 1e7: return f"{s}₹{a/1e7:.2f} Cr"
    if a >= 1e5: return f"{s}₹{a/1e5:.2f}L"
    return f"{s}₹{a:,.0f}"

# ---------- broker table ----------
broker_rows = ""
for b in S["brokers"]:
    wr = f"{b['win_rate_trade']*100:.0f}% trade" if b["win_rate_trade"] else "—"
    ws = f"{b['win_rate_scrip']*100:.0f}% scrip" if b["win_rate_scrip"] else ""
    broker_rows += f"""<tr><td class="sym">{b['name']}</td><td>{b['window']}</td>
    <td class="num gain">+{inr(b['net_realized'])}</td><td class="num">{inr(b['turnover'])}</td>
    <td class="num">{b['orders']}</td><td class="num">{wr}{'<span class=mut> · '+ws+'</span>' if ws else ''}</td>
    <td class="mut">{b['notes']}</td></tr>"""

# ---------- open book table ----------
pill = {"thesis": '<span class="pill pthesis">THESIS HOLD</span>',
        "review": '<span class="pill preview">UNDER REVIEW</span>',
        "disclosure": '<span class="pill pdisc">DISCLOSURE</span>'}
op_rows = ""
for p in openpos:
    mark = f"<span class='loss'>{p['mark_pct']*100:.1f}%</span>" if p["mark_pct"] is not None else "<span class='pend'>mark pending</span>"
    cur = inr(p["current_value"]) if p["current_value"] else "—"
    cost = inr(p["cost"]) if p["cost"] else "—"
    op_rows += f"""<tr><td class="sym">{p['symbol']}<div class="mut sm">{p['broker']} · {p['qty']} sh</div></td>
    <td class="num">{cost}</td><td class="num">{cur}</td><td class="num">{mark}</td>
    <td>{pill[p['status']]}<div class="mut sm frame">{p['frame']}</div></td></tr>"""

# ---------- exhibits ----------
ex_cards = "".join(
    f"""<div class="exhibit"><div class="eyebrow">{e['tag']}</div><h3>{e['title']}</h3><p>{e['body']}</p></div>"""
    for e in S["exhibits"])

# ---------- returns cards ----------
r = S["returns"]
xr_lo_s = f"{xirr_lo*100:.1f}%" if xirr_lo is not None else "—"
xr_hi_s = f"+{xirr_hi*100:.1f}%" if xirr_hi and xirr_hi > 0 else (f"{xirr_hi*100:.1f}%" if xirr_hi is not None else "—")
returns_cards = f"""
<div class="rcard live"><div class="rname">Groww · all-in XIRR</div>
 <div class="rval">{xr_lo_s} <span class="to">to</span> {xr_hi_s}</div>
 <div class="rnote">{r['groww_xirr_note']}</div></div>
<div class="rcard"><div class="rname">Zerodha · all-in XIRR</div><div class="rval pend">PENDING</div>
 <div class="rnote">{r['zerodha_note']}</div></div>
<div class="rcard"><div class="rname">AngelOne · all-in XIRR</div><div class="rval pend">PENDING</div>
 <div class="rnote">{r['angelone_note']}</div></div>
<div class="rcard"><div class="rname">Combined · all-in XIRR</div><div class="rval pend">PENDING</div>
 <div class="rnote">{r['combined_note']}</div></div>"""

K = S["kpis"]
tpl = Template(open(ROOT / "template.html").read())
html = tpl.safe_substitute(
    PERSON=S["person"], TITLE=S["title"], WINDOW=S["window"], ASOF=S["as_of"],
    NET=inr(K["net_realized_total"]), NETNOTE=K["net_realized_note"],
    TURN=inr(K["turnover"]), ORDERS=str(K["orders"]),
    WIN=f"{K['blended_win_rate']*100:.0f}%", PF=f"{K['profit_factor_groww']:.2f}",
    HOLD=f"{K['median_hold_groww_days']:.0f}d / {K['median_hold_zerodha_days']:.0f}d",
    BROKER_ROWS=broker_rows, OPEN_ROWS=op_rows, EXHIBITS=ex_cards, RETURNS=returns_cards,
    PAYLOAD=json.dumps(payload),
)
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html)
print(f"built {OUT} ({len(html):,} bytes) · Groww XIRR range {xr_lo_s} → {xr_hi_s}")
