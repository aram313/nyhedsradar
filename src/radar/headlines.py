"""Does a headline say the news, or withhold it? (the owner's rule of 2026-10-17, docs/hjerne/notes-owner-headlines.md)

A curiosity headline makes the reader curious instead of stating who did or said what: a question, 'Derfor …', 'Se …',
'Her er …', 'Sådan …', 'Det skal du vide', a cliff-hanger after a colon, a quotation with no speaker, an opinion piece
or a blog. The radar uses it to choose which outlet leads a story (a curiosity headline leads only when no outlet says
the news), and the editor's tools may use it to find the admitted stories that most need an informative headline.
Danish and English only: the other languages never lead a story an outlet in these two carries."""
import re

# opening words that withhold the news (Danish, then English)
OPENERS = re.compile(
    r'^(?:derfor|se\b|se:|her er|her får|sådan|det skal du vide|hvorfor|hvad|hvem|hvordan|hvornår|hvorfor|hvis du|'
    r'du skal|du kan|tjek|test dig|quiz|overblik|kommentar|analyse|leder|debat|klumme|interview|essay|'
    r'why|how|what|who|when|where|which|is|are|can|could|should|would|will|does|do|did|has|have|here\'?s|here is|'
    r'here are|this is|these are|that\'?s|watch|explainer|explained|analysis|opinion|comment|editorial|op-ed|inside|'
    r'the blogs|q&a|quiz|podcast|in pictures|in photos|photos|video)\b', re.I)
# a label of the column or the feeling before a colon: 'Klamt fund:', 'Analyse:', 'Breaking:'
LABEL = re.compile(r'^(?:\w+\s)?(?:fund|chok|afsløring|drama|kaos|skandale|overraskelse|vending|nyhed|besked|opråb|'
                   r'analyse|analysis|kommentar|comment|opinion|leder|debat|explainer|overblik|live|watch|video|blog)\s*:',
                   re.I)
# words that tease
TEASE = re.compile(r'(?:\bog det er ikke godt\b|\bdet er derfor\b|\bher er grunden\b|\bundrer sig\b|\bdu ikke vidste\b|'
                   r'\bsådan gør du\b|\bdet betyder det\b|\bhere\'?s why\b|\bhere\'?s what\b|\bwhat we know\b|'
                   r'\bwhat to know\b|\byou need to know\b|\bwhat it means\b|\band why\b|\bthis is why\b|\bthe reason\b|'
                   r'\bmight surprise\b|\bnever guess\b)', re.I)
# an opinion or analysis piece marked at the end: '… - analysis', '… - opinion'
TAIL = re.compile(r'\s[-–]\s(?:opinion|analysis|comment|editorial|op-ed|udtalelse|analyse|kommentar)\s*$', re.I)
QUOTE_OPEN = '»"“”\'‘’„«'


def curious(title):
    """True when the headline withholds the news instead of stating it."""
    t = (title or '').strip()
    if not t:
        return True
    if t.endswith('?') or re.search(r'\?\s*[»"“”\'’]?\s*$', t):
        return True
    if '?' in t and re.match(r'(?:kan|skal|vil|er|har|bliver|får|bør|må)\b', t, re.I):
        return True   # a question first, then the news: 'Kan Europa stole på USA? Mette Frederiksen tøver'
    first = t.split()[0]
    acronym = first.isupper() and len(first.strip('.,:')) >= 2   # 'WHO warns …', 'IS claims …'
    if (OPENERS.match(t) and not acronym) or LABEL.match(t) or TEASE.search(t) or TAIL.search(t):
        return True
    if t.endswith(':'):   # only who speaks ('Kamala Harris on Israel:'), nothing of what was said
        return True
    if t[0] in QUOTE_OPEN:
        # a quotation with no one named after it: '»Jeg er ikke så let at krænke«' (but '»…«: Trump kalder …' names him)
        if not re.search('[«»"“”’\'][,.]?\\s*(?:[:,–-]\\s*\\S+\\s+\\S+|(?:\\S+\\s+){0,4}(?:says|said|tells|told|warns|'
                         'siger|sagde|fortæller|advarer)\\b)', t[1:]):
            return True
    return False
