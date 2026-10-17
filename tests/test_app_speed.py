"""The owner's rule on speed and smoothness (docs/hjerne/notes-owner-performance.md), checked on the app's files: what
was measured as a bottleneck on 17/10 must not come back."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')
SW = (PUBLIC / 'sw.js').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)            # the app without its comments
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)      # the style without its comments


def test_no_blur_behind_a_bar():
    # a backdrop blur under a fixed bar is drawn again at every frame of a scroll on iPhone
    assert not re.search(r'backdrop-filter:(?!\s*none)', RULES)


def test_no_blend_layers_and_no_animated_filter_or_height():
    assert 'mix-blend-mode' not in RULES
    for prop in re.findall(r'transition:\s*([^;}]+)', RULES):
        assert not re.search(r'\b(filter|height|grid-template-rows|top|left|box-shadow|background-color)\b', prop), prop


def test_every_font_size_follows_the_text_size():
    sizes = re.findall(r'font(?:-size)?:\s*([^;}]*\d+(?:\.\d+)?px[^;}]*)', RULES)
    assert sizes and all('var(--ts, 1)' in s for s in sizes), [s for s in sizes if 'var(--ts, 1)' not in s]


def test_reduce_motion_is_respected():
    assert '@media (prefers-reduced-motion: reduce)' in CSS
    # the motions the app starts itself ask first
    for m in re.finditer(r'\.animate\(', CODE):
        line = CODE[CODE.rfind('\n', 0, m.start()):m.start()]
        assert 'reduceMotion' in line, line


def test_dates_are_formatted_by_formatters_made_once():
    # toLocale…String with options builds a formatter at every call (a tenth of a second on a list of eighty rows)
    assert not re.search(r'\.toLocale(?:Time|Date)String\(', CODE.split('function statsHtml')[0])


def test_a_reload_compares_text_and_patches_the_page():
    load = CODE[CODE.index('async function load('):CODE.index('function renderSoon')]
    assert 'JSON.stringify' not in load and 'store.set(' not in load   # no stringify of large objects, no synchronous copy
    assert 'keepRaw(' in load
    assert 'function morph(' in CODE and 'morph(pg, tpl.content' in CODE
    assert 'restorePlace(pg, place)' in CODE


def test_rows_enter_only_when_new_and_long_lists_are_skipped_out_of_sight():
    assert "'enter'" not in CODE and '--i:' not in CODE
    assert re.search(r'\.story\.pic:not\(\.open\)[^{]*\{\s*content-visibility:\s*auto', RULES)


def test_the_service_worker_shows_the_phones_copy_of_the_page_at_once():
    assert "e.request.mode === 'navigate'" in SW
    nav = SW[SW.index("e.request.mode === 'navigate'"):]
    assert nav.index('caches.match(key)') < nav.index('e.respondWith(fresh(')


# the reviewers' findings of 2026-10-17 (round 2)

def test_a_lead_change_keeps_the_readers_story():
    # a card's id is its lead article's: when a better outlet takes the lead, the row is renamed in place and stays
    # opened and seen – it is neither rebuilt nor counted or glowing as new
    assert 'function carryOver(' in CODE and re.search(r'carryOver\(cache\.list, items\)', CODE)
    body = CODE[CODE.index('function carryOver('):CODE.index('const firstFound')]
    assert 'expanded, covOpen, shownIds' in body and "el.id = 's-' + i.id" in body
    assert 'firstFound(i)' in CODE[CODE.index('const isNew'):CODE.index('const isNew') + 200]


def test_a_failed_picture_is_not_asked_for_again_at_a_reload():
    assert 'onerror="this.remove()"' not in APP and "this.src = '" not in APP
    assert 'function picFailed(' in CODE and 'badPics.has(' in CODE[CODE.index('function thumb('):CODE.index('function meta(')]


def test_every_redraw_waits_for_the_finger():
    assert re.search(r'function staleOn\(tabs\) \{ if \(tabs\.includes\(tab\)\) renderSoon\(', CODE)
    body = CODE[CODE.index('function redrawPages('):CODE.index('const picWatch')]
    assert 'handBusy()' in body


def test_the_front_page_shows_a_story_once():
    body = CODE[CODE.index('function composedHome('):CODE.index('function home(')]
    assert re.search(r'nowStrip\(.*, skip\)', body)
    assert re.search(r'nowStrip\(3, new Set\(', CODE[CODE.index('function fixedHome('):])


def test_a_closed_headline_keeps_its_words_at_large_text():
    assert re.search(r'\.story\.hero:not\(\.open\) \.hero-tx \.h[^{]*\{[^}]*-webkit-line-clamp: 3', RULES)
    assert re.search(r'\.ts-l \.story\.pic:not\(\.open\):not\(\.hero\) \.h \{ -webkit-line-clamp: 3', RULES)
    assert "classList.toggle('ts-l'" in CODE
