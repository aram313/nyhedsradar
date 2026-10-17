"""The phone app's fixed points, checked on its files (public/): the three tabs, the versioned files, the config the
deploy writes, the wiki files the app reads, and the owner's rule that the app never names Claude."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
INDEX = (PUBLIC / 'index.html').read_text(encoding='utf-8')
APP = (PUBLIC / 'app.js').read_text(encoding='utf-8')
CSS = (PUBLIC / 'style.css').read_text(encoding='utf-8')


def test_three_tabs_forside_live_analyser_in_that_order():
    nav = INDEX[INDEX.index('<nav class="tabs"'):INDEX.index('</nav>')]
    assert re.findall(r'data-tab="(\w+)"', nav) == ['home', 'latest', 'analyses']
    assert [s for s in re.findall(r'<span>([^<]+)</span>', nav)] == ['Forside', 'Live', 'Analyser']
    assert "const SWIPE_TABS = ['home', 'latest', 'analyses'];" in APP


def test_every_page_the_app_draws_has_its_section():
    pages = re.findall(r'<section class="page[^"]*" data-tab="(\w+)"', INDEX)
    assert pages == ['home', 'latest', 'analyses', 'threads', 'begreb', 'begreber', 'svar', 'gemt', 'search']
    for side in ('threads', 'begreb', 'begreber', 'svar', 'gemt'):
        assert f'<section class="page side" data-tab="{side}"' in INDEX


def test_the_old_section_tabs_open_live():
    assert "const START = { dk: 'latest', me: 'latest', world: 'latest'" in APP


def test_app_and_style_carry_one_version():
    v = re.findall(r'(?:app\.js|style\.css)\?v=([\w-]+)', INDEX)
    assert len(v) == 2 and v[0] == v[1], v


def test_the_deploy_writes_the_answers_and_energy_urls():
    pages = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
    for key in ('dataUrl', 'digestUrl', 'searchUrl', 'movesUrl', 'answersUrl', 'analysesUrl', 'energyUrl'):
        assert re.search(rf'^\s+{key}: "https://raw\.githubusercontent\.com/', pages, re.M), key
    assert 'digest/answers.json' in pages and 'data/analyses.json' in pages


def test_the_wiki_files_the_app_reads_are_published_with_it():
    for name in ('begreber-index.json', 'begreber.json', 'movement-index.json', 'movement.json'):
        assert f"'{name}'" in APP, name
        data = json.loads((PUBLIC / 'viden' / name).read_text(encoding='utf-8'))
        assert data.get('version') == 1, name


def test_the_app_never_names_claude():
    for path in [PUBLIC / 'index.html', PUBLIC / 'app.js', PUBLIC / 'style.css', PUBLIC / 'manifest.webmanifest', PUBLIC / 'guide.html']:
        assert not re.search(r'claude', path.read_text(encoding='utf-8'), re.I), path.name


def test_the_movements_face_is_its_own_and_every_new_font_size_follows_the_text_size():
    assert re.search(r'--serif: ui-serif, "New York", "Iowan Old Style", Charter, Georgia, serif', CSS)
    assert '--ht-bg: #efe7d6' in CSS
    new = CSS[CSS.index("/* ------------------------------------------------------------ a row's tap lies under its words"):]
    sizes = re.findall(r'font-size:\s*([^;]+);', new)
    assert sizes and all('var(--fs-' in s for s in sizes), [s for s in sizes if 'var(--fs-' not in s]


def test_a_link_to_the_wiki_is_never_put_inside_a_button():
    # the rows that open (a story, a recap line, a step) keep their button or link under the words, never around them
    assert '<button class="row"' not in APP and '<button class="hero-row"' not in APP and 'class="step"' not in APP
    assert '<button class="hit" data-toggle' in APP
