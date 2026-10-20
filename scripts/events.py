"""Begivenheder: the pages the editor keeps for the day's great events, with fact boxes (the owner, 18/10: 'Hvad skal der
til for at vi kan få sådan nogle faktabokse og begivenheds sider. Lige nu sker der kæmpe store optøjer i Frankrig. Men
ser man på vores side føles det som en fodnote' – '/goal gør vores forside livlig og lav undersider hvor vi følger med i
begivenheder med faktabokse der rapportere store begivenheder … Lav moduler som vores redaktør kan udnytte').

events.json on the digest branch: {'updated', 'items': [event]}. An event, as an update writes it:
  id        lowercase letters, digits and hyphens ('frankrig-uroligheder-2026-10'); an update with the same id changes it,
            {"id": …, "remove": true} takes it away
  title     what is happening, in Danish (at most TITLE characters): 'Uroligheder i Frankrig'
  kicker    the small label over it: where or what (at most KICKER): 'Frankrig'
  status    'i gang' (under way), 'kommende' (ahead: a vote, a summit – with 'date') or 'afsluttet' (over)
  since     YYYY-MM-DD, the day its development began (i gang, afsluttet) – YYYY-MM when the stories give only the
            month (20/10: 'Kaos i Frankrig' counted 4 days from the weekend's riots, while its stories say the protests
            began a month before at the high schools); date: YYYY-MM-DD, the day it happens (kommende)
  dek       one factual line of what is happening and why it matters (at most DEK) – reality, never a forecast
  facts     at most FACTS boxes: {label, value, note, ids} – 'Demonstranter' · '550.000' · 'ifølge indenrigsministeriet';
            numbers of news value only (FACT_RULE; the owner, 19/10: 'faktatallene … har ikke nyhedsværdi, derfor skal
            der enten findes bedre faktatal ellers ingen skal vises. dette skal være en generel regel'): the tool never
            asks for a box because the stories carry numbers, and a page without one shows no 'Fakta';
            every number in a value stands in a story it cites (its headline, teaser or another outlet's headline) –
            the editor has no internet and never writes a number the news do not carry. A box may say more, so the app
            draws it (the owner, 18/10: 'Gør gerne tallene … visuel interessant med professionelle stilfulde widgets'):
            'of' – the whole the value is a share of ('7 af 10' is one already, as '68 %'): a ring; 'was' –
            {value, when, ids}, the number before ('400', 'fredag'): two bars and the change
  places    at most PLACES names of the places it happens in ('Paris', 'Lyon'), the main one first – looked up by the
            radar (src/radar/places.py) in the kicker's land; the page's map shows them as dots
  map       optional, how the map frames them (19/10, the owner: 'giv redaktørerne bedre værktøjer til at lave bedre kort'):
            {km: how many km it shows at least each way (MAP_KM), focus: the places it frames}; without it, or with
            "auto", the places' own spread (`frame`, as the app's evFrame)
  quotes    at most QUOTES statements: {who, text, ids}
  stories   at most STORIES story ids: its stories in Live
  topic     a recap topic name: its timeline (the development of the same name)
  article   at most PARAS paragraphs {text, ids}: the event told objectively – what happened, who, where, when, the
            numbers and what was said (the owner, 18/10: 'artikler til store begivenheder, hvor vi holder os objektive
            til selve begivenheden, ligesom vi får beskrevet i vores thaqafah … ikke meninger … men fakta, begivenhed og
            tal'); no judgement, no forecast; every number in it (but a date, a year or a clock time) stands in a story
            the paragraph cites
The file keeps an event EVENT_KEEP days after its last change (a 'kommende' one until its day has passed).
Stdlib only."""
import re
from datetime import date, datetime, timedelta

STATUSES = ('i gang', 'kommende', 'afsluttet')
TITLE, KICKER, DEK, LABEL, VALUE, NOTE = 60, 24, 220, 30, 18, 70
FACTS, PLACES, QUOTES, STORIES = 6, 12, 3, 20
FACT_RULE = ("only numbers of news value – the event's size as a whole: the dead, the injured, those arrested among the people it is about, the marchers, the displaced, the villages, homes or trees hit, the attacks counted (by the UN, a ministry, a rights group), the money, the votes or the seats –, never a detail of one incident ('2 såret i et angreb på en ambulance') or a side count ('8 anholdte bosættere' while the attacks are the news); when the material holds no such number the page has no boxes – none is better than a weak one (the owner, 19/10)")
MAP_KM = (10, 4000)              # the breadth an editor may give a page's map
MAP_MIN_KM, KM_DEG = 40, 111.32  # the automatic frame's least breadth each way – the app's evFrame is the same
PARAS, PARA = 6, 420     # the article: paragraphs, and characters a paragraph
MAX_EVENTS = 5          # events at a time: the great ones, not every story
EVENT_KEEP = 4          # days an event stays after its last change
ID = re.compile(r'^[a-z0-9][a-z0-9-]{2,80}$')
DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
MONTH = re.compile(r'^\d{4}-\d{2}$')
# what a page's stories say of when its development began ('began last month', 'weeks of protests', 'siden 2. oktober')
BEGAN = re.compile(r'\b(?:began|begun|started|erupted|broke out|since (?:early |mid-|late )?(?:january|february|march|april|may|'
                   r'june|july|august|september|october|november|december|\w+day|last)|weeks? of|months? of|for (?:weeks|months)|'
                   r'(?:second|third|fourth|fifth) week|begyndte|startede|brød ud|siden (?:\d|starten|begyndelsen|januar|februar|'
                   r'marts|april|maj|juni|juli|august|september|oktober|november|december)|i (?:flere )?uger|ugers)\b', re.I)
# a beginning with its time ('began last month', 'started in September', 'weeks of protests'): said first
WHEN = re.compile(r'\b(?:last (?:month|week|year)|ago|in (?:january|february|march|april|may|june|july|august|september|october|'
                  r'november|december)|on (?:\d|january|february|march|april|may|june|july|august|september|october|november|'
                  r'december)|weeks?|months?|sidste (?:måned|uge)|siden|for \d+|uger|måneder)\b', re.I)
NUMBER = re.compile(r'\d+(?:[.,\s]\d{3})*(?:[.,]\d+)?')


ARABIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')


def digits(text):
    """Every number a text carries, as its plain digits: '550.000', '550,000' and '550 000' are all '550000', '2,5'
    and '2.5' both '25' (Arabic-Indic digits read as their Western ones – a wire line's own text)."""
    return {re.sub(r'\D', '', m) for m in NUMBER.findall(str(text or '').translate(ARABIC_DIGITS)) if re.sub(r'\D', '', m)}


