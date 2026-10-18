"""Begivenheder (the owner, 18/10: 'Hvad skal der til for at vi kan få sådan nogle faktabokse og begivenheds sider' –
'artikler til store begivenheder, hvor vi holder os objektive … fakta, begivenhed og tal'): the editor's event pages,
their fact boxes grounded in the news, the objective article, and the front page's event modules (scripts/events.py,
scripts/editor.py compose)."""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))

import events  # noqa: E402
import voice  # noqa: E402

NOW = datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 18)
STORIES = {
    'fr1': {'id': 'fr1', 'title': 'Around 550,000 people take part in protests across France, about 400 arrested: minister'},
    'fr2': {'id': 'fr2', 'title': '1.200 personer anholdt efter uroligheder i flere franske byer.',
            'also': [{'title': 'Macron: No place for violence after riots in Paris and Lyon'}]},
    'ab1': {'id': 'ab1', 'title': 'Alberta votes Monday on a path towards leaving Canada'},
}
RIOTS = {'id': 'frankrig-uroligheder-2026-10', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang',
         'since': '2026-10-16', 'dek': 'Demonstrationer mod leveomkostningerne i flere franske byer, med sammenstød og anholdelser.',
         'facts': [{'label': 'Demonstranter', 'value': '550.000', 'note': 'ifølge indenrigsministeriet', 'ids': ['fr1']},
                   {'label': 'Anholdte', 'value': '1.200', 'ids': ['fr2']}],
         'places': ['Paris', 'Lyon'], 'stories': ['fr1', 'fr2'],
         'article': [{'text': 'Omkring 550.000 mennesker demonstrerede den 17. oktober i Frankrig ifølge indenrigsministeriet.',
                      'ids': ['fr1']}]}


def make(entries, current=None, today=TODAY):
    problems = []
    out = events.events_file(entries, current, STORIES, NOW, today, problems, voice)
    return out, problems


def test_an_event_page_with_its_fact_boxes_grounded_in_the_news():
    out, problems = make([RIOTS])
    assert not problems, problems
    (e,) = out['items']
    assert [f['value'] for f in e['facts']] == ['550.000', '1.200'] and e['places'] == ['Paris', 'Lyon']
    assert e['article'][0]['ids'] == ['fr1'] and e['status'] == 'i gang' and e['since'] == '2026-10-16'


def test_a_number_the_news_do_not_carry_is_refused():
    wrong = {**RIOTS, 'facts': [{'label': 'Demonstranter', 'value': '800.000', 'ids': ['fr1']}]}
    _, problems = make([wrong])
    assert any("'800.000' stands in none of the stories" in p for p in problems), problems
    _, problems = make([{**RIOTS, 'facts': [{'label': 'Anholdte', 'value': '1.200'}]}])
    assert any('ids – the stories the number stands in' in p for p in problems), problems
    # an article's number too – but a date, a year and a clock time are no counts
    loose = {**RIOTS, 'article': [{'text': 'Den 17. oktober 2026 kl. 21.30 var 1.200 anholdt og 150 betjente såret.', 'ids': ['fr2']}]}
    _, problems = make([loose])
    assert [p for p in problems if 'article 1' in p] == [p for p in problems if '150 stand in none' in p] and problems, problems


def test_the_article_holds_to_the_event_not_to_opinions():
    said = {**RIOTS, 'article': [{'text': 'Det er tydeligt, at regeringen vil falde, og protesterne vil sprede sig.', 'ids': ['fr1']}]}
    _, problems = make([said])
    assert any('article 1' in p for p in problems), problems


