"""Build the movement layer (public/viden/movement.json): Hizb ut-Tahrir's political answers 2003-2026 as Khabar
read them – one entry per answer (a Danish title, question and short note, never the answer's text), the readings
of each state, power and relation over time, the current reading of each, the history of each issue, and the
answers' expectations. Everything in the layer is the movement's reading: attributed ('Ifølge Hizb ut-Tahrirs svar
af d/m/åååå …'), never a confirmed fact and never Khabar's own judgement.

Input (local, not in the repo): .cache/movement/extract/*.json (one file per answer, read by the extract agents),
.cache/movement/synth/<group>.json (8 regional syntheses: timelines, current, issues, expectations); in the repo:
docs/hjerne/qa-index.json (the English edition's numbers of the 2026 answers) and, for the check's protected names,
docs/hjerne/knowledge-v0.json (the check runs without it, with its own list of non-ruling persons and parties only).

Answer numbers: the app and the radar key an answer by the number in its CMO URL, and the English edition's number
wins when the answer has one. ALIASES maps the other edition's number (or a copy) to it; an Arabic-only answer
whose number is also an English answer's number is keyed 'ar-<nr>' (the two are different answers).

    py scripts/build_movement.py            -> public/viden/movement.json and the app's slim public/viden/movement-index.json

The index holds what the app's lists need at once: per answer its date, Danish title and question, issues, states and
powers; per subject only its current reading. The app loads the full layer only when a timeline, a reader or an
answer's readings are opened. The wiki of concepts (scripts/build_begreber.py → public/viden/begreber.json) is built
from this layer.
"""
import glob
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / '.cache' / 'movement'
OUT = ROOT / 'public' / 'viden' / 'movement.json'
INDEX = ROOT / 'public' / 'viden' / 'movement-index.json'
QA = ROOT / 'docs' / 'hjerne' / 'qa-index.json'
SEED = ROOT / 'docs' / 'hjerne' / 'knowledge-v0.json'

# Khabar's voice (the Khabar 2 rules, kept here since its editor and model are not on this branch): no praise of or call
# to violence, no verdict on peoples, religions or anyone's belief, Israel by its name ('den jødiske entitet' only inside
# a quotation), no forgeries or conspiracy myths (cards H4, H5, D10)
VOICE_BANNED = [
    (re.compile(r'\b(heltemod\w*|martyr\w*|nusra\w*|omstyrt\w*|hærindgriben|væbnet kamp|væbnede kamp|til våben)\b', re.I),
     "no praise of violence and no call to violence, a coup or an army's intervention in Khabar's own voice (H4)"),
    (re.compile(r'\b(jøderne|de kristne|de vantro|kuffar|kafir\w*|kufr|riddah|nifaq|danskerne er)\b', re.I),
     "judge states, rulers, policies and ideas – never peoples, religions or anyone's belief (H5, D10)"),
    (re.compile(r'(?<![«»"„“])\b(den jødiske entitet|den zionistiske entitet)\b', re.I),
     "Khabar says 'Israel'; 'den jødiske entitet' only inside a quotation with who said it (H5)"),
    (re.compile(r'\b(zions vise|protokol\w* fra zion|franklin-citat\w*|IS (blev )?skabt af)\b', re.I),
     'no forgeries or conspiracy myths (H5)'),
]
# a claim that someone serves, sponsors or stages: needs deeds, and never about a protected person (card H1, H3)
AGENT_WORDS = re.compile(r'\b(agent\w*|marionet\w*|lakaj\w*|bagmand\w*|står bag|stod bag|iscenesat\w*|iscenesæt\w*|'
                         r'på ordre fra|på vegne af|tjener \w+ interesser|går \w+ ærinde|aftalt spil|patron\w*|hoflærd\w*|'
                         r'del af kampagnen|forræder\w*|vasal\w*|proxy\w*|stedfortræder\w*|styret af|falsk flag)', re.I)
# never said to serve, sponsor or stage anything (card H3): every identifiable person who is not a sitting ruler, all
# Danish persons and organisations, parties, mosques, media and scholars (the seed model's actor kinds)
PROTECTED = ('person', 'privatperson', 'dansk offentlig person', 'dansk organisation', 'medie', 'lærd', 'moské', 'parti')


def check_voice(text, where, problems):
    for rx, why in VOICE_BANNED:
        hit = rx.search(text or '')
        if hit:
            problems.append(f"{where}: '{hit.group(0)}' – {why}")