# The page's counts against its own development (18/10, the owner on the France page: 'hvad skaber denne kognitive
# dissonans' – the boxes said 150 police injured and over 2.000 arrested while 'Forløbet' under them gave the interior
# ministry's 997 and 2.397): a count is the number a text ties to an arrest, an injury or a death – the words after it to
# the next clause ('2.397 mennesker er anholdt'), else those before it ('arrest of 2397') – and whether police are
# counted; a page is behind when a line of its development counts more than every box of that kind
COUNT_KINDS = (('anholdt', re.compile(r'(?<!\w)(?:anhold\w*|arrest\w*|tilbagehold\w*|detain\w*|detention\w*)', re.I)),
               ('såret', re.compile(r'(?<!\w)(?:såre\w*|såret|kvæst\w*|injur\w*|wound\w*|hurt)', re.I)),
               ('dræbt', re.compile(r'(?<!\w)(?:dræbt\w*|omkom\w*|døde\b|dødsofre\w*|killed|dead|deaths?)', re.I)))
POLICE = re.compile(r'(?<!\w)(?:politi\w*|betjent\w*|police\w*|officer\w*|gendarm\w*|sikkerhedsfolk\w*|security)', re.I)
CLAUSE = re.compile(r'[,;:]|\s(?:og|samt|mens|and|while)\s', re.I)


def _kind(text):
    for kind, rx in COUNT_KINDS:
        if rx.search(text or ''):
            return kind
    return None


def counts_in(text):
    """[(kind, police, number)] for the counts a text gives."""
    text = str(text or '').translate(ARABIC_DIGITS)
    hits = list(NUMBER.finditer(text))
    out = []
    for k, m in enumerate(hits):
        end = hits[k + 1].start() if k + 1 < len(hits) else len(text)
        after = CLAUSE.split(text[m.end():end])[0]
        start = hits[k - 1].end() if k else 0
        before = CLAUSE.split(text[start:m.start()])[-1]
        part = after if _kind(after) else before
        kind = _kind(part)
        n = re.sub(r'\D', '', m.group())
        if kind and n:
            out.append((kind, bool(POLICE.search(after) or POLICE.search(before)), int(n)))
    return out


def box_counts(page):
    """The page's boxes as counts: {(kind, police): the highest value shown}."""
    got = {}
    for f in page.get('facts') or []:
        kind, n = _kind(f.get('label')), sorted(digits(f.get('value')), key=len)
        if kind and n:
            key = (kind, bool(POLICE.search(str(f.get('label') or ''))))
            got[key] = max(got.get(key, 0), int(n[-1]))
    return got


COUNT_LABEL = {('anholdt', False): 'anholdte', ('anholdt', True): 'anholdte politifolk', ('såret', False): 'sårede',
         ('såret', True): 'sårede politifolk', ('dræbt', False): 'dræbte', ('dræbt', True): 'dræbte politifolk'}


def article_behind(page, lines):
    """The counts of the page's development higher than every count of their kind its article tells (18/10, the owner:
    the boxes had the interior ministry's 2.397 while the article still told Lecornu's 1.200 and 'Bygger på' named the
    old sources): [(what, the article's highest, count, line)] – only for a kind the article tells at all."""
    told = {}
    for para in page.get('article') or []:
        for kind, police, n in counts_in(para.get('text') if isinstance(para, dict) else para):
            told[(kind, police)] = max(told.get((kind, police), 0), n)
    out = []
    for line in lines:
        for kind, police, n in counts_in(f"{line.get('who') or ''}: {line.get('text') or ''}"):
            have = told.get((kind, police))
            if have is not None and n > have and not any(x[2] == n and x[0] == COUNT_LABEL[(kind, police)] for x in out):
                out.append((COUNT_LABEL[(kind, police)], have, n, line))
    return out


def behind(page, lines):
    """The counts of the page's development (lines: [{id, who, text}]) higher than every box of their kind – or of a
    kind the page shows no box for at all, when it shows that kind otherwise: [(what, box value or None, count, line)]."""
    boxes, out = box_counts(page), []
    if not boxes:
        return out
    for line in lines:
        for kind, police, n in counts_in(f"{line.get('who') or ''}: {line.get('text') or ''}"):
            have = boxes.get((kind, police))
            if (have is not None and n > have) or (have is None and any(k == kind for k, _ in boxes)):
                if not any(x[2] == n and x[0] == COUNT_LABEL[(kind, police)] for x in out):
                    out.append((COUNT_LABEL[(kind, police)], have, n, line))
    return out


def story_text(it):
    """What a story carries: its headlines (the outlet's, the translations, the other outlets') and its teasers."""
    own = it.get('source') not in NO_CITE
    parts = [it.get(k) for k in ('title', 'title_tr', 'title_da', 'summary', 'summary_tr', 'summary_da', 'origTitle')] if own else []
    parts += [a.get(k) for a in it.get('also') or [] if isinstance(a, dict) and a.get('source') not in NO_CITE
              for k in ('title', 'title_tr')]
    # the sentences with counts the radar read in its outlets' articles (radar/reader.py, 18/10)
    parts += [x.get('t') for x in it.get('said') or [] if isinstance(x, dict) and x.get('s') not in NO_CITE]
    return ' · '.join(str(p) for p in parts if p)


MONTHS = 'januar|februar|marts|april|maj|juni|juli|august|september|oktober|november|december'
EN_MONTHS = 'january|february|march|april|may|june|july|august|september|october|november|december'
NOT_A_COUNT = re.compile(r'\b\d{1,2}\.\s*(?:' + MONTHS + r')\b|\b\d{1,2}/\d{1,2}\b|\b(?:19|20)\d{2}\b'
                         r'|\bkl\.\s*\d{1,2}[.:]\d{2}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:' + EN_MONTHS + r')\b'
                         r'|\b(?:' + EN_MONTHS + r')\s+\d{1,2}\b', re.I)


# the article holds to the event (the owner, 18/10: 'objektive til selve begivenheden … ikke meninger … men fakta'):
# no judgement of Khabar's own ('det er tydeligt', 'viser, at', 'bør', 'desværre') and no forecast of what will come
# ('vil falde', 'vil sprede sig') – a statement inside quotation marks is the speaker's
OPINION = re.compile(r'\b(det er (?:tydeligt|klart|åbenlyst|indlysende)|tydeligvis|åbenlyst|utvivlsomt|uden tvivl|'
                     r'efter alt at dømme|(?:det )?viser,? at|beviser|afslører,? at|understreger,? at|desværre|heldigvis|'
                     r'chokerende|skandaløs\w*|bør|burde|må nødvendigvis|kan konkluderes|med andre ord|reelt set|'
                     r'vil (?:falde|sprede sig|stige|fortsætte|eskalere|vokse|brede sig|kollapse|true|lykkes|mislykkes|føre))\b',
                     re.I)