def test_pages_change_by_id_are_removed_and_kept_a_few_days():
    out, _ = make([RIOTS])
    out, problems = make([{'id': RIOTS['id'], 'status': 'afsluttet'}], out)
    assert not problems and out['items'][0]['status'] == 'afsluttet' and out['items'][0]['facts']   # the rest stays
    out, problems = make([{'id': RIOTS['id'], 'remove': True}], out)
    assert out['items'] == [] and not problems
    vote = {'id': 'alberta-folkeafstemning', 'title': 'Folkeafstemning i Alberta', 'kicker': 'Canada', 'status': 'kommende',
            'date': '2026-10-19', 'dek': 'Vælgerne i Alberta stemmer om vejen mod løsrivelse fra Canada.', 'stories': ['ab1']}
    out, problems = make([vote])
    assert not problems and out['items'][0]['date'] == '2026-10-19'
    later, _ = make(None, out, today=date(2026, 10, 30))          # long past its day: gone
    assert later['items'] == []
    _, problems = make([{**vote, 'date': '2026-10-01'}])
    assert any('has passed' in p for p in problems)


def test_only_the_great_events_get_a_page():
    many = [{**RIOTS, 'id': f'uro-{n}'} for n in range(events.MAX_EVENTS + 1)]
    _, problems = make(many)
    assert any('only the great events' in p for p in problems)


def test_the_front_page_modules_name_an_event_page():
    import editor
    find = {'fr1': {**STORIES['fr1'], 'members': ['fr1']}}
    page = make([RIOTS])[0]['items'][0]
    spec = {'blocks': [{'kind': 'begivenhed', 'event': page['id']}, {'kind': 'tal', 'event': page['id'], 'fact': 2},
                       {'kind': 'nedtaelling', 'event': page['id']}, {'kind': 'tal', 'event': 'ukendt'}]}
    problems = []
    out = editor.compose(spec, None, find, None, {}, [], None, 'En lede.', NOW, problems, None, {page['id']: page})
    assert [b.get('event') for b in out['blocks']] == [page['id'], page['id'], page['id'], None]
    assert out['blocks'][1]['fact'] == 2
    assert any("a countdown is for an event ahead" in p for p in problems)
    assert any("'ukendt' is no event page" in p for p in problems)


def test_a_box_can_be_a_share_or_a_change_and_both_are_grounded():
    # the owner, 18/10: 'Gør gerne tallene … visuel interessant med professionelle stilfulde widgets'
    stories = {**STORIES, 'poll': {'id': 'poll', 'title': 'Nearly 7 in 10 French people approve Oct. 17 protests'},
               'old': {'id': 'old', 'title': 'About 400 arrested: minister', 'pic': 'https://img.test/riot.jpg'}}
    e = {**RIOTS, 'stories': ['old', 'fr1'],
         'facts': [{'label': 'Støtter protesterne', 'value': '7', 'of': '10', 'ids': ['poll']},
                   {'label': 'Anholdte', 'value': '1.200', 'was': {'value': '400', 'when': 'fredag', 'ids': ['old']}, 'ids': ['fr2']}]}
    problems = []
    out = events.events_file([e], None, stories, NOW, TODAY, problems, voice)
    assert not problems, problems
    f1, f2 = out['items'][0]['facts']
    assert f1['of'] == '10' and f2['was'] == {'value': '400', 'when': 'fredag', 'ids': ['old']}
    assert out['items'][0]['pic'] == 'https://img.test/riot.jpg'      # the first story with a picture
    bad = {**e, 'facts': [{'label': 'Støtte', 'value': '7', 'of': '12', 'ids': ['poll']},
                          {'label': 'Anholdte', 'value': '1.200', 'was': {'value': '300', 'ids': ['old']}, 'ids': ['fr2']}]}
    problems = []
    events.events_file([bad], None, stories, NOW, TODAY, problems, voice)
    assert any("of '12' stands in none" in p for p in problems) and any("was '300' stands in none" in p for p in problems), problems


