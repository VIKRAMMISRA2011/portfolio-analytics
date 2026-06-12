"""Consolidates reconciled broker analysis into structured data files for the dashboard.
Sources: cleaned datasets derived from raw Zerodha/AngelOne/Groww exports (tradebooks,
P&L statements, fund ledgers, dividend report). Raw files excluded from repo for privacy."""
import pandas as pd, numpy as np, json, sys, os

WORK = os.environ.get('WORK_DIR', '/home/claude/portfolio')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

z_rt = pd.read_csv(f'{WORK}/zerodha_roundtrips.csv', parse_dates=['buy_date','sell_date'])
g_rt = pd.read_csv(f'{WORK}/groww_realized_clean.csv', parse_dates=['bd','sd'])
a_tr = pd.read_csv(f'{WORK}/angelone_trades_oct24_aug25.csv', parse_dates=['Date'])
a_eq = pd.read_csv(f'{WORK}/angelone_equity_pnl.csv')
a_fn = pd.read_csv(f'{WORK}/angelone_fno_pnl.csv')
g_open = pd.read_csv(f'{WORK}/groww_open_positions_current.csv')
zt = pd.read_csv(f'{WORK}/zerodha_trades_fy2324.csv')
g_or = pd.read_csv(f'{WORK}/groww_orders.csv')

Z_NET, Z_GROSS, Z_CHG = 40561.46, 46866.53, 6305.07
A_EQ_NET, A_FNO_NET = 110371.57, -8443.61
A_NET = A_EQ_NET + A_FNO_NET
G_STMT_NET, G_IPO = 95061.79, 59233.66
G_NET = G_STMT_NET + G_IPO
DIV = 12297.95
TOTAL_NET = Z_NET + A_NET + G_NET + DIV

z_turn = float(zt['value'].sum())
a_turn = float(a_eq['Buy Value'].sum()+a_eq['Sell Value'].sum()+a_fn['buy_val'].sum()+a_fn['sell_val'].sum())
g_turn = float(g_or['value'].sum())
orders = dict(zerodha=int(zt['order_id'].nunique()), angelone=53, groww=int(len(g_or)))

zm = z_rt.groupby(z_rt['sell_date'].dt.to_period('M'))['pnl'].sum().rename('Zerodha')
gm = g_rt.groupby(g_rt['sd'].dt.to_period('M'))['Realised P&L'].sum().rename('Groww')
gm.loc[pd.Period('2024-10')] = gm.get(pd.Period('2024-10'), 0) + G_IPO
a_tr['key'] = a_tr['Scrip/Contract'].str.strip()
last_sell = a_tr[a_tr['side']=='sell'].groupby('key')['Date'].max()
am_rows = []
eq_map = {'VMM':'VISHAL MEGA MART','RECLTD':'REC','SUZLON':'SUZLON ENERGY','PFC':'POWER FIN CORP',
          'ENRIN':'SIEMENS ENERGY INDIA','RAYMOND':'RAYMOND','SIEMENS':'SIEMENS'}
for _, r in a_eq.iterrows():
    nm = eq_map.get(r['Scrip Symbol'], r['Scrip Symbol'])
    cand = [d for k, d in last_sell.items() if nm.split()[0] in k.upper()]
    am_rows.append((max(cand) if cand else pd.Timestamp('2025-08-01'), r['Net PnL']))
for _, r in a_fn.iterrows():
    k = r['contract'].strip()
    am_rows.append((last_sell.get(k, pd.Timestamp('2025-01-31')), r['net']))
am = pd.DataFrame(am_rows, columns=['d','pnl'])
am = am.groupby(am['d'].dt.to_period('M'))['pnl'].sum().rename('AngelOne')
monthly = pd.concat([zm, am, gm], axis=1).fillna(0).sort_index()
monthly.index = monthly.index.astype(str)
monthly['Total'] = monthly.sum(axis=1)
monthly['Cumulative'] = monthly['Total'].cumsum()
monthly.to_csv(f'{OUT}/monthly_realized.csv', index_label='month')

