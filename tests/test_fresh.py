"""An old article Google News carries again as new (the owner, 18/10: 'undersøg de gamle artikler der kommer igen'):
a scout's item is looked up before it enters (radar/fresh.py)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import fresh  # noqa: E402

NOW = datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc)


def test_an_address_carries_its_month_or_its_day():
    assert fresh.path_date('https://energynow.ca/2026/04/deal-delay-or-strike/') == datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc)
    assert fresh.path_date('https://x.test/news/2026/10/17/story') == datetime(2026, 10, 17, 23, 59, tzinfo=timezone.utc)
    assert fresh.path_date('https://abcnews.com/Politics/story?id=131764525') is None
    assert fresh.path_date('https://x.test/2026/13/story') is None


def test_an_old_scout_item_is_found_and_a_new_or_unknown_one_kept():
    items = [{'id': 'abc', 'link': 'https://news.google.com/rss/articles/A'},            # April, by its page
             {'id': 'energy', 'link': 'https://energynow.ca/2026/04/deal/'},              # April, by its address
             {'id': 'today', 'link': 'https://news.google.com/rss/articles/B'},
             {'id': 'unknown', 'link': 'https://news.google.com/rss/articles/C'}]
    dates = {'A': datetime(2026, 4, 6, 18, 48, tzinfo=timezone.utc), 'B': datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc)}
    asked = []

    def look(link):
        asked.append(link)
        return dates.get(link.rsplit('/', 1)[-1])
    found, later = fresh.old(items, NOW, 2, look)
    assert found == {'abc', 'energy'} and later == set()
    assert not any('energynow' in a for a in asked)   # the address's month needs no request


def test_at_most_a_few_are_looked_up_a_pass_the_rest_wait(monkeypatch):
    monkeypatch.setattr(fresh, 'PER_RUN', 2)
    items = [{'id': str(n), 'link': f'https://news.google.com/rss/articles/{n}'} for n in range(5)]
    found, later = fresh.old(items, NOW, 2, lambda link: None)
    assert found == set() and later == {'2', '3', '4'}


def test_a_page_date_is_read_from_its_own_markup(monkeypatch):
    page = '<script type="application/ld+json">{"datePublished":"2026-04-06T18:48:12.000Z"}</script>'
    monkeypatch.setattr(fresh, 'get', lambda url, data=None, headers=None: page)
    assert fresh.real_date('https://abcnews.com/Politics/story?id=1') == datetime(2026, 4, 6, 18, 48, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(fresh, 'get', lambda url, data=None, headers=None: (_ for _ in ()).throw(OSError('blocked')))
    assert fresh.real_date('https://news.google.com/rss/articles/X') is None   # unknown: kept, as before
