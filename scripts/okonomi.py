"""The economy editor's day on the Økonomi page (the owner, 18/10: 'kan vi erstatte en af senior kørslerne i løbet af
dagen som kan kigge på økonomi og kalender siden? tilføje kontekst forbedre layout og gøre det mere livligt. en gang om
dagen er nok til det. dette er dog primært til økonomi siden').

The page's numbers come from the radar every five minutes (src/radar/energy.py); what they lacked is the news behind
them. Once a day the economy editor writes `okonomi` in its update, which `editor.py publish` checks here and keeps as
okonomi.json on the digest branch:

- `dag`: two or three sentences at the top of 'Lige nu' – what moved the economy today, as the news tell it;
- `emner`: for a topic (fuel, oil, mkt, ai, debt, raw, kris), one or two sentences under its headline and up to three
  stories shown under its figures ('I nyhederne');
- `kommende`: up to four planned economic events of the next fortnight from the calendar ('Det kommer');
- `citat`: the day's statement on the economy – a central banker, a finance minister, OPEC, the IMF ('Dagens citat').

Every text is reality, as the event pages are: who did or said what, each number standing in a story it cites, no
judgement, no forecast and no advice to buy or sell; the outlets it rests on are named under it. The radar's energy step
reads the file (RADAR_OKONOMI) and puts it, with the stories' records, in energy.json for the page (`ed`).
"""
import re
from datetime import datetime, timedelta

import events as event_pages

TOPICS = {'fuel': 'Brændstof', 'oil': 'Olie og gas', 'mkt': 'Markeder', 'ai': 'AI-boblen', 'debt': 'Gæld',
          'raw': 'Råvarer', 'kris': 'Finans og økonomi'}
DAG_TEXT, TOPIC_TEXT, STORIES, COMING, AHEAD_DAYS = 420, 300, 3, 4, 14
# the figures the input shows, by topic, with the page's own Danish names
FIGURES = {
    'oil': [('brent', 'Brent', '$/tønde'), ('wti', 'WTI', '$/tønde'), ('ulsd', 'Diesel (ULSD)', '$/gal.'), ('ttf', 'TTF-gas', '€/MWh'),
            ('hh', 'Henry Hub-gas', '$/MMBtu'), ('crack_diesel', 'Raffineringsmargin diesel', '$/tønde')],
    'mkt': [('spx', 'S&P 500', ''), ('ndx', 'Nasdaq 100', ''), ('sx5e', 'Euro Stoxx 50', ''), ('c25', 'C25', ''), ('n225', 'Nikkei 225', ''),
            ('sse', 'Shanghai', ''), ('vix', 'VIX', ''), ('tnx', 'USA 10-årig rente', '%'), ('dxy', 'Dollarindeks', ''),
            ('usddkk', 'Dollar i kroner', 'kr.')],
    'ai': [('nvda', 'Nvidia', '$'), ('tsm', 'TSMC', '$'), ('msft', 'Microsoft', '$'), ('googl', 'Alphabet', '$'), ('meta', 'Meta', '$'),
           ('amzn', 'Amazon', '$'), ('aapl', 'Apple', '$'), ('avgo', 'Broadcom', '$')],
    'raw': [('gold', 'Guld', '$/oz'), ('copper', 'Kobber', '$/lb'), ('wheat', 'Hvede', '¢/bu'), ('btc', 'Bitcoin', '$')],
}
# the economy beyond the page's own news patterns (energy.NEWS, energy.CRISIS): markets, central banks, the AI giants,
# metals and currencies – what the figures of Markeder, AI-boblen and Råvarer move with
MARKETS = re.compile(r"(?<![\w-])(wall street|stocks?|shares|equities|aktie\w*|børs\w*|nasdaq|s&p|dow jones|nikkei|"
                     r"federal reserve|the fed|fed chair|centralbank\w*|central bank\w*|nationalbank\w*|interest rates?|"
                     r"rentestigning\w*|rentenedsættelse\w*|styringsrente\w*|nvidia|tsmc|semiconductor\w*|chips?|"
                     r"gold|guld\w*|bitcoin|dollar\w*|yuan|renminbi|copper|kobber|wheat|hvede|gdp|bnp|economy|"
                     r"økonomi\w*|vækst\w*|arbejdsløshed\w*|unemployment|jobs report)(?![\w-])", re.I)
# no advice: Khabar tells what the markets did, never what a reader should do with money (the page's foot says so)
ADVICE = re.compile(r'\b(?:(?:køb|sælg|invester)(?: nu| op| ud| i)\b|bør (?:købe|sælge|investere|placere)\b|anbefal\w*|'
                    r'godt tidspunkt at\b|kan betale sig at (?:købe|sælge|investere)\b|værd at (?:købe|eje)\b)', re.I)


def _pct(x):
    try:
        return (x['v'] - x['p']) / x['p'] * 100 if x.get('p') else None
    except (TypeError, ZeroDivisionError, KeyError):
        return None


