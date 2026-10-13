"""TWSE price and institutional-data collection (partial four-signal scanner).

Only official daily snapshots; do not assert verified trade dates or missing signals.
"""
import json
import csv
import io
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
BASE = 'https://openapi.twse.com.tw/v1/exchangeReport/'

URLS = {
    'prices': BASE + 'STOCK_DAY_ALL',
    'institutional': 'https://www.twse.com.tw/rwd/zh/fund/T86',
    'margin': 'https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN',
    'tdcc': 'https://opendata.tdcc.com.tw/getOD.ashx?id=1-5'
}


def fetch_latest_institutional():
    today = datetime.now(ZoneInfo('Asia/Taipei')).date()
    history = []
    seen_dates = set()

    for days_back in range(15):
        day = today - timedelta(days=days_back)

        # 週六、週日不查詢
        if day.weekday() >= 5:
            continue

        date_str = day.strftime('%Y%m%d')
        url = (
            URLS['institutional']
            + '?date=' + date_str
            + '&selectType=ALLBUT0999&response=json'
        )

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json'
                }
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                payload = json.load(resp)

            if payload.get('stat') != 'OK':
                continue

            response_date = str(payload.get('date', '')).strip()
            if response_date != date_str:
                continue

            inst = parse_institutional(payload.get('data', []))
            if len(inst) < 100:
                continue

            iso_date = day.isoformat()
            if iso_date in seen_dates:
                continue

            history.append({
                'date': iso_date,
                'stocks': inst
            })
            seen_dates.add(iso_date)

            print('Verified institutional date:', iso_date,
                  'records:', len(inst))

            if len(history) == 3:
                break

        except Exception as e:
            print('T86 query failed:', date_str, str(e))

    if len(history) != 3:
        raise ValueError(
            '三日法人資料不足，目前取得 ' + str(len(history)) + ' 日'
        )

    return history

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
        if not isinstance(r, list) or len(r) < 11:
            continue

        sid = str(r[0]).strip()
        foreign = num(r[4])
        trust = num(r[10])

        if (
            len(sid) == 4
            and sid.isdigit()
            and foreign is not None
            and trust is not None
        ):
            out[sid] = {
                'foreign': foreign,
                'trust': trust
            }
    return out

def check_three_day_buying(sid, history):
    records = []

    for day in history:
        flow = day['stocks'].get(sid)

        if flow is None:
            return False, records

        foreign = flow.get('foreign')
        trust = flow.get('trust')

        if foreign is None or trust is None:
            return False, records

        records.append({
            'date': day['date'],
            'foreign_net_shares': foreign,
            'trust_net_shares': trust
        })

    passed = (
        len(records) == 3
        and all(
            r['foreign_net_shares'] > 0
            and r['trust_net_shares'] > 0
            for r in records
        )
    )

    return passed, records

def parse_margin(payload):
    result = {}

    for table in payload.get('tables', []):
        fields = table.get('fields', [])

        # 找到含個股融資餘額的資料表
        if '代號' not in fields or '名稱' not in fields:
            continue

        # 證交所此表有兩組「今日餘額」
        # 第一組為融資，第二組為融券
        balance_indices = [
            i for i, field in enumerate(fields)
            if field == '今日餘額'
        ]

        if len(balance_indices) < 2:
            continue

        balance_index = balance_indices[0]
        code_index = fields.index('代號')

        for row in table.get('data', []):
            if len(row) <= max(code_index, balance_index):
                continue

            sid = str(row[code_index]).strip()
            balance = num(row[balance_index])

            if len(sid) == 4 and sid.isdigit() and balance is not None:
                result[sid] = balance

    return result

def fetch_margin_history():
    today = datetime.now(ZoneInfo('Asia/Taipei')).date()
    history = []
    seen_dates = set()

    for days_back in range(20):
        day = today - timedelta(days=days_back)

        if day.weekday() >= 5:
            continue

        date_str = day.strftime('%Y%m%d')
        url = (
            URLS['margin']
            + '?date=' + date_str
            + '&selectType=ALL&response=json'
        )

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=40) as resp:
                payload = json.load(resp)

            if payload.get('stat') != 'OK':
                continue

            if str(payload.get('date', '')).strip() != date_str:
                continue

            margin = parse_margin(payload)

            if len(margin) < 100:
                continue

            iso_date = day.isoformat()

            if iso_date in seen_dates:
                continue

            history.append({
                'date': iso_date,
                'stocks': margin
            })
            seen_dates.add(iso_date)

            print('Verified margin date:', iso_date,
                  'records:', len(margin))

            if len(history) == 4:
                break

        except Exception as e:
            print('Margin query failed:', date_str, str(e))

    if len(history) != 4:
        raise ValueError(
            '融資資料不足四日，目前取得 '
            + str(len(history)) + ' 日'
        )

    return history

def check_margin_decline(sid, history):
    if len(history) != 4:
        return False, []

    records = []

    for day in history:
        balance = day['stocks'].get(sid)

        if balance is None:
            return False, records

        records.append({
            'date': day['date'],
            'margin_balance': balance
        })

    balances = [r['margin_balance'] for r in records]

    passed = (
        balances[0] < balances[1]
        and balances[1] < balances[2]
        and balances[2] < balances[3]
    )

    return passed, records