lots = pd.concat([
    pd.DataFrame(dict(pnl=z_rt['pnl'], hold=z_rt['hold_days'], broker='Zerodha', symbol=z_rt['symbol'])),
    pd.DataFrame(dict(pnl=g_rt['Realised P&L'], hold=g_rt['hold'], broker='Groww', symbol=g_rt['Stock name'])),
], ignore_index=True)
lots.to_csv(f'{OUT}/trade_lots.csv', index=False)
win_rate_lots = float((lots['pnl']>0).mean())
w, l = lots.loc[lots['pnl']>0,'pnl'], lots.loc[lots['pnl']<0,'pnl']
profit_factor_lots = float(w.sum()/abs(l.sum()))

inst = pd.concat([
    z_rt.groupby('symbol')['pnl'].sum(),
    g_rt.groupby('Stock name')['Realised P&L'].sum(),
    a_eq.set_index('Scrip Symbol')['Net PnL'].rename(index=lambda s: eq_map.get(s, s)),
    pd.Series({'OLA ELECTRIC (IPO flip)': G_IPO, 'NIFTY options (Dec 24)': float(a_fn[a_fn['contract'].str.contains('NIFTY')]['net'].sum()),
               'ZOMATO futures (intraday)': float(a_fn[a_fn['contract'].str.contains('ZOMATO')]['net'].sum())})
]).groupby(level=0).sum().sort_values()
inst.to_csv(f'{OUT}/instrument_pnl.csv', header=['realized_pnl'])

g_grp = g_open.groupby('Stock name').agg(qty=('Quantity','sum'), cost=('Buy value','sum'), value=('Closing value','sum'), unrl=('Unrealised P&L','sum'))
open_rows = [
    dict(position='PATEL ENGINEERING', broker='Zerodha', qty=1559, cost=107081.06, value=40908.16, unrl=-66172.90, as_of='11-Jun-2026', frame='Conviction hold — EPC re-rating thesis (user)'),
    dict(position='PATEL ENGINEERING', broker='Groww', qty=int(g_grp.loc['PATEL ENGINEERING LTD.','qty']), cost=float(g_grp.loc['PATEL ENGINEERING LTD.','cost']), value=float(g_grp.loc['PATEL ENGINEERING LTD.','value']), unrl=float(g_grp.loc['PATEL ENGINEERING LTD.','unrl']), as_of='01-Jun-2026', frame='Conviction hold — EPC re-rating thesis (user)'),
    dict(position='WARDWIZARD INNOVATIONS', broker='Groww', qty=593, cost=float(g_grp.loc['WARDWIZARD INNOVATIONS AND MOB','cost']), value=float(g_grp.loc['WARDWIZARD INNOVATIONS AND MOB','value']), unrl=float(g_grp.loc['WARDWIZARD INNOVATIONS AND MOB','unrl']), as_of='01-Jun-2026', frame='Under review'),
    dict(position='OLA ELECTRIC (pledged)', broker='Groww', qty=2441, cost=244710.25, value=np.nan, unrl=np.nan, as_of='mark pending', frame='Under review — re-entry after IPO exit'),
    dict(position='Tracker positions (4)', broker='Groww', qty=5, cost=float(g_grp.loc[['NTPC LTD','MOREPEN LAB. LTD','INDIAN RAILWAY FIN CORP L'],'cost'].sum()), value=float(g_grp.loc[['NTPC LTD','MOREPEN LAB. LTD','INDIAN RAILWAY FIN CORP L'],'value'].sum()), unrl=float(g_grp.loc[['NTPC LTD','MOREPEN LAB. LTD','INDIAN RAILWAY FIN CORP L'],'unrl'].sum()), as_of='01-Jun-2026', frame='1-share monitors'),
    dict(position='LODHA — disclosure', broker='Zerodha', qty=26, cost=38565.00, value=np.nan, unrl=np.nan, as_of='not covered', frame='Open at Aug-24 window end; absent from current holdings. Exit falls in a period not covered by provided statements; its P&L is excluded from all totals.'),
]
ob = pd.DataFrame(open_rows); ob.to_csv(f'{OUT}/open_book.csv', index=False)

