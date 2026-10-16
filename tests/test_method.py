"""The brain in the selection of news: the books' order of importance, with the powers as Hizb ut-Tahrir's newest
answers read them, and the actors a headline names."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from radar.method import Method  # noqa: E402

M = Method()


def tier(title, sec='world', trivia=False, **kw):
    return M.weigh({'title': title, 'sec': sec, **kw}, trivia)[0]


def test_the_powers_follow_the_newest_answers():
    assert M.leading == 'usa'
    assert M.powers == {'usa', 'storbritannien', 'frankrig', 'rusland', 'kina'}
    assert M.great == {'storbritannien', 'frankrig'}                     # weakened, but still great powers
    assert 'tyskland' in M.names and 'eu' in M.names                     # actors, not powers
    assert not {'tyskland', 'eu'} & M.powers


def test_the_tiers_follow_the_books_order():
    assert tier('US and China sign trade agreement in Geneva') == 1        # the leading state with another power
    assert tier('Trump and Putin meet for a summit in Alaska') == 1
    assert tier('Trump orders more troops to the Gulf') == 2               # an act aimed outward needs no other name
    assert tier('Trump announces trade deal with Japan') == 2
    assert tier('Britain imposes sanctions on Israeli settlers', sec='me') == 3
    assert tier('Military coup in Niger: president ousted') == 4
    assert tier('Hizbollah melder om nye kampe', sec='me') == 5            # the Middle East, nothing heavier
    assert tier('Ny lov: imamer skal prædike på dansk', sec='dk') == 6     # the campaign, even when it looks small
    assert tier('Muslimsk influencer i strid med TV 2', sec='dk') == 6
    assert tier('IMF approves new loan conditions') == 7
    assert tier('Leaked emails expose a lobbying campaign') == 8
    assert tier('Hormuz-strædet lukket for tankskibe') == 9
    assert tier('Drone attack hits a refinery') == 10
    assert tier('Trump fires his new spokeswoman') == 11                   # the leading state at home
    assert tier('Folketinget vedtager finansloven', sec='dk') == 12        # Danish, not placed internationally
    assert tier('Kongen fejrer jubilæum', sec='dk', trivia=True) == 13
    assert tier('Trump congratulates the new mayor of New York') == 13     # ceremony is weighed down
    assert tier('Putin congratulates Trump on the peace deal') == 1        # … but not a sign of change


def test_russia_china_germany_and_the_eu_are_no_great_powers_now():
    assert tier('Rusland og Iran indgår militæraftale') == 5               # a middle power: the major issues
    assert tier('China and Russia sign a partnership treaty') == 5         # no sign of change without the leading state
    assert tier('Tyskland sender tropper til Litauen') == 5
    assert tier('EU vedtager nye sanktioner mod Iran') == 5
    assert tier('Germany and France agree on a European army plan') == 3  # France still is one


def test_no_act_of_a_great_power_without_another_state_or_an_outward_act():
    assert tier('UK court rules on ITV broadcasting deal') == 11
    assert tier('US solicits oil from its strategic reserve') == 9           # oil, but no act aimed at a state
    assert tier('Frankrigs regering holder krisemøde forud for stor demodag') == 11   # Frank-krig is no war
    assert tier('French police accused over war-like injuries') == 11
    assert tier('Liberal Alliance vil have et nyt forlig med Trump-tilhængere', sec='dk') == 12
    assert tier('Mænd fra Aarhus-egnen lagde attentatplaner', sec='dk') == 12           # no change of ruler


def test_actors_are_named_without_false_friends():
    actors = lambda t: M.actors(M.text({'title': t}))
    assert actors('Houthis seize Bab el-Mandeb after a week-long offensive') == ['houthierne']
    assert actors('Mali junta expels French troops') == ['frankrig', 'mali']
    assert actors('Wildfire reaches Malibu') == []
    assert actors('Niger closes border') == ['niger'] and actors('Nigeria votes') == ['nigeria']
    assert actors('Talks in Islamabad') == ['pakistan']
    assert tier('Talks in Islamabad end without a deal') != 6               # Islamabad is not the campaign against Islam
    assert actors('الحوثيون يسيطرون على الساحل الغربي') == ['houthierne']
    assert actors('Trump meets Erdoğan') == ['tyrkiet', 'usa']


def test_the_wiki_lends_its_danish_names_as_whole_words():
    m = Method(wiki={'items': {'mali': {'kind': 'stat', 'name': 'Mali', 'aliases': ['Malis']},
                               'sekularisme': {'kind': 'begreb', 'name': 'Sekularisme', 'aliases': ['sekulær']},
                               'golfstaterne': {'kind': 'stat', 'name': 'Golfstaterne', 'aliases': ['Golfstaternes']}}})
    actors = lambda t: m.actors(m.text({'title': t}))
    assert actors('Golfstaternes ledere mødes') == ['golfstaterne']
    assert actors('Malibu brænder') == []
    assert actors('En sekulær stat') == []                                 # a concept is no actor


def test_naming_denmark_does_not_take_a_danish_story_abroad():
    m = Method(wiki={'items': {'danmark': {'kind': 'stat', 'name': 'Danmark', 'aliases': ['Danmark']}}})
    weigh = lambda t: m.weigh({'title': t, 'sec': 'dk'})[0]
    assert weigh('Attentatplaner i Danmark: to mænd dømt') == 12
    assert weigh('Iran stod bag attentatplaner i Danmark') == 4
    assert weigh('USA og Danmark indgår ny forsvarsaftale') == 2
