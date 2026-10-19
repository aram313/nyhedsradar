import hashlib
import hmac
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radar import admin  # noqa: E402

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
KEY = 'abcd-efgh-ijkl-mnop'
ITEMS = {'s1': {'title': 'AP hub page', 'source': 'AP', 'link': 'https://apnews.com/hub/x'}}


def signed(**m):
    m.setdefault('at', str(int(NOW.timestamp() * 1000)))
    m['sig'] = hmac.new(KEY.encode(), admin.signed_text(m).encode(), hashlib.sha256).hexdigest()
    return {'kind': 'admin', **m}


def run(msgs, state=None, key=KEY):
    state = state or {'removed': [], 'moved': {}}
    return admin.apply(state, msgs, ITEMS, key, NOW, lambda it: it['title']), state


def test_a_signed_removal_is_remembered_with_its_reason():
    n, st = run([signed(act='hide', id='s1', why='noise', sec='')])
    assert n == 1 and st['removed'][0]['id'] == 's1' and st['removed'][0]['why'] == 'noise'
    assert st['removed'][0]['t'] == 'AP hub page'


def test_unsigned_wrong_key_old_or_odd_messages_do_nothing():
    bad_sig = {**signed(act='hide', id='s1', why='noise', sec=''), 'sig': '0' * 64}
    old = signed(act='hide', id='s1', why='noise', sec='', at=str(int((NOW - timedelta(days=4)).timestamp() * 1000)))
    odd = signed(act='hide', id='s1', why='because', sec='')
    unknown = signed(act='hide', id='nope', why='noise', sec='')
    n, st = run([bad_sig, old, odd, unknown, {'kind': 'admin', 'act': 'hide', 'id': 's1'}])
    assert n == 0 and st['removed'] == []
    n, st = run([signed(act='hide', id='s1', why='noise', sec='')], key='')   # no ADMIN_KEY set: nothing counts
    assert n == 0


def test_move_and_undo():
    n, st = run([signed(act='move', id='s1', why='', sec='dk')])
    assert st['moved'] == {'s1': 'dk'}
    n, st = run([signed(act='hide', id='s1', why='dup', sec=''), signed(act='undo', id='s1', why='', sec='')], st)
    assert st['removed'] == [] and st['moved'] == {}


def test_prune_forgets_old_removals():
    st = {'removed': [{'id': 'a', 'at': (NOW - timedelta(days=40)).isoformat()},
                      {'id': 'b', 'at': (NOW - timedelta(days=2)).isoformat()}], 'moved': {}}
    assert [r['id'] for r in admin.prune(st, NOW, 30)['removed']] == ['b']


def test_the_owner_picks_the_front_page_quote():
    n, st = run([signed(act='quote', id='0a1b2c3d', why='', sec='')])
    assert n == 1 and st['quote']['key'] == '0a1b2c3d'
    n, st = run([signed(act='quote', id='not-a-key', why='', sec='')], st)
    assert n == 0 and st['quote']['key'] == '0a1b2c3d'
    n, st = run([signed(act='quote', id='', why='', sec='')], st)   # back to the editor's choice
    assert n == 1 and 'quote' not in st


def test_the_owner_picks_the_main_story_and_raises_or_lowers_stories():
    sid = 'aaaabbbbccccdddd'
    n, st = run([signed(act='lead', id=sid, why='', sec=''), signed(act='rank', id=sid, why='up', sec=''),
                 signed(act='rank', id='1111222233334444', why='down', sec=''), signed(act='rank', id=sid, why='sideways', sec='')])
    assert n == 3 and st['lead']['id'] == sid and st['rank'][sid]['v'] == 'up' and st['rank']['1111222233334444']['v'] == 'down'
    n, st = run([signed(act='rank', id=sid, why='', sec=''), signed(act='lead', id='', why='', sec='')], st)
    assert sid not in st['rank'] and 'lead' not in st
    old = (NOW - timedelta(days=3)).isoformat()
    st = {'removed': [], 'moved': {}, 'rank': {sid: {'v': 'up', 'at': old}}, 'lead': {'id': sid, 'at': old}}
    st = admin.prune(st, NOW, 30)
    assert st['rank'] == {} and 'lead' not in st


def test_the_owner_chooses_a_storys_picture():
    # 18/10, the owner: 'vælge mellem 3 billeder når jeg holder nede på de store artikler på forsiden'
    sid, key = 'aaaabbbbccccdddd', '0123456789abcdef'
    n, st = run([signed(act='pic', id=sid, why=key, sec=''), signed(act='pic', id=sid, why='not-a-key', sec='')])
    assert n == 1 and st['pics'][sid]['k'] == key
    n, st = run([signed(act='pic', id=sid, why='', sec='')], st)
    assert sid not in st['pics']                                                  # back to Khabar's own choice
    st = admin.prune({'removed': [], 'moved': {}, 'pics': {sid: {'k': key, 'at': (NOW - timedelta(days=4)).isoformat()}}}, NOW, 30)
    assert st['pics'] == {}


