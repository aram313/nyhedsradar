"""The brain in the editor's input: what makes a story weigh, after the political books Khabar is built on and
Hizb ut-Tahrir's newest political answers. It is used ONLY to choose and order the news – the lede, the picks,
Dagens historie and the order of the recap's topics. The app shows no analysis: the editor's own text stays reality
(who did or said what, where, when), never a reading or judgement of its own, and never the movement's reading
presented as fact.

    section(top, extra_answers)   the brain section of the input, at most BUDGET characters:
                                  a. the books' order of weight – the radar's tiers (config/method.json when present)
                                     and the weight rules V of docs/hjerne/operating-card.md, compact;
                                  b. 'Den internationale tilstand ifølge Hizb ut-Tahrirs nyeste svar': the powers'
                                     current readings (public/viden/movement.json), one dated line each;
                                  c. the states, powers, groups and concepts the top stories name – alias matching with
                                     public/viden/begreber-index.json when present, else the movement's subjects – with
                                     their current reading, one dated line each, at most MAX_NAMED;
                                  d. the movement's three newest answers (title, date).
    tier_of(item)                 the radar's tier of a story (1 heaviest … 13 weighed down): the story's own 'tier',
                                  else radar.method's weighing when it is there, else None
    known_ids()                   every subject id the movement layer and the concept pages know

The movement's newest answer governs: a subject's current reading is the newest answer's (the layer and the concept
pages are built that way); older readings never appear here."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEN = ROOT / 'public' / 'viden'
METHOD = ROOT / 'config' / 'method.json'
BUDGET = 6000      # characters of the whole brain section
LINE = 260         # characters of one reading: its first sentence, cut at a clause only when longer
MAX_NAMED = 12     # subjects of the top stories shown with their reading
MAX_PAIRS = 3      # of those, relations between two subjects one story names together (at least two stories)
NEWEST = 3         # the movement's newest answers listed

LEADING = 'usa'
POWERS = ['usa', 'kina', 'rusland', 'storbritannien', 'frankrig', 'tyskland', 'eu']   # without config/method.json
TIERS = {   # the books' order of weight (docs/hjerne method §4); config/method.json words the tiers it defines
    1: 'sign of change in the international situation: two great powers in one act (agreement, alliance, war, summit, sanctions)',
    2: "the leading state's political acts (a new or changed plan weighs more than a changed means)",
    3: "another great power's acts, and the rivalry inside the Western camp",
    4: "who controls a state's ruler, army or economy: coup, succession, regime change, a ruler ousted or dead",
    5: 'the major issues, the Middle East first (a story that joins two issues weighs more)',
    6: 'the campaign against the belief and the concepts: curricula, "moderate Islam", laws on imams, mosques and dress, labels',
    7: 'instruments in use: the UN and international law, conferences, alliances, bases, sanctions, IMF/WTO terms',
    8: 'exposure of a means: a leak or a rival revealing it',
    9: 'colonial and economic interest read politically: oil, gas, pipelines, straits, ports, minerals',
    10: 'military acts',
    11: 'the rest',
    12: 'a Danish story that cannot be placed internationally',
    13: 'weighed down: ceremonial diplomacy without a change of policy, entertainment',
}
RULES = [
    "Weight is whether a development moves – a plan, a standing, the international situation – never noise or the number "
    "of outlets alone. A great power's political act is never dropped. The campaign against the belief weighs up even "
    "when it looks small.",
    "Danmark: Danish politics is never buried. Stories on Islam and Muslims, integration and immigration, and Denmark's "
    "foreign policy and its place in a great power's plan get two or three picks whenever they exist.",
]
PURPOSE = [
    "Use it only to weigh: the lede, the picks, Dagens historie (the recap's first topic with three lines or more – "
    "set by 'order') and the order of the recap's topics. The app shows no analysis. Your own text – lede, recap lines, "
    "summaries, headlines, quotes – stays reality only: who did or said what, where, when; never a reading or "
    "judgement of your own, and never the movement's reading presented as fact (not 'Iran, nu USA's satellit, …', not "
    "'det underordnede Saudi-Arabien'). The readings below are Hizb ut-Tahrir's, dated: they tell you what weighs, not "
    "what to write.",
]
NAMES = {   # how a movement subject is named when no concept page names it (the rest: the id, capitalised)
    'usa': 'USA', 'eu': 'EU', 'rsf': 'RSF', 'saudi-arabien': 'Saudi-Arabien', 'graekenland': 'Grækenland',
    'palaestinensisk-selvstyre': 'Det Palæstinensiske Selvstyre', 'houthierne': 'Houthierne', 'burkina-faso': 'Burkina Faso',
    'emiraterne': 'Emiraterne', 'hizbollah': 'Hizbollah', 'storbritannien': 'Storbritannien',
}
# the movement's subjects as Danish (and the machine's) headlines name them, when public/viden/begreber-index.json is
# not there yet: a name matches as a whole word (with a possessive s), a stem ending in * as the start of a word
FALLBACK_ALIASES = {
    'usa': ['USA', 'amerikansk*', 'Trump', 'Washington', 'Det Hvide Hus', 'Pentagon'],
    'rusland': ['Rusland', 'russisk*', 'Kreml', 'Putin', 'Moskva'],
    'kina': ['Kina', 'kinesisk*', 'Beijing', 'Xi Jinping'],
    'storbritannien': ['Storbritannien', 'britisk*', 'Starmer'],
    'frankrig': ['Frankrig', 'fransk*', 'Macron'],
    'tyskland': ['Tyskland', 'tysk*', 'Merz'],
    'eu': ['EU', 'Europa-Kommissionen', 'von der Leyen'],
    'israel': ['Israel', 'israelsk*', 'Netanyahu'],
    'iran': ['Iran', 'iransk*', 'Teheran', 'Khamenei'],
    'saudi-arabien': ['Saudi-Arabien', 'Saudiarabien', 'Saudi', 'saudisk*', 'saudiarabisk*', 'Riyadh'],
    'tyrkiet': ['Tyrkiet', 'tyrkisk*', 'Erdoğan', 'Erdogan', 'Ankara'],
    'egypten': ['Egypten', 'egyptisk*', 'Kairo'],
    'syrien': ['Syrien', 'syrisk*', 'Damaskus'],
    'libanon': ['Libanon', 'libanesisk*', 'Beirut'],
    'irak': ['Irak', 'irakisk*', 'Bagdad'],
    'yemen': ['Yemen', 'Jemen', 'yemenitisk*', 'Aden', 'Sanaa'],
    'houthierne': ['houthi*', 'Ansar Allah'],
    'hamas': ['Hamas'],
    'hizbollah': ['Hizbollah', 'Hezbollah'],
    'palaestinensisk-selvstyre': ['Selvstyret', 'Selvstyre', 'Abbas'],
    'qatar': ['Qatar', 'qatarsk*', 'Doha'],
    'emiraterne': ['Emiraterne', 'emiratisk*', 'UAE', 'Abu Dhabi'],
    'jordan': ['Jordan', 'jordansk*'],
    'pakistan': ['Pakistan', 'pakistansk*', 'Islamabad'],
    'indien': ['Indien', 'indisk*', 'Modi'],
    'afghanistan': ['Afghanistan', 'afghansk*', 'Taliban'],
    'ukraine': ['Ukraine', 'ukrainsk*', 'Zelenskyj', 'Kyiv'],
    'sudan': ['Sudan', 'sudanesisk*', 'Khartoum'],
    'rsf': ['RSF'],
    'libyen': ['Libyen', 'libysk*', 'Haftar'],
    'somalia': ['Somalia', 'somalisk*'],
    'danmark': ['Danmark'],
}
TITLE_PREFIX = re.compile(r'^(?:Svar på (?:politiske )?spørgsmål|Spørgsmål og svar|Svar på et spørgsmål)\s*:\s*', re.I)
SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-ZÆØÅ»"])')


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def d_slash(iso):
    """2026-06-12 → 12/6/2026, the movement's attribution date (anything else as it is)."""
    try:
        y, m, d = str(iso)[:10].split('-')
        return f'{int(d)}/{int(m)}/{y}'
    except ValueError:
        return str(iso)


