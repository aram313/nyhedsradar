"""The energy page's numbers: pump prices per chain, derived spreads, contract months and energy news (no network)."""
import io
import json
import re
import sys
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import energy  # noqa: E402


def test_pump_products_are_matched_on_the_chains_own_names():
    assert energy.product('miles 95') == energy.product('Benzin 95') == energy.product('GoEasy 95 E10') == 'benzin'
    assert energy.product('Miles Diesel') == energy.product('Diesel') == energy.product('GoEasy Diesel') == 'diesel'
    assert energy.product('GoEasy Diesel Extra') == 'diesel_plus' and energy.product('UPGRADE 95') == 'benzin_plus'
    assert energy.product('AdBlue') is None and energy.product('HPC') is None


def test_q8_city_is_the_words_between_house_number_and_postcode():
    assert energy.q8_city('Dronningemaen 34 Svendborg 5700 Danmark') == 'Svendborg'
    assert energy.q8_city('Vejlevej 2A Kolding 6000 Danmark') == 'Kolding'
    assert energy.q8_city('Ukendt adresse') == ''


def test_each_chain_gets_its_list_price_and_its_cheapest_station():
    st = [{'c': 'F24', 'city': c, 'p': {'benzin': v, 'diesel': 18.89}, 'chg': '2026-10-17T00:01:00+00:00'}
          for c, v in (('Aarhus', 17.69), ('Odense', 17.69), ('Sindal', 17.49))]
    st.append({'c': 'Q8', 'city': 'Vejle', 'p': {'benzin': 17.79}, 'chg': None})
    chains = energy.summarize_pumps(st)
    assert [c['c'] for c in chains] == ['Q8', 'F24']          # the fixed chain order, only chains with stations
    f24 = chains[1]
    assert f24['n'] == 3 and f24['chg'] == '2026-10-17T00:01:00+00:00'
    b = f24['p']['benzin']
    assert (b['v'], b['min'], b['at'], b['nmin']) == (17.69, 17.49, ['Sindal'], 1)


def series(*pairs, t='2026-10-16T20:59:00+00:00'):
    return {'v': pairs[-1][1], 't': t, 'h': [list(p) for p in pairs]}


def test_spreads_join_on_the_days_both_sides_have():
    raw = {'brent': series(('2026-10-15', 100), ('2026-10-16', 110)),
           'wti': series(('2026-10-15', 90), ('2026-10-16', 99)),
           'rbob': series(('2026-10-16', 3.0)),
           'ulsd': series(('2026-10-16', 4.0)),
           'brent_spot': series(('2026-10-14', 120), ('2026-10-15', 125), t='2026-10-15'),
           'usddkk': series(('2026-10-15', 6.5), ('2026-10-16', 6.6))}
    d = energy.derive(raw)
    assert d['brent_wti']['h'] == [['2026-10-15', 10], ['2026-10-16', 11]]
    assert d['crack321']['v'] == (2 * 3.0 * 42 + 4.0 * 42 - 3 * 99) / 3
    assert d['crack_diesel']['v'] == 4.0 * 42 - 110
    # physical minus paper only where the spot has a price, and dated as old as the spot
    assert d['phys_prem']['h'] == [['2026-10-15', 25]] and d['phys_prem']['t'] == '2026-10-15'
    assert abs(d['brent_kr']['v'] - 110 * 6.6 / 158.987) < 1e-3
    assert energy.with_prev(d['brent_wti'])['p'] == 10


def test_contract_months_roll_over_the_year():
    got = energy.contracts('BZ', date(2026, 11, 3), n=3)
    assert got == [('2026-11', 'BZX26.NYM'), ('2026-12', 'BZZ26.NYM'), ('2027-01', 'BZF27.NYM')]