# the same answer in two editions (same date ±3 days and the same subject) or a copy: the other number → the one kept
ALIASES = {
    '111779': '30420',   # Yemen 27/9/2026: Arabic edition; the English edition is 30420
    '72992': '552',      # Kirgisistan 16/4/2010: Arabic copy of the English 552
    '3642': '366',       # Centralasien: Arabic 19/9/2009, English edition 366 (dated 20/10/2010)
    '72990': '2450',     # Sri Lanka 23/5/2009: two Arabic uploads; 2450 is the original number
}
ATTRIB = [   # the movement's readings name the movement: 'Ifølge Hizb ut-Tahrirs svar af …' (card M1)
    (re.compile(r'^Ifølge svaret af '), 'Ifølge Hizb ut-Tahrirs svar af '),
    (re.compile(r'^Ifølge svarene '), 'Ifølge Hizb ut-Tahrirs svar '),
    (re.compile(r'^Ifølge (?:bevægelsens|Hizb ut-Tahrirs) svar(ene)? '), 'Ifølge Hizb ut-Tahrirs svar '),
    (re.compile(r'^Ifølge en række svar '), 'Ifølge en række af Hizb ut-Tahrirs svar '),
    (re.compile(r'^Ifølge (\w+) svar '), r'Ifølge \1 af Hizb ut-Tahrirs svar '),
    (re.compile(r'^Bevægelsens svar '), 'Hizb ut-Tahrirs svar '),
]
OPENINGS = [   # a text that opens on the answers without naming the movement
    (re.compile(r'^Fra (\d{4}) til (\d{4}) læser (?:svarene|bevægelsens svar) '), r'Fra \1 til \2 læser Hizb ut-Tahrirs svar '),
    (re.compile(r'^Svarene (?:af )?'), 'Hizb ut-Tahrirs svar '),
    (re.compile(r'^Svaret '), 'Hizb ut-Tahrirs svar '),
    (re.compile(r'^Bevægelsen '), 'Hizb ut-Tahrir '),
]
# where the groups' 'current' readings of a subject are facets of different arenas, not rival readings: the group whose
# reading is the whole one. USA: the global reading (the answer of 14/1/2026 on its security strategy); the regional
# groups' newer readings of USA (Levant, Palestine, the subcontinent) are its plans in one arena and stay in 'readings'
CURRENT_FROM = {'usa': 'magterne'}
# a standing's class (the app compares classes, never the free words): the answers alternate 'underordnet' and
# 'satellit' for one bound standing; a break, an unclear or independent standing, a leading power, a remnant of an old
# patron's hold, a looser leaning and a protected or marginal place are standings of their own
STAND_CLASSES = (
    ('brud', re.compile(r'→\s*brud|\bbrud\b')),
    ('uklar', re.compile(r'uklar|ikke underordnet|skifte|vender tilbage')),
    ('uafhængig', re.compile(r'uafhæng')),
    ('førende', re.compile(r'førende')),
    ('rest', re.compile(r'\brest\b')),
    ('orienteret', re.compile(r'orienteret')),
    ('beskyttet', re.compile(r'beskyttet')),
    ('marginal', re.compile(r'marginal')),
    ('bundet', re.compile(r'underordnet|satellit|\bbane\b')),
)
# a reading of the past, dated by the answer that recalls it ('svaret af 2/9/2025 (historisk) var kongen …'): never a change
HISTORICAL = re.compile(r'\(historisk\)')
MONTHS = {m: i + 1 for i, m in enumerate(('januar', 'februar', 'marts', 'april', 'maj', 'juni', 'juli', 'august', 'september',
                                           'oktober', 'november', 'december'))}
SPAN_DATE = ('latest', 'latest_date', 'last_date', 'date_last', 'until')
SPAN_NR = ('latest_nr', 'last_nr')
WORD = re.compile(r'\w{4,}', re.U)


def d_slash(iso):
    y, m, d = iso[:10].split('-')
    return f'{int(d)}/{int(m)}/{y}'


def day(iso):
    return date.fromisoformat(iso[:10])


