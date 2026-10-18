"""The great stories' articles read for their counts (src/radar/reader.py) – the owner, 18/10, on DR's overview of
France's riots: 'Se kilderne her, hvorfor kan vi ikke bruge de samme?'."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from radar import reader  # noqa: E402
import events  # noqa: E402

NOW = datetime(2026, 10, 18, 16, 0, tzinfo=timezone.utc)
PAGE = ('<html><script type="application/ld+json">{"@type": "NewsArticle", "articleBody": "PARIS, Oct 17 (Reuters) - '
        'Around 550,000 people marched across France on Friday, the interior ministry said, while the CGT union put the '
        'number at 800,000. Police counted 110 marches in the country. The protests began in 2026 over prices. '
        'President Macron said there was no place for violence. More than 1,200 people were arrested and 150 police '
        'officers were injured, the ministry said at 10:30."}</script><p>Sign up for our newsletter today.</p></html>')


def test_the_sentences_with_counts_are_kept_and_nothing_else():
    got = reader.sentences(reader.body(PAGE))
    assert got[0].startswith('PARIS, Oct 17 (Reuters) - Around 550,000 people marched') and 'CGT' in got[0]
    assert 'Police counted 110 marches in the country.' in got
    assert any('1,200 people were arrested and 150 police' in s for s in got)
    assert not any('Macron' in s or 'began in 2026' in s for s in got)   # no count: a year or no number


def test_the_great_stories_get_their_articles_counts_and_the_editor_can_ground_them():
    card = {'id': 'f1', 'live': 'rank', 'outlets': 23, 'source': 'BT', 'link': 'https://bt.test/a', 'title': 'Uro i Frankrig'}
    members = {'f1': [{'id': 'f2', 'source': 'Reuters', 'link': 'https://news.google.com/rss/articles/abc'}]}
    pages = {'https://bt.test/a': '<p>' + 'Demonstranter stormede rådhuse i flere byer, og politiet satte tåregas ind mod mængden. ' + '</p>',
             'https://reuters.test/x': PAGE}
    small = {'id': 's', 'live': 'rank', 'outlets': 2, 'link': 'https://x.test/s'}
    memory = reader.attach([card, small], members, {}, NOW, resolve=lambda link: 'https://reuters.test/x', fetch=pages.get)
    assert card['said'][0]['s'] == 'Reuters' and '800,000' in card['said'][0]['t'] and 'said' not in small
    assert memory['own'] == {'https://news.google.com/rss/articles/abc': 'https://reuters.test/x'}
    # the next run reads nothing again
    reader.attach([card], members, memory, NOW, resolve=lambda link: 1 / 0, fetch=lambda url: 1 / 0)
    assert card['said'][0]['s'] == 'Reuters'
    # the editor's tool: the count grounded in the article's sentence, credited to its outlet, listed as material
    assert events.grounded('800.000', [card]) and events.sources([card], '800.000') == ['Reuters']
    lines = events.material(card, lambda i: i['title'], lambda i: '')
    assert any(line.strip().startswith("In Reuters's article: PARIS, Oct 17 (Reuters) - Around 550,000") for line in lines)


def test_a_page_whose_articles_carry_new_counts_is_named():
    story = {'id': 'f1', 'source': 'BT', 'title': 'Uro i Frankrig',
             'said': [{'s': 'Reuters', 't': 'Around 550,000 marched, the ministry said; the CGT put it at 800,000.'},
                      {'s': 'Reuters', 't': 'Police counted 110 marches and 1,800 arrests.'}]}
    page = {'id': 'frankrig', 'status': 'i gang', 'stories': ['f1'],
            'facts': [{'label': 'Anholdte', 'value': '1.800'}], 'article': [{'text': 'Mere end 1.800 er anholdt.'}]}
    assert events.unused([page], {'f1': story}.get) == [(page, ['550,000', '800,000', '110'])]
    page['facts'].append({'label': 'Demonstranter', 'value': '550.000'})
    assert events.unused([page], {'f1': story}.get) == []        # two left: not enough to call for an update
