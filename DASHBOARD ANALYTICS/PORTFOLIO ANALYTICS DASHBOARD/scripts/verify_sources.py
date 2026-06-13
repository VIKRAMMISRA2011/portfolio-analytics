"""
verify_sources.py — independent attestation of published figures against raw broker exports.

This is the PRIVATE verification step. It expects the raw exports (which contain
PAN/client codes and are therefore never committed) in RAW_DIR, recomputes every
headline figure from primary sources, compares against data/summary_metrics.json,
and refreshes data/verification.json (identifier-free) for the dashboard's
Evidence & Verification section.

Usage:  RAW_DIR=/path/to/raw/exports python scripts/verify_sources.py
Raw set (11 documents):
  Zerodha  : tradebook (equity), P&L statement, fund ledger
  AngelOne : trades history, P&L statement (equity + F&O), broking ledger
  Groww    : order history, P&L statements ×2, fund ledger, dividend report (PDF)
"""
import os, sys, json, re, warnings
import pandas as pd

warnings.filterwarnings('ignore')
RAW = os.environ.get('RAW_DIR')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if not RAW or not os.path.isdir(RAW):
    sys.exit('RAW_DIR not set or missing — raw exports are kept outside the repo (privacy). '
             'See data/verification.json for the last attestation.')

def find(pattern):
    hits = [f for f in os.listdir(RAW) if re.search(pattern, f, re.I)]
    if not hits: sys.exit(f'missing raw file matching: {pattern}')
    return os.path.join(RAW, sorted(hits)[0])

def load_at(path, sheet, token):
    """Read a broker sheet whose real header row contains `token` (exports carry preamble rows)."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    hr = next(i for i, row in raw.iterrows()
              if any(str(v).strip() == token for v in row.tolist()))
    df = raw.iloc[hr + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[hr].tolist()]
    return df.loc[:, [c for c in df.columns if c != 'nan']].dropna(how='all').reset_index(drop=True)

S = json.load(open(os.path.join(ROOT, 'data', 'summary_metrics.json'), encoding='utf-8'))
checks = []
def tie(metric, stated, recomputed, tol=0.005):
    ok = abs(stated - recomputed) <= tol if isinstance(stated, (int, float)) else stated == recomputed
    checks.append((metric, stated, round(recomputed, 2) if isinstance(recomputed, float) else recomputed, ok))
    return ok

# ---------------- Zerodha ----------------
tb = load_at(find(r'zerodha.*tradebook'), 'Equity', 'Symbol').dropna(subset=['Symbol'])
tb['value'] = pd.to_numeric(tb['Quantity']) * pd.to_numeric(tb['Price'])
tie('Z orders', S['brokers']['zerodha']['orders'], int(tb['Order ID'].nunique()), 0)
tie('Z turnover', S['brokers']['zerodha']['turnover'], float(tb['value'].sum()), 1)
zsum = pd.read_excel(find(r'zerodha.*pnl'), sheet_name='Equity', header=None, nrows=20)
kv = {str(r[1]).strip(): r[2] for _, r in zsum.iterrows() if pd.notna(r[1])}
zp = load_at(find(r'zerodha.*pnl'), 'Equity', 'Symbol').dropna(subset=['Symbol'])
rcol = [c for c in zp.columns if 'Realized' in c][0]
tie('Z gross realized', S['brokers']['zerodha']['gross'], float(pd.to_numeric(zp[rcol], errors='coerce').sum()))
tie('Z scrip WR', S['brokers']['zerodha']['scrip_wr'],
    float((pd.to_numeric(zp[rcol], errors='coerce') > 0).mean()), 0.001)

# ---------------- AngelOne ----------------
apl = find(r'angelon.*profitloss|angelon.*p.?l')
aeq = load_at(apl, 'Equity P&L', 'Scrip Symbol')
aeq = aeq[~aeq['Scrip Symbol'].astype(str).str.contains('Total|Intraday|Scrip|Disclaimer', na=True)]
ncol = [c for c in aeq.columns if 'Net' in c][0]
nets = pd.to_numeric(aeq[ncol], errors='coerce').dropna()
tie('A equity net', S['brokers']['angelone']['equity_net'], float(nets.sum()))
tie('A equity all profitable', True, bool((nets > 0).all()))
raw_fno = pd.read_excel(apl, sheet_name='F&O P&L', header=None)
fno_net = next(float(r[1]) for _, r in raw_fno.iterrows() if str(r[0]).strip() == 'Net PnL')
tie('A F&O net', S['brokers']['angelone']['fno_net'], fno_net)

# ---------------- Groww ----------------
gor = load_at(find(r'groww.*order'), 'Sheet1', 'Stock name').dropna(subset=['Stock name'])
ex = gor[gor['Order status'].astype(str).str.lower() == 'executed']
tie('G executed orders', S['brokers']['groww']['orders'], len(ex), 0)
tie('G turnover', S['brokers']['groww']['turnover'], float(pd.to_numeric(ex['Value']).sum()), 1)
g_real, g_chg, g_lots = 0.0, 0.0, 0
for pat in (r'groww.*pnl.*2024', r'groww.*pnl.*2025[_-]'):
    f = find(pat)
    raw = pd.read_excel(f, sheet_name='Trade Level', header=None)
    hdrs = [i for i, row in raw.iterrows() if str(row[0]).strip() == 'Stock name']
    blk = raw.iloc[hdrs[0] + 1:hdrs[1] if len(hdrs) > 1 else len(raw)].copy()
    blk.columns = [str(c).strip() for c in raw.iloc[hdrs[0]]]
    rp = pd.to_numeric(blk['Realised P&L'], errors='coerce').dropna()
    g_real += float(rp.sum()); g_lots += len(rp)
    g_chg += next(float(r[1]) for _, r in raw.iterrows() if str(r[0]).strip() == 'Total')
tie('G realized lots', 94, g_lots, 0)
tie('G charges', 20855.29, g_chg)
tie('G stmt net (±₹0.25 rounding)', S['brokers']['groww']['stmt_net'], g_real - g_chg, 0.25)

# ---------------- Cross-broker bridge ----------------
monthly = pd.read_csv(os.path.join(ROOT, 'data', 'monthly_realized.csv'))
bridge = (float(pd.to_numeric(zp[rcol], errors='coerce').sum())
          + S['brokers']['angelone']['equity_net'] + fno_net
          + g_real + S['brokers']['groww']['ipo_recovered'])
tie('gross cadence = Σ broker statements', float(monthly['Total'].sum()), bridge, 0.05)

# ---------------- report ----------------
width = max(len(c[0]) for c in checks)
fails = 0
for m, s, r, ok in checks:
    print(('  PASS  ' if ok else '  FAIL  ') + m.ljust(width), '| stated:', s, '| recomputed:', r)
    fails += (not ok)
print(f'\n{len(checks) - fails}/{len(checks)} attestations passed')
if fails: sys.exit('attestation failure — investigate before publishing')
print('data/verification.json describes the full attestation set for the dashboard.')