def fetch_tdcc():
    import time

    req = urllib.request.Request(
        URLS['tdcc'],
        headers={'User-Agent': 'Mozilla/5.0'}
    )

    raw = None


    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read()
            break

        except Exception as e:
            print('TDCC download attempt', attempt + 1, 'failed:', str(e))

            if attempt == 2:
                raise

            time.sleep(5)
    text = raw.decode('utf-8-sig')
    rows = list(csv.DictReader(io.StringIO(text)))

    if not rows:
        raise ValueError('TDCC CSV 沒有資料')
    print('TDCC CSV columns:', list(rows[0].keys()))
    print('TDCC first row:', rows[0])
    print('TDCC last row:', rows[-1])
    result = {}

    for row in rows:
        sid = str(row.get('證券代號', '')).strip()
        date = str(row.get('資料日期', '')).strip()
        level = str(row.get('持股分級', '')).strip()

        if len(sid) != 4 or not sid.isdigit():
            continue

        if sid not in result:
            result[sid] = {'date': date}

        if level == '15':
            result[sid]['large_holder_pct'] = num(
                row.get('占集保庫存數比例%')
            )

        elif level == '17':
            result[sid]['shareholder_count'] = num(
                row.get('人數')
            )

    valid = {
        sid: data for sid, data in result.items()
        if data.get('large_holder_pct') is not None
        and data.get('shareholder_count') is not None
    }

    if len(valid) < 100:
        raise ValueError('TDCC 有效股票資料不足')

    return valid

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
        institutional_history = fetch_latest_institutional()
        inst = institutional_history[0]['stocks']
        institutional_date = institutional_history[0]['date']
        print('Institutional trade date:', institutional_date)
        print('Institutional history days:', len(institutional_history))
    except Exception as e:
        institutional_history = []
        inst = {}
        institutional_date = ''
        errors.append('法人：' + str(e))


    # The TWSE OpenAPI endpoints can return a prior session on a holiday.
    # Do not label collection date as verified exchange trading date or count
    # consecutive sessions until an official dated source is integrated.
    
    try:
        margin_history = fetch_margin_history()
        print('Margin history days:', len(margin_history))
    except Exception as e:
        margin_history = []
        errors.append('融資：' + str(e))
        print('Margin history error:', str(e))


    try:
        tdcc = fetch_tdcc()
        print('TDCC records:', len(tdcc))
    except Exception as e:
        tdcc = {}
        errors.append('TDCC：' + str(e))
        print('TDCC error:', str(e))


    stocks = []
    for sid, p in prices.items():
        flow = inst.get(sid, {'foreign': None, 'trust': None})
        
        institutional_passed, institutional_records = (
            check_three_day_buying(sid, institutional_history)
        )

        margin_passed, margin_records = (
            check_margin_decline(sid, margin_history)
        )

        stocks.append({'id':sid, 'name':p['name'], 'close':p['close'],
                       'trade_date':'',
                      
                      
                    'checks':{'institutional':institutional_passed, 'holders':False, 'retail':margin_passed, 'brokers':False},


                       'evidence':{'volume_shares':p['volume'],
                                   'foreign_net_shares':flow['foreign'],
                                   'trust_net_shares':flow['trust'],
                                   'collection_date_tw':local.date().isoformat(),

                                   'institutional': (
                                       '外資與投信皆連續三個有效交易日買超'
                                       if institutional_passed
                                       else '未符合或三日法人資料不完整'
                                   ),
                                   'institutional_history': institutional_records,
                                   'margin_history': margin_records,
                                   'institutional_trade_date': institutional_date,

                                   'holders':'TDCC待接入', 'retail':'融資待接入',
                                   'brokers':'券商分點待接入'},
                       'sources':list(URLS.values())})
        
    institutional_matches = [
        s for s in stocks
        if s['checks']['institutional']
    ]

    print('Three-day institutional matches:', len(institutional_matches))
    print('Matched stock IDs:', ', '.join(
        s['id'] for s in institutional_matches
    ))

    two_signal_matches = [
        s for s in stocks
        if s['checks']['institutional']
        and s['checks']['retail']
    ]

    print('Two-signal matches:', len(two_signal_matches))
    print('Two-signal stock IDs:', ', '.join(
        s['id'] for s in two_signal_matches
    ))

    payload = {'generated_at':now.isoformat(), 'stocks':stocks,
               'notice':'已接入證交所上市股票公開行情與法人單日資料；尚未完成交易日驗證、連續買超、TDCC、融資及分點，所有四項訊號保守標示未驗證。' + (' 讀取錯誤：'+'；'.join(errors) if errors else ''),
               'source_status':{'prices':len(prices), 'institutional':len(inst), 'errors':errors}}
    (DATA/'latest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Price records:',len(prices),'institutional:',len(inst),'output stocks:',len(stocks))

if __name__ == '__main__':
    main()