def test_energy_news_finds_oil_and_fuel_but_not_gaza(tmp_path):
    now = datetime.now(timezone.utc)
    iso = lambda h: (now - timedelta(hours=h)).isoformat()  # noqa: E731
    (tmp_path / 'data.json').write_text(json.dumps({'items': [
        {'id': 'a', 'title': 'Oil tanker hit in the Strait of Hormuz', 'title_da': 'Olietankskib ramt i Hormuz-strædet',
         'kw_da': ['Hormuz-strædet'], 'source': 'Reuters', 'published': iso(1), 'link': 'u', 'outlets': 3, 'live': 'rank',
         'members': ['a2']},
        {'id': 'b', 'title': 'Talks on Gaza resume in Cairo', 'source': 'AP', 'published': iso(1), 'link': 'u', 'live': 'rank'},
        {'id': 'c', 'title': 'Brent crude above $110', 'source': 'AP', 'published': iso(100), 'link': 'u', 'live': 'rank'},
    ]}), encoding='utf-8')
    (tmp_path / 'lines.json').write_text(json.dumps({'items': [
        {'i': 'd', 't': 'ارتفاع أسعار النفط', 'tr': 'Oil prices rise', 'da': 'Oliepriserne stiger', 's': 'Al Jazeera', 'p': iso(2), 'u': 'u'},
    ]}), encoding='utf-8')
    (tmp_path / 'summaries.json').write_text(json.dumps({'titles': {
        'a2': {'title': 'Iran: Olietankskib ramt af mine i Hormuz-strædet', 'at': iso(0)}}}), encoding='utf-8')
    news = energy.energy_news(tmp_path, summaries=tmp_path / 'summaries.json')
    # Gaza is not gas; 100 hours is too old; the wire's machine-translated lines are not shown
    assert [n['i'] for n in news] == ['a']
    assert news[0]['ed'] == 'Iran: Olietankskib ramt af mine i Hormuz-strædet'    # the editor's, found by a member
    assert news[0]['da'] == 'Olietankskib ramt i Hormuz-strædet' and news[0]['kd'] == ['Hormuz-strædet']


def test_eia_history_rows_become_dated_prices():
    html = ("<tr> <td class='B6'>&nbsp;&nbsp;2026 Sep-28 to Oct- 2</td> <td class='B3'>120.10</td> <td class='B3'>121.00</td>"
            " <td class='B3'></td> <td class='B3'>119.5</td> <td class='B3'>118.25</td> </tr>"
            " <tr> <td class='B6'>&nbsp;&nbsp;2026 Oct-12 to Oct-16</td> <td class='B3'>129.95</td> <td class='B3'>125.78</td>"
            " <td class='B3'>126.55</td> <td class='B3'></td> <td class='B3'></td> </tr>")
    rows = energy.eia_rows(html, days=10 ** 5)
    assert rows[:3] == [['2026-09-28', 120.1], ['2026-09-29', 121.0], ['2026-10-01', 119.5]]   # the week runs into October
    assert rows[-1] == ['2026-10-14', 126.55] and len(rows) == 7                                  # empty cells skipped


def test_a_chain_changed_its_list_price_when_most_of_its_stations_did():
    st = [{'c': 'Circle K', 'city': f'By {i}', 'p': {'benzin': 17.79}, 'chg': '2026-10-16T08:59:00Z'} for i in range(5)]
    st.append({'c': 'Circle K', 'city': 'Odense', 'p': {'benzin': 17.49}, 'chg': '2026-10-17T08:34:00Z'})
    (ck,) = energy.summarize_pumps(st)
    assert ck['chg'] == '2026-10-16T08:59:00Z'               # one station's own price change is not the chain's


def offline(monkeypatch, **fns):
    """Every source answers nothing (or as given): no test reaches the network."""
    base = {'fetch_markets': lambda: {}, 'fetch_curves': lambda fronts: {}, 'fetch_fred': lambda: {},
            'fetch_pumps': lambda: (None, []), 'fetch_usfuel': lambda: {}, 'fetch_eu': lambda: None,
            'fetch_spy': lambda: None, 'fetch_debt': lambda: None, 'fetch_imf': lambda: None}
    for name, fn in {**base, **fns}.items():
        monkeypatch.setattr(energy, name, fn)


def test_a_source_that_failed_rests_before_it_is_asked_again(tmp_path, monkeypatch):
    calls = []
    offline(monkeypatch, fetch_fred=lambda: calls.append(1) or {}, fetch_debt=lambda: calls.append(2))
    energy.run(tmp_path)
    energy.run(tmp_path)
    assert sorted(calls) == [1, 2]                                 # the second pass, minutes later, leaves the dead sources be


