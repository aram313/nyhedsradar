"""Headlines that say the news: the rules at intake (feeds.tidy, docs/hjerne/kilder-maaling.md 'Små rettelser'), a
Turkish post in an English channel, and the curiosity headline (src/radar/headlines.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from radar import feeds  # noqa: E402
from radar.headlines import curious  # noqa: E402

FEEDS = {f['name']: f for f in json.loads((ROOT / 'config' / 'feeds.json').read_text(encoding='utf-8'))}


def tidy(source, title, summary='', lang='en'):
    got = feeds.tidy({'id': 'x', 'title': title, 'summary': summary, 'link': 'https://x.test/1', 'source': source,
                      'lang': lang}, FEEDS[source])
    return got and got['title']


def test_no_news_is_left_out():
    assert tidy('Times of Israel', 'The Blogs: Why Do We Love Noah’s Ark?') is None
    assert tidy('Jerusalem Post', 'How war with Iran is influencing Israeli, US elections - analysis') is None
    assert tidy('Jerusalem Post', 'Where should Canadian Jews go? Where is the Promised Land? - opinion') is None
    assert tidy('BT', 'Premier League Bet Builder hos Expekt: Odds 3,17 på flere Haaland-mål', lang='da') is None
    assert tidy('Ahram Online', "Man Utd have 'moved on' from Martinez outburst, says Carrick - World - Sports") is None
    # the news of the same sources stays as it was
    assert tidy('Jerusalem Post', 'IDF kills Hamas commander in Gaza') == 'IDF kills Hamas commander in Gaza'
    assert tidy('BT', 'Houthier har angrebet saudiarabisk lufthavn 20 gange i oktober', lang='da') == \
        'Houthier har angrebet saudiarabisk lufthavn 20 gange i oktober'


def test_what_is_not_the_news_is_cut_off():
    assert tidy('Ahram Online', 'Egypt, 18 countries condemn Colombia’s Jerusalem embassy inauguration - Foreign Affairs - '
                'Egypt') == 'Egypt, 18 countries condemn Colombia’s Jerusalem embassy inauguration'
    assert tidy('Shafaq News', 'Shafaq News..US pauses strikes on Iranian missiles in Hormuz, Axios says') == \
        'US pauses strikes on Iranian missiles in Hormuz, Axios says'
    assert tidy('INA', 'Oil: Two new oil wells brought into service at the Nasiriyah oil field » Iraqi News Agency') == \
        'Oil: Two new oil wells brought into service at the Nasiriyah oil field'
    assert tidy('Enab Baladi', 'Death and Prison Sentences Issued Over Syria Coast Violence - Enab Baladi') == \
        'Death and Prison Sentences Issued Over Syria Coast Violence'
    assert tidy('Petra', 'Jordan Welcomes UN Security Council Condemnation of Houthi Attacks - The Jordan News Agency') == \
        'Jordan Welcomes UN Security Council Condemnation of Houthi Attacks'
    # a source named at the end of the news stays (it is who said it)
    assert tidy('UN News', 'Gaza: 340 children killed despite ceasefire agreement - UNICEF') == \
        'Gaza: 340 children killed despite ceasefire agreement - UNICEF'
    # a second pass changes nothing
    assert tidy('Shafaq News', 'US pauses strikes on Iranian missiles in Hormuz, Axios says') == \
        'US pauses strikes on Iranian missiles in Hormuz, Axios says'


def test_a_channel_post_that_only_names_who_speaks():
    got = feeds.tidy({'id': 'x', 'title': 'Kamala Harris on Israel:', 'link': 'https://t.me/c/1', 'source': 'Clash Report',
                      'lang': 'en', 'summary': 'It is in our interest to hold our allies accountable. They must pay their share.'},
                     FEEDS['Clash Report'])
    assert got['title'] == 'Kamala Harris on Israel: It is in our interest to hold our allies accountable.', got['title']
    assert got['summary'] == 'They must pay their share.'
    assert feeds.tidy(dict(got), FEEDS['Clash Report'])['title'] == got['title']
    # from the channel's page, as the radar reads it
    page = ('<div data-post="clashreport/9"><div class="tgme_widget_message_text js-message_text">'
            'Palantir CTO Shyam Sankar:<br/>So many AI researchers have started smoking as a signal. More soon.'
            '</div><time datetime="2026-10-17T06:00:00+00:00"></time></div>')
    item = feeds.tidy(feeds.parse_telegram(page, FEEDS['Clash Report'])[0], FEEDS['Clash Report'])
    assert item['title'] == 'Palantir CTO Shyam Sankar: So many AI researchers have started smoking as a signal.'


def test_turkish_posts_in_an_english_channel():
    assert feeds.sniff('Kazakistan, Kırgızistan vb gibi Türki devletler salonda kalmaya devam ediyorlar', 'en') == 'tr'
    assert feeds.sniff('İstanbul Medeniyet Üniversitesi öğretim görevlisi Dr. Elnur İsmayıl: Azerbaycan\'ın kararı hicaba '
                       'karşı değil.', 'en') == 'tr'
    assert feeds.sniff("Türkiye's Erdoğan meets Putin in İstanbul", 'en') == 'en'
    assert feeds.sniff('Erdoğan and Şahin say the talks in Ankara were good for both sides', 'en') == 'en'
    got = feeds.tidy({'id': 'x', 'title': 'Bazı okullarda müdürler fiziki müdahalelere başladı ve bu devam ediyor',
                      'summary': '', 'link': 'https://t.me/d/1', 'source': 'Daily Islamist', 'lang': 'en',
                      'title_da': 'maskinens danske'}, FEEDS['Daily Islamist'])
    assert got['lang'] == 'tr' and 'title_da' not in got   # translated again, from Turkish


def test_curiosity_headlines():
    for t in ['Derfor er Putin stadig præsident', 'Se billederne: Kaos i lufthavnen', 'Her er de tre største udfordringer',
              'Kan Europa stole på USA? Mette Frederiksen tøver', 'Why is the haze so bad in Southeast Asia this year?',
              'How Israel’s ‘Yellow Line’ is reshaping southern Lebanon', 'Explainer: What is Starshield?',
              'Klamt fund: Skjult kamera fundet i kahyt', '»Jeg er ikke så let at krænke«', 'Kamala Harris on Israel:',
              'Elections delayed: A generation is denied its right to choose - opinion', 'What we know about the arrest']:
        assert curious(t), t
    for t in ['Trump om Grønlandsaftale: Nok min bedste ejendomshandel nogensinde', 'Moldova fordømmer Rusland efter '
              'droners indtrængen', '»Fik det for ingenting«: Trump kalder Grønlandsaftale en handel',
              'WHO warns of Ebola spread in 22 countries', 'Israeli settlers attack Palestinians in West Bank',
              'Kremlin: Starlink should not be used for war', "'We will respond,' Iran says after strikes"]:
        assert not curious(t), t
