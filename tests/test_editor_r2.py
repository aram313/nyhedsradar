"""The editor, round 2 (the owner's rules of 2026-10-17): an informative headline for every story Live shows, the day's
level with take and drop (live.json), the front page the editor composes (front.json), and the look that calls for an
update when stories wait for their headline."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import editor  # noqa: E402
from test_editor import NOW, TODAY, add_items, check, folder, publish, story, viden  # noqa: E402,F401 – fixtures


def out_file(tmp_path, name):
    path = tmp_path / 'out' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def write(folder, name, obj):
    (folder / name).write_text(json.dumps(obj), encoding='utf-8')


def admit(folder, *ids, **live):
    """The radar's slim app.json: these stories are in Live."""
    write(folder, 'app.json', {'updated': NOW, 'items': [{'id': i} for i in ids], **({'live': live} if live else {})})


# ------------------------------------------------------------------ the day's level, take and drop

def test_the_level_take_and_drop_go_into_live_json_for_the_danish_day(folder, tmp_path):
    add_items(folder, story('c1', 'Kort', '2026-10-10T19:00:00+00:00', members=['c0', 'c1']))
    write(folder, 'live.json', {'updated': '2026-10-09T20:00:00+00:00', 'days': {
        '2026-10-09': {'level': 'få', 'take': [], 'drop': [], 'note': 'Stille dag.'},
        '2026-10-08': {'level': 'mange', 'take': [], 'drop': [], 'note': ''}}})
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'level': 'mange', 'take': ['s4', 'c0'], 'drop': ['s3'],
                               'note': 'Mange angreb og to topmøder.'})
    live = out_file(tmp_path, 'live.json')
    assert live['updated'] == NOW and list(live['days']) == ['2026-10-10', '2026-10-09']   # two Danish days kept
    day = live['days']['2026-10-10']
    assert day == {'level': 'mange', 'take': ['s4', 'c1'], 'drop': ['s3'], 'note': 'Mange angreb og to topmøder.', 'at': NOW}
    write(folder, 'live.json', live)
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'take': ['s3'], 'drop': ['c1']}, now='2026-10-10T20:16:00+00:00')
    day = out_file(tmp_path, 'live.json')['days']['2026-10-10']
    assert day['level'] == 'mange' and day['take'] == ['s4', 's3'] and day['drop'] == ['c1']   # added to today's
    assert day['note'] == 'Mange angreb og to topmøder.'


def test_live_json_is_written_at_every_update_and_a_bad_level_is_refused(folder, tmp_path, capsys):
    publish(folder, tmp_path, {'lede': 'Dagen kort.'})
    assert out_file(tmp_path, 'live.json') == {'updated': NOW, 'days': {}}       # nothing set today: the radar's normal
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'level': 'masser', 'take': ['nope', 's1'], 'drop': ['s1'],
                                   'note': 'Rusland er nu en mellemmagt. ' * 8})
    out = capsys.readouterr().out
    assert "level: få, normal or mange – not 'masser'" in out and "take: unknown story id 'nope'" in out
    assert 'take and drop: s1' in out and 'note: one line (at most 160' in out and "'mellemmagt' is a reading" in out


def test_the_input_shows_the_level_and_the_stories_at_the_line(folder):
    add_items(folder, story('a1', 'Svag i Live', '2026-10-10T18:00:00+00:00', rank=61),
              story('a2', 'Stærk i Live', '2026-10-10T18:00:00+00:00', rank=88),
              story('b1', 'Lige under stregen', '2026-10-10T18:00:00+00:00', rank=59),
              story('b2', 'Langt under', '2026-10-10T18:00:00+00:00', rank=20),
              story('g1', 'Stor', '2026-10-10T18:00:00+00:00', rank=40, big=True))
    admit(folder, 's1', 'a1', 'a2', 'g1', line=60)
    write(folder, 'live.json', {'days': {'2026-10-10': {'level': 'mange', 'take': ['b2'], 'drop': [], 'note': 'Tung dag.'}}})
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    live = text.split('## Live – how much the app shows today')[1].split('## The front page')[0]
    assert "Today's level: mange (yours: Tung dag.) · taken in: b2" in live
    assert "4 stories in Live from the last 24 hours · the radar's line at rank 60" in live
    above = live.split('Just above the line')[1].split('Just below the line')[0]
    assert above.index('[a1]') < above.index('[a2]') and '[g1]' not in above      # weakest first; a big story never at it
    below = live.split('Just below the line')[1]
    assert below.index('[s4]') < below.index('[b1]') < below.index('[b2]')       # strongest left out first
    heads = text.split('## Headlines to write')[1].split('## Live')[0]
    assert '[g1]' in heads and '[a1]' in heads and '[b1]' not in heads            # only the stories in Live