def clean(s):
    return ' '.join(str(s or '').split())


# ------------------------------------------------------------------ the stories' tier

_method = []


def tier_of(it):
    """The radar's tier of a story; while the radar gives none, radar.method's weighing of its headline (the same
    rules), else None."""
    t = it.get('tier')
    if isinstance(t, int):
        return t
    if not _method:
        try:
            sys.path.insert(0, str(ROOT / 'src'))
            from radar.method import Method
            _method.append(Method())
        except Exception:  # noqa: BLE001 – no method module or no config/method.json: no tiers
            _method.append(None)
    if _method[0] is None:
        return None
    try:
        return _method[0].weigh(it)[0]
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ the movement layer and the concept pages

def layer():
    """The movement layer's current readings and answers (movement.json, else the app's slim index)."""
    m = load(VIDEN / 'movement.json', None) or load(VIDEN / 'movement-index.json', {})
    return {'current': m.get('current') or {}, 'answers': m.get('answers') or {}, 'readings': m.get('readings') or {}}


def static_answers():
    """The 321 answers of the static layer by number (the app's slim index, else the full layer)."""
    m = load(VIDEN / 'movement-index.json', None) or load(VIDEN / 'movement.json', {})
    return m.get('answers') or {}


def concepts():
    """(index, pages): public/viden/begreber-index.json and begreber.json, each {} when not built yet."""
    return (load(VIDEN / 'begreber-index.json', {}).get('items') or {}), (load(VIDEN / 'begreber.json', {}).get('items') or {})