def test_the_great_events_are_grouped_by_event_and_the_events_come_first():
    # 18/10: the editor's first run with event pages passed France's riots by – it weighed only the most widely carried
    # story (a decision) and the riots came as two stories
    head = lambda i: i['title']   # noqa: E731
    pool = [
        {'id': 'ru', 'outlets': 41, 'title': 'Trump suspenderer nye sanktioner og told mod Rusland'},
        {'id': 'f1', 'outlets': 23, 'title': 'Demonstranter stormer rådhuse og turistkontor står i flammer i Frankrig',
         'summary': 'Omkring 1.200 anholdt, 150 politifolk såret den 17. oktober'},
        {'id': 'f2', 'outlets': 22, 'title': 'Store uroligheder i Frankrig'},
        {'id': 'ws', 'outlets': 23, 'title': 'Europæiske diplomater angrebet af israelske bosættere',
         'also': [{'title': 'Israeli strikes on Gaza kill one'}]},
        {'id': 'an', 'outlets': 14, 'kind': 'kommentar', 'title': 'Analyse: krigen i Ukraine og Trumps nye linje'},
    ]
    groups = events.great_events(pool, head)
    assert [i['id'] for i in groups[0]['items']] == ['f1', 'f2'] and groups[0]['kind'] == 'uro'
    assert all(g['word'] is None for g in groups[1:])   # a decision and an attack ('strike' is also a raid): not marked
    assert 'an' not in {i['id'] for g in groups for i in g['items']}   # an analysis is no event
    text = '\n'.join(events.great_lines(groups, head, lambda i: i.get('summary', '')))
    assert "[A] EVENT – uro ('demonstr') · 2 stories · up to 23 outlets" in text
    assert 'Numbers in its stories: 1.200, 150' in text and '17' not in text.split('Numbers in its stories:')[1].split('\n')[0]
    # two stories sharing one word only are one event when they are the same kind, never otherwise
    a = {'id': 'a', 'outlets': 12, 'title': 'Krigen i Sudan: hæren rykker frem mod Khartoum'}
    b = {'id': 'b', 'outlets': 10, 'title': 'Valget i Sudan udskudt igen'}
    assert len(events.great_events([a, b], head)) == 2


def test_an_english_date_is_no_count():
    assert events.ungrounded('Den 17. oktober og October 17 og 17 October gik 550.000 på gaden.',
                             [{'title': '550,000 marched'}]) == []


def test_a_page_under_way_without_its_numbers_is_named_and_its_material_listed():
    # 18/10: the first page the editor built had no fact box – the input gave one teaser, while the other outlets'
    # headlines carried '1,200 arrested, 150 cops injured' and 'More than 1,800 arrested, Interior Minister says'
    story = {'id': 'f1', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
             'also': [{'source': 'Times of Israel', 'title': 'Mass protests in France; 1,200 arrested, 150 cops injured'},
                      {'source': 'DW', 'title': 'France protests: More than 1,800 arrested, Interior Minister says'}]}
    page = {'id': 'frankrig', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang',
            'since': '2026-10-18', 'dek': '…', 'facts': [], 'stories': ['f1'], 'at': '2026-10-18T14:49:58+00:00'}
    find = {'f1': story}.get
    assert events.thin([page], find) == [(page, ['tal (1,200, 150, 1,800 i dens historier)'])]
    text = '\n'.join(events.lines({'items': [page]}, NOW, find, lambda i: i['title'], lambda i: ''))
    assert 'DW: France protests: More than 1,800 arrested, Interior Minister says' in text
    assert 'Numbers in its stories: 1,200, 150, 1,800' in text and 'Bring each page under way up to date' in text
    # a page with its numbers is not thin
    assert events.thin([{**page, 'facts': [{}, {}]}], find) == []


def test_one_outlets_word_marks_no_event():
    head = lambda i: i['title']   # noqa: E731
    one = {'id': 'z', 'outlets': 14, 'title': 'Zelenskyj kritiserer Trumps pause i sanktionerne',
           'also': [{'title': "Zelenskyy says the waiver will intensify war in Ukraine"}]}
    assert events.great_events([one], head)[0]['word'] is None
    two = {**one, 'also': one['also'] + [{'title': 'Russia steps up its war on the energy grid'}]}
    assert events.great_events([two], head)[0]['kind'] == 'krig'