# ------------------------------------------------------------------ the look: stories waiting for their headline

def test_the_look_calls_for_an_update_when_eight_stories_wait_for_a_headline(folder, capsys):
    ids = [f'h{k}' for k in range(8)]
    add_items(folder, *[story(i, f'Historie {i}', '2026-10-10T19:55:00+00:00') for i in ids])
    write(folder, 'summaries.json', {'items': {}, 'titles': {'h0': {'title': 'Har sin', 'at': NOW}}})
    admit(folder, *ids)
    out = check(folder, capsys)
    assert out[3] == 'Live: level normal (default) · 8 admitted in 24 h · 7 wait for a headline (longest 6 min)'
    assert 'venter på redaktørens overskrift' not in out[-1]                      # seven: not yet
    admit(folder, *ids, 's1')
    out = check(folder, capsys)
    assert '8 historier i Live venter på redaktørens overskrift' in out[-1]


def test_one_story_waiting_over_45_minutes_calls_for_an_update_by_day_only(folder, capsys):
    admit(folder, 's1')   # found 14.01 Danish time
    out = check(folder, capsys, now='2026-10-10T12:50:00+00:00')                  # 14.50: 49 minutes
    assert out[-1] == 'OPDATÉR: en historie i Live har ventet 49 min på redaktørens overskrift'
    assert check(folder, capsys, now='2026-10-10T12:40:00+00:00')[-1] == 'INTET NYT AF VÆGT'   # 39 minutes
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    data['items'][0].update(found='2026-10-10T23:00:00+00:00', published='2026-10-10T23:00:00+00:00')
    write(folder, 'data.json', data)
    night = {**TODAY, 'date': '2026-10-11', 'updates': ['2026-10-10T22:03:00+00:00'], 'topics': [], 'ids': ['w1', 'w2', 'w3', 'w4']}
    write(folder, 'moves.json', {'days': [night, TODAY]})
    assert check(folder, capsys, now='2026-10-11T01:00:00+00:00')[-1] == 'INTET NYT AF VÆGT'   # 03.00: waits for 06


def test_the_gate_fires_once_for_the_headlines_of_an_update(folder, capsys):
    ids = [f'h{k}' for k in range(8)]
    add_items(folder, *[story(i, f'Historie {i}', '2026-10-10T19:55:00+00:00') for i in ids])
    admit(folder, *ids)
    editor.main(['gate', '--dir', str(folder), '--data-dir', str(folder), '--now', NOW])
    rec = json.loads((folder / 'editor-gate.json').read_text(encoding='utf-8'))['fires'][-1]
    assert 'heads:2026-10-10T11:35:00+00:00' in rec['keys']
    rec['ok'] = True   # as if the routine had been fired
    write(folder, 'editor-gate.json', {'fires': [{**rec, 'at': '2026-10-10T19:30:00+00:00'}]})
    capsys.readouterr()
    editor.main(['gate', '--dir', str(folder), '--data-dir', str(folder), '--now', NOW])
    assert 'Gate: no fire' in capsys.readouterr().out


