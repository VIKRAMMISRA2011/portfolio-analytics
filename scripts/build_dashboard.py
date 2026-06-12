"""Builds the static dashboard (docs/index.html) from data/ files. Re-run after updating data."""
import pandas as pd, numpy as np, json, os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D = lambda f: os.path.join(ROOT, 'data', f)
S = json.load(open(D('summary_metrics.json')))
monthly = pd.read_csv(D('monthly_realized.csv'))
lots = pd.read_csv(D('trade_lots.csv'))
inst = pd.read_csv(D('instrument_pnl.csv'), index_col=0)
ob = pd.read_csv(D('open_book.csv'))

# ---- palette / fonts ----
BG0, BG1, BG2 = '#0A0E13', '#10161E', '#161E28'
TXT, MUT, HAIR = '#E8ECF1', '#8A97A6', '#232D3A'
BRASS, UP, DN = '#C9A227', '#34C98E', '#E5604C'
BROKER_C = {'Zerodha':'#5B8DEF', 'AngelOne':'#C9A227', 'Groww':'#34C98E'}
FONT = 'IBM Plex Mono, monospace'

def inr(x, dec=0):
    if pd.isna(x): return '—'
    neg = x < 0; x = abs(x)
    s = f'{x:,.{dec}f}'
    parts = s.split('.'); ip = parts[0].replace(',','')
    if len(ip) > 3:
        ip = ip[:-3][::-1]
        ip = ','.join(ip[i:i+2] for i in range(0,len(ip),2))[::-1] + ',' + s.split('.')[0].replace(',','')[-3:]
    out = '₹' + ip + ('.'+parts[1] if dec else '')
    return ('−' if neg else '') + out

LAYOUT = dict(template=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
  font=dict(family=FONT, color=MUT, size=11.5), margin=dict(l=8,r=8,t=8,b=8),
  xaxis=dict(gridcolor=HAIR, zerolinecolor=HAIR, linecolor=HAIR, tickfont=dict(size=11)),
  yaxis=dict(gridcolor=HAIR, zerolinecolor=HAIR, linecolor=HAIR, tickfont=dict(size=11)),
  legend=dict(orientation='h', y=1.08, x=0, font=dict(size=11), bgcolor='rgba(0,0,0,0)'),
  hoverlabel=dict(bgcolor=BG2, bordercolor=HAIR, font=dict(family=FONT, color=TXT, size=12)))

CFG = dict(displayModeBar=False, responsive=True)
frag = lambda fig, h: fig.to_html(include_plotlyjs=False, full_html=False, default_height=h, config=CFG)

# ---- 1. monthly cadence + cumulative ----
f1 = make_subplots(specs=[[{'secondary_y': True}]])
for b in ['Zerodha','AngelOne','Groww']:
    f1.add_bar(x=monthly['month'], y=monthly[b], name=b, marker_color=BROKER_C[b], marker_line_width=0,
               hovertemplate=b+' · %{x}<br>%{y:,.0f}<extra></extra>')
f1.add_scatter(x=monthly['month'], y=monthly['Cumulative'], name='Cumulative', mode='lines',
               line=dict(color=TXT, width=2.2, shape='spline', smoothing=0.6), secondary_y=True,
               hovertemplate='Cumulative · %{x}<br>%{y:,.0f}<extra></extra>')
f1.update_layout(barmode='relative', **LAYOUT)
f1.update_yaxes(title=None, secondary_y=False, gridcolor=HAIR, zerolinecolor=HAIR)
f1.update_yaxes(showgrid=False, secondary_y=True, tickfont=dict(color=TXT))
CH1 = frag(f1, 360)

# ---- 2. lot P&L distribution ----
clip = lots[(lots.pnl>-12000)&(lots.pnl<12000)]
outl = len(lots)-len(clip)
f2 = go.Figure()
f2.add_histogram(x=clip.loc[clip.pnl>=0,'pnl'], nbinsx=40, marker_color=UP, marker_line_width=0, name='Profitable lots')
f2.add_histogram(x=clip.loc[clip.pnl<0,'pnl'], nbinsx=40, marker_color=DN, marker_line_width=0, name='Losing lots')
f2.update_layout(barmode='overlay', **LAYOUT); f2.update_traces(opacity=0.92, hovertemplate='%{x:,.0f} band · %{y} lots<extra></extra>')
CH2 = frag(f2, 300)

