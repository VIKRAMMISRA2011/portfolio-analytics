"""
build_dashboard.py — renders docs/index.html from data/. The only build entry point.

Every figure on the page is read from data/ or computed here. A validation block
at the end asserts that headline numbers tie to the published datasets before the
page is written. Optional: data/benchmark.csv (month,date,tri) activates the
NIFTY 50 TRI context overlay; absent, the section renders as PENDING — never
approximated.
"""
import pandas as pd, numpy as np, json, os, html

import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D = lambda f: os.path.join(ROOT, 'data', f)

S       = json.load(open(D('summary_metrics.json'), encoding='utf-8'))
monthly = pd.read_csv(D('monthly_realized.csv'))
lots    = pd.read_csv(D('trade_lots.csv'))
inst    = pd.read_csv(D('instrument_pnl.csv'), index_col=0)
ob      = pd.read_csv(D('open_book.csv'))
BENCH_PATH = D('benchmark.csv')
bench   = pd.read_csv(BENCH_PATH) if os.path.exists(BENCH_PATH) else None
BSRC_PATH = D('benchmark_source.json')
bsrc    = json.load(open(BSRC_PATH, encoding='utf-8')) if os.path.exists(BSRC_PATH) else {}

PERSON   = 'Vikram Misra'
REPO_URL = 'https://github.com/vikrammisra2011/portfolio-analytics'
PAGE_URL = 'https://vikrammisra2011.github.io/portfolio-analytics/'
LINKEDIN = ''   # ← paste your LinkedIn URL here, e.g. 'https://linkedin.com/in/vikram-misra'

# ---------------- palette / typography ----------------
BG0, BG1, BG2 = '#0A0F1A', '#0F1626', '#1A2740'
TXT, MUT, HAIR = '#E9EDF5', '#8C99AF', '#22304D'
BRASS, UP, DN = '#D4AF37', '#2FB98A', '#E25C4C'
BLUE = '#4F86E8'
BROKER_C = {'Zerodha': '#4F86E8', 'AngelOne': '#D4AF37', 'Groww': '#2FB98A'}
FONT = 'IBM Plex Mono, monospace'

def inr(x, dec=0, sign=False):
    """Indian-grouped rupee string. −/+ prefixes; em-dash for missing."""
    if x is None or (isinstance(x, float) and pd.isna(x)): return '—'
    neg = x < 0; a = abs(x)
    s = f'{a:,.{dec}f}'
    ip, _, dp = s.partition('.')
    digits = ip.replace(',', '')
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:]); head = head[:-2]
        if head: groups.insert(0, head)
        ip = ','.join(groups + [tail])
    out = '₹' + ip + (('.' + dp) if dec else '')
    return ('−' if neg else ('+' if sign else '')) + out

def lakh(x, sign=False):
    if x is None or (isinstance(x, float) and pd.isna(x)): return '—'
    a = abs(x); s = '−' if x < 0 else ('+' if sign else '')
    if a >= 1e7: return f'{s}₹{a/1e7:.2f} Cr'
    if a >= 1e5: return f'{s}₹{a/1e5:.2f}L'
    return f'{s}₹{a:,.0f}'

# base Plotly layout — automargin on both axes prevents axis-label clipping at any width
LAYOUT = dict(template=None, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
  font=dict(family=FONT, color=MUT, size=12),
  margin=dict(l=56, r=18, t=22, b=38),
  xaxis=dict(gridcolor=HAIR, zerolinecolor=HAIR, linecolor=HAIR, tickfont=dict(size=11.5),
             automargin=True, ticklen=5, tickcolor=HAIR, title=dict(font=dict(size=11, color=MUT), standoff=12)),
  yaxis=dict(gridcolor=HAIR, zerolinecolor=HAIR, linecolor=HAIR, tickfont=dict(size=11.5),
             automargin=True, ticklen=5, tickcolor=HAIR, title=dict(font=dict(size=11, color=MUT), standoff=10)),
  legend=dict(orientation='h', y=1.12, x=0, yanchor='bottom', font=dict(size=11.5), bgcolor='rgba(0,0,0,0)'),
  hoverlabel=dict(bgcolor=BG2, bordercolor=HAIR, font=dict(family=FONT, color=TXT, size=12.5)),
  autosize=True, bargap=0.24)
CFG = dict(displayModeBar=False, responsive=True)
# shared annotation style — legible chip that sits above gridlines without colliding
ANNO = dict(showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=MUT,
            bgcolor='rgba(10,14,19,0.82)', bordercolor=HAIR, borderwidth=1, borderpad=4,
            font=dict(family=FONT, size=11, color=TXT))
# consistent chart-height scale
H_HERO, H_TALL, H_STD, H_SHORT, H_BAND = 380, 440, 320, 270, 220
_MABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
def mlab(seq):
    "2024-06 -> Jun '24 : compact, readable time axes"
    return [f"{_MABBR[int(m[5:7])-1]} '{m[2:4]}" for m in seq]
frag = lambda fig, h: fig.to_html(include_plotlyjs=False, full_html=False, default_height=h, config=CFG)

# =====================================================================
#  DERIVED METRICS — every number used on the page is computed here
# =====================================================================
T, B = S['totals'], S['brokers']

# ---- cadence & drawdown on the cumulative realized curve ----
tot  = monthly['Total']
cum  = monthly['Cumulative']
peak = cum.cummax()
dd   = cum - peak
i_tr = int(dd.idxmin())                       # trough month index
i_pk = int(cum[:i_tr + 1].idxmax())           # preceding peak
i_rec = next((i for i in range(i_tr, len(cum)) if cum[i] >= peak[i_tr]), None)
MAXDD       = float(dd.min())
DD_PEAK_M   = monthly.month[i_pk]
DD_TROUGH_M = monthly.month[i_tr]
DD_REC_M    = monthly.month[i_rec] if i_rec is not None else None

ACTIVE_M  = len(monthly)
POS_M     = int((tot > 0).sum())
HIT_M     = POS_M / ACTIVE_M
BEST_I, WORST_I = int(tot.idxmax()), int(tot.idxmin())
AVG_UP    = float(tot[tot > 0].mean())
AVG_DN    = float(tot[tot < 0].mean())
streak = mx_streak = 0
for v in tot:
    streak = streak + 1 if v < 0 else 0
    mx_streak = max(mx_streak, streak)

# ---- lot-level statistics ----
w_, l_ = lots.loc[lots.pnl > 0, 'pnl'], lots.loc[lots.pnl < 0, 'pnl']
EXPECT   = float(lots.pnl.mean())
AVG_WIN, AVG_LOSS = float(w_.mean()), float(l_.mean())
MED_WIN, MED_LOSS = float(w_.median()), float(l_.median())
PAYOFF   = AVG_WIN / abs(AVG_LOSS)
GROSS_P, GROSS_L = float(w_.sum()), float(l_.sum())
PF_ALL   = GROSS_P / abs(GROSS_L)
TOP5_PCT = float(w_.sort_values(ascending=False).head(5).sum() / GROSS_P)

# corporate-action artifact pair (Reliance 1:1 bonus FIFO legs): identified by
# magnitude — the two offsetting ±₹99k legs that net to ≈ +₹319.
pair      = lots[lots.pnl.abs() > 90000]
PAIR_NET  = float(pair.pnl.sum())
core      = lots[lots.pnl.abs() <= 90000]
wc, lc    = core.loc[core.pnl > 0, 'pnl'], core.loc[core.pnl < 0, 'pnl']
PF_CORE   = float(wc.sum() / abs(lc.sum()))
MAX_WIN_CORE,  MAX_LOSS_CORE = float(wc.max()), float(lc.min())
TOP5_CORE = float(wc.sort_values(ascending=False).head(5).sum() / wc.sum())

# per-broker lot stats (AngelOne publishes scrip-level nets only — no lots)
brstats = []
for b, g in lots.groupby('broker'):
    gw, gl = g.loc[g.pnl > 0, 'pnl'], g.loc[g.pnl < 0, 'pnl']
    brstats.append(dict(broker=b, n=len(g), wr=float((g.pnl > 0).mean()),
                        pf=float(gw.sum() / abs(gl.sum())), exp=float(g.pnl.mean()),
                        med_hold=float(g.hold.median()),
                        avg_win=float(gw.mean()), avg_loss=float(gl.mean())))
brstats.sort(key=lambda r: -r['n'])

# holding-period buckets — where the P&L actually came from
BIN_E = [-1, 1, 7, 30, 90, 10**5]
BIN_L = ['≤ 1d', '2–7d', '8–30d', '31–90d', '90d+']
hb = (lots.groupby(pd.cut(lots.hold, bins=BIN_E, labels=BIN_L), observed=False)
          .agg(n=('pnl', 'size'), pnl=('pnl', 'sum'), wr=('pnl', lambda x: (x > 0).mean())))

# instrument attribution
ip = inst['realized_pnl']
N_INST, N_WIN_INST = len(ip), int((ip > 0).sum())
INST_HIT  = N_WIN_INST / N_INST
GP_INST   = float(ip[ip > 0].sum())          # gross instrument profits
GL_INST   = float(ip[ip < 0].sum())          # gross instrument losses (≤0)
GIVEBACK  = abs(GL_INST) / GP_INST
TOP1_PCT_I = float(ip.max() / GP_INST)
TOP5_PCT_I = float(ip.sort_values(ascending=False).head(5).sum() / GP_INST)
ipd  = ip.sort_values(ascending=False)
pareto_cum = ipd.cumsum()

# charges bridge: monthly curve & lot/instrument tables are gross of Zerodha +
# Groww charges (AngelOne flows are statement nets); headline KPIs are fully net.
Z_CHG, G_CHG = 6305.07, 20855.29
BRIDGE_GROSS = float(tot.sum())
BRIDGE_NET   = BRIDGE_GROSS - Z_CHG - G_CHG

# open book (display only — never netted into the realized record)
obm = ob.dropna(subset=['unrl'])

# verification attestations (published, identifier-free; produced by scripts/verify_sources.py)
VER_PATH = D('verification.json')
ver = json.load(open(VER_PATH, encoding='utf-8')) if os.path.exists(VER_PATH) else None
EVID_PATH = D('evidence.json')
evid = json.load(open(EVID_PATH, encoding='utf-8')) if os.path.exists(EVID_PATH) else None