def _num(v):
    return f'{v:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def figure_lines(energy):
    """The page's figures now, topic by topic: value, the day's move and the figure's time."""
    s = (energy or {}).get('s') or {}
    out = ['## The Økonomi page now (the radar\'s numbers – the page shows them beside your text; do not repeat them)', '',
           f"Updated {(energy or {}).get('updated', '?')}. Fields: name · value · move against the previous close · the figure's time", '']
    for topic, figs in FIGURES.items():
        rows = []
        for key, name, unit in figs:
            x = s.get(key)
            if not isinstance(x, dict) or x.get('v') is None:
                continue
            p = _pct(x)
            rows.append(f"- {name}: {_num(x['v'])}{' ' + unit if unit else ''}{f' · {p:+.1f} %' if p is not None else ''} · {str(x.get('t') or '')[:16]}")
        if rows:
            out += [f'### {TOPICS[topic]} ({topic})', *rows, '']
    pumps = (energy or {}).get('pumps') or {}
    low = {}
    for c in pumps.get('chains') or []:
        for f in ('benzin', 'diesel'):
            v = ((c.get('p') or {}).get(f) or {}).get('v')
            if v and (f not in low or v < low[f][0]):
                low[f] = (v, c.get('c'))
    if low:
        out += ['### Brændstof (fuel)'] + [f"- {f}: {_num(v)} kr./l, laveste listepris ({who})" for f, (v, who) in low.items()] + ['']
    debt = (energy or {}).get('debt') or {}
    if debt.get('v'):
        out += ['### Gæld (debt)', f"- USA's gæld: {debt['v'] / 1e12:.2f} billioner $ ({debt.get('t')})", '']
    return out


def coming(cal, kal, now):
    """The calendar's events of the next AHEAD_DAYS days (both files), soonest first, with their ids."""
    today = now.date()
    out = []
    for src in (kal, cal):
        for e in (src or {}).get('items') or []:
            if not isinstance(e, dict) or not e.get('id') or len(str(e.get('date') or '')) < 10:
                continue
            try:
                d = datetime.fromisoformat(str(e['date'])[:10]).date()
            except ValueError:
                continue
            if 0 <= (d - today).days <= AHEAD_DAYS and e['id'] not in {x['id'] for x in out}:
                out.append(e)
    return sorted(out, key=lambda e: str(e['date']))


def input_lines(energy, stories, current, cal, kal, now, story_lines):
    """The economy editor's own part of the input: the figures, the economic news, the fortnight ahead, the page now."""
    out = figure_lines(energy)
    out += [f'## Economic news of the last 36 hours – {len(stories)} (oil, fuel, gas, markets, debt, central banks, tariffs, '
            'sanctions), strongest first', '']
    for i in stories:
        out += story_lines(i)
    out += [f'## Planned events of the next {AHEAD_DAYS} days in the calendar (the ids for `kommende`)', '']
    for e in coming(cal, kal, now):
        out.append(f"[{e['id']}] {e['date']} · {e.get('kind') or ''} · {e.get('title')}{' · ' + e['place'] if e.get('place') else ''}")
    cur = (current or {})
    out += ['', '## The Økonomi page as the last economy update left it' + (f" ({cur.get('at')})" if cur.get('at') else ' – none yet'), '']
    if cur.get('dag'):
        out.append(f"dag: {cur['dag'].get('text')}")
    for k, v in (cur.get('emner') or {}).items():
        out.append(f"{k}: {v.get('text') or ''} · stories {', '.join(v.get('stories') or [])}")
    if cur.get('kommende'):
        out.append('kommende: ' + ', '.join(e.get('id', '') for e in cur['kommende']))
    return out + ['']


def _text(v, n):
    return re.sub(r'\s+', ' ', str(v or '')).strip()[:n * 2]


def check_text(text, cited, where, problems, voice, limit):
    """Reality only, every number from a cited story, no judgement, forecast or advice."""
    if not text:
        problems.append(f'{where}: text – one to three factual sentences')
        return
    if len(text) > limit:
        problems.append(f'{where}: {len(text)} characters – at most {limit}')
    if not cited:
        problems.append(f'{where}: ids – the stories the text rests on')
    need = event_pages.digits(event_pages.NOT_A_COUNT.sub(' ', text))
    have = set().union(*(event_pages.digits(event_pages.story_text(it)) for it in cited)) if cited else set()
    if need - have:
        problems.append(f"{where}: {', '.join(sorted(need - have))} stands in none of the stories it cites – a number from "
                        "the news only (the page shows its own figures beside your text)")
    hit = event_pages.opinion(text)
    if hit:
        problems.append(f"{where}: '{hit}' is a judgement or a forecast of Khabar's own – say what happened, as the news tell it")
    m = ADVICE.search(text)
    if m:
        problems.append(f"{where}: '{m.group(0)}' – Khabar tells what the markets did, never what a reader should do with money")
    if event_pages.MEDIA_SAY.search(text):
        problems.append(f'{where}: name who gives each fact (the Fed, OPEC, Reuters), never "medierne"')
    if voice:
        voice.check_voice(text, where, problems)
        voice.check_forecast(text, where, problems)
        voice.check_reality(text, where, problems)
        voice.check_distance(text, where, problems)


