"""The energy page's numbers: pump prices per chain, derived spreads, contract months and energy news (no network)."""
import json
import sys
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


def test_a_source_that_failed_rests_before_it_is_asked_again(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(energy, 'fetch_markets', lambda: {})
    monkeypatch.setattr(energy, 'fetch_curves', lambda fronts: {})
    monkeypatch.setattr(energy, 'fetch_fred', lambda: calls.append(1) or {})
    monkeypatch.setattr(energy, 'fetch_pumps', lambda: (None, []))
    energy.run(tmp_path)
    energy.run(tmp_path)
    assert len(calls) == 1                                   # the second pass, minutes later, leaves the dead source be


def test_a_run_keeps_the_last_good_numbers_when_every_source_fails(tmp_path, monkeypatch):
    old = {'ok': {}, 's': {'brent': {**series(('2026-10-16', 110)), 'p': None}}, 'curve': {'brent': [['2026-12', 110]]},
           'pumps': {'t': 'x', 'chains': [{'c': 'F24'}], 'h': []}}
    (tmp_path / 'energy.json').write_text(json.dumps(old), encoding='utf-8')
    monkeypatch.setattr(energy, 'fetch_markets', lambda: {})
    monkeypatch.setattr(energy, 'fetch_curves', lambda fronts: {})
    monkeypatch.setattr(energy, 'fetch_fred', lambda: {})
    monkeypatch.setattr(energy, 'fetch_pumps', lambda: (None, []))
    out = energy.run(tmp_path)
    assert out['s']['brent']['v'] == 110 and out['curve'] == old['curve'] and out['pumps'] == old['pumps']
    assert out['ok'] == {}                                   # nothing new: every source is tried again after RETRY
    assert set(out['tried']) == {'markets', 'curve', 'fred', 'pumps'}