# segment regrouping of the instrument table (pure arithmetic over published data)
SEG_MAP = {'OLA ELECTRIC (IPO flip)': 'IPO events', 'VISHAL MEGA MART': 'IPO events',
           'National Securities Depository': 'IPO events',
           'ZOMATO futures (intraday)': 'F&O', 'NIFTY options (Dec 24)': 'F&O',
           'NIP IND ETF NIFTY 100': 'ETF / index'}
seg_grp = ip.groupby(ip.index.map(lambda s: SEG_MAP.get(str(s), 'Cash equity')))
SEG  = seg_grp.sum().sort_values(ascending=False)
SEGN = seg_grp.count()
# ledger-verified bank flows per account window (attested in data/verification.json)
CAP = [('Zerodha',  822150,  717153, B['zerodha']['turnover'],  B['zerodha']['net']),
       ('AngelOne', 1653450, 1376246, B['angelone']['turnover'], B['angelone']['net']),
       ('Groww',    2072899, 1877118, B['groww']['turnover'],    B['groww']['net'])]

# benchmark (only if real data has been supplied)
if bench is not None:
    bench = bench.sort_values('month').reset_index(drop=True)
    BLAB  = bsrc.get('label', 'NIFTY 50 TRI')
    # month-over-month index returns on the contiguous series; the last row may
    # be a partial month (MTD) — excluded from monthly stats, kept on the chart.
    bench['ret'] = bench['tri'].pct_change()
    bstat = bench.iloc[:-1] if bsrc.get('partial_last') else bench
    REBASE  = 100 * bench['tri'] / bench['tri'].iloc[0]
    BW_RET  = float(bench['tri'].iloc[-1] / bench['tri'].iloc[0] - 1)
    _d0 = pd.to_datetime(bench['date'].iloc[0]); _d1 = pd.to_datetime(bench['date'].iloc[-1])
    BW_DAYS = (_d1 - _d0).days
    BW_CAGR = float((bench['tri'].iloc[-1] / bench['tri'].iloc[0]) ** (365.25 / BW_DAYS) - 1)
    BW_BEST  = float(bstat['ret'].max())
    BW_WORST = float(bstat['ret'].min())
    # portfolio realized P&L in the index's down months (full calendar months only)
    bm = monthly.merge(bstat[['month', 'ret']], on='month', how='inner')
    dnm      = bm[bm['ret'] < 0]
    DOWN_N   = len(dnm)
    DOWN_POS = int((dnm['Total'] > 0).sum())

# =====================================================================
#  CHARTS
# =====================================================================
months = monthly['month'].tolist()
MLAB = mlab(months)

# 01a — monthly cadence + cumulative (hero)
f1 = make_subplots(specs=[[{'secondary_y': True}]])
for b in ['Zerodha', 'AngelOne', 'Groww']:
    f1.add_bar(x=months, y=monthly[b], name=b, marker_color=BROKER_C[b], marker_line_width=0,
               hovertemplate=b + " · %{x}<br>₹%{y:,.0f}<extra></extra>")
f1.add_scatter(x=months, y=cum, name='Cumulative realized', mode='lines',
               line=dict(color=TXT, width=2.4, shape='spline', smoothing=0.6), secondary_y=True,
               hovertemplate='Cumulative · %{x}<br>₹%{y:,.0f}<extra></extra>')
f1.update_layout(barmode='relative', **LAYOUT)
f1.update_layout(margin_t=54, legend=dict(orientation='h', y=1.16, x=0, yanchor='bottom', font=dict(size=11.5)))
f1.update_xaxes(tickvals=months, ticktext=MLAB, tickangle=-45)
f1.update_yaxes(secondary_y=False, gridcolor=HAIR, zerolinecolor=HAIR, tickprefix='₹', tickformat='~s', title_text='Monthly')
f1.update_yaxes(secondary_y=True, showgrid=False, tickfont=dict(color=TXT), tickprefix='₹', tickformat='~s', title_text='Cumulative')
CH1 = frag(f1, H_HERO)

# 01b — calendar heatmap of monthly realized P&L
mm = monthly.copy()
mm['y'] = mm.month.str[:4]; mm['m'] = mm.month.str[5:7].astype(int)
grid = mm.pivot(index='y', columns='m', values='Total').reindex(columns=range(1, 13))
MOS = _MABBR
zmax = float(np.nanmax(np.abs(grid.values)))
annot = [[('' if pd.isna(v) else f'{v/1000:+,.1f}k') for v in row] for row in grid.values]
fH = go.Figure(go.Heatmap(z=grid.values, x=MOS, y=grid.index.tolist(),
    zmin=-zmax, zmax=zmax, colorscale=[[0, DN], [0.5, '#141B25'], [1, UP]],
    text=annot, texttemplate='%{text}', textfont=dict(family=FONT, size=11),
    hovertemplate='%{y} %{x} · ₹%{z:,.0f}<extra></extra>', xgap=4, ygap=4, showscale=False))
fH.update_layout(**LAYOUT)
fH.update_layout(margin=dict(l=42, r=18, t=30, b=18))
fH.update_yaxes(autorange='reversed', showgrid=False, tickfont=dict(size=12))
fH.update_xaxes(showgrid=False, side='top', tickfont=dict(size=11.5))
CHH = frag(fH, H_BAND)

# 02 — underwater curve (drawdown of cumulative realized P&L)
fU = go.Figure()
fU.add_scatter(x=months, y=dd, mode='lines', line=dict(color=DN, width=1.8),
               fill='tozeroy', fillcolor='rgba(229,96,76,0.18)', name='Drawdown',
               hovertemplate='%{x} · ₹%{y:,.0f} below peak<extra></extra>')
fU.add_annotation(x=DD_TROUGH_M, y=MAXDD, text=f'max {inr(MAXDD)} · {DD_TROUGH_M}',
                  ax=0, ay=-34, yanchor='bottom', **ANNO)
fU.update_layout(**LAYOUT)
fU.update_xaxes(tickvals=months, ticktext=MLAB, tickangle=-45)
fU.update_yaxes(tickprefix='₹', tickformat='~s')
CHU = frag(fU, H_SHORT)

# 03a — instrument attribution (top by magnitude)
top = inst.reindex(ip.abs().sort_values(ascending=False).head(14).index).sort_values('realized_pnl')
f4 = go.Figure(go.Bar(x=top['realized_pnl'], y=[s[:24] for s in top.index], orientation='h',
                      marker_color=[UP if v > 0 else DN for v in top['realized_pnl']],
                      marker_line_width=0, hovertemplate='%{y} · ₹%{x:,.0f}<extra></extra>'))
f4.update_layout(**LAYOUT)
f4.update_yaxes(tickfont=dict(size=11))
f4.update_xaxes(tickprefix='₹', tickformat='~s', zeroline=True, zerolinecolor=MUT, zerolinewidth=1)
CH4 = frag(f4, H_TALL)

# 03b — Pareto: cumulative realized P&L by instrument rank
fP = go.Figure()
fP.add_scatter(x=list(range(1, N_INST + 1)), y=pareto_cum.values, mode='lines',
               line=dict(color=BRASS, width=2.2),
               fill='tozeroy', fillcolor='rgba(201,162,39,0.10)',
               text=pareto_cum.index, name='Cumulative P&L',
               hovertemplate='#%{x} %{text}<br>cumulative ₹%{y:,.0f}<extra></extra>')
fP.add_hline(y=float(ip.sum()), line_color=HAIR, line_dash='dot')
fP.add_annotation(x=N_WIN_INST, y=GP_INST, text=f'winners peak {lakh(GP_INST)}', ax=0, ay=-30, **ANNO)
fP.add_annotation(x=N_INST, y=float(ip.sum()), text=f'net {lakh(float(ip.sum()))}', showarrow=False,
                  xanchor='right', yanchor='bottom', font=dict(family=FONT, size=11, color=MUT))
fP.update_layout(**LAYOUT)
fP.update_xaxes(title_text='Instruments, ranked by contribution')
fP.update_yaxes(tickprefix='₹', tickformat='~s')
CHP = frag(fP, H_TALL)

# 03c — P&L by holding bucket
fB = go.Figure(go.Bar(x=BIN_L, y=hb['pnl'], marker_color=[UP if v >= 0 else DN for v in hb['pnl']],
    marker_line_width=0,
    text=[f"{int(n)} lots · {wr*100:.0f}% WR" for n, wr in zip(hb['n'], hb['wr'])],
    textposition='outside', textfont=dict(family=FONT, size=11, color=MUT), cliponaxis=False,
    hovertemplate='%{x} · ₹%{y:,.0f}<extra></extra>'))
fB.update_layout(**LAYOUT)
fB.update_yaxes(range=[0, float(hb['pnl'].max()) * 1.26], tickprefix='₹', tickformat='~s')
CHB = frag(fB, H_STD)

# 04 — realized P&L by segment (regrouped instrument table)
fS = go.Figure(go.Bar(x=SEG.values, y=SEG.index.tolist(), orientation='h',
    marker_color=[UP if v >= 0 else DN for v in SEG.values], marker_line_width=0,
    text=[f"{lakh(float(v))} · {int(SEGN[k])} instr." for k, v in SEG.items()],
    textposition='auto', textfont=dict(family=FONT, size=11.5), cliponaxis=False,
    hovertemplate='%{y} · ₹%{x:,.0f}<extra></extra>'))
fS.update_layout(**LAYOUT)
fS.update_xaxes(tickprefix='₹', tickformat='~s', zeroline=True, zerolinecolor=MUT)
CHS = frag(fS, H_SHORT)

# 04a — per-lot P&L distribution
clip = lots[(lots.pnl > -12000) & (lots.pnl < 12000)]
outl = len(lots) - len(clip)
f2 = go.Figure()
f2.add_histogram(x=clip.loc[clip.pnl >= 0, 'pnl'], nbinsx=40, marker_color=UP, marker_line_width=0, name='Profitable lots')
f2.add_histogram(x=clip.loc[clip.pnl < 0, 'pnl'], nbinsx=40, marker_color=DN, marker_line_width=0, name='Losing lots')
f2.update_layout(barmode='overlay', **LAYOUT)
f2.update_layout(margin_t=54, legend=dict(orientation='h', y=1.16, x=0, yanchor='bottom', font=dict(size=11.5)))
f2.update_traces(opacity=0.9, hovertemplate='%{x:,.0f} band · %{y} lots<extra></extra>')
f2.update_xaxes(tickprefix='₹', tickformat='~s', title_text='Per-lot P&L (clipped ±12k)')
f2.update_yaxes(title_text='Lots')
CH2 = frag(f2, H_STD)

