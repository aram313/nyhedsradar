"""The map is shelved (the owner, 2026-10-17: "Du skal kassere kortvisningen, eller gemme den, i hvert fald for nu, og
ikke lave videre på den"): the Kort tab is gone and nothing reaches its code, which stays in the repo, so no request
goes to Leaflet, MapLibre, the cluster plugin or the tile servers; the radar's Map step is switched off. Also the
Økonomi tab and the options dock above the tabs, checked on the app's files."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')
INDEX = (PUBLIC / 'index.html').read_text(encoding='utf-8')
SW = (PUBLIC / 'sw.js').read_text(encoding='utf-8')
ENERGI = (PUBLIC / 'energi' / 'index.html').read_text(encoding='utf-8')
PAGES = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
RADAR = (ROOT / '.github' / 'workflows' / 'radar.yml').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
# the shelved section of app.js, from its header to the swipe's
KORT = CODE[CODE.index('const KKINDS = '):CODE.index('const SWIPE_TABS = ')]
OUTSIDE = CODE.replace(KORT, '')


def fn(name):
    m = re.search(r'\n(?:async )?function ' + re.escape(name) + r'\(.*?\n\}', CODE, re.S)
    assert m, name
    return m.group(0)


def rule(sel):
    m = re.search(r'(?:^|\})\s*' + re.escape(sel) + r'\s*\{([^}]*)\}', RULES)
    assert m, sel
    return m.group(1)


# ---------------------------------------------------------------- the shelved map
def test_the_kort_tab_and_its_page_are_gone():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert 'data-tab="kort"' not in nav and 'Kort' not in nav
    assert 'data-tab="kort"' not in INDEX and 'page-kort' not in INDEX
    assert "kort: 'Kort'" not in CODE.split('const TITLES = ')[1].split('};')[0]
    assert "'kort'" not in CODE.split('const SWIPE_TABS = ')[1].split('\n')[0]
    assert '<b>Kort</b>' not in INDEX and '<b>Kalender</b>' in INDEX   # the first visit's intro names the tabs


def test_an_old_kort_link_opens_the_front_page():
    start = CODE.split('const START = ')[1].split('};')[0]
    assert "kort: 'home'" in start
    assert "else if (startTab && startTab !== 'home') setTab(startTab, { top: true });" in CODE   # Forside draws itself


def test_the_kort_code_stays_but_nothing_reaches_it():
    assert "// SHELVED since 17/10 at the owner's wish" in APP   # the section's one-line mark
    for name in ('kortPage', 'kortWarm', 'kortShown', 'kortLook', 'kortTap', 'kortOpts', 'kortFill', 'loadLeaflet', 'kMapUp'):
        assert f'function {name}(' in KORT, name             # kept
        assert not re.search(rf'\b{name}\b', OUTSIDE), name   # but never called from outside the section
    # inside the section no listener starts it: nothing at the top level calls into the map
    assert "addEventListener('change', kortLook)" not in CODE
    assert "need('map')" not in OUTSIDE


def test_no_request_goes_to_the_map_services():
    for host in ('leaflet', 'markercluster', 'maplibre', 'cartocdn', 'openstreetmap', 'openfreemap', 'tile.'):
        assert host not in INDEX.lower(), host
        assert host not in SW.lower(), host
        assert host not in OUTSIDE.lower(), host   # only the shelved section names them
    assert 'mapUrl' not in PAGES and 'CARTO_KEY' not in PAGES


def test_the_radar_no_longer_makes_the_map():
    step = RADAR[RADAR.index('- name: Map'):]
    step = step[:step.index('- name:', 5)]
    assert 'if: false' in step and 'python -m radar.osint' in step   # switched off, kept for when it returns
    assert (ROOT / 'src' / 'radar' / 'osint.py').exists() and (ROOT / 'config' / 'map-places.json').exists()


# ---------------------------------------------------------------- Økonomi
def test_okonomi_is_the_fourth_tab_and_hosts_the_energy_page():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert re.findall(r'data-tab="(\w+)"', nav) == ['home', 'latest', 'kalender', 'okonomi', 'analyses']
    assert '<section class="page" data-tab="okonomi" id="page-okonomi" role="tabpanel" aria-labelledby="tab-okonomi">' in INDEX
    page = fn('okPage')
    assert "if (pg.querySelector('iframe')) return;" in page   # made once, when first shown
    assert '<iframe src="energi/?embed=1"' in page
    assert "if (t === 'okonomi') { okPage(pg); return; }" in fn('draw')
    assert "if (tab === 'okonomi') okPage(pageEl('okonomi'));" in fn('setTab')
    assert 'okPage' not in CODE.split('const START = ')[1].split('\n')[0]   # nothing at the start
    start = CODE.split('const START = ')[1].split('};')[0]
    assert "okonomi: 'okonomi'" in start and "priser: 'okonomi'" in start   # ?tab=priser stays an alias
    assert re.search(r'\.page\[data-tab="okonomi"\] \{ overflow-y: hidden; \}', RULES)
    assert 'var(--dock)' in rule('.ok-pr iframe')


def test_the_energy_links_lead_to_okonomi():
    assert 'href="energi/"' not in APP + INDEX
    assert 'data-priser' not in CODE + INDEX and '?tab=priser' not in CODE + INDEX
    assert '<a class="wide row-link" href="?tab=okonomi" data-okonomi>' in INDEX
    assert 'href="?tab=okonomi" data-okonomi>' in CODE.split('const energyRow = ')[1].split('\n')[0]
    assert 'energyRow()' not in fn('homeFoot')
    assert "setTab('okonomi', { top: true })" in fn('openOkonomi')


def test_the_energy_page_in_the_frame_wears_the_apps_look():
    assert "get('embed') === '1' && parent !== window" in ENERGI
    assert 'html.embed .bar { display: none; }' in ENERGI
    assert "attributeFilter: ['data-theme', 'data-tone', 'data-dark', 'style']" in ENERGI
    assert "localStorage.getItem('textSize')" in ENERGI


# ---------------------------------------------------------------- the options dock above the tabs
def test_the_dock_holds_the_pages_options_above_the_tabs():
    dock = INDEX[INDEX.index('<div class="dock" id="dock">'):INDEX.index('</nav>')]
    assert dock.index('<div class="opts" id="opts"') < dock.index('<nav class="tabs"')   # inside the dock, above the tabs
    paint = fn('paintOpts')
    assert "t === 'latest' ? liveOpts() : t === 'kalender' ? calOpts() : t === 'analyses' ? anOpts() : t === 'okonomi' ? okOpts() : ''" in paint
    assert 'ASIDE.has(t)' in paint   # side pages and search: none
    assert 'morph(box, tpl.content, [])' in paint   # a row keeps its element and its sideways place
    assert '!reduceMotion' in paint
    # Live, Kalender and Analyser: their options are the dock's, not a strip under the bar
    # Live is one list since 18/10 (the owner: 'ingen "seneste" og "vigtigste"'): only the three filters
    assert 'data-live-sec' in fn('liveOpts') and 'data-live-sort' not in CODE and 'liveSort' not in CODE
    assert 'data-cal-f' in fn('calOpts') and 'data-cal-win' in fn('calOpts') and 'data-cal-f' not in fn('kalenderPage')
    assert 'class="o-row an-chips"' in CODE and 'an-chips' not in fn('analysesPage')
    # Økonomi (18/10): its topics are the app's dock; the frame has no fixed dock of its own when embedded
    assert 'data-ok-sec' in CODE and 'window.khabarOk' in CODE and 'contentWindow.okJump' in CODE
    assert 'id="anQ"' in fn('analysesPage')   # the search field stays under the bar: the dock goes with the keyboard
    # the same buttons work in the dock
    assert "$('opts').addEventListener('click', onTap);" in CODE
    # the dock follows the page in view: a tab, a swipe, a redraw
    assert 'paintOpts(tab);' in fn('setTab') and 'paintOpts(SWIPE_TABS[Math.round(k)]);' in CODE
    assert 'if (t === dockTab) paintOpts(t);' in fn('draw')


def test_the_dock_is_solid_reachable_and_out_of_the_way():
    opts = rule('.opts')
    assert 'backdrop-filter' not in opts
    assert re.search(r'\.opts\[hidden\], \.keyboard \.opts \{ display: none; \}', RULES)   # gone while typing
    row = rule('.o-row')
    assert 'overflow-x: auto' in row and 'touch-action: pan-x' in row   # sideways when the row overflows
    assert "new ResizeObserver(() => document.documentElement.style.setProperty('--dock', $('dock').offsetHeight + 'px')).observe($('dock'));" in CODE
    assert re.search(r'\.page::after \{ content: ""; display: block; height: calc\(var\(--dock\) \+ 28px\); \}', RULES)
    assert "innerHeight - $('dock').offsetHeight - 12" in fn('keepInView')
    assert re.search(r'\.dock \{[^}]*padding-bottom: var\(--bottom\)', RULES)   # the safe area under it
