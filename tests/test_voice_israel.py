"""The owner's house style for the name Israel (2026-10-17): lower case inside curly quotes, every form, in all of
the editor's text (scripts/voice.py quote_israel, applied by editor.py publish to every file it writes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import editor  # noqa: E402
import voice  # noqa: E402


def test_every_form_of_the_name_is_quoted_in_lower_case():
    q = voice.quote_israel
    assert q('Israel angriber Gaza by') == '“israel” angriber Gaza by'
    assert q('Israelske styrker anholder fem i Jenin') == '“israelske” styrker anholder fem i Jenin'
    assert q('Israels premierminister') == '“israels” premierminister'
    assert q('Israel-Hamas-krigen') == '“israel”-Hamas-krigen'
    assert q('"Israel" og »Israel«') == '“israel” og “israel”'           # other quotes become the house form
    assert q('»Israel angriber«, siger han') == '»“israel” angriber«, siger han'   # a quotation keeps its marks
    assert q(q('Israel')) == '“israel”'                                       # idempotent
    assert q('https://example.com/israel-news') == 'https://example.com/israel-news'
    # an outlet's name is no name of the state (18/10), and one set so before is set back
    assert q('ifølge Times of Israel og Israel Hayom; Israel svarer') == 'ifølge Times of Israel og Israel Hayom; “israel” svarer'
    assert q('ifølge Times of “israels” gengivelse') == 'ifølge Times of Israels gengivelse'


def test_publish_quotes_text_but_never_ids_or_links():
    x = editor.quoted({'lede': 'Israel og Iran', 'picks': [{'id': 'israel1', 'why': 'Israel handler'}],
                       'link': 'https://t.me/israel', 'topics': [{'name': 'Israel og Libanon', 'lines': [{'text': 'Israelsk angreb'}]}]})
    assert x['lede'] == '“israel” og Iran' and x['picks'][0] == {'id': 'israel1', 'why': '“israel” handler'}
    assert x['link'] == 'https://t.me/israel' and x['topics'][0]['name'] == '“israel” og Libanon'
    assert x['topics'][0]['lines'][0]['text'] == '“israelsk” angreb'


def test_the_app_writes_the_outlets_danish_headlines_the_same_way():
    app = (Path(__file__).resolve().parents[1] / 'public' / 'app.js').read_text(encoding='utf-8')
    assert 'const quoteIsrael = t =>' in app
    assert "if (d.how === 'ed' || (d.to || i.lang) === 'da') {" in app and 'title: quoteIsrael(d.title)' in app
    assert 'esc(quoteIsrael(e.t))' in app                                         # the map's events
    energi = (Path(__file__).resolve().parents[1] / 'public' / 'energi' / 'index.html').read_text(encoding='utf-8')
    assert 'n.ed ? [qi(n.ed), n.kd]' in energi
