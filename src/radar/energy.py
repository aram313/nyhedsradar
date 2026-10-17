"""The economy page's numbers (khabar.nu/energi, the app's Økonomi tab): fuel, oil and gas, markets, the AI giants,
debt and commodities, Danish pump prices and energy news.

Runs after every radar pass (radar.yml) and writes `energy.json` into the state folder, which is saved on the data
branch the page reads. Stdlib only. Every source has its own clock (EVERY) and a failed fetch keeps the last good
numbers, so one source being down never blanks the page.

Sources (all free, open and keyless):
- futures, indices, risk gauges, commodities, the AI companies, USD/DKK and EUR/DKK: Yahoo Finance chart API
  (~10–15 min delayed), daily closes for 6 months and each market's session (to tell an open market from a close);
  the Brent and WTI curves from the individual contract months
- physical spot prices: EIA's daily series (Brent FOB, WTI Cushing, New York Harbor gasoline and diesel, Gulf Coast
  jet fuel, Henry Hub), a few days behind – from EIA's own history pages, else from FRED (FRED does not answer
  GitHub's runners); a source that fails is tried again after RETRY, not on every pass
- US pump prices: EIA's weekly retail regular gasoline and diesel, US average ($/gallon), two years of Mondays
- European pump prices: the EU's Weekly Oil Bulletin, latest prices with taxes (EUR per 1000 litres, every Monday)
- the AI giants' weight in the S&P 500: State Street's daily holdings of SPY, the fund that tracks the index
- US federal debt: the Treasury's Debt to the Penny (api.fiscaldata.treasury.gov), daily, with its average growth
- government debt in % of GDP: the IMF's DataMapper (GGXWDG_NGDP), annual
- Danish pump prices: Circle K's public price API (Circle K and INGO stations) and Q8's station price list (Q8 and
  F24), every station; the page shows each chain's list price and its cheapest station
- news: stories about oil, fuel and gas from this radar run (data.json), with the editor's headline where he
  wrote one (summaries.json, RADAR_SUMMARIES); the wire's one-liners are left out (machine-translated Arabic)

The page holds the names, units and explanations; this file only holds numbers, so wording can change without a run.
"""
import csv
import gzip
import io
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from radar.stats import dk

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
BBL_L = 158.987     # litres in a barrel
GAL_L = 3.78541     # litres in a US gallon
GAL_BBL = 42        # gallons in a barrel

# seconds between fetches of each source (the radar runs every ~5 minutes)
EVERY = {'markets': 4 * 60, 'curve': 30 * 60, 'fred': 3 * 3600, 'pumps': 20 * 60, 'usfuel': 6 * 3600,
         'eu': 12 * 3600, 'spy': 6 * 3600, 'debt': 3 * 3600, 'imf': 24 * 3600}
RETRY = 30 * 60     # a source that failed is asked again after half an hour, so a dead one never slows every pass

YAHOO = {               # key -> symbol; prices in the exchange's unit
    'brent': 'BZ=F',    # Brent, front month, $/bbl
    'wti': 'CL=F',      # WTI, front month, $/bbl
    'rbob': 'RB=F',     # RBOB gasoline (New York Harbor), $/gal
    'ulsd': 'HO=F',     # ULSD diesel (New York Harbor), $/gal
    'hh': 'NG=F',       # Henry Hub natural gas, $/MMBtu
    'ttf': 'TTF=F',     # Dutch TTF gas, EUR/MWh
    'usddkk': 'DKK=X',  # kroner per dollar
    'eurdkk': 'EURDKK=X',   # kroner per euro (the EU's pump prices)
    # indices
    'spx': '^GSPC', 'ndx': '^NDX', 'sx5e': '^STOXX50E', 'c25': '^OMXC25', 'n225': '^N225', 'sse': '000001.SS',
    # risk gauges: the VIX, the US 10-year yield (in %), the dollar index
    'vix': '^VIX', 'tnx': '^TNX', 'dxy': 'DX-Y.NYB',
    # commodities: gold $/oz, copper $/lb, wheat US cents/bushel, Bitcoin $
    'gold': 'GC=F', 'copper': 'HG=F', 'wheat': 'ZW=F', 'btc': 'BTC-USD',
    # the AI giants
    'nvda': 'NVDA', 'msft': 'MSFT', 'googl': 'GOOGL', 'meta': 'META', 'amzn': 'AMZN', 'aapl': 'AAPL', 'tsm': 'TSM',
    'avgo': 'AVGO',
}
# the AI basket's tickers as SPY's holdings list them (Alphabet has two share classes; TSMC is not in the S&P 500)
AI = {'nvda': ['NVDA'], 'msft': ['MSFT'], 'googl': ['GOOGL', 'GOOG'], 'meta': ['META'], 'amzn': ['AMZN'],
      'aapl': ['AAPL'], 'tsm': [], 'avgo': ['AVGO']}
US_FUEL = {                       # EIA weekly retail prices, US average, $/gallon (all formulations, regular / No. 2 diesel)
    'us_gas': 'EMM_EPMR_PTE_NUS_DPG',
    'us_diesel': 'EMD_EPD2D_PTE_NUS_DPG',
}
# the EU's Weekly Oil Bulletin, 'Prices with taxes – latest prices' (the document id stays; its file name changes)
EU_URL = 'https://energy.ec.europa.eu/document/download/264c2d0f-f161-4ea3-a777-78faae59bea0_en'
EU_LAND = {'EU': 'EUR27', 'DE': 'Germany', 'SE': 'Sweden', 'FR': 'France', 'NL': 'Netherlands', 'DK': 'Denmark',
           'IT': 'Italy', 'PL': 'Poland', 'ES': 'Spain'}