def test_the_wait_counts_from_the_radars_admission_and_the_line_is_read_as_the_radar_writes_it(folder, capsys):
    data = json.loads((folder / 'data.json').read_text(encoding='utf-8'))
    for i in data['items']:
        i['live'] = 'rank' if i['id'] == 's1' else None                         # the radar's rank line in data.json
    data['live'] = {'level': 'normal', 'why': 'forældet', 'floor': 96, 'count': 45, 'line': 96, 'n_24h': 1}
    write(folder, 'data.json', data)
    write(folder, 'admitted.json', {'s1': '2026-10-10T12:45:00+00:00'})          # admitted 14.45, found 14.01
    write(folder, 'live.json', {'updated': '2026-10-10T10:00:00+00:00',
                                'days': {'2026-10-10': {'level': 'mange', 'take': [], 'drop': [], 'note': ''}}})
    out = check(folder, capsys, now='2026-10-10T13:20:00+00:00')                  # 15.20: 35 minutes since admitted
    assert out[3] == ("Live: level mange (set by the editor) · 1 admitted in 24 h · the radar's line: rank 96 · "
                      '1 wait for a headline (longest 35 min)')
    assert out[-1] == 'INTET NYT AF VÆGT'
    editor.main(['input', '--dir', str(folder), '--now', '2026-10-10T13:20:00+00:00'])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    assert ("1 stories in Live from the last 24 hours · the radar's line at rank 96 · the level's soft count 45 · "
            'the radar applies normal (forældet)') in text
    assert '[s1] dk · DR (?) · 1 outlets · waited 35 min' in text


def test_without_the_radars_line_the_headlines_call_for_nothing(folder, capsys):
    add_items(folder, *[story(f'h{k}', f'Historie {k}', '2026-10-10T19:55:00+00:00') for k in range(9)])
    out = check(folder, capsys, now='2026-10-10T20:01:00+00:00')
    assert 'the radar draws no line yet' in out[3] and 'venter på redaktørens overskrift' not in out[-1]


# ------------------------------------------------------------------ the front page the editor composes

def recap_folder(folder):
    add_items(folder, story('d1', 'Folketinget vedtager lov', '2026-10-10T19:00:00+00:00', sec='dk', members=['d0', 'd1']),
              story('d2', 'Minister om moskeer', '2026-10-10T19:10:00+00:00', sec='dk'),
              story('m1', 'Angreb i Riyadh', '2026-10-10T19:20:00+00:00', sec='me', big=True))
    write(folder, 'analyses.json', {'items': [{'id': '30555', 'date': '2026-10-09', 'title': 'Iran'}]})


GOOD_FRONT = {'blocks': [
    {'kind': 'top', 'story': 'm1', 'title': 'Houthi-angreb rammer Riyadh; 12 dræbt', 'with': ['s4'], 'timeline': 'ukraine'},
    {'kind': 'liste', 'title': 'Danmark', 'stories': ['d0', 'd2', 's1']},
    {'kind': 'udvikling', 'topics': ['Ukraine']},
    {'kind': 'citat', 'quote': 'q1'},
    {'kind': 'svar', 'nr': '30555'},
    {'kind': 'linje', 'text': '14 nye angreb på Riyadh i dag'}]}


def test_the_editors_composition_is_checked_and_written_to_front_json(folder, tmp_path):
    recap_folder(folder)
    publish(folder, tmp_path, {'lede': 'Angreb på Riyadh og en ny lov i Folketinget.', 'front': GOOD_FRONT,
                               'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world', 'ids': ['w3']}]})
    front = out_file(tmp_path, 'front.json')
    assert front['updated'] == NOW and front['lede'] == 'Angreb på Riyadh og en ny lov i Folketinget.'
    top, liste, udv, citat, svar, linje = front['blocks']
    assert top == {'kind': 'top', 'title': 'Houthi-angreb rammer Riyadh; 12 dræbt', 'story': 'm1', 'with': ['s4'],
                   'timeline': 'Ukraine', 'picture': True}                       # the topic's name as the recap writes it
    assert liste == {'kind': 'liste', 'title': 'Danmark', 'stories': ['d1', 'd2', 's1'], 'style': 'kompakt'}   # by member
    assert udv == {'kind': 'udvikling', 'topics': ['Ukraine']}
    assert citat['quote'] == 'q1' and citat['who'] == 'Kreml' and citat['link'] == 'https://t.me/ajanews/w3'
    assert svar == {'kind': 'svar', 'nr': '30555'}
    assert linje == {'kind': 'linje', 'text': '14 nye angreb på Riyadh i dag'}
    assert out_file(tmp_path, 'digest.json')['editor']['quotes'][0]['id'] == 'q1'


