"""Energy prices for khabar.nu/energi: crude, products, crack spreads, gas, Danish pump prices and energy news.

Runs after every radar pass (radar.yml) and writes `energy.json` into the state folder, which is saved on the data
branch the page reads. Stdlib only. Every source has its own clock (EVERY) and a failed fetch keeps the last good
numbers, so one source being down never blanks the page.

Sources (all free and open):
- futures, gas and USD/DKK: Yahoo Finance chart API (NYMEX/ICE prices, ~10 min delayed), daily closes for 6 months;
  the Brent and WTI curves from the individual contract months
- physical spot prices: EIA's daily series (Brent FOB, WTI Cushing, New York Harbor gasoline and diesel, Gulf Coast
  jet fuel, Henry Hub), a few days behind – from EIA's own history pages, else from FRED (FRED does not answer
  GitHub's runners); a source that fails is tried again after RETRY, not on every pass
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
EVERY = {'markets': 4 * 60, 'curve': 30 * 60, 'fred': 3 * 3600, 'pumps': 20 * 60}
RETRY = 30 * 60     # a source that failed is asked again after half an hour, so a dead one never slows every pass

YAHOO = {               # key -> symbol; prices in the exchange's unit
    'brent': 'BZ=F',    # Brent, front month, $/bbl
    'wti': 'CL=F',      # WTI, front month, $/bbl
    'rbob': 'RB=F',     # RBOB gasoline (New York Harbor), $/gal
    'ulsd': 'HO=F',     # ULSD diesel (New York Harbor), $/gal
    'hh': 'NG=F',       # Henry Hub natural gas, $/MMBtu
    'ttf': 'TTF=F',     # Dutch TTF gas, EUR/MWh
    'usddkk': 'DKK=X',  # kroner per dollar
}
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
            return {'v': r4(price), 't': datetime.fromtimestamp(at, timezone.utc).isoformat(),
                    'h': sorted(hist.items())}
        except Exception:
            continue
    return None


def fetch_markets():
    with ThreadPoolExecutor(8) as ex:
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
    try:
        html = get(f'https://www.eia.gov/dnav/{n.lower()}/hist/LeafHandler.ashx?n={n}&s={sid}&f=D', timeout=15).decode('utf-8', 'replace')
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


def energy_news(state, hours=72, limit=16, summaries=None):
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
        if NEWS.search(text) and it.get('id') not in seen:
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


def run(state):
    path = state / 'energy.json'
    try:
        prev = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        prev = {}
    t = now()
    # the fetched series are the memory for the next run; derived ones are rebuilt from them every time
    raw = {k: v for k, v in (prev.get('s') or {}).items() if k in YAHOO or k in FRED}
    ok = dict(prev.get('ok') or {})
    # a source that failed less than RETRY ago stays marked (due() skips it); one asked again now is marked anew below
    tried = {k: v for k, v in (prev.get('tried') or {}).items() if (t - datetime.fromisoformat(v)).total_seconds() < RETRY - 30}
    curve = prev.get('curve') or {}
    pumps = prev.get('pumps') or {}

    if due(prev, 'markets', t):
        got = fetch_markets()
        raw.update(got)
        if got:
            ok['markets'] = t.isoformat()
        else:
            tried['markets'] = t.isoformat()
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
        'news': energy_news(state),
    }
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out


def main():
    state = Path(os.environ.get('RADAR_STATE', Path(__file__).resolve().parents[2] / 'state'))
    state.mkdir(parents=True, exist_ok=True)
    out = run(state)
    print(f"energy: {len(out['s'])} series, curves {sorted(out['curve'])}, "
          f"pumps {len((out['pumps'] or {}).get('chains') or [])} chains, {len(out['news'])} news, ok {out['ok']}")


if __name__ == '__main__':
    main()