class Numbers:
    """Every number the extracts and syntheses use → the one number of that answer."""

    def __init__(self, extracts):
        en = {x['nr'] for x in extracts if '/en/' in x['url']}
        self.by_key = {}
        self.dates = {}
        self.subjects = {}
        for x in extracts:
            nr = ALIASES.get(x['nr'], x['nr'])
            if '/en/' not in x['url'] and nr == x['nr'] and nr in en:
                nr = f'ar-{nr}'
            self.by_key[x['key']] = nr
            self.dates.setdefault(nr, []).append(x['date'])
            self.subjects.setdefault(nr, set()).update(x['states'] + x['issues'] + x['powers'])
        self.collide = {n[3:] for n in self.dates if n.startswith('ar-')}

    def of(self, nr, when=None, subject=None):
        nr = ALIASES.get(str(nr), str(nr))
        if nr not in self.collide:
            return nr
        ar = f'ar-{nr}'
        if when:
            near = lambda n: any(abs((day(when) - day(d)).days) <= 3 for d in self.dates[n])   # noqa: E731
            if near(ar) and not near(nr):
                return ar
            if near(nr):
                return nr
        if subject:
            parts = set(subject.split('--'))
            if parts & self.subjects[ar] and not parts & self.subjects[nr]:
                return ar
        return nr

    def text(self, s):
        """Fix the numbers cited inside a text ('nr 111779' → 'nr 30420')."""
        return re.sub(r'(?:(?<=nr )|(?<=nr\. )|(?<=nr\.))(\d{3,6})\b|\b(\d{5,6})\b',
                      lambda m: ALIASES.get(m.group(1) or m.group(2), m.group(1) or m.group(2)), s or '')


# Khabar's own words about the corpus are no reading of the movement's and stay out of the reader texts (2026-10-17
# review): 'Ingen nyere svar …', 'Kuwait nævnes ikke særskilt', '(svarets påstand … er ikke gengivet)' – what an answer
# does not say is simply not said
META = [
    (re.compile(r'\s*\((?:svarets påstand|svarets påstande)[^()]*?er ikke gengivet(?:; gerningsbelæg mangler)?\)'), ''),
    (re.compile(r';\s*svarets påstand[^;.]*?er ikke gengivet(?:; gerningsbelæg mangler)?(?=[.;]|$)'), ''),
    (re.compile(r'(?:^|(?<=[.;:] ))(?:Hizb ut-Tahrirs|Bevægelsens) svar har ingen nutidig stillingslæsning af [^.]+\.\s*'), ''),
    (re.compile(r'\s*(?:Der er intet|Ingen) nyere (?:svar|læsning)[^.]*\.'), ''),
    (re.compile(r'\s*(?:Intet svar dækker|Der er intet svar om|Svarene har ingen (?:egen )?læsning af)[^.]*\.'), ''),
    (re.compile(r';\s*[A-ZÆØÅ][\w-]* (?:får ingen særskilt læsning|nævnes ikke særskilt)[^.;]*'), ''),
    (re.compile(r'\s*[A-ZÆØÅ][\w-]* nævnes ikke som part i svarene[^.]*\.'), ''),
    (re.compile(r' – det seneste om regionen –'), ''),
    (re.compile(r'; svaret af [\d/]+ er det seneste(?=\.)'), ''),
    (re.compile(r'(?:^|(?<=\. ))Svaret af ([\d/]+) er det seneste: (\w+) er '), r'Ifølge svaret af \1 er \2 '),
]
# the people loyal to a power, never 'Storbritanniens folk' – in Danish that first reads as the British people, and
# Khabar judges states, never peoples (review 2026-10-17); 'vasaller' is an agent word – the layer says 'underordnede'
WORDING = [
    (re.compile(r"\b(USA's|USA’s|Storbritanniens|Frankrigs|Europas|Ruslands|Amerikas|Englands|kolonimagts|kolonimagtens) folk\b"),
     r'\1 tilhængere'),
    (re.compile(r'\bdets folk\b(?= (?:i|afløser|fra|mod)\b|,|$)'), 'dets tilhængere'),
    (re.compile(r'(?<!det )\b(amerikanske og britiske|britiske|amerikanske|franske) folk\b'), r'\1 tilhængere'),
    (re.compile(r'\bikke meget forskelligt fra vasaller\b'), 'ikke meget forskelligt fra underordnede stater'),
]


def tidy(s):
    s = ' '.join(str(s or '').split())
    for rx, to in META + WORDING:
        s = rx.sub(to, s)
    return re.sub(r'\s+([.;,])', r'\1', s).strip()


