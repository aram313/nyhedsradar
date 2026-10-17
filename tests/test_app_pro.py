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
    assert re.search(r'\.lede-d > span \{[^}]*color: var\(--text-3\)', RULES)
    assert '.live-tab.has-new { color' not in RULES
    assert re.search(r'\.day span \{[^}]*background: var\(--fill-2\); color: var\(--text\)', RULES)
    # 'Topnyhed' is rationed: the five strongest big stories of the Danish day, twelve hours each, never in chosen blocks
    assert 'const TOP_MAX = 5, TOP_HOURS = 12' in CODE and "topNow().has(i.id)" in fn('meta')
    assert 'opts.top' in fn('meta')


def test_red_is_used_only_for_live_big_and_new():
    # review of 2026-10-17: the stale box, search marks, the switches, the focus ring and the offline logo were red
    # and since 17/10 the front page's accents (the owner: "Forsiden bliver for monoton, brug gerne lidt rød")
    allowed = ('.logo', '.block-h .live', '.m .big', '.nd', '.tab-dot', '.live-dot', '.story.fresh', 'li.new', '.intro', ':root',
               '.page[data-tab="home"]', '.page[data-tab="kalender"]')
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', RULES):
        sel, decl = ' '.join(m.group(1).split()), m.group(2)
        if 'var(--pulse' in decl:
            assert any(a in sel for a in allowed), sel
    for sel in ('.notice', 'mark', '.switch:checked', ':focus-visible', '.chip.on', '.sources li.bad::before'):
        body = ''.join(re.findall(r'(?:^|\})\s*' + re.escape(sel) + r'\s*\{([^}]*)\}', RULES))
        assert body and 'pulse' not in body, sel
    assert "classList.toggle('stale', !!isStale() || offline)" in fn('renderHeader')   # the logo's dot grey offline
    # a chosen chip is a chosen segment: a step lighter in dark, never a white pill
    assert re.search(r'\.chip\.on \{[^}]*background: var\(--seg-on\)', RULES)


def test_the_lede_is_whole_and_no_paragraph_is_a_button():
    assert not re.search(r'\.lede-t \{[^}]*line-clamp', RULES)
    head = fn('ledeHead')
    assert 'data-go' not in head and 'Del overblik' in head and 'data-brief' in head


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
    assert "x.state === 'error') { x.state = 'idle'; need(k); }" in CODE   # every file that failed, again online
    hdr = fn('renderHeader')
    assert "'offline'" in hdr and '#i-${icon}' in hdr and "'Ingen forbindelse. '" in hdr
    # the same cause, the same words: no network says so on every page, with its icon
    assert "netDown() ? 'offline' : 'error'" in CODE and "Ingen forbindelse. ${cap(what)} kommer" in CODE
    notice = fn('pageHtml')
    assert 'fromWhen(data.updated)' in notice and '#i-offline' in notice and 'clock(data.updated)' not in notice
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
    assert "['item', 'svar', 'begreb', 'forlob', 'digest', 'tab', 'gemt', 'kalender'].some(k => q.has(k))" in INDEX
    assert "if (deep || (seen && away < 6 * 3600e3)) d.classList.add('intro-skip')" in INDEX
    assert "`forlob=${encodeURIComponent(arg)}`" in CODE and "openSide('threads', params.get('forlob'))" in CODE


# ------------------------------------------------------------------ what is shared is what is seen

def test_the_share_sends_the_editors_sentence_and_the_way_back():
    share = fn('shareText')
    assert 'sumOf(d)' in share and 'firstSentence(ed && ed.text)' in share and 'cleanTeaser(d.summary' in share
    assert 'via ${itemUrl(d.id)}' in share and "const itemUrl = id => `khabar.nu/?item=" in CODE
    assert 'asShown(el)' in CODE.split('async function onTap(e) {')[1].split('\n')[1]
    assert "$('list').addEventListener('click', onTap);" in CODE


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
    assert "SAVE_MAX = 200" in CODE and "idle(storeSaved)" in fn('toggleSave')
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
    # a news app: the news before the movement's answers; the answers named in their title first, 'via' last
    assert page.index('Begreber</h2>') < page.index('Udviklinger</h2>') < page.index('På Khabar') < page.index('Hizb ut-Tahrirs svar')
    assert 'm.via ? 2 : 1' in page and "data-unfold=\"${ok}\">Vis flere" in page
    assert "hasWord(f, w)" in page and 'startsAt(f, i)' in fn('mark')   # 'iran' is not marked in 'Mirán'
    # a file that comes later redraws the search page and Gemt too
    loaded = fn('vLoaded')
    assert "'search', 'gemt'" in loaded and "bfull: ['begreb', 'svar', 'search'" in loaded
    assert "idle(() => store.set('recentQ', recentQ))" in fn('rememberQuery')


