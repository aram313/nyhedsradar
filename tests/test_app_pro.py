"""Khabar made professional (docs/hjerne/pro-plan.md, 2026-10-17), the app's part, checked on its files: two voices,
red only for live and big, rows that keep their words, every state designed, one time format and one word set, what
is shared is what is seen, the views' refinements and the five new functions – within the owner's rules (no ids, no
consent prompts, nothing that follows a person, the app never names Claude)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')
INDEX = (PUBLIC / 'index.html').read_text(encoding='utf-8')
HEAD = (ROOT / 'src' / 'radar' / 'headlines.py').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)


def fn(name):
    """The source of one function of app.js (to its first line that closes at the start)."""
    m = re.search(r'\n(?:async )?function ' + re.escape(name) + r'\(.*?\n\}', CODE, re.S)
    assert m, name
    return m.group(0)


def rules_for(selector):
    return [m.group(1) for m in re.finditer(r'(?:^|\})\s*([^{}]*?)\s*\{', RULES) if selector in m.group(1)]


# ------------------------------------------------------------------ the visual system

def test_the_serif_is_the_movements_voice_only():
    allowed = ('.ht', '.an-', '.rd-', '.wk-', '.th b', '.intro-ink', '.logo', ':root')
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', RULES):
        sel, decl = ' '.join(m.group(1).split()), m.group(2)
        if 'Georgia' in decl or 'var(--serif)' in decl:
            assert any(a in sel for a in allowed), sel
    for sel in ('.lede-t', '.thr h3', '.fol-row b', '.quote q', '.intro-lead'):
        body = ''.join(re.findall(re.escape(sel) + r'\s*\{([^}]*)\}', RULES))
        assert body and 'serif' not in body and 'Georgia' not in body, sel


def test_red_means_live_or_big():
    head = CODE.split('const blockHead')[1].split('\n')[0]
    assert "${live ? '<i class=\"live\"" in head   # a block title carries the red dot only when asked for: Live
    assert "blockHead('Live', moreLink('Se alt', 'latest'), true)" in CODE   # the front page's one red dot
    assert re.search(r'\.lede-d span \{[^}]*color: var\(--text-3\)', RULES)
    assert '.live-tab.has-new { color' not in RULES
    assert re.search(r'\.day span \{[^}]*background: var\(--fill-2\); color: var\(--text\)', RULES)
    # 'Topnyhed' is rationed: the five strongest big stories of the Danish day, twelve hours each, never in chosen blocks
    assert 'const TOP_MAX = 5, TOP_HOURS = 12' in CODE and "topNow().has(i.id)" in fn('meta')
    assert 'opts.top' in fn('meta')


def test_rows_keep_their_words_and_the_meta_line_breaks_between_items():
    assert re.search(r'\.m \{[^}]*flex-wrap: wrap;[^}]*clip-path: inset\(0 0 0 12px\)', RULES)
    assert re.search(r'\.m > span \{ flex: none; white-space: nowrap; \}', RULES)
    assert re.search(r'\.m > span::before \{ content: "·"', RULES)
    # a list of one section does not say the section on every row
    assert 'tag = new Set(list.map(secOf)).size > 1' in fn('composedHome')


def test_segments_chips_and_minis_reach_44_points():
    assert re.search(r'\.seg button \{[^}]*min-height: 44px', RULES)
    assert re.search(r'\.chip::after \{ content: ""; position: absolute; inset: -4px 0; \}', RULES)
    assert re.search(r'\.mini \{[^}]*min-height: 40px', RULES) and re.search(r'\.mini::after \{[^}]*inset: -2px 0', RULES)
    assert re.search(r'\.jump button \{[^}]*min-height: 44px', RULES)


def test_one_icon_set():
    for icon in ('i-back', 'i-save', 'i-saved', 'i-refresh', 'i-offline', 'i-plus'):
        assert f'<symbol id="{icon}"' in INDEX, icon
    assert 'content: "›"' not in RULES and 'content: "↗"' not in RULES   # the glyphs became the app's icons
    assert 'html.aside .brand::before' not in RULES and 'html.aside .brand .back { display: block; }' in RULES


# ------------------------------------------------------------------ states, time and words

def test_every_state_has_a_message_and_a_way_on():
    assert 'function stateBlock(' in CODE and 'function noNews(' in CODE
    assert "Date.now() - bootAt < 4000" in fn('noNews') and 'data-reload' in fn('noNews')
    assert "addEventListener('online', () => load(true))" in CODE
    assert "'ingen forbindelse'" in fn('renderHeader') and "'offline · '" in fn('renderHeader')
    assert "retry('svarets tekst', 'mfull')" in fn('svarPage') and "retry('siden', 'bfull')" in fn('begrebPage')
    assert 'Siden findes ikke.' in fn('begrebPage') and 'Svaret findes ikke.' in fn('svarPage')
    assert 'Historien er ikke længere i Live.' in fn('latestPage')
    assert "say(`${fresh}" in CODE and 'id="srStatus"' in INDEX


def test_one_time_format_and_one_word_set():
    assert 'function ago(' not in CODE and 'function stamp(' in CODE
    st = fn('stamp')
    assert "Math.floor(m) + ' min'" in st and "'i går kl. '" in st and 'FMT.wd.format(d)' in st
    assert "'linje' : 'linjer'" not in CODE and "'linjer'" not in CODE and 'udviklinger · senest' not in CODE
    assert "`fulgt i ${t.days} dage`" in CODE and "'opdatering' : 'opdateringer'" in CODE
    assert 'newestFirst(tp.lines).slice(0, n)' in fn('storyline') and 'data-follow' in fn('storyline')


def test_deep_links_skip_the_intro_and_name_the_page_in_view():
    assert "['item', 'svar', 'begreb', 'forlob', 'digest', 'tab', 'gemt'].some(k => q.has(k))" in INDEX
    assert "if (deep || (seen && away < 6 * 3600e3)) d.classList.add('intro-skip')" in INDEX
    assert "`forlob=${encodeURIComponent(arg)}`" in CODE and "openSide('threads', params.get('forlob'))" in CODE


# ------------------------------------------------------------------ what is shared is what is seen

def test_the_share_sends_the_editors_sentence_and_the_way_back():
    share = fn('shareText')
    assert 'sumOf(d)' in share and 'firstSentence(ed && ed.text)' in share and 'cleanTeaser(d.summary' in share
    assert 'via ${itemUrl(d.id)}' in share and "const itemUrl = id => `khabar.nu/?item=" in CODE
    assert 'asShown(el)' in CODE.split("$('list').addEventListener('click'")[1].split('\n')[1]


def test_the_teaser_cleaning_is_the_radars():
    # the app's copy keeps the radar's calls to action and its picture credits (src/radar/headlines.py)
    for word in ('Følg|Se|Læs|Hør|Lyt', 'Read more|Continue reading', 'screengrab', 'appeared first on'):
        assert word in HEAD and word in APP, word
    assert 'd.summary = cleanTeaser(d.summary, d.title)' in fn('display')


def test_an_answer_shows_once_on_the_front_page():
    assert 'frontAns.add(a.nr)' in fn('mainAnswer') and 'if (svarSet) frontAns.add(svarSet)' in fn('composedHome')
    assert "detailOpts = (i, opts = {}) => (opts.home ? { skip: [...frontAns].join(',') }" in CODE
    # the answer line sits right under the main story, before its development and the stories with it
    body = fn('composedHome')
    assert body.index('mainAnswer(i,') < body.index('storyline(tp)') < body.index("(b.with || [])")


# ------------------------------------------------------------------ the five new functions

def test_gem_keeps_snapshots_on_the_phone_in_idle_time():
    assert "SAVE_MAX = 200" in CODE and "idle(() => store.set('saved', saved))" in fn('toggleSave')
    snap = fn('snapshot')
    for f in ('title', 'source', 'link', 'summary', 'also'):
        assert f in snap, f
    assert '<section class="page side" data-tab="gemt"' in INDEX
    assert "c.saveData || /2g/.test(c.effectiveType || '')" in fn('prefetchLibrary')


def test_one_search_with_scopes():
    assert "const SCOPES = [['alle', 'Alle'], ['nyheder', 'Nyheder'], ['svar', 'Svar'], ['begreber', 'Begreber']]" in CODE
    page = fn('searchPage')
    for group in ('Begreber', 'Udviklinger', 'Hizb ut-Tahrirs svar', 'På Khabar', 'Andre nyheder'):
        assert group in page, group
    assert page.index('Begreber</h2>') < page.index('Udviklinger</h2>') < page.index('Hizb ut-Tahrirs svar') < page.index('På Khabar')
    assert "idle(() => store.set('recentQ', recentQ))" in fn('rememberQuery')


def test_the_catch_up_line_stores_nothing_new():
    assert 'const CATCH_AFTER = 3 * 3600e3' in CODE
    line = fn('catchUpLine')
    assert 'store.' not in line and 'Siden ' in line
    assert "classList.add('fade')" in fn('fadeCatchUp') and re.search(r'\.catch \{[^}]*transition: opacity', RULES)


def test_the_days_overview_uses_checked_headlines_only():
    brief = fn('briefText')
    assert '*Dagens nyheder – ' in brief and "'via khabar.nu'" in brief and 'slice(0, 5)' in brief
    assert "x.ed" in brief


def test_notifications_by_choice_travel_with_the_phones_own_address():
    assert "const PUSH_KINDS = ['top', 'digest', 'svar']" in CODE
    assert "...(kind === 'sub' ? { want: pushWant } : {})" in fn('tellKhabar')
    for want in ('top', 'digest', 'svar'):
        assert f'data-want="{want}"' in INDEX


def test_no_ids_no_prompts_and_no_claude():
    assert not re.search(r'crypto\.randomUUID|uuid|fingerprint', CODE, re.I)
    assert 'confirm(' not in CODE and 'prompt(' not in CODE.replace('installEvent.prompt()', '')
    assert not re.search(r'claude', APP + INDEX + CSS, re.I)