def test_a_source_that_raises_is_marked_failed_not_fatal(tmp_path, monkeypatch):
    def boom():
        raise OSError('down')
    offline(monkeypatch, fetch_imf=boom, fetch_spy=boom)
    out = energy.run(tmp_path)
    assert {'imf', 'spy'} <= set(out['tried']) and out['imf'] is None


def test_a_run_keeps_the_last_good_numbers_when_every_source_fails(tmp_path, monkeypatch):
    old = {'ok': {}, 's': {'brent': {**series(('2026-10-16', 110)), 'p': None},
                           'us_gas': {**series(('2026-10-12', 4.33)), 'p': None}},
           'curve': {'brent': [['2026-12', 110]]},
           'pumps': {'t': 'x', 'chains': [{'c': 'F24'}], 'h': []},
           'debt': {'v': 4e13, 't': '2026-10-15', 'g': 6e9, 'h': []}, 'imf': {'y': 2025, 'c': {'USA': [[2025, 124.4]]}},
           'eu': {'t': '2026-10-12', 'c': {'EU': [2009.8, 2135.9]}, 'h': []}, 'spy': {'t': '2026-10-15', 'ai': 35.5, 'h': []}}
    (tmp_path / 'energy.json').write_text(json.dumps(old), encoding='utf-8')
    offline(monkeypatch)
    out = energy.run(tmp_path)
    assert out['s']['brent']['v'] == 110 and out['curve'] == old['curve'] and out['pumps'] == old['pumps']
    assert out['s']['us_gas']['v'] == 4.33
    assert all(out[k] == old[k] for k in ('debt', 'imf', 'eu', 'spy'))
    assert out['ok'] == {}                                   # nothing new: every source is tried again after RETRY
    assert set(out['tried']) == {'markets', 'curve', 'fred', 'pumps', 'usfuel', 'eu', 'spy', 'debt', 'imf'}


def test_each_source_keeps_its_own_clock(tmp_path, monkeypatch):
    calls = []
    offline(monkeypatch, fetch_imf=lambda: calls.append('imf') or {'y': 2025, 'c': {}},
            fetch_debt=lambda: calls.append('debt') or {'v': 1, 't': '2026-10-15', 'g': 1, 'h': []})
    energy.run(tmp_path)
    energy.run(tmp_path)
    assert sorted(calls) == ['debt', 'imf']                       # asked once; a good answer waits for its EVERY
    assert energy.EVERY['imf'] >= 24 * 3600 and energy.EVERY['markets'] <= 5 * 60


# ---- the economy page's new sources ---------------------------------------------------------------------------------

def test_eia_weekly_rows_become_dated_mondays(monkeypatch):
    monkeypatch.setattr(energy, 'now', lambda: datetime(2026, 10, 17, tzinfo=timezone.utc))
    html = ("<tr> <td class='B6'>&nbsp;&nbsp;2025-Dec</td> <td class='B5'>12/29&nbsp;</td> <td class='B3'>3.100&nbsp;</td> </tr>"
            " <tr> <td class='B6'>&nbsp;&nbsp;2026-Jan</td> <td class='B5'>12/29&nbsp;</td> <td class='B3'>3.105&nbsp;</td>"
            " <td class='B5'>01/05&nbsp;</td> <td class='B3'>3.120&nbsp;&nbsp;&nbsp;</td> </tr>"
            " <tr> <td class='B6'>&nbsp;&nbsp;2026-Oct</td> <td class='B5'>10/05&nbsp;</td> <td class='B3'>4.354&nbsp;&nbsp;&nbsp;</td>"
            " <td class='B5'>10/12&nbsp;</td> <td class='B3'>4.331&nbsp;&nbsp;&nbsp;</td> <td class='B5'>&nbsp;</td>"
            " <td class='B3'>&nbsp;&nbsp;&nbsp;</td> </tr>"
            " <tr> <td class='B6'>&nbsp;&nbsp;2023-Jan</td> <td class='B5'>01/02&nbsp;</td> <td class='B3'>3.2&nbsp;</td> </tr>")
    rows = energy.eia_weeks(html)
    # a January row's late-December week belongs to the year before; empty cells skipped; older than two years cut
    assert rows == [['2025-12-29', 3.1], ['2025-12-29', 3.105], ['2026-01-05', 3.12], ['2026-10-05', 4.354],
                    ['2026-10-12', 4.331]]


