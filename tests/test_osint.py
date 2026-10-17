"""The Kort tab's events: which headlines are armed events, and where the map puts them (no network)."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import osint  # noqa: E402

P = osint.load_places()


def where(text):
    p = osint.place_of(text, P)
    return p and p['pl']


def test_the_most_specific_place_wins():
    assert where('Israeli airstrike kills five in Khan Younis, southern Gaza') == 'Khan Younis'
    assert where('Israelsk drone dræbte en mand i Jabalia-lejren') == 'Jabalia'          # a compound names it too
    assert where('Missiler rammer Adens lufthavn i Yemen') == 'Aden'                       # and a genitive
    assert where('Israel strikes Lebanon') == 'Libanon'                                    # countries: the one acted on
    assert where('Russian drones hit port in Odesa, Ukraine') == 'Odesa'


def test_hamas_is_not_hama_and_a_speaking_capital_is_no_place():
    assert where('Hamas says talks stalled') is None
    assert where('Moscow says the strike on the depot was a provocation') is None
    assert where('Jerusalem Daily: settlers burn olive groves near Nablus') == 'Nablus'   # an outlet's name is no place


def test_violence_that_happened_is_an_event_and_threats_and_words_are_not():
    assert osint.kind_of('Israeli airstrike kills five in Khan Younis') == 'luft'
    assert osint.kind_of('Én palæstinenser dræbt i israelsk droneangreb i Gaza') == 'drone'
    assert osint.kind_of('Iran: tanker exploded after hitting a mine in Hormuz') == 'eksplosion'
    assert osint.kind_of('Trump threatens to strike Iran') is None
    assert osint.kind_of('Zelenskiy blasts US-Russian diesel deal') is None
    assert osint.kind_of('Kraftigt jordskælv har ramt Rusland') is None
    assert osint.kind_of('Workers strike at Danish port') is None
    assert osint.kind_of('Rusland siger strategiske bombefly udfører planlagt flyvning over Østersøen') is None


def test_events_keep_the_editors_headline_and_leave_out_reactions_and_single_posts():
    now = datetime.now(timezone.utc)
    iso = lambda h: (now - timedelta(hours=h)).isoformat()  # noqa: E731
    items = [
        {'id': 'a', 'title': 'Israeli strike kills 3 in Gaza City', 'published': iso(1), 'outlets': 3, 'live': 'rank',
         'source': 'Reuters', 'link': 'u', 'members': ['a2']},
        {'id': 'b', 'title': 'UN Security Council condemns Houthi attacks on Saudi Arabia', 'published': iso(1),
         'outlets': 4, 'live': 'rank'},
        {'id': 'c', 'title': 'Drone strike hits Sumy', 'published': iso(2), 'outlets': 1, 'live': None},
        {'id': 'd', 'title': 'Airstrike on Idlib market', 'published': iso(100), 'outlets': 3, 'live': 'rank'},
    ]
    ev = osint.events(items, P, {'a2': 'Israelsk angreb dræber tre i Gaza by'})
    assert [e['i'] for e in ev] == ['a']           # a reaction, a lone unconfirmed post and a story of 100 hours: out
    assert ev[0]['t'] == 'Israelsk angreb dræber tre i Gaza by' and ev[0]['pl'] == 'Gaza by' and not ev[0]['ca']


def test_a_run_writes_the_map(tmp_path):
    now = datetime.now(timezone.utc).isoformat()
    (tmp_path / 'data.json').write_text(json.dumps({'items': [
        {'id': 'x', 'title': 'Russian missile strike on Kharkiv kills two', 'published': now, 'outlets': 2, 'live': 'rank'}]}),
        encoding='utf-8')
    out = osint.run(tmp_path)
    assert json.loads((tmp_path / 'map.json').read_text(encoding='utf-8'))['events'][0]['pl'] == 'Kharkiv'
    assert out['events'][0]['k'] == 'missil'