SPY_URL = 'https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx'
DEBT_URL = ('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny'
            '?sort=-record_date&page%5Bsize%5D=600&fields=record_date,tot_pub_debt_out_amt')
IMF_URL = 'https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP'
# the countries of the debt bars (IMF codes); the page names them
IMF_LAND = ['USA', 'JPN', 'GBR', 'FRA', 'ITA', 'DEU', 'CHN', 'DNK', 'TUR', 'EGY', 'SAU', 'ISR', 'PAK', 'RUS', 'IRN', 'GRC']
CURVES = {'brent': 'BZ', 'wti': 'CL'}
MONTHS = 'FGHJKMNQUVXZ'

FRED = {                         # key -> FRED series id (EIA spot prices)
    'brent_spot': 'DCOILBRENTEU',     # Europe Brent spot FOB, $/bbl
    'wti_spot': 'DCOILWTICO',         # WTI Cushing spot, $/bbl
    'gas_nyh': 'DGASNYH',             # NY Harbor conventional gasoline, $/gal
    'ulsd_nyh': 'DDFUELNYH',          # NY Harbor ultra-low-sulfur diesel, $/gal
    'jet_gulf': 'DJFUELUSGULF',       # US Gulf Coast jet fuel, $/gal
    'hh_spot': 'DHHNGSP',             # Henry Hub spot, $/MMBtu
}
EIA = {                          # the same series on EIA's own history pages (n, s)
    'brent_spot': ('PET', 'RBRTE'),
    'wti_spot': ('PET', 'RWTC'),
    'gas_nyh': ('PET', 'EER_EPMRU_PF4_Y35NY_DPG'),
    'ulsd_nyh': ('PET', 'EER_EPD2DXL0_PF4_Y35NY_DPG'),
    'jet_gulf': ('PET', 'EER_EPJK_PF4_RGC_DPG'),
    'hh_spot': ('NG', 'RNGWHHD'),
}
EIA_MON = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}

# pump products, matched on the chains' own product names (lower case)
PRODUCTS = {
    'benzin': {'miles 95', 'benzin 95', 'goeasy 95 e10'},
    'diesel': {'miles diesel', 'diesel', 'goeasy diesel'},
    'benzin_plus': {'miles+ 95', 'milesplus95', 'upgrade 95', 'goeasy 95 extra e5'},
    'diesel_plus': {'miles+ diesel', 'milesplus di', 'goeasy diesel extra'},
    'hvo': {'neste my (hvo100)'},
}
CHAINS = ['Circle K', 'INGO', 'Q8', 'F24']

# energy news: whole words in a headline (English, Danish, Arabic, Turkish); 'gas' only in compounds (tear gas, Gaza)
NEWS = re.compile(
    r"(?<![\w-])(oil|oils|crude|brent|opec\+?|petrol|petroleum|gasoline|diesel|refiner(?:y|ies)|tankers?|lng|"
    r"natural gas|gas (?:price|prices|field|fields|supply|supplies|exports?|pipeline)|pipelines?|hormuz|aramco|"
    r"fuel|fuels|energy prices?|barrels?|olie\w*|råolie\w*|benzin\w*|brændstof\w*|raffinaderi\w*|naturgas\w*|"
    r"gaspris\w*|gasledning\w*|energipris\w*|tankskib\w*|hormuz-strædet|"
    r"نفط|النفط|بنزين|أوبك|الغاز|غاز|برنت|petrol|akaryakıt|doğalgaz|ham petrol)(?![\w-])", re.I)
# economic crises for the page's own topic (the owner, 17/10: "der skal også være økonomi nyheder, primært kriser"):
# a state's default or debt crisis, a currency's fall, a bank's collapse or a run on it, a crash, recession, an IMF
# rescue, sanctions and tariffs between powers, a trade war, inflation out of hand
CRISIS = re.compile(
    r"(?<![\w-])(default(?:s|ed)?|debt crisis|sovereign debt|bankrupt\w*|bailout|bail-out|imf|recession|"
    r"currency (?:crisis|collapse|plunge\w*|crash\w*)|devalu\w*|hyperinflation|inflation (?:soars|surges|hits|record)|"
    r"bank run|bank (?:collapse\w*|failure\w*)|market (?:crash\w*|rout|turmoil|selloff|sell-off)|stocks? (?:plunge\w*|"
    r"tumble\w*|crash\w*)|trade war|tariffs?|sanctions?|credit rating|downgrade\w*|financial crisis|"
    r"economic crisis|statsbankerot|betalingsstandsning|gældskrise\w*|økonomisk(?:e)? krise\w*|finanskrise\w*|"
    r"valutakrise\w*|devaluering\w*|recession\w*|lavkonjunktur\w*|redningspakke\w*|nødlån\w*|bankkrak\w*|"
    r"børskrak\w*|børsfald\w*|kursfald\w*|handelskrig\w*|toldmur\w*|toldsats\w*|toldkrig\w*|told på|told mod|"
    r"straftold\w*|sanktion\w*|nedgradering\w*|"
    r"inflation\w*|hyperinflation\w*|IMF|"
    # a state's borrowing under stress and the central bank asked to step in (18/10: the French debt crisis and the
    # ECB never reached the page): bond yields, borrowing costs, the spread to German bonds, ratings, a budget crisis
    r"bond yields?|bond market|borrowing costs?|yield spread|bond spread|spread (?:over|to|with) (?:german )?bunds?|"
    r"ECB|European Central Bank|Lagarde|bond[- ]buying|credit (?:outlook|downgrade)|budget crisis|fiscal crisis|"
    r"lånerente\w*|renteforskel\w*|renten på (?:franske |italienske )?statsobligationer|statsobligation\w*|"
    r"kreditvurdering\w*|Den Europæiske Centralbank|budgetkrise\w*|gældsloft\w*)(?![\w-])", re.I)


