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


def test_crop_keeps_the_subject_in_view():
    # a tall portrait with the face near the top: the box starts at the top, not in the middle (the neck)
    assert thumbs.crop_box((600, 1200), (330, 300), (.5, .15)) == (0, 0, 600, 545)
    # a wide picture with the face at the right: the box slides right as far as the picture allows
    assert thumbs.crop_box((1600, 900), (330, 300), (.85, .4)) == (610, 0, 1600, 900)



def test_other_outlets_pages_when_the_lead_has_none(tmp_path, monkeypatch, photo):
    pages = {'https://pol.test/a': '', 'https://dr.test/a': 'https://dr.test/photo.jpg'}   # the lead's page has none
    monkeypatch.setattr(thumbs, 'get', lambda url, limit, accept, timeout=8:
                        (f'<meta property="og:image" content="{pages[url]}">' if pages[url] else '<p>no picture</p>').encode()
                        if url in pages else photo[0])
    cards = [{'id': 'a', 'source': 'Politiken', 'link': 'https://pol.test/a', 'img': ''}]
    members = {'a': [{'id': 'a2', 'source': 'DR', 'link': 'https://dr.test/a', 'img': ''}]}
    memory = {}
    for _ in range(3):   # a run looks at one page per card; the next run goes on to the next
        memory = thumbs.attach(cards, members, set(), tmp_path, memory)
    assert cards[0]['thumb'] == thumbs.name_of('https://dr.test/photo.jpg')   # another outlet's page gave one


def test_a_picture_too_dark_to_see_is_no_picture(tmp_path, monkeypatch, photo):
    # the front page's review, 18/10: Dagens historie wore a night shot in which almost nothing could be seen
    Image = pytest.importorskip('PIL.Image')
    jpg, _ = photo
    night, dusk = io.BytesIO(), io.BytesIO()
    Image.new('RGB', (640, 360), (14, 14, 18)).save(night, 'JPEG')
    Image.new('RGB', (640, 360), (60, 60, 60)).save(dusk, 'JPEG')
    assert thumbs.shrink(night.getvalue()) is None and thumbs.shrink(dusk.getvalue()) and thumbs.shrink(jpg)
    monkeypatch.setattr(thumbs, 'get', lambda url, limit, accept, timeout=8: night.getvalue() if 'night' in url else jpg)
    cards = [{'id': 'a', 'source': 'DR', 'link': 'https://news.google.com/a', 'img': 'https://img.test/night.jpg'}]
    members = {'a': [{'id': 'a2', 'source': 'BBC', 'link': 'https://news.google.com/b', 'img': 'https://img.test/day.jpg'}]}
    memory = thumbs.attach(cards, members, set(), tmp_path, {})
    assert 'https://img.test/night.jpg' in memory['bad']
    thumbs.attach(cards, members, set(), tmp_path, memory)            # the next run takes the other outlet's picture
    assert cards[0]['thumb'] == thumbs.name_of('https://img.test/day.jpg')
    # a picture made before the rule is looked at once and set aside when it is too dark
    old = tmp_path / thumbs.name_of('https://img.test/old.jpg')
    Image.new('RGB', (330, 300), (10, 10, 10)).save(old, 'JPEG')
    cards = [{'id': 'b', 'source': 'DR', 'link': 'https://news.google.com/c', 'img': 'https://img.test/old.jpg'}]
    memory = thumbs.attach(cards, {}, set(), tmp_path, {})
    assert 'https://img.test/old.jpg' in memory['bad'] and not cards[0].get('thumb')


def test_a_picture_for_a_headline_on_it():
    # 18/10, the owner: 'Er det ikke bedre at finde billeder der passer bedre til dagens historie' – wide, sharp, light
    # enough, a scene or a small face high up; a close portrait leaves no room for the headline
    scene = thumbs.fitness(1600, 900, 120, [.5, .4, 1.78, 0, 0])
    small_face = thumbs.fitness(1600, 900, 120, [.5, .3, 1.78, 1, .15])
    portrait = thumbs.fitness(1600, 900, 120, [.45, .45, 1.78, 1, .45])
    upright = thumbs.fitness(800, 1200, 120, [.5, .4, .67, 0, 0])
    small = thumbs.fitness(500, 300, 120, [.5, .4, 1.67, 0, 0])
    night = thumbs.fitness(1600, 900, 30, [.5, .4, 1.78, 0, 0])
    assert small_face > scene > portrait and scene > upright and scene > small and scene > night


def test_the_best_picture_of_a_story_is_kept_as_a_light_copy(tmp_path, monkeypatch):
    # and 'Billederne tager alt for lang tid at loade': the outlets' originals weigh up to a few MB
    Image = pytest.importorskip('PIL.Image')
    wide, narrow = io.BytesIO(), io.BytesIO()
    Image.new('RGB', (2400, 1350), (180, 160, 140)).save(wide, 'JPEG', quality=95)
    Image.new('RGB', (420, 700), (180, 160, 140)).save(narrow, 'JPEG')
    pics = {'https://img.test/wide.jpg': wide.getvalue(), 'https://img.test/narrow.jpg': narrow.getvalue()}
    monkeypatch.setattr(thumbs, 'get', lambda url, limit, accept, timeout=8: pics[url])
    cards = [{'id': 'a', 'source': 'DR', 'link': 'https://news.google.com/a', 'img': 'https://img.test/narrow.jpg',
              'rank': 120, 'live': 'rank'}]
    members = {'a': [{'id': 'a2', 'source': 'BBC', 'link': 'https://news.google.com/b', 'img': 'https://img.test/wide.jpg'}]}
    folder = tmp_path / 't'
    memory = thumbs.attach(cards, members, set(), folder, {})
    card = cards[0]
    assert card['pic'] == 'https://img.test/wide.jpg' and card['pl']          # the wide one, though the lead's is narrow
    light = (tmp_path / 'l' / card['pl']).read_bytes()
    with Image.open(io.BytesIO(light)) as im:
        assert im.width == thumbs.LARGE_W
    assert len(light) < len(pics['https://img.test/wide.jpg']) / 3
    assert card['pl'] == 'l' + thumbs.name_of('https://img.test/wide.jpg')
    assert memory['grade']['https://img.test/wide.jpg'][0] > memory['grade']['https://img.test/narrow.jpg'][0]
    assert [f.name for f in (tmp_path / 'l').glob('*.jpg')] == [card['pl']]   # only the chosen one is kept
    # the next run grades nothing again, and a story that left takes its copy with it
    monkeypatch.setattr(thumbs, 'get', lambda *a, **k: (_ for _ in ()).throw(AssertionError('fetched again')))
    thumbs.attach(cards, members, set(), folder, memory)
    assert cards[0]['pl'] == card['pl']
    thumbs.attach([], {}, set(), folder, memory)
    assert not list((tmp_path / 'l').glob('*.jpg'))