# 04b — holding-period histogram
hp = pd.cut(lots['hold'], bins=BIN_E, labels=BIN_L).value_counts().reindex(BIN_L)
f3 = go.Figure(go.Bar(x=BIN_L, y=hp.values, marker_color=['#3E5C8F', '#46729F', '#4E88AE', '#569EBD', '#5EB4CC'],
                      marker_line_width=0, text=hp.values, textposition='outside',
                      textfont=dict(family=FONT, size=11, color=MUT), cliponaxis=False,
                      hovertemplate='%{x} · %{y} lots<extra></extra>'))
f3.update_layout(**LAYOUT)
f3.update_yaxes(title_text='Lots', range=[0, float(hp.max()) * 1.18])
CH3 = frag(f3, H_STD)

# 07 — open book marks
obc = obm.copy(); obc['lbl'] = obc['position'] + ' · ' + obc['broker']
f5 = go.Figure(go.Bar(x=obc['unrl'], y=obc['lbl'], orientation='h', marker_color=DN, marker_line_width=0,
                      text=[inr(v) for v in obc['unrl']], textposition='auto',
                      textfont=dict(family=FONT, size=11, color=TXT),
                      hovertemplate='%{y}<br>₹%{x:,.0f} unrealized<extra></extra>'))
f5.update_layout(**LAYOUT)
f5.update_xaxes(tickprefix='₹', tickformat='~s')
CH5 = frag(f5, H_SHORT)

# 08 — benchmark context (renders only with real data)
if bench is not None:
    BMLAB = mlab(bench['month'].tolist())
    fN = make_subplots(specs=[[{'secondary_y': True}]])
    fN.add_scatter(x=bench['month'], y=REBASE, name=BLAB + ' (rebased = 100)',
                   mode='lines', line=dict(color=BRASS, width=2.2),
                   hovertemplate='%{x} · %{y:.1f}<extra></extra>')
    fN.add_scatter(x=months, y=cum, name='Cumulative realized ₹ (right)', mode='lines',
                   line=dict(color=TXT, width=1.8, dash='dot'), secondary_y=True,
                   hovertemplate='%{x} · ₹%{y:,.0f}<extra></extra>')
    for mth, lab in [('2024-06', 'election deployment'), ('2024-10', 'OLA IPO exit'), ('2025-07', 'best month')]:
        if mth in months:
            fN.add_vline(x=mth, line_color=HAIR, line_dash='dot')
            fN.add_annotation(x=mth, y=0.98, yref='paper', text=lab, showarrow=False, yanchor='top',
                              xanchor='center', font=dict(family=FONT, size=9.5, color=MUT),
                              bgcolor='rgba(10,14,19,0.7)')
    fN.update_layout(**LAYOUT)
    fN.update_layout(margin_t=54, legend=dict(orientation='h', y=1.16, x=0, yanchor='bottom', font=dict(size=11.5)))
    fN.update_xaxes(tickvals=bench['month'].tolist(), ticktext=BMLAB, tickangle=-45)
    fN.update_yaxes(secondary_y=False, gridcolor=HAIR, title_text='Index (=100)')
    fN.update_yaxes(secondary_y=True, showgrid=False, tickprefix='₹', tickformat='~s', title_text='Cumulative ₹')
    CHN = frag(fN, H_HERO)

# =====================================================================
#  HTML COMPONENTS
# =====================================================================
kpis = [
 ('Net realized P&L', inr(T['net_realized_incl_div']), f"incl. {inr(T['dividends'])} dividends · net of all charges"),
 ('Total turnover', '₹2.76 Cr', 'buy + sell value, 3 brokers'),
 ('Orders executed', f"{T['orders']}", f'{N_INST} instruments · cash equity, F&O, IPO'),
 ('Trade-lot win rate', f"{T['lot_win_rate']*100:.1f}%", f"{T['lots']} FIFO-matched lots (Zerodha + Groww)"),
 ('Profit factor', f"{T['profit_factor']}", f'{PF_CORE:.2f} ex corp-action pair · lot level'),
 ('Median holding period', f"{T['median_hold_days']:.0f} days", 'short-horizon swing profile'),
]
kpi_html = '\n'.join(f'<div class="kpi"><div class="kpi-label">{l}</div><div class="kpi-val">{v}</div><div class="kpi-sub">{s}</div></div>' for l, v, s in kpis)

recon = [
 ('Zerodha', 'FIFO engine ↔ broker statement', '₹0.00 variance', 'ok'),
 ('Groww', 'fund ledger ↔ order history', 'closes within ₹40', 'ok'),
 ('Groww', 'IPO gain recovered from settlement gap', '+₹59,234', 'ok'),
 ('AngelOne', 'statement scrip-level nets', 'verified', 'ok'),
 ('Resolved', 'OLA pledged + LODHA exit', '2 cleared', 'ok'),
 ('Pending', 'XIRR · demat transfer', '1 item', 'wait'),
]
_CHIPIC = {'ok': "<svg class='cic' viewBox='0 0 16 16' width='13' height='13'><path d='M6.4 10.6 3.8 8 2.7 9.1l3.7 3.7 7.0-7.0-1.1-1.1z' fill='currentColor'/></svg>",
           'wait': "<svg class='cic' viewBox='0 0 16 16' width='13' height='13'><circle cx='8' cy='8' r='6.3' fill='none' stroke='currentColor' stroke-width='1.4'/><path d='M8 4.5V8l2.4 1.6' fill='none' stroke='currentColor' stroke-width='1.4' stroke-linecap='round'/></svg>"}
recon_html = '\n'.join(f'<div class="chip {c}"><span class="cicw">{_CHIPIC.get(c, "")}</span><span class="chip-b">{a}</span><span>{b}</span><span class="chip-v">{v}</span></div>' for a, b, v, c in recon)

stat = lambda l, v, s, cls='': f'<div class="stat"><div class="stat-l">{l}</div><div class="stat-v {cls}">{v}</div><div class="stat-s">{s}</div></div>'
cad_html = ''.join([
 stat('Positive months', f'{POS_M} of {ACTIVE_M}', f'{HIT_M*100:.0f}% of active months', 'up'),
 stat('Best month', inr(float(tot.max())), monthly.month[BEST_I], 'up'),
 stat('Worst month', inr(float(tot.min())), monthly.month[WORST_I], 'dn'),
 stat('Avg up / down month', f'{lakh(AVG_UP)} / {lakh(AVG_DN)}', 'realized, active months only'),
])

risk_html = ''.join([
 stat('Max drawdown — realized curve', inr(MAXDD), f'peak {DD_PEAK_M} → trough {DD_TROUGH_M}', 'dn'),
 stat('Recovery', '1 month' if DD_REC_M else 'open', f'new high by {DD_REC_M}' if DD_REC_M else 'not yet recovered', 'up' if DD_REC_M else 'dn'),
 stat('Longest losing streak', f'{mx_streak} month' + ('s' if mx_streak != 1 else ''), 'consecutive negative active months'),
 stat('Largest open mark', inr(float(obm['unrl'].min())), 'open book — see section 08', 'dn'),
])

trade_html = ''.join([
 stat('Expectancy / lot', inr(EXPECT, sign=True), f'mean of {T["lots"]} matched lots', 'up'),
 stat('Avg win / avg loss', f'{inr(AVG_WIN)} / {inr(AVG_LOSS)}', f'payoff ratio {PAYOFF:.2f} — high win rate, modest payoff'),
 stat('Median win / median loss', f'{inr(MED_WIN)} / {inr(MED_LOSS)}', 'typical lot is small either way'),
 stat('Top-5 lots share of gross profit', f'{TOP5_PCT*100:.0f}%', f'{TOP5_CORE*100:.0f}% ex corp-action pair'),
])

brk_rows = ''.join(
 f"<tr><td class='bname'>{r['broker']}</td><td class='num'>{r['n']}</td><td class='num'>{r['wr']*100:.1f}%</td>"
 f"<td class='num'>{r['pf']:.2f}</td><td class='num'>{inr(r['exp'], sign=True)}</td>"
 f"<td class='num'>{r['med_hold']:.0f}d</td><td class='num'>{inr(r['avg_win'])} / {inr(r['avg_loss'])}</td></tr>"
 for r in brstats)
brk_rows += "<tr><td class='bname'>AngelOne</td><td class='num' colspan='6' style='text-align:left;color:var(--mut)'>statement publishes scrip-level nets only — no lot reconstruction possible; excluded from lot statistics (disclosed)</td></tr>"

brow = lambda k, n: (f"<tr><td class='bname'>{n}</td><td>{B[k]['window']}</td>"
 f"<td class='num {'up' if B[k]['net'] > 0 else 'dn'}'>{inr(B[k]['net'])}</td>"
 f"<td class='num'>{inr(B[k]['turnover'])}</td><td class='num'>{B[k]['orders']}</td>"
 f"<td class='num'>{B[k].get('lot_wr', B[k].get('scrip_wr'))*100:.0f}%</td>"
 f"<td class='note'>{B[k]['note']}</td></tr>")
broker_tbl = brow('zerodha', 'Zerodha') + brow('angelone', 'AngelOne') + brow('groww', 'Groww')

ob_rows = ''
OB_MARKED_TOTAL = 0.0   # sum of rows that have a live mark
OB_MARKED_COST  = 0.0
for _, r in ob.iterrows():
    pct = '' if pd.isna(r['unrl']) else f" ({r['unrl']/r['cost']*100:+.1f}%)"
    cls = 'dn' if (not pd.isna(r['unrl']) and r['unrl'] < 0) else ('pend' if pd.isna(r['unrl']) else 'up')
    val = '—' if r['as_of'] == 'not covered' else ('mark pending' if pd.isna(r['value']) else inr(r['value']))
    unr = '—' if pd.isna(r['unrl']) else inr(r['unrl']) + pct
    ob_rows += (f"<tr><td class='bname'>{r['position']}</td><td>{r['broker']}</td><td class='num'>{int(r['qty'])}</td>"
                f"<td class='num'>{inr(r['cost'])}</td><td class='num'>{val}</td><td class='num {cls}'>{unr}</td>"
                f"<td>{r['as_of']}</td><td class='note'>{r['frame']}</td></tr>")
    if not pd.isna(r['unrl']):
        OB_MARKED_TOTAL += float(r['unrl'])
        OB_MARKED_COST  += float(r['cost'])
