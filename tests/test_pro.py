"""Khabar made professional (docs/hjerne/pro-plan.md, 2026-10-17), the radar's and the editor's part: teasers without
calls to action or picture captions, commentary labelled and never a main story, a notification that says what the app
shows, a lede that does not repeat the main story's headline, an outlet named as a speaker only when it carries the
story, and the check's note when Dagens historie's timeline is another development."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / 'scripts'))

import voice  # noqa: E402
from radar import run  # noqa: E402
from radar.headlines import clean_teaser, commentary  # noqa: E402
from test_editor import NOW, TODAY, add_items, check, folder, publish, story, viden  # noqa: E402,F401 – fixtures
from test_editor_r2 import GOOD_FRONT, out_file, recap_folder, write  # noqa: E402


# ------------------------------------------------------------------ teasers and commentary

def test_a_teaser_loses_its_call_to_action_link_and_picture_caption():
    assert clean_teaser('USA har med dieselaftale nærmet sig Rusland, og Ukraine føler sig svigtet. Følg udviklingen i '
                        'krigen her.') == 'USA har med dieselaftale nærmet sig Rusland, og Ukraine føler sig svigtet.'
    memo = ('Women protest against hijab ban in schools. [Sabir Mazhar – Anadolu Agency] " data-large-file="https://i0.wp.com'
            '/x.jpg?fit=920%2C613&ssl=1" /> Dozens of people gathered outside the embassy in London')
    assert clean_teaser(memo, 'Protest outside Azerbaijan embassy') == 'Dozens of people gathered outside the embassy in London'
    assert clean_teaser('Brigadier Yahya Saree gives a speech in Sanaa, Yemen on June 8, 2026. [Screengrab/AA] "', 'Houthis') == ''
    assert clean_teaser('Read the statement at https://example.test/a and more. Læs mere') == 'Read the statement at and more.'
    # a teaser that says the news stays as it is, even when it shares no word with its headline
    plain = 'Anthony Scaramucci mistede selv jobbet som pressesekretær i Det Hvide Hus.'
    assert clean_teaser(plain, 'Efter vild fyring: Trumps eks-pressechef reagerer') == plain
    assert clean_teaser(clean_teaser(memo, 'x'), 'x') == clean_teaser(memo, 'x')   # once is enough


@pytest.mark.parametrize('link, title, yes', [
    ('https://www.berlingske.dk/kommentatorer/venstres-nedtur?referrer=RSS', 'Venstres nedtur', True),
    ('https://www.theguardian.com/commentisfree/2026/oct/17/x', 'Europe must act', True),
    ('https://jyllands-posten.dk/debat/kronik/ECE1/x/', 'Et opråb', True),
    ('https://x.test/a', 'Ukraine war has changed - analysis', True),
    ('https://x.test/a', 'Analyse: Putin vinder tid', True),
    ('https://www.dr.dk/nyheder/indland/regeringen-strammer', 'Regeringen strammer', False),
    ('https://www.aljazeera.com/news/2026/10/17/analysis-of-ceasefire', 'Ceasefire holds in Gaza', False)])
def test_commentary_is_told_by_its_section_or_its_label(link, title, yes):
    assert commentary(link, title) is yes


# ------------------------------------------------------------------ the notification says what the app shows

def test_a_notification_uses_the_editors_headline_else_the_danish_else_a_plain_teaser():
    titles = run.editor_titles({'titles': {
        'a1': {'title': 'Houthierne rammer lufthavn i Aden', 'members': ['a2'], 'at': '2026-10-17T08:00:00+00:00'},
        'b1': {'title': 'Hvorfor rammer houthierne Aden?', 'at': '2026-10-17T08:00:00+00:00'}}})
    assert run.push_headline({'id': 'x', 'members': ['a2'], 'title': 'Houthis hit Aden'}, titles) == 'Houthierne rammer lufthavn i Aden'
    # never the machine's translation (the owner, 18/10: 'i dag er de for svage'): the editor's curiosity headline is
    # skipped as the app skips it, and a story in another language waits for a reviewed headline – a Danish outlet's own
    assert run.push_headline({'id': 'b1', 'title': 'Houthis hit Aden', 'title_da': 'Houthierne rammer Aden'}, titles) == ''
    assert run.push_headline({'id': 'b2', 'title': 'Houthis hit Aden', 'also': [{'lang': 'da', 'title': 'Houthierne rammer Aden'}]},
                             titles) == 'Houthierne rammer Aden'
    assert run.push_headline({'id': 'c', 'lang': 'da', 'title': 'Hvorfor brænder Aden?', 'summary': 'Houthi-missiler ramte '
                              'lufthavnen i Aden fredag. Mere følger.'}, {}) == 'Houthi-missiler ramte lufthavnen i Aden fredag'


# ------------------------------------------------------------------ the editor's front page

def test_the_lede_restates_the_main_story_only_when_its_first_clause_is_the_headline():
    head = 'Trump sætter nye sanktioner mod Rusland på pause; Putins rådgiver kalder det historisk'
    assert voice.restates('Trump sætter nye sanktioner mod Rusland på pause, houthi-angreb rammer Saudi-Arabien.', head)
    assert not voice.restates('Houthi-angreb rammer Saudi-Arabien og Aden, og Unicef melder om 340 dræbte børn.', head)
    assert not voice.restates('Angreb på Riyadh og en ny lov i Folketinget.', 'Houthi-angreb rammer Riyadh; 12 dræbt')


def test_a_story_is_commentary_only_when_every_readable_article_is():
    col = {'link': 'https://www.berlingske.dk/kommentatorer/x', 'title': 'En ridse i lakken', 'lang': 'da'}
    news = {'link': 'https://www.dr.dk/nyheder/politik/x', 'title': 'Messerschmidt frifundet', 'lang': 'da'}
    arabic = {'link': 'https://x.test/a', 'title': 'خبر', 'lang': 'ar'}
    assert run.story_kind(col, [news]) is None              # a column leads a news story: still news
    assert run.story_kind(col, [arabic]) == 'kommentar'     # its only readable article is a column
    assert run.story_kind(col, [dict(col, link='https://politiken.dk/debat/x')]) == 'kommentar'
    src = (ROOT / 'src' / 'radar' / 'run.py').read_text(encoding='utf-8')
    assert "if commentary(x.get('link'), x.get('title')):" in src and "s.get('lead_comment', 0.6)" in src   # news leads
    assert "if it.get('kind') == 'kommentar':\n            continue   # an opinion piece" in src            # never notified


def test_topnyhed_in_a_notification_is_the_apps_five_of_the_day():
    from datetime import datetime, timedelta, timezone
    now = run.NOW
    local = now.astimezone(timezone(timedelta(hours=2)))
    at = lambda h: (now - timedelta(hours=h)).isoformat()  # noqa: E731
    # 18/10, the owner: the coverage weighs less than the editor's picks or the books' heaviest tiers
    S = lambda i, h=1, **k: {'id': i, 'rank': 100, 'published': at(h), 'found': at(h), **k}  # noqa: E731
    shown = [S(f'big{k}', big=True, rank=200 + k) for k in range(4)]                        # coverage alone: never high
    shown += [S('pick', rank=50), S('pick-old', h=20, rank=60),                           # the editor's: 24 hours
              S('tier', tier=2, rank=90), S('tier-big', tier=1, big=True, rank=80),       # the books' heaviest
              S('tier-alone', tier=3, confirmed=0), S('tier-old', h=13, tier=1),           # unconfirmed, too old
              S('col', tier=1, kind='kommentar'), S('tier5', tier=5, big=True)]
    tops = run.top_now(shown, [{'id': 'pick'}, {'id': 'pick-old'}], local)
    assert tops == {'pick', 'pick-old', 'tier-big', 'tier'}, tops
    assert run.top_score(S('x', tier=6, big=True), lambda it: 99) == 3   # Danish policy on Islam: a heavy tier
    src = (ROOT / 'src' / 'radar' / 'run.py').read_text(encoding='utf-8')
    assert "'Høj betydning' if lead['id'] in tops else 'Vigtig nyhed'" in src
    # a new answer's notification is in Danish: its title machine-translated, else a plain Danish line
    assert "translator([en], 'en', 'da')[0]" in src and "'body': tidy(da) if da else analyses.NO_TITLE" in src


def test_an_outlet_is_a_speaker_only_when_it_carries_the_story():
    labels = {'reuters', 'anadolu', 'bbc'}
    got = []
    voice.check_prefix('Reuters: Israel bomber Gaza', ['Anadolu', 'BBC'], labels, 't', got)
    assert got and "'Reuters:' names an outlet" in got[0]
    got = []
    for title in ('Anadolu: Israel bomber Gaza', 'Donald Trump: Grønland var gratis', 'Israel bomber Gaza'):
        voice.check_prefix(title, ['Anadolu'], labels, 't', got)
    assert got == []
    # a government's own channel is who speaks: the editor's labels are the news outlets' only, so 'Kreml: …' stays
    assert voice.NEWS_GROUPS == {'dk', 'west', 'mena', 'il', 'east', 'channel'}
    editor_src = (ROOT / 'scripts' / 'editor.py').read_text(encoding='utf-8')
    assert "if (v.get('group') or 'west') in voice.NEWS_GROUPS}" in editor_src
    voice.check_prefix('Kreml: Rusland genstarter dieseleksport', ['Reuters'], labels, 't', got)
    assert got == []


def test_a_lede_that_repeats_dagens_historie_is_refused(folder, tmp_path, capsys):
    recap_folder(folder)
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Houthi-angreb rammer Riyadh, og Folketinget vedtager en lov.', 'front': GOOD_FRONT,
                                   'quotes': [{'who': 'Kreml', 'text': 'Samtalerne fortsætter.', 'sec': 'world', 'ids': ['w3']}]})
    assert "lede: its first clause says what Dagens historie's headline says" in capsys.readouterr().out


def test_commentary_is_never_a_main_story(folder, tmp_path, capsys):
    recap_folder(folder)
    add_items(folder, story('k1', 'Venstres nedtur', '2026-10-10T19:30:00+00:00', sec='dk', kind='kommentar', big=True))
    with pytest.raises(SystemExit):
        publish(folder, tmp_path, {'lede': 'Dagen kort.', 'front': {'blocks': [{'kind': 'top', 'story': 'k1'}]}})
    assert 'story k1 is commentary' in capsys.readouterr().out


def test_the_check_notes_a_timeline_that_is_another_development(folder, capsys):
    recap_folder(folder)
    write(folder, 'front.json', {'updated': NOW, 'blocks': [{'kind': 'top', 'story': 'm1', 'timeline': 'Ukraine'}]})
    out = check(folder, capsys)
    assert any("NOTE: Dagens historie's timeline 'Ukraine' shares few words with its story" in x for x in out)


def test_the_app_json_carries_the_kind_and_search_the_danish_headline():
    src = (ROOT / 'src' / 'radar' / 'run.py').read_text(encoding='utf-8')
    assert "'live', 'kind')" in src and "it['kind'] = story_kind(it, members_of.get(it['id'], []))" in src
    assert "'da': v.get('title_da'), 's': label_of" in src
    flow = (ROOT / '.github' / 'workflows' / 'radar.yml').read_text(encoding='utf-8')
    assert 'FETCH_HEAD:summaries.json > .cache/summaries.json' in flow and 'RADAR_SUMMARIES: .cache/summaries.json' in flow


# ------------------------------------------------------------------ notifications by the reader's choice (pro-plan 5.5)

def test_a_phone_gets_the_kinds_it_chose_and_an_older_one_what_it_had():
    from radar import analyses, push
    sub = lambda n: {'endpoint': f'https://fcm.googleapis.com/x/{n}', 'keys': {'p256dh': 'k', 'auth': 'a'}}  # noqa: E731
    phones = push.sign_up([], [{'kind': 'sub', 'sub': sub(1)}, {'kind': 'sub', 'sub': sub(2), 'want': ['svar']}], 'now', 0)
    assert 'want' not in phones[0] and phones[1]['want'] == ['svar']
    phones = push.sign_up(phones, [{'kind': 'sub', 'sub': sub(1), 'want': ['top', 'svar', 'nonsense']}], 'now', 0)
    assert len(phones) == 2 and phones[0]['want'] == ['top', 'svar']          # a new choice, the same place
    ends = lambda kind: [p['endpoint'][-1] for p in push.everyone(phones, kind)]  # noqa: E731
    assert ends('top') == ['1'] and ends('svar') == ['1', '2'] and ends('digest') == [] and ends(None) == ['1', '2']
    old = push.sign_up([], [{'kind': 'sub', 'sub': sub(3)}], 'now', 0)       # signed up before the switches
    assert [p['endpoint'][-1] for p in push.everyone(old, 'digest')] == ['3'] and push.everyone(old, 'svar') == []
    # a new answer is told once, while it is new; its title as the notification says it
    from datetime import datetime, timezone
    now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    memory = {'items': [{'id': '1', 'title': 'Answer to Question: the Jewish Entity and Gaza', 'text': 't', 'fetched': '2026-10-17T10:00:00+00:00'},
                        {'id': '2', 'title': 'Old', 'text': 't', 'fetched': '2026-10-10T10:00:00+00:00'},
                        {'id': '3', 'title': 'Known', 'text': 't', 'fetched': '2026-10-17T10:00:00+00:00', 'known': True}]}
    assert [x['id'] for x in analyses.to_tell(memory, set(), now)] == ['1']
    assert analyses.to_tell(memory, {'1'}, now) == []
    assert analyses.push_title(memory['items'][0]['title']) == 'Israel and Gaza'