def known_ids():
    lay, (index, pages) = layer(), concepts()
    return set(lay['current']) | set(lay['readings']) | set(index) | set(pages)


def name_of(sid, index=None, pages=None):
    for src in (index or {}, pages or {}):
        if (src.get(sid) or {}).get('name'):
            return src[sid]['name']
    if '--' in sid:
        return ' – '.join(name_of(p, index, pages) for p in sid.split('--'))
    return NAMES.get(sid) or '-'.join(w[:1].upper() + w[1:] for w in sid.split('-'))


def matcher(aliases, case_sensitive=None):
    """One pattern for a subject's names. A name matches as a whole word, with a possessive s ('Irans', "USA's"); a
    stem ending in * as the start of a word ('iransk*' finds 'iranske'). case_sensitive None: an acronym (USA, EU, RSF)
    matches as written, the rest in any case."""
    groups = {True: ([], []), False: ([], [])}
    for a in aliases or []:
        a = clean(a)
        if not a or a == '*':
            continue
        stem = a.endswith('*')
        word = a.rstrip('*')
        cs = case_sensitive if case_sensitive is not None else (word.isupper() and len(word) <= 5)
        groups[bool(cs)][1 if stem else 0].append(re.escape(word))
    rxs = []
    for cs, (whole, stems) in groups.items():
        parts = ([r'(?<!\w)(?:' + '|'.join(whole) + r")(?:s|'s|’s)?(?!\w)"] if whole else []) + \
                ([r'(?<!\w)(?:' + '|'.join(stems) + ')'] if stems else [])
        if parts:
            rxs.append(re.compile('|'.join(parts), 0 if cs else re.I))
    return rxs


def subjects(lay, index):
    """{id: (name, [patterns])} – the concept pages' names when the index is there, else the movement's subjects."""
    if index:   # the concept pages' names, and the headline forms above for the same subjects (iransk*, Kreml …)
        return {k: (v.get('name') or name_of(k),
                    matcher(list(v.get('aliases') or []) + [v.get('name') or ''], bool(v.get('case_sensitive')))
                    + matcher(FALLBACK_ALIASES.get(k) or []))
                for k, v in index.items()}
    out = {}
    for sid in lay['current']:
        if '--' in sid:
            continue
        name = name_of(sid)
        out[sid] = (name, matcher(FALLBACK_ALIASES.get(sid) or [name]))
    return out


FILED_KINDS = {'stilling': 0, 'tilstand': 1, 'forhold': 2, 'rolle': 3, 'plan': 4, 'fremgangsmåde': 5, 'motiv': 6}


