"""The Kalender tab (the owner, 2026-10-17: a calendar of planned events in a tab of its own; the Islamic dates left out
at his wish the same day): the radar's calendar.json (src/radar/calendar.py – Wikipedia's electoral calendars, the Fed
and the ECB, config/calendar.json), the editor's own entries (kalender.json),
and the tab, the dock and the front page's 'Det sker snart' in the app. No network: the pages are excerpts of the real
ones as fetched on 2026-10-17."""
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / 'scripts'))

from radar import calendar as cal  # noqa: E402
import editor  # noqa: E402
from test_editor import NOW, folder, publish, viden  # noqa: E402,F401 – fixtures

PUBLIC = ROOT / 'public'
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')
INDEX = (PUBLIC / 'index.html').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)

# ---------------------------------------------------------------- excerpts of the real pages (2026-10-17)
WIKI_2027 = '''<div class="mw-heading mw-heading2"><h2 id="January">January</h2></div>
<ul><li>16 January: <a href="/wiki/Elections_in_Nigeria" title="Elections in Nigeria">Nigeria</a>, <a href="/wiki/2027_Nigerian_general_election" title="2027 Nigerian general election">President, Senate and House of Representatives</a><sup id="cite_ref-1" class="reference"><a href="#cite_note-1">[1]</a></sup></li>
<li>24 January: <a href="/wiki/Elections_in_Chile" title="Elections in Chile">Chile</a>, <a href="/wiki/x">President</a></li></ul>
<div class="mw-heading mw-heading2"><h2 id="March">March</h2></div>
<ul><li>March: <a href="/wiki/Estonia" title="Estonia">Estonia</a>, <a href="/wiki/Next_Estonian_parliamentary_election" title="Next Estonian parliamentary election">Parliament</a></li>
<li>March: <i><a href="/wiki/Elections_in_Somaliland">Somaliland</a>, <a href="/wiki/x">Parliament</a></i></li></ul>
<div class="mw-heading mw-heading2"><h2 id="April">April</h2></div>
<ul><li>18 April:
<ul><li><a href="/wiki/Elections_in_France" title="Elections in France">France</a>, <a href="/wiki/2027_French_presidential_election" title="2027 French presidential election">President</a><sup class="reference"><a href="#c">[4]</a></sup></li>
<li><a href="/wiki/Elections_in_Finland" title="Elections in Finland">Finland</a>, <a href="/wiki/2027_Finnish_parliamentary_election">Parliament</a></li></ul></li>
<li>By 30 April: <a href="/wiki/Elections_in_Iraq">Iraq</a>, <a href="/wiki/x">Council of Representatives</a></li></ul>
<div class="mw-heading mw-heading2"><h2 id="May">May</h2></div>
<ul><li>9&#8211;10 May: <a href="/wiki/Elections_in_the_Czech_Republic">Czech Republic</a>, <a href="/wiki/y">Senate (1st round)</a></li>
<li>23 May: <a href="/wiki/Elections_in_Turkey">Turkey</a>, <a href="/wiki/z">Municipal councils</a></li>
<li>30 May: <a href="/wiki/Elections_in_Israel">Israel</a>, <a href="/w/index.php?title=x&amp;redlink=1" class="new">Knesset</a></li></ul>
<div class="mw-heading mw-heading2"><h2 id="Unknown_date">Unknown date</h2></div>
<ul><li><a href="/wiki/Elections_in_Libya">Libya</a>, <a href="/wiki/w">President</a></li></ul>'''

FOMC = '''<div class="panel panel-default"><div class="panel-heading"><h4><a id="1">2026 FOMC Meetings</a></h4></div>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>Oct/Nov</strong></div>
<div class="fomc-meeting__date col-xs-4">31-1</div></div>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>December</strong></div>
<div class="fomc-meeting__date col-xs-4">8-9*</div></div></div>
<div class="panel panel-default"><div class="panel-heading"><h4><a id="2">2027 FOMC Meetings</a></h4></div>
<div class="row fomc-meeting"><div class="fomc-meeting__month col-xs-5"><strong>January</strong></div>
<div class="fomc-meeting__date col-xs-4">26-27</div></div></div>'''