# an article tells who gives each fact, never 'the media' in general (18/10: 'Ifølge danske medier … Medierne omtaler
# situationen som …' on the first page)
MEDIA_SAY = re.compile(r'\b(?:ifølge (?:danske |flere |udenlandske |internationale |franske )?medier(?:ne)?|'
                       r'(?:danske |flere |udenlandske |internationale |franske )?medier(?:ne)? (?:omtaler|beskriver|skriver|'
                       r'melder|rapporterer|kalder))\b', re.I)
HOW_MUCH = re.compile(r'(?:mere end|over|omkring|cirka|ca\.|næsten|op mod|mindst|under)\b', re.I)   # belongs in the value
OUTLET_SAY = re.compile(r'\b(?:skriver|skrev|omtaler|omtalte|melder|meldte|rapporterer|rapporterede|beretter|'
                        r'bragte|bringer)\b', re.I)
QUOTED = re.compile(r'»[^«»]*«|«[^«»]*»|"[^"]*"|“[^”]*”')


def opinion(paragraph):
    """A word of judgement or forecast in Khabar's own words of an article, or None."""
    hit = OPINION.search(QUOTED.sub(' ', paragraph or ''))
    return hit.group(0) if hit else None


def ungrounded(paragraph, stories):
    """The numbers of an article's paragraph that stand in none of the stories it cites (a date, a year and a clock
    time are no counts and are left out)."""
    have = set().union(*(digits(story_text(it)) for it in stories)) if stories else set()
    return sorted(digits(NOT_A_COUNT.sub(' ', paragraph)) - have)


def grounded(value, stories):
    """Whether every number in a fact's value stands in one of the stories it cites."""
    need = digits(value)
    have = set().union(*(digits(story_text(it)) for it in stories)) if stories else set()
    return bool(need) and need <= have


# the input's great events (18/10: the editor's first run with event pages passed France's riots by – it weighed only the
# most widely carried story, a decision, and the riots came as two stories): the widely carried stories grouped by what
# their headlines share, a group marked when its words tell an event – a people in the streets, a war, a strike, a
# coup, a disaster, a vote – from a decision or a statement
EVENT_KINDS = {
    'uro': r'urolighed|optøj|protest|demonstr|strejk|oprør|\briots?\b|unrest|uprising|walkout',   # 'strike' is also a raid
    'krig': r'\bkrig(?:en)?\b|invasion|offensiv|belejr|massakre|\bwar\b|offensive|siege|massacre',
    'kup': r'\bkup\b|kuppet|militærkup|\bcoup\b',
    'katastrofe': r'jordskælv|oversvøm|orkan|cyklon|tsunami|skovbrand|naturkatastrof|earthquake|flood|hurricane|cyclone|'
                  r'wildfire',
    'valg': r'folkeafstemning|\bvalget\b|valgkamp|(?:parlaments|præsident|folketings|kommunal|lokal|regions|midtvejs|del|'
            r'nyt?)valg(?:et)?\b|referendum|election',
}
EVENTISH = re.compile('|'.join(f'(?P<{k}>{v})' for k, v in EVENT_KINDS.items()), re.I)
STEM_STOP = set('''efter over under store stort flere mere siger sagde have blev bliver være skal ville også ikke første
mens hvor eller deres sine denne dette disse mellem uden igen mange hele andre anden andet nogle alle siden omkring
ifølge imod fordi kunne skulle gennem mandag tirsdag onsdag torsdag fredag lørdag søndag efterhånden blandt
after with from that this says said will have their about into amid against more than first what when where been were
they them would could should other some also just only over'''.split())


def stems(headline):
    """A headline's distinctive words, by their first five letters."""
    return {w[:5] for w in re.findall(r'[^\W\d_]{4,}', str(headline or '').lower()) if w not in STEM_STOP}


def eventish(it):
    """(the word that marks a story as an event, its kind), or (None, None): in its own headline or teaser, or in two
    other outlets' headlines – one outlet's 'will intensify war' under a story on a decision marks nothing."""
    own = ' · '.join(str(it.get(k) or '') for k in ('title', 'title_tr', 'title_da', 'summary', 'summary_tr',
                                                     'summary_da', 'origTitle'))
    hit = EVENTISH.search(own)
    if hit:
        return hit.group(0).lower(), hit.lastgroup
    hits = [h for h in (EVENTISH.search(' · '.join(str(a.get(k) or '') for k in ('title', 'title_tr')))
                        for a in it.get('also') or [] if isinstance(a, dict)) if h]
    return (hits[0].group(0).lower(), hits[0].lastgroup) if len(hits) >= 2 else (None, None)


def great_events(stories, head, most=6):
    """The widely carried stories (strongest first, commentary left out) as groups: two stories are one event when their
    headlines share two distinctive words, or one when both are marked as the same kind of event. Each group: {'items',
    'word' – the event's word or None, 'kind', 'outlets' – its most widely carried story's}; the marked groups first,
    the most widely carried first."""
    groups = []
    for it in sorted(stories, key=lambda i: -(i.get('outlets') or 1)):
        if it.get('kind') == 'kommentar':
            continue
        s, (word, kind) = stems(head(it)), eventish(it)
        for g in groups:
            shared = s & g['stems']
            if len(shared) >= 2 or (shared and kind and kind == g['kind']):
                g['items'].append(it)
                g['stems'] |= s
                if not g['word']:
                    g['word'], g['kind'] = word, kind
                break
        else:
            groups.append({'items': [it], 'stems': s, 'word': word, 'kind': kind, 'outlets': it.get('outlets') or 1})
    groups.sort(key=lambda g: (not g['word'], -g['outlets'], -len(g['items'])))
    return groups[:most]


def numbers_in(stories, most=14):
    """The counts the stories carry, as they are written ('550.000', '1.800'), each once – the material a fact box may
    use (a date, a year or a clock time is no count; a single digit is left out)."""
    out, seen = [], set()
    for it in stories:
        for m in NUMBER.findall(NOT_A_COUNT.sub(' ', story_text(it))):
            d = re.sub(r'\D', '', m)
            if len(d) >= 2 and d not in seen:
                seen.add(d)
                out.append(m.strip())
    return out[:most]


LATIN = re.compile(r'^[\x00-\u024f\u2000-\u206f\u20ac\s]*$')