def xlsx(rows, strings):
    """A minimal .xlsx: rows of {column: value}; str values become shared strings."""
    def cell(ref, v):
        if isinstance(v, str):
            return f'<c r="{ref}" t="s"><v>{strings.index(v)}</v></c>'
        return f'<c r="{ref}" t="n"><v>{v}</v></c>'
    sheet = ''.join(f'<row r="{i + 1}">' + ''.join(cell(f'{c}{i + 1}', v) for c, v in r.items()) + '</row>'
                    for i, r in enumerate(rows))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/sharedStrings.xml', '<sst>' + ''.join(f'<si><t>{s}</t></si>' for s in strings) + '</sst>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet><sheetData>{sheet}</sheetData></worksheet>')
    return buf.getvalue()


def test_the_eu_bulletin_gives_petrol_and_diesel_per_land():
    strings = ['in EUR', 'Euro-super 95  (I)', 'Gas oil automobile', '1000 l', 'Denmark', 'Germany', 'Sweden',
               'CE/EC/EG EUR27_2020 (IV)\nWeighted average']
    blob = xlsx([{'A': 'in EUR', 'B': 'Euro-super 95  (I)', 'C': 'Gas oil automobile'},
                 {'A': 46307, 'B': '1000 l', 'C': '1000 l'},
                 {'A': 'Denmark', 'B': 2658.2651, 'C': 2501.739},
                 {'A': 'Germany', 'B': 2214, 'C': 2270},
                 {'A': 'Sweden', 'B': 1692.49},
                 {'A': 'CE/EC/EG EUR27_2020 (IV)\nWeighted average', 'B': 2009.759, 'C': 2135.879}], strings)
    eu = energy.eu_prices(energy.xlsx_rows(blob))
    assert eu['t'] == '2026-10-12'                          # Excel's day number is the bulletin's Monday
    assert eu['c']['DK'] == [2658.27, 2501.74] and eu['c']['EU'] == [2009.76, 2135.88]
    assert 'SE' not in eu['c']                              # a land without both prices is left out
    merged = energy.eu_merge({'h': [['2026-10-05', 2000, 2100], ['2026-10-12', 1, 1]]}, eu)
    assert merged['h'] == [['2026-10-05', 2000, 2100], ['2026-10-12', 2009.76, 2135.88]]
    assert energy.eu_merge({'t': 'old'}, None) == {'t': 'old'}


def test_spy_holdings_give_the_ai_basket_its_weight_in_the_sp500():
    strings = ['Fund Name:', 'Holdings:', 'As of 15-Oct-2026', 'Name', 'Ticker', 'Identifier', 'Weight', 'NVIDIA', 'NVDA',
               'Alphabet A', 'GOOGL', 'Alphabet C', 'GOOG', 'Other', 'X']
    rows = [{'A': 'Fund Name:'}, {'A': 'Holdings:', 'B': 'As of 15-Oct-2026'},
            {'A': 'Name', 'B': 'Ticker', 'C': 'Identifier', 'E': 'Weight'},
            {'A': 'NVIDIA', 'B': 'NVDA', 'E': 7.5}, {'A': 'Alphabet A', 'B': 'GOOGL', 'E': 3.0},
            {'A': 'Alphabet C', 'B': 'GOOG', 'E': 2.5}]
    rows += [{'A': 'Other', 'B': f'X{i}', 'E': 0.17} for i in range(500)]
    strings += [f'X{i}' for i in range(500)]
    w = energy.spy_weights(energy.xlsx_rows(xlsx(rows, strings)))
    assert w['t'] == '2026-10-15' and w['n'] == 503
    assert w['w']['nvda'] == 7.5 and w['w']['googl'] == 5.5   # both of Alphabet's share classes
    assert w['w']['tsm'] is None and w['w']['msft'] == 0     # TSMC is not in the index; a missing holding is 0
    assert w['ai'] == 13.0 and w['top10'] == round(7.5 + 3.0 + 2.5 + 7 * 0.17, 4)
    short = energy.spy_weights(energy.xlsx_rows(xlsx(rows[:8], strings)))
    assert short is None                                     # a cut file is not the index
    assert energy.spy_merge(None, w)['h'] == [['2026-10-15', 13.0]]


