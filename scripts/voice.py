"""Khabar's content rules as checks, ported from Khabar 2 (scripts/editor2.py, scripts/knowledge.py and
scripts/build_movement.py on the khabar2 branch). editor.py publish runs them on what the editor writes.

    check_voice(text, where, problems)     every Danish text: no praise of or call to violence; judge states, rulers,
                                           policies and ideas – never peoples, religions or anyone's belief; 'Israel'
                                           in Khabar's own voice ('den jødiske entitet' only inside a quotation); no
                                           forgeries or conspiracy myths (card H4, H5, D10)
    check_reality(text, where, problems)   Khabar's own text (the lede, the summaries) is reality only: none of the
                                           movement's reading words (standing, rank, serving) and never Hizb
                                           ut-Tahrir's reading – the brain weighs the news, the app shows no analysis
                                           (card H2; the owner's decision of 2026-10-17)
    check_movement(text, where, problems)  a reading of one of Hizb ut-Tahrir's answers (the answer object): no agent
                                           words (the layer says 'underordnet'); no attack with dead said to be staged
                                           or sponsored unless deeds are said to be missing; no claim that a mosque, an
                                           imam or scholar, a media outlet, a Danish person or organisation or a
                                           non-ruling person serves anyone; quotations of at most QUOTE_MAX characters
                                           and no local paths (the repo and the digest branch are public) (card G13, H1,
                                           H3)"""
import re

VOICE_BANNED = [   # a call to arms ('Til våben!', 'grib til våben'), not a thing 'gjort til våben' (weaponised)
    (re.compile(r'\b(heltemod\w*|martyr\w*|nusra\w*|omstyrt\w*|hærindgriben|væbnet kamp|væbnede kamp|grib (?:\w+ )?til våben)\b'
                r'|(?:^|[.!?:»«"]\s*)til våben\b', re.I | re.M),
     "no praise of violence and no call to violence, a coup or an army's intervention in Khabar's own voice (H4)"),
    (re.compile(r'\b(jøderne|de kristne|de vantro|kuffar|kafir\w*|kufr|riddah|nifaq|danskerne er)\b', re.I),
     "judge states, rulers, policies and ideas – never peoples, religions or anyone's belief (H5, D10)"),
    (re.compile(r'(?<![«»"„“])\b(den jødiske entitet|den zionistiske entitet)\b', re.I),
     "Khabar says 'Israel'; 'den jødiske entitet' only inside a quotation with who said it (H5)"),
    (re.compile(r'\b(zions vise|protokol\w* fra zion|franklin-citat\w*|IS (blev )?skabt af)\b', re.I),
     'no forgeries or conspiracy myths (H5)'),
]
AGENT_WORDS = re.compile(r'\b(agent\w*|marionet\w*|lakaj\w*|bagmand\w*|står bag|stod bag|iscenesat\w*|iscenesæt\w*|'
                         r'på ordre fra|på vegne af|tjener \w+ interesser|går \w+ ærinde|aftalt spil|patron\w*|hoflærd\w*|'
                         r'del af kampagnen|forræder\w*|vasal\w*|proxy\w*|stedfortræder\w*|styret af|falsk flag)', re.I)
# Khabar's own text (the lede, the summaries) carries none of the movement's reading: its standing and rank words, its
# serving words and its name as a source. Only words that are readings, not news: 'står bag', 'på vegne af', 'styret
# af', 'agent' and 'forræderi' are everyday news (who claimed an attack, a court's verdict, a charge) and stay allowed
# – the editor's summaries of a month held them four times, every time as plain fact.
REALITY_BANNED = re.compile(r"\b(satellitstat\w*|(?:som|blev|er|var|nu|igen) (?:en |USA's |Ruslands |Kinas )?satellit\b|"
                            r"(?:USA's|Ruslands|Kinas|Storbritanniens|amerikansk|russisk|kinesisk|britisk) satellit\b|"
                            r"satellit(?:ten)? (?:for|i|under) (?:USA|Rusland|Kina|Storbritannien)|underordne(?:t|de) (?:stat\w*|under\b)|"
                            r"i (?:USA's|amerikansk) bane|kredser om USA|marionet\w*|lakaj\w*|vasal\w*|hoflærd\w*|"
                            r'aftalt spil|falsk flag|tjener \w+ interesser|går \w+ ærinde|del af kampagnen|den førende stat|'
                            r'faldet fra stormagt|svækket stormagt|mellemmagt\w*|'
                            r'ifølge Hizb ut-Tahrir\w*|Hizb ut-Tahrirs (?:svar|læsning)\w*)', re.I)
# the movement layer's own vocabulary for 'serves' (card H1): the agent words and the softer ones the answers use
SERVE = re.compile(AGENT_WORDS.pattern[:-1] + r'|redskab\w*|[\w-]*loyal\w*|knyttet til|tjener|i hånden|underlagt|'
                   r'søjle for|støttes af|støttet af|hører til|\w+s (?:mand|mænd|folk|tilhængere)\b|planlagt af|planlagde|handler for)', re.I)