def attributed(s, when=None):
    s = tidy(s)
    for rx, to in ATTRIB:
        if rx.match(s):
            return rx.sub(to, s, count=1)
    if when and re.match(r'^Ifølge svaret[ :]', s):
        return 'Ifølge Hizb ut-Tahrirs svar af ' + d_slash(when) + s[len('Ifølge svaret'):]
    return s


# a working label of the syntheses ('ÆNDRING: redskabet skifter …') is no part of the reading the app shows; the known
# acronyms stay ('NATO: …' as a speaker)
ACRONYMS = ('NATO', 'OPEC', 'ISIS', 'UNRWA', 'BRICS', 'IAEA', 'CENTCOM', 'AFRICOM', 'ECOWAS', 'ASEAN', 'UNHCR', 'UNICEF',
            'USAID', 'SWIFT', 'AUKUS', 'QUAD', 'SDF', 'PKK', 'IMF')
LABEL = re.compile(r'(?<![\w])(?!(?:' + '|'.join(ACRONYMS) + r')\b)[A-ZÆØÅ]{4,}:\s*([a-zæøå]?)')


def unlabel(s):
    """The text without its working labels; the sentence a label opened starts with a capital."""
    return LABEL.sub(lambda m: m.group(1).upper(), s) if s else s


def owned(s, when, lead='af'):
    """Every text of the layer names the movement (card M1), also where the app shows it outside its answer: a text that
    does not start with an attribution gets 'Ifølge Hizb ut-Tahrirs svar af d/m/åååå: '."""
    s = unlabel(s)
    s = attributed(s, when)
    for rx, to in OPENINGS:
        if rx.match(s):
            s = rx.sub(to, s, count=1)
            break
    if 'Hizb ut-Tahrir' not in s and when:
        s = f'Ifølge Hizb ut-Tahrirs svar {lead} {d_slash(when)}: ' + s
    return s


def stand_class(value):
    v = str(value or '').lower()
    return next((c for c, rx in STAND_CLASSES if rx.search(v)), 'andet') if v else None