def test_us_debt_grows_by_its_average_day_over_a_year():
    rows = [{'record_date': '2026-10-15', 'tot_pub_debt_out_amt': '40388317675071.91'},
            {'record_date': '2026-10-14', 'tot_pub_debt_out_amt': '40329229827541.02'},
            {'record_date': '2025-10-15', 'tot_pub_debt_out_amt': '37942700000000.00'},
            {'record_date': '2025-01-02', 'tot_pub_debt_out_amt': 'bad'}]
    d = energy.debt_series(rows)
    assert d['t'] == '2026-10-15' and d['v'] == 40388317675072 and d['gd'] == 365
    assert d['g'] == round((40388317675071.91 - 37942700000000.0) / 365)
    assert d['h'][-1] == ['2026-10-15', 40388.3]             # billions in the chart's history
    assert energy.debt_series(rows[:1]) is None


def test_imf_debt_stops_at_the_last_full_year():
    d = {'values': {'GGXWDG_NGDP': {'USA': {'1999': 60, '2024': 121.0, '2025': 124.4, '2026': 127.0},
                                    'ISR': {'2025': 67.9}, 'DNK': {'2025': 27.4}, 'JPN': {'2025': 204.8},
                                    'GBR': {'2025': 102.1}, 'XXX': {'2025': 1}}}}
    out = energy.imf_debt(d, year=2025)
    assert out['y'] == 2025 and out['c']['USA'] == [[2024, 121.0], [2025, 124.4]]   # no projection, nothing before 2000
    assert 'XXX' not in out['c'] and set(out['c']) == {'USA', 'ISR', 'DNK', 'JPN', 'GBR'}
    assert energy.imf_debt({'values': {}}) is None


# ---- the page (public/energi/index.html): string checks --------------------------------------------------------------

PAGE = (Path(__file__).resolve().parents[1] / 'public' / 'energi' / 'index.html').read_text(encoding='utf-8')


def test_the_page_knows_every_series_the_file_carries():
    for k in [*energy.YAHOO, *energy.FRED, *energy.US_FUEL, 'crack321', 'phys_prem', 'rbob_kr']:
        assert f'\n  {k}: {{' in PAGE, k
    for k in energy.IMF_LAND:
        assert f'\n  {k}: [' in PAGE, k                     # every debt bar has its Danish name and note


TOPIC_ORDER = (('nu', 'Lige nu'), ('kris', 'Kriser'), ('fuel', 'Brændstof'), ('oil', 'Olie'), ('mkt', 'Markeder'), ('ai', 'AI'), ('debt', 'Gæld'),
               ('raw', 'Råvarer'))


def test_the_page_is_one_long_page_of_eight_topics_in_a_fixed_order():
    block = PAGE.split('const TOPICS = [')[1].split('\n];')[0]
    assert re.findall(r"\{ id: '(\w+)', tab: '([^']+)'", block) == list(TOPIC_ORDER)
    assert 'role="tabpanel"' not in PAGE and 'data-group' not in PAGE and 'ecSec' not in PAGE   # no tab views or chips
    # each topic: a section with its fly title, the headline line in the serif (a heading), its time and sources once
    assert '<section class="ec-sec" id="s-${T.h}" data-t="${T.id}" aria-labelledby="f-${T.id}">' in PAGE
    assert '<p class="ec-fly" id="f-${T.id}">${esc(T.fly)}</p><h2 class="ec-head">${esc(head(T.id))}</h2>' in PAGE
    assert re.search(r'\.ec-top::before \{[^}]*background: var\(--red\)', PAGE)        # the short red rule
    assert re.search(r'\.ec-sec \{ padding-top: \d{2}px; \}', PAGE)                     # generous space above
    assert 'font-family: var(--display)' in PAGE.split('.ec-head {')[1].split('}')[0]
    assert "const parts = ['Opdateret ' + when(D.updated)];" in PAGE and "'kilder: ' : 'kilde: '" in PAGE
    assert 'seneste ${esc(stamp(k, x))}' not in PAGE                                    # no time on every row