def now():
    return datetime.now(timezone.utc)


def get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get('Content-Encoding') == 'gzip' or body[:2] == b'\x1f\x8b':
            body = gzip.decompress(body)
    return body


def r4(x):
    """Four significant decimals is plenty for a price and keeps the file small."""
    return None if x is None else float(f'{x:.6g}')


# ---- futures (Yahoo) ---------------------------------------------------------------------------------------------

def yahoo(symbol, rng='6mo'):
    """Daily closes and the live price: {'v', 't', 'h': [[date, close], ...]}, or None."""
    q = urllib.parse.quote(symbol)
    for host in ('query1', 'query2'):
        try:
            d = json.loads(get(f'https://{host}.finance.yahoo.com/v8/finance/chart/{q}?range={rng}&interval=1d'))
            res = (d.get('chart') or {}).get('result')
            if not res:
                continue
            r = res[0]
            meta, ts = r['meta'], r.get('timestamp') or []
            closes = r['indicators']['quote'][0].get('close') or []
            off = meta.get('gmtoffset') or 0
            hist = {}
            for t, c in zip(ts, closes):
                if c is not None:
                    hist[datetime.fromtimestamp(t + off, timezone.utc).date().isoformat()] = r4(c)
            price, at = meta.get('regularMarketPrice'), meta.get('regularMarketTime')
            if price is None or not at:
                continue
            hist[datetime.fromtimestamp(at + off, timezone.utc).date().isoformat()] = r4(price)
            out = {'v': r4(price), 't': datetime.fromtimestamp(at, timezone.utc).isoformat(),
                   'h': [list(p) for p in sorted(hist.items())]}
            # the session the price belongs to (epoch seconds): the page tells an open market from a closing price
            reg = (meta.get('currentTradingPeriod') or {}).get('regular') or {}
            if reg.get('start') and reg.get('end'):
                out['o'] = [reg['start'], reg['end']]
            return out
        except Exception:
            continue
    return None


def fetch_markets():
    with ThreadPoolExecutor(10) as ex:
        got = dict(zip(YAHOO, ex.map(yahoo, YAHOO.values())))
    return {k: v for k, v in got.items() if v}


def contracts(root, today, n=15):
    """Yahoo symbols of the next n contract months, e.g. BZZ26.NYM."""
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append((f'{y}-{m:02d}', f'{root}{MONTHS[m - 1]}{y % 100:02d}.NYM'))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def fetch_curves(front_times):
    """Brent and WTI forward curves: [[YYYY-MM, price], ...] for the next 12 live contract months."""
    today = now().date()
    jobs = [(key, month, sym) for key, root in CURVES.items() for month, sym in contracts(root, today)]

    def one(job):
        key, month, sym = job
        q = urllib.parse.quote(sym)
        try:
            d = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{q}?range=5d&interval=1d'))
            meta = d['chart']['result'][0]['meta']
            return key, month, meta.get('regularMarketPrice'), meta.get('regularMarketTime')
        except Exception:
            return key, month, None, None

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, jobs))
    out = {}
    for key in CURVES:
        front = front_times.get(key)
        pts = []
        for k, month, price, at in rows:
            # an expired month still answers with its last price: keep only months that traded with the front month
            if k != key or price is None or not at:
                continue
            if front and abs(at - front) > 4 * 86400:
                continue
            pts.append([month, r4(price)])
        if len(pts) >= 3:
            out[key] = pts[:12]
    return out


# ---- physical spot prices (EIA via FRED) ---------------------------------------------------------------------------

def eia_rows(html, days=200):
    """EIA's daily history page: one row a week ('2026 Oct-12 to Oct-16', then Monday … Friday) -> [[date, v], ...]."""
    cut = (now().date() - timedelta(days=days)).isoformat()
    hist = []
    for row in re.findall(r"<tr>\s*<td class='B6'>(.*?)</tr>", html, re.S):
        m = re.search(r'(\d{4})\s+([A-Z][a-z]{2})-\s*(\d{1,2})\s+to', row)
        if not m or m.group(2) not in EIA_MON:
            continue
        monday = date(int(m.group(1)), EIA_MON[m.group(2)], int(m.group(3)))
        for i, cell in enumerate(re.findall(r"<td class='B3'>\s*([^<]*?)\s*</td>", row)[:5]):
            try:
                v = float(cell)
            except ValueError:
                continue      # an empty cell: a holiday, or a day not yet reported
            d = (monday + timedelta(days=i)).isoformat()
            if d >= cut:
                hist.append([d, r4(v)])
    return sorted(hist)


def eia(key, days=200):
    n, sid = EIA[key]
    # the gas pages have no LeafHandler (404): their static history page holds the same rows
    url = (f'https://www.eia.gov/dnav/ng/hist/{sid.lower()}D.htm' if n == 'NG'
           else f'https://www.eia.gov/dnav/{n.lower()}/hist/LeafHandler.ashx?n={n}&s={sid}&f=D')
    try:
        html = get(url, timeout=20).decode('utf-8', 'replace')
    except Exception:
        return None
    hist = eia_rows(html, days)
    return {'v': hist[-1][1], 't': hist[-1][0], 'h': hist} if hist else None