ECB = '''<dl><dt> 28/10/2026 </dt><dd> Governing Council of the ECB: monetary policy meeting in Frankfurt (Day 1)<br></dd>
<dt> 29/10/2026 </dt><dd> Governing Council of the ECB: monetary policy meeting in Frankfurt (Day 2), followed by press conference<br></dd>
<dt> 29/10/2026 </dt><dd> Press conference following the Governing Council meeting of the ECB in Frankfurt<br></dd>
<dt> 25/11/2026 </dt><dd> Governing Council of the ECB: non-monetary policy meeting (in Frankfurt)<br></dd>
<dt> 10/10/2028 </dt><dd> Governing Council of the ECB: monetary policy meeting in Frankfurt<br></dd>
<dt> 11/10/2028 </dt><dd> Governing Council of the ECB: monetary policy meeting in Frankfurt (Day 2), followed by press conference<br></dd></dl>'''


def test_wikipedias_calendar_gives_the_elections_of_weight():
    got = {e['title']: e for e in cal.parse_wiki(WIKI_2027, 2027)}
    assert set(got) == {'Præsident- og parlamentsvalg i Nigeria', 'Parlamentsvalg i Estland', 'Præsidentvalg i Frankrig',
                        'Parlamentsvalg i Finland', 'Parlamentsvalg i Irak (senest)', 'Senatsvalg i Tjekkiet (1. runde)',
                        'Parlamentsvalg i “israel”', 'Præsidentvalg i Libyen'}
    # Chile (no weight to the group), Somaliland (in italics) and Turkey's municipal councils: out; the unknown date's
    # elections since 18/10 as the year alone, 'forventet' (the owner found the calendar empty)
    assert got['Præsidentvalg i Libyen']['date'] == '2027' and got['Præsidentvalg i Libyen']['approx'] is True
    n = got['Præsident- og parlamentsvalg i Nigeria']
    assert n['date'] == '2027-01-16' and n['kind'] == 'valg' and n['place'] == 'Nigeria' and 'approx' not in n
    assert n['link'] == 'https://en.wikipedia.org/wiki/2027_Nigerian_general_election'
    assert got['Parlamentsvalg i Estland']['date'] == '2027-03' and got['Parlamentsvalg i Estland']['approx'] is True
    assert got['Præsidentvalg i Frankrig']['date'] == got['Parlamentsvalg i Finland']['date'] == '2027-04-18'   # a nested list
    assert got['Parlamentsvalg i Irak (senest)']['approx'] is True and got['Parlamentsvalg i Irak (senest)']['date'] == '2027-04-30'
    cz = got['Senatsvalg i Tjekkiet (1. runde)']
    assert (cz['date'], cz['end']) == ('2027-05-09', '2027-05-10')
    il = got['Parlamentsvalg i “israel”']   # the house style; a red link falls back to the calendar's page
    assert il['place'] == '“israel”' and il['link'] == 'https://en.wikipedia.org/wiki/2027_national_electoral_calendar'
    assert all(re.fullmatch(r'[a-z0-9-]+', e['id']) for e in got.values())


def test_a_missing_page_is_an_empty_answer_not_a_failure():
    assert cal.wiki_html({'error': {'code': 'missingtitle'}}) == ''
    assert cal.wiki_html({'parse': {'text': '<p>x</p>'}}) == '<p>x</p>' and cal.wiki_html({'parse': {}}) is None
    assert 'User-Agent' not in cal.UA and '@' not in cal.UA   # a descriptive agent with no personal data


def test_the_fed_and_the_ecb_give_their_decision_days():
    fed = cal.parse_fomc(FOMC)
    assert [e['date'] for e in fed] == ['2026-11-01', '2026-12-09', '2027-01-27']   # Oct/Nov 31-1: the first of November
    assert 'fremskrivninger' in fed[1]['why'] and 'fremskrivninger' not in fed[0]['why']   # * marks the projections
    assert all(e['kind'] == 'centralbank' and e['title'] == 'Fed: rentebeslutning' for e in fed)
    ecb = cal.parse_ecb(ECB)
    assert [e['date'] for e in ecb] == ['2026-10-29', '2028-10-11']   # the non-monetary meeting is no rate meeting
    assert 'Nationalbank' in ecb[0]['why'] and ecb[0]['place'] == 'Eurozonen'


def test_the_curated_events_each_carry_their_source():
    cfg = json.loads((ROOT / 'config' / 'calendar.json').read_text(encoding='utf-8'))
    ids = [e['id'] for e in cfg['events']]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r'[a-z0-9-]+', i) for i in ids)
    for e in cfg['events']:
        assert e['link'].startswith('https://'), e['id']
        assert e['kind'] in editor.CAL_KINDS, e['id']
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', e['date']) or (re.fullmatch(r'\d{4}(?:-\d{2})?', e['date']) and e.get('approx')), e['id']
        problems = []
        import voice
        voice.check_headline(e['title'], e['id'], problems)
        voice.check_forecast(e['why'], e['id'], problems)
        voice.check_reality(e['why'], e['id'], problems)
        assert not problems, problems
    dates = {e['id']: e['date'] for e in cfg['events']}
    assert dates['us-midtvejsvalg-2026'] == '2026-11-03' and dates['us-praesidentvalg-2028'] == '2028-11-07'


