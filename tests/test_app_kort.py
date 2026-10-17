"""The Kort tab (the owner's wish of 2026-10-17: 'en fane for sig selv der bliver en slags live osint med kort og
seneste angreb lidt ligesom LiveUAmap') and, since 2026-10-18, the Økonomi tab beside it and the options dock above
the tabs, checked on the app's files: the tabs and their pages, Leaflet and its cluster plugin fetched only when the map
is needed (with SRI), the map's attribution, the quiet look, the zones, the dock, and the energy links leading to
Økonomi."""
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


def rule(sel):
    m = re.search(r'(?:^|\})\s*' + re.escape(sel) + r'\s*\{([^}]*)\}', RULES)
    assert m, sel
    return m.group(1)


def test_the_tab_its_page_and_its_name():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert '<button role="tab" id="tab-kort" aria-controls="page-kort" data-tab="kort"' in nav and '#i-map' in nav
    assert '<symbol id="i-map"' in INDEX
    assert '<section class="page" data-tab="kort" id="page-kort" role="tabpanel" aria-labelledby="tab-kort">' in INDEX
    assert "kort: 'Kort'" in CODE.split('const TITLES = ')[1].split('};')[0]
    start = CODE.split('const START = ')[1].split('};')[0]
    assert "kort: 'kort'" in start
    assert '<b>Kort</b>' in INDEX and '<b>Økonomi</b>' in INDEX   # the first visit's intro names the tabs
    assert 'data-kview' not in CODE and 'Priser' not in fn('kortPage')   # no Kort/Priser segment any more


def test_a_drag_on_the_map_pans_the_map_not_the_pages():
    assert re.search(r'\.k-box \{[^}]*touch-action: none', RULES)
    assert "!e.target.closest('.k-box')) pull = {" in CODE   # no pull to refresh from the map either


def test_leaflet_and_its_clusters_are_fetched_only_when_the_map_is_needed_with_sri():
    assert 'leaflet' not in INDEX.lower() and 'markercluster' not in INDEX.lower()   # never in the page: never at the start
    assert "const LEAFLET = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/';" in CODE
    assert "const CLUSTER = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/';" in CODE
    load = fn('loadLeaflet')
    assert "LEAFLET + 'leaflet.min.css'" in load and "LEAFLET + 'leaflet.min.js'" in load and load.count("integrity: 'sha256-") == 2
    assert '.then(loadCluster)' in load   # the plugin after Leaflet: it extends Leaflet's L
    cl = fn('loadCluster')
    assert "CLUSTER + 'MarkerCluster.css'" in cl and "CLUSTER + 'leaflet.markercluster.js'" in cl
    assert "integrity: 'sha256-YU3qCpj/P06tdPBJGPax0bm6Q1wltfwjsho5TR4+TYc='" in cl
    assert "integrity: 'sha256-Hk4dIpcqOSb0hZjgyvFOP+cEmDXUKKNE/tT542ZbNQg='" in cl
    assert '.catch(() => null)' in cl   # without the plugin the markers stand alone
    assert "el.crossOrigin = 'anonymous';" in fn('leafPart')   # SRI on a cross-origin file needs CORS
    # asked for only from the map's own view, when the tab is in view or a swipe heads for it
    callers = [m.start() for m in re.finditer(r'(?<!function )loadLeaflet\(\)', CODE)]
    owners = {CODE[:c].rsplit('\nfunction ', 1)[1].split('(')[0] for c in callers}
    assert owners == {'kortWarm', 'kMapUp'}, owners
    assert re.findall(r'(?<!function )loadCluster\b', CODE) == ['loadCluster']   # only after Leaflet
    assert "if (tab === 'kort') kMapUp(pg);" in fn('kortPage')
    assert "if (tab === 'kort') kortShown();" in fn('setTab')