def material(it, head, teaser, most=10, indent='        '):
    """A story's material for an event page: its headline's teaser and every other outlet's headline with the outlet
    (18/10: the first page the editor built had no fact box – the input gave one teaser, while the other outlets'
    headlines carried '1,200 arrested, 150 cops injured' and 'More than 1,800 arrested, Interior Minister says')."""
    out = []
    if teaser(it):
        out.append(f"{indent}Teaser: {text(teaser(it), 300)}")
    for a in sorted((x for x in it.get('also') or [] if isinstance(x, dict) and x.get('source') not in NO_CITE),
                    key=lambda x: x.get('source') in LAST)[:most]:
        t = a.get('title') if LATIN.match(str(a.get('title') or '')) else a.get('title_tr') or a.get('title')
        if t:
            out.append(f"{indent}{a.get('source') or '?'}: {text(t, 160)}")
    # what the outlets' articles say in numbers (radar/reader.py): who gives each count is in the sentence
    said = sorted((x for x in it.get('said') or [] if isinstance(x, dict) and x.get('t') and x.get('s') not in NO_CITE),
                  key=lambda x: x.get('s') in LAST)
    for x in said[:most + 2]:
        out.append(f"{indent}In {x.get('s') or '?'}'s article: {text(x['t'], 300)}")
    return out


def voice_distance(e):
    """The first quotation marks of distance in a page's line or article (voice.check_distance), or ''."""
    try:
        import voice
    except ImportError:
        return ''
    found = []
    for t in [e.get('dek'), *(a.get('text') for a in e.get('article') or [] if isinstance(a, dict))]:
        voice.check_distance(str(t or ''), '', found)
    return found[0].split(' – ')[0].lstrip(': ') if found else ''


def thin(items, find):
    """The pages under way that the tool would refuse now (events_file): fewer than three paragraphs while their
    stories hold six other outlets' headlines, a number no cited story carries, and the like – (page, what it lacks).
    Never 'too few boxes': a box is the editor's judgement of news value (FACT_RULE)."""
    out = []
    for e in items or []:
        if e.get('status') != 'i gang':
            continue
        told = [it for it in (find(x) for x in e.get('stories') or []) if it]
        heads = sum(len(it.get('also') or []) for it in told)
        lacks = []
        if heads >= 6 and len(e.get('article') or []) < 3:
            lacks.append(f"en hel artikel ({len(e.get('article') or [])} afsnit, {heads} overskrifter i dens historier)")
        loose = [f.get('value') for f in e.get('facts') or [] if isinstance(f, dict) and f.get('value')
                 and not grounded(f['value'], [it for it in (find(x) for x in f.get('ids') or []) if it])]
        loose += [n for a in e.get('article') or [] if isinstance(a, dict)
                  for n in ungrounded(str(a.get('text') or ''), [it for it in (find(x) for x in a.get('ids') or []) if it])]
        if loose:
            lacks.append(f"en kilde, vi bruger, for {', '.join(dict.fromkeys(map(str, loose)))}")
        if voice_distance(e):
            lacks.append('ord uden anførselstegn – Khabar tager ikke afstand (' + voice_distance(e) + ')')
        if any(MEDIA_SAY.search(str(a.get('text') or '')) for a in e.get('article') or [] if isinstance(a, dict)):
            lacks.append('kilder ved navn (artiklen siger »medierne«)')
        if sum(len(OUTLET_SAY.findall(str(a.get('text') or ''))) for a in e.get('article') or [] if isinstance(a, dict)) >= 3:
            lacks.append('en artikel om selve begivenheden (den gengiver, hvad medierne skriver)')
        if any(HOW_MUCH.match(str(f.get('note') or '')) for f in e.get('facts') or [] if isinstance(f, dict)):
            lacks.append('»over …« i selve tallet (noten begynder med det)')
        if any(digits(NOT_A_COUNT.sub(' ', str(f.get('note') or ''))) and not f.get('was')
               for f in e.get('facts') or [] if isinstance(f, dict)):
            lacks.append('det tidligere tal i grafikken (det står i en note)')
        if lacks:
            out.append((e, lacks))
    return out


def unused(items, find, least=3):
    """The pages under way whose stories' articles (radar/reader.py) carry counts the page does not show – at least
    `least` of them: (page, those counts as written). The check names such a page once for each set of counts."""
    out = []
    for e in items or []:
        if e.get('status') != 'i gang':
            continue
        told = [it for it in (find(x) for x in e.get('stories') or []) if it]
        shown = set().union(*(digits(t) for t in [*(f.get('value') for f in e.get('facts') or []),
                                                    *((f.get('was') or {}).get('value') for f in e.get('facts') or []),
                                                    *(a.get('text') for a in e.get('article') or [])] if t)) if e else set()
        new, seen = [], set()
        for it in told:
            for x in it.get('said') or []:
                for m in NUMBER.findall(NOT_A_COUNT.sub(' ', str(x.get('t') or ''))):
                    d = re.sub(r'\D', '', m)
                    if len(d) >= 2 and d not in shown and d not in seen:
                        seen.add(d)
                        new.append(m.strip())
        if len(new) >= least:
            out.append((e, new[:6]))
    return out


def great_lines(groups, head, teaser):
    """The input's section on the great events without a page."""
    if not groups:
        return []
    out = [f'## Great events without a page – {len(groups)} (many outlets, the last 36 hours): decide on each', '',
           'Stories that share their subject are one group. A group marked EVENT (a people in the streets, a war, a '
           'strike, a coup, a disaster, a vote) gets its page in this update under "events", built from these stories: '
           "their teasers, every other outlet's headline, the sentences with counts from their articles (\"In X's article\" – who gives each count is in the sentence) and the numbers they carry are below. A decision, a statement, "
           'a single attack or an analysis gets none.', '']
    for k, g in enumerate(groups):
        tag = f"EVENT – {g['kind']} ('{g['word']}')" if g['word'] else 'not marked – a page only when it is an event all the same'
        out.append(f"[{chr(65 + k)}] {tag} · {len(g['items'])} {'story' if len(g['items']) == 1 else 'stories'} · "
                   f"up to {g['outlets']} outlets")
        for it in g['items']:
            out.append(f"    [{it['id']}] {it.get('outlets') or 1} outlets · {it.get('source') or '?'} · {head(it)}")
            if g['word']:
                out += material(it, head, teaser, 10 if k < 2 else 3)
        if g['word']:
            nums = numbers_in(g['items'])
            out.append(f"    Numbers in its stories: {', '.join(nums) if nums else 'none – the page gets no fact box yet'}")
    return out + ['']


OWN = ('title', 'title_tr', 'title_da', 'summary', 'summary_tr', 'summary_da', 'origTitle')


def _marked(key, value, fallback):
    """The sources config/feeds.json marks so (their names and labels)."""
    import json
    from pathlib import Path
    try:
        feeds = json.loads((Path(__file__).resolve().parents[1] / 'config' / 'feeds.json').read_text(encoding='utf-8'))
        return {str(n) for f in feeds if isinstance(f, dict) and f.get(key) is value for n in (f.get('name'), f.get('label')) if n}
    except (OSError, ValueError):
        return set(fallback)


