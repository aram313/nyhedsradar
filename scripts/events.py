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
  since     YYYY-MM-DD, the day it began (i gang, afsluttet); date: YYYY-MM-DD, the day it happens (kommende)
  dek       one factual line of what is happening and why it matters (at most DEK) – reality, never a forecast
  facts     at most FACTS boxes: {label, value, note, ids} – 'Demonstranter' · '550.000' · 'ifølge indenrigsministeriet';
            every number in a value stands in a story it cites (its headline, teaser or another outlet's headline) –
            the editor has no internet and never writes a number the news do not carry. A box may say more, so the app
            draws it (the owner, 18/10: 'Gør gerne tallene … visuel interessant med professionelle stilfulde widgets'):
            'of' – the whole the value is a share of ('7 af 10' is one already, as '68 %'): a ring; 'was' –
            {value, when, ids}, the number before ('400', 'fredag'): two bars and the change
  places    at most PLACES names of the places it happens in ('Paris', 'Lyon')
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
PARAS, PARA = 6, 420     # the article: paragraphs, and characters a paragraph
MAX_EVENTS = 5          # events at a time: the great ones, not every story
EVENT_KEEP = 4          # days an event stays after its last change
ID = re.compile(r'^[a-z0-9][a-z0-9-]{2,80}$')
DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
NUMBER = re.compile(r'\d+(?:[.,\s]\d{3})*(?:[.,]\d+)?')


def digits(text):
    """Every number a text carries, as its plain digits: '550.000', '550,000' and '550 000' are all '550000', '2,5'
    and '2.5' both '25'."""
    return {re.sub(r'\D', '', m) for m in NUMBER.findall(str(text or '')) if re.sub(r'\D', '', m)}


def story_text(it):
    """What a story carries: its headlines (the outlet's, the translations, the other outlets') and its teasers."""
    parts = [it.get(k) for k in ('title', 'title_tr', 'title_da', 'summary', 'summary_tr', 'summary_da', 'origTitle')]
    parts += [a.get(k) for a in it.get('also') or [] if isinstance(a, dict) for k in ('title', 'title_tr')]
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
    for a in (it.get('also') or [])[:most]:
        if not isinstance(a, dict):
            continue
        t = a.get('title') if LATIN.match(str(a.get('title') or '')) else a.get('title_tr') or a.get('title')
        if t:
            out.append(f"{indent}{a.get('source') or '?'}: {text(t, 160)}")
    return out


def thin(items, find):
    """The pages under way that the tool would refuse now (events_file): fewer than two boxes while their stories carry
    two counts or more, or fewer than three paragraphs while their stories hold six other outlets' headlines –
    (page, what it lacks)."""
    out = []
    for e in items or []:
        if e.get('status') != 'i gang':
            continue
        told = [it for it in (find(x) for x in e.get('stories') or []) if it]
        nums, heads = numbers_in(told), sum(len(it.get('also') or []) for it in told)
        lacks = []
        if len(e.get('facts') or []) < min(2, len(nums)):
            lacks.append(f"tal ({', '.join(nums[:4])} i dens historier)")
        if heads >= 6 and len(e.get('article') or []) < 3:
            lacks.append(f"en hel artikel ({len(e.get('article') or [])} afsnit, {heads} overskrifter i dens historier)")
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


def great_lines(groups, head, teaser):
    """The input's section on the great events without a page."""
    if not groups:
        return []
    out = [f'## Great events without a page – {len(groups)} (many outlets, the last 36 hours): decide on each', '',
           'Stories that share their subject are one group. A group marked EVENT (a people in the streets, a war, a '
           'strike, a coup, a disaster, a vote) gets its page in this update under "events", built from these stories: '
           "their teasers, every other outlet's headline and the numbers they carry are below. A decision, a statement, "
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


def carriers(stories, number):
    """The outlets whose own headline or teaser carries a number (its digits): the story's own outlet, or another
    outlet of it by its headline."""
    out = []
    for it in stories:
        if number in digits(' · '.join(str(it.get(k) or '') for k in OWN)) and it.get('source'):
            out.append(str(it['source']))
        for a in it.get('also') or []:
            if isinstance(a, dict) and a.get('source') and number in digits(f"{a.get('title') or ''} · {a.get('title_tr') or ''}"):
                out.append(str(a['source']))
    return out


def sources(stories, said=None):
    """The outlets a box, a paragraph or a statement rests on, each once: the app names them under it, also when a
    story has left Live. With the text it says (a box's value, a paragraph), the outlets that carry its numbers (18/10:
    the first page credited BT for the arrests The Hindu and Times of Israel gave); else, or none found, the cited
    stories' own outlets."""
    got = [o for n in sorted(digits(NOT_A_COUNT.sub(' ', said or ''))) for o in carriers(stories, n)]
    return list(dict.fromkeys(got)) or list(dict.fromkeys(str(it.get('source')) for it in stories if it.get('source')))


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


def events_file(entries, current, find, now, today, problems, voice=None):
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
        elif since and not DAY.match(since):
            problems.append(f'{where}: since – YYYY-MM-DD, the day it began')
        if voice:
            for field, val in (('title', title), ('kicker', kicker)):
                if val:
                    voice.check_headline(val, f'{where} {field}', problems)
            if dek:
                voice.check_voice(dek, f'{where} dek', problems)
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
        told = stories_of(e.get('stories') or [], 'stories')[:STORIES]
        stories = [it['id'] for it in told]
        # its picture: the outlet's own of its first story that has one (the card and the page set it large with the
        # title on a dark fade – the owner, 18/10), kept also when the story leaves Live
        first = next((it for it in told if str(it.get('pic') or '').startswith('http')), None)
        pic = (first or {}).get('pic') or old.get('pic', '')
        pf = (first or {}).get('pf') if first else old.get('pf')
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
                voice.check_reality(para, f'{where} article {n}', problems)
                voice.check_forecast(para, f'{where} article {n}', problems)
            article.append({'text': para, 'ids': [it['id'] for it in cited], 'src': sources(cited, para)})
        # a page under way holds the counts its stories carry, and is told from its material (18/10: the first page
        # had two paragraphs and no box while its stories' headlines carried the arrests and the injured)
        if status == 'i gang' and told:
            nums = numbers_in(told)
            if len(facts) < min(2, len(nums)):
                problems.append(f"{where}: its stories carry {', '.join(nums[:6])} – give each count its box (label, the "
                                'number, who gives it), the earlier figure as "was" when it has grown')
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
                'facts': facts, 'places': places[:PLACES], 'quotes': quotes, 'stories': stories,
                **({'article': article} if article else {}), **({'pic': pic} if pic else {}), **({'pf': pf} if pic and pf else {}), 'at': stamp}
        items[ident] = item
    # the outlets under the pages this update leaves as they are follow their stories too (the news grow)
    changed = {text(x.get('id')) for x in entries or [] if isinstance(x, dict)}
    for ident, e in items.items():
        if ident in changed:
            continue
        for part, said in [*((f, f.get('value')) for f in e.get('facts') or []), *((a, a.get('text')) for a in e.get('article') or [])]:
            cited = [it for it in (find.get(str(i)) for i in part.get('ids') or []) if it]
            if cited:
                part['src'] = sources(cited, said)
    keep = [e for e in items.values() if (last_day(e) or today) >= today - timedelta(days=EVENT_KEEP)]
    live = [e for e in keep if e.get('status') != 'afsluttet']
    if len(live) > MAX_EVENTS:
        problems.append(f'events: {len(live)} pages under way or ahead – at most {MAX_EVENTS}: only the great events '
                        '(mark the others afsluttet, or remove them)')
    keep.sort(key=lambda e: ({'i gang': 0, 'kommende': 1, 'afsluttet': 2}.get(e.get('status'), 3), str(e.get('date') or '')))
    return {'updated': stamp, 'items': keep}


def lines(current, now, find=None, head=None, teaser=None):
    """The input's view of the event pages: what each says now, so an update changes only what the news moved – and,
    for a page under way, its stories' material (with find, head and teaser)."""
    items = (current or {}).get('items') or []
    out = [f'## Event pages (Begivenheder) – {len(items)} now', '']
    if find and any(e.get('status') == 'i gang' for e in items):
        out += ['Bring each page under way up to date from its stories\' material below: every count they carry in a box '
                '(the earlier figure as "was" when it has grown), who gives each, the places named, a statement, and '
                'the article told from all of it.', '']
    if not items:
        out.append('None yet. A great event (many outlets, a state or a people in motion, a vote ahead) gets a page.')
    for e in items:
        facts = '; '.join(f"{f.get('label')}: {f.get('value')}{' (' + f['note'] + ')' if f.get('note') else ''}"
                          for f in e.get('facts') or [])
        when = e.get('date') if e.get('status') == 'kommende' else e.get('since') or ''
        out.append(f"[{e['id']}] {e.get('status')} {when} · {e.get('kicker')} · {e.get('title')} – {e.get('dek')}")
        out.append(f"    facts: {facts or '–'} · places: {', '.join(e.get('places') or []) or '–'} · "
                   f"{len(e.get('stories') or [])} stories · topic: {e.get('topic') or '–'} · "
                   f"article: {len(e.get('article') or [])} paragraphs")
        if find and e.get('status') == 'i gang':
            told = [it for it in (find(x) for x in (e.get('stories') or [])[:4]) if it]
            for it in told:
                out.append(f"    [{it['id']}] {it.get('outlets') or 1} outlets · {it.get('source') or '?'} · {head(it)}")
                out += material(it, head, teaser, 8)
            if told:
                nums = numbers_in(told)
                out.append(f"    Numbers in its stories: {', '.join(nums) if nums else 'none'}")
    return out + ['']
