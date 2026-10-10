"""Feed parsing: the item's own picture, and posts in another language than their channel's."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar import feeds  # noqa: E402

RSS = b"""<?xml version="1.0"?>
<rss xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Guardian style: several sizes of the same picture</title><link>https://a.test/1</link>
  <media:content url="https://img.test/small.jpg" width="140"/><media:content url="https://img.test/big.jpg" width="460"/></item>
<item><title>A podcast episode with only an audio file attached</title><link>https://a.test/2</link>
  <enclosure url="https://a.test/ep.mp3" type="audio/mpeg"/></item>
<item><title>Picture only inside the escaped HTML of the description</title><link>https://a.test/3</link>
  <description>&lt;p&gt;&lt;img src="https://img.test/in-html.jpg" /&gt; Tekst&lt;/p&gt;</description></item>
<item><title>Video feed: the thumbnail, never the video file</title><link>https://a.test/4</link>
  <media:group><media:content url="https://www.youtube.com/v/abc" type="application/x-shockwave-flash"/>
  <media:thumbnail url="https://i.ytimg.test/vi/abc/hqdefault.jpg" width="480"/></media:group></item>
</channel></rss>"""


def test_feed_pictures():
    got = {i['link']: i['img'] for i in feeds.parse(RSS, {'name': 'Test', 'lang': 'en'})}
    assert got == {'https://a.test/1': 'https://img.test/big.jpg', 'https://a.test/2': '',
                   'https://a.test/3': 'https://img.test/in-html.jpg',
                   'https://a.test/4': 'https://i.ytimg.test/vi/abc/hqdefault.jpg'}, got


def test_sniff_mixed_channels():
    assert feeds.sniff("Pakistan Başbakanı Şahbaz Şerif: Nobel Barış ödülü başkan Trump'a verilmeli", 'en') == 'tr'
    assert feeds.sniff("Türkiye's Erdoğan meets Putin in İstanbul", 'en') == 'en'   # names alone change nothing
    assert feeds.sniff('عاجل | مراسل الجزيرة: غارات إسرائيلية على جنوب لبنان', 'en') == 'ar'
    assert feeds.sniff('Israeli strikes hit southern Lebanon, says the army', 'ar') == 'en'
    assert feeds.sniff('Regeringen vil stramme reglerne for statsborgerskab', 'da') == 'da'


def test_telegram_posts_become_clean_headlines():
    page = ('<div data-post="kanal/1"><div class="tgme_widget_message_text js-message_text">'
            '⚡️ Lebanese sources An Israeli drone targets the town of Kfar Tebnit in southern Lebanon.<br/>'
            'More details to follow https://x.com/abc [Ak]</div><time datetime="2026-10-10T10:00:00+00:00"></time></div>'
            '<div data-post="kanal/2"><div class="tgme_widget_message_text js-message_text">'
            'Students were denied entry to Secondary School No. 9 in Jelilabad city for wearing the hijab, parents say.'
            '</div><time datetime="2026-10-10T10:05:00+00:00"></time></div>')
    a, b = feeds.parse_telegram(page, {'name': 'Kanal', 'lang': 'en'})
    assert a['title'] == 'An Israeli drone targets the town of Kfar Tebnit in southern Lebanon.', a['title']
    assert 'x.com' not in a['summary'] and '[Ak]' not in a['summary']
    assert b['title'].startswith('Students were denied entry to Secondary School No. 9 in Jelilabad'), b['title']
    assert feeds.clean('president ​Mahmoud ​Abbas') == 'president Mahmoud Abbas'