def test_a_composition_that_breaks_the_rules_is_refused(folder, tmp_path, capsys):
    recap_folder(folder)
    bad = {'blocks': [
        {'kind': 'hero', 'story': 'm1'},
        {'kind': 'top', 'story': 'm1', 'title': 'Se billederne: Kaos i Riyadh'},
        {'kind': 'top', 'story': 'd1'}, {'kind': 'top', 'story': 'nope'},
        {'kind': 'liste', 'title': 'I dag', 'stories': ['d0', 'm1']},
        {'kind': 'udvikling', 'topics': ['Sudan']},
        {'kind': 'svar', 'nr': '99999'},
        {'kind': 'linje', 'text': 'Saudi-Arabien er en underordnet stat under USA'},
        {'kind': 'citat', 'quote': 'q9'}]}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'front': bad})
    out = capsys.readouterr().out
    assert "front: 9 blocks – at most 6" in out and "front block 1: kind 'hero'" in out
    assert 'front block 2 (top) title' in out and 'curiosity headline' in out
    assert "front block 4 (top): story – unknown story id 'nope'" in out
    assert "looks like a day marker" in out
    assert 'front block 5 (liste): stories d0 is in block 3 already' in out and 'm1 is in block 2 already' in out
    assert "'Sudan' is no topic of the recap" in out and "nr '99999' is no answer" in out
    assert "front block 8 (linje) text: 'underordnet stat' is a reading or judgement word" in out
    assert "front: 3 'top' blocks" in out


def test_a_front_page_story_must_be_in_live_unless_taken_in(folder, tmp_path, capsys):
    recap_folder(folder)
    admit(folder, 's1', 'd1')
    front = {'blocks': [{'kind': 'liste', 'title': 'Danmark', 'stories': ['d1', 'd2']}, {'kind': 'top', 'story': 'm1'}]}
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'front': front})
    assert 'stories d2 is not in Live today' in capsys.readouterr().out          # m1 is big: always in
    publish(folder, tmp_path, {'lede': 'Dagen kort.', 'front': front, 'take': ['d2']})
    assert out_file(tmp_path, 'front.json')['blocks'][0]['stories'] == ['d1', 'd2']


def test_a_kept_composition_is_re_dated_without_the_stories_that_left_and_yesterdays_is_not_kept(folder, tmp_path):
    write(folder, 'front.json', {'updated': '2026-10-10T18:00:00+00:00', 'lede': 'Gammel.', 'blocks': [
        {'kind': 'top', 'story': 'gone', 'with': []},
        {'kind': 'liste', 'title': 'Danmark', 'stories': ['s1', 'gone2'], 'style': 'kompakt'},
        {'kind': 'live', 'n': 3}]})
    publish(folder, tmp_path, {'lede': 'Ny lede.'})
    front = out_file(tmp_path, 'front.json')
    assert front['updated'] == NOW and front['lede'] == 'Ny lede.'
    assert front['blocks'] == [{'kind': 'liste', 'title': 'Danmark', 'stories': ['s1'], 'style': 'kompakt'},
                               {'kind': 'live', 'n': 3}]
    write(folder, 'front.json', {**front, 'updated': '2026-10-09T18:00:00+00:00'})
    publish(folder, tmp_path, {'lede': 'Ny lede.'})
    assert out_file(tmp_path, 'front.json') is None   # an earlier day's: the app's fixed page until a new one; not pushed


def test_the_front_pages_lede_is_the_updates(folder, tmp_path, capsys):
    (folder / 'digest.json').write_text(json.dumps({**TODAY, 'editor': {
        'created': '2026-10-10T11:35:00+00:00', 'lede': 'Formiddagens lede.', 'lede_at': '2026-10-10T11:35:00+00:00'}}),
        encoding='utf-8')
    publish(folder, tmp_path, {'front': {'lede': 'Aftenens lede.', 'blocks': [{'kind': 'live', 'n': 5}]}})
    assert out_file(tmp_path, 'front.json')['lede'] == 'Aftenens lede.'
    assert out_file(tmp_path, 'digest.json')['editor']['lede'] == 'Aftenens lede.'
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'En.', 'front': {'lede': 'En anden.', 'blocks': [{'kind': 'live'}]}})
    assert 'give the lede once' in capsys.readouterr().out