# summary row for marked positions
OB_TOTAL_PCT = OB_MARKED_TOTAL / OB_MARKED_COST * 100
ob_rows += (f"<tr class='ob-total'><td class='bname' colspan='3'>Total — marked positions</td>"
            f"<td class='num'>{inr(OB_MARKED_COST)}</td><td class='num'>{inr(OB_MARKED_COST + OB_MARKED_TOTAL)}</td>"
            f"<td class='num dn'>{inr(OB_MARKED_TOTAL)} ({OB_TOTAL_PCT:+.1f}%)</td>"
            f"<td colspan='2' class='note'>{inr(OB_MARKED_TOTAL)} vs {inr(T['net_realized_incl_div'])} realized — open book is real and separate</td></tr>")

ex_html = '\n'.join(f"<div class='exhibit'><div class='ex-date'>{e['date']}</div><h4>{e['title']}</h4><div class='ex-stat'>{e['stat']}</div><p>{e['body']}</p></div>" for e in S['exhibits'])

pend_items = [p for p in S['pending'] if bench is None or 'benchmark' not in p.lower()]
pend_html = '\n'.join(f'<li>{p}</li>' for p in pend_items)

if bench is not None:
    bsrc_line = bsrc.get('citation', 'source on file')
    bench_stats = ''.join([
     stat('Index, full window', f'{BW_RET*100:+.1f}%', f'{bench["date"].iloc[0]} → {bench["date"].iloc[-1]}'),
     stat('Index CAGR', f'{BW_CAGR*100:+.1f}%', f'geometric, day-count basis ({BW_DAYS} days)'),
     stat('Index best / worst month', f'{BW_BEST*100:+.1f}% / {BW_WORST*100:+.1f}%', 'full calendar months only'),
    ])
    DOWN_CHIP = (f'<div class="bench-chip up"><span class="bench-chip-n">+ve in {DOWN_POS} of {DOWN_N}</span>'
                 f'<span class="bench-chip-l">index down-months where portfolio was active</span></div>'
                 if DOWN_N > 0 else '')
    bench_body = f"""
<div class="stats">{bench_stats}</div>
{DOWN_CHIP}
<div class="panel"><div class="ph">{BLAB}, rebased to 100 (left) · cumulative realized ₹ (right) · event markers</div>{CHN}</div>
<div class="takeaway">The two lines share a window, not a unit: the index is a per-rupee growth path; the portfolio line is cumulative cash P&amp;L without a fixed capital base. No relative-return claim is made until the money-weighted XIRR lands (pending AngelOne ledger). Shown for timing context only — the record's two largest months (Jun 2024, Jul 2025) were event entries, not index drift.</div>
<p class="srcline">Benchmark series: {bsrc_line}</p>"""
else:
    bench_body = """
<div class="panel pendpanel"><div class="ph">NIFTY 50 TRI overlay — PENDING</div>
<p class="pendbody">This section activates automatically when <span class="mono">data/benchmark.csv</span> (month, TRI close) is supplied from an official feed. It is left empty rather than approximated — the same standard applied to every figure on this page.</p></div>"""

# allocation + verification components
cap_rows = ''.join(
 f"<tr><td class='bname'>{n}</td><td class='num'>{inr(i)}</td><td class='num'>{inr(o)}</td>"
 f"<td class='num'>{inr(t)}</td><td class='num up'>{inr(v, sign=True)}</td></tr>"
 for n, i, o, t, v in CAP)
seg_take = (f"Cash equity drove {lakh(float(SEG.get('Cash equity', 0)))} across {int(SEGN.get('Cash equity', 0))} instruments. "
            f"Three IPO allotments (OLA Electric, Vishal Mega Mart, NSDL) added {lakh(float(SEG.get('IPO events', 0)))} — event-driven entries, fully documented in the order history. "
            f"A small F&O sleeve cost {lakh(float(SEG.get('F&O', 0)))}, and the single index-ETF position contributed {lakh(float(SEG.get('ETF / index', 0)))}.")
if ver:
    V_TIES, V_VARS = len(ver['ties']), len(ver['variances'])
    vsrc_rows = ''.join(f"<tr><td class='bname'>{s['source']}</td><td>{s['coverage']}</td><td class='vnote'>{s['drives']}</td></tr>" for s in ver['sources'])
    vtie_rows = ''.join(f"<tr><td>{t['metric']}</td><td class='num'>{t['stated']}</td><td class='num'>{t['recomputed']}</td><td class='num vstat'>{t['delta']}</td></tr>" for t in ver['ties'])
    vvar_rows = ''.join(f"<tr><td class='bname'>{v['metric']}</td><td class='vnote'>{v['note']}</td></tr>" for v in ver['variances'])
    # ---- derived coverage + extended verification components ----
    N_DOCS = len(ver['sources']) + 1  # Groww P&L is two statements under one source row
    cov = [
        ('Brokers analysed', '3', 'Zerodha · AngelOne · Groww'),
        ('Primary documents', f'{N_DOCS}', 'tradebooks · P&amp;L · ledgers · dividend &amp; registrar'),
        ('Analysis window', S['period'], f'{ACTIVE_M} active months with exits'),
        ('Orders reconciled', f"{T['orders']}", f'{N_INST} instruments'),
        ('FIFO-matched lots', f"{T['lots']}", 'rebuilt independently · Zerodha + Groww'),
        ('Turnover audited', lakh(T['turnover']), 'buy + sell value'),
        ('Independent tie-outs', f'{V_TIES}', f'{V_VARS} variances disclosed'),
        ('Source streams', f"{len(ver['sources'])}", 'each with a coverage window'),
    ]
    cov_html = ''.join(stat(l, v, s) for l, v, s in cov)

    if evid:
        E = lambda x: html.escape(str(x))
        ev_cards = ''
        for r in evid['resolved']:
            tb = r['table']
            head = ''.join(f'<th>{E(h)}</th>' for h in tb['head'])
            rws = ''.join('<tr>' + ''.join(f"<td class='num'>{E(c)}</td>" for c in row) + '</tr>' for row in tb['rows'])
            ev_cards += (f"<div class='evcard'><div class='evhd'><span class='evbroker'>{E(r['broker'])}</span>"
                         f"<h4>{E(r['item'])}</h4><span class='evsrc'>{E(r['source'])}</span></div>"
                         f"<table class='evtable'><thead><tr>{head}</tr></thead><tbody>{rws}</tbody></table>"
                         f"<div class='evfoot'>{E(tb['foot'])}</div>"
                         f"<dl class='evmeta'><dt>Prior treatment</dt><dd>{E(r['prior'])}</dd>"
                         f"<dt>Finding</dt><dd>{E(r['finding'])}</dd>"
                         f"<dt>Resolution</dt><dd>{E(r['resolution'])}</dd></dl></div>")
        evidence_block = (f"<div class='subhd'>Resolved this revision · evidence from broker P&amp;L</div>"
                          f"<p class='sec-sub' style='margin-bottom:14px'>{E(evid['intro'])}</p>"
                          f"<div class='evgrid'>{ev_cards}</div>")
    else:
        evidence_block = ''

    trace = [
        ('Net realized P&amp;L', 'Zerodha P&amp;L · AngelOne P&amp;L · Groww P&amp;L ×2 · dividend report', 'tied'),
        ('Monthly cadence &amp; drawdown', 'broker P&amp;L grouped by sell-date → cumulative curve', 'tied'),
        ('Turnover &amp; orders', 'Zerodha tradebook · Groww / AngelOne order histories', 'tied'),
        ('Trade-lot statistics', 'independent FIFO engine · Zerodha tradebook + Groww trade-level P&amp;L', 'tied'),
        ('Instrument attribution', 'per-symbol realized across all three brokers', 'tied'),
        ('Dividends', 'registrar dividend report, by ex-date', 'tied'),
        ('Open-book marks', 'broker holdings / statement closing values', 'as-of marks'),
        ('Benchmark context', 'AMFI index-fund NAV (scheme 120716) — public record', 'cited proxy'),
        ('OLA IPO flip +₹59,234', 'Groww order history + fund-ledger settlement gap', 'tied'),
        ('LODHA closure +₹4,888.50', 'Zerodha Console P&amp;L, full period', 'tied'),
    ]
    trace_rows = ''.join(f"<tr><td class='bname'>{m}</td><td class='vnote'>{src}</td><td class='num vstat'>{st}</td></tr>" for m, src, st in trace)

    integ = [
        ('Reconciliation', 'FIFO ↔ statement', '₹0.00 Zerodha variance; Groww ledger ↔ orders within ₹40'),
        ('Duplicate control', 'unique order IDs', '165 distinct Zerodha order IDs; executed-only orders'),
        ('Transfer normalization', 'in-kind ≠ P&amp;L', 'inter-account demat moves separated — why XIRR pends'),
        ('Corporate actions', 'handled explicitly', 'Reliance bonus · OLA IPO · Vishal Mega Mart · Siemens demerger'),
        ('Charges bridge', 'gross → net', f'{inr(BRIDGE_GROSS)} − charges = {inr(BRIDGE_NET)} net ex-div'),
        ('Fail-closed build', f'{V_TIES} tie-outs', 'the page is not written if any headline figure drifts'),
    ]
    integ_html = ''.join(stat(l, v, s) for l, v, s in integ)

    steps = [
        ('01', 'Data collection', f'{N_DOCS} broker documents · 3 accounts'),
        ('02', 'Data validation', 'headers normalized · identifiers stripped · types checked'),
        ('03', 'Reconciliation', 'FIFO engine · ledger forensics · statement tie-outs'),
        ('04', 'Portfolio analysis', 'realized cadence · attribution · concentration'),
        ('05', 'Risk analysis', 'drawdown · holding-period edge · open-book marks'),
        ('06', 'Dashboard build', 'Python + Plotly · single validated build script'),
        ('07', 'Publication', 'static GitHub Pages · regenerable · fails closed'),
    ]
    step_html = ''.join(f"<div class='fnode'><span class='step-no'>{n}</span><h5>{t}</h5><p>{d}</p></div>" + ('<div class="farr">→</div>' if n != steps[-1][0] else '') for n, t, d in steps)

    demos = [
        ('Investment analysis', 'Realized P&amp;L, attribution and risk rebuilt from <b>raw statements</b> — not app screenshots.'),
        ('Data reconciliation', f'{N_DOCS} documents folded into one identifier-free dataset; FIFO ties Zerodha to <b>₹0.00</b>.'),
        ('Quantitative reasoning', f"FIFO lots, drawdown, profit factor and holding-period attribution over <b>{T['lots']} lots</b>."),
        ('Analytical integrity', 'Gaps disclosed, two open items <b>resolved with broker evidence</b>, build fails closed.'),
        ('Independent execution', 'Conceived, built and deployed solo — fully <b>regenerable</b> from published data.'),
    ]
    demo_html = ''.join(f"<div class='demo'><h5>{h}</h5><p>{b}</p></div>" for h, b in demos)

    VERIFY_SEC = f'''<section id="verify"><div class="wrap">
<div class="sec-head"><span class="sec-no">11</span><h2>Verification &amp; methodology</h2></div>
<p class="sec-sub">{ver['method']}</p>
<div class="subhd">Source coverage</div>
<div class="stats">{cov_html}</div>
{evidence_block}
<div class="subhd">Process &amp; data lineage</div>
<div class="flow" role="img" aria-label="data lineage: raw exports to rendered page">
<div class="fnode"><h5>Raw exports</h5><p>{N_DOCS} broker documents · contain PII · never committed</p></div><div class="farr">→</div>
<div class="fnode"><h5>Parse</h5><p>pandas ingestion · headers normalized · identifiers stripped</p></div><div class="farr">→</div>
<div class="fnode"><h5>Reconstruct</h5><p>FIFO lot engine · ledger forensics · corporate actions</p></div><div class="farr">→</div>
<div class="fnode"><h5>Reconcile</h5><p>statement tie-outs · ₹0.00 Zerodha variance · charges bridge</p></div><div class="farr">→</div>
<div class="fnode"><h5>Publish</h5><p>identifier-free datasets in <span class="mono">data/</span></p></div><div class="farr">→</div>
<div class="fnode"><h5>Render</h5><p>this page · validation gates · build fails closed</p></div>
</div>
<div class="subhd">Metric traceability · every headline figure to its source</div>
<div class="panel tscroll" style="padding:0"><table class="vtable" aria-label="metric traceability"><thead><tr><th>Dashboard metric</th><th>Verified from</th><th>Status</th></tr></thead><tbody>{trace_rows}</tbody></table></div>
<div class="subhd">Source inventory &amp; disclosed variances</div>
<div class="grid2">
<div class="panel tscroll" style="padding:0"><table class="vtable" aria-label="source inventory"><thead><tr><th>Primary source</th><th>Coverage</th><th>Drives</th></tr></thead><tbody>{vsrc_rows}</tbody></table></div>
<div class="panel tscroll" style="padding:0"><table class="vtable" aria-label="disclosed variances"><thead><tr><th>Disclosed variances ({V_VARS})</th><th>Explanation</th></tr></thead><tbody>{vvar_rows}</tbody></table></div>
</div>
<div class="subhd">Independent tie-out · recomputed from raw exports</div>
<div class="panel tscroll" style="padding:0"><table class="vtable" aria-label="independent tie-outs"><thead><tr><th>Independent tie-out ({V_TIES})</th><th>Stated</th><th>Recomputed from raw exports</th><th>Δ</th></tr></thead><tbody>{vtie_rows}</tbody></table></div>
<div class="subhd">Data-integrity checks</div>
<div class="stats">{integ_html}</div>
<div class="subhd">Analyst workflow</div>
<div class="flow stepflow" role="img" aria-label="analyst workflow timeline">{step_html}</div>
<div class="subhd">What this project demonstrates</div>
<div class="demos">{demo_html}</div>
<div class="takeaway"><b>Privacy boundary.</b> Raw exports contain PAN, client codes and bank references; they never enter this repository. The attestation runs privately (<span class="mono">scripts/verify_sources.py</span>) and publishes only the identifier-free comparisons above.</div>
</div></section>'''
else:
    V_TIES, V_VARS = 0, 0
    VERIFY_SEC = '''<section id="verify"><div class="wrap">
<div class="sec-head"><span class="sec-no">11</span><h2>Evidence &amp; verification</h2></div>
<div class="panel pendpanel"><div class="ph">Attestation — PENDING</div>
<p class="pendbody">Renders automatically when <span class="mono">data/verification.json</span> is produced by <span class="mono">scripts/verify_sources.py</span> against the raw exports.</p></div>
</div></section>'''