def fred(series, days=200):
    start = (now().date() - timedelta(days=days)).isoformat()
    try:
        # FRED's bot shield drops a browser-like agent that lacks a browser's other headers; a plain one is let in
        text = get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}',
                   {'User-Agent': 'khabar.nu energy prices'}, timeout=12).decode()
    except Exception:
        return None
    hist = []
    for row in list(csv.reader(io.StringIO(text)))[1:]:
        if len(row) >= 2:
            try:
                hist.append([row[0], r4(float(row[1]))])
            except ValueError:
                continue      # '.' marks a day without a price
    if not hist:
        return None
    return {'v': hist[-1][1], 't': hist[-1][0], 'h': hist}


def spot(key):
    return eia(key) or fred(FRED[key])


def fetch_fred():
    with ThreadPoolExecutor(6) as ex:
        got = dict(zip(FRED, ex.map(spot, FRED)))
    return {k: v for k, v in got.items() if v}


# ---- US pump prices (EIA, weekly) ------------------------------------------------------------------------------------

def eia_weeks(html, days=731):
    """EIA's weekly history page: one row a month ('2026-Oct', then up to five 'MM/DD' and price pairs) ->
    [[date, v], ...] for the last `days` days."""
    cut = (now().date() - timedelta(days=days)).isoformat()
    hist = []
    for row in re.findall(r"<tr>\s*<td class='B6'>(.*?)</tr>", html, re.S):
        m = re.search(r'(\d{4})-([A-Z][a-z]{2})', row)
        if not m or m.group(2) not in EIA_MON:
            continue
        year, mon = int(m.group(1)), EIA_MON[m.group(2)]
        for mm, dd, v in re.findall(r"<td class='B5'>\s*(\d{2})/(\d{2})[^<]*</td>\s*<td class='B3'>\s*([\d.]+)", row):
            y = year - 1 if int(mm) == 12 and mon == 1 else year + 1 if int(mm) == 1 and mon == 12 else year
            try:
                d = date(y, int(mm), int(dd)).isoformat()
                hist.append([d, r4(float(v))])
            except ValueError:
                continue
    return sorted(x for x in hist if x[0] >= cut)


def fetch_usfuel():
    def one(sid):
        try:
            html = get(f'https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={sid}&f=W', timeout=15).decode('utf-8', 'replace')
        except Exception:
            return None
        hist = eia_weeks(html)
        return {'v': hist[-1][1], 't': hist[-1][0], 'h': hist} if hist else None

    with ThreadPoolExecutor(2) as ex:
        got = dict(zip(US_FUEL, ex.map(one, US_FUEL.values())))
    return {k: v for k, v in got.items() if v}


# ---- spreadsheets (stdlib: an .xlsx is a zip of XML) -----------------------------------------------------------------

def xlsx_rows(blob):
    """The first sheet of an .xlsx as rows of {column letter: text or number}."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode('utf-8', 'replace'), re.S):
            strings.append(re.sub(r'<[^>]+>', '', si).replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<').strip())
    sheet = z.read('xl/worksheets/sheet1.xml').decode('utf-8', 'replace')
    rows = []
    for row in re.findall(r'<row\b[^>]*>(.*?)</row>', sheet, re.S):
        cells = {}
        for col, attrs, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', row, re.S):
            v = re.search(r'<v>(.*?)</v>', inner or '', re.S)
            if not v:
                t = re.search(r'<t[^>]*>(.*?)</t>', inner or '', re.S)     # an inline string
                if t:
                    cells[col] = t.group(1).strip()
                continue
            v = v.group(1)
            if 't="s"' in attrs:
                cells[col] = strings[int(v)] if int(v) < len(strings) else ''
            elif 't="str"' in attrs:
                cells[col] = v
            else:
                try:
                    cells[col] = float(v)
                except ValueError:
                    cells[col] = v
        rows.append(cells)
    return rows


def excel_day(n):
    return (date(1899, 12, 30) + timedelta(days=int(n))).isoformat()


# ---- European pump prices (the EU's Weekly Oil Bulletin) -------------------------------------------------------------

def eu_prices(rows):
    """The bulletin's latest prices with taxes: {'t': Monday, 'c': {code: [petrol, diesel]}} in EUR per 1000 litres."""
    day = next((r['A'] for r in rows[:4] if isinstance(r.get('A'), float)), None)
    out = {}
    for r in rows:
        name = str(r.get('A') or '')
        for code, land in EU_LAND.items():
            if code not in out and (name == land or (land == 'EUR27' and 'EUR27' in name)):
                b, d = r.get('B'), r.get('C')
                if isinstance(b, float) and isinstance(d, float):
                    out[code] = [r4(b), r4(d)]
    if not day or 'EU' not in out:
        return None
    return {'t': excel_day(day), 'c': out}


def fetch_eu():
    return eu_prices(xlsx_rows(get(EU_URL, timeout=30)))


def eu_merge(prev, got):
    """The new week, with the EU average's own history (one point a Monday, two years) kept from the earlier weeks."""
    if not got:
        return prev
    hist = [h for h in (prev or {}).get('h') or [] if h[0] != got['t']] + [[got['t'], *got['c']['EU']]]
    cut = (now().date() - timedelta(days=731)).isoformat()
    return {**got, 'h': sorted(h for h in hist if h[0] >= cut)}