def filed_reading(sid, filed):
    """(date, nr, text): the newest reading of a subject in the answers the editor filed after the static layer
    (answers.json on the digest branch) – a standing before the other kinds of one answer – else None."""
    rows = [(str(a.get('date') or ''), str(a.get('nr') or nr), r) for nr, a in (filed or {}).items() if isinstance(a, dict)
            for r in a.get('readings') or [] if isinstance(r, dict) and r.get('subject') == sid and r.get('text_da')]
    if not rows:
        return None
    date, nr, r = max(rows, key=lambda x: (x[0], -FILED_KINDS.get(x[2].get('kind'), 9)))
    return (date, nr, r['text_da']) if date else None


def newer(*readings):
    """The newest of some (date, nr, text) readings (None when there is none): the newest answer governs."""
    got = [r for r in readings if r]
    return max(got, key=lambda r: r[0]) if got else None


def reading_of(sid, lay, pages, filed=None):
    """(date, nr, text): the subject's current reading – the newest of an answer the editor filed since the static build
    and the concept page's lead (its first sentence carries its day; where it does not, the page's own row of that
    answer), else the layer's current reading."""
    p = pages.get(sid) or {}
    static = None
    if p.get('lead_da') and p.get('lead_date'):
        text = p['lead_da']
        first = (SENTENCE_END.split(clean(text)) or [''])[0]
        if d_slash(p['lead_date']) not in first:
            row = next((r for r in p.get('timeline') or [] if str(r.get('nr')) == str(p.get('lead_nr'))), None)
            text = row['text_da'] if row and row.get('text_da') else text
        static = (p['lead_date'], str(p.get('lead_nr') or ''), text)
    else:
        c = lay['current'].get(p.get('subject') or sid) or lay['current'].get(sid)
        if c and c.get('text_da') and c.get('date'):
            static = (c['date'], str(c.get('nr') or ''), c['text_da'])
    return newer(filed_reading(sid, filed), static)


def pair_reading(a, b, lay, pages, filed=None):
    """The relation between two subjects: the newest of a filed answer's reading of the pair, the concept pages' newest
    and the layer's current reading of the pair."""
    rows = [r for x, y in ((a, b), (b, a)) for r in (pages.get(x) or {}).get('relations') or []
            if r.get('with') == y and r.get('text_da') and r.get('date')]
    static = None
    if rows:
        r = max(rows, key=lambda r: r['date'])
        static = (r['date'], str(r.get('nr') or ''), r['text_da'])
    else:
        c = lay['current'].get('--'.join(sorted((a, b))))
        if c and c.get('text_da') and c.get('date'):
            static = (c['date'], str(c.get('nr') or ''), c['text_da'])
    return newer(filed_reading('--'.join(sorted((a, b))), filed), static)


def one_line(date, nr, text, limit=LINE):
    """A reading as one dated, attributed line: its first sentence (the newest, leading part), cut at a clause only
    when longer than the limit; 'Ifølge Hizb ut-Tahrirs svar af d/m/åååå: ' when the sentence does not name the
    movement, and the date and number up front when the sentence does not carry the date."""
    t = clean(text)
    m = SENTENCE_END.search(t)
    s = t[:m.start()] if m else t
    if len(s) > limit:
        cut = max(s.rfind('; ', 0, limit), s.rfind(' – ', 0, limit))
        if cut < 80:   # no clause long enough to stand alone: cut at a word
            cut = s.rfind(' ', 0, limit - 1)
            s = s[:cut].rstrip(',;:') + ' …'
        else:
            s = s[:cut]
    when = d_slash(date)
    if 'Hizb ut-Tahrir' not in s:
        s = f'Ifølge Hizb ut-Tahrirs svar af {when}: {s}'
    head = (f'nr {nr}' if when in s else f'{when}, nr {nr}') if nr else when
    return f'({head}): {s}'


def story_text(i):
    return ' · '.join(clean(x) for x in (i.get('title'), i.get('title_da'), i.get('title_tr')) if x)


def named(top, subs):
    """{subject: [stories]} for the subjects the stories' headlines name – by their names, and by the actors the
    radar found in the headline (a story's 'actors', when the radar gives them)."""
    out = {}
    for i in top:
        text = story_text(i)
        actors = set(i.get('actors') or [])
        for sid, (_, rxs) in subs.items():
            if sid in actors or any(rx.search(text) for rx in rxs):
                out.setdefault(sid, []).append(i)
    return out