# ---- 3. holding periods ----
bins = [-1,1,7,30,90,10000]; labs=['Intraday–1d','2–7d','8–30d','31–90d','90d+']
hp = pd.cut(lots['hold'], bins=bins, labels=labs).value_counts().reindex(labs)
f3 = go.Figure(go.Bar(x=labs, y=hp.values, marker_color=['#3E5C8F','#46729F','#4E88AE','#569EBD','#5EB4CC'],
                      marker_line_width=0, hovertemplate='%{x} · %{y} lots<extra></extra>'))
f3.update_layout(**LAYOUT); CH3 = frag(f3, 300)

# ---- 4. instrument attribution ----
top = inst.reindex(inst['realized_pnl'].abs().sort_values(ascending=False).head(14).index).sort_values('realized_pnl')
f4 = go.Figure(go.Bar(x=top['realized_pnl'], y=[s[:26] for s in top.index], orientation='h',
                      marker_color=[UP if v>0 else DN for v in top['realized_pnl']], marker_line_width=0,
                      hovertemplate='%{y} · %{x:,.0f}<extra></extra>'))
f4.update_layout(**LAYOUT); f4.update_yaxes(tickfont=dict(size=10.5)); CH4 = frag(f4, 420)

# ---- 5. open book marks (ex-pending) ----
obm = ob.dropna(subset=['unrl']).copy()
obm['lbl'] = obm['position'] + ' · ' + obm['broker']
f5 = go.Figure(go.Bar(x=obm['unrl'], y=obm['lbl'], orientation='h', marker_color=DN, marker_line_width=0,
                      hovertemplate='%{y}<br>%{x:,.0f} unrealized<extra></extra>'))
f5.update_layout(**LAYOUT); CH5 = frag(f5, 230)

T = S['totals']; B = S['brokers']
kpis = [
 ('Net realized P&L', inr(T['net_realized_incl_div']), 'incl. ₹12,298 dividends · net of all charges', 'v'),
 ('Total turnover', '₹2.76 Cr', 'buy + sell value, 3 brokers', 'v'),
 ('Orders executed', f"{T['orders']}", '48+ instruments · cash equity, F&O, IPO', 'v'),
 ('Trade-lot win rate', f"{T['lot_win_rate']*100:.1f}%", f"{T['lots']} FIFO-matched lots (Zerodha + Groww)", 'v'),
 ('Profit factor', f"{T['profit_factor']}", 'gross profits ÷ gross losses, lot level', 'v'),
 ('Median holding period', f"{T['median_hold_days']:.0f} days", 'short-horizon swing profile', 'v'),
]
kpi_html = '\n'.join(f'''<div class="kpi"><div class="kpi-label">{l}</div><div class="kpi-val">{v}</div><div class="kpi-sub">{s}</div></div>''' for l,v,s,_ in kpis)

recon = [
 ('Zerodha', 'FIFO engine ↔ broker statement', '₹0.00 variance', 'ok'),
 ('Groww', 'fund ledger ↔ order history', 'closes within ₹40', 'ok'),
 ('Groww', 'IPO gain recovered from settlement gap', '+₹59,234', 'ok'),
 ('AngelOne', 'statement scrip-level nets', 'verified', 'ok'),
 ('Pending', 'XIRR · benchmark · 1 mark · FY25 file', '4 items', 'wait'),
]
recon_html = '\n'.join(f'''<div class="chip {c}"><span class="chip-b">{a}</span><span>{b}</span><span class="chip-v">{v}</span></div>''' for a,b,v,c in recon)