def test_the_headlines_are_made_from_the_numbers():
    h = PAGE.split('function head(id) {')[1].split('\n}')[0]
    for tid, _ in TOPIC_ORDER:
        assert f"id === '{tid}'" in h, tid
    assert "`Benzin ${nf(low.benzin.v, 2)} kr. – diesel ${nf(low.diesel.v, 2)} kr.`" in h
    assert '`USA’s gæld: ${nf(D.debt.v / 1e12, 1)} billioner $`' in h
    assert "const verb = diff > 0 ? 'steg' : 'faldt';" in PAGE.split('function phrase(')[1].split('\n}')[0]
    assert not re.search(r'\b(vil stige|vil falde|forventes|bør)\b', h)                   # reality only


def test_the_dock_follows_the_scroll():
    assert '<nav class="ec-dock" aria-label="Emner"><div class="ec-tabs" id="tabs"></div></nav>' in PAGE
    assert 'aria-current="${T.id === current}"' in PAGE and "a.setAttribute('aria-current', on)" in PAGE
    assert '.ec-dock { position: fixed; z-index: 30; left: 0; right: 0; bottom: 0; padding-bottom: var(--bottom);' in PAGE
    spy = PAGE.split('function watch() {')[1].split('\n}')[0]
    assert 'new IntersectionObserver(' in spy and 'rootMargin' in spy
    assert "addEventListener('scroll', () => $('#bar').classList.toggle('scrolled', scrollY > 4), { passive: true });" in PAGE
    assert len(re.findall(r"addEventListener\('scroll'", PAGE)) == 1                    # the spy is no scroll listener
    assert "history.replaceState(null, '', '#'" in PAGE and 'history.pushState' not in PAGE   # no steps in the app's history
    # a tap jumps to the topic (smooth unless Reduce Motion), and the chosen chip scrolls into view inside the dock
    j = PAGE.split('function jump(')[1].split('\n}')[0]
    assert "behavior: instant || calm() ? 'auto' : 'smooth'" in j and 'scrollIntoView' not in PAGE
    assert 'box.scrollWidth > box.clientWidth + 1) box.scrollTo({ left: chip.offsetLeft' in PAGE
    assert "matchMedia('(prefers-reduced-motion: reduce)')" in PAGE


def test_each_topic_shows_a_few_tiles_and_folds_the_rest_away():
    block = PAGE.split('const TOPICS = [')[1].split('\n];')[0]
    lists = re.findall(r'tiles: \[(.*?)\]\]', block)
    assert len(lists) == 3                                                              # oil, markets, commodities
    for tiles in lists:
        assert 3 <= tiles.count("['") <= 4, tiles
    # Danish pump prices and the US average in dollars a gallon (the owner, 17/10); the chains' table is gone
    assert "else if (t === 'fuel') out = [pumpTile('benzin'), pumpTile('diesel'), usTile('us_gas'), usTile('us_diesel')];" in PAGE
    assert "'$/gal.'" in PAGE and 'Kæderne i dag' not in PAGE
    assert "else if (t === 'ai') out = [aiwTile(), aiIdxTile(), ...AI_TILES.map(k => sTile(k, '$'))];" in PAGE
    # one quiet 'Flere tal' row per topic, unfolded in place; its contents are made only when unfolded
    assert '<button class="ec-fold" data-fold aria-expanded="${on}" aria-controls="more-${T.id}">Flere tal${CHEV}</button>' in PAGE
    assert "<div class=\"ec-folded\" id=\"more-${T.id}\"${on ? '' : ' hidden'}>${on ? foldHtml(T, base) : ''}</div>" in PAGE
    assert "const FOLDS = new Set(['fuel', 'oil', 'mkt', 'ai', 'debt']);" in PAGE
    # what is folded: crack spreads, the curve, physical minus paper, the single AI stocks, the lands beyond the top 5
    for k in ('crack321', 'curve', 'phys_prem'):
        assert k in block.split("id: 'oil'")[1].split('more:')[1].split('] },')[0], k
    assert "more: [['De øvrige selskaber', ['msft', 'aapl', 'googl', 'amzn', 'avgo', 'meta']]]" in block
    assert '${imfBars(0, 5)}' in PAGE and '${imfBars(5)}' in PAGE
    assert "table(['benzin_plus', 'diesel_plus', 'hvo'], 'Premium')" in PAGE.split('function pumps() {')[1].split('\n}')[0]
    # charts are drawn only for what is opened
    assert 'drawCharts(el);' in PAGE.split('function fill(T) {')[1].split('\n}')[0]


