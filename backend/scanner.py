"""Conservative 4-signal evaluator. Never turn missing inputs into positive signals.
Input: data/source.json (verified observations from licensed/public data pipelines).
Output: data/latest.json (Android app consumes this).
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'data'/'source.json'
OUT=ROOT/'data'/'latest.json'

def evaluate(s):
    # Required dates and numeric observations are explicit. All four rules fail closed.
    inst=s.get('institutional',{})
    holders=s.get('holders',{})
    retail=s.get('retail',{})
    brokers=s.get('brokers',{})
    vol=s.get('avg_daily_volume_20d')
    checks={
      'institutional': bool(vol and vol>0 and inst.get('consecutive_buy_days',0)>=3 and inst.get('net_buy_3d',0)/vol>=0.05 and inst.get('asof')),
      'holders': bool(holders.get('large_holder_pct_change',0)>0 and holders.get('shareholder_count_change',0)<0 and holders.get('asof') and holders.get('prior_asof')),
      'retail': bool(retail.get('margin_balance_change_5d',0)<0 and retail.get('asof') and retail.get('margin_balance_5d_ago') is not None),
      'brokers': bool(brokers.get('verified_distinct_days',0)>=3 and brokers.get('net_buy_shares',0)>0 and brokers.get('not_daytrade_evidence') is True and brokers.get('asof') and brokers.get('source_url')),
    }
    return {'id':s.get('id',''),'name':s.get('name',''),'close':s.get('close'),
      'trade_date':s.get('trade_date',''),'checks':checks,
      'evidence':s.get('evidence',''),'sources':s.get('sources',[])}

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if not SOURCE.exists():
        stocks=[]
        notice='尚未匯入可驗證的完整市場資料；不顯示假陽性。'
    else:
        raw=json.loads(SOURCE.read_text(encoding='utf-8'))
        stocks=[evaluate(s) for s in raw.get('stocks',[])]
        notice='四條件採保守判斷；分點資料需有授權來源。'
    payload={'generated_at':datetime.now(timezone.utc).isoformat(),'stocks':stocks,'notice':notice}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'generated {OUT}: {len(stocks)} stocks, {sum(all(s["checks"].values()) for s in stocks)} matches')

if __name__=='__main__':main()
