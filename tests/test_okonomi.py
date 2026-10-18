"""The economy editor's day on the Økonomi page (the owner, 18/10: 'kan vi erstatte en af senior kørslerne i løbet af
dagen som kan kigge på økonomi og kalender siden? tilføje kontekst forbedre layout og gøre det mere livligt'): its
checks (scripts/okonomi.py), its input (editor.py input --okonomi), its way through the radar (energy.editor_layer) and
the page that shows it."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import editor  # noqa: E402
import okonomi  # noqa: E402
import voice  # noqa: E402
from radar import energy  # noqa: E402
from test_editor import NOW, add_items, folder, publish, story, viden  # noqa: E402,F401 – fixtures

T = datetime.fromisoformat(NOW)
OIL = {'id': 'o1', 'title': 'Oil rises 4% as Houthis hit Saudi pipeline', 'title_da': 'Olien stiger 4 % efter houthi-angreb på saudisk rørledning',
       'summary': 'Brent rose after the attack on the East-West pipeline.', 'source': 'Reuters', 'link': 'https://x.test/o1',
       'published': NOW, 'found': NOW, 'outlets': 6, 'lang': 'en', 'members': ['o0']}
FED = {'id': 'f1', 'title': 'Fed holds rates, Powell says inflation remains too high', 'source': 'AP', 'link': 'https://x.test/f1',
       'published': NOW, 'found': NOW, 'outlets': 3, 'lang': 'en'}
FIND = {'o1': OIL, 'o0': OIL, 'f1': FED}.get
CAL = {'items': [{'id': 'fed-2026-10-20', 'date': '2026-10-20', 'title': 'Fed: rentebeslutning', 'kind': 'centralbank', 'place': 'USA',
                  'why': 'Den amerikanske centralbank fastsætter renten.'},
                 {'id': 'langt-ude', 'date': '2026-12-01', 'title': 'Noget langt ude', 'kind': 'andet'}]}


def check(entry):
    problems = []
    return okonomi.okonomi_file(entry, {}, FIND, CAL, {}, T, problems, voice), problems


def test_the_days_lines_rest_on_the_stories_they_cite_and_name_their_outlets():
    out, problems = check({'dag': {'text': 'Houthierne har ramt en saudisk rørledning, og olien stiger 4 %, oplyser Reuters.', 'ids': ['o0']},
                           'emner': {'oil': {'text': 'Houthierne har ramt rørledningen øst-vest.', 'ids': ['o1'], 'stories': ['o1', 'f1']}},
                           'kommende': ['fed-2026-10-20'],
                           'citat': {'who': 'Jerome Powell', 'text': 'Inflationen er stadig for høj.', 'ids': ['f1']}})
    assert problems == []
    assert out['dag'] == {'text': 'Houthierne har ramt en saudisk rørledning, og olien stiger 4 %, oplyser Reuters.', 'ids': ['o1'],
                          'src': ['Reuters']}                                  # a member's id finds the story
    assert out['emner']['oil']['stories'] == ['o1', 'f1'] and out['emner']['oil']['src'] == ['Reuters']
    assert out['kommende'][0]['title'] == 'Fed: rentebeslutning' and out['kommende'][0]['why']   # the calendar's own lines
    assert out['citat']['who'] == 'Jerome Powell' and out['citat']['u'] == 'https://x.test/f1'
    assert out['at'] == T.isoformat(timespec='seconds')


def test_a_number_of_its_own_a_forecast_or_advice_is_refused():
    _, problems = check({'dag': {'text': 'Olien stiger 12 %, og prisen vil stige yderligere.', 'ids': ['o1']},
                         'emner': {'mkt': {'text': 'Nu er det et godt tidspunkt at købe aktier.', 'ids': ['f1']},
                                   'krypto': {'text': 'x', 'ids': ['f1']}},
                         'kommende': ['langt-ude', 'findes-ikke']})
    text = '\n'.join(problems)
    assert '12 stands in none of the stories it cites' in text
    assert "'vil stige'" in text                                                # a forecast of Khabar's own
    assert 'never what a reader should do with money' in text
    assert 'okonomi emner krypto: no such topic' in text
    assert 'langt-ude is no event of the next 14 days' in text and 'findes-ikke is no event' in text
    fine, ok = check({'emner': {'kris': {'text': 'Kongressen gav Trump frist til at lægge told på købere af russisk olie.', 'ids': ['f1']}}})
    assert ok == [] and fine['emner']['kris']['text'].startswith('Kongressen')    # 'købere' is a fact, not advice


def test_the_editor_input_for_the_economy_holds_the_figures_the_news_and_the_dates(folder, capsys):
    add_items(folder, {**OIL, 'sec': 'me', 'rank': 90, 'confirmed': 3})
    (folder / 'energy.json').write_text(json.dumps({'updated': NOW, 's': {'brent': {'v': 109.86, 'p': 105.92, 't': NOW}}}), encoding='utf-8')
    (folder / 'calendar.json').write_text(json.dumps(CAL), encoding='utf-8')
    editor.main(['input', '--okonomi', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert '## The Økonomi page now' in text and 'Brent: 109,86 $/tønde · +3.7 %' in text
    assert '## Economic news of the last 36 hours' in text and '[o1]' in text
    assert '[fed-2026-10-20] 2026-10-20 · centralbank · Fed: rentebeslutning' in text and 'langt-ude' not in text.split('## Planned events')[1].split('##')[0]
    assert '"okonomi"' in text and '"kommende"' in text                        # the shape to write
    assert 'Regeringen strammer reglerne' not in text.split('## Economic news')[1].split('## Planned')[0]   # no economy


def test_publish_keeps_the_day_in_okonomi_json(folder, tmp_path):
    add_items(folder, {**OIL, 'sec': 'me', 'rank': 90, 'confirmed': 3})
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'okonomi': {'dag': {'text': 'Houthierne har ramt en saudisk rørledning.', 'ids': ['o1']}}})
    day = json.loads((tmp_path / 'out' / 'okonomi.json').read_text(encoding='utf-8'))
    assert day['dag']['text'] == 'Houthierne har ramt en saudisk rørledning.' and 'okonomi.json' in editor.DIGEST_FILES


def test_the_radar_hands_the_day_to_the_page_with_its_stories(tmp_path):
    (tmp_path / 'data.json').write_text(json.dumps({'items': [OIL, FED]}), encoding='utf-8')
    now = datetime.now(timezone.utc)
    day = {'at': now.isoformat(), 'dag': {'text': 'Dagen.', 'src': ['Reuters']},
           'emner': {'oil': {'text': 'Olien.', 'src': ['Reuters'], 'stories': ['o0', 'gone']}},
           'kommende': [{'id': 'fed-2026-10-20', 'date': '2026-10-28', 'title': 'Fed: rentebeslutning'}],
           'citat': {'who': 'Jerome Powell', 'text': 'Inflationen er stadig for høj.', 'ids': ['f1'], 'u': 'https://x.test/f1', 's': 'AP'}}
    (tmp_path / 'okonomi.json').write_text(json.dumps(day), encoding='utf-8')
    layer = energy.editor_layer(tmp_path, path=str(tmp_path / 'okonomi.json'), summaries='__none__')
    assert layer['dag']['text'] == 'Dagen.' and layer['kommende'][0]['id'] == 'fed-2026-10-20'
    news = layer['emner']['oil']['news']
    assert len(news) == 1 and news[0]['i'] == 'o1' and news[0]['u'] == 'https://x.test/o1' and news[0]['da'].startswith('Olien stiger')
    q = energy.econ_quote([], digest='__none__', ed=layer)
    assert q['who'] == 'Jerome Powell' and q['i'] == 'f1' and q['ed']           # the economy editor's statement first
    old = {**day, 'at': (now - timedelta(hours=31)).isoformat()}
    (tmp_path / 'okonomi.json').write_text(json.dumps(old), encoding='utf-8')
    assert energy.editor_layer(tmp_path, path=str(tmp_path / 'okonomi.json'), summaries='__none__') is None   # a missed day


PAGE = (ROOT / 'public' / 'energi' / 'index.html').read_text(encoding='utf-8')
APP = (ROOT / 'public' / 'app.js').read_text(encoding='utf-8')
FLOW = (ROOT / '.github' / 'workflows' / 'radar.yml').read_text(encoding='utf-8')


def test_the_page_shows_the_day_the_lines_the_stories_and_the_dates():
    assert 'h += edLine(T.id);' in PAGE                                   # under every topic's headline
    assert 'h += bigNews() + nowRows(list, base) + coming();' in PAGE     # 'Det kommer' in Lige nu
    assert 'h += edNews(T.id);' in PAGE                                   # 'I nyhederne' under the figures
    assert 'Bygger på' in PAGE and "appFn('khabarOpenCal')" in PAGE
    assert 'window.khabarOpenCal = id =>' in APP                          # the app's calendar opens at the date
    assert 'git show FETCH_HEAD:okonomi.json > .cache/okonomi.json' in FLOW and 'RADAR_OKONOMI: .cache/okonomi.json' in FLOW


def test_the_radar_finds_the_workflows_cache_files_from_its_working_directory(tmp_path, monkeypatch):
    # RADAR_OKONOMI and RADAR_SUMMARIES are '.cache/…' from the job's folder, not the state's (18/10: the page got none)
    state = tmp_path / 'state'
    (tmp_path / '.cache').mkdir()
    state.mkdir()
    (state / 'data.json').write_text(json.dumps({'items': [OIL]}), encoding='utf-8')
    day = {'at': datetime.now(timezone.utc).isoformat(), 'emner': {'oil': {'text': 'Olien.', 'stories': ['o1']}}}
    (tmp_path / '.cache' / 'okonomi.json').write_text(json.dumps(day), encoding='utf-8')
    (tmp_path / '.cache' / 'summaries.json').write_text(json.dumps({'titles': {'o1': {'title': 'Redaktørens overskrift', 'at': NOW}}}), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('RADAR_OKONOMI', '.cache/okonomi.json')
    monkeypatch.setenv('RADAR_SUMMARIES', '.cache/summaries.json')
    layer = energy.editor_layer(state)
    assert layer['emner']['oil']['news'][0]['ed'] == 'Redaktørens overskrift'