# a source of last resort ("last": true): a source only when no other outlet carries the fact (the owner, 18/10: 'Brug
# kun times of israel som kilde hvis der ikke er andre')
LAST = _marked('last', True, {'Times of Israel'})
# a source never cited on Khabar's pages ("cite": false – the owner, 18/10: 'The hindu skal også ud'): its headlines and
# its articles' sentences are no material, ground no number and are credited for nothing
NO_CITE = _marked('cite', False, {'The Hindu'})


def carriers(stories, number):
    """The outlets whose own headline or teaser carries a number (its digits): the story's own outlet, or another
    outlet of it by its headline."""
    out = []
    for it in stories:
        if number in digits(' · '.join(str(it.get(k) or '') for k in OWN)) and it.get('source') and it['source'] not in NO_CITE:
            out.append(str(it['source']))
        for a in it.get('also') or []:
            if isinstance(a, dict) and a.get('source') and a['source'] not in NO_CITE and \
                    number in digits(f"{a.get('title') or ''} · {a.get('title_tr') or ''}"):
                out.append(str(a['source']))
        for x in it.get('said') or []:   # a sentence of an outlet's article
            if isinstance(x, dict) and x.get('s') and x['s'] not in NO_CITE and number in digits(NOT_A_COUNT.sub(' ', str(x.get('t') or ''))):
                out.append(str(x['s']))
    return out


def sources(stories, said=None):
    """The outlets a box, a paragraph or a statement rests on, each once: the app names them under it, also when a
    story has left Live. With the text it says (a box's value, a paragraph), the outlets that carry its numbers (18/10:
    the first page credited BT for the arrests The Hindu and Times of Israel gave); else, or none found, the cited
    stories' own outlets."""
    got = []
    for n in sorted(digits(NOT_A_COUNT.sub(' ', said or ''))):
        by = carriers(stories, n)
        got += [o for o in by if o not in LAST] or by      # a source of last resort only for a number no other carries
    got = list(dict.fromkeys(got))
    own = list(dict.fromkeys(str(it.get('source')) for it in stories if it.get('source') and it['source'] not in NO_CITE))
    return got or [o for o in own if o not in LAST] or own


def last_named(said, stories):
    """(the source of last resort a text names, the other outlets that carry its numbers) when others do, else None."""
    named = next((o for o in LAST if o.lower() in str(said or '').lower()), None)
    if not named:
        return None
    others = [o for n in sorted(digits(NOT_A_COUNT.sub(' ', said or ''))) for o in carriers(stories, n) if o not in LAST]
    return (named, list(dict.fromkeys(others))) if others else None


def text(x, limit=None):
    t = re.sub(r'\s+', ' ', str(x or '')).strip()
    return t[:limit] if limit else t


def last_day(e):
    """The last day an event matters: a coming one its day, else the day of its last change."""
    try:
        if e.get('status') == 'kommende' and DAY.match(str(e.get('date') or '')):
            return date.fromisoformat(e['date'])
        return datetime.fromisoformat(str(e.get('at'))).date()
    except ValueError:
        return None