def test_the_input_shows_the_composition_and_the_palette(folder):
    recap_folder(folder)
    write(folder, 'front.json', {'updated': '2026-10-10T18:00:00+00:00', 'lede': 'x', 'blocks': [
        {'kind': 'top', 'story': 'm1', 'with': ['s4'], 'timeline': 'Ukraine', 'picture': True},
        {'kind': 'liste', 'title': 'Danmark', 'stories': ['d1', 'd2'], 'style': 'kompakt'},
        {'kind': 'live', 'n': 3}]})
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    front = text.split('## The front page – your composition ("front")')[1].split('## Al Jazeera')[0]
    assert 'Now (composed 10.10 20.00):' in front
    assert '1. top · [m1] Angreb i Riyadh · with [s4] Kun på Telegram · timeline: Ukraine' in front
    assert "2. liste · 'Danmark' (kompakt): [d1] Folketinget vedtager lov; [d2] Minister om moskeer" in front
    assert '- linje: one short line of reality' in front and 'never like a day marker' in front
    assert 'Denmark only when it matters' in front and 'Danish politics never buried' not in front   # the owner, 17/10
    assert 'the app draws 6 blocks' in front and 'the first three' in front
    assert '"front"' in text.split('## Write /tmp/editor/update.json')[1]


def test_the_check_names_the_composition(folder, capsys):
    write(folder, 'front.json', {'updated': '2026-10-10T12:00:00+00:00', 'blocks': [
        {'kind': 'top', 'story': 's1'}, {'kind': 'liste', 'title': 'Danmark', 'stories': ['s3']}]})
    out = check(folder, capsys)
    assert "  Composition (10.10 14.00): top, liste 'Danmark' – OLDER THAN 6 HOURS: the app shows its fixed page" in out


# ------------------------------------------------------------------ the reviewers' findings of 2026-10-17

@pytest.mark.parametrize('title', [
    'Besættelsesstyrker anholder to palæstinensere i Silwad', 'Den zionistiske fjende bomber Gaza',
    'Zionist-regimet dræber 12 i Gaza', 'Zionistiske bosættere angriber landsby nær Nablus',
    'Heroisk modstand slår israelske styrker tilbage', 'Modstandskæmpere angriber i en heroisk operation',
    'Dette sker der nu i Gaza', 'Intern terror vejer tungere end ekstern jord: Israels egentlige valgtema',
    'Amerikansk fotojournalist fortæller om overgreb på Vestbredden – video'])
def test_channel_words_judgements_and_labels_are_refused_in_a_headline(title):
    problems = []
    editor.voice.check_headline(title, 'titles: x', problems)
    assert problems, title


@pytest.mark.parametrize('title', [
    'Israelske styrker anholder to palæstinensere i Silwad', 'Hamas: »Besættelsesstyrkerne« trækker sig fra Rafah',
    'Analytiker: Israels egentlige mål er Libanon', 'FN: Israel er besættelsesmagt på Vestbredden',
    'Kreml: Dette er en provokation', 'Zionismen debatteres på konference i London',
    'Israelske besættelsesstyrker sprænger hjem øst for Gaza by'])   # the source's framing word beside Israel's name
def test_attributed_and_plain_headlines_pass(title):
    problems = []
    editor.voice.check_headline(title, 'titles: x', problems)
    assert not problems, problems


def test_an_earlier_headline_that_breaks_the_rules_is_written_again_and_removed(folder, tmp_path, capsys):
    admit(folder, 's1', 's4')
    write(folder, 'summaries.json', {'items': {}, 'titles': {
        's1': {'title': 'Hvorfor forbyder Aserbajdsjan hijab i skolerne?', 'at': '2026-10-10T08:00:00+00:00'},
        's4': {'title': 'Aserbajdsjan forbyder hijab i skolerne', 'at': '2026-10-10T08:00:00+00:00'}}})
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    heads = (editor.WORK / 'input.md').read_text(encoding='utf-8').split('## Headlines to write')[1].split('## Live')[0]
    assert '[s1]' in heads and '[s4]' not in heads
    publish(folder, tmp_path, {'lede': 'Dagen kort.'})
    titles = out_file(tmp_path, 'summaries.json')['titles']
    assert 's1' not in titles and 's4' in titles
    assert "1 earlier headline(s) broke today's rules" in capsys.readouterr().out


