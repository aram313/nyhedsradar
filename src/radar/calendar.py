"""The Kalender tab's planned events (the owner, 2026-10-17: "en kalender, som viser fremtidige begivenheder … man kan
se i kalenderen, hvad der skal til at ske snart, af planlagte begivenheder", in a tab of its own; the Islamic dates left out at his wish the same day).

Runs after every radar pass (radar.yml, after the energy step) and writes `calendar.json` into the state folder, which
is saved on the data branch the app reads. Stdlib only. Every source has its own clock (EVERY: a day is plenty) and a
failed one rests (RETRY) and keeps its last good items, as energy.py does, so one source being down never blanks the
tab. The editor's own entries from the news are another file (kalender.json on the digest branch, scripts/editor.py);
the app merges the two.

Sources:
- elections: Wikipedia's "<year> national electoral calendar" for this year and the next two, through the MediaWiki API
  (action=parse), kept to the countries of geopolitical weight to the group (COUNTRIES: every Muslim-majority state, the
  great powers, the EU states, Israel, Ukraine, Brazil); a month only, or 'by'/'no later than', is 'forventet'
- the Fed's FOMC meetings (federalreserve.gov) and the ECB's monetary policy meetings (ecb.europa.eu): the decision day
- the summits and fixed dates of config/calendar.json (curated, each with its source)

Every text is Danish and reality only: what happens, where, and one factual line on why it matters – never a forecast.
"""
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from radar.stats import dk

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'config' / 'calendar.json'
# Wikimedia asks for a descriptive agent; no person's name or address in it
UA = 'KhabarCalendar/1.0 (https://khabar.nu; news app calendar of planned events)'
EVERY = {'wiki': 24 * 3600, 'fed': 24 * 3600, 'ecb': 24 * 3600}
RETRY = 3 * 3600        # a source that failed is asked again after three hours
PAST = 30               # days of past events kept (the tab's 'Tidligere')
WIKI_API = 'https://en.wikipedia.org/w/api.php'
FED_URL = 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
ECB_URL = 'https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html'

MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                      'September', 'October', 'November', 'December'], 1)}
SHORT = {m[:3]: i for m, i in MONTHS.items()}