# ---- the AI giants' weight in the S&P 500 (SPY's holdings) -----------------------------------------------------------

def spy_weights(rows):
    """SPY's holdings -> {'t': as-of date, 'w': {key: % of the fund}, 'ai': the basket's %, 'top10': the ten largest
    holdings' %, 'n': holdings}. SPY holds the S&P 500 at the index's own weights."""
    t = None
    for r in rows[:6]:
        m = re.search(r'(\d{1,2})-([A-Z][a-z]{2})-(\d{4})', ' '.join(str(v) for v in r.values()))
        if m and m.group(2) in EIA_MON:
            t = date(int(m.group(3)), EIA_MON[m.group(2)], int(m.group(1))).isoformat()
            break
    head = next((i for i, r in enumerate(rows) if str(r.get('B', '')).strip().lower() == 'ticker'), None)
    if head is None:
        return None
    cols = {str(v).strip().lower(): k for k, v in rows[head].items()}
    wcol = cols.get('weight')
    if not wcol:
        return None
    by = {}
    for r in rows[head + 1:]:
        tick, w = str(r.get('B') or '').strip().upper(), r.get(wcol)
        if tick and isinstance(w, float) and tick != '-':
            by[tick] = by.get(tick, 0) + w
    if len(by) < 400:
        return None      # not the whole index: a cut file or another fund
    w = {k: r4(sum(by.get(x, 0) for x in ticks)) if ticks else None for k, ticks in AI.items()}
    top = sorted(by.values(), reverse=True)
    return {'t': t, 'w': w, 'ai': r4(sum(v for v in w.values() if v)), 'top10': r4(sum(top[:10])), 'n': len(by)}


def fetch_spy():
    return spy_weights(xlsx_rows(get(SPY_URL, timeout=30)))


def spy_merge(prev, got):
    """The new day's weights and the basket's share by day (400 days) kept from the earlier days."""
    if not got:
        return prev
    day = got['t'] or now().date().isoformat()
    hist = [h for h in (prev or {}).get('h') or [] if h[0] != day] + [[day, got['ai']]]
    cut = (now().date() - timedelta(days=400)).isoformat()
    return {**got, 'h': sorted(h for h in hist if h[0] >= cut)}


# ---- US federal debt (the Treasury's Debt to the Penny) --------------------------------------------------------------

def debt_series(rows, days=400):
    """The Treasury's rows (newest first) -> {'v': dollars, 't': record date, 'g': average growth a day over the last
    year (dollars), 'h': [[date, billions], ...]}."""
    pts = []
    for r in rows:
        try:
            pts.append((r['record_date'], float(r['tot_pub_debt_out_amt'])))
        except (KeyError, TypeError, ValueError):
            continue
    pts.sort()
    if len(pts) < 2:
        return None
    last_d, last_v = pts[-1]
    end = date.fromisoformat(last_d)
    # the growth a day: the last figure against the one nearest a year earlier, so one big auction day weighs little
    base = min(pts, key=lambda p: abs((end - date.fromisoformat(p[0])).days - 365))
    span = (end - date.fromisoformat(base[0])).days
    g = (last_v - base[1]) / span if span > 0 else None
    cut = (end - timedelta(days=days)).isoformat()
    return {'v': round(last_v), 't': last_d, 'g': round(g) if g is not None else None, 'gd': span,
            'h': [[d, round(v / 1e9, 1)] for d, v in pts if d >= cut]}


def fetch_debt():
    return debt_series(json.loads(get(DEBT_URL, timeout=20)).get('data') or [])


# ---- government debt in % of GDP (IMF) -----------------------------------------------------------------------------

def imf_debt(d, year=None):
    """The IMF's DataMapper answer -> {'y': the last year shown, 'c': {code: [[year, %], ...]}} from 2000 to that year
    (the current year's figure is a projection, so the last full year is the newest shown)."""
    year = year or now().year - 1
    vals = ((d or {}).get('values') or {}).get('GGXWDG_NGDP') or {}
    out = {}
    for code in IMF_LAND:
        rows = sorted((int(y), v) for y, v in (vals.get(code) or {}).items()
                      if str(y).isdigit() and 2000 <= int(y) <= year and isinstance(v, (int, float)))
        if rows:
            out[code] = [[y, r4(v)] for y, v in rows]
    return {'y': year, 'c': out} if len(out) >= 5 else None


def fetch_imf():
    # the IMF's bot shield turns a browser-like agent away and lets Python's own in
    return imf_debt(json.loads(get(IMF_URL, {'User-Agent': 'Python-urllib/3'}, timeout=30)))


# ---- Danish pump prices --------------------------------------------------------------------------------------------

def product(name):
    n = (name or '').strip().lower()
    for key, names in PRODUCTS.items():
        if n in names:
            return key
    return None


def q8_city(address):
    """'Dronningemaen 34 Svendborg 5700 Danmark' -> 'Svendborg' (the words between the house number and postcode)."""
    m = re.match(r'^(.*?)\s(\d{4})\s+Danmark\s*$', address or '')
    if not m:
        return ''
    words = m.group(1).split()
    nums = [i for i, w in enumerate(words) if re.match(r'^\d+\w?$', w)]
    tail = words[nums[-1] + 1:] if nums else words[-1:]
    return ' '.join(tail).strip(' ,') or m.group(2)