def test_a_run_keeps_a_failed_sources_last_good_items(tmp_path):
    t = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    good = {'wiki2026': lambda: cal.parse_wiki(WIKI_2027.replace('2027', '2026'), 2026), 'fed': lambda: cal.parse_fomc(FOMC),
            'ecb': lambda: cal.parse_ecb(ECB)}
    out = cal.run(tmp_path, good, t)
    assert set(out['ok']) == {'wiki2026', 'fed', 'ecb'} and not out['tried']
    kinds = {e['kind'] for e in out['items']}
    assert {'valg', 'centralbank', 'topmøde'} <= kinds and 'islamisk' not in kinds   # no Islamic dates (the owner, 17/10)
    assert not any('hijri' in e for e in out['items']) and not hasattr(cal, 'islamic_dates')
    # the US midterms: the curated entry wins over Wikipedia's on the same day and place
    assert sum(e['date'] == '2026-11-03' and e.get('place') == 'USA' for e in out['items']) <= 1

    def down():
        raise OSError('down')
    later = datetime(2026, 10, 18, 13, tzinfo=timezone.utc)   # a day on: every source is due again, and all are down
    again = cal.run(tmp_path, {'wiki2026': down, 'fed': down, 'ecb': down}, later)
    assert set(again['tried']) == {'wiki2026', 'fed', 'ecb'}
    assert [e for e in again['items'] if e['src'] == 'fed'] == [e for e in out['items'] if e['src'] == 'fed']   # kept
    # a source that failed rests: the next pass does not ask it
    asked = []
    cal.run(tmp_path, {'fed': lambda: asked.append(1) or []}, later.replace(minute=5))
    assert not asked
    # the past beyond thirty days is left out
    assert all(cal.last_day(e) >= date(2026, 9, 18) for e in again['items'])


def test_the_radar_runs_it_after_the_energy_step():
    radar = (ROOT / '.github' / 'workflows' / 'radar.yml').read_text(encoding='utf-8')
    assert radar.index('- name: Energy prices') < radar.index('- name: Calendar') < radar.index('- name: Save state')
    step = radar[radar.index('- name: Calendar'):radar.index('- name: Map')]
    assert 'continue-on-error: true' in step and 'timeout-minutes: 3' in step and 'python -m radar.calendar' in step
    pages = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
    assert 'calendarUrl: "https://raw.githubusercontent.com/${{ github.repository }}/data/calendar.json"' in pages
    assert 'kalenderUrl: "https://raw.githubusercontent.com/${{ github.repository }}/digest/kalender.json"' in pages


# ---------------------------------------------------------------- the editor's own entries (kalender.json)
def out_file(tmp_path, name):
    path = tmp_path / 'out' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


ENTRY = {'date': '2026-10-24', 'title': 'Våbenhvilen i Gaza udløber', 'kind': 'frist', 'place': 'Gaza',
         'why': 'Aftalen mellem Israel og Hamas løber 14 dage fra 10. oktober.', 'ids': ['s3']}


def test_the_editors_entries_are_checked_kept_changed_and_removed(folder, tmp_path):
    assert 'kalender.json' in editor.DIGEST_FILES
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'calendar': [ENTRY]})
    kal = out_file(tmp_path, 'kalender.json')
    [e] = kal['items']
    assert e['id'] == 'ed-2026-10-24-vaabenhvilen-i-gaza-udloeber' and e['src'] == 'ed' and e['ids'] == ['s3']
    assert e['why'] == 'Aftalen mellem “israel” og Hamas løber 14 dage fra 10. oktober.'   # the house style
    assert e['link'] == 'https://x.test/3'   # no link given: the story's
    (folder / 'kalender.json').write_text(json.dumps(kal), encoding='utf-8')
    # a later update without "calendar" keeps it; one with the same id changes it
    publish(folder, tmp_path, {'lede': 'Dagen kort.'})
    assert [x['id'] for x in out_file(tmp_path, 'kalender.json')['items']] == [e['id']]
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'calendar': [{**ENTRY, 'id': e['id'], 'date': '2026-10-25'}]})
    assert out_file(tmp_path, 'kalender.json')['items'][0]['date'] == '2026-10-25'
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'calendar': [{'id': e['id'], 'remove': True}]})
    assert out_file(tmp_path, 'kalender.json')['items'] == []


