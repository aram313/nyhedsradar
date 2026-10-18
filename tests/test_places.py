"""The event pages' places on a map (src/radar/places.py) – the owner, 18/10: 'Lad os lave kortet'."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import places  # noqa: E402

NOW = datetime(2026, 10, 18, 17, 0, tzinfo=timezone.utc)
ANSWERS = {'Lyon, Frankrig': [{'lat': '45.7578', 'lon': '4.8320', 'addresstype': 'city'}],
           'Paris, Frankrig': [{'lat': '48.8566', 'lon': '2.3522', 'addresstype': 'city'}],
           'Frankrig': [{'lat': '46.6034', 'lon': '1.8883', 'addresstype': 'country'}]}


def fake(url):
    from urllib.parse import parse_qs, urlparse
    q = parse_qs(urlparse(url).query)['q'][0]
    return ANSWERS.get(q, [])


def test_the_places_are_looked_up_once_a_second_apart_and_kept():
    events = {'items': [{'id': 'f', 'kicker': 'Frankrig', 'places': ['Paris', 'Lyon', 'Atlantis']}]}
    waits = []
    got = places.update(events, {}, NOW, fetch=fake, sleep=waits.append)
    assert got['places'] == {'paris|frankrig': [48.8566, 2.3522, 'city'], 'lyon|frankrig': [45.7578, 4.832, 'city'],
                             'frankrig|frankrig': [46.6034, 1.8883, 'country']}
    assert 'atlantis|frankrig' in got['missed'] and waits == [1.1, 1.1, 1.1]   # four asked, a second apart
    # the next run asks nothing again, and a place no page names any more is let go
    again = places.update({'items': [{'id': 'f', 'kicker': 'Frankrig', 'places': ['Paris']}]}, got, NOW,
                          fetch=lambda url: 1 / 0, sleep=waits.append)
    assert set(again['places']) == {'paris|frankrig', 'frankrig|frankrig'} and waits == [1.1, 1.1, 1.1]