def nice_city(s):
    s = (s or '').strip()
    return s.title() if s.isupper() else s


def fetch_circlek():
    d = json.loads(get('https://api.circlek.com/eu/prices/v1/fuel/countries/DK', {'X-App-Name': 'PRICES'}))
    out = []
    for site in d.get('sites', []):
        chain = 'INGO' if (site.get('name') or '').upper().startswith('INGO') else 'Circle K'
        prices, changed = {}, []
        for f in site.get('fuelPrices') or []:
            key = product(f.get('displayName'))
            if key and f.get('price'):
                prices[key] = float(f['price'])
                if f.get('lastUpdated'):
                    changed.append(f['lastUpdated'])
        if prices:
            out.append({'c': chain, 'city': nice_city((site.get('address') or {}).get('city')), 'p': prices,
                        'chg': max(changed) if changed else None})
    return out


def fetch_q8():
    d = json.loads(get('https://www.q8.dk/Station/GetStationPrices?page=1&pageSize=2000'))
    out = []
    for st in (d.get('data') or {}).get('stationsPrices') or []:
        chain = 'F24' if (st.get('stationName') or '').upper().startswith('F24') else 'Q8'
        prices, changed = {}, []
        for p in st.get('products') or []:
            key = product(p.get('productName'))
            if key and p.get('price'):
                prices[key] = float(p['price'])
                if p.get('priceChangeDate'):    # Danish local time without a zone
                    local = datetime.fromisoformat(p['priceChangeDate'])
                    offset = dk(local.replace(tzinfo=timezone.utc)).utcoffset()
                    changed.append((local - offset).replace(tzinfo=timezone.utc).isoformat())
        if prices:
            out.append({'c': chain, 'city': q8_city(st.get('address')), 'p': prices,
                        'chg': max(changed) if changed else None})
    return out