# English name on Wikipedia -> Danish name: the countries of geopolitical weight to the group (the owner's choice,
# 17/10): every Muslim-majority state, the great powers, the EU states, Israel (written “israel”), Ukraine, Russia,
# India, Pakistan, Brazil, Turkey and Iran
COUNTRIES = {
    # Muslim-majority states
    'Afghanistan': 'Afghanistan', 'Albania': 'Albanien', 'Algeria': 'Algeriet', 'Azerbaijan': 'Aserbajdsjan',
    'Bahrain': 'Bahrain', 'Bangladesh': 'Bangladesh', 'Bosnia and Herzegovina': 'Bosnien-Hercegovina', 'Brunei': 'Brunei',
    'Burkina Faso': 'Burkina Faso', 'Chad': 'Tchad', 'Comoros': 'Comorerne', 'Djibouti': 'Djibouti', 'Egypt': 'Egypten',
    'Gambia': 'Gambia', 'The Gambia': 'Gambia', 'Guinea': 'Guinea', 'Indonesia': 'Indonesien', 'Iran': 'Iran',
    'Iraq': 'Irak', 'Jordan': 'Jordan', 'Kazakhstan': 'Kasakhstan', 'Kosovo': 'Kosovo', 'Kuwait': 'Kuwait',
    'Kyrgyzstan': 'Kirgisistan', 'Lebanon': 'Libanon', 'Libya': 'Libyen', 'Malaysia': 'Malaysia', 'Maldives': 'Maldiverne',
    'Mali': 'Mali', 'Mauritania': 'Mauretanien', 'Morocco': 'Marokko', 'Niger': 'Niger', 'Nigeria': 'Nigeria',
    'Oman': 'Oman', 'Pakistan': 'Pakistan', 'Palestine': 'Palæstina', 'State of Palestine': 'Palæstina',
    'Qatar': 'Qatar', 'Saudi Arabia': 'Saudi-Arabien', 'Senegal': 'Senegal', 'Sierra Leone': 'Sierra Leone',
    'Somalia': 'Somalia', 'Sudan': 'Sudan', 'Syria': 'Syrien', 'Tajikistan': 'Tadsjikistan', 'Tunisia': 'Tunesien',
    'Turkey': 'Tyrkiet', 'Türkiye': 'Tyrkiet', 'Turkmenistan': 'Turkmenistan',
    'United Arab Emirates': 'De Forenede Arabiske Emirater', 'Uzbekistan': 'Usbekistan', 'Yemen': 'Yemen',
    # the EU states
    'Austria': 'Østrig', 'Belgium': 'Belgien', 'Bulgaria': 'Bulgarien', 'Croatia': 'Kroatien', 'Cyprus': 'Cypern',
    'Czech Republic': 'Tjekkiet', 'Czechia': 'Tjekkiet', 'Denmark': 'Danmark', 'Estonia': 'Estland', 'Finland': 'Finland',
    'France': 'Frankrig', 'Germany': 'Tyskland', 'Greece': 'Grækenland', 'Hungary': 'Ungarn', 'Ireland': 'Irland',
    'Italy': 'Italien', 'Latvia': 'Letland', 'Lithuania': 'Litauen', 'Luxembourg': 'Luxembourg', 'Malta': 'Malta',
    'Netherlands': 'Holland', 'Poland': 'Polen', 'Portugal': 'Portugal', 'Romania': 'Rumænien', 'Slovakia': 'Slovakiet',
    'Slovenia': 'Slovenien', 'Spain': 'Spanien', 'Sweden': 'Sverige',
    # the great powers and the others of weight
    'United States': 'USA', 'China': 'Kina', 'Russia': 'Rusland', 'United Kingdom': 'Storbritannien', 'Japan': 'Japan',
    'India': 'Indien', 'Brazil': 'Brasilien', 'Ukraine': 'Ukraine', 'Israel': '“israel”',
}

# the office an entry names -> the kind of election (local and regional ones are left out)
REFERENDUM = re.compile(r'referend', re.I)
PRESIDENT = re.compile(r'\bpresiden', re.I)
PARLIAMENT = re.compile(r'parliament|house of|national assembly|chamber|senate|legislat|knesset|bundestag|sejm|majlis|'
                        r'council of states|national council|general election|lok sabha|duma|grand national|riksdag|'
                        r'folketing|cortes|assembly|congress|diet\b|storting|sabor|seimas|saeima|riigikogu|eduskunta|'
                        r'althing|dáil|dail|national people|kurultai|mazhilis|jatiya|shura|sansad|representatives|deputies', re.I)
LOCAL = re.compile(r'\b(?:local|municipal|regional|provincial|gubernatorial|governor|mayor|state legislat|county|city|'
                   r'cantonal|prefectur)', re.I)
ROUND = re.compile(r'\((1st|2nd|first|second) round\)', re.I)


def now():
    return datetime.now(timezone.utc)


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def slug(text):
    t = text.lower().translate(str.maketrans({'æ': 'ae', 'ø': 'oe', 'å': 'aa', 'ü': 'u', 'ö': 'o', 'é': 'e', '“': '', '”': ''}))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def plain(fragment):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


# ---- elections: Wikipedia's national electoral calendar ----------------------------------------------------------

def wiki_url(year):
    q = {'action': 'parse', 'page': f'{year}_national_electoral_calendar', 'prop': 'text', 'format': 'json',
         'formatversion': '2', 'redirects': '1'}
    return WIKI_API + '?' + urllib.parse.urlencode(q)


def wiki_html(payload):
    """The page's HTML from the API's answer; '' for a page that does not exist (yet), None for anything else."""
    d = json.loads(payload) if isinstance(payload, str) else payload
    if (d.get('error') or {}).get('code') == 'missingtitle':
        return ''
    text = (d.get('parse') or {}).get('text')
    if isinstance(text, dict):
        text = text.get('*')
    return text if isinstance(text, str) else None