def section(top, extra_answers=None, budget=BUDGET):
    """The brain section of the input (a list of lines, at most `budget` characters). top: the day's top stories;
    extra_answers: the movement's answers noted after the static layer (answers.json items on the digest branch)."""
    cfg = load(METHOD, {})
    leading = cfg.get('leading') or LEADING
    powers = list(cfg.get('powers') or POWERS)
    powers = [leading] + [p for p in powers if p != leading]
    lay = layer()
    index, pages = concepts()
    tiers = {t: ((cfg.get('tiers') or {}).get(str(t)) or {}).get('what') or TIERS[t] for t in TIERS}
    if (cfg.get('down') or {}).get('what'):
        tiers[13] = 'weighed down: ' + cfg['down']['what'].split(': ', 1)[-1]
    shown = [i for i in top if tier_of(i) is not None]
    head = ["## The brain – how today's news weighs (the books' order and Hizb ut-Tahrir's newest answers)", '', *PURPOSE, '',
            "### The books' order of weight (heaviest first)" + (" – each story's tier is in the lists below" if shown else ''), '']
    head += [f'{t} {tiers[t]}' for t in sorted(tiers)] + [''] + RULES + ['']
    # b. the powers, by the movement's newest answers
    state = ['### Den internationale tilstand ifølge Hizb ut-Tahrirs nyeste svar', '']
    filed = extra_answers or {}
    for p in powers:
        r = reading_of(p, lay, pages, filed)
        if r:
            state.append(f'- {name_of(p, index, pages)} {one_line(*r)}')
    state.append('')
    # c. what the top stories name: singles (not the powers above) by how many stories name them, then pairs
    subs = subjects(lay, index)
    hits = named(top, subs)
    rank = lambda sid: (-len(hits[sid]), min((tier_of(i) or 99) for i in hits[sid]),   # noqa: E731
                        -max((i.get('rank') or 0) for i in hits[sid]))
    singles = [s for s in sorted(hits, key=rank) if s not in powers and reading_of(s, lay, pages, filed)
               and (index.get(s) or {}).get('n_answers', 2) >= 2]   # a page of one answer says too little to weigh by
    together = {}
    for i in top:
        ids = sorted(s for s, rows in hits.items() if i in rows)
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                together[(ids[x], ids[y])] = together.get((ids[x], ids[y]), 0) + 1
    pairs = [(a, b, n) for (a, b), n in sorted(together.items(), key=lambda kv: -kv[1]) if n >= 2
             and pair_reading(a, b, lay, pages, filed)][:MAX_PAIRS]
    singles = singles[:MAX_NAMED - len(pairs)]
    named_lines = [f'- {name_of(s, index, pages)} · {len(hits[s])} {"story" if len(hits[s]) == 1 else "stories"} '
                   f'{one_line(*reading_of(s, lay, pages, filed))}' for s in singles]
    named_lines += [f'- {name_of(a, index, pages)} – {name_of(b, index, pages)} · {n} stories '
                    f'{one_line(*pair_reading(a, b, lay, pages, filed))}' for a, b, n in pairs]
    # d. the newest answers
    answers = {k: {'date': v.get('date'), 'title_da': v.get('title_da')} for k, v in lay['answers'].items()}
    answers.update({k: {'date': v.get('date'), 'title_da': v.get('title_da')} for k, v in (extra_answers or {}).items()})
    newest = sorted(((k, v) for k, v in answers.items() if v.get('date') and v.get('title_da')),
                    key=lambda kv: kv[1]['date'], reverse=True)[:NEWEST]
    tail = ["### Hizb ut-Tahrir's newest answers", ''] + [f"- {d_slash(v['date'])} · nr {k} · {TITLE_PREFIX.sub('', clean(v['title_da']))}"
                                                          for k, v in newest] + ['']

    def render(lines_c):
        mid = (["### Named in today's top stories – their current reading (Hizb ut-Tahrir's, dated)", ''] + lines_c + ['']
               if lines_c else [])
        return head + state + mid + tail
    while named_lines and len('\n'.join(render(named_lines))) > budget:
        named_lines.pop()            # the pairs and the least named go first
    out = render(named_lines)
    while len('\n'.join(out)) > budget and len(tail) > 3:
        tail.pop(-2)
        out = render(named_lines)
    return out