def summarize_pumps(stations):
    """Per chain: stations, list price (the most common price), cheapest price and where, last price change."""
    chains = []
    for chain in CHAINS:
        mine = [s for s in stations if s['c'] == chain]
        if not mine:
            continue
        prods = {}
        for key in PRODUCTS:
            vals = [(s['p'][key], s['city']) for s in mine if key in s['p']]
            if not vals:
                continue
            prices = [v for v, _ in vals]
            mode = Counter(prices).most_common(1)[0][0]
            low = min(prices)
            where = sorted({c for v, c in vals if v == low and c})
            prods[key] = {'v': mode, 'min': low, 'max': max(prices), 'n': len(prices), 'at': where[:3],
                          'nmin': sum(1 for v in prices if v == low), 'med': r4(statistics.median(prices))}
        # when the list price changed: the middle change time of the stations at the list price (one station's own
        # change is not the chain's)
        lead = 'benzin' if 'benzin' in prods else next(iter(prods), None)
        at_list = [s['chg'] for s in mine if s.get('chg') and lead and s['p'].get(lead) == prods[lead]['v']]
        changes = sorted(at_list or [s['chg'] for s in mine if s.get('chg')])
        chains.append({'c': chain, 'n': len(mine), 'chg': changes[len(changes) // 2] if changes else None, 'p': prods})
    return chains


def fetch_pumps():
    stations, ok = [], []
    for name, fn in (('circlek', fetch_circlek), ('q8', fetch_q8)):
        try:
            got = fn()
            if got:
                stations += got
                ok.append(name)
        except Exception:
            continue
    return (summarize_pumps(stations), ok) if stations else (None, ok)


# ---- derived series ------------------------------------------------------------------------------------------------

def join(fn, *series):
    """A new daily series from others on the dates they share: fn(*values) per date."""
    if any(not s for s in series):
        return None
    maps = [dict(s['h']) for s in series]
    days = sorted(set.intersection(*(set(m) for m in maps)))
    hist = [[d, r4(fn(*(m[d] for m in maps)))] for d in days]
    if not hist:
        return None
    return {'v': hist[-1][1], 't': min(s['t'] for s in series), 'h': hist}   # as old as its oldest part


def derive(s):
    g = s.get
    out = {
        # 3-2-1 crack: three barrels of WTI make two of gasoline and one of diesel; the refiner's gross margin per barrel
        'crack321': join(lambda w, r, u: (2 * r * GAL_BBL + u * GAL_BBL - 3 * w) / 3, g('wti'), g('rbob'), g('ulsd')),
        'crack_gas': join(lambda b, r: r * GAL_BBL - b, g('brent'), g('rbob')),
        'crack_diesel': join(lambda b, u: u * GAL_BBL - b, g('brent'), g('ulsd')),
        'brent_wti': join(lambda b, w: b - w, g('brent'), g('wti')),
        # physical Brent against the paper (futures) Brent on the same day: above 0 = cargoes are scarce
        'phys_prem': join(lambda sp, f: sp - f, g('brent_spot'), g('brent')),
        'brent_kr': join(lambda b, fx: b * fx / BBL_L, g('brent'), g('usddkk')),
        'rbob_kr': join(lambda r, fx: r * fx / GAL_L, g('rbob'), g('usddkk')),
        'ulsd_kr': join(lambda u, fx: u * fx / GAL_L, g('ulsd'), g('usddkk')),
    }
    return {k: v for k, v in out.items() if v}


def with_prev(x):
    """Add the previous day's value (p) for the change shown next to each price."""
    h = x.get('h') or []
    return {**x, 'p': h[-2][1] if len(h) >= 2 else None}


# ---- news ----------------------------------------------------------------------------------------------------------

def editor_titles(summaries):
    """The editor's checked headlines: article id -> headline, under the story's id and its members, the newest winning
    (a copy of run.editor_titles, which this stdlib-only step cannot import)."""
    out, at = {}, {}
    for k, v in ((summaries or {}).get('titles') or {}).items():
        if not isinstance(v, dict) or not v.get('title'):
            continue
        for i in [k, *(v.get('members') or [])]:
            if i not in out or str(v.get('at') or '') > at[i]:
                out[i], at[i] = v['title'], str(v.get('at') or '')
    return out


def energy_news(state, hours=72, limit=16, summaries=None, pattern=None):
    """Stories about oil, fuel and gas, newest first: those with the editor's headline and Danish outlets' own."""
    def load(name):
        try:
            return json.loads(Path(name if os.path.isabs(str(name)) else state / name).read_text(encoding='utf-8'))
        except Exception:
            return {}

    ed = editor_titles(load(summaries or os.environ.get('RADAR_SUMMARIES') or '__none__'))
    cut = now() - timedelta(hours=hours)
    seen, out = set(), []
    for it in load('data.json').get('items', []):
        text = ' '.join(x for x in (it.get('title'), it.get('title_tr'), it.get('title_da')) if x)
        if (pattern or NEWS).search(text) and it.get('id') not in seen:
            seen.add(it.get('id'))
            mine = next((ed[k] for k in [it.get('id'), *(it.get('members') or [])] if k in ed), None)
            if not mine and it.get('lang') != 'da':
                continue      # the machine's Danish of a foreign headline reads badly: only the editor's or a Danish outlet's
            # every version the app knows; the page picks by the reader's language setting, as the app does
            out.append({'i': it.get('id'), 'o': it.get('title'), 'en': it.get('title_tr'), 'da': it.get('title_da'),
                        'ed': mine, 'l': it.get('lang'), 'k': (it.get('kw_tr') if it.get('title_tr') else it.get('kw')) or [],
                        'kd': it.get('kw_da') or [], 's': it.get('source'), 'p': it.get('published') or it.get('found'),
                        'u': it.get('link'), 'n': it.get('outlets') or 1, 'big': bool(it.get('big'))})
    fresh = []
    for x in out:
        try:
            if (x['o'] or x['da']) and x['p'] and datetime.fromisoformat(x['p']) >= cut:
                fresh.append(x)
        except ValueError:
            continue
    fresh.sort(key=lambda x: x['p'], reverse=True)
    # one story once: a headline that shares two longer words with one shown already is the same news again
    # (a word's start and end, so 'olieraffinaderier' meets 'raffinaderier')
    words = lambda x: {p for w in re.findall(r'\w{5,}', (x['ed'] or x['o'] or '').lower()) for p in (w[:5], '-' + w[-6:])}  # noqa: E731
    shown = []
    for x in fresh:
        if not any(len(words(x) & words(y)) >= 3 for y in shown):
            shown.append(x)
    return shown[:limit]


# ---- one run -------------------------------------------------------------------------------------------------------

def due(prev, source, t):
    tried = (prev.get('tried') or {}).get(source)
    if tried and (t - datetime.fromisoformat(tried)).total_seconds() < RETRY - 30:
        return False      # it failed a moment ago: give it a rest
    last = (prev.get('ok') or {}).get(source)
    if not last:
        return True
    return (t - datetime.fromisoformat(last)).total_seconds() >= EVERY[source] - 30


# 'Uro i økonomien' keeps its own memory (the owner, 18/10: 'kan vi fylde uro i økonomien i retrospekt'): the stories
# of the last CRISIS_DAYS days – the radar's of the last four days added at every run to what the topic held, and the
# backward fill of config/crisis-seed.json – one story once, newest first
CRISIS_DAYS, CRISIS_MAX = 30, 40
SEED = Path(__file__).resolve().parents[2] / 'config' / 'crisis-seed.json'


def _stems(x):
    """A headline's longer words by their start and end, so 'olieraffinaderier' meets 'raffinaderier'."""
    return {p for w in re.findall(r'\w{5,}', (x.get('ed') or x.get('o') or '').lower()) for p in (w[:5], '-' + w[-6:])}


def crisis_seed(path=SEED):
    try:
        items = json.loads(Path(path).read_text(encoding='utf-8')).get('items') or []
    except (OSError, ValueError):
        return []
    return [{'i': x['i'], 'o': x.get('o'), 'en': None, 'da': None, 'ed': x.get('ed'), 'l': x.get('l', 'en'), 'k': [], 'kd': [],
             's': x.get('s'), 'p': x.get('p'), 'u': x.get('u'), 'n': 1, 'big': False}
            for x in items if isinstance(x, dict) and x.get('i') and x.get('p') and (x.get('ed') or x.get('o'))]


def crisis_archive(fresh, kept, seed, t=None, days=CRISIS_DAYS, limit=CRISIS_MAX):
    """The topic's list: the fresh stories first (their newest headline wins), then what it held and the seed – each
    story once (its id, its link, or three shared stems with one taken), none older than `days`, newest first."""
    cut = (t or now()) - timedelta(days=days)
    out, ids, links = [], set(), set()
    for x in [*fresh, *kept, *seed]:
        try:
            if not x.get('p') or datetime.fromisoformat(x['p']) < cut:
                continue
        except (ValueError, TypeError):
            continue
        # the same news again: its id, its link, or three shared stems with a story of the same two days (across a
        # month, two stories share words like 'stiger' and 'økonomien' without being one)
        when = datetime.fromisoformat(x['p'])
        if x.get('i') in ids or (x.get('u') and x['u'] in links) or any(
                abs((when - datetime.fromisoformat(y['p'])).total_seconds()) < 48 * 3600 and len(_stems(x) & _stems(y)) >= 3 for y in out):
            continue
        ids.add(x.get('i')), links.add(x.get('u'))
        out.append(x)
    out.sort(key=lambda x: x['p'], reverse=True)
    return out[:limit]


def run(state):
    path = state / 'energy.json'
    try:
        prev = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        prev = {}
    t = now()
    # the fetched series are the memory for the next run; derived ones are rebuilt from them every time
    raw = {k: v for k, v in (prev.get('s') or {}).items() if k in YAHOO or k in FRED or k in US_FUEL}
    ok = dict(prev.get('ok') or {})
    # a source that failed less than RETRY ago stays marked (due() skips it); one asked again now is marked anew below
    tried = {k: v for k, v in (prev.get('tried') or {}).items() if (t - datetime.fromisoformat(v)).total_seconds() < RETRY - 30}
    curve = prev.get('curve') or {}
    pumps = prev.get('pumps') or {}

    def ask(fetch):
        try:
            return fetch() or None
        except Exception:
            return None

    # the slow, rarely asked sources side by side, so a hanging one never holds up the others
    slow = {'usfuel': fetch_usfuel, 'eu': fetch_eu, 'spy': fetch_spy, 'debt': fetch_debt, 'imf': fetch_imf}
    slow = {k: fn for k, fn in slow.items() if due(prev, k, t)}
    with ThreadPoolExecutor(max(1, len(slow))) as ex:
        pending = {k: ex.submit(ask, fn) for k, fn in slow.items()}
        if due(prev, 'markets', t):
            got = fetch_markets()
            raw.update(got)
            if got:
                ok['markets'] = t.isoformat()
            else:
                tried['markets'] = t.isoformat()
        answers = {k: f.result() for k, f in pending.items()}
    for k in slow:
        if answers[k]:
            ok[k] = t.isoformat()
        else:
            tried[k] = t.isoformat()
    raw.update(answers.get('usfuel') or {})
    eu = eu_merge(prev.get('eu'), answers.get('eu'))
    spy = spy_merge(prev.get('spy'), answers.get('spy'))
    debt = answers.get('debt') or prev.get('debt')
    imf = answers.get('imf') or prev.get('imf')
    if due(prev, 'curve', t):
        fronts = {k: int(datetime.fromisoformat(raw[k]['t']).timestamp()) for k in CURVES if raw.get(k)}
        got = fetch_curves(fronts)
        if got:
            curve = {**curve, **got}
            ok['curve'] = t.isoformat()
        else:
            tried['curve'] = t.isoformat()
    if due(prev, 'fred', t):
        got = fetch_fred()
        raw.update(got)
        if got:
            ok['fred'] = t.isoformat()
        else:
            tried['fred'] = t.isoformat()
    if due(prev, 'pumps', t):
        chains, sources = fetch_pumps()
        if chains:
            # one point a day per chain (the latest list price), kept for 400 days
            today = dk(t).date().isoformat()
            day = {c['c']: {k: c['p'][k]['v'] for k in ('benzin', 'diesel') if k in c['p']} for c in chains}
            hist = [h for h in pumps.get('h') or [] if h[0] != today] + [[today, day]]
            cut = (t.date() - timedelta(days=400)).isoformat()
            pumps = {'t': t.isoformat(), 'chains': chains, 'src': sources, 'h': [h for h in hist if h[0] >= cut]}
            ok['pumps'] = t.isoformat()
        else:
            tried['pumps'] = t.isoformat()

    series = {k: with_prev(v) for k, v in {**raw, **derive(raw)}.items()}
    out = {
        'updated': t.isoformat(),
        'ok': ok,
        'tried': tried,
        's': series,
        'curve': curve,
        'pumps': pumps,
        'eu': eu,
        'spy': spy,
        'debt': debt,
        'imf': imf,
        'news': energy_news(state),
        # the economy page's 'Uro i økonomien', with its memory of 30 days and the backward fill
        'crisis': crisis_archive(energy_news(state, hours=96, limit=12, pattern=CRISIS), prev.get('crisis') or [], crisis_seed(), t),
    }
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out


def main():
    state = Path(os.environ.get('RADAR_STATE', Path(__file__).resolve().parents[2] / 'state'))
    state.mkdir(parents=True, exist_ok=True)
    out = run(state)
    missing = sorted(k for k in [*YAHOO, *FRED, *US_FUEL] if k not in out['s'])
    print(f"energy: {len(out['s'])} series{' (missing ' + ', '.join(missing) + ')' if missing else ''}, "
          f"curves {sorted(out['curve'])}, pumps {len((out['pumps'] or {}).get('chains') or [])} chains, "
          f"eu {bool(out['eu'])}, spy {bool(out['spy'])}, debt {bool(out['debt'])}, "
          f"imf {len(((out['imf'] or {}).get('c')) or {})} lands, {len(out['news'])} news, ok {sorted(out['ok'])}, "
          f"failed {sorted(out['tried'])}, {path_size(state)} bytes")


def path_size(state):
    try:
        return (state / 'energy.json').stat().st_size
    except OSError:
        return 0


if __name__ == '__main__':
    main()