def test_a_dropped_story_leaves_live_at_once_and_is_not_offered_back(folder):
    add_items(folder, story('g1', 'Stor', '2026-10-10T18:00:00+00:00', rank=99, big=True),
              story('b1', 'Lige under stregen', '2026-10-10T18:00:00+00:00', rank=59))
    admit(folder, 's1', 'g1', line=60)
    write(folder, 'live.json', {'updated': NOW, 'days': {
        '2026-10-09': {'level': 'normal', 'take': [], 'drop': ['b1'], 'note': ''},
        '2026-10-10': {'level': 'normal', 'take': [], 'drop': ['g1'], 'note': ''}}})
    editor.main(['input', '--dir', str(folder), '--now', NOW])
    text = (editor.WORK / 'input.md').read_text(encoding='utf-8')
    heads = text.split('## Headlines to write')[1].split('## Live')[0]
    assert '[g1]' not in heads                                                  # dropped: not in Live, no headline due
    live = text.split('## Live – how much the app shows today')[1].split('## The front page')[0]
    assert 'Still in force from yesterday: taken out b1' in live
    assert 'Just below the line' in live and '[b1]' not in live.split('Just below the line')[1]   # not offered back


def test_a_kept_composition_loses_its_lines_at_midnight(folder, tmp_path):
    write(folder, 'front.json', {'updated': '2026-10-10T21:30:00+00:00', 'lede': 'x', 'blocks': [
        {'kind': 'liste', 'title': 'Danmark', 'stories': ['s1'], 'style': 'kompakt'},
        {'kind': 'linje', 'text': '14 nye angreb på Riyadh i dag'}]})
    publish(folder, tmp_path, {'lede': 'Natten kort.'}, now='2026-10-10T23:10:00+00:00')   # 01.10 Danish time
    assert [b['kind'] for b in out_file(tmp_path, 'front.json')['blocks']] == ['liste']


def test_every_story_that_waited_too_long_fires_once(folder, capsys):
    add_items(folder, story('h1', 'Historie et', '2026-10-10T19:00:00+00:00'),
              story('h2', 'Historie to', '2026-10-10T19:05:00+00:00'))
    admit(folder, 'h1', 'h2')
    editor.main(['gate', '--dir', str(folder), '--data-dir', str(folder), '--now', NOW])
    rec = json.loads((folder / 'editor-gate.json').read_text(encoding='utf-8'))['fires'][-1]
    late = [k for k in rec['keys'] if k.startswith('late:')]
    assert len(late) >= 2, rec['keys']   # each story that waited too long has its own key


def test_a_level_about_to_lapse_calls_for_an_update(folder, capsys):
    admit(folder, 's1', line=60)
    write(folder, 'summaries.json', {'items': {}, 'titles': {'s1': {'title': 'Har sin', 'at': NOW}}})
    write(folder, 'live.json', {'updated': '2026-10-10T14:30:00+00:00',
                                'days': {'2026-10-10': {'level': 'få', 'take': [], 'drop': [], 'note': ''}}})
    out = check(folder, capsys)                                                    # 5 h 31 min since live.json
    assert 'dagens niveau (få) holder kun 6 timer efter sidste opdatering' in out[-1]


# ------------------------------------------------------------------ a story that changed its lead since the input

def test_a_story_named_by_its_old_lead_is_filed_under_its_current_id(folder, tmp_path):
    """The radar runs every five minutes and may give a story a new lead article between the editor's input and its
    publish: the editor's recap line, pick and summary then name an id that is a member now – found by it and filed
    under the story's current id (found in a real run on 17/10, where three of them refused the whole update)."""
    add_items(folder, story('c1', 'Kort', '2026-10-10T19:00:00+00:00', members=['c0', 'c1']))
    publish(folder, tmp_path, {
        'lede': 'Dagen kort.',
        'topics': [{'name': 'Et emne', 'section': 'world', 'lines': [{'who': 'Reuters', 'text': 'Noget skete.', 'story': 'c0'}]}],
        'picks': [{'id': 'c0', 'why': 'stor'}],
        'summaries': [{'id': 'c0', 'text': 'Noget skete i dag. Reuters melder det.', 'paywall': True}]})
    digest = out_file(tmp_path, 'digest.json')
    assert any(p['id'] == 'c1' for p in (digest.get('editor') or {}).get('picks') or [])
    sums = out_file(tmp_path, 'summaries.json')['items']
    assert 'c1' in sums and 'c0' not in sums