def events_file(entries, current, find, now, today, problems, voice=None, chosen=None):
    """events.json as this update leaves it. entries: the update's 'events' (a list; None keeps the file as it is);
    current: the file now; find: story id -> story (resolver); today: the Danish date; voice: the content rules
    (scripts/voice.py), the same as a headline's."""
    stamp = now.isoformat(timespec='seconds')
    items = {e['id']: e for e in (current or {}).get('items') or [] if isinstance(e, dict) and e.get('id')}
    if entries is not None and not isinstance(entries, list):
        problems.append('events: a list of event pages – or leave "events" out to keep them as they are')
        entries = []
    for k, x in enumerate(entries or [], 1):
        where = f'event {k}'
        if not isinstance(x, dict):
            problems.append(f'{where}: an object with id, title, kicker, status, dek and facts')
            continue
        ident = text(x.get('id'))
        if x.get('remove'):
            if ident not in items:
                problems.append(f'{where}: {ident!r} is no event page to remove')
            items.pop(ident, None)
            continue
        old = items.get(ident, {})
        e = {**old, **{k2: v for k2, v in x.items() if v is not None}}
        title, kicker, dek = text(e.get('title')), text(e.get('kicker')), text(e.get('dek'))
        where = f"event {k} ({title[:40] or ident or '?'})"
        if not ID.match(ident):
            problems.append(f'{where}: id – lowercase letters, digits and hyphens, e.g. frankrig-uroligheder-2026-10')
        if not title or len(title) > TITLE:
            problems.append(f'{where}: title – what is happening, in Danish (at most {TITLE} characters)')
        if not kicker or len(kicker) > KICKER:
            problems.append(f'{where}: kicker – the small label over the title: where or what (at most {KICKER} characters)')
        if not dek or len(dek) > DEK:
            problems.append(f'{where}: dek – one factual line of what is happening (at most {DEK} characters)')
        status = text(e.get('status'))
        if status not in STATUSES:
            problems.append(f"{where}: status – {' | '.join(STATUSES)}")
        since, day = text(e.get('since')), text(e.get('date'))
        if status == 'kommende':
            if not DAY.match(day):
                problems.append(f'{where}: date – YYYY-MM-DD, the day it happens')
            elif date.fromisoformat(day) < today:
                problems.append(f"{where}: {day} has passed – status 'afsluttet', or remove it")
        elif since and not (DAY.match(since) or MONTH.match(since)):
            problems.append(f'{where}: since – YYYY-MM-DD, the day its development began (YYYY-MM when only the month is known)')
        elif since and since > today.isoformat()[:len(since)]:
            problems.append(f'{where}: since {since} lies ahead – the day its development began')
        if voice:
            for field, val in (('title', title), ('kicker', kicker)):
                if val:
                    voice.check_headline(val, f'{where} {field}', problems)
            if dek:
                voice.check_voice(dek, f'{where} dek', problems)
                voice.check_distance(dek, f'{where} dek', problems)
                voice.check_reality(dek, f'{where} dek', problems)
                voice.check_forecast(dek, f'{where} dek', problems)

        def stories_of(ids, label):
            got = []
            for sid in ids if isinstance(ids, list) else []:
                it = find.get(str(sid))
                if not it:
                    problems.append(f'{where}: {label} – unknown story id {sid!r}')
                else:
                    got.append(it)
            return got
        facts = []
        raw = e.get('facts') or []
        if not isinstance(raw, list) or len(raw) > FACTS:
            problems.append(f'{where}: facts – a list of at most {FACTS} boxes')
            raw = raw[:FACTS] if isinstance(raw, list) else []
        for n, f in enumerate(raw, 1):
            if not isinstance(f, dict):
                problems.append(f'{where} fact {n}: an object with label, value, note and ids')
                continue
            label, value, note = text(f.get('label')), text(f.get('value')), text(f.get('note'))
            cited = stories_of(f.get('ids'), f'fact {n} ids')
            if not label or len(label) > LABEL:
                problems.append(f'{where} fact {n}: label – what is counted (at most {LABEL} characters)')
            if not value or len(value) > VALUE:
                problems.append(f'{where} fact {n}: value – the number, as the news give it (at most {VALUE} characters)')
            elif not cited:
                problems.append(f'{where} fact {n}: ids – the stories the number stands in')
            elif not grounded(value, cited):
                problems.append(f'{where} fact {n}: {value!r} stands in none of the stories it cites – a number from the '
                                'news only (their headline, teaser or another outlet\'s headline), or leave the box out')
            if len(note) > NOTE:
                problems.append(f'{where} fact {n}: note – who says it, at most {NOTE} characters')
            hit = last_named(f"{note} {value}", cited) if note else None
            if hit:
                problems.append(f"{where} fact {n}: {hit[0]} is a source only when no other outlet carries the number – "
                                f"{', '.join(hit[1])} carry it")
            if HOW_MUCH.match(note):
                problems.append(f"{where} fact {n}: the note {note!r} begins with how much – put it in the value ('over "
                                f"{value}'); the note says who gives the count")
            if digits(NOT_A_COUNT.sub(' ', note)) and not f.get('was'):
                problems.append(f"{where} fact {n}: the note {note!r} holds a number – a note says who gives the count; "
                                'an earlier count goes in "was": {"value": …, "when": …, "ids": […]} (the app draws both)')
            if voice and note:
                voice.check_voice(note, f'{where} fact {n} note', problems)
            box = {'label': label, 'value': value, **({'note': note} if note else {}),
                   'ids': [it['id'] for it in cited], 'src': sources(cited, value)}
            whole = text(f.get('of'))
            if whole:
                if not digits(whole):
                    problems.append(f'{where} fact {n}: of – the whole as a number (e.g. 10 for 7 of 10)')
                elif not grounded(whole, cited):
                    problems.append(f'{where} fact {n}: of {whole!r} stands in none of the stories it cites')
                else:
                    box['of'] = whole
            was = f.get('was')
            if was and isinstance(was, dict) and re.search(r'\bifølge\b|\baccording\b', str(was.get('when') or ''), re.I):
                problems.append(f"{where} fact {n}: was when {was.get('when')!r} – 'when' is a time ('fredag', 'i går'); an earlier "
                                "figure is the same giver's – one from another source is no growth: give it a box of its own "
                                "with who gives it")
            if was:
                if not isinstance(was, dict) or not text(was.get('value')):
                    problems.append(f'{where} fact {n}: was – {{value, when, ids}}: the number before')
                else:
                    before = stories_of(was.get('ids') or f.get('ids'), f'fact {n} was ids')
                    if not grounded(text(was.get('value')), before):
                        problems.append(f"{where} fact {n}: was {text(was.get('value'))!r} stands in none of the stories it cites")
                    else:
                        box['was'] = {'value': text(was.get('value'), VALUE), **({'when': text(was.get('when'), 24)} if was.get('when') else {}),
                                      'ids': [it['id'] for it in before]}
            facts.append(box)
        places = [text(p, 40) for p in (e.get('places') or []) if text(p)] if isinstance(e.get('places') or [], list) else []
        if len(places) > PLACES:
            problems.append(f'{where}: places – at most {PLACES}')
        frame_set = map_of(e.get('map'), places, where, problems)
        quotes = []
        for n, q in enumerate((e.get('quotes') or [])[:QUOTES] if isinstance(e.get('quotes') or [], list) else [], 1):
            if not isinstance(q, dict) or not text(q.get('who')) or not text(q.get('text')):
                problems.append(f'{where} quote {n}: an object with who, text and ids')
                continue
            cited = stories_of(q.get('ids'), f'quote {n} ids')
            if not cited:
                problems.append(f'{where} quote {n}: ids – the stories the statement comes from')
            if voice:
                voice.check_voice(text(q.get('text')), f'{where} quote {n}', problems)
            quotes.append({'who': text(q.get('who'), 60), 'text': text(q.get('text'), 300), 'ids': [it['id'] for it in cited],
                           'src': sources(cited)})
        told = [it for it in stories_of(e.get('stories') or [], 'stories') if not it.get('wire')]   # a wire line is no story
        told = list({it['id']: it for it in told}.values())[:STORIES]   # each story once
        stories = [it['id'] for it in told]
        # its picture: the outlet's own of its first story that has one (the card and the page set it large with the
        # title on a dark fade – the owner, 18/10), kept also when the story leaves Live
        first = next((it for it in told if str(it.get('pic') or '').startswith('http')), None)
        pic = (first or {}).get('pic') or old.get('pic', '')
        pf = (first or {}).get('pf') if first else old.get('pf')
        pl = (first or {}).get('pl') if first else old.get('pl')
        article = []
        raw = e.get('article') or []
        if not isinstance(raw, list) or len(raw) > PARAS:
            problems.append(f'{where}: article – a list of at most {PARAS} paragraphs')
            raw = raw[:PARAS] if isinstance(raw, list) else []
        for n, a in enumerate(raw, 1):
            para = text(a.get('text')) if isinstance(a, dict) else ''
            cited = stories_of(a.get('ids'), f'article {n} ids') if isinstance(a, dict) else []
            if not para or len(para) > PARA:
                problems.append(f'{where} article {n}: text – one paragraph of what happened (at most {PARA} characters)')
                continue
            if not cited:
                problems.append(f'{where} article {n}: ids – the stories the paragraph tells')
            else:
                loose = ungrounded(para, cited)
                if loose:
                    problems.append(f"{where} article {n}: {', '.join(loose)} stand in none of the stories it cites – the "
                                    'news\'s own numbers only')
            hit = last_named(para, cited)
            if hit:
                problems.append(f"{where} article {n}: {hit[0]} is a source only when no other outlet carries the fact – "
                                f"{', '.join(hit[1])} carry its numbers")
            meta = MEDIA_SAY.search(para)
            if meta:
                problems.append(f"{where} article {n}: '{meta.group(0)}' – name who gives each fact (the interior minister, "
                                'the police, the outlet by name), never the media in general')
            said = opinion(para)
            if said:
                problems.append(f"{where} article {n}: '{said}' is a judgement or a forecast – the article tells the event: "
                                'what happened, who, where, when, the numbers and what was said')
            if voice:
                voice.check_voice(para, f'{where} article {n}', problems)
                voice.check_distance(para, f'{where} article {n}', problems)
                voice.check_reality(para, f'{where} article {n}', problems)
                voice.check_forecast(para, f'{where} article {n}', problems)
            article.append({'text': para, 'ids': [it['id'] for it in cited], 'src': sources(cited, para)})
        # a page under way is told from its material (18/10: the first page had two paragraphs); its boxes are the
        # editor's judgement of news value – never demanded because the stories carry numbers (19/10, the owner: the
        # settler attacks' '8 anholdte bosættere' and '2 såret i angreb på ambulance' had none)
        if status == 'i gang' and told:
            heads = sum(len(it.get('also') or []) for it in told)
            if heads >= 6 and len(article) < 3:
                problems.append(f'{where}: the article has {len(article)} paragraph(s) while its stories hold {heads} other '
                                "outlets' headlines – tell what happened, where, the counts and what was said in three to "
                                'six paragraphs')
        wrote = sum(len(OUTLET_SAY.findall(a['text'])) for a in article)
        if wrote >= 3:
            problems.append(f"{where}: the article says {wrote} times what an outlet writes ('BT skriver', 'DR omtaler') – tell "
                            'the event itself, each fact with its first source (oplyser indenrigsministeren, siger politiet); '
                            'an outlet by name only where the news give no other')
        item = {'id': ident, 'title': title, 'kicker': kicker, 'status': status, 'dek': dek,
                **({'since': since} if since and status != 'kommende' else {}), **({'date': day} if status == 'kommende' else {}),
                **({'cal': text(e.get('cal'))} if e.get('cal') else {}), **({'topic': text(e.get('topic'), 80)} if e.get('topic') else {}),
                'facts': facts, 'places': places[:PLACES], **({'map': frame_set} if frame_set else {}), 'quotes': quotes, 'stories': stories,
                **({'article': article} if article else {}), **({'pic': pic} if pic else {}), **({'pf': pf} if pic and pf else {}), **({'pl': pl} if pic and pl else {}), 'at': stamp}
        items[ident] = item
    # the outlets under the pages this update leaves as they are follow their stories too (the news grow)
    changed = {text(x.get('id')) for x in entries or [] if isinstance(x, dict)}
    for ident, e in items.items():
        if ident in changed:
            continue
        first = next((it for it in (find.get(str(i)) for i in e.get('stories') or []) if it and str(it.get('pic') or '').startswith('http')), None)
        if first:
            e['pic'] = first['pic']
            for k in ('pf', 'pl'):
                if first.get(k):
                    e[k] = first[k]
                else:
                    e.pop(k, None)
        for part, said in [*((f, f.get('value')) for f in e.get('facts') or []), *((a, a.get('text')) for a in e.get('article') or [])]:
            cited = [it for it in (find.get(str(i)) for i in part.get('ids') or []) if it]
            if cited:
                part['src'] = sources(cited, said)
    # the owner's own picture of a page (19/10; chosen: {id: {pic, pf, pl}}, found among its stories' best) over the
    # first story's
    for ident, own in (chosen or {}).items():
        if ident in items and own.get('pic'):
            items[ident].update({k: v for k, v in own.items() if v})
    keep = [e for e in items.values() if (last_day(e) or today) >= today - timedelta(days=EVENT_KEEP)]
    live = [e for e in keep if e.get('status') != 'afsluttet']
    if len(live) > MAX_EVENTS:
        problems.append(f'events: {len(live)} pages under way or ahead – at most {MAX_EVENTS}: only the great events '
                        '(mark the others afsluttet, or remove them)')
    keep.sort(key=lambda e: ({'i gang': 0, 'kommende': 1, 'afsluttet': 2}.get(e.get('status'), 3), str(e.get('date') or '')))
    return {'updated': stamp, 'items': keep}


