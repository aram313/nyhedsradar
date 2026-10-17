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


# ---------------------------------------------------------------- teasers and commentary (2026-10-17, pro-plan 3.3, 3.4)
# A teaser is the outlet's own introduction. Some carry what is no introduction: a call to action at the end ('Følg
# udviklingen i krigen her.'), a link, or a picture's caption with its credit and the page's markup before the real
# teaser (Middle East Monitor: '… [Sabir Mazhar – Anadolu Agency] " data-large-file="…" /> Dozens of people …'). The
# app keeps a copy (cleanTeaser in app.js) – keep the two alike.
CTA = re.compile(
    r'\s*(?:(?:Følg|Se|Læs|Hør|Lyt)\b[^.!?]{0,80}?\b(?:her|live|nedenfor)\b\s*[.!:]?'
    r'|(?:Læs mere|Læs også|Læs hele artiklen|Se videoen|Se video|Se billederne|Read more|Continue reading|Click here'
    r'|Watch the video|Watch video|Watch live)\b[^.!?]{0,60}?[.!:…]?'
    r'|The post .{1,200}? appeared first on .{1,80}?\.?'
    r'|\[(?:…|\.\.\.|&hellip;)\])\s*$', re.I)
LEAD_TAG = re.compile(r'^(?:live|video|watch|se video|breaking)\s*[:|–-]\s*', re.I)
URL = re.compile(r'\s*(?:https?://|www\.)\S+', re.I)
# a picture's caption with its credit ('[Sabir Mazhar – Anadolu Agency]', '[Screengrab/AA]') and the markup after it
CREDIT = re.compile(r'^.{0,400}?\[[^\]]{0,80}(?:agency|\bAA\b|anadolu|getty|afp|reuters|\bAP\b|screengrab|photo|foto|epa|'
                    r'ritzau|scanpix|–)[^\]]{0,80}\]\s*"?(?:\s*[\w-]+="[^"]*")*\s*/?>?\s*', re.I)
MARKUP = re.compile(r'^[^<>]{0,300}?"?\s*(?:[\w-]+="[^"]*"\s*)+/?>\s*')
# a first sentence that describes a picture, not the news
CAPTION = re.compile(r'\b(?:is|are) seen\b|\bpictured\b|\bgives a speech\b|\bposes? for\b|\b(?:on|in) (?:January|February|'
                     r'March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b', re.I)
STEM_STOP = {'that', 'this', 'with', 'from', 'have', 'their', 'there', 'which', 'about', 'after', 'over', 'into', 'som',
             'ikke', 'efter', 'over', 'under', 'siger', 'blev', 'være', 'været', 'eller', 'også', 'deres', 'mens'}


def stems(text):
    return {w[:5] for w in re.findall(r'[^\W\d_]{4,}', (text or '').lower()) if w not in STEM_STOP}


def clean_teaser(text, title=''):
    """The teaser without what is no introduction: a call to action, a link, a picture's caption and its credit."""
    t = ' '.join(str(text or '').split())
    if not t:
        return ''
    m = CREDIT.match(t) or MARKUP.match(t)
    if m:
        t = t[m.end():].strip(' "')
    t = URL.sub('', LEAD_TAG.sub('', t)).strip()
    for _ in range(3):
        cut = CTA.sub('', t).strip()
        if cut == t:
            break
        t = cut
    if title:
        first = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)
        if CAPTION.search(first[0]) and len(stems(first[0]) & stems(title)) < 2:
            t = first[1] if len(first) > 1 else ''
    return t if len(t) >= 20 else ''


# commentary, not news: the outlets' own sections for opinion and analysis, and the headline's own label
COMMENT_PATH = re.compile(r'/(?:kommentar\w*|kommentatorer|debat\w*|opinions?|analyse\w*|analysis|leder\w*|blogs?|'
                          r'meninger|klummer?|comment(?:isfree)?|op-?ed)(?:/|$|\?)', re.I)
COMMENT_LABEL = re.compile(r'^(?:kommentar|analyse|analysis|leder|debat|klumme|opinion|comment|editorial|op-ed)\s*:', re.I)


def commentary(link, title=''):
    """True for an opinion or analysis piece: from the outlet's opinion section or marked so in its headline."""
    path = (link or '').split('://', 1)[-1]
    path = path[path.find('/'):] if '/' in path else ''
    t = (title or '').strip()
    return bool(COMMENT_PATH.search(path) or COMMENT_LABEL.match(t) or TAIL.search(t))