def wiki_date(prefix, month, year):
    """('YYYY-MM-DD' or 'YYYY-MM', approx, end) from an entry's date prefix ('3 October', '9–10 October', 'October',
    'By 30 October', 'No later than 5 May'); None when it names no day or month of its section."""
    p = ' '.join(prefix.replace('–', '-').replace('—', '-').split())
    by = bool(re.match(r'(?:by|no later than|before|not later than)\b', p, re.I))
    soft = bool(re.match(r'(?:early|mid|late|expected|tentative|around|circa|c\.)\b', p, re.I))
    m = re.search(r'(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s+([A-Z][a-z]+)', p)
    if m and m.group(3) in MONTHS:
        mo = MONTHS[m.group(3)]
        try:
            d = date(year, mo, int(m.group(1)))
            end = date(year, mo, int(m.group(2))) if m.group(2) else None
        except ValueError:
            return None
        return d.isoformat(), by or soft, (end.isoformat() if end and end > d else None)
    m = re.search(r'\b([A-Z][a-z]+)\b', p)
    if m and m.group(1) in MONTHS:
        return f'{year}-{MONTHS[m.group(1)]:02d}', True, None
    if month:
        return f'{year}-{month:02d}', True, None
    return None


def office_kind(office):
    """The Danish name of the election an entry's office names, or None for a local or regional one."""
    o = office or ''
    if REFERENDUM.search(o):
        return 'Folkeafstemning'
    if LOCAL.search(o) and not PARLIAMENT.search(o) and not PRESIDENT.search(o):
        return None
    pres, parl = PRESIDENT.search(o), PARLIAMENT.search(o)
    if pres and parl:
        return 'Præsident- og parlamentsvalg'
    if pres:
        return 'Præsidentvalg'
    if re.fullmatch(r'\s*senate(?:\s*\([^)]*\))?\s*', o, re.I):   # the senate alone ('Senate (1st round)')
        return 'Senatsvalg'
    if parl:
        return 'Parlamentsvalg'
    return 'Valg'


WHY = {'Folkeafstemning': 'Folkeafstemning på nationalt plan.', 'Præsidentvalg': 'Valg af præsident.',
       'Præsident- og parlamentsvalg': 'Valg af præsident og parlament.', 'Senatsvalg': 'Valg til senatet.',
       'Parlamentsvalg': 'Valg til det nationale parlament.', 'Valg': 'Nationalt valg.'}


def parse_wiki(page_html, year):
    """Every national election of the page in a country of weight: dicts in the calendar's shape."""
    out, seen = [], set()
    text = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>', '', page_html, flags=re.S)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S)
    parts = re.split(r'<h2 id="([^"]+)"', text)
    for k in range(1, len(parts), 2):
        section, body = parts[k], parts[k + 1]
        month = MONTHS.get(section)
        if not month:
            continue   # 'Unknown_date', 'Indirect_elections', 'See_also', 'References'
        prefix = None
        for li in re.finditer(r'<li>(.*?)(?=<li>|</ul>|<ul>)', body, re.S):
            raw = li.group(1)
            head = re.match(r'\s*([^<:]{1,60}):\s*', raw)
            if head:
                prefix = html.unescape(head.group(1))
                raw = raw[head.end():]
            if '<a ' not in raw:
                continue   # a date whose elections follow in a nested list
            if raw.lstrip().startswith('<i>'):
                continue   # a state the page sets in italics (not generally recognised)
            links = re.findall(r'<a\s+([^>]*)>(.*?)</a>', raw, re.S)
            if len(links) < 1:
                continue
            country = plain(links[0][1])
            da = COUNTRIES.get(country)
            if not da:
                continue
            office = plain(links[1][1]) if len(links) > 1 else plain(raw.split('</a>', 1)[-1]).lstrip(', ')
            kind = office_kind(office)
            if not kind:
                continue
            when = wiki_date(prefix or '', month, year)
            if not when:
                continue
            day, approx, end = when
            r = ROUND.search(office)
            rnd = f" ({'1' if r.group(1).lower() in ('1st', 'first') else '2'}. runde)" if r else ''
            href = re.search(r'href="([^"]+)"', links[1][0]) if len(links) > 1 else None
            link = ('https://en.wikipedia.org' + html.unescape(href.group(1))) if href and href.group(1).startswith('/wiki/') else \
                f'https://en.wikipedia.org/wiki/{year}_national_electoral_calendar'
            by = bool(re.match(r'\s*(?:by|no later than|not later than|before)\b', prefix or '', re.I))
            title = f'{kind} i {da}{rnd}' + (' (senest)' if by else '')
            ident = f'valg-{slug(da)}-{day}-{slug(kind)}{"-r" + rnd[2] if rnd else ""}'
            if ident in seen:
                continue
            seen.add(ident)
            item = {'id': ident, 'date': day, 'title': title, 'kind': 'valg', 'place': da, 'why': WHY[kind],
                    'link': link, 'src': 'wiki'}
            if end:
                item['end'] = end
            if approx:
                item['approx'] = True
            out.append(item)
    return out