def test_zoomed_out_the_map_shows_numbered_bubbles_never_a_ring():
    init = fn('kInit')
    assert 'Lf.markerClusterGroup ? Lf.markerClusterGroup({' in init and ': Lf.layerGroup()' in init
    assert 'zoomToBoundsOnClick: true' in init and 'spiderfyOnMaxZoom: true' in init   # a tap zooms in or fans out
    assert 'animate: !reduceMotion' in init and 'iconCreateFunction: kClusterIcon' in init
    assert 'kSpread' not in CODE and 'kRing' not in CODE   # the old fan-out ring is gone
    icon = fn('kClusterIcon')
    assert 'getAllChildMarkers()' in icon and '<b>${n}</b>' in icon and "'<i class=\"live-dot\"></i>'" in icon
    assert 'm.options.kLive' in icon and 'kLive: kLive(e)' in fn('kMarkers')
    assert 'kLayer.addLayers(ms)' in fn('kMarkers')
    kc = rule('.kc')
    assert 'var(--bg)' in kc and 'pulse' not in kc and 'red' not in kc   # quiet: no red unless an event of the last hour
    assert 'font-size: var(--fs-meta)' in rule('.kc b')


def test_the_zones_fly_and_keep_the_list_to_them():
    zones = CODE.split('const KZONES = [')[1].split('];')[0]
    names = re.findall(r"\['\w+', '([^']+)', \[", zones)
    assert names == ['Gaza', 'Vestbredden', 'Libanon/Syrien', 'Irak/Iran', 'Jemen/Rødehavet', 'Ukraine/Rusland', 'Afrika']
    opts = fn('kortOpts')
    assert "['', 'Hele kortet', all.length]" in opts and 'data-kzone=' in opts and '<small>${n}</small>' in opts
    to = fn('kZoneTo')
    assert 'if (reduceMotion) kMap.fitBounds(b' in to and 'kMap.flyToBounds(b' in to
    assert "kFit(kShown(), true)" in to   # Hele kortet: the default view back
    assert 'kZone ? shown.filter(e => kZoneOf(e) === kZone) : shown' in fn('kortFill')


def test_the_map_names_its_sources():
    assert 'OpenStreetMap</a> contributors' in CODE and 'CARTO</a>' in CODE
    assert 'attribution: CARTO' in fn('kortLook') and 'attribution: OSM' in fn('kortLook')
    assert "Lf.control.attribution({ position: 'bottomright', prefix: false })" in fn('kInit')
    look = fn('kortLook')
    assert "dark ? 'dark_all' : 'light_all'" in look and '?key=${encodeURIComponent(CFG.cartoKey)}' in look
    assert 'cartoKey: "${{ vars.CARTO_KEY }}"' in PAGES and 'mapUrl: "https://raw.githubusercontent.com/' in PAGES


def test_the_look_stays_quiet():
    assert not re.search(r'backdrop-filter:(?!\s*none)', RULES)
    kort = RULES[RULES.index('.k-box {'):RULES.index('.ok-pr iframe')]
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', kort):
        sel, decl = ' '.join(m.group(1).split()), m.group(2)
        if 'pulse' in decl:
            assert '.live-dot' in sel, sel   # red only as the ring of an event of the last hour
        for t in re.findall(r'transition:\s*([^;}]+)', decl):
            assert t.strip().startswith('transform'), (sel, t)
    assert re.search(r'\.km\.ca \{[^}]*dashed', RULES)   # an approximate place: a hollow dashed ring
    assert 'const kLive = e => Date.now() - new Date(e.p) < 3600e3;' in CODE


def test_the_map_fills_the_room_above_the_dock_and_the_list_scrolls_under_it():
    box = rule('.k-box')
    assert 'position: sticky' in box and 'var(--dock)' in box and 'var(--barh)' in box
    assert 'scrollTo' not in fn('kPick')   # the map is always in view: a row's choice does not scroll the list away
    assert 'new ResizeObserver(() => { if (kMap) kMap.invalidateSize' in fn('kInit')


def test_rows_follow_the_apps_row_rules():
    row = CODE.split('function kRow(e) {')[1].split('\n}')[0]
    assert 'class="hit" data-kev=' in row and 'aria-hidden="true"' in row and 'stamp(e.p)' in row
    assert 'n >= 3 ?' in row and 'omtrentlig placering' in row and '<a ' not in row   # no link inside the row's button
    assert "Ingen angreb eller kampe${zn ? ' i ' + zn : ''} i nyhederne de seneste ${win}." in fn('kortFill')
    assert "retry('kortet', 'map')" in fn('kortFill') and "loadingBlock('Henter kortet …')" in fn('kortFill')


