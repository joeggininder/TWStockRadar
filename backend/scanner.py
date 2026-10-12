"""TWSE price and institutional-data collection (partial four-signal scanner).

Only official daily snapshots; do not assert verified trade dates or missing signals.
"""
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
BASE = 'https://openapi.twse.com.tw/v1/exchangeReport/'
URLS = {'prices': BASE + 'STOCK_DAY_ALL', 'institutional': BASE + 'T86'}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 TWStockRadar/1.1', 'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        value = json.load(resp)
    if not isinstance(value, list) or len(value) < 100:
        raise ValueError('Unexpected/empty market response')
    return value

def num(x):
    try:
        return float(str(x).replace(',', '').strip())
    except (TypeError, ValueError):
        return None

def parse_prices(rows):
    out = {}
    for r in rows:
        sid = str(r.get('Code', r.get('證券代號', ''))).strip()
        close = num(r.get('ClosingPrice', r.get('收盤價')))
        volume = num(r.get('TradeVolume', r.get('成交股數')))
        if len(sid) == 4 and sid.isdigit() and close is not None and volume is not None:
            out[sid] = {'id':sid, 'name':r.get('Name', r.get('證券名稱','')), 'close':close, 'volume':volume}
    return out

def parse_institutional(rows):
    out = {}
    for r in rows:
        sid = str(r.get('證券代號', r.get('Code', ''))).strip()
        foreign = num(r.get('外陸資買賣超股數(不含外資自營商)', r.get('外資及陸資買賣超股數(不含外資自營商)')))
        trust = num(r.get('投信買賣超股數'))
        if len(sid) == 4 and sid.isdigit() and (foreign is not None or trust is not None):
            out[sid] = {'foreign':foreign, 'trust':trust}
    return out

def main():
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo('Asia/Taipei'))
    errors = []
    try:
        prices = parse_prices(fetch(URLS['prices']))
        if len(prices) < 100: raise ValueError('Not enough valid prices')
    except Exception as e:
        prices = {}
        errors.append('價格：'+str(e))
    try:
        inst = parse_institutional(fetch(URLS['institutional']))
        if len(inst) < 100: raise ValueError('Not enough valid institutional data')
    except Exception as e:
        inst = {}
        errors.append('法人：'+str(e))

    # The TWSE OpenAPI endpoints can return a prior session on a holiday.
    # Do not label collection date as verified exchange trading date or count
    # consecutive sessions until an official dated source is integrated.
    stocks = []
    for sid, p in prices.items():
        flow = inst.get(sid, {'foreign': None, 'trust': None})
        stocks.append({'id':sid, 'name':p['name'], 'close':p['close'],
                       'trade_date':'',
                       'checks':{'institutional':False, 'holders':False, 'retail':False, 'brokers':False},
                       'evidence':{'volume_shares':p['volume'],
                                   'foreign_net_shares':flow['foreign'],
                                   'trust_net_shares':flow['trust'],
                                   'collection_date_tw':local.date().isoformat(),
                                   'institutional':'需交易日驗證與連續3日歷史資料',
                                   'holders':'TDCC待接入', 'retail':'融資待接入',
                                   'brokers':'券商分點待接入'},
                       'sources':list(URLS.values())})
    payload = {'generated_at':now.isoformat(), 'stocks':stocks,
               'notice':'已接入證交所上市股票公開行情與法人單日資料；尚未完成交易日驗證、連續買超、TDCC、融資及分點，所有四項訊號保守標示未驗證。' + (' 讀取錯誤：'+'；'.join(errors) if errors else ''),
               'source_status':{'prices':len(prices), 'institutional':len(inst), 'errors':errors}}
    (DATA/'latest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Price records:',len(prices),'institutional:',len(inst),'output stocks:',len(stocks))

if __name__ == '__main__':
    main()