def test_the_catch_up_line_stores_nothing_new():
    assert 'const CATCH_AFTER = 3 * 3600e3' in CODE
    line = fn('catchUpLine')
    assert 'store.' not in line and 'Siden ' in line
    assert "classList.add('fade')" in fn('fadeCatchUp') and re.search(r'\.catch \{[^}]*transition: opacity', RULES)


def test_the_days_overview_takes_one_story_per_block_with_checked_words_only():
    brief = fn('briefText')
    assert '*Dagens nyheder – ' in brief and "'via khabar.nu'" in brief and 'rows.length < 5' in brief
    assert 'put(ids(b).find(' in brief and 'cleanLink(x.i.link)' in brief   # one from each block, then the rest
    ok = CODE.split('const briefOk = ')[1].split('\n')[0]
    assert "i.how === 'ed'" in ok and "i.lang === 'da' && !i.how && !i.teased && !curious(i.title)" in ok and 'kommentar' in ok


def test_notifications_by_choice_travel_with_the_phones_own_address():
    assert "const PUSH_KINDS = ['top', 'digest', 'svar']" in CODE
    assert "...(kind === 'sub' ? { want: pushWant } : {})" in fn('tellKhabar')
    for want in ('top', 'digest', 'svar'):
        assert f'data-want="{want}"' in INDEX


def test_gem_has_one_home_in_the_bar_and_sends_nothing():
    assert 'id="openSaved"' in INDEX and "$('openSaved').addEventListener('click', () => openSide('gemt'))" in CODE
    save = fn('toggleSave')
    assert 'learnFrom' not in save and 'relay(' not in save and "['Se Gemt', () => openSide('gemt')]" in save
    gemt = fn('gemtPage')
    assert "stateBlock('empty', 'Intet gemt endnu.', [['Til Live', 'data-go=\"latest\"']])" in gemt
    # 18/10, the owner: 'Ser lidt uprofessionelt ud, analyser bør også være over nyheder (kald det ikke historier)'
    assert gemt.index('Analyser · ') < gemt.index('Nyheder · ') < gemt.index('Begreber · ') and 'Historier' not in gemt
    assert 'rows.map(a => anRow(a))' in gemt and "svBtn('b', x.id" in gemt   # one bookmark a row: the answers' own
    story = CODE.split('const savedStory = x => {')[1].split('\n};')[0]
    assert 'class="act' not in story and "svBtn('s', x.id" in story and 'data-live=' in story   # a quiet row, no Læs/Del


def test_saves_outlive_an_update():
    # 18/10, the owner: 'hvordan kan vi sørge for en bruger aldrig mister sine gemte bookmarks?'
    assert "for (const key of ['saved', 'saved-bak'])" in CODE and 'v.filter(okSave)' in CODE
    assert "store.set('saved', saved); store.set('saved-bak', saved)" in CODE
    assert 'idle(storeSaved)' in fn('toggleSave') and 'st.persist()' in CODE and 'Firefox' in CODE


def test_saves_move_by_a_link_that_adds_or_replaces():
    # 18/10, the owner: a new phone keeps the saves; 'tilføj til eksisterende' or 'erstat eksisterende' when it is opened
    link = fn('moveLink')
    assert '?gemt=1#flyt=' in link and 'summary' not in link   # in the fragment: never sent to a server
    take = fn('takeMove')
    assert 'history.replaceState' in take and 'data-a="flyt:add"' in take and 'data-a="flyt:replace"' in take
    assert "if (!saved.length) { useMove('add'); return; }" in take
    use = fn('useMove')
    assert "how === 'replace' ? [...got]" in use and 'storeSaved()' in use and 'SAVE_MAX' in use
    assert "if (kind === 'flyt') { useMove(val); return; }" in CODE and 'data-move' in fn('gemtPage')
    assert 'fetch(' not in link + take + use and 'relay(' not in link + take + use
    assert 'data-go="gemt"' not in CODE   # no scattered ways in: the bar's bookmark is the one