def test_a_past_entry_drops_two_days_after_its_day(folder, tmp_path):
    old = {**ENTRY, 'id': 'ed-old', 'date': '2026-10-08', 'src': 'ed', 'at': NOW}
    older = {**ENTRY, 'id': 'ed-older', 'date': '2026-10-07', 'src': 'ed', 'at': NOW}
    (folder / 'kalender.json').write_text(json.dumps({'items': [old, older]}), encoding='utf-8')
    publish(folder, tmp_path, {'lede': 'Dagen kort.'})
    assert [x['id'] for x in out_file(tmp_path, 'kalender.json')['items']] == ['ed-old']   # 10/10: two days after 8/10


def test_an_entry_that_breaks_the_rules_is_refused(folder, tmp_path, capsys):
    bad = [{**ENTRY, 'date': '2026-10-01'}, {**ENTRY, 'title': 'Hvad sker der med våbenhvilen?'},
           {**ENTRY, 'kind': 'krig'}, {**ENTRY, 'why': 'Våbenhvilen vil sandsynligvis blive forlænget.'},
           {**ENTRY, 'ids': ['nope']}, {**ENTRY, 'ids': [], 'link': ''}, {**ENTRY, 'date': '2026-11'},
           {'id': 'ed-none', 'remove': True}]
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'calendar': bad})
    out = capsys.readouterr().out
    assert 'has passed' in out and 'curiosity headline' in out and 'kind must be one of' in out
    assert "'sandsynligvis' is a forecast" in out and "unknown story id 'nope'" in out
    assert 'name the stories it comes from (ids) or its source (link)' in out
    assert 'YYYY-MM with "approx": true' in out and "'ed-none' is no entry of the calendar to remove" in out


