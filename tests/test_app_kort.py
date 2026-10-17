"""The Kort tab (the owner's wish of 2026-10-17: 'en fane for sig selv der bliver en slags live osint med kort og
seneste angreb lidt ligesom LiveUAmap'), checked on the app's files: the tab and its page, Leaflet fetched only when
the map is needed, the map's attribution, the quiet look, and the old energy links leading to the tab's Priser view."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')
INDEX = (PUBLIC / 'index.html').read_text(encoding='utf-8')
ENERGI = (PUBLIC / 'energi' / 'index.html').read_text(encoding='utf-8')
PAGES = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
CODE = re.sub(r'(^|\s)//[^\n]*', r'\1', APP)
RULES = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)


def fn(name):
    m = re.search(r'\n(?:async )?function ' + re.escape(name) + r'\(.*?\n\}', CODE, re.S)
    assert m, name
    return m.group(0)


def test_the_tab_its_page_and_its_name():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert '<button role="tab" id="tab-kort" aria-controls="page-kort" data-tab="kort"' in nav and '#i-map' in nav
    assert '<symbol id="i-map"' in INDEX
    assert '<section class="page" data-tab="kort" id="page-kort" role="tabpanel" aria-labelledby="tab-kort">' in INDEX
    assert "kort: 'Kort'" in CODE.split('const TITLES = ')[1].split('};')[0]
    start = CODE.split('const START = ')[1].split('};')[0]
    assert "kort: 'kort'" in start and "priser: 'kort'" in start
    assert "if (params.get('tab') === 'priser') kView = 'priser';" in CODE
    assert '<b>Kort</b>' in INDEX   # the first visit's intro names the four tabs


def test_a_drag_on_the_map_pans_the_map_not_the_pages():
    assert re.search(r'\.k-box \{[^}]*touch-action: none', RULES)
    assert "!e.target.closest('.k-box')) pull = {" in CODE   # no pull to refresh from the map either


def test_leaflet_is_fetched_only_when_the_map_is_needed():
    assert 'leaflet' not in INDEX.lower()   # never in the page: never at the start
    assert "const LEAFLET = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/';" in CODE
    load = fn('loadLeaflet')
    assert "LEAFLET + 'leaflet.min.css'" in load and "LEAFLET + 'leaflet.min.js'" in load and load.count("integrity: 'sha256-") == 2
    # asked for only from the map's own view, when the tab is in view or a swipe heads for it
    callers = [m.start() for m in re.finditer(r'(?<!function )loadLeaflet\(\)', CODE)]
    owners = {CODE[:c].rsplit('\nfunction ', 1)[1].split('(')[0] for c in callers}
    assert owners == {'kortWarm', 'kMapUp'}, owners
    assert "if (tab !== 'kort') return;" in fn('kortView')
    assert "if (tab === 'kort') kortShown();" in fn('setTab')


def test_the_map_names_its_sources():
    assert 'OpenStreetMap</a> contributors' in CODE and 'CARTO</a>' in CODE
    assert 'attribution: CARTO' in fn('kortLook') and 'attribution: OSM' in fn('kortLook')
    assert "Lf.control.attribution({ position: 'bottomright', prefix: false })" in fn('kInit')
    look = fn('kortLook')
    assert "dark ? 'dark_all' : 'light_all'" in look and '?key=${encodeURIComponent(CFG.cartoKey)}' in look
    assert 'cartoKey: "${{ vars.CARTO_KEY }}"' in PAGES and 'mapUrl: "https://raw.githubusercontent.com/' in PAGES


def test_the_look_stays_quiet():
    assert not re.search(r'backdrop-filter:(?!\s*none)', RULES)
    kort = RULES[RULES.index('.k-top {'):RULES.index('.k-pr iframe')]
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', kort):
        sel, decl = ' '.join(m.group(1).split()), m.group(2)
        if 'pulse' in decl:
            assert '.live-dot' in sel, sel   # red only as the ring of an event of the last hour
        for t in re.findall(r'transition:\s*([^;}]+)', decl):
            assert t.strip().startswith('transform'), (sel, t)
    assert re.search(r'\.km\.ca \{[^}]*dashed', RULES)   # an approximate place: a hollow dashed ring
    assert 'const kLive = e => Date.now() - new Date(e.p) < 3600e3;' in CODE


def test_rows_follow_the_apps_row_rules():
    row = CODE.split('function kRow(e) {')[1].split('\n}')[0]
    assert 'class="hit" data-kev=' in row and 'aria-hidden="true"' in row and 'stamp(e.p)' in row
    assert 'n >= 3 ?' in row and 'omtrentlig placering' in row and '<a ' not in row   # no link inside the row's button
    assert 'Ingen angreb eller kampe i nyhederne de seneste ${win}.' in fn('kortFill')
    assert "retry('kortet', 'map')" in fn('kortFill') and "loadingBlock('Henter kortet …')" in fn('kortFill')


def test_a_file_the_same_as_last_time_draws_nothing():
    assert 'map: 90e3' in CODE.split('const VFRESH = ')[1].split('\n')[0]   # with the news's two-minute cycle
    assert "map: ['kort']" in fn('vLoaded')
    assert "if (sig === kDrawn && kOf === V('map')) return;" in fn('kortFill')
    assert 'if (!Lf || key === kBuilt) return false;' in fn('kMarkers')
    assert "if (t === 'kort') { kortPage(pg); return; }" in fn('draw')


def test_reduce_motion_and_the_remembered_choices():
    pick = fn('kPick')
    assert 'if (reduceMotion) kMap.setView(' in pick and 'kMap.flyTo(' in pick
    assert "store.get('kortView', 'kort')" in CODE and "store.get('kortWin', 24)" in CODE
    assert "store.set('kortWin', h)" in CODE and "store.set('kortView', v)" in CODE


def test_the_energy_links_lead_to_the_tab():
    assert 'href="energi/"' not in APP + INDEX
    assert '<a class="wide row-link" href="?tab=priser" data-priser>' in INDEX
    assert "href=\"?tab=priser\" data-priser>" in CODE.split('const energyRow = ')[1].split('\n')[0]
    assert 'energyRow()' not in fn('homeFoot')   # the front page's foot link is gone
    assert "kView = 'priser'" in fn('openPriser')
    assert '<iframe src="energi/?embed=1"' in fn('kFrame')


def test_the_energy_page_in_the_frame_wears_the_apps_look():
    assert "get('embed') === '1' && parent !== window" in ENERGI
    assert 'html.embed .bar { display: none; }' in ENERGI
    assert "attributeFilter: ['data-theme', 'data-tone', 'data-dark', 'style']" in ENERGI
    assert "localStorage.getItem('textSize')" in ENERGI