def dates_in(text):
    """Every day, month or year a text names ('4/10/2023', '2/2009', 'januar 2015', '2013'), as the first day it can mean,
    without the attribution's own date."""
    t = re.sub(r'^Ifølge Hizb ut-Tahrirs svar (?:til og med|fra|af) [\d/]+:\s*', '', text or '')
    out = []
    for rx, make in ((r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', lambda m: (int(m[3]), int(m[2]), int(m[1]))),
                     (r'\b(\d{1,2})/((?:19|20)\d\d)\b', lambda m: (int(m[2]), int(m[1]), 1)),
                     (r'\b(' + '|'.join(MONTHS) + r') ((?:19|20)\d\d)\b', lambda m: (int(m[2]), MONTHS[m[1]], 1)),
                     (r'(?<![\d/])((?:19|20)\d\d)(?![\d/])', lambda m: (int(m[1]), 1, 1))):
        for m in re.finditer(rx, t):
            try:
                out.append(date(*make(m)))
            except ValueError:
                pass
        t = re.sub(rx, ' ', t)
    return out


def changed_before(since, text):
    """A 'changed_from' is the reading that 'since' replaced: every date in it falls before 'since', and it is a reading,
    not 'unchanged'."""
    return bool(since) and not re.search(r'uændret|den samme siden', text) and all(d < day(since) for d in dates_in(text))


def similar(a, b):
    wa, wb = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    return len(wa & wb) / max(1, len(wa | wb))


def cites(strings, own, answers_by_day):
    """The earlier answers an answer cites ('Svar på spørgsmål af 11/12/2022 om …') → their numbers, by date."""
    out = []
    for s in strings or []:
        for d, m, y in re.findall(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', s):
            try:
                when = date(int(y), int(m), int(d))
            except ValueError:
                continue
            hits = answers_by_day.get(when.isoformat(), [])
            if not hits:
                near = [n for k, ns in answers_by_day.items() if abs((day(k) - when).days) <= 3 for n in ns]
                hits = near if len(set(near)) == 1 else []
            out += [n for n in hits if n != own]
    return list(dict.fromkeys(out))


def build(now=None):
    extracts = [json.loads(Path(f).read_text(encoding='utf-8')) for f in sorted(glob.glob(str(SRC / 'extract' / '*.json')))]
    groups = {Path(f).stem: json.loads(Path(f).read_text(encoding='utf-8')) for f in sorted(glob.glob(str(SRC / 'synth' / '*.json')))}
    qa = json.loads(QA.read_text(encoding='utf-8'))
    en_url = {re.search(r'/(\d+)\.html', q['url']).group(1): q['url'] for q in qa}
    nums = Numbers(extracts)

    # answers: one per number; the kept edition gives the text fields, the earliest edition the date
    answers = {}
    for x in sorted(extracts, key=lambda x: ('/en/' not in x['url'], x['nr'] in ALIASES, x['date'])):
        nr = nums.by_key[x['key']]
        a = answers.get(nr)
        if a is None:
            answers[nr] = {'date': x['date'], 'title_da': x['title_da'], 'question_da': tidy(nums.text(x['question_da'])),
                           'note_da': nums.text(x['note_da']), 'url': en_url.get(nr) or x['url'],
                           'issues': list(x['issues']), 'states': list(x['states']), 'powers': list(x['powers']),
                           '_cites': list(x.get('cites') or [])}
        else:
            a['date'] = min(a['date'], x['date'])
            for k in ('issues', 'states', 'powers'):
                a[k] = list(dict.fromkeys(a[k] + x[k]))
            a['_cites'] += x.get('cites') or []
    by_day = {}
    for nr, a in answers.items():
        by_day.setdefault(a['date'], []).append(nr)
    for nr, a in answers.items():
        c = cites(a.pop('_cites'), nr, by_day)
        if c:
            a['cites_nrs'] = c
    answers = dict(sorted(answers.items(), key=lambda kv: (kv[1]['date'], kv[0])))
    for a in answers.values():
        a['note_da'] = owned(a['note_da'], a['date'])

    def answer_date(nr, fallback):
        return answers[nr]['date'] if nr in answers else fallback

    def lead_answer(text, nr, subj):
        """The answer a current reading leads with ('Ifølge Hizb ut-Tahrirs svar af 28/6/2026 …'), which may be older than
        the answer that last touched the subject."""
        m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', text)
        if not m:
            return nr
        try:
            when = date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return nr
        if answer_date(nr, '') == when:
            return nr
        hits = by_day.get(when) or []
        if not hits:
            near = [n for k, ns in by_day.items() if abs((day(k) - day(when)).days) <= 3 for n in ns]
            hits = near if len(set(near)) == 1 else []
        if not hits:
            return nr
        parts = set(subj.split('--'))
        own = [n for n in hits if parts & set(answers[n]['states'] + answers[n]['powers'] + answers[n]['issues'])]
        return (own or hits)[0]

    # readings over time, merged across the groups
    readings, home = {}, {}
    for g, s in groups.items():
        for subj, rows in s['timelines'].items():
            home.setdefault(subj, {})[g] = len(rows)
            for r in rows:
                nr = nums.of(r['nr'], r.get('date'), subj)
                row = {'date': answer_date(nr, r['date']), 'nr': nr, 'kind': r['kind']}
                for k in ('object', 'value'):
                    if r.get(k):
                        row[k] = r[k]
                if row['kind'] == 'stilling' and row.get('value'):
                    row['class'] = stand_class(row['value'])
                row['text_da'] = owned(nums.text(r['text_da']), row['date'])
                if HISTORICAL.search(row['text_da']):
                    row['historical'] = True
                also = [nums.of(n, None, subj) for n in r.get('also') or []]
                also = [n for n in dict.fromkeys(also) if n != nr]
                if also:
                    row['also'] = also
                last = next((r[k] for k in SPAN_DATE if r.get(k)), None)
                last_nr = next((r[k] for k in SPAN_NR if r.get(k)), None)
                last_nr = nums.of(last_nr, last, subj) if last_nr else None
                if last_nr in answers:
                    last = answers[last_nr]['date']
                if last and last[:10] != row['date']:
                    row['last'] = last[:10]
                if last_nr and last_nr != nr:
                    row['last_nr'] = last_nr
                rows_out = readings.setdefault(subj, [])
                dup = next((x for x in rows_out if x['nr'] == nr and x['kind'] == row['kind']
                            and x.get('object') == row.get('object') and similar(x['text_da'], row['text_da']) >= 0.3), None)
                if dup is None:
                    rows_out.append(row)
                    continue
                if len(row['text_da']) > len(dup['text_da']):
                    dup['text_da'] = row['text_da']
                    if row.get('value'):
                        dup['value'] = row['value']
                        if row.get('class'):
                            dup['class'] = row['class']
                if row.get('also'):
                    dup['also'] = [n for n in dict.fromkeys((dup.get('also') or []) + row['also']) if n != nr]
                if row.get('last') and row['last'] > dup.get('last', ''):
                    dup['last'] = row['last']
                    if row.get('last_nr'):
                        dup['last_nr'] = row['last_nr']
    for subj in readings:
        readings[subj].sort(key=lambda x: (x['date'], x['nr'], x['kind']))
    readings = dict(sorted(readings.items()))

    # the current reading: where two groups give one, the newest answer governs (a tie: the group that reads the
    # subject most)
    current, reconciled = {}, []
    for g, s in groups.items():
        for subj, c in s['current'].items():
            nr = nums.of(c['nr'], c.get('date'), subj)
            touched = answer_date(nr, c['date'])
            text = owned(nums.text(c['text_da']), touched)
            lead = lead_answer(text, nr, subj)
            row = {'text_da': text, 'date': answer_date(lead, touched), 'nr': lead, 'since': c.get('since') or c['date']}
            if lead != nr:      # the reading leads with an older answer; a newer one has touched the subject since
                row['latest'], row['latest_nr'] = touched, nr
            if c.get('changed_from'):
                # what the reading was before 'since' – or, where the text spans the years after it too, the reading's
                # course ('earlier_da', shown without a date)
                before = owned(nums.text(c['changed_from']), touched, 'til og med')
                row['changed_from' if changed_before(row['since'], before) else 'earlier_da'] = before
            old = current.get(subj)
            weight = (CURRENT_FROM.get(subj) == g, touched, home.get(subj, {}).get(g, 0), len(row['text_da']))
            if old is None or weight > old[0]:
                if old is not None:
                    reconciled.append((subj, old[1].get('latest') or old[1]['date'], touched, g))   # (subject, lost, kept, group kept)
                current[subj] = (weight, row)
            else:
                reconciled.append((subj, touched, old[1].get('latest') or old[1]['date'], 'the earlier group'))
    current = {k: v[1] for k, v in sorted(current.items())}
    stale = [(k, c.get('latest') or c['date'], readings[k][-1]['date']) for k, c in current.items()
             if k in readings and readings[k][-1]['date'] > (c.get('latest') or c['date'])]

    issues = {}
    for g, s in groups.items():
        for iid, v in s['issues'].items():
            nrs = list(dict.fromkeys(nums.of(n) for n in v.get('nrs') or []))
            first = min((answers[n]['date'] for n in nrs if n in answers), default=None)
            text = owned(nums.text(v['history_da']), first, 'fra')
            if iid in issues:   # one group per issue so far; keep the longer history if that changes
                if len(text) <= len(issues[iid]['history_da']):
                    issues[iid]['nrs'] = list(dict.fromkeys(issues[iid]['nrs'] + nrs))
                    continue
            issues[iid] = {'history_da': text, 'nrs': nrs}
    issues = dict(sorted(issues.items()))

    expectations, said = [], []      # said: the texts as the groups wrote them (the attribution would make all alike)
    for g, s in groups.items():
        for e in s['expectations']:
            nr = nums.of(e['nr'], e.get('date'), e.get('subject'))
            when = answer_date(nr, e['date'])
            text = nums.text(e['text_da'])
            row = {'date': when, 'nr': nr, 'subject': e.get('subject'), 'text_da': owned(text, when)}
            text = re.sub(r'^Ifølge [^:]{0,60}?svar\w*(?: af [\d/]+)?(?: forventedes)?:? ', '', text)
            if e.get('outcome'):
                row['outcome'] = e['outcome']
            if any(n == nr and similar(t, text) >= 0.5 for n, t in said):
                continue
            expectations.append(row)
            said.append((nr, text))
    expectations.sort(key=lambda x: (x['date'], x['nr']))

    layer = {'version': 1, 'built': (now or datetime.now(timezone.utc)).isoformat(timespec='seconds'),
             'answers': answers, 'readings': readings, 'current': current, 'issues': issues, 'expectations': expectations}
    return layer, reconciled, stale


# the layer's own vocabulary for 'serves' (card H1): the agent words plus the softer ones the answers use
SERVE = re.compile(AGENT_WORDS.pattern[:-1] + r'|redskab\w*|[\w-]*loyal\w*|knyttet til|tjener|i hånden|underlagt|'
                   r'søjle for|støttes af|støttet af|hører til|\w+s (?:mand|mænd|folk|tilhængere)\b|planlagt af|planlagde)', re.I)
# an attack with dead or a bombing: never said to be staged or sponsored on a reader surface (card G13), whoever the subject
STAGED = re.compile(r'\b(iscenesat\w*|iscenesæt\w*|står bag|stod bag|falsk flag|planlagt af|planlagde|på ordre fra)\b', re.I)
ATTACK = re.compile(r'\b(\w*angreb\w*|\w*bombe\w*|bombning\w*|drab\w*|dræb\w*|massakre\w*|attentat\w*|eksplosion\w*|volden)\b',
                    re.I)
UNPROVEN = 'gerningsbelæg mangler'
# identifiable persons who were not ruling when the answer was written, and parties (card H3): never said to serve anyone,
# whether or not the model knows them. Their government or rule may be read ('styret under X', 'X-regeringen').
NOT_RULING = ('Compaoré', 'Kaboré', 'Tandja', 'Hasina', 'Kongrespart', 'Kongres-part', 'BJP', 'Ruto', 'Hamzah', 'Sonia Gandhi',
              'Beidh', 'Folkepartiet', 'PPP', 'Republikan', 'Demokraterne', 'Trumps kreds', 'Trump-fløj', 'Bhutto', 'Imran Khan',
              'Hamdok', 'Issoufou', 'Odinga', 'Bilawal', 'Gülen')
GOVERNMENT = re.compile(r'\b(?:[Ss]tyret|[Rr]egeringen|[Rr]egering) under [\w\-]+(?: [A-ZÆØÅ][\w\-]+)?|[\w\-]+-(?:regering\w*|styre\w*|'
                        r'ledede regering\w*|lejren)|[\w\-]+s (?:regering\w*|styre\b|styret)', re.U)
LOCAL = re.compile(r'\b[A-Za-z]:[\\/]|[\\/]Alpha[\\/]|pCloud|[\\/]Users[\\/]', re.I)
QUOTE = re.compile(r'»([^«»]*)«|«([^«»]*)»')     # Danish »…« and the other way round
QUOTE_MAX = 60


def texts_of(layer):
    """Every text of the layer, with where it is and whether it must name the movement."""
    out = []
    for k, a in layer['answers'].items():
        out += [(f'answer {k} title', a['title_da'], False), (f'answer {k} question', a['question_da'], False),
                (f'answer {k} note', a['note_da'], True)]
    for k, rows in layer['readings'].items():
        for i, r in enumerate(rows):
            out.append((f'reading {k}[{i}]', r['text_da'], True))
            if r.get('value'):
                out.append((f'reading {k}[{i}] value', r['value'], False))
    for k, c in layer['current'].items():
        out.append((f'current {k}', c['text_da'], True))
        for f in ('changed_from', 'earlier_da'):
            if c.get(f):
                out.append((f'current {k} {f}', c[f], True))
    out += [(f'issue {k}', v['history_da'], True) for k, v in layer['issues'].items()]
    out += [(f"expectation {e['nr']}", e['text_da'], True) for e in layer['expectations']]
    return out


def protected_names():
    """The names never said to serve anyone: the seed model's protected actors (when the model is here) and the
    non-ruling persons and parties the layer's own list names."""
    seed = json.loads(SEED.read_text(encoding='utf-8')) if SEED.exists() else {'actors': {}}
    protected = [a['name'] for a in seed['actors'].values() if a.get('kind') in PROTECTED and len(a['name']) > 4]
    return protected + list(NOT_RULING)


def serving_problems(where, t, names, problems):
    """The sentence-level rules of a reader text: no attack with dead said to be staged or sponsored (G13), no serving
    claim near a protected or non-ruling person or a party (H3)."""
    for sentence in re.split(r'(?<=[.!?])\s+', t):
        if sentence.rstrip().endswith('?') or UNPROVEN in sentence:
            continue
        for m in STAGED.finditer(sentence):
            near = sentence[max(0, m.start() - 80):m.end() + 80]
            if ATTACK.search(near):
                problems.append(f"{where}: an attack said to be staged or sponsored (G13) – write '{UNPROVEN}' or drop it: {near}")
                break
        plain = GOVERNMENT.sub('REGERINGEN', sentence)
        for m in SERVE.finditer(plain):
            near = plain[max(0, m.start() - 60):m.end() + 60]
            hit = next((n for n in names if n in near), None)
            if hit:
                problems.append(f'{where}: a serving claim near a protected or non-ruling person or a party ({hit}, H3): {near}')
                break


def check(layer):
    """Khabar's hard rules hold in the movement's layer too (card G13, H1-H5, M1): the movement named in every reading;
    no forgeries or verdicts on peoples; no agent words (the layer says 'underordnet'); no claim that an attack with dead
    was staged or sponsored unless it says that deeds are missing; no serving claim about a protected person the model
    knows, a non-ruling person or a party; no local paths and no long quotations (the repo is public); every date is its
    answer's date."""
    names = protected_names()
    problems = []
    for where, t, own in texts_of(layer):
        check_voice(t, where, problems)
        if own and 'Hizb ut-Tahrir' not in t:
            problems.append(f"{where}: the movement is not named ('Ifølge Hizb ut-Tahrirs svar af …', M1): {t[:80]}")
        hit = re.search(r'\bagent\w*', t, re.I)
        if hit:
            problems.append(f"{where}: '{hit.group(0)}' – the layer says 'underordnet' (H1): {t[max(0, hit.start() - 60):hit.end() + 40]}")
        if LOCAL.search(t):
            problems.append(f'{where}: a local path or private name')
        for q in (a or b for a, b in QUOTE.findall(t)):
            if len(q) > QUOTE_MAX:
                problems.append(f'{where}: a quotation over {QUOTE_MAX} characters')
        serving_problems(where, t, names, problems)
    answers = layer['answers']
    for k, a in answers.items():
        if not a.get('url'):
            problems.append(f'answer {k}: no source url')

    def dated(where, nr, when):
        if nr not in answers:
            problems.append(f'{where}: unknown answer {nr}')
        elif when != answers[nr]['date']:
            problems.append(f"{where}: dated {when}, but answer {nr} is of {answers[nr]['date']}")
    for k, rows in layer['readings'].items():
        for i, r in enumerate(rows):
            dated(f'reading {k}[{i}]', r['nr'], r['date'])
            if r.get('last_nr'):
                dated(f'reading {k}[{i}] last', r['last_nr'], r.get('last'))
    for k, rows in layer['readings'].items():
        for i, r in enumerate(rows):
            if r['kind'] == 'stilling' and r.get('value') and r.get('class') != stand_class(r['value']):
                problems.append(f"reading {k}[{i}]: the standing '{r['value']}' has no class or the wrong one")
    for k, c in layer['current'].items():
        if c.get('changed_from') and not changed_before(c.get('since'), c['changed_from']):
            problems.append(f"current {k}: 'changed_from' names dates on or after 'since' {c.get('since')} or no change – "
                            "make it 'earlier_da'")
        dated(f'current {k}', c['nr'], c['date'])
        if c.get('latest_nr'):
            dated(f'current {k} latest', c['latest_nr'], c['latest'])
    for e in layer['expectations']:
        dated(f"expectation {e['nr']}", e['nr'], e['date'])
    return problems


INDEX_ANSWER = ('date', 'title_da', 'question_da', 'issues', 'states', 'powers')


def index(layer):
    """The app's slim index: what its lists show at once (the answers' titles, the current readings)."""
    return {'version': layer['version'], 'built': layer['built'],
            'answers': {k: {f: a[f] for f in INDEX_ANSWER if a.get(f)} for k, a in layer['answers'].items()},
            'current': layer['current']}


def main():
    layer, reconciled, stale = build()
    problems = check(layer)
    for p in problems:
        print(' -', p)
    if problems:
        sys.exit(1)
    text = json.dumps(layer, ensure_ascii=False, separators=(',', ':'))
    slim = json.dumps(index(layer), ensure_ascii=False, separators=(',', ':'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    INDEX.write_text(slim, encoding='utf-8')
    n = sum(len(v) for v in layer['readings'].values())
    print(f"answers {len(layer['answers'])} · subjects {len(layer['readings'])} · readings {n} · current {len(layer['current'])} · "
          f"issues {len(layer['issues'])} · expectations {len(layer['expectations'])} · {len(text.encode('utf-8'))} bytes "
          f"(index {len(slim.encode('utf-8'))} bytes)")
    for subj, lost, kept, g in reconciled:
        print(f'  current {subj}: {kept} governs over {lost} ({g})')
    for subj, cur, newest in stale:
        print(f'  current {subj} ({cur}) is older than its newest reading ({newest})')


if __name__ == '__main__':
    main()