def test_the_input_lists_the_next_thirty_days(folder):
    (folder / 'calendar.json').write_text(json.dumps({'items': [
        {'id': 'fed-2026-10-28', 'date': '2026-10-28', 'title': 'Fed: rentebeslutning', 'kind': 'centralbank', 'place': 'USA'},
        {'id': 'g20-2026', 'date': '2026-12-14', 'title': 'G20-topmøde', 'kind': 'topmøde'}]}),
        encoding='utf-8')
    (folder / 'kalender.json').write_text(json.dumps({'items': [{**ENTRY, 'id': 'ed-x'}]}), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    part = text[text.index('## The calendar – the next 30 days'):]
    part = part[:part.index('\n## ')]
    assert '[ed-x] 2026-10-24 · frist · Våbenhvilen i Gaza udløber (Gaza) – editor' in part
    assert '[fed-2026-10-28] 2026-10-28 · centralbank · Fed: rentebeslutning (USA) – radar' in part
    assert 'G20' not in part   # beyond thirty days
    assert '"calendar"' in text   # the template shows it


def test_the_routine_prompt_names_the_calendar():
    prompt = (ROOT / 'docs' / 'hjerne' / 'routine-prompt.md').read_text(encoding='utf-8')
    assert '`calendar`' in prompt and 'kalender.json' in prompt


# ---------------------------------------------------------------- the app
def fn(name):
    m = re.search(r'\n(?:async )?function ' + re.escape(name) + r'\(.*?\n\}', CODE, re.S)
    assert m, name
    return m.group(0)


def test_the_tab_its_icon_and_its_links():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert '<button role="tab" id="tab-kalender" aria-controls="page-kalender" data-tab="kalender"' in nav and '#i-cal' in nav
    sym = INDEX[INDEX.index('<symbol id="i-cal"'):]
    sym = sym[:sym.index('</symbol>')]
    assert 'fill="none" stroke="currentColor" stroke-width="1.8"' in sym   # the other icons' line style
    assert '<section class="page" data-tab="kalender" id="page-kalender" role="tabpanel" aria-labelledby="tab-kalender">' in INDEX
    assert "kalender: 'Kalender'" in CODE.split('const TITLES = ')[1].split('};')[0]
    start = CODE.split('const START = ')[1].split('};')[0]
    assert "kalender: 'kalender'" in start and "kort: 'home'" in start
    assert "params.get('kalender') ? 'kalender'" in CODE   # ?kalender=<id> opens the tab at the event
    assert "'kalender'].some(k => q.has(k))" in INDEX   # and skips the intro
    assert 'kalender: kalenderPage' in CODE.split('const OWN = ')[1].split('\n')[0]   # drawn before the news come


def test_the_two_files_are_merged_and_the_editor_wins():
    items = fn('calItems')
    assert "V('kal')" in items and "V('cal')" in items
    assert "!mine.has(e.date + '|' + calNorm(e.title))" in items and '!ids.has(e.id)' in items
    assert 'quoteIsrael(String(e.title))' in items
    assert "cal: () => CFG.calendarUrl ||" in CODE and "kal: () => CFG.kalenderUrl ||" in CODE


def test_the_page_names_what_comes_next_then_the_week_then_the_months():
    page = fn('kalenderPage')
    assert '<p class="cal-fly">Kalender' in page and 'class="cal-next">${next ? `Næste: ${esc(next.title)} ${calCount(next, today)}`' in page
    assert "blockHead('Det sker snart')" in page and 'calDay(e.date) - today <= 7' in page
    assert 'class="cal-mh"' in page and 'Tidligere' in page and 'today - 30' in page
    count = CODE.split('const calCount = ')[1].split('\n')[0]
    assert "'i dag'" in count and "'i morgen'" in count and '`om ${n} dage`' in count
    row = fn('calRow')
    assert '<b>${d.getDate()}</b><small>${esc(FMT.wd.format(d))}</small>' in row   # the day large, its weekday small
    assert "'<span>forventet</span>'" in row and 'hijri' not in row and 'class="hit"' in row and '<a ' not in row
    detail = fn('calDetail')
    assert 'e.why' in detail and 'Kilde<svg' in detail and 'data-live=' in detail and 'data-cal-share' in detail
    assert "calOpen.size ? `${titlesVer}|${data && data.updated}` : ''" in CODE   # a reload draws nothing it does not change


def test_red_only_for_the_next_48_hours_and_calm_kind_colours():
    assert 'calDay(e.date) - today <= 1' in CODE.split('const calNear = ')[1].split('\n')[0]
    assert re.search(r'\.ck\.near i \{ background: var\(--red\); \}', RULES)
    for k in ('valg', 'top', 'bank', 'frist', 'dansk'):
        assert f'--c-{k}:' in RULES
    assert 'islamisk' not in RULES and '--c-isl' not in RULES
    assert re.search(r'\.cal-next \{[^}]*font-family: var\(--display\)', RULES)   # Source Serif 4, as the front page
    assert re.search(r'\.cal-fly \{[^}]*color: var\(--red\)', RULES)
    assert re.search(r'\.ce:not\(\.open\) \{ content-visibility: auto;', RULES)


def test_the_dock_holds_the_kinds_and_only_important():
    opts = fn('calOpts')
    filters = CODE.split('const CAL_FILTERS = ')[1].split(';')[0]
    assert re.findall(r"'([^']+)'\]", filters) == ['Alle', 'Valg', 'Topmøder', 'Centralbanker', 'Frister', 'Danmark']
    assert 'islamisk' not in CODE.split('const CAL_KINDS = ')[1].split('};')[0] and 'islamisk' not in editor.CAL_KINDS
    # 18/10, the owner: no window of months – everything ahead – and 'Kun vigtige' hides the events of low weight
    assert 'CAL_WINS' not in CODE and 'calWin' not in CODE and 'data-cal-win' not in CODE
    # and since 18/10 one toggle, Vigtige · Alle, the kinds' chips gone (the owner: 'kun være "Vigtige" og "alle"')
    assert 'data-cal-f=' not in opts and 'data-cal-imp="1"' in opts and 'data-cal-imp="0"' in opts and 'class="imp-i"' in opts and 'class="chip' in opts
    assert "store.set('calImp', calImp)" in fn('calTap') and '(!calImp || calWOf(e) > 1)' in fn('kalenderPage')


def test_the_front_page_shows_what_happens_soon_between_the_news_and_the_developments():
    block = fn('calBlock')
    assert 'calDay(e.date) - today <= 14' in block and '.slice(0, 4)' in block and "if (!list.length) return '';" in block
    assert 'calWOf(e) > 1' in block   # 18/10: only high and middle weight on the front page
    assert "moreLink('Alle', 'kalender')" in block and 'data-cal-go' in fn('calRow')
    assert "(FRONT_RANK[b.kind] ?? 4) > CAL_RANK && html) { calPut = true; html += calBlock(); }" in fn('composedHome')
    fixed = fn('fixedHome')
    assert fixed.index("blockHead('Døgnets vigtigste'") < fixed.index('calBlock()') < fixed.index('followStrip(own)')


def test_an_event_is_shared_as_text_with_the_way_back():
    text = CODE.split('const calText = ')[1].split('\n')[0]
    assert '${calDm(e)} · ${e.title}' in text and "' – ' + e.why" in text and 'via khabar.nu/?kalender=${encodeURIComponent(e.id)}' in text
    assert "if (sh.dataset.calShare) share(calText(e)); else if (await copyText(calText(e))) toast('Kopieret');" in fn('calTap')


def test_eu_summits_weigh_in_the_middle_and_climate_summits_low():
    from radar import calendar as c
    assert c.weight({'kind': 'topmøde', 'title': 'EU-topmøde', 'place': 'Bruxelles'}) == 2
    assert c.weight({'kind': 'topmøde', 'title': "FN's klimatopmøde COP31"}) == 1
    assert c.weight({'kind': 'topmøde', 'title': 'G20-topmøde'}) == 3
    assert c.weight({'kind': 'topmøde', 'title': 'EU-topmøde', 'w': 3}) == 3   # raised by the editor
    # 18/10, the owner: the rate decisions are abstract – no mark, the Fed's too (the app holds the same, calWOf)
    assert c.weight({'kind': 'centralbank', 'title': 'Fed: rentebeslutning', 'place': 'USA'}) == 1


def test_events_of_weight_get_their_fuller_explanation_in_reality_only():
    from radar import calendar as c
    rules = c.why_rules()
    ev = c.deeper({'kind': 'valg', 'title': 'Midtvejsvalg i USA', 'place': 'USA', 'w': 3, 'why': 'kort'}, rules)
    assert 'Repræsentanternes Hus' in ev['why']
    assert c.deeper({'kind': 'valg', 'title': 'Præsidentvalg i Gambia', 'place': 'Gambia', 'w': 2, 'why': 'kort'}, rules)['why'].startswith('Gambia er')
    assert c.deeper({'kind': 'valg', 'title': 'Senatsvalg i Tjekkiet', 'place': 'Tjekkiet', 'w': 1, 'why': 'kort'}, rules)['why'] == 'kort'
    assert c.deeper({'kind': 'frist', 'title': 'x', 'w': 3, 'why': 'eget', 'src': 'ed'}, rules)['why'] == 'eget'   # the editor's own
    for r in rules:   # the owner's house style, and no forecast
        assert 'Israel' not in r['why'] and not re.search(r'forventes|sandsynligvis|vil føre til|kan føre til', r['why']), r


def test_the_editor_is_shown_the_dates_the_news_name():
    # 18/10, the owner: the calendar looked empty – the editor had added nothing the news named
    now = datetime(2026, 10, 18, 10, tzinfo=timezone.utc)
    today = editor.dk(now).date()
    assert editor.date_in('Truce extended to Jan. 10', today) == date(2027, 1, 10)   # said in October: next year
    assert editor.date_in('Våbenhvilen udløber 12. november', today) == date(2026, 11, 12)
    assert editor.date_in('the October 5 attack', today) is None   # a day just passed is no coming event
    at = lambda h: (now.replace(hour=10 - h)).isoformat()  # noqa: E731
    stories = [{'id': 'a', 'title': 'US and China extend trade truce to January 10', 'found': at(2), 'rank': 90},
               {'id': 'b', 'title': 'UN Security Council to vote on Gaza resolution', 'found': at(3), 'rank': 80},
               {'id': 'c', 'title': 'Leaders meet at the summit', 'found': at(1), 'rank': 70},          # no day, a weak word
               {'id': 'd', 'title': 'Talks in Doha on 2 December', 'found': at(1), 'rank': 60}]
    cal_items = {'items': [{'date': '2027-01-10', 'title': 'Handelsvåbenhvilen mellem USA og Kina udløber'}]}
    out = '\n'.join(editor.news_dates(stories, cal_items, {}, now))
    assert '[d] 02.12.2026' in out and 'ikke i kalenderen' in out.split('[d]')[1].split('\n')[0]
    assert '[a] 10.01.2027' in out and 'kalenderen har: Handelsvåbenhvilen' in out
    assert '[b]' in out and 'ingen dato nævnt' in out and '[c]' not in out
    assert out.index('[d]') < out.index('[a]') < out.index('[b]')   # a day the calendar lacks first
    assert editor.news_dates([stories[2]], {}, {}, now) == []         # nothing to show: no section