def fetch_wiki(year):
    page = wiki_html(get(wiki_url(year)))
    if page is None:
        raise ValueError('no page text')
    return parse_wiki(page, year)


# ---- the central banks -------------------------------------------------------------------------------------------

def parse_fomc(page):
    """The FOMC's meetings as their decision day (the last day of the meeting)."""
    out = []
    panels = re.split(r'<h4><a id="\d+">(\d{4}) FOMC Meetings</a></h4>', page)
    for k in range(1, len(panels), 2):
        year, body = int(panels[k]), panels[k + 1]
        for mon, days in re.findall(r'fomc-meeting__month[^>]*><strong>([^<]+)</strong>\s*</div>\s*'
                                    r'<div class="fomc-meeting__date[^>]*>([^<]+)<', body):
            names = [m.strip()[:3] for m in mon.split('/')]
            nums = re.findall(r'\d{1,2}', days)
            if not nums or names[-1] not in SHORT:
                continue
            last_month = SHORT[names[-1]]
            if 'unscheduled' in days.lower() or 'notation' in days.lower():
                continue
            try:
                d = date(year, last_month, int(nums[-1]))
            except ValueError:
                continue
            sep = '*' in days
            out.append({'id': f'fed-{d.isoformat()}', 'date': d.isoformat(), 'title': 'Fed: rentebeslutning',
                        'kind': 'centralbank', 'place': 'USA',
                        'why': "Den amerikanske centralbank fastsætter USA's styringsrente efter et todages møde"
                               + (' og offentliggør nye økonomiske fremskrivninger.' if sep else '.'),
                        'link': FED_URL, 'src': 'fed'})
    return out


def parse_ecb(page):
    """The ECB's monetary policy meetings as their decision day (the meeting's last day, with the press conference)."""
    days = []
    for dt, dd in re.findall(r'<dt>\s*(\d{2}/\d{2}/\d{4})\s*</dt>\s*<dd>(.*?)</dd>', page, re.S):
        what = plain(dd).lower()
        if 'monetary policy meeting' not in what or 'non-monetary' in what:
            continue
        d, m, y = (int(x) for x in dt.split('/'))
        days.append(date(y, m, d))
    out, group = [], []
    for d in sorted(set(days)) + [None]:
        if group and (d is None or (d - group[-1]).days > 1):
            last = group[-1]
            out.append({'id': f'ecb-{last.isoformat()}', 'date': last.isoformat(), 'title': 'ECB: rentebeslutning',
                        'kind': 'centralbank', 'place': 'Eurozonen',
                        'why': 'Den Europæiske Centralbank fastsætter eurozonens renter; Danmarks Nationalbank følger '
                               'normalt ECB, når den ændrer renten.',
                        'link': ECB_URL, 'src': 'ecb'})
            group = []
        if d is not None:
            group.append(d)
    return out


def fetch_fed():
    return parse_fomc(get(FED_URL))


def fetch_ecb():
    return parse_ecb(get(ECB_URL))


# ---- the curated summits and fixed dates -------------------------------------------------------------------------