summary = dict(
  period='Sep 2023 – Jun 2026', generated=str(pd.Timestamp.today().date()),
  totals=dict(net_realized_incl_div=round(TOTAL_NET,2), net_realized_ex_div=round(TOTAL_NET-DIV,2), dividends=DIV,
              turnover=round(z_turn+a_turn+g_turn,0), orders=sum(orders.values()),
              lot_win_rate=round(win_rate_lots,4), lots=int(len(lots)), profit_factor=round(profit_factor_lots,2),
              median_hold_days=float(lots['hold'].median())),
  brokers=dict(
    zerodha=dict(window='Sep 2023 – Aug 2024', net=round(Z_NET,0), gross=Z_GROSS, charges=round(Z_CHG,0), turnover=round(z_turn,0), orders=orders['zerodha'], lot_wr=round(float((z_rt['pnl']>0).mean()),3), scrip_wr=0.875, note='FIFO engine ties to broker statement: ₹0.00 variance'),
    angelone=dict(window='Oct 2024 – Aug 2025', net=round(A_NET,0), equity_net=A_EQ_NET, fno_net=A_FNO_NET, turnover=round(a_turn,0), orders=orders['angelone'], scrip_wr=1.0, note='Statement scrip-level nets; 7/7 equity names profitable'),
    groww=dict(window='May 2024 – Jun 2026', net=round(G_NET,0), stmt_net=G_STMT_NET, ipo_recovered=G_IPO, turnover=round(g_turn,0), orders=orders['groww'], lot_wr=round(float((g_rt['Realised P&L']>0).mean()),3), profit_factor=1.71, note='Ledger ↔ order-history reconciliation closes within ₹40; +₹59,234 IPO gain recovered from settlement gap')),
  exhibits=[
    dict(title='Election-week deployment', date='Jun 2024', stat='+₹81,015 realized over Jun–Jul 24', body='~₹7.5L committed on 6 Jun 2024, two sessions after the election-result drawdown — ICICI, HDFC, JIOFIN, IDBI, Adani Green, Phoenix. Exited through June–July.'),
    dict(title='OLA Electric IPO flip', date='Oct 2024', stat='+₹59,234 realized', body='2,441 shares allotted at ₹76, sold at ₹100.26. Absent from broker P&L (IPO cost basis); recovered by reconciling a ₹1.85L settlement-ledger gap.'),
    dict(title='Research with capital committed', date='Jan 2025 – May 2026', stat='Held a −26% drawdown · 3 dividends', body='Initiated independent coverage on Triveni Turbine; bought 284 sh at ₹703.79. Marked −26% by May 2025; averaged 10 sh at ₹539 into the drawdown; exited all 294 at ₹709.90 in May 2026, three dividends collected.')],
  pending=['Combined money-weighted return (XIRR) — requires AngelOne fund ledger + final OLA mark; withheld until computable across all accounts',
           'NIFTY 50 TRI benchmark overlay — to be added with a market-data feed',
           'OLA Electric current mark — pledged holding, not priced in broker P&L export',
           'Zerodha post-Aug-2024 disposals (incl. LODHA 26 sh open at window end) — pending FY25 export'],
  charges_total=round(Z_CHG+2943.75+1027.61+761.45+20855.29,0))
json.dump(summary, open(f'{OUT}/summary_metrics.json','w'), indent=1)
print('monthly tail:\n', monthly.tail(8).round(0).to_string())
print('lots:', len(lots), '| lot WR:', round(win_rate_lots,3), '| PF:', round(profit_factor_lots,2), '| median hold:', lots['hold'].median())
print('TOTAL NET (incl div):', round(TOTAL_NET,0), '| turnover Cr:', round((z_turn+a_turn+g_turn)/1e7,3), '| orders:', sum(orders.values()))
