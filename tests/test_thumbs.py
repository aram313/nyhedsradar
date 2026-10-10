"""Card pictures: the page's share image, and the choice and lifetime of the small files."""
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import thumbs  # noqa: E402


def test_share_image():
    page = ('<head><meta name="twitter:card" content="summary">'
            '<meta content="/img/a.jpg?w=1200&amp;h=630" property="og:image"></head>')
    assert thumbs.share_image(page, 'https://news.test/2026/x') == 'https://news.test/img/a.jpg?w=1200&h=630'
    assert thumbs.share_image('<meta property="og:title" content="x">', 'https://news.test/') == ''


def test_stand_in_names():
    assert thumbs.STAND_IN.search('https://www.bt.dk/brands/bt/share.jpg')
    assert thumbs.STAND_IN.search('https://x.test/static/og-default.png?v=2')
    assert not thumbs.STAND_IN.search('https://www.al-monitor.com/sites/default/files/styles/social/2026-10/photo.jpg')
    assert not thumbs.STAND_IN.search('https://asset.dr.dk/drdk/umbraco-images/1stndkbu/20260921-150403-5.jpg?im=x')


@pytest.fixture
def photo():
    Image = pytest.importorskip('PIL.Image')
    buf, icon = io.BytesIO(), io.BytesIO()
    Image.new('RGB', (640, 360), (200, 30, 30)).save(buf, 'JPEG')
    Image.new('RGB', (64, 64)).save(icon, 'PNG')
    return buf.getvalue(), icon.getvalue()


def test_attach(tmp_path, monkeypatch, photo):
    jpg, icon = photo
    calls = []

    def fake_get(url, limit, accept, timeout=8):
        calls.append(url)
        if url == 'https://dr.test/story':
            return b'<meta property="og:image" content="https://dr.test/photo.jpg">'
        if url == 'https://img.test/icon.png':
            return icon
        if url.startswith('https://img.test/') or url == 'https://dr.test/photo.jpg':
            return jpg
        raise OSError('blocked')
    monkeypatch.setattr(thumbs, 'get', fake_get)

    cards = [
        {'id': 'a', 'source': 'Politiken', 'link': 'https://pol.test/a', 'img': ''},      # takes another outlet's
        {'id': 'b', 'source': 'DR', 'link': 'https://dr.test/story', 'img': ''},          # the page's share image
        {'id': 'c', 'source': 'Kanal', 'link': 'https://t.me/kanal/1', 'img': 'https://img.test/war.jpg'},
        {'id': 'd', 'source': 'BBC', 'link': 'https://news.google.com/x', 'img': 'https://img.test/icon.png'},
    ]
    members = {'a': [{'id': 'a2', 'source': 'BBC', 'link': 'https://bbc.test/a', 'img': 'https://img.test/bbc.jpg'}]}
    memory = thumbs.attach(cards, members, {'Kanal'}, tmp_path, {})
    got = {c['id']: c.get('thumb') for c in cards}
    assert got['a'] == thumbs.name_of('https://img.test/bbc.jpg')
    assert got['b'] == thumbs.name_of('https://dr.test/photo.jpg')
    assert got['c'] is None and 'https://img.test/war.jpg' not in calls   # channels never lend a picture
    assert got['d'] is None and 'https://img.test/icon.png' in memory['bad']   # an icon is no photo
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([got['a'], got['b']])

    calls.clear()                      # the next run reuses the files and asks nobody
    thumbs.attach(cards[:1], members, {'Kanal'}, tmp_path, memory)
    assert calls == [] and cards[0]['thumb'] == got['a']
    assert [p.name for p in tmp_path.iterdir()] == [got['a']]   # pictures no card uses are deleted


def test_stand_ins_are_no_pictures(tmp_path, monkeypatch, photo):
    pages = {'https://bt.test/1': 'https://bt.test/brands/bt/share.jpg',      # named as the site's stand-in
             'https://pol.test/1': 'https://pol.test/img/house.jpg',           # one picture for two stories:
             'https://pol.test/2': 'https://pol.test/img/house.jpg'}           # the site's default
    monkeypatch.setattr(thumbs, 'get', lambda url, limit, accept, timeout=8:
                        f'<meta property="og:image" content="{pages[url]}">'.encode() if url in pages else photo[0])
    cards = [{'id': k, 'source': 'X', 'link': k, 'img': ''} for k in pages]
    memory = thumbs.attach(cards, {}, set(), tmp_path, {})
    assert [c.get('thumb') for c in cards] == [None, None, None]
    assert not list(tmp_path.iterdir())
    thumbs.attach(cards, {}, set(), tmp_path, memory)   # and stays so in the next run
    assert [c.get('thumb') for c in cards] == [None, None, None]