def test_a_page_under_way_holds_its_counts_is_told_whole_and_names_who_says_it():
    # 18/10: the editor's first page had no box, two paragraphs and 'Ifølge danske medier … Medierne omtaler …'
    rich = {'id': 'fx', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
            'also': [{'source': f'S{k}', 'title': t} for k, t in enumerate(
                ['1,200 arrested, 150 cops injured', 'More than 1,800 arrested, Interior Minister says', 'Riots in Paris',
                 'Looting in Lyon', 'Yellow Vests return', 'UN flags concern over violence'])]}
    page = {'id': 'frankrig-uro', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang',
            'since': '2026-10-18', 'dek': 'Demonstrationer mod leveomkostningerne i flere franske byer.', 'stories': ['fx'],
            'facts': [], 'article': [{'text': 'Ifølge danske medier har demonstranter stormet rådhuse.', 'ids': ['fx']}]}
    problems = []
    events.events_file([page], None, {'fx': rich}, NOW, TODAY, problems, voice)
    text = ' | '.join(problems)
    assert 'its stories carry 1,200, 150, 1,800 – give each count its box' in text
    assert "the article has 1 paragraph(s) while its stories hold 6 other outlets' headlines" in text
    assert "'Ifølge danske medier' – name who gives each fact" in text


def test_the_article_tells_the_event_not_what_the_outlets_write():
    # 18/10, the editor's third try: 'BT skriver, at … DR omtaler situationen som … Times of Israel skrev, at … The Hindu
    # skriver, at …', and the earlier count of the arrests in a note ('tidligere meldt 1.200')
    story = {'id': 'fx', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
             'also': [{'title': '1,200 arrested, 150 cops injured'}, {'title': 'More than 1,800 arrested, minister says'}]}
    page = {'id': 'frankrig-uro', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang',
            'since': '2026-10-18', 'dek': 'Demonstrationer mod leveomkostningerne i flere franske byer.', 'stories': ['fx'],
            'facts': [{'label': 'Anholdte', 'value': '1.800', 'note': 'tidligere meldt 1.200', 'ids': ['fx']},
                      {'label': 'Sårede politifolk', 'value': '150', 'ids': ['fx']}],
            'article': [{'text': 'BT skriver, at demonstranter har stormet rådhuse.', 'ids': ['fx']},
                        {'text': 'DR omtaler situationen som store uroligheder.', 'ids': ['fx']},
                        {'text': 'The Hindu skriver, at mere end 1.800 er anholdt.', 'ids': ['fx']}]}
    problems = []
    events.events_file([page], None, {'fx': story}, NOW, TODAY, problems, voice)
    text = ' | '.join(problems)
    assert "the note 'tidligere meldt 1.200' holds a number" in text
    assert "the article says 3 times what an outlet writes" in text
    good = {**page, 'facts': [{**page['facts'][0], 'note': 'ifølge indenrigsministeren',
                               'was': {'value': '1.200', 'when': 'fredag', 'ids': ['fx']}}, page['facts'][1]],
            'article': [{'text': 'Mere end 1.800 er anholdt, oplyser indenrigsministeren.', 'ids': ['fx']},
                        {'text': 'Demonstranter stormede rådhuse i flere byer.', 'ids': ['fx']}]}
    problems = []
    events.events_file([good], None, {'fx': story}, NOW, TODAY, problems, voice)
    assert problems == [], problems


