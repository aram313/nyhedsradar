"""Hizb ut-Tahrir's new political answers: the list page, an answer's text, the rhythm of fetching, no text of an
answer the app already holds, and what data.json lists."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import analyses  # noqa: E402

LIST_PAGE = '''<div class="itemList">
<article class="itemView groupPrimary"><header><h4>
  <a href="/en/index.php/qestions/political-questions/30420.html">Answer to Question: The Scope of Military Developments in Yemen</a>
</h4><ul><li class="itemDate"><time> 15 Rabi' II 1448 </time>&nbsp;|&nbsp;<time datetime="2026-09-27T22:30:00+03:00">Sunday</time></li></ul></header></article>
<article class="itemView groupPrimary"><header><h4>
  <a href="/en/index.php/qestions/political-questions/30170.html">Question and Answer The Saudi-Turkish-Pakistani Tripartite Alliance</a>
</h4><ul><li class="itemDate"><time datetime="2026-08-18T21:00:00+03:00">Tuesday</time></li></ul></header></article>
</div>'''

ANSWER_PAGE = '''<div class="itemBody"><div class="itemFullText">
<p>Answer to Question</p><p>The Scope of Military Developments in Yemen</p>
<p>Question:</p><p>&quot;On Friday, the chiefs of staff met in Riyadh&quot;</p>
<p>Answer:</p><p>To clarify matters, let&#039;s examine the following:</p>
</div><div class="itemSocialSharing">share this</div>'''

NOW = datetime(2026, 10, 17, 18, 0, tzinfo=timezone.utc)


def fake_site(calls):
    def fetch(url):
        calls.append(url)
        return LIST_PAGE if url == analyses.LIST else ANSWER_PAGE
    return fetch


def test_list_page_gives_the_answers_newest_first():
    items = analyses.parse_list(LIST_PAGE)
    assert [x['id'] for x in items] == ['30420', '30170']
    assert items[0]['title'] == 'Answer to Question: The Scope of Military Developments in Yemen'
    assert items[0]['url'] == analyses.BASE + '/en/index.php/qestions/political-questions/30420.html'
    assert items[0]['date'] == '2026-09-27T22:30:00+03:00'


def test_answer_text_is_the_article_body_only():
    text = analyses.parse_answer(ANSWER_PAGE)
    assert text.startswith('Answer to Question')
    assert '"On Friday, the chiefs of staff met in Riyadh"' in text and "let's examine" in text
    assert 'share this' not in text
    assert analyses.parse_answer('<p>no article</p>') == ''


def test_update_reads_the_list_rarely_and_fetches_new_texts():
    calls = []
    memory = analyses.update({}, NOW, fake_site(calls))
    assert calls[0] == analyses.LIST and len(calls) == 3          # the list, then both new answers
    assert all(x['text'] for x in memory['items']) and memory['checked'] == NOW.isoformat(timespec='seconds')
    calls.clear()
    memory = analyses.update(memory, NOW + timedelta(hours=1), fake_site(calls))
    assert calls == []                                             # nothing new to fetch, and the list was read lately
    analyses.update(memory, NOW + analyses.EVERY, fake_site(calls))
    assert calls == [analyses.LIST]                                # time to look at the list again


def test_no_text_of_an_answer_the_app_already_holds():
    calls = []
    memory = analyses.update({}, NOW, fake_site(calls), known={'30170'})
    assert len(calls) == 2 and calls[1].endswith('/30420.html')    # only the new answer's text is fetched
    held = {x['id']: x for x in memory['items']}
    assert held['30420']['text'] and not held['30420']['known']
    assert held['30170']['text'] == '' and held['30170']['known']
    # once the app's next build holds the new answer too, its text leaves the state
    memory = analyses.update(memory, NOW + timedelta(hours=1), fake_site([]), known={'30170', '30420'})
    assert all(x['text'] == '' for x in memory['items'])


def test_a_failing_site_keeps_what_was_there():
    memory = analyses.update({}, NOW, fake_site([]))

    def down(url):
        raise OSError('timeout')
    again = analyses.update(memory, NOW + analyses.EVERY, down)
    assert again['items'] == memory['items'] and again['checked'] == memory['checked']


def test_data_json_lists_new_answers_without_their_text():
    memory = analyses.update({}, NOW, fake_site([]), known={'30170'})
    assert analyses.for_app(memory) == [{'id': '30420', 'title': memory['items'][0]['title'],
                                         'date': '2026-09-27T22:30:00+03:00', 'url': memory['items'][0]['url']}]
    assert analyses.for_app({}) == []
