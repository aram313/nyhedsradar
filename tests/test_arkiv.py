"""The front-page archive (the owner, 18/10: 'ja lav et arkiv, men kun ved dagens sidste opdatering. så vi får et om
dagen'): every publish with a composition writes the Danish day's front page over the one before (arkiv/<date>.json on
the digest branch), arkiv/index.json lists the days, and the push carries Dagens historie's light copy along."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import editor  # noqa: E402
from test_editor import NOW, TODAY, add_items, folder, git, publish, story, viden  # noqa: E402,F401 – fixtures
from test_editor_r2 import GOOD_FRONT, out_file, recap_folder, write  # noqa: E402

LATER = '2026-10-10T21:01:00+00:00'   # 23.01 Danish summer time: the day's last update


def arkiv(tmp_path, name):
    path = tmp_path / 'out' / 'arkiv' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def front_update(**front):
    return {'lede': 'Angreb på Riyadh og en ny lov i Folketinget.', 'front': {**GOOD_FRONT, **front},
            'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world', 'ids': ['w3']}]}


def test_the_days_front_page_goes_into_the_archive_as_it_was_shown(folder, tmp_path):
    recap_folder(folder)
    publish(folder, tmp_path, front_update())
    snap = arkiv(tmp_path, '2026-10-10.json')
    assert snap['date'] == '2026-10-10' and snap['at'] == NOW and snap['lede'] == 'Angreb på Riyadh og en ny lov i Folketinget.'
    assert [b['kind'] for b in snap['blocks']] == ['top', 'liste', 'udvikling', 'citat', 'svar', 'linje']
    top, liste = snap['blocks'][:2]
    assert top['title'] == 'Houthi-angreb rammer Riyadh; 12 dræbt' and top['story'] == 'm1' and top['with'] == ['s4']
    assert liste['stories'] == ['d1', 'd2', 's1']                                   # 'd0' is a member of d1: the card's id
    assert snap['blocks'][3]['who'] == 'Kreml' and snap['blocks'][3]['text'] == 'Samtalerne fortsætter.'   # the quote itself
    assert set(snap['stories']) == {'m1', 's4', 'd1', 'd2', 's1'}
    m1 = snap['stories']['m1']
    assert m1['title'] == 'Angreb i Riyadh' and m1['source'] == 'Reuters' and m1['link'] == 'https://x.test/m1' and m1['big']
    assert [tp['name'] for tp in snap['day']['topics']] == ['Ukraine']                 # the day's recap with it
    assert arkiv(tmp_path, 'index.json')['days'] == [{'date': '2026-10-10', 'at': NOW, 'lede': snap['lede'],
                                                      'head': 'Houthi-angreb rammer Riyadh; 12 dræbt'}]


def test_the_days_last_update_stays_and_the_earlier_days_with_it(folder, tmp_path):
    recap_folder(folder)
    (folder / 'arkiv').mkdir()
    write(folder, 'arkiv/index.json', {'days': [{'date': '2026-10-09', 'at': '2026-10-09T21:00:00+00:00', 'lede': 'I går.', 'head': 'x'}]})
    publish(folder, tmp_path, front_update())
    publish(folder, tmp_path, {**front_update(), 'lede': 'Aftenens lede om Riyadh og Folketinget.'}, now=LATER)
    days = arkiv(tmp_path, 'index.json')['days']
    assert [d['date'] for d in days] == ['2026-10-10', '2026-10-09']                    # one a day, newest first
    assert days[0]['at'] == LATER and days[0]['lede'] == 'Aftenens lede om Riyadh og Folketinget.'
    assert arkiv(tmp_path, '2026-10-10.json')['at'] == LATER
    assert sorted(p.name for p in (tmp_path / 'out' / 'arkiv').iterdir()) == ['2026-10-10.json', 'index.json']


def test_after_midnight_the_update_files_the_new_day(folder, tmp_path):
    recap_folder(folder)
    publish(folder, tmp_path, front_update(), now='2026-10-10T22:05:00+00:00')         # 00.05 on the 11th, Danish time
    assert arkiv(tmp_path, '2026-10-11.json') and not arkiv(tmp_path, '2026-10-10.json')


def test_no_composition_no_archive(folder, tmp_path):
    publish(folder, tmp_path, {'lede': 'Dagen kort.'})
    assert not (tmp_path / 'out' / 'arkiv').exists()


def test_the_live_block_keeps_the_newest_stories_no_other_block_shows(folder, tmp_path):
    recap_folder(folder)
    publish(folder, tmp_path, front_update(blocks=[*GOOD_FRONT['blocks'][:2], {'kind': 'live', 'n': 2}]))
    live = arkiv(tmp_path, '2026-10-10.json')['blocks'][-1]
    assert live['kind'] == 'live' and live['stories'] == ['s3', 's2']   # not s4: unconfirmed; the others are in blocks


def test_an_archived_story_keeps_the_headline_and_summary_it_wore():
    i = {'id': 'k1', 'members': ['k0'], 'title': 'Israeli strike kills 12 in Gaza', 'title_da': 'Israelsk angreb dræber 12 i Gaza',
         'summary': 'The strike hit a school.', 'lang': 'en', 'source': 'Reuters', 'link': 'https://x.test/k1',
         'published': NOW, 'sec': 'me', 'outlets': 4, 'pic': 'https://img.test/k1.jpg', 'pf': [0.5, 0.3, 1.5, 1, 0.2],
         'also': [{'id': 'k2', 'source': 'BBC', 'title': 'Strike on Gaza school', 'link': 'https://x.test/k2', 'group': 'west', 'lang': 'en'}]}
    titles = {'k0': {'title': '“israelsk” angreb dræber 12 i en skole i Gaza', 'at': NOW}}
    sums = {'k2': {'text': 'Angrebet ramte en skole i Gaza, oplyser Reuters.', 'paywall': True, 'at': NOW}}
    s = editor.arch_story(i, titles, sums)
    assert s['title'] == '“israelsk” angreb dræber 12 i en skole i Gaza' and s['how'] == 'ed'   # filed under a member
    assert s['ed'] == {'text': 'Angrebet ramte en skole i Gaza, oplyser Reuters.', 'paywall': True}   # by another outlet's id
    assert s['origTitle'] == 'Israeli strike kills 12 in Gaza'                              # the outlet's own, as it wrote it
    assert s['pic'] == 'https://img.test/k1.jpg' and s['also'][0]['source'] == 'BBC' and s['outlets'] == 4
    plain = editor.arch_story({**i, 'title_da': ''}, {}, {})
    assert plain['title'] == 'Israeli strike kills 12 in Gaza' and plain['how'] == '' and 'origTitle' not in plain
    danish = editor.arch_story({**i, 'members': [], 'also': []}, {}, {})
    assert danish['title'] == '“israelsk” angreb dræber 12 i Gaza' and danish['how'] == 'mt'   # the house style for Israel
    teased = editor.arch_story({**i, 'lang': 'da', 'title': 'Se billederne: Kaos i lufthavnen', 'title_da': '',
                                'summary': 'Lufthavnen i Riyadh er lukket efter et angreb. Tolv er dræbt.', 'members': [], 'also': []}, {}, {})
    assert teased['title'] == 'Lufthavnen i Riyadh er lukket efter et angreb.'                # a curiosity headline gives way


def test_an_event_under_way_the_editor_did_not_place_is_archived_where_the_app_set_it(folder, tmp_path):
    recap_folder(folder)
    write(folder, 'events.json', {'items': [{'id': 'uro-frankrig', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig',
                                             'status': 'i gang', 'since': '2026-10-09', 'places': ['Paris', 'Lyon'], 'stories': ['m1'],
                                             'at': NOW, 'pic': 'https://img.test/e.jpg', 'pl': 'le.jpg'}]})
    write(folder, 'places.json', {'places': {'paris|frankrig': [48.86, 2.32, 'city'], 'frankrig|frankrig': [46.6, 1.9, 'country']}})
    publish(folder, tmp_path, front_update())
    snap = arkiv(tmp_path, '2026-10-10.json')
    assert {'kind': 'begivenhed', 'event': 'uro-frankrig', 'auto': 'i gang'} in snap['blocks']
    e = snap['events'][0]
    assert e['id'] == 'uro-frankrig' and e['img'] == '2026-10-10-uro-frankrig.jpg' and 'pl' not in e
    assert e['geo'] == {'Paris': [48.86, 2.32, 'city'], 'Frankrig': [46.6, 1.9, 'country']}   # the map of that day


def test_push_carries_the_archive_and_its_picture_and_drops_the_days_unused_one(tmp_path, monkeypatch):
    remote, clone = tmp_path / 'remote.git', tmp_path / 'clone'
    git(tmp_path, 'init', '-q', '--bare', str(remote))
    git(tmp_path, 'init', '-q', str(clone))
    git(clone, 'remote', 'add', 'origin', str(remote))

    def branch(name, files):
        blobs = {n: git(clone, 'hash-object', '-w', '--stdin', data=body) for n, body in files.items()}
        sub = {}
        for n, b in blobs.items():
            sub.setdefault(os.path.dirname(n), {})[os.path.basename(n)] = b

        def tree(d):
            rows = [f'100644 blob {b}\t{n}' for n, b in sub.get(d, {}).items()]
            rows += [f"040000 tree {tree(k)}\t{os.path.basename(k)}" for k in sub if k and os.path.dirname(k) == d]
            return git(clone, 'mktree', data=('\n'.join(sorted(rows, key=lambda r: r.split('\t')[1])) + '\n').encode())
        for k in list(sub):   # every folder on the way down
            while k:
                k = os.path.dirname(k)
                sub.setdefault(k, {})
        git(clone, 'push', '-q', 'origin', f"{git(clone, 'commit-tree', tree(''), '-m', name)}:refs/heads/{name}")
    branch('digest', {'other.json': b'{}', 'arkiv/index.json': b'{"days": []}', 'arkiv/2026-10-09.json': b'{"date": "2026-10-09"}',
                      'arkiv/img/2026-10-09-x.jpg': b'yesterday', 'arkiv/img/2026-10-10-old.jpg': b'an earlier main story'})
    branch('data', {'data.json': b'{}', 'l/lm1.jpg': b'the light copy'})
    git(clone, 'fetch', '-q', 'origin', '+refs/heads/digest:refs/remotes/origin/digest', '+refs/heads/data:refs/remotes/origin/data')
    out = tmp_path / 'out'
    (out / 'arkiv').mkdir(parents=True)
    (out / 'digest.json').write_text('{"new": true}', encoding='utf-8')
    (out / 'arkiv' / '2026-10-10.json').write_text('{"date": "2026-10-10"}', encoding='utf-8')
    (out / 'arkiv' / 'index.json').write_text('{"days": [1]}', encoding='utf-8')
    monkeypatch.chdir(clone)
    editor.push(out, 'Opdatering 10.10 23.01', {'arkiv/img/2026-10-10-m1.jpg': 'l/lm1.jpg', 'arkiv/img/2026-10-10-gone.jpg': 'l/none.jpg'})
    names = git(remote, 'ls-tree', '-r', '--name-only', 'digest').split()
    assert names == sorted(['other.json', 'digest.json', 'arkiv/index.json', 'arkiv/2026-10-09.json', 'arkiv/2026-10-10.json',
                            'arkiv/img/2026-10-09-x.jpg', 'arkiv/img/2026-10-10-m1.jpg'])   # the day's unused picture goes
    assert git(remote, 'show', 'digest:arkiv/img/2026-10-10-m1.jpg') == 'the light copy'     # the data branch's own blob
    assert git(remote, 'show', 'digest:arkiv/index.json') == '{"days": [1]}'
    assert git(remote, 'show', 'digest:arkiv/2026-10-09.json') == '{"date": "2026-10-09"}'


APP = (Path(__file__).resolve().parents[1] / 'public' / 'app.js').read_text(encoding='utf-8')
INDEX = (Path(__file__).resolve().parents[1] / 'public' / 'index.html').read_text(encoding='utf-8')


def test_the_app_shows_the_archive_quietly_beside_the_front_page():
    assert r"CFG.digestUrl.replace(/digest\.json$/, 'arkiv/')" in APP                   # the digest branch's arkiv/
    assert "ark: () => ARK && ARK + 'index.json'" in APP and "ARK + k.slice(3) + '.json'" in APP
    assert 'forsider: arkListPage, forside: arkPage' in APP and "'begivenhed', 'forsider', 'forside']);" in APP
    assert 'return arkRow() + `<p class="foot">' in APP                                 # the way in: the front page's foot
    assert 'dayBody(day) + arkLinkFor(day.date)' in APP                                 # and an earlier day on Udvikling
    assert 'd.date < dkYmd(new Date())' in APP                                          # today is the front page itself
    assert '<section class="page side fp" data-tab="forside"' in INDEX                  # in the front page's look
    # an archived story opens in place under an id of its own, with the summary it wore, and is never new
    assert 'el.dataset.ark && arkItem(el.dataset.ark, el.dataset.id)' in APP and 'const isNew = i => !i.ark &&' in APP
    assert 'const sumOf = i => i.ed ||' in APP and "id: arkId(date, id), sid: id" in APP
    # an archived event as it stood that day: its state, its countdown and its map
    assert "const today = e._day ? calDay(e._day) : calToday();" in APP and "(e.geo || {})[p]" in APP
    assert 'eventOf(evId) || arkEvent(evId)' in APP