def okonomi_file(entry, current, find, cal, kal, now, problems, voice=None):
    """okonomi.json as this update leaves it (the whole day written anew), or None when the update has none."""
    if not entry:
        return None
    if not isinstance(entry, dict):
        problems.append('okonomi: an object with dag, emner and kommende – or leave it out')
        return None

    def stories_of(ids, where):
        got = []
        for x in ids or []:
            it = find(str(x))
            if it is None:
                problems.append(f'{where}: {x} is no story in the input')
            elif it not in got:
                got.append(it)
        return got

    def credit(cited):
        return list(dict.fromkeys(str(it['source']) for it in cited if it.get('source') and it['source'] not in event_pages.NO_CITE))[:4]

    out = {'at': now.isoformat(timespec='seconds')}
    dag = entry.get('dag')
    if dag:
        text, cited = _text((dag or {}).get('text'), DAG_TEXT), stories_of((dag or {}).get('ids'), 'okonomi dag ids')
        check_text(text, cited, 'okonomi dag', problems, voice, DAG_TEXT)
        out['dag'] = {'text': text, 'ids': [it['id'] for it in cited], 'src': credit(cited)}
    emner = {}
    for key, v in (entry.get('emner') or {}).items():
        where = f'okonomi emner {key}'
        if key not in TOPICS:
            problems.append(f"{where}: no such topic – one of {', '.join(TOPICS)}")
            continue
        if not isinstance(v, dict):
            problems.append(f'{where}: an object with text, ids and stories')
            continue
        box = {}
        if v.get('text'):
            text, cited = _text(v['text'], TOPIC_TEXT), stories_of(v.get('ids'), f'{where} ids')
            check_text(text, cited, where, problems, voice, TOPIC_TEXT)
            box.update(text=text, ids=[it['id'] for it in cited], src=credit(cited))
        shown = stories_of((v.get('stories') or [])[:STORIES + 1], f'{where} stories')
        if len(v.get('stories') or []) > STORIES:
            problems.append(f'{where}: stories – at most {STORIES}')
        if shown:
            box['stories'] = [it['id'] for it in shown[:STORIES]]
        if box:
            emner[key] = box
    if emner:
        out['emner'] = emner
    planned = {e['id']: e for e in coming(cal, kal, now)}
    picks = []
    for x in (entry.get('kommende') or [])[:COMING + 1]:
        e = planned.get(str(x))
        if not e:
            problems.append(f'okonomi kommende: {x} is no event of the next {AHEAD_DAYS} days in the calendar')
            continue
        picks.append({k: e[k] for k in ('id', 'date', 'end', 'approx', 'title', 'kind', 'place', 'why') if e.get(k)})
    if len(entry.get('kommende') or []) > COMING:
        problems.append(f'okonomi kommende: at most {COMING}')
    if picks:
        out['kommende'] = picks[:COMING]
    q = entry.get('citat')
    if q:
        cited = stories_of((q or {}).get('ids'), 'okonomi citat ids') if isinstance(q, dict) else []
        who, said = _text((q or {}).get('who'), 60) if isinstance(q, dict) else '', _text((q or {}).get('text'), 300) if isinstance(q, dict) else ''
        if not who or not said or not cited:
            problems.append('okonomi citat: who, text (the statement in Danish) and ids – the story it comes from')
        else:
            if voice:
                voice.check_voice(said, 'okonomi citat', problems)
            out['citat'] = {'who': who, 'text': said, 'ids': [it['id'] for it in cited], 'u': cited[0].get('link') or '',
                            's': str(cited[0].get('source') or '')}
    if len(out) == 1:
        problems.append('okonomi: nothing to show – write dag, emner or kommende, or leave okonomi out')
    return out


TEMPLATE = {'okonomi': {
    'dag': {'text': 'To-tre faktuelle sætninger om dagens økonomi, som nyhederne fortæller den', 'ids': ['<story id>']},
    'emner': {'oil': {'text': 'En-to sætninger: hvad nyhederne siger om olien i dag', 'ids': ['<story id>'],
                      'stories': ['<story id>', '<story id>']}},
    'kommende': ['<calendar id>'],
    'citat': {'who': '<who said it: a central banker, a minister, OPEC>', 'text': '<the statement in Danish>', 'ids': ['<story id>']}}}


def age_ok(file, now, hours=30):
    """Whether the page should still show the editor's day (the radar drops one older than this)."""
    try:
        return now - datetime.fromisoformat(str(file.get('at'))) < timedelta(hours=hours)
    except (ValueError, TypeError):
        return False