def test_a_notification_choice_that_was_not_sent_is_sent_later():
    assert "store.set('wantDirty', 1); toast(" in CODE and "store.set('wantDirty', 0)" in fn('tellKhabar')
    assert "if (store.get('pushWant', null) === null) store.set('wantDirty', 1)" in CODE   # a phone from before the switches
    assert 'resendWant()' in CODE.split("addEventListener('online', () => { for")[1].split('\n')[0]
    assert "document.addEventListener('visibilitychange', () => { if (!document.hidden) resendWant(); })" in CODE


def test_the_answer_reader_is_one_panel_under_a_quiet_header():
    # 17/10, the owner on the as-Suwayda answer: "uoverskuelig" – too many boxes, labels and heavy buttons
    page = fn('svarPage')
    # the question under the title, the movement's face without a box or a label of its own
    assert '<p class="ht rd-q">${esc(a.q)}</p>' in page and 'Spørgsmålet' not in page
    assert page.index('<h1 class="ht">') < page.index('rd-q') < page.index("knowActs('a', a.nr)")
    # one ochre panel: 'Svaret kort', then the readings under hairlines – no heading of their own, no box per reading
    assert page.count('class="ht-box') == 3   # the panel, and the full text unfolded: held, or the English layer
    assert 'Hvad svaret læser' not in page and 'class="rd-r"' in page and 'htLabel(' not in page
    assert re.search(r'\.rd-ans \.rd-r \{[^}]*border-top: 1px solid var\(--ht-line\)', RULES)
    # the newer answer is a quiet row under the panel, not a box
    assert page.index('rd-ans') < page.index('class="qrow rd-newer"') and 'ht-line' not in page
    # four concepts at most before '+ n', under 'Begreber'
    assert 'SHOW_SVAR_CHIPS = 4' in CODE and "h2 class=\"grp rd-h\">Begreber</h2>${chips(pages, `svar|${a.nr}|pages`, SHOW_SVAR_CHIPS, 0)}" in page
    # no big 'Åbn originalen' (the byline's 'Originalen' is it); a held text folded behind one quiet row
    assert 'Åbn originalen' not in page and 'class="wide' not in page and 'Originalen<svg' in page
    assert 'Læs hele svaret' in page and 'if (open) h +=' in page
    # Del · Kopiér · Gem: one quiet row, left, not stretched (the wiki page's too), with Gem's state
    assert re.search(r'\.know-acts \.act \{[^}]*flex: none;[^}]*min-height: 40px', RULES)
    assert re.search(r'\.know-acts \.act::after \{[^}]*inset: -2px 0', RULES)
    acts = CODE.split('const knowActs = ')[1].split('};')[0]
    assert 'aria-pressed="${on}"' in acts and "on ? 'Gemt' : 'Gem'" in acts


def test_the_library_is_fetched_once_per_build_and_read_only_when_needed():
    pre = fn('prefetchLibrary')
    assert "store.get('libFor', '') === built" in pre and 'arrayBuffer()' in pre and "need('mfull')" not in pre


def test_the_wiki_index_filters_every_page_into_one_group():
    kinds = CODE.split('const AZ_KINDS = ')[1].split(';')[0]
    for k in ('stat', 'magt', 'gruppe', 'organisation', 'sted', 'sag', 'proces', 'begreb', 'aftale'):
        assert f"'{k}'" in kinds, k
    assert 'class="an-chips az-kinds"' in fn('begreberPage')   # one sideways chip row, not a two-row segment


def test_the_main_storys_development_and_answer_belong_to_it():
    # 17/10: Trump's pause of the Russia sanctions wore 'Iran og angrebet' and the Iran answer – the development's name
    # must share a subject with the headline (or the editor filed the story in it) before it, or its name, is used
    body = fn('composedHome')
    assert 'if (tp && !topicOf(shown, tp))' in body and 'tp = t2 && topicOf(shown, t2) ? t2 : null' in body
    assert 'overlap(storyStems(shown), topicStems(tp)) < 3' not in body
    assert "own = pkg && pkg.topic && topicOf(lead, pkg.topic)" in fn('fixedHome')
    assert 'topicFits(i, t)' in fn('threadFor')
    fits = fn('topicFits')
    assert 'GEN.has(w)' in fits and 'BROAD' in fits and 'i.actors' in fits