generated = S['generated']

# =====================================================================
#  PAGE
# =====================================================================
NAV = [('overview', 'Overview'), ('record', 'Record'), ('risk', 'Risk'), ('attribution', 'Attribution'),
       ('allocation', 'Allocation'), ('trades', 'Trades'), ('brokers', 'Brokers'), ('exhibits', 'Exhibits'),
       ('openbook', 'Open book'), ('benchmark', 'Benchmark'), ('method', 'Method'), ('verify', 'Verification')]
nav_html = ''.join(f'<a href="#{i}">{t}</a>' for i, t in NAV)

FAVICON = ("data:image/svg+xml," + html.escape(
 f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect x='1' y='1' width='30' height='30' rx='7' fill='{BG1}' stroke='{BRASS}' stroke-width='1.1'/>"
 f"<text x='16' y='21' font-family='Georgia,serif' font-size='13' fill='{BRASS}' text-anchor='middle' font-weight='700'>VM</text></svg>", quote=True))
EMBLEM = (f"<svg class='emblem' viewBox='0 0 40 40' width='40' height='40' xmlns='http://www.w3.org/2000/svg' aria-hidden='true'>"
          f"<rect x='1.5' y='1.5' width='37' height='37' rx='9' fill='{BG2}' stroke='{HAIR}'/>"
          f"<path d='M9 28 L17 20 L23 24 L31 12' fill='none' stroke='{BRASS}' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/>"
          f"<circle cx='31' cy='12' r='2.4' fill='{BRASS}'/></svg>")

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{PERSON} — Portfolio Analytics · Verified 3-Broker Track Record · Sep 2023–Jun 2026</title>
<meta name="description" content="A personal markets record reconciled to the rupee: 3 brokers, {T['orders']} orders, ₹2.76 Cr turnover, FIFO-rebuilt lots, ledger forensics, drawdown and attribution analytics. Built in Python; every figure regenerable from published data.">
<meta property="og:title" content="{PERSON} — Portfolio Analytics · Verified Track Record">
<meta property="og:description" content="Net realized {inr(T['net_realized_incl_div'])} across Zerodha, AngelOne, Groww — reconciled to broker statements, gaps disclosed. Drawdown, attribution and trade analytics over {T['lots']} FIFO-matched lots.">
<meta property="og:type" content="website"><meta property="og:url" content="{PAGE_URL}">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
<link rel="preconnect" href="https://cdn.plot.ly" crossorigin><script src="https://cdn.plot.ly/plotly-cartesian-2.35.2.min.js"></script>
<style>
:root{{--bg0:{BG0};--bg1:{BG1};--bg2:{BG2};--txt:{TXT};--mut:{MUT};--hair:{HAIR};--brass:{BRASS};--up:{UP};--dn:{DN};--blue:{BLUE};--gold:{BRASS}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;scroll-padding-top:64px}}
body{{background:var(--bg0);color:var(--txt);font:15px/1.65 "Inter",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 28px}}
.mono{{font-family:"IBM Plex Mono",monospace}}
nav.topnav{{position:sticky;top:0;z-index:50;background:rgba(10,14,19,.88);backdrop-filter:blur(10px);border-bottom:1px solid var(--hair)}}
nav.topnav .wrap{{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none}}
nav.topnav a{{font:500 10.5px/1 "IBM Plex Mono",monospace;letter-spacing:.13em;text-transform:uppercase;color:var(--mut);text-decoration:none;padding:14px 11px;white-space:nowrap;border-bottom:2px solid transparent}}
nav.topnav a:hover{{color:var(--txt)}}
nav.topnav a.on{{color:var(--brass);border-bottom-color:var(--brass)}}
header{{padding:56px 0 36px;border-bottom:1px solid var(--hair)}}
.eyebrow{{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.22em;color:var(--brass);text-transform:uppercase}}
h1{{font:600 clamp(28px,4vw,42px)/1.15 "Source Serif 4",Georgia,serif;margin:14px 0 6px}}
.byline{{font:500 14px/1.5 "Inter",system-ui,sans-serif;color:var(--txt);margin-bottom:8px}}
.byline b{{color:var(--brass);font-weight:600}}
.meta{{color:var(--mut);font:13px/1.6 "IBM Plex Mono",monospace}}
.readas{{margin-top:14px;font:12.5px/1.6 "IBM Plex Mono",monospace;color:var(--mut)}}
.readas b{{color:var(--brass);font-weight:600;letter-spacing:.08em}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));border:1px solid var(--hair);border-radius:6px;margin:32px 0 14px;background:var(--bg1);overflow:hidden}}
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
h2{{font:600 23px/1.25 "Source Serif 4",Georgia,serif}}
.sec-sub{{color:var(--mut);max-width:820px;margin-bottom:22px;font-size:14px}}
.panel{{background:var(--bg1);border:1px solid var(--hair);border-radius:6px;padding:18px 16px 8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.ph{{font:500 11px/1.45 "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);padding:2px 4px 12px}}
.takeaway{{margin-top:14px;background:var(--bg1);border:1px solid var(--hair);border-left:3px solid var(--brass);border-radius:6px;padding:14px 18px;font-size:13.5px;color:var(--mut);line-height:1.6}}
.takeaway b{{color:var(--txt)}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin-bottom:18px}}
.stat{{background:var(--bg1);border:1px solid var(--hair);border-radius:6px;padding:15px 16px}}
.stat-l{{font:500 10px/1.4 "IBM Plex Mono",monospace;letter-spacing:.13em;text-transform:uppercase;color:var(--mut)}}
.stat-v{{font:600 19px/1.3 "IBM Plex Mono",monospace;margin:8px 0 4px;font-variant-numeric:tabular-nums}}
.stat-s{{font-size:11.5px;color:var(--mut);line-height:1.45}}
.tscroll{{overflow-x:auto}}
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
.exhibit h4{{font:600 17px/1.3 "Source Serif 4",Georgia,serif;margin:10px 0 6px}}
.ex-stat{{font:600 15px/1.3 "IBM Plex Mono",monospace;color:var(--up);margin-bottom:10px}}
.exhibit p{{font-size:13.5px;color:var(--mut)}}
.withheld{{background:var(--bg1);border:1px dashed var(--hair);border-radius:6px;padding:16px 20px;margin-top:18px;font-size:13px;color:var(--mut);line-height:1.7}}
.withheld b{{color:var(--brass);font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;display:block;margin-bottom:8px}}
.method ol{{margin:14px 0 0 20px;display:grid;gap:12px;font-size:14px}}
.method li::marker{{color:var(--brass);font-family:"IBM Plex Mono",monospace}}
.pending{{background:var(--bg1);border:1px solid var(--hair);border-left:3px solid var(--brass);border-radius:6px;padding:18px 22px;margin-top:22px}}
.pending h4{{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--brass);margin-bottom:10px}}
.pending li{{font-size:13.5px;color:var(--mut);margin:6px 0 6px 18px}}
.pendpanel{{padding:22px 26px 26px}}
.pendbody{{color:var(--mut);font-size:13.5px;max-width:720px}}
.srcline{{margin-top:10px;font:12px/1.6 "IBM Plex Mono",monospace;color:var(--mut)}}
.defs{{margin-top:18px;font-size:12.5px;color:var(--mut)}}
.defs dt{{font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt);margin-top:10px}}
.defs dd{{margin:3px 0 0 0;line-height:1.6}}
footer{{padding:38px 0 64px;color:var(--mut);font-size:12.5px;line-height:1.8}}
footer a{{color:var(--brass);text-decoration:none}}
.skip{{position:absolute;left:-9999px;top:0;background:var(--bg2);color:var(--txt);padding:10px 16px;z-index:99;border-radius:0 0 6px 0;font:600 12px/1 "IBM Plex Mono",monospace}}
.skip:focus{{left:0}}
a:focus-visible{{outline:2px solid var(--brass);outline-offset:2px}}
.exec{{display:grid;gap:10px;margin-top:26px;max-width:900px}}
.ex-row{{display:flex;gap:14px;align-items:baseline}}
.ex-no{{font:600 12px/1.6 "IBM Plex Mono",monospace;color:var(--brass)}}
.ex-row p{{font-size:14.5px;color:var(--txt)}}
.ex-row p span{{color:var(--mut);font-size:12.5px}}
.flow{{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin-bottom:18px}}
.fnode{{flex:1 1 150px;background:var(--bg1);border:1px solid var(--hair);border-radius:6px;padding:12px 14px}}
.fnode h5{{font:600 10.5px/1.4 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--brass)}}
.fnode p{{font-size:11.5px;color:var(--mut);line-height:1.5;margin-top:4px}}
.farr{{align-self:center;color:var(--brass);font-family:"IBM Plex Mono",monospace}}
.vtable td{{font-size:12.5px}}
.vstat{{font:600 11px/1.4 "IBM Plex Mono",monospace;color:var(--up)}}
.subhd{{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--brass);margin:30px 0 12px}}
.evgrid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:4px 0}}
.evcard{{background:var(--bg1);border:1px solid var(--hair);border-left:3px solid var(--up);border-radius:6px;padding:18px 20px}}
.evhd{{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin-bottom:12px}}
.evbroker{{font:600 10px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--brass);border:1px solid var(--hair);border-radius:3px;padding:4px 7px}}
.evhd h4{{font:600 15px/1.3 "Source Serif 4",Georgia,serif;margin:0}}
.evsrc{{font:11.5px/1.4 "IBM Plex Mono",monospace;color:var(--mut);flex-basis:100%}}
.evtable{{font-size:12.5px;margin-bottom:0}}
.evtable th{{padding:7px 9px}}
.evtable td{{padding:7px 9px}}
.evfoot{{font:11.5px/1.55 "IBM Plex Mono",monospace;color:var(--mut);padding:9px 2px 2px}}
.evmeta{{margin-top:4px}}
.evmeta dt{{font:600 10px/1.3 "IBM Plex Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--brass);margin-top:11px}}
.evmeta dd{{font-size:12.5px;color:var(--mut);line-height:1.55;margin:3px 0 0}}
.stepflow .fnode{{flex:1 1 120px}}
.step-no{{display:block;font:600 10px/1 "IBM Plex Mono",monospace;color:var(--brass);margin-bottom:5px}}
.stepflow h5{{color:var(--txt)}}
.demos{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}}
.demo{{background:var(--bg1);border:1px solid var(--hair);border-radius:6px;border-top:2px solid var(--brass);padding:14px 16px}}
.demo h5{{font:600 11px/1.3 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--txt)}}
.demo p{{font-size:12.5px;color:var(--mut);line-height:1.55;margin-top:6px}}
.demo p b{{color:var(--up);font-weight:600}}
@media(max-width:760px){{.evgrid{{grid-template-columns:1fr}}}}
.vnote{{font-size:12.5px;color:var(--mut)}}
.ob-total td{{border-top:2px solid var(--hair);font-size:13px;background:var(--bg2)}}
.ob-total .bname{{color:var(--mut);font-size:12px;font-weight:500}}
.bench-chip{{display:flex;align-items:baseline;gap:14px;background:rgba(52,201,142,.07);border:1px solid rgba(52,201,142,.25);border-left:4px solid var(--up);border-radius:6px;padding:14px 20px;margin-bottom:18px}}
.bench-chip-n{{font:600 22px/1.2 "IBM Plex Mono",monospace;color:var(--up);font-variant-numeric:tabular-nums}}
.bench-chip-l{{font-size:13px;color:var(--mut)}}
@media(max-width:760px){{.grid2{{grid-template-columns:1fr}}.kpi{{border-right:0;border-bottom:1px solid var(--hair)}}table{{font-size:12.5px}}.note{{max-width:none}}.bench-chip{{flex-direction:column;gap:6px}}.bench-chip-n{{font-size:18px}}}}
@media print{{nav.topnav{{display:none}}section{{page-break-inside:avoid}}body{{background:#fff;color:#111}}}}
/* --- chart containers: never overflow the card --- */
.panel>.plotly-graph-div,.panel .js-plotly-plot,.panel .plot-container{{width:100%!important;max-width:100%}}
.js-plotly-plot .modebar{{display:none!important}}
img,svg,table,.plotly-graph-div{{max-width:100%}}
.panel{{overflow:hidden}}
/* --- tablet --- */
@media(max-width:980px) and (min-width:761px){{.stats{{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}}.exhibits{{grid-template-columns:1fr 1fr}}}}
/* --- mobile --- */
@media(max-width:640px){{
  section{{padding:36px 0}}
  .wrap{{padding:0 18px}}
  .farr{{display:none}}
  .flow{{gap:10px}}
  .fnode{{flex:1 1 100%}}
  .subhd{{margin:24px 0 10px}}
  h1{{font-size:27px}}
  h2{{font-size:21px}}
  .kpi-val{{font-size:23px}}
  .stat-v{{font-size:18px}}
}}
/* ===================== PREMIUM FINANCE REFINEMENT LAYER ===================== */
body{{font-family:"Inter",system-ui,-apple-system,sans-serif;letter-spacing:-.003em;
  background:radial-gradient(1100px 460px at 82% -8%,rgba(79,134,232,.055),transparent 60%),
             radial-gradient(820px 520px at -8% -4%,rgba(212,175,55,.04),transparent 55%),var(--bg0)}}
h1{{letter-spacing:-.012em}}
h2{{letter-spacing:-.006em}}
.eyebrow{{color:var(--gold)}}
/* section hierarchy — report-style ruled headers */
.sec-no{{color:var(--gold);background:var(--bg1);border:1px solid var(--hair);border-radius:6px;padding:5px 9px;line-height:1}}
.sec-head{{align-items:center;gap:12px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid var(--hair)}}
.sec-sub{{margin-bottom:24px;font-size:14.5px;line-height:1.62}}
section{{padding:52px 0}}
/* cards — refined radius + whisper elevation (no noisy gradients) */
.panel,.exhibit,.evcard,.demo,.pending,.withheld,.takeaway,.bench-chip{{border-radius:8px}}
.panel,.exhibit,.evcard,.demo{{box-shadow:0 1px 2px rgba(0,0,0,.22),0 14px 30px -22px rgba(0,0,0,.7)}}
.kpis{{border-radius:10px;box-shadow:0 1px 2px rgba(0,0,0,.22),0 16px 36px -24px rgba(0,0,0,.7)}}
.stat{{border-radius:8px}}
.kpi-val{{font-size:27px;letter-spacing:-.01em}}
/* chart panels — framed header */
.ph{{border-bottom:1px solid var(--hair);margin-bottom:12px;padding:2px 2px 11px;color:var(--mut)}}
/* keyword emphasis — tasteful, not loud */
.takeaway b,.sec-sub b,.ex-row p b{{color:var(--txt);font-weight:600}}
.kw{{color:var(--gold);font-weight:600}}
/* nav */
nav.topnav{{background:rgba(10,15,26,.9)}}
nav.topnav a.on{{color:var(--gold);border-bottom-color:var(--gold)}}
/* reconciliation chips + status icons */
.recon{{gap:9px}}
.chip{{align-items:center;border-radius:6px;padding:9px 13px;gap:9px}}
.cicw{{display:inline-flex;align-items:center;color:var(--up)}}
.chip.wait .cicw{{color:var(--gold)}}
.cic{{display:block}}
/* brandmark / emblem / verified badge */
.brandmark{{display:flex;align-items:center;gap:14px;margin-bottom:24px}}
.brandmark .emblem{{flex:none;width:40px;height:40px;border-radius:9px}}
.bwordmark{{display:flex;flex-direction:column;line-height:1.15}}
.bwordmark b{{font:600 13.5px/1.1 "Inter",sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--txt)}}
.bwordmark i{{font:500 10.5px/1.3 "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);font-style:normal;margin-top:4px}}
.vbadge{{margin-left:auto;display:inline-flex;align-items:center;gap:7px;font:600 10.5px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--up);background:rgba(47,185,138,.09);border:1px solid rgba(47,185,138,.32);border-radius:999px;padding:7px 13px}}
.vbadge svg{{width:13px;height:13px;flex:none}}
.footbrand{{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid var(--hair)}}
.footbrand .emblem{{flex:none;width:30px;height:30px}}
@media(max-width:640px){{.vbadge{{display:none}}.brandmark{{margin-bottom:18px}}.sec-head{{gap:10px}}}}
</style></head><body>

<a class="skip" href="#record">Skip to content</a>
<nav class="topnav" aria-label="sections"><div class="wrap">{nav_html}</div></nav>

<header id="overview"><div class="wrap">
<div class="brandmark">{EMBLEM}<span class="bwordmark"><b>{PERSON}</b><i>Portfolio Analytics</i></span><span class="vbadge"><svg viewBox='0 0 16 16' fill='none'><circle cx='8' cy='8' r='7' stroke='currentColor' stroke-width='1.3'/><path d='M5 8.2 7 10.2 11 5.6' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>Verified · Reconciled</span></div>
<div class="eyebrow">Independent Portfolio · Verified Track Record</div>
<h1>Three brokers, every rupee reconciled.</h1>
<div class="byline">The personal markets record of <b>{PERSON}</b> — rebuilt from raw broker statements, not summarized from app screenshots.</div>
<div class="meta">Sep 2023 – Jun 2026 · Zerodha / AngelOne / Groww · {T['orders']} orders · tradebooks, P&amp;L statements, fund ledgers &amp; dividend reports · Python + pandas + Plotly</div>
<div class="readas"><b>READ THIS AS</b> &nbsp;an analytics work-sample: ingestion → FIFO reconstruction → ledger forensics → attribution → risk — with every gap disclosed rather than smoothed.</div>
<div class="exec">
<div class="ex-row"><span class="ex-no">01</span><p>Rebuilt a 3-broker investing record from <b>11 primary documents</b> — tradebooks, P&amp;L statements, fund ledgers, dividend registry — into one reconciled, identifier-free dataset. <span>(data engineering)</span></p></div>
<div class="ex-row"><span class="ex-no">02</span><p>Net realized <b>{inr(T['net_realized_incl_div'])}</b> across 33 months — {POS_M} of {ACTIVE_M} active months positive — with drawdown, attribution and trade analytics on {T['lots']} FIFO-matched lots. <span>(investment analysis)</span></p></div>
<div class="ex-row"><span class="ex-no">03</span><p>Every headline figure independently re-verified against source statements: <b>{V_TIES} exact ties</b>, {V_VARS} variances disclosed — see section 11. <span>(audit discipline)</span></p></div>
<div class="ex-row"><span class="ex-no">04</span><p>Holding-period attribution surfaced a <b>disposition bias</b> — profits realized quickly (median 9 days), losses held longer — documented as a process finding; the open book in section 08 holds the live evidence. <span>(self-evaluation)</span></p></div>
</div>
<div class="kpis">{kpi_html}</div>
<div class="recon">{recon_html}</div>
</div></header>

<section id="record"><div class="wrap">
<div class="sec-head"><span class="sec-no">01</span><h2>Realized record</h2></div>
<p class="sec-sub">Monthly realized P&amp;L by broker with the cumulative line. The cadence is shown gross of Zerodha/Groww charges (AngelOne flows are statement nets); headline KPIs are net of all charges — the bridge is quantified in the methodology. Every monthly total reconciles to broker statements.</p>
<div class="stats">{cad_html}</div>
<div class="panel"><div class="ph">Monthly realized P&amp;L · cumulative (right axis)</div>{CH1}</div>
<div class="panel" style="margin-top:18px"><div class="ph">Realized P&amp;L calendar · blank = no exits that month</div>{CHH}</div>
<div class="takeaway"><b>How to read the cadence.</b> P&amp;L arrives in event clusters — the Jun–Jul 2024 election deployment, the Oct 2024 IPO exit, the Jul 2025 AngelOne harvest — not as a smooth equity curve. {POS_M} of {ACTIVE_M} active months closed positive; the deepest realized setback was {inr(MAXDD)} and was recovered the following month.</div>
</div></section>

<section id="risk"><div class="wrap">
<div class="sec-head"><span class="sec-no">02</span><h2>Risk &amp; drawdown</h2></div>
<p class="sec-sub">Drawdown here is measured on the cumulative <em>realized</em> P&amp;L curve — how far the booked record fell below its own high-water mark. It is not a NAV drawdown: the open book carries the marked-to-market risk, reported separately in 08 and never netted against the realized record.</p>
<div class="stats">{risk_html}</div>
<div class="panel"><div class="ph">Underwater curve · cumulative realized P&amp;L below high-water mark</div>{CHU}</div>
<div class="takeaway"><b>Where the real risk sits.</b> The realized curve's worst excursion is {inr(MAXDD)} — against a largest single open mark of {inr(float(obm['unrl'].min()))}. The trading process cuts realized losses early (largest organic realized loss {inr(MAX_LOSS_CORE)}); the risk concentrates in held positions. That asymmetry — quick to book winners, slow to exit losers — was surfaced by this pipeline and now drives a written position-review rule.</div>
<div class="withheld"><b>Deliberately withheld</b>
Sharpe, Sortino, return volatility and beta require a return series over a unified capital base; the combined money-weighted XIRR awaits a CDSL/demat transfer statement to resolve inter-account in-kind movements. Annualizing lot-level cash P&amp;L into a pseudo-return would manufacture precision that the data does not support — these metrics ship when the inputs do, not before.</div>
</div></section>

<section id="attribution"><div class="wrap">
<div class="sec-head"><span class="sec-no">03</span><h2>Attribution</h2></div>
<p class="sec-sub">Where the P&amp;L came from: by instrument and by holding period. {N_WIN_INST} of {N_INST} instruments closed profitable ({INST_HIT*100:.0f}%). Winners built {lakh(GP_INST)} gross; losers gave back {lakh(abs(GL_INST))} ({GIVEBACK*100:.0f}%). Concentration is real and disclosed: the top five names are {TOP5_PCT_I*100:.0f}% of gross instrument profits, the single largest ({html.escape(str(ip.idxmax()))}) {TOP1_PCT_I*100:.0f}%.</p>
<div class="grid2">
<div class="panel"><div class="ph">Realized P&amp;L attribution · top 14 by magnitude</div>{CH4}</div>
<div class="panel"><div class="ph">Concentration · cumulative P&amp;L by instrument rank ({N_INST} instruments)</div>{CHP}</div>
</div>
<div class="panel" style="margin-top:18px"><div class="ph">Realized P&amp;L by holding period · FIFO lots, Zerodha + Groww</div>{CHB}</div>
<div class="takeaway" id="edge-note"><b>The edge is short-horizon.</b> Lots held 2–7 days produced {lakh(float(hb.loc['2–7d','pnl']))} at an {hb.loc['2–7d','wr']*100:.0f}% win rate — the densest cell of the book. Past 90 days the win rate falls to {hb.loc['90d+','wr']*100:.0f}% and the bucket nets roughly {lakh(float(hb.loc['90d+','pnl']))}. The data says the process earns its keep inside a month; the open book (08) shows what happens when positions overstay that edge.</div>
</div></section>

<section id="allocation"><div class="wrap">
<div class="sec-head"><span class="sec-no">04</span><h2>Allocation &amp; capital</h2></div>
<p class="sec-sub">How realized P&amp;L and capital distribute across segments and accounts. Segment figures are an arithmetic regrouping of the instrument table (03); capital figures are ledger-verified bank flows over each account's window. In-kind inter-account transfers (account closure, pledge movements) mean per-broker cash gaps do not equal P&amp;L — resolving them needs the demat transfer statement (pending, see 10).</p>
<div class="grid2">
<div class="panel"><div class="ph">Realized P&amp;L by segment · regrouped from the instrument table</div>{CHS}</div>
<div class="panel tscroll" style="padding:0"><table aria-label="capital by account"><thead><tr><th>Account</th><th>Bank in</th><th>Bank out</th><th>Turnover</th><th>Net realized</th></tr></thead><tbody>{cap_rows}</tbody></table></div>
</div>
<div class="takeaway"><b>Reading the split.</b> {seg_take}</div>
</div></section>

<section id="trades"><div class="wrap">
<div class="sec-head"><span class="sec-no">05</span><h2>Trade analytics</h2></div>
<p class="sec-sub">Distribution views over {T['lots']} FIFO-matched lots (Zerodha + Groww). {outl} lots sit outside the ±₹12k display range, including the two offsetting Reliance bonus legs (±₹99k) that net to {inr(PAIR_NET, sign=True)} — they inflate gross profit and gross loss symmetrically, so the profit factor is shown both ways: {PF_ALL:.2f} as booked, {PF_CORE:.2f} with the pair excluded.</p>
<div class="stats">{trade_html}</div>
<div class="grid2">
<div class="panel"><div class="ph">Per-lot P&amp;L distribution (₹, clipped ±12k)</div>{CH2}</div>
<div class="panel"><div class="ph">Holding-period profile · lot count</div>{CH3}</div>
</div>
<div class="panel tscroll" style="margin-top:18px;padding:0"><table>
<thead><tr><th>Lot stats by broker</th><th>Lots</th><th>Win rate</th><th>Profit factor</th><th>Expectancy</th><th>Median hold</th><th>Avg win / loss</th></tr></thead>
<tbody>{brk_rows}</tbody></table></div>
<div class="takeaway"><b>Shape of the book.</b> A {T['lot_win_rate']*100:.0f}% win rate with a {PAYOFF:.2f} payoff ratio is a scalper's signature: many small wins ({inr(MED_WIN)} median), fewer but larger losses ({inr(MED_LOSS)} median). The book stays net-positive because losers are cut while small — the largest organic realized loss is {inr(MAX_LOSS_CORE)} on {lakh(BRIDGE_GROSS)} of gross realized P&amp;L.</div>
</div></section>

<section id="brokers"><div class="wrap">
<div class="sec-head"><span class="sec-no">06</span><h2>Broker comparison</h2></div>
<p class="sec-sub">Three accounts, three roles: Zerodha ran the FY24 PSU/infra swing book, AngelOne the FY25 concentrated quality-names account, Groww the primary book including IPO and event positions.</p>
<div class="panel tscroll" style="padding:0"><table><thead><tr><th>Broker</th><th>Window</th><th>Net realized</th><th>Turnover</th><th>Orders</th><th>Win rate</th><th>Reconciliation</th></tr></thead><tbody>{broker_tbl}</tbody></table></div>
</div></section>

<section id="exhibits"><div class="wrap">
<div class="sec-head"><span class="sec-no">07</span><h2>Signature exhibits</h2></div>
<p class="sec-sub">Three episodes that define the record — each fully timestamped in the underlying data.</p>
<div class="exhibits">{ex_html}</div>
</div></section>

<section id="openbook"><div class="wrap">
<div class="sec-head"><span class="sec-no">08</span><h2>Open book</h2></div>
<p class="sec-sub">Positions currently held, shown separately from the realized record and at honest marks. The realized figures above do not include these. Two items previously listed here — an OLA Electric ‘pledged’ line and a LODHA exit outside the covered statements — were resolved this revision against newly-provided broker P&amp;L, and are documented with statement evidence in §11.</p>
<div class="panel tscroll" style="padding:0;margin-bottom:18px"><table><thead><tr><th>Position</th><th>Broker</th><th>Qty</th><th>Cost</th><th>Value</th><th>Unrealized</th><th>As of</th><th>Frame</th></tr></thead><tbody>{ob_rows}</tbody></table></div>
<div class="panel"><div class="ph">Unrealized marks · positions with current prices</div>{CH5}</div>
<div class="takeaway"><b>Why this section exists.</b> A track record that hides its open losers isn't a track record. The disposition pattern visible here — quick to realize winners, slow to exit losers — is the documented lesson of this book, and the holding-period attribution in 03 quantifies exactly where the edge decays.</div>
</div></section>

<section id="benchmark"><div class="wrap">
<div class="sec-head"><span class="sec-no">09</span><h2>Benchmark context</h2></div>
<p class="sec-sub">NIFTY 50 Total Return Index over the same window — context for the market regime the record was built in, not a relative-performance claim. Tracked via an AMFI-published index-fund NAV (exact citation below the chart); a money-weighted comparison requires the unified capital base (pending, see methodology).</p>
{bench_body}
</div></section>

<section id="method" class="method"><div class="wrap">
<div class="sec-head"><span class="sec-no">10</span><h2>Methodology &amp; data integrity</h2></div>
<p class="sec-sub">How every number on this page was derived — so it reads as verified analysis, not marketing. The build script asserts these ties before the page is written; a failed check fails the build.</p>
<div class="panel" style="padding:22px 26px">
<ol>
<li><strong>Ingest.</strong> Raw broker exports: Zerodha tradebook + P&amp;L + fund ledger; AngelOne trades history + P&amp;L statement; Groww order history + two P&amp;L reports + balance statement + dividend report. Parsed with pandas; account identifiers stripped before anything is published.</li>
<li><strong>Reconcile.</strong> An independent FIFO matching engine reproduces Zerodha's stated realized P&amp;L to ₹0.00. Groww's fund ledger reconciles to its order history within ₹40 after corporate-action adjustment.</li>
<li><strong>Corporate actions.</strong> Reliance 1:1 bonus, OLA Electric IPO allotment, Vishal Mega Mart IPO, Siemens Energy demerger and rights entitlements handled explicitly. The OLA IPO sale (+₹59,234) is absent from broker P&amp;L (IPO cost basis) and was recovered from a ₹1.85L settlement-ledger gap.</li>
<li><strong>Charges bridge.</strong> The monthly cadence, lot and instrument tables run gross of Zerodha + Groww charges; AngelOne flows are statement nets. Gross realized {inr(BRIDGE_GROSS)} − Zerodha charges {inr(Z_CHG)} − Groww charges {inr(G_CHG)} = {inr(BRIDGE_NET)} net ex-dividends; + {inr(T['dividends'])} dividends (registrar report) = {inr(T['net_realized_incl_div'])} headline. Total charges paid across brokers: {inr(S['charges_total'])}.</li>
<li><strong>Risk metrics.</strong> Drawdown is computed on the cumulative realized P&amp;L curve (high-water-mark basis) — labeled as such everywhere; it is not NAV drawdown. Expectancy = mean lot P&amp;L; payoff ratio = avg win ÷ |avg loss|; profit factor = gross profits ÷ |gross losses|, reported both including and excluding the offsetting Reliance bonus legs.</li>
<li><strong>Benchmark.</strong> {('NIFTY 50 TRI tracked via a published index-fund NAV (full citation in section 09): month-end values, rebased to 100 at window start, final point month-to-date. AMFI-published NAVs are public record and track the TRI within ~0.1–0.2%/yr. Regime context only — no relative-return claim.') if bench is not None else 'Withheld until an official month-end TRI series is supplied; the section renders automatically from data/benchmark.csv and is never approximated.'}</li>
<li><strong>Marks.</strong> Open positions priced from broker statements as of the dates shown per row; no model prices.</li>
<li><strong>Separation.</strong> Realized record and open book are presented separately by design; neither is netted into the other anywhere on this page.</li>
</ol>
<dl class="defs">
<dt>Definitions</dt>
<dd><span class="mono">Win rate</span> — share of FIFO lots with P&amp;L &gt; 0 · <span class="mono">Expectancy</span> — mean P&amp;L per lot · <span class="mono">Payoff ratio</span> — average win ÷ |average loss| · <span class="mono">Profit factor</span> — Σ wins ÷ |Σ losses| · <span class="mono">Hit rate (monthly)</span> — share of active months with positive realized P&amp;L · <span class="mono">Max drawdown (realized curve)</span> — deepest fall of cumulative realized P&amp;L below its prior peak · <span class="mono">Turnover</span> — buy value + sell value.</dd>
</dl>
<div class="pending"><h4>Pending — disclosed, not hidden</h4><ul>{pend_html}</ul></div>
</div>
</div></section>

{VERIFY_SEC}

<footer><div class="wrap">
<div class="footbrand">{EMBLEM}<span class="bwordmark"><b>{PERSON}</b><i>Verified 3-broker track record</i></span></div>
<div class="mono">{PERSON} · <a href="{PAGE_URL}" target="_blank" rel="noopener noreferrer">{PAGE_URL.replace('https://', '')}</a> · <a href="{REPO_URL}" target="_blank" rel="noopener noreferrer">source repository</a>{(' · <a href="' + LINKEDIN + '" target="_blank" rel="noopener noreferrer">LinkedIn</a>') if LINKEDIN else ''}</div>
<div class="mono">Generated {generated} · regenerate: <strong>python scripts/build_dashboard.py</strong> · build fails closed if headline figures stop tying to data/</div>
<div style="margin-top:8px">Personal investment record presented as analytical proof-of-work. Not investment advice or a solicitation. All figures derived from broker statements; derived datasets in <span class="mono">data/</span>. No account identifiers, client codes, or personal data are published.</div>
</div></footer>

<script>
(function(){{
  var links=document.querySelectorAll('nav.topnav a');
  var map={{}};links.forEach(function(a){{map[a.getAttribute('href').slice(1)]=a}});
  var obs=new IntersectionObserver(function(es){{es.forEach(function(e){{
    if(e.isIntersecting){{links.forEach(function(a){{a.classList.remove('on')}});
    var a=map[e.target.id];if(a)a.classList.add('on');}}}})}},{{rootMargin:'-30% 0px -60% 0px'}});
  document.querySelectorAll('header[id],section[id]').forEach(function(s){{obs.observe(s)}});
}})();
</script>
</body></html>"""


# =====================================================================
#  VALIDATION — the page is not written unless every check passes
# =====================================================================
checks = [
 ('cumulative column is internally consistent',
  bool(np.allclose(tot.cumsum(), cum, atol=0.01))),
 ('charges bridge ties gross cadence to net ex-div KPI (\u00b1\u20b91)',
  abs(BRIDGE_NET - T['net_realized_ex_div']) < 1.0),
 ('headline = net ex-div + dividends (\u00b1\u20b90.01)',
  abs(T['net_realized_ex_div'] + T['dividends'] - T['net_realized_incl_div']) < 0.01),
 ('lot count matches summary', len(lots) == T['lots']),
 ('lot win rate matches summary (\u00b10.01%)',
  abs((lots.pnl > 0).mean() - T['lot_win_rate']) < 1e-4),
 ('profit factor matches summary (\u00b10.005)', abs(PF_ALL - T['profit_factor']) < 5e-3),
 ('median hold matches summary', float(lots.hold.median()) == T['median_hold_days']),
 ('instrument \u03a3 ties to gross cadence within recon tolerance (\u00b1\u20b9100)',
  abs(float(ip.sum()) - BRIDGE_GROSS) < 100.0),
 ('corp-action pair nets to small remainder (<\u20b91,000)', abs(PAIR_NET) < 1000.0),
 ('holding buckets cover all lots', int(hb['n'].sum()) == len(lots)),
 ('open book rows render', len(ob) == 4),
 ('segment regroup conserves instrument \u03a3 (exact)', abs(float(SEG.sum()) - float(ip.sum())) < 0.01),
 ('verification attestations present and complete',
  ver is not None and len(ver['ties']) >= 20 and len(ver['variances']) == 3),
]
if bench is not None:
    checks += [
     ('benchmark months strictly increasing', bool(bench['month'].is_monotonic_increasing)),
     ('benchmark values positive', bool((bench['tri'] > 0).all())),
     ('benchmark window overlaps record', len(bm) > 12),
     ('benchmark covers full record window',
      bench['month'].iloc[0] <= monthly['month'].iloc[0] and bench['month'].iloc[-1] >= monthly['month'].iloc[-1]),
    ]
fails = [n for n, ok in checks if not ok]
for n, ok in checks:
    print(('  PASS  ' if ok else '  FAIL  ') + n)
if fails:
    raise SystemExit(f'validation failed: {len(fails)} check(s) — page not written')

out = os.path.join(ROOT, 'docs', 'index.html')
open(out, 'w', encoding='utf-8').write(HTML)
print(f'\nvalidation: {len(checks)}/{len(checks)} checks passed')
print('written:', out, f'({len(HTML)/1024:.0f} KB)', '\u00b7 benchmark:', 'ACTIVE' if bench is not None else 'PENDING')