brow = lambda k,n: f'''<tr><td class="bname">{n}</td><td>{B[k]['window']}</td><td class="num {'up' if B[k]['net']>0 else 'dn'}">{inr(B[k]['net'])}</td><td class="num">{inr(B[k]['turnover'])}</td><td class="num">{B[k]['orders']}</td><td class="num">{f"{B[k].get('lot_wr',B[k].get('scrip_wr'))*100:.0f}%"}</td><td class="note">{B[k]['note']}</td></tr>'''
broker_tbl = brow('zerodha','Zerodha') + brow('angelone','AngelOne') + brow('groww','Groww')

ob_rows = ''
for _,r in ob.iterrows():
    pct = '' if pd.isna(r['unrl']) else f" ({r['unrl']/r['cost']*100:+.1f}%)"
    cls = 'dn' if (not pd.isna(r['unrl']) and r['unrl']<0) else ('pend' if pd.isna(r['unrl']) else 'up')
    val = '—' if r['as_of']=='not covered' else ('mark pending' if pd.isna(r['value']) else inr(r['value']))
    unr = '—' if pd.isna(r['unrl']) else inr(r['unrl'])+pct
    ob_rows += f'''<tr><td class="bname">{r['position']}</td><td>{r['broker']}</td><td class="num">{int(r['qty'])}</td><td class="num">{inr(r['cost'])}</td><td class="num">{val}</td><td class="num {cls}">{unr}</td><td>{r['as_of']}</td><td class="note">{r['frame']}</td></tr>'''

ex_html = '\n'.join(f'''<div class="exhibit"><div class="ex-date">{e['date']}</div><h4>{e['title']}</h4><div class="ex-stat">{e['stat']}</div><p>{e['body']}</p></div>''' for e in S['exhibits'])
pend_html = '\n'.join(f'<li>{p}</li>' for p in S['pending'])