def test_a_file_the_same_as_last_time_draws_nothing():
    assert 'map: 90e3' in CODE.split('const VFRESH = ')[1].split('\n')[0]   # with the news's two-minute cycle
    assert "map: ['kort']" in fn('vLoaded')
    assert "if (sig === kDrawn && kOf === V('map')) return;" in fn('kortFill')
    assert 'if (!Lf || key === kBuilt) return false;' in fn('kMarkers')
    assert "if (t === 'kort') { kortPage(pg); return; }" in fn('draw')


def test_reduce_motion_and_the_remembered_choices():
    pick = fn('kPick')
    assert 'if (reduceMotion) { kMap.setView(' in pick and 'kMap.flyTo(' in pick
    assert 'kLayer.zoomToShowLayer(mk.m' in pick   # a row's event comes out of its bubble
    assert "store.get('kortWin', 24)" in CODE and "store.set('kortWin', h)" in CODE


def test_okonomi_is_the_fifth_tab_and_hosts_the_energy_page():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert re.findall(r'data-tab="(\w+)"', nav) == ['home', 'latest', 'kort', 'okonomi', 'analyses']
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
    assert "t === 'latest' ? liveOpts() : t === 'kort' ? kortOpts() : t === 'analyses' ? anOpts() : ''" in paint
    assert 'ASIDE.has(t)' in paint   # side pages and search: none
    assert 'morph(box, tpl.content, [])' in paint   # a row keeps its element and its sideways place
    assert '!reduceMotion' in paint
    # Live, Kort and Analyser: their options are the dock's, not a strip under the bar
    assert 'data-live-sort' in fn('liveOpts') and 'data-live-sec' in fn('liveOpts') and 'data-live-sort' not in fn('latestPage')
    assert 'data-kwin' in fn('kortOpts') and 'data-kkind' in fn('kortOpts') and 'data-kzone' in fn('kortOpts')
    assert '"k-chips' not in CODE and '"k-kinds' not in CODE
    assert 'class="o-row an-chips"' in CODE and 'an-chips' not in fn('analysesPage')
    assert 'id="anQ"' in fn('analysesPage')   # the search field stays under the bar: the dock goes with the keyboard
    # the same buttons work in the dock
    assert "$('opts').addEventListener('click', onTap);" in CODE
    assert "$('opts').addEventListener('click', e => { if ($('opts').dataset.for === 'kort') kortTap(e.target); });" in CODE
    # the dock follows the page in view: a tab, a swipe, a redraw
    assert 'paintOpts(tab);' in fn('setTab') and 'paintOpts(SWIPE_TABS[Math.round(k)]);' in CODE
    assert "if (t === dockTab && t !== 'kort') paintOpts(t);" in fn('draw')


def test_the_dock_is_solid_reachable_and_out_of_the_way():
    opts = rule('.opts')
    assert 'backdrop-filter' not in opts
    assert re.search(r'\.opts\[hidden\], \.keyboard \.opts \{ display: none; \}', RULES)   # gone while typing
    row = rule('.o-row')
    assert 'overflow-x: auto' in row and 'touch-action: pan-x' in row   # sideways when the row overflows
    # the dock lies in the fixed .dock, whose height (tabs + options + the home bar) is --dock: the pages' room at
    # their foot, the toast's place and keepInView (an opened story's buttons come up above it) all count it
    assert "new ResizeObserver(() => document.documentElement.style.setProperty('--dock', $('dock').offsetHeight + 'px')).observe($('dock'));" in CODE
    assert re.search(r'\.page::after \{ content: ""; display: block; height: calc\(var\(--dock\) \+ 28px\); \}', RULES)
    assert "innerHeight - $('dock').offsetHeight - 12" in fn('keepInView')
    assert re.search(r'\.dock \{[^}]*padding-bottom: var\(--bottom\)', RULES)   # the safe area under it
