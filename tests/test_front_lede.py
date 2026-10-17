"""The front page reworked (the owner, 17/10): the lede's parts open their stories ("øverste titel skal linke til de
forskellige nyheder"), Dagens historie has its picture ("Kan dagens historie ikke få et billede?"), less on the page
and Denmark only when it matters ("danmark er ikke så vigtig … medmindre det er vigtige historier")."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import editor  # noqa: E402
from test_editor import NOW, folder, publish, viden  # noqa: E402,F401 – fixtures

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'public' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'public' / 'style.css').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
PROMPT = (ROOT / 'docs' / 'hjerne' / 'routine-prompt.md').read_text(encoding='utf-8')

LEDE = ('Trump ophæver nye sanktioner og told mod Rusland, som Moskva kalder et historisk øjeblik, mens houthierne '
        'rammer Aden og Saudi-Arabien, og bosættere angriber landmænd på Vestbredden.')
SAMPLES = [LEDE, 'Folketinget vedtager loven; Iran og USA mødes i Oman – og Hamas svarer.', 'Kort.',
           'Israel og Iran, USA og Kina samt Rusland mødes i Genève, mens EU venter', '']


def fn(name):
    m = re.search(r'\n(?:async )?function ' + re.escape(name) + r'\(.*?\n\}', CODE, re.S)
    assert m, name
    return m.group(0)


def run_js(calls):
    """The app's lede helpers (from 'const LEDE_CUT' to the paragraph's drawing) run by Node on the given calls."""
    if not shutil.which('node'):
        pytest.skip('node is not installed')
    start = APP.index('const LEDE_CUT = ')
    js = APP[start:APP.index('// the lede as one paragraph', start)] + f'\nconsole.log(JSON.stringify({calls}));'
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ------------------------------------------------------------------ the lede's parts

def test_the_lede_is_cut_where_its_clauses_meet_and_short_parts_join_a_neighbour():
    parts = run_js(f'ledeParts({json.dumps(LEDE)})')
    assert [p['t'] for p in parts] == ['Trump ophæver nye sanktioner', 'told mod Rusland',
                                       'som Moskva kalder et historisk øjeblik', 'houthierne rammer Aden og Saudi-Arabien',
                                       'bosættere angriber landmænd på Vestbredden.']
    assert ''.join(p['sep'] + p['t'] for p in parts) == LEDE   # nothing lost: the paragraph reads as written
    assert [p['sep'] for p in parts] == ['', ' og ', ', ', ', mens ', ', og ']


def test_the_editor_cuts_the_lede_as_the_app_does():
    got = run_js('[' + ','.join(f'ledeParts({json.dumps(s)}).map(p => p.t)' for s in SAMPLES) + ']')
    assert got == [editor.lede_parts(s) for s in SAMPLES]
    assert editor.lede_parts('Kort.') == ['Kort.'] and editor.lede_parts('') == []


FRONT = [{'id': 'f1', 'title': 'Trump suspenderer nye sanktioner og told mod Rusland', 'actors': ['rusland']},
         {'id': 'f2', 'title': 'Houthierne påtager sig angreb på lufthavnen i Aden'},
         {'id': 'f3', 'title': 'Israelske bosættere brænder palæstinensiske olivenlunde på Vestbredden'}]
LIVE = [{'id': 'l1', 'title': 'Kreml: Moskva kalder Trumps beslutning et historisk øjeblik'},
        {'id': 'l2', 'title': 'Houthierne rammer Aden igen', 'also': [{'title': 'Houthis strike Aden'}]},
        {'id': 'l3', 'title': 'Folketinget vedtager ny lov om moskeer'}] + \
       [{'id': f'x{k}', 'title': f'Nyhed nummer {k} om vejret i Bergen'} for k in range(8)]


def test_each_part_opens_the_story_it_names_front_page_first():
    links = run_js(f'ledeLinks({json.dumps(LEDE)}, {json.dumps(FRONT)}, {json.dumps(LIVE)})')
    got = [(p['t'], p['id']) for p in links]
    # the two first parts are one story: one link; Aden is on the front page (f2) and in Live (l2): the front page wins
    assert got[0] == ('Trump ophæver nye sanktioner og told mod Rusland', 'f1')
    assert ('houthierne rammer Aden og Saudi-Arabien', 'f2') in got
    assert got[-1] == ('bosættere angriber landmænd på Vestbredden.', 'f3')
    # a part the front page does not name is looked for in Live
    assert ('som Moskva kalder et historisk øjeblik', 'l1') in got


def test_a_part_without_a_story_stays_plain_and_the_editors_ids_win():
    plain = run_js(f'ledeLinks("Vejret bliver koldt i hele landet, og børnene holder efterårsferie i ugen", [], {json.dumps(LIVE)})')
    assert all(p['id'] is None for p in plain)
    by = {i['id']: i for i in FRONT + LIVE}
    links = run_js(f'(() => {{ const by = {json.dumps(by)}; return ledeLinks({json.dumps(LEDE)}, {json.dumps(FRONT)}, '
                   f'{json.dumps(LIVE)}, ["l2", "", "l1", "", "gone"], id => by[id] || null); }})()')
    got = [(p['t'], p['id']) for p in links]
    assert got[0] == ('Trump ophæver nye sanktioner', 'l2') and got[1] == ('told mod Rusland', None)
    assert got[3] == ('houthierne rammer Aden og Saudi-Arabien', None)   # '' : the editor says it names no story
    assert got[4][1] == 'f3'                                             # an id that left: found by its words


def test_the_lede_is_one_paragraph_of_quiet_links_without_the_wikis_underline():
    head = fn('ledeHead')
    assert '<p class="lede-t">${ledeHtml(' in head and 'rich(lede' not in head and 'data-go' not in head
    html = fn('ledeHtml')
    assert '<a class="lede-a" href="?item=${encodeURIComponent(p.id)}"' in html and 'button' not in html
    body = ''.join(re.findall(r'\.lede-t a\.lede-a \{([^}]*)\}', RULES))
    assert 'text-decoration-style: solid' in body and 'var(--line)' in body
    assert 'dotted' not in body and 'pulse' not in body and 'color: inherit' in body
    assert re.search(r'\.lede-t a\.lede-a:active \{[^}]*text-decoration-color: var\(--text-3\)', RULES)
    # a tap: the story on the front page opens in place, in view; else in Live as ?item= does
    go = fn('ledeGo')
    assert "pg$('s-' + i.id)" in go and 'toggle(el)' in go and 'openInLive(i.id)' in go and 'scrollToEl(el' in go
    assert "t.closest('[data-lede]')" in CODE
    assert 'f.lede_ids' in fn('home') and 'notes().lede_ids' in fn('fixedHome')


# ------------------------------------------------------------------ Dagens historie's picture, less clutter, Denmark

def test_dagens_historie_has_its_own_picture_with_the_headline_on_it():
    lead = APP[APP.index('const leadPic = '):APP.index('function thumb(')]
    assert 'i.pic' in lead and 'badPics.has(x)' in lead and 'thumb' not in lead.split('\n')[0]   # never the small copy
    assert 'badPics.add(' in fn('leadPicFailed') and "classList.remove('lp')" in fn('leadPicFailed')
    st = fn('story')
    assert 'onerror="leadPicFailed(this)"' in st and 'loading="lazy"' not in st.split('const lp =')[1].split('\n')[0]
    assert 'first || b.picture !== false ? leadPic(i)' in fn('composedHome') and 'pic: leadPic(lead)' in fn('fixedHome')
    assert re.search(r'\.lead-pic \{[^}]*aspect-ratio: 4 / 3;', RULES)                     # colour, text on a fade
    assert re.search(r'\.lead-pic::after \{[^}]*linear-gradient\(to top, rgba\(0, 0, 0, \.9\)', RULES)
    assert re.search(r'\.story\.lp \.row > \.tx \{[^}]*position: absolute;[^}]*bottom: 14px', RULES)
    assert re.search(r'\.lead-pic img \{[^}]*filter: var\(--press\)', RULES) and '.lead-pic::before' in RULES   # 15 % colour, grain
    assert re.search(r'\.lead-pic img \{[^}]*object-fit: cover', RULES)


def test_the_front_page_shows_less():
    comp = fn('composedHome')
    assert 'const FRONT_MAX = 6' in CODE and 'if (drawn >= FRONT_MAX) break;' in comp
    assert "most = b.dkQuiet ? 2 : 3" in comp and 'data-unfold="${esc(key)}"' in comp   # 'Alle ›' unfolds the rest
    assert "top: true }); break; } }" in comp and ".slice(0, 3)" in comp   # one more story under Dagens historie
    line = fn('storyline')
    assert 'storyline(tp, n = 2)' in line and 'stepsWithDays(lines, null)' in line and 'Hele udviklingen' in line
    assert "esc(String(b.text))" in comp   # a linje without the wiki's underlines


def test_denmark_only_when_it_matters():
    assert "tops.has(i.id) || (!!i.big && i.live === 'dk')" in CODE
    order = fn('frontOrder')
    assert "list.every(i => secOf(i) === 'dk')" in order and 'dkQuiet: true' in order and 'return [...rest, ...quiet]' in order
    fixed = fn('fixedHome')
    assert 'dkMatters(i, tops)), 2)' in fixed and "blockHead('Danmark')" in fixed
    assert 'two or three Danish ones' not in PROMPT and 'Danish politics never buried' not in PROMPT
    assert "Denmark's place in a great power's plan" in PROMPT and 'a short block late on the page' in PROMPT


# ------------------------------------------------------------------ the editor's lede_ids

def test_lede_ids_are_checked_stored_and_kept_with_a_kept_lede(folder, tmp_path, capsys):
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    data['items'][1]['members'] = ['s0', 's4']   # s4's old lead article
    (folder / 'data.json').write_text(json.dumps(data), encoding='utf-8')
    lede = 'Regeringen strammer reglerne for statsborgerskab, mens kanalerne melder om nye angreb i Gaza.'
    assert editor.lede_parts(lede) == ['Regeringen strammer reglerne for statsborgerskab', 'kanalerne melder om nye angreb i Gaza.']
    digest, _ = publish(folder, tmp_path, {'lede': lede, 'lede_ids': ['s1', 's0'], 'front': {'blocks': [{'kind': 'live', 'n': 3}]}})
    assert digest['editor']['lede_ids'] == ['s1', 's4']   # an old lead id resolved to its story's id now
    front = json.loads((tmp_path / 'out' / 'front.json').read_text(encoding='utf-8'))
    assert front['lede'] == lede and front['lede_ids'] == ['s1', 's4']
    # kept: the lede keeps its ids, in digest.json and in the kept composition
    (folder / 'digest.json').write_text(json.dumps({**digest}), encoding='utf-8')
    (folder / 'front.json').write_text(json.dumps(front), encoding='utf-8')
    digest2, _ = publish(folder, tmp_path, {'topics': []}, now='2026-10-10T20:20:00+00:00')
    assert digest2['editor']['lede'] == lede and digest2['editor']['lede_ids'] == ['s1', 's4']
    assert json.loads((tmp_path / 'out' / 'front.json').read_text(encoding='utf-8'))['lede_ids'] == ['s1', 's4']
    # a new lede without ids: none (the app finds the parts' stories itself)
    digest3, _ = publish(folder, tmp_path, {'lede': 'Dagen kort med flere nyheder.'}, now='2026-10-10T20:30:00+00:00')
    assert 'lede_ids' not in digest3['editor']
    # one id per part, each a story of the pool
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': lede, 'lede_ids': ['s1']})
    assert 'lede_ids: 1 ids for 2 parts of the lede' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': lede, 'lede_ids': ['s1', 'nope']})
    assert "lede_ids: unknown story id 'nope'" in capsys.readouterr().out
    digest4, _ = publish(folder, tmp_path, {'lede': lede, 'front': {'lede_ids': ['', 's4'], 'blocks': [{'kind': 'live'}]}})
    assert digest4['editor']['lede_ids'] == ['', 's4']   # '' : a part that names no story


def test_the_input_shows_the_ledes_parts(folder):
    (folder / 'digest.json').write_text(json.dumps({'date': '2026-10-10', 'editor': {
        'created': NOW, 'lede': 'Regeringen strammer reglerne, mens Israel angriber Gaza igen.', 'lede_at': NOW,
        'lede_ids': ['s1', '']}}), encoding='utf-8')
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert 'Lede parts: 1. Regeringen strammer reglerne = [s1] | 2. Israel angriber Gaza igen.' in text
    assert '"lede_ids"' in text