HTML = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent Portfolio — Verified Track Record · Sep 2023–Jun 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{{--bg0:{BG0};--bg1:{BG1};--bg2:{BG2};--txt:{TXT};--mut:{MUT};--hair:{HAIR};--brass:{BRASS};--up:{UP};--dn:{DN}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg0);color:var(--txt);font:15px/1.65 "IBM Plex Sans",sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 28px}}
header{{padding:64px 0 36px;border-bottom:1px solid var(--hair)}}
.eyebrow{{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.22em;color:var(--brass);text-transform:uppercase}}
h1{{font:600 clamp(28px,4vw,42px)/1.15 "IBM Plex Serif",serif;margin:14px 0 10px}}
.meta{{color:var(--mut);font:13px/1.6 "IBM Plex Mono",monospace}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));border:1px solid var(--hair);border-radius:6px;margin:36px 0 14px;background:var(--bg1);overflow:hidden}}
.kpi{{padding:20px 18px;border-right:1px solid var(--hair)}}.kpi:last-child{{border-right:0}}
.kpi-label{{font:500 10.5px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}}
.kpi-val{{font:600 26px/1.2 "IBM Plex Mono",monospace;margin:10px 0 6px;font-variant-numeric:tabular-nums}}
.kpi-sub{{font-size:12px;color:var(--mut);line-height:1.45}}
.recon{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}}
.chip{{display:flex;gap:8px;align-items:baseline;font:12px/1 "IBM Plex Mono",monospace;border:1px solid var(--hair);border-radius:4px;padding:8px 12px;background:var(--bg1);color:var(--mut)}}
.chip.ok{{border-left:3px solid var(--up)}}.chip.wait{{border-left:3px solid var(--brass)}}
.chip-b{{color:var(--txt);font-weight:600}}.chip-v{{color:var(--brass)}}
section{{padding:46px 0;border-bottom:1px solid var(--hair)}}
.sec-head{{display:flex;align-items:baseline;gap:14px;margin-bottom:6px}}
.sec-no{{font:600 12px/1 "IBM Plex Mono",monospace;color:var(--brass);letter-spacing:.14em}}
h2{{font:600 23px/1.25 "IBM Plex Serif",serif}}
.sec-sub{{color:var(--mut);max-width:760px;margin-bottom:22px;font-size:14px}}
.panel{{background:var(--bg1);border:1px solid var(--hair);border-radius:6px;padding:18px 16px 8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.ph{{font:500 11px/1 "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);padding:2px 4px 12px}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th{{font:500 10.5px/1.3 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);text-align:left;padding:10px 12px;border-bottom:1px solid var(--hair)}}
td{{padding:11px 12px;border-bottom:1px solid var(--hair);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
.num{{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;white-space:nowrap}}
.bname{{font-weight:600}}.up{{color:var(--up)}}.dn{{color:var(--dn)}}.pend{{color:var(--brass)}}
.note{{color:var(--mut);font-size:12.5px;max-width:300px}}
.exhibits{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}
.exhibit{{background:var(--bg1);border:1px solid var(--hair);border-left:3px solid var(--brass);border-radius:6px;padding:22px}}
.ex-date{{font:600 11px/1 "IBM Plex Mono",monospace;color:var(--mut);letter-spacing:.14em}}
.exhibit h4{{font:600 17px/1.3 "IBM Plex Serif",serif;margin:10px 0 6px}}
.ex-stat{{font:600 15px/1.3 "IBM Plex Mono",monospace;color:var(--up);margin-bottom:10px}}
.exhibit p{{font-size:13.5px;color:var(--mut)}}
.method ol{{margin:14px 0 0 20px;display:grid;gap:12px;font-size:14px}}
.method li::marker{{color:var(--brass);font-family:"IBM Plex Mono",monospace}}
.pending{{background:var(--bg1);border:1px solid var(--hair);border-left:3px solid var(--brass);border-radius:6px;padding:18px 22px;margin-top:22px}}
.pending h4{{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--brass);margin-bottom:10px}}
.pending li{{font-size:13.5px;color:var(--mut);margin:6px 0 6px 18px}}
footer{{padding:38px 0 64px;color:var(--mut);font-size:12.5px;line-height:1.7}}
footer .mono{{font-family:"IBM Plex Mono",monospace}}
@media(max-width:760px){{.grid2{{grid-template-columns:1fr}}.kpi{{border-right:0;border-bottom:1px solid var(--hair)}}table{{font-size:12.5px}}.note{{max-width:none}}}}
</style></head><body>
<header><div class="wrap">
<div class="eyebrow">Independent Portfolio · Verified Track Record</div>
<h1>Three brokers, every rupee reconciled.</h1>
<div class="meta">Sep 2023 – Jun 2026 · Zerodha / AngelOne / Groww · {T['orders']} orders · built from tradebooks, P&amp;L statements, fund ledgers &amp; dividend reports · Python + pandas + Plotly</div>
<div class="kpis">{kpi_html}</div>
<div class="recon">{recon_html}</div>
</div></header>

<section><div class="wrap">
<div class="sec-head"><span class="sec-no">01</span><h2>Realized record</h2></div>
<p class="sec-sub">Monthly realized P&amp;L by broker with the cumulative line. Trade-lot cadence shown gross of charges (AngelOne per statement nets); headline figures above are net of all charges. Every monthly total reconciles to broker statements.</p>
<div class="panel"><div class="ph">Monthly realized P&amp;L · cumulative (right axis)</div>{CH1}</div>
</div></section>

<section><div class="wrap">
<div class="sec-head"><span class="sec-no">02</span><h2>Broker comparison</h2></div>
<p class="sec-sub">Three accounts, three roles: Zerodha ran the FY24 PSU/infra swing book, AngelOne the FY25 concentrated quality-names account, Groww the primary book including IPO and event positions.</p>
<div class="panel" style="padding:0"><table><thead><tr><th>Broker</th><th>Window</th><th>Net realized</th><th>Turnover</th><th>Orders</th><th>Win rate</th><th>Reconciliation</th></tr></thead><tbody>{broker_tbl}</tbody></table></div>
</div></section>

<section><div class="wrap">
<div class="sec-head"><span class="sec-no">03</span><h2>Signature exhibits</h2></div>
<p class="sec-sub">Three episodes that define the record — each fully timestamped in the underlying data.</p>
<div class="exhibits">{ex_html}</div>
</div></section>

<section><div class="wrap">
<div class="sec-head"><span class="sec-no">04</span><h2>Trade analytics</h2></div>
<p class="sec-sub">Distribution views over {T['lots']} FIFO-matched lots (Zerodha + Groww). {outl} offsetting corporate-action lots (±₹99k, Reliance bonus) sit outside the histogram range and net to ≈ +₹319.</p>
<div class="grid2">
<div class="panel"><div class="ph">Per-lot P&amp;L distribution (₹)</div>{CH2}</div>
<div class="panel"><div class="ph">Holding-period profile</div>{CH3}</div>
</div>
<div class="panel" style="margin-top:18px"><div class="ph">Realized P&amp;L attribution by instrument · top 14 by magnitude</div>{CH4}</div>
</div></section>

<section><div class="wrap">
<div class="sec-head"><span class="sec-no">05</span><h2>Open book</h2></div>
<p class="sec-sub">Positions currently held, shown separately from the realized record and at honest marks. The realized figures above do not include these. One pledged holding awaits a current mark and is shown at cost. One historical exit outside the covered statements is disclosed rather than estimated.</p>
<div class="panel" style="padding:0;margin-bottom:18px"><table><thead><tr><th>Position</th><th>Broker</th><th>Qty</th><th>Cost</th><th>Value</th><th>Unrealized</th><th>As of</th><th>Frame</th></tr></thead><tbody>{ob_rows}</tbody></table></div>
<div class="panel"><div class="ph">Unrealized marks · positions with current prices</div>{CH5}</div>
</div></section>

<section class="method"><div class="wrap">
<div class="sec-head"><span class="sec-no">06</span><h2>Methodology &amp; data integrity</h2></div>
<p class="sec-sub">How every number on this page was derived — so it reads as verified analysis, not marketing.</p>
<div class="panel" style="padding:22px 26px">
<ol>
<li><strong>Ingest.</strong> Raw broker exports: Zerodha tradebook + P&amp;L + fund ledger; AngelOne trades history + P&amp;L statement; Groww order history + two P&amp;L reports + balance statement + dividend report. Parsed with pandas; account identifiers stripped.</li>
<li><strong>Reconcile.</strong> An independent FIFO matching engine reproduces Zerodha's stated realized P&amp;L to ₹0.00. Groww's fund ledger reconciles to its order history within ₹40 after corporate-action adjustment.</li>
<li><strong>Corporate actions.</strong> Reliance 1:1 bonus, OLA Electric IPO allotment, Vishal Mega Mart IPO, Siemens Energy demerger and rights entitlements handled explicitly. The OLA IPO sale (+₹59,234) is absent from broker P&amp;L (IPO cost basis) and was recovered from a ₹1.85L settlement-ledger gap.</li>
<li><strong>Metrics.</strong> Net realized = statement realized − all charges (₹31,894 total across brokers) + dividends per registrar report. Win rate and profit factor computed on FIFO-matched lots. Turnover = buy value + sell value. Holding period = sell date − FIFO buy date.</li>
<li><strong>Marks.</strong> Open positions priced from broker statements as of the dates shown per row; no model prices.</li>
<li><strong>Separation.</strong> Realized record and open book are presented separately by design; neither is netted into the other anywhere on this page.</li>
</ol>
<div class="pending"><h4>Pending — disclosed, not hidden</h4><ul>{pend_html}</ul></div>
</div>
</div></section>

<footer><div class="wrap">
<div class="mono">Generated {S['generated']} · regenerate with <strong>python scripts/build_dashboard.py</strong> after updating data/</div>
<div style="margin-top:8px">Personal investment record presented as analytical proof-of-work. Not investment advice or a solicitation. All figures derived from broker statements; derived datasets in <span class="mono">data/</span>. No account identifiers, client codes, or personal data are published.</div>
</div></footer>
</body></html>'''

out = os.path.join(ROOT, 'docs', 'index.html')
open(out, 'w').write(HTML)
print('written:', out, f'({len(HTML)/1024:.0f} KB)')