# the people loyal to a power are its 'tilhængere', never 'Storbritanniens folk' – that first reads as the British people
# (Khabar judges states, never peoples; review 2026-10-17)
POWER_FOLK = re.compile(r"\b(?:USA's|USA’s|Storbritanniens|Frankrigs|Europas|Ruslands|Kinas|Amerikas|Englands) folk\b")
# an attack with dead or a bombing is never said to be staged or sponsored (card G13), whoever the subject
STAGED = re.compile(r'\b(iscenesat\w*|iscenesæt\w*|står bag|stod bag|falsk flag|planlagt af|planlagde|på ordre fra|skuespil\w*)\b',
                    re.I)
ATTACK = re.compile(r'\b(\w*angreb\w*|\w*bombe\w*|bombning\w*|drab\w*|dræb\w*|massakre\w*|attentat\w*|eksplosion\w*|volden|'
                    r'terror\w*|skyderi\w*|anslag\w*)\b', re.I)
UNPROVEN = 'gerningsbelæg mangler'
# never said to serve anyone (card H3): mosques, imams and scholars, media, Danish persons and organisations, and the
# non-ruling persons and parties the answers have named (build_movement.NOT_RULING)
PROTECTED = re.compile(r'\b(moské\w*|moske\w*|imam\w*|lærd\w*|sheik\w*|shaykh\w*|mufti\w*|prædikant\w*|'
                       r'medie(?:r|rne|rnes|t|ts|hus\w*)?|avis(?:en|ens|er|erne|ernes)?|journalist\w*|tv-station\w*|forening\w*|'
                       r'danske? (?:muslim\w*|organisation\w*|forening\w*|parti\w*|politiker\w*|imam\w*|moské\w*|medie\w*|'
                       r'avis\w*|person\w*|statsborger\w*))\b', re.I)
# a government or a rule may be read ('styret under X', 'X-regeringen', 'Xs regering'): the serving check reads it as
# the state, not as the person or party that leads it – as build_movement.check() does for the layer
GOVERNMENT = re.compile(r'\b(?:[Ss]tyret|[Rr]egeringen|[Rr]egering) under [\w\-]+(?: [A-ZÆØÅ][\w\-]+)?|[\w\-]+-(?:regering\w*|styre\w*|'
                        r'ledede regering\w*|lejren)|[\w\-]+s (?:regering\w*|styre\b|styret)', re.U)
NOT_RULING = ('Compaoré', 'Kaboré', 'Tandja', 'Hasina', 'Kongrespart', 'Kongres-part', 'BJP', 'Ruto', 'Hamzah', 'Sonia Gandhi',
              'Beidh', 'Folkepartiet', 'PPP', 'Republikan', 'Demokraterne', 'Trumps kreds', 'Trump-fløj', 'Bhutto', 'Imran Khan',
              'Hamdok', 'Issoufou', 'Odinga', 'Bilawal', 'Gülen')
LOCAL = re.compile(r'\b[A-Za-z]:[\\/]|[\\/]Alpha[\\/]|pCloud|[\\/]Users[\\/]', re.I)
QUOTE = re.compile(r'»([^«»]*)«|«([^«»]*)»|"([^"]*)"|“([^”]*)”')
QUOTE_MAX = 60


def check_voice(text, where, problems):
    for rx, why in VOICE_BANNED:
        hit = rx.search(text or '')
        if hit:
            problems.append(f"{where}: '{hit.group(0)}' – {why}")


def check_reality(text, where, problems):
    hit = REALITY_BANNED.search(text or '')
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' is a reading or judgement word – Khabar's own text is reality only "
                        "(who did or said what, where, when); the movement's readings only weigh the news")


def check_movement(text, where, problems):
    t = text or ''
    hit = re.search(r'\bagent\w*|\bmarionet\w*|\blakaj\w*|\bhoflærd\w*|\bvasal\w*|\bproxy\w*|\bforræder\w*', t, re.I)
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' – the movement's readings say 'underordnet' or 'satellit' (H1)")
    if LOCAL.search(t):
        problems.append(f'{where}: a local path or private name')
    hit = POWER_FOLK.search(t)
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' reads as a people – write '{hit.group(0)[:-5]} tilhængere'")
    for q in (next(x for x in groups if x) for groups in QUOTE.findall(t) if any(groups)):
        if len(q) > QUOTE_MAX:
            problems.append(f'{where}: a quotation over {QUOTE_MAX} characters – the repo is public: say it in your own words')
    for sentence in re.split(r'(?<=[.!?])\s+', t):
        if sentence.rstrip().endswith('?') or UNPROVEN in sentence:
            continue
        for m in STAGED.finditer(sentence):
            near = sentence[max(0, m.start() - 80):m.end() + 80]
            if ATTACK.search(near):
                problems.append(f"{where}: an attack said to be staged or sponsored (G13) – write '{UNPROVEN}' or leave it "
                                f'out: {near}')
                break
        plain = GOVERNMENT.sub('REGERINGEN', sentence)
        for m in SERVE.finditer(plain):
            near = plain[max(0, m.start() - 60):m.end() + 60]
            who = PROTECTED.search(near) or next((n for n in NOT_RULING if n in near), None)
            if who:
                who = who.group(0) if hasattr(who, 'group') else who
                problems.append(f"{where}: a serving claim near '{who}' – never about a mosque, a scholar, a media outlet, a "
                                f'Danish person or organisation or a non-ruling person (H3): {near}')
                break