def test_the_owner_comments_on_any_element_and_takes_a_comment_back():
    # 18/10, the owner: 'Giv mig også et felt hvor jeg kan skrive en kommentar til elementet til redaktørerne … alle
    # elementer burde kunne holdes nede og få en "kommentar" valgmulighed'
    at = str(int(NOW.timestamp() * 1000))
    note = signed(act='note', id='ev:frankrig-uroligheder-2026-10:fakta:2', why='Tallet er forældet –\n ministeriet siger 997.',
                  sec='Begivenhed · Fakta · »Anholdte 412«', at=at)
    n, st = run([note, note, signed(act='note', id='story:aaaabbbbccccdddd', why='   ', sec=''),
                 signed(act='note', id='has space', why='x', sec=''), signed(act='note', id='kal:x', why='y' * 1001, sec='')])
    assert n == 1 and st['notes'] == [{'id': f'n{at}', 'ref': 'ev:frankrig-uroligheder-2026-10:fakta:2',
                                       'text': 'Tallet er forældet – ministeriet siger 997.',
                                       'ctx': 'Begivenhed · Fakta · »Anholdte 412«', 'at': NOW.isoformat()}]
    n, st = run([signed(act='unnote', id=f'n{at}', why='', sec='')], st)
    assert n == 1 and st['notes'] == []
    old = {'id': 'n1', 'ref': 'kal:x', 'text': 'x', 'ctx': '', 'at': (NOW - timedelta(days=15)).isoformat()}
    assert admin.prune({'removed': [], 'moved': {}, 'notes': [old]}, NOW, 30)['notes'] == []


def test_the_owner_writes_a_storys_or_an_event_pages_headline():
    # 18/10, the owner: 'giv også en funktion der lader mig edit overskrifter direkte'
    sid = 'aaaabbbbccccdddd'
    n, st = run([signed(act='title', id=sid, why='Macron:  undtagelsestilstand i Paris', sec='Macron taler til nationen'),
                 signed(act='title', id='ev:frankrig-uroligheder-2026-10', why='Urolighederne i Frankrig', sec='Store uroligheder'),
                 signed(act='title', id='not-a-story', why='x', sec=''), signed(act='title', id=sid, why='to\nlinjer', sec='')])
    assert n == 2 and st['titles'][sid] == {'t': 'Macron: undtagelsestilstand i Paris', 'was': 'Macron taler til nationen',
                                            'at': NOW.isoformat()}
    assert st['titles']['ev:frankrig-uroligheder-2026-10']['t'] == 'Urolighederne i Frankrig'
    n, st = run([signed(act='title', id=sid, why='', sec='')], st)
    assert sid not in st['titles']                                                 # back to the editors' headline
    five = (NOW - timedelta(days=5)).isoformat()
    kept = admin.prune({'removed': [], 'moved': {}, 'titles': {sid: {'t': 'x', 'at': five}, 'ev:a-b': {'t': 'y', 'at': five}}}, NOW, 30)
    assert list(kept['titles']) == ['ev:a-b']                                      # a story's lasts four days, a page's 30
    assert admin.load(Path('/nonexistent')) == {'removed': [], 'moved': {}}


APP = (Path(__file__).resolve().parents[1] / 'public' / 'app.js').read_text(encoding='utf-8')
ECON = (Path(__file__).resolve().parents[1] / 'public' / 'energi' / 'index.html').read_text(encoding='utf-8')


def test_every_element_can_be_held_and_the_sheet_is_ordered_for_the_owner():
    # 18/10, the owner: 'alle elementer burde kunne holdes nede og få en "kommentar" valgmulighed … til slut så ryd op i
    # admin funktionerne så det er mere brugervenlige'
    assert "const holdable = t => adminKey && t.closest('.page')" in APP          # every page, reading text too
    sheet = APP.split('function openAct(i, h = null) {')[1].split('\n}\n')[0]
    order = ["['note', 'i-quote', 'Kommentar']", "picGrid(pics, shown, !!mine, 'pic')", "osSeg('Prioritet'", "osSeg('Sektion'",
             "Dagens historie</h4>", "osSeg('Fjern fra Khabar'"]
    at = [sheet.index(x) for x in order]
    assert at == sorted(at)                                                        # comment first, removal last
    assert "window.khabarOwnerHold = x =>" in APP and "appFn('khabarOwnerHold')" in ECON   # Økonomi's frame too
    # the app reads a comment's scope as the editors' tool does
    assert "/^(oko:|side:okonomi)/" in APP and "/^(svar:|begreb:|side:(analyses|svar|begreb))/" in APP


def test_the_owners_headline_wins_in_the_app():
    assert "const ed = ownerTitleOf(i) || edTitle(i);" in APP
    assert "const t = ownerTitleOf(i) || (first && pin" in APP                     # over the front page's own headline
    assert "const t = (owner().titles || {})['ev:' + e.id];" in APP                # an event page's title


def test_the_owner_chooses_an_event_pages_picture():
    # 19/10, the owner: 'er det meningen jeg ikke kan holde nede og vælge billede på begivenheder'
    n, st = run([signed(act='pic', id='ev:vestbredden-olivenhoest-2026-10', why='0123456789abcdef', sec=''),
                 signed(act='pic', id='ev:Not An Id', why='0123456789abcdef', sec='')])
    assert n == 1 and st['pics']['ev:vestbredden-olivenhoest-2026-10']['k'] == '0123456789abcdef'
    sheet = APP.split('function openHeld(h) {')[1].split('\n}\n')[0]
    assert "evPicChoices(h.ev)" in sheet and "picGrid(pics, shown, !!mine, 'evpic')" in sheet
    assert "if (kind === 'evpic' && h && h.ev)" in APP and "ownerAct('pic', { id: 'ev:' + h.ev.id }, val)" in APP