def test_the_outlet_is_said_once_and_a_speaker_stays():
    disp = fn('display')
    assert 'x === outletKey(d.source) || outletNames().has(x)' in disp
    assert "const NEWS_GROUPS = new Set(['dk', 'west', 'mena', 'il', 'east', 'channel'])" in CODE
    assert 'NEWS_GROUPS.has(v.group' in CODE.split('const outletNames = ')[1].split('.set;')[0]


def test_small_pure_helpers_behave(tmp_path):
    import shutil
    import subprocess
    import pytest
    if not shutil.which('node'):
        pytest.skip('node is not installed')
    take = lambda start, end: APP[APP.index(start):APP.index(end, APP.index(start))]  # noqa: E731
    js = '\n'.join([
        take('const fold = ', '\n') + '\n',
        take('const OUTLET_ALIAS = ', '// commentary') if '// commentary' in APP[APP.index('const OUTLET_ALIAS = '):] else '',
        take('const TRACKING = ', 'const briefOk'),
        take('const LETTER = ', 'function mark('),
        'const esc = s => String(s);',
        fn('mark'),
        'console.log(JSON.stringify(['
        'cleanLink("https://www.berlingske.dk/a/b?referrer=RSS"),'
        'cleanLink("https://x.dk/a?utm_source=x&id=7"),'
        'outletKey("The Guardian"), outletKey("Associated Press"), outletKey("Quds News (arabisk)"),'
        'hasWord("directorate of miran", "iran"), hasWord("irans atomprogram", "iran"),'
        'mark("Directorate of Mirán og Iran", ["iran"])]))'])
    f = tmp_path / 'h.js'
    f.write_text(js, encoding='utf-8')
    out = subprocess.run(['node', str(f)], capture_output=True, text=True, encoding='utf-8')
    assert out.returncode == 0, out.stderr
    import json
    got = json.loads(out.stdout)
    assert got[0] == 'https://www.berlingske.dk/a/b' and got[1] == 'https://x.dk/a?id=7'
    assert got[2:5] == ['guardian', 'ap', 'quds news']
    assert got[5] is False and got[6] is True
    assert got[7] == 'Directorate of Mirán og <mark>Iran</mark>'


def test_no_ids_no_prompts_and_no_claude():
    assert not re.search(r'crypto\.randomUUID|uuid|fingerprint', CODE, re.I)
    assert 'confirm(' not in CODE and 'prompt(' not in CODE.replace('installEvent.prompt()', '')
    assert not re.search(r'claude', APP + INDEX + CSS, re.I)


def test_the_front_page_has_its_red_accents_in_a_readable_red():
    for sel in ('.page[data-tab="home"] .lede-d > span', '.page[data-tab="home"] .block-h h2::before',
                '.page[data-tab="home"] .more, .page[data-tab="home"] .tl-all'):
        assert re.search(re.escape(sel) + r' \{[^}]*var\(--red\)', RULES), sel
    # the readable red only on the front page, the chosen tab's icon (17/10) and the Kalender tab's Economist accents (its
    # fly title, its block titles' rule and the dot of an event in the next 48 hours)
    calendar = ('.page[data-tab="kalender"]', '.cal-fly', '.ck.near i')
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', RULES):
        if 'var(--red)' in m.group(2):
            sel = m.group(1)
            assert '.page[data-tab="home"]' in sel or '.tabs button[aria-selected="true"] > svg' in sel or any(c in sel for c in calendar), sel


def test_the_whole_english_text_is_one_tap_away():
    page = fn('svarPage')
    assert "Læs hele svaret (engelsk)" in page and "oversat fra arabisk" in page
    assert "fetch(VIDEN + 'svar-en/index.json')" in CODE and 'svar-en/${encodeURIComponent(k)}.json' in CODE


def test_an_answer_can_be_saved_from_its_row():
    assert 'class="an-save' in CODE and 'data-ksave="a:${esc(a.nr)}"' in CODE
    assert re.search(r'\.an-save \{[^}]*width: 44px; height: 44px', RULES)


def test_a_live_story_can_be_saved_from_its_row():
    assert "${opts.tick ? rowSave(i) : thumb(i.source, i.thumb)}" in CODE and 'class="st-save' in CODE
    assert 'pointer-events: auto' in RULES.split('.story .row > .st-save {')[1].split('}')[0]