def test_lige_nu_keeps_only_the_biggest_moves_each_a_way_to_its_topic():
    top = PAGE.split('function topMoves() {')[1].split('\n}')[0]
    assert 'if (out.length === 4) break;' in top and '> 2) continue;' in top
    assert '<button class="ec-mv" data-go="${m.k}">' in PAGE
    assert 'if (go) { goFigure(go.dataset.go); return; }' in PAGE
    assert '<b>Pumpen:</b>' not in PAGE and '<b>Brent:</b>' not in PAGE   # no repeats of the topics below
    assert all(k in PAGE.split('const HOME = {};')[1].split('const FOLDS')[0] for k in ('T.tiles', 'T.more', 'AI'))


def test_each_figure_says_what_it_is_why_and_what_a_rise_or_fall_means():
    assert '<dt>Hvad er det</dt>' in PAGE and 'Hvorfor holde øje med det nu' in PAGE
    assert 'Stiger det' in PAGE and 'Falder det' in PAGE
    block = PAGE.split('const C = {')[1].split('\n};')[0]
    for k in [*energy.YAHOO, *energy.US_FUEL]:
        text = re.split(r'\n  \w+: \{', block.split(f'\n  {k}: {{')[1])[0]   # this figure's entry only
        assert 'what:' in text and 'why:' in text and 'up:' in text and 'down:' in text, k


def test_the_page_says_it_is_not_investment_advice():
    assert 'Siden er information, ikke investeringsrådgivning.' in PAGE
    assert not re.search(r'\b(køb nu|sælg nu|anbefaler vi)\b', PAGE, re.I)


def test_the_debt_counter_is_labelled_an_estimate():
    assert '<span class="ec-est">Skøn</span>' in PAGE and 'Skøn mellem de daglige tal' in PAGE
    assert "aria-label=\"USA’s statsgæld, skøn\"" in PAGE


def test_the_page_keeps_the_embed_contract_and_the_house_style():
    assert "get('embed') === '1' && parent !== window" in PAGE and 'html.embed .bar { display: none; }' in PAGE
    assert "localStorage.getItem('textSize')" in PAGE and 'href="../style.css"' in PAGE
    assert 'Source+Serif+4:opsz,wght@8..60,400..700' in PAGE
    assert "ISR: ['“israel”'" in PAGE and 'Israel' not in PAGE.split('const LAND = {')[1].split('};')[0]
    assert 'backdrop-filter' not in PAGE and 'prefers-reduced-motion' in PAGE
    assert 'Claude' not in PAGE
    assert 'setInterval(() => { if (!document.hidden) load(); }, 5 * 60e3);' in PAGE
    assert "document.addEventListener('visibilitychange'" in PAGE


def test_economic_crises_are_news_of_their_own():
    assert energy.CRISIS.search('Egypt seeks IMF bailout as pound plunges') and energy.CRISIS.search('Ny straftold mod Kina')
    assert not energy.CRISIS.search('Sisi: I have told Netanyahu many times') and not energy.CRISIS.search('Plane crash in Nepal')
    assert "'crisis': energy_news(state, hours=96, limit=12, pattern=CRISIS)" in (Path(energy.__file__).read_text(encoding='utf-8'))
    assert "news(D.crisis || [], 'Ingen nyheder om økonomiske kriser de seneste fire døgn.'" in PAGE