def map_of(given, places, where, problems):
    """An update's `map`, checked: {km, focus} or None (left out, "auto": the automatic frame)."""
    if given is None or (isinstance(given, str) and given.strip().casefold() in ('', 'auto')):
        return None
    if not isinstance(given, dict):
        problems.append(f'{where}: map – {{"km": how many km it shows at least each way, "focus": [places it frames]}}, '
                        'or "auto"')
        return None
    out = {}
    if given.get('km') not in (None, ''):
        try:
            km = float(given['km'])
        except (TypeError, ValueError):
            km = None
        if km is None or not MAP_KM[0] <= km <= MAP_KM[1]:
            problems.append(f'{where}: map km – how many km the map shows at least each way, {MAP_KM[0]}-{MAP_KM[1]}')
        else:
            out['km'] = round(km)
    focus = given.get('focus') or []
    if not isinstance(focus, list):
        problems.append(f'{where}: map focus – a list of the places it frames')
    else:
        named = {p.lower() for p in places}
        wrong = [text(f) for f in focus if text(f).lower() not in named]
        if wrong:
            problems.append(f"{where}: map focus {', '.join(wrong)} – only places the page names under 'places'")
        elif focus:
            out['focus'] = [text(f, 40) for f in focus][:PLACES]
    return out or None


def distance_km(a, b):
    """Kilometres between two (lat, lon), on the sphere."""
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(min(1.0, math.sqrt(h)))