def test_a_box_credits_the_outlets_that_carry_its_number():
    # 18/10: the first page credited BT (the story's own outlet) for the arrests The Hindu and Times of Israel gave
    story = {'id': 'fx', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
             'also': [{'source': 'Times of Israel', 'title': 'Mass protests in France; 1,200 arrested, 150 cops injured'},
                      {'source': 'DW', 'title': 'France protests: More than 1,800 arrested, Interior Minister says'}]}
    assert events.sources([story], 'over 1.800') == ['DW']
    assert events.sources([story], 'Mere end 1.800 er anholdt; tidligere 1.200.') == ['Times of Israel', 'DW']
    assert events.sources([story], 'Demonstranter stormede rådhuse.') == ['BT']
    # and a page the update leaves as it is follows its stories
    page = {'id': 'frankrig', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang', 'since': '2026-10-18',
            'dek': '…', 'stories': ['fx'], 'at': '2026-10-18T08:00:00+00:00',
            'facts': [{'label': 'Anholdte', 'value': '1.800', 'note': 'mere end, ifølge indenrigsministeren', 'ids': ['fx'], 'src': ['BT']}]}
    out = events.events_file([], {'items': [page]}, {'fx': story}, NOW, TODAY, [], voice)
    assert out['items'][0]['facts'][0]['src'] == ['DW']
    assert any('»over …«' in w for _, lacks in events.thin(out['items'], {'fx': story}.get) for w in lacks)


def test_times_of_israel_is_a_source_only_when_no_other_carries_the_fact():
    # the owner, 18/10: 'Brug kun times of israel som kilde hvis der ikke er andre'
    assert 'Times of Israel' in events.LAST
    story = {'id': 'fx', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
             'also': [{'source': 'Times of Israel', 'title': '1,800 arrested and 150 cops injured in France'},
                      {'source': 'DW', 'title': 'France protests: More than 1,800 arrested, Interior Minister says'}]}
    assert events.sources([story], '1.800') == ['DW']
    assert events.sources([story], '150') == ['Times of Israel']        # no other carries it
    assert events.last_named('ifølge Times of Israel', [story]) is None
    assert events.last_named('1.800 er anholdt, skriver Times of Israel', [story]) == ('Times of Israel', ['DW'])
    lines = events.material(story, lambda i: i['title'], lambda i: '')
    assert lines[-1].strip().startswith('Times of Israel:')            # listed after the others
    page = {'id': 'frankrig-uro', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang',
            'since': '2026-10-18', 'dek': 'Demonstrationer mod leveomkostningerne.', 'stories': ['fx'],
            'facts': [{'label': 'Anholdte', 'value': '1.800', 'note': 'ifølge Times of Israel', 'ids': ['fx']},
                      {'label': 'Sårede politifolk', 'value': '150', 'note': 'ifølge Times of Israel', 'ids': ['fx']}]}
    problems = []
    events.events_file([page], None, {'fx': story}, NOW, TODAY, problems, voice)
    assert any('fact 1: Times of Israel is a source only when no other outlet carries the number – DW carry it' in p
               for p in problems), problems
    assert not any('fact 2:' in p for p in problems), problems


def test_the_hindu_is_never_a_source():
    # the owner, 18/10: 'The hindu skal også ud' ("cite": false in config/feeds.json)
    assert 'The Hindu' in events.NO_CITE
    story = {'id': 'fx', 'outlets': 23, 'source': 'BT', 'title': 'Demonstranter stormer rådhuse i Frankrig',
             'also': [{'source': 'The Hindu', 'title': 'France protests: More than 1,800 arrested, Interior Minister says'},
                      {'source': 'DW', 'title': 'Some 1,200 arrested and 150 police injured, Lecornu says'}],
             'said': [{'s': 'The Hindu', 't': 'More than 6,800 people have been detained since the start of the protests.'}]}
    assert not events.grounded('1.800', [story]) and not events.grounded('6.800', [story])
    assert events.grounded('1.200', [story]) and events.sources([story], '1.200') == ['DW']
    text = '\n'.join(events.material(story, lambda i: i['title'], lambda i: ''))
    assert 'The Hindu' not in text and 'DW: Some 1,200 arrested' in text
    page = {'id': 'frankrig', 'title': 'Uroligheder i Frankrig', 'kicker': 'Frankrig', 'status': 'i gang', 'stories': ['fx'],
            'facts': [{'label': 'Anholdte', 'value': 'over 1.800', 'ids': ['fx']}, {'label': 'Sårede politifolk', 'value': '150', 'ids': ['fx']}]}
    assert any('en kilde, vi bruger, for over 1.800' in w for _, lacks in events.thin([page], {'fx': story}.get) for w in lacks)