def curated(path=CONFIG):
    """config/calendar.json's events (each with its verified source), in the calendar's shape."""
    try:
        cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    out = []
    for e in cfg.get('events') or []:
        if not isinstance(e, dict) or not e.get('id') or not e.get('date') or not e.get('title') or not e.get('link'):
            continue
        out.append({k: e[k] for k in ('id', 'date', 'end', 'approx', 'title', 'kind', 'place', 'why', 'link') if e.get(k)}
                   | {'src': 'fast'})
    return out


# ---- one run -----------------------------------------------------------------------------------------------------

def due(prev, source, t, every):
    tried = (prev.get('tried') or {}).get(source)
    if tried and (t - datetime.fromisoformat(tried)).total_seconds() < RETRY - 30:
        return False      # it failed a moment ago: give it a rest
    last = (prev.get('ok') or {}).get(source)
    if not last:
        return True
    return (t - datetime.fromisoformat(last)).total_seconds() >= every - 30


def last_day(item):
    """The last day an event lasts (a month only: its last day)."""
    d = item.get('end') or item['date']
    if len(d) == 7:
        y, m = int(d[:4]), int(d[5:7])
        return date(y + m // 12, m % 12 + 1, 1) - timedelta(days=1)
    return date.fromisoformat(d)


def merge(groups, today):
    """All sources as one list, the past beyond PAST days left out: a curated event wins over Wikipedia's election on
    the same day in the same country, each id once, sorted by day."""
    fixed = {(e['date'], e.get('place')) for e in groups.get('fast') or [] if e.get('kind') in ('valg', 'dansk')}
    out, seen = [], set()
    for src in ('fast', 'fed', 'ecb', *sorted(k for k in groups if k.startswith('wiki'))):
        for e in groups.get(src) or []:
            if e['id'] in seen or last_day(e) < today - timedelta(days=PAST):
                continue
            if src.startswith('wiki') and (e['date'], e.get('place')) in fixed:
                continue
            seen.add(e['id'])
            out.append(e)
    return sorted(out, key=lambda e: (e['date'] if len(e['date']) > 7 else e['date'] + '-32', e['id']))


# How much an event weighs (the owner, 17/10: "vægte de begivenheder … der har højeste betydning med en indikator eller
# en baggrundsfarve"): 3 the events that move the balance of the powers or the group's own country – elections in the
# great powers and the states at the centre of the Muslim world, Denmark's general election, the summits where the
# powers meet; 2 the elections in the rest of the Muslim world, the Fed (the dollar and oil), OPEC+, the G7, the SCO,
# the Arab League and the OIC; 1 the rest. A curated or editor's entry may set its own `w`.
HEAVY_STATES = {'USA', 'Kina', 'Rusland', 'Storbritannien', 'Frankrig', 'Tyskland', 'Indien', 'Ukraine', '“israel”',
                'Tyrkiet', 'Iran', 'Egypten', 'Pakistan', 'Saudi-Arabien', 'Irak', 'Syrien', 'Palæstina', 'Danmark'}
MUSLIM_STATES = set(list(COUNTRIES.values())[:list(COUNTRIES).index('Austria')])
HEAVY_SUMMIT = re.compile(r'\b(?:G20|NATO|BRICS|FN|Generalforsamling)', re.I)
# the EU summits weigh 2 (the owner, 17/10): what they decide binds Denmark – asylum, borders, terror laws – and they
# settle the sanctions on Russia, the money for Ukraine, the trade agreement with “israel”; the editor raises one to 3
# when its agenda holds such a decision
MID_SUMMIT = re.compile(r'\b(?:G7|OPEC|SCO|Shanghai|Arabiske Liga|OIC|Islamisk Samarbejde|EU-topmøde|Det Europæiske Råd)', re.I)
# a head of state the parliament elects, whose office is ceremonial: not an election that moves a power
CEREMONIAL = {('Præsidentvalg', 'Indien'), ('Præsidentvalg', 'Tyskland'), ('Præsidentvalg', '“israel”'), ('Præsidentvalg', 'Irak')}


def weight(e):
    if e.get('w') in (1, 2, 3):
        return e['w']
    kind, title, place = e.get('kind'), e.get('title') or '', e.get('place') or ''
    if kind in ('valg', 'dansk') and 'Folketingsvalg' in title:
        return 3
    if kind == 'valg':
        if any(title.startswith(k) and p in place for k, p in CEREMONIAL):
            return 1
        heavy = any(s in place for s in HEAVY_STATES)
        if heavy and not re.search(r'\bSenat|Folkeafstemning', title):
            return 3
        if heavy or any(s in place for s in MUSLIM_STATES):
            return 2
        return 1
    if kind == 'topmøde':
        if re.search(r'klima|COP\d', title):
            return 1     # the climate summits move no power's position
        return 3 if HEAVY_SUMMIT.search(title) else 2 if MID_SUMMIT.search(title) else 1
    if kind == 'centralbank':
        return 2 if title.startswith('Fed') else 1
    return 1


WHY_FILE = ROOT / 'config' / 'calendar-why.json'


def why_rules(path=WHY_FILE):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8')).get('rules') or []
    except Exception:
        return []


def deeper(e, rules):
    """The fuller explanation of an event of weight 2 or 3 (config/calendar-why.json, the owner 17/10); an editor's own
    'why' and an event of weight 1 keep theirs."""
    if e.get('w', 1) < 2 or e.get('src') == 'ed':
        return e
    place, title = e.get('place') or '', e.get('title') or ''
    for r in rules:
        if r.get('kind') != e.get('kind'):
            continue
        if r.get('place') and r['place'] not in place:
            continue
        if r.get('title') and not re.search(r['title'], title):
            continue
        if r.get('muslim') and not any(s in place for s in MUSLIM_STATES):
            continue
        return {**e, 'why': r['why'].replace('{place}', place)}
    return e


def run(state, fetchers=None, t=None):
    path = state / 'calendar.json'
    try:
        prev = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        prev = {}
    t = t or now()
    today = dk(t).date()   # the Danish day
    ok = dict(prev.get('ok') or {})
    tried = {k: v for k, v in (prev.get('tried') or {}).items() if (t - datetime.fromisoformat(v)).total_seconds() < RETRY - 30}
    groups = {k: v for k, v in (prev.get('src') or {}).items() if isinstance(v, list)}
    fetchers = fetchers or {**{f'wiki{y}': (lambda y=y: fetch_wiki(y)) for y in (today.year, today.year + 1, today.year + 2)},
                            'fed': fetch_fed, 'ecb': fetch_ecb}
    for key, fetch in fetchers.items():
        every = EVERY['wiki' if key.startswith('wiki') else key]
        if not due(prev, key, t, every):
            continue
        try:
            got = fetch()
        except Exception:
            got = None
        # a page with no events of weight is an answer; an empty list from a bank's page is not
        if got is None or (not got and key in ('fed', 'ecb')):
            tried[key] = t.isoformat()
        else:
            groups[key] = got
            ok[key] = t.isoformat()
            tried.pop(key, None)
    groups = {k: v for k, v in groups.items() if k in fetchers}   # last year's Wikipedia page leaves with its year
    groups['fast'] = curated()
    rules = why_rules()
    items = [deeper({**e, 'w': weight(e)}, rules) for e in merge(groups, today)]
    out = {'updated': t.isoformat(), 'ok': ok, 'tried': tried,
           'src': {k: v for k, v in groups.items() if k != 'fast'}, 'items': items}
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out


def main():
    state = Path(os.environ.get('RADAR_STATE', ROOT / 'state'))
    state.mkdir(parents=True, exist_ok=True)
    out = run(state)
    kinds = {}
    for e in out['items']:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    srcs = {}
    for e in out['items']:
        srcs[e['src']] = srcs.get(e['src'], 0) + 1
    print(f"calendar: {len(out['items'])} events {dict(sorted(kinds.items()))}, by source {dict(sorted(srcs.items()))}, "
          f"ok {sorted(out['ok'])}, failed {sorted(out['tried'])}")


if __name__ == '__main__':
    main()