def frame(e, places):
    """What a page's map shows, as the app frames it (evFrame): {dots: [(name, lat, lon)], missing: [names not found
    yet], across: km the map shows from side to side (its box is half again as wide as high), set: the editor's,
    far: [(name, km from the others' middle)]} – or None without places."""
    import math
    kick = str(e.get('kicker') or '').strip().lower()
    dots, missing = [], []
    for p in e.get('places') or []:
        hit = (places or {}).get(f'{str(p).strip().lower()}|{kick}')
        if not hit:
            if str(p).strip().lower() != kick:
                missing.append(p)
        elif hit[2] == 'city':
            dots.append((p, hit[0], hit[1]))
    if not dots:
        return {'dots': [], 'missing': missing, 'across': 0, 'set': bool(e.get('map')), 'far': []} if missing else None
    m = e.get('map') or {}
    focus = {str(x).strip().lower() for x in m.get('focus') or []}
    use = [d for d in dots if d[0].strip().lower() in focus] or dots
    s, n = min(d[1] for d in use), max(d[1] for d in use)
    w, o = min(d[2] for d in use), max(d[2] for d in use)
    k = max(0.1, math.cos(math.radians((s + n) / 2)))
    if m.get('km'):
        high = wide = float(m['km'])
    else:
        high = max((n - s) * 1.1 * KM_DEG, MAP_MIN_KM)
        wide = max((o - w) * 1.1 * KM_DEG * k, MAP_MIN_KM)
    mid = (sorted(d[1] for d in dots)[len(dots) // 2], sorted(d[2] for d in dots)[len(dots) // 2])
    off = [(d[0], distance_km(mid, d[1:])) for d in dots]
    typical = sorted(x[1] for x in off)[len(off) // 2] if len(off) >= 3 else 0
    far = [(name, round(km)) for name, km in off if len(off) >= 3 and km > 150 and km > 4 * max(typical, 10)]
    return {'dots': dots, 'missing': missing, 'across': round(max(wide, high * 1.5)), 'set': bool(m.get('km') or m.get('focus')), 'far': far}


def map_line(e, places):
    """The input's line on a page's map: what it shows and how the editor can frame it better."""
    f = frame(e, places)
    if f is None:
        return ''
    out = f"    map: {len(f['dots'])} {'dot' if len(f['dots']) == 1 else 'dots'}"
    if f['dots']:
        out += f" ({', '.join(d[0] for d in f['dots'][:8])}{' …' if len(f['dots']) > 8 else ''}) · it shows about {f['across']} km across"
        out += " (your map.km/focus)" if f['set'] else ' (automatic: the dots\' own spread)'
    if f['missing']:
        out += f" · not found yet: {', '.join(f['missing'])} – the radar looks a place up at its next pass; one still not found " \
               "is better named as the outlets name it, or left out"
    for name, km in f['far']:
        out += f" · {name} lies {km} km from the others – a wrong place of that name? name it more precisely or leave it out"
    return out


def began_in(stories, head, teaser, most=4):
    """What a page's stories say of when its development began: up to `most` short sentences ('The protests in France
    began last month at high schools …')."""
    found = []
    for it in stories:
        texts = [teaser(it) if teaser else '', it.get('summary') or '',
                 *[x.get('t') or '' for x in it.get('said') or [] if isinstance(x, dict)]]
        for text in texts:
            for part in re.split(r'(?<=[.!?])\s+', str(text or '')):
                m = BEGAN.search(part)
                if m and part.strip()[:160] not in [f[1] for f in found]:
                    found.append((0 if WHEN.search(part) else 1, part.strip()[:160]))
    return [t for _, t in sorted(found, key=lambda f: f[0])[:most]]


def named_here(e, stories):
    """The radar's other stories that name a page's places or its kicker (an outlet's article on the same development
    that the page does not list)."""
    names = [n for n in [*(e.get('places') or []), e.get('kicker') or ''] if len(n) >= 4]
    rx = re.compile(r'\b(?:' + '|'.join(re.escape(n) for n in names) + r')\b', re.I) if names else None
    return [it for it in stories or [] if rx and rx.search(' '.join(str(it.get(k) or '') for k in ('title', 'summary', 'title_tr')))]


def lines(current, now, find=None, head=None, teaser=None, development=None, places=None, pool=None):
    """The input's view of the event pages: what each says now, so an update changes only what the news moved – and,
    for a page under way, its stories' material (with find, head and teaser) and its development's lines (development:
    {topic name: [recap lines]}), with the counts there the boxes do not show yet."""
    items = (current or {}).get('items') or []
    out = [f'## Event pages (Begivenheder) – {len(items)} now', '']
    if find and any(e.get('status') == 'i gang' for e in items):
        out += ['Bring each page under way up to date from its stories\' material below: its boxes, the article, every '
                "city the stories and their articles name in 'places' (the page's map shows them), a statement.",
                f'Fact boxes: {FACT_RULE}. A weak box you find on a page you take away ("facts": [] leaves none); the earlier '
                'figure as "was" when a count of news value has grown; who gives each.', '']
    if not items:
        out.append('None yet. A great event (many outlets, a state or a people in motion, a vote ahead) gets a page.')
    if places is not None and any(e.get('places') for e in items):
        out += ["The maps: a page's places are its map's dots, the main one first, looked up in the kicker's land; the map "
                "frames their own spread. To frame it otherwise give the page \"map\": {\"km\": how many km it shows at "
                'least each way – a village or a town 10-40, a district or a small land 60-150, a region 300-800, a country '
                '800-1500 – \"focus\": [the places it frames]}; \"map\": \"auto\" gives it back. Each page says below what '
                'its map shows now.', '']
    for e in items:
        facts = '; '.join(f"{f.get('label')}: {f.get('value')}{' (' + f['note'] + ')' if f.get('note') else ''}"
                          for f in e.get('facts') or [])
        when = e.get('date') if e.get('status') == 'kommende' else e.get('since') or ''
        out.append(f"[{e['id']}] {e.get('status')} {when} · {e.get('kicker')} · {e.get('title')} – {e.get('dek')}")
        out.append(f"    facts: {facts or '–'} · places: {', '.join(e.get('places') or []) or '–'} · "
                   f"{len(e.get('stories') or [])} stories · topic: {e.get('topic') or '–'} · "
                   f"article: {len(e.get('article') or [])} paragraphs")
        if places is not None and map_line(e, places):
            out.append(map_line(e, places))
        if find and e.get('status') == 'i gang':
            own = [it for it in (find(x) for x in e.get('stories') or []) if it]
            began = began_in([*own, *named_here(e, [it for it in pool or [] if it not in own])], head, teaser)
            out.append(f"    Since {e.get('since') or '–'}: the day its development began, not its latest turn – "
                       + (f"its stories say: {' | '.join(began)}" if began else 'its stories say nothing of its beginning'))
            told = [it for it in (find(x) for x in (e.get('stories') or [])[:4]) if it]
            for it in told:
                out.append(f"    [{it['id']}] {it.get('outlets') or 1} outlets · {it.get('source') or '?'} · {head(it)}")
                out += material(it, head, teaser, 8)
            if told:
                nums = numbers_in(told)
                out.append(f"    Numbers in its stories (material – a box only for one of news value): {', '.join(nums) if nums else 'none'}")
        dev = (development or {}).get(e.get('topic') or '') or []
        if dev and e.get('status') == 'i gang':
            out.append(f"    Its development ('{e.get('topic')}', the page shows it under 'Forløbet') – a wire line [id] grounds a box "
                       "too: cite its id")
            out += [f"    [{x.get('id')}] {x.get('hm') or str(x.get('at') or '')[11:16]} · {x.get('who') + ': ' if x.get('who') else ''}{x.get('text')}"
                    for x in dev[:6]]
            for what, have, n, line in behind(e, dev):
                out.append(f"    BEHIND: its development counts {n} {what} ([{line.get('id')}]), the boxes "
                           f"{have if have is not None else 'none'} – update the box (the old value as \"was\" only when the "
                           "same giver gave it), or the page contradicts itself")
            for what, have, n, line in article_behind(e, dev):
                out.append(f"    BEHIND (article): its development counts {n} {what} ([{line.get('id')}]), the article tells at "
                           f"most {have} – tell the newest count in the article, with who gives it (cite the line's id); an "
                           "earlier count stays only as the earlier one")
    return out + ['']
