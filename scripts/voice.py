"""Khabar's content rules as checks, ported from Khabar 2 (scripts/editor2.py, scripts/knowledge.py and
scripts/build_movement.py on the khabar2 branch). editor.py publish runs them on what the editor writes.

    check_voice(text, where, problems)     every Danish text: no praise of or call to violence ('heroisk', 'helte' near
                                           fighting); judge states, rulers, policies and ideas – never peoples, religions
                                           or anyone's belief; 'Israel' and 'israelske styrker' in Khabar's own voice
                                           ('den jødiske entitet', 'den zionistiske fjende', 'besættelsesstyrker' only
                                           inside a quotation); no forgeries or conspiracy myths (card H4, H5, D10)
    check_reality(text, where, problems)   Khabar's own text (the lede, the summaries) is reality only: none of the
                                           movement's reading words (standing, rank, serving) and never Hizb
                                           ut-Tahrir's reading – the brain weighs the news, the app shows no analysis
                                           (card H2; the owner's decision of 2026-10-17)
    check_headline(text, where, problems)  the editor's headlines, block titles and front-page lines: informative, never a
                                           curiosity headline (a question, 'Derfor …', 'Se …', 'Her er …', 'Sådan …',
                                           'Det skal du vide', a cliff-hanger colon or '…', '– video' at the end;
                                           English equivalents – the owner's rule of 2026-10-17), no judgement of its
                                           own ('egentlige', 'i virkeligheden') unless as 'Who: what', and the voice and
                                           reality checks (the source's own words inside »…« are its framing);
                                           curiosity(text) says which words
    check_movement(text, where, problems)  a reading of one of Hizb ut-Tahrir's answers (the answer object): no agent
                                           words (the layer says 'underordnet'); no attack with dead said to be staged
                                           or sponsored unless deeds are said to be missing; no claim that a mosque, an
                                           imam or scholar, a media outlet, a Danish person or organisation or a
                                           non-ruling person serves anyone; quotations of at most QUOTE_MAX characters
                                           and no local paths (the repo and the digest branch are public) (card G13, H1,
                                           H3)
    check_plain(text, where, problems)     a note or reading of an answer is said in plain Danish without its attribution
                                           ('Ifølge Hizb ut-Tahrirs svar af …', 'Ifølge svaret …', 'Hizb ut-Tahrirs svar
                                           læser …'): the app shows it under the label 'Hizb ut-Tahrirs svar ·
                                           d/m/åååå' (the owner, 2026-10-17: "det står over det hele")"""
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
# outside a quotation (»…«) only: the channels' own names for Israel's state and forces ('den zionistiske fjende',
# 'Zionist-regimet') – Khabar says Israel, 'israelske styrker' (H5) – and praise of fighters ('heroisk', 'helte' near
# an attack or an operation: H4). The ideology is named as an idea ('zionismen') and stays allowed. A source's framing
# word ('besættelsesstyrker', 'Israeli occupation aircraft' → 'Israelske besættelsesfly') may be kept – the owner's
# headline rule – but only beside Israel's own name: never in its place ('Besættelsesstyrker anholder …').
OWN_VOICE = [
    (re.compile(r'\b(zionist(?:isk|iske)?[\s-]*(?:fjende\w*|regime\w*|styrke\w*|stat\b|staten\w*|hær\w*|bosætter\w*|soldat\w*|'
                r'besættelse\w*|entitet\w*|myndighed\w*|fly\b|flyene|angreb\w*|krigsmaskine\w*)|zionisterne\w*)', re.I),
     "Khabar says 'Israel' and 'israelske styrker'; the channels' own names only inside a quotation with who said it (H5)"),
    (re.compile(r'\bheroisk\w*', re.I),
     "no praise of violence in Khabar's own voice – say what happened (H4)"),
]
OCCUPATION = re.compile(r'\b(besættelses(?:styrke|hær|stat|myndighed|soldat|regering|regime|politi|tropp|fly|magten)\w*)', re.I)
ISRAEL_NAMED = re.compile(r'\bisrael', re.I)
# The owner's house style (2026-10-17: "israel altid skal skrives med anførselstegn “israel”", also 'israelsk'): every
# form of the name in Khabar's own text is written in lower case inside curly quotes – “israel”, “israels”,
# “israelske”, “israel”-Hamas-krigen. quote_israel() writes it so; it is idempotent, and a form the editor already set
# in other quotes ('"Israel"', '»Israel«') becomes the house form. A link or an id is never touched.
_ISRAEL_QUOTED = re.compile(r'[“"»„](israel\w*)[”"«“]', re.I)
_ISRAEL_BARE = re.compile(r'(?<![\w“/.:#=])(israel\w*)(?![\w”/])', re.I)


def quote_israel(text):
    if not isinstance(text, str) or not ISRAEL_NAMED.search(text) or re.match(r'^https?://', text):
        return text
    text = _ISRAEL_QUOTED.sub(lambda m: '“' + m.group(1).lower() + '”', text)
    return _ISRAEL_BARE.sub(lambda m: '“' + m.group(1).lower() + '”', text)
HERO = re.compile(r'\b(?:helt(?:e|ene|enes|emodig\w*)|heltedåd\w*)\b', re.I)
VIOLENCE = re.compile(r'\b(\w*angreb\w*|operation\w*|modstand\w*|kamp\w*|kæmpe\w*|\w*bombe\w*|dræb\w*|raket\w*|soldat\w*|'
                      r'styrker|krig\w*|martyr\w*|faldne)\b', re.I)
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
# a curiosity headline withholds the news to make the reader click (the owner 2026-10-17, notes-owner-headlines.md): a
# question, a teaser opening ('Derfor …', 'Se …', 'Her er …', 'Sådan …', 'Det skal du vide') at the start or after a
# colon or dash, a cliff-hanger colon or '…' at the end, and the click phrases; English equivalents for the same. 'Who:
# what' ('Kreml: Samtalerne fortsætter', 'Ekspert: Putin holder magten, fordi han …') is the wire's style and stays.
CURIOUS_DA = re.compile(r'(?:^|[:–—]\s*|\s-\s+)[»«"„“\']?(derfor|se|her er|her får du|her kan du|her ser du|sådan|'
                        r'det skal du vide|dét skal du vide|hvorfor|hvordan)\b', re.I)
# at the start only: after a colon these open a quoted statement as often as a teaser ('Kreml: Dette er en provokation')
CURIOUS_OPEN = re.compile(r'^[»«"„“\']?(det ved vi|det betyder|dette er|det her er|det sker der|dette sker|det her sker|'
                          r'nu sker der|hvad|hvem|hvornår|'
                          r'hvilke[nt]?|hvor (?:meget|mange|langt|stor)|så (?:meget|mange)|nu sker det|forklaring|læs)\b', re.I)
CURIOUS_EN = re.compile(r"(?:^|[:–—]\s*|\s-\s+)[»«\"'“]?(Why|How|What|Who|When|Where|Which|Here's|Here’s|Here is|This is|"
                        r"These are|Watch|See|Explained|Everything you need|The reason|You won't believe|Inside)\b")
CURIOUS_ANY = re.compile(r'og det er ikke godt|eksperter? undrer sig|eksperter? er forbløffe\w*|du skal vide|du ikke vidste|'
                         r'du vil ikke tro|ikke hvad du tror|det skal du vide|det vil overraske|'
                         r"you need to know|you won.t believe|what we know|what to know|what you need", re.I)
CURIOUS_END = re.compile(r'(?:…|\.\.\.|:)\s*[»«"”]?\s*$')
EDGES = ' :–—-»«"„“\''
CURIOUS_TAIL = re.compile(r'\s[-–—]\s*(?:video|se video|se|se billederne|billeder|fotos?|live|watch|photos)\s*$|'
                          r'\((?:video|billeder|fotos?|live)\)\s*$', re.I)
# a judgement of Khabar's own in a headline ('Israels egentlige valgtema', 'i virkeligheden'): allowed only as someone's
# statement, 'Who: what' (the reviewers 2026-10-17: an op-ed's thesis read as Khabar's own words)
JUDGED = re.compile(r'\b(egentlig(?:e|t)?|reelle|reelt|i virkeligheden|vejer tungere|i realiteten|den sande|det sande|'
                    r'skjulte dagsorden|afslører sig|viser sit sande)\b', re.I)
SAID_BY = re.compile(r'^(?:[^\s:»«"]+\s+){0,4}[^\s:»«"]+:\s')   # a who of at most five words before the colon
CURIOUS_LABEL = re.compile(r'^\s*(?:video|billeder|fotos?|chok|afsløring|afsløret|watch|photos|revealed|shock)\s*:', re.I)


def curiosity(text):
    """The words that make a headline a curiosity headline, or None for an informative one."""
    t = ' '.join(str(text or '').split())
    if not t:
        return None
    if '?' in t:
        return 'a question'
    for rx in (CURIOUS_LABEL, CURIOUS_DA, CURIOUS_OPEN, CURIOUS_EN, CURIOUS_ANY, CURIOUS_TAIL):
        hit = rx.search(t)
        if hit:
            words = hit.group(0).strip(EDGES)
            return f"'{words}'"
    if CURIOUS_END.search(t):
        return "a cliff-hanger at the end ('…' or ':')"
    return None


def check_headline(text, where, problems):
    """The editor's headline is informative: who did or said what, where – a statement, never a teaser (the owner's
    rule of 2026-10-17); and it keeps the content rules."""
    why = curiosity(text)
    if why:
        problems.append(f'{where}: {why} makes it a curiosity headline – state the news: who did or said what, where '
                        "(a statement, as a news wire writes it; 'Who: what' is fine)")
    check_voice(text, where, problems)
    check_reality(QUOTE.sub('', text or ''), where, problems)   # the source's own words inside »…« are its framing
    plain = QUOTE.sub('', text or '')
    hit = JUDGED.search(plain)
    if hit and not SAID_BY.match(plain):
        problems.append(f"{where}: '{hit.group(0)}' is a judgement – in a headline only as someone's statement ('Who: what'); "
                        'else state what happened')


LOCAL = re.compile(r'\b[A-Za-z]:[\\/]|[\\/]Alpha[\\/]|pCloud|[\\/]Users[\\/]', re.I)
QUOTE = re.compile(r'»([^«»]*)«|«([^«»]*)»|"([^"]*)"|“([^”]*)”')
QUOTE_MAX = 60


def check_voice(text, where, problems):
    for rx, why in VOICE_BANNED:
        hit = rx.search(text or '')
        if hit:
            problems.append(f"{where}: '{hit.group(0)}' – {why}")
    own = QUOTE.sub('', text or '')   # a quotation is the speaker's
    for rx, why in OWN_VOICE:
        hit = rx.search(own)
        if hit:
            problems.append(f"{where}: '{hit.group(0)}' – {why}")
    hit = OCCUPATION.search(own)
    if hit and not ISRAEL_NAMED.search(own):
        problems.append(f"{where}: '{hit.group(0)}' in Israel's place – name Israel ('israelske styrker', 'Israels "
                        "besættelsesstyrker'); the source's word only beside the name (H5)")
    for m in HERO.finditer(own):
        if VIOLENCE.search(own[max(0, m.start() - 80):m.end() + 80]):
            problems.append(f"{where}: '{m.group(0)}' near fighting – no praise of violence in Khabar's own voice (H4)")
            break


def check_reality(text, where, problems):
    hit = REALITY_BANNED.search(text or '')
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' is a reading or judgement word – Khabar's own text is reality only "
                        "(who did or said what, where, when); the movement's readings only weigh the news")


# a reading's own attribution: the app's label says whose and when ('Hizb ut-Tahrirs svar · d/m/åååå')
ATTRIBUTION = re.compile(r'\b[Ii]følge (?:Hizb ut-Tahrir\w*|svar(?:et|ene)?\b|bevægelsen\w*|en række svar)|'
                         r'\bHizb ut-Tahrirs (?:svar|læsning)\w*|\bHizb ut-Tahrir (?:læser|mener|ser|skriver|siger|forventer)\b|'
                         r'\b[Bb]evægelsens svar\w*')


def check_plain(text, where, problems):
    hit = ATTRIBUTION.search(text or '')
    if hit:
        problems.append(f"{where}: '{hit.group(0)}' – write it without the attribution, in plain Danish ('Saudi-Arabien er "
                        "underordnet USA'): the app shows it under 'Hizb ut-Tahrirs svar · d/m/åååå'")


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


# ------------------------------------------------------------------ the front page as a professional page (2026-10-17)
STEM_STOP = {'efter', 'under', 'siger', 'mange', 'flere', 'denne', 'dette', 'imod', 'mellem', 'omkring', 'over', 'ikke',
             'også', 'være', 'blev', 'eller', 'deres', 'sine', 'sin', 'sit', 'hvor', 'mens'}


def stems(text):
    """The words of a text that carry it (four letters and more, their first five), for comparing two texts."""
    return {w[:5] for w in re.findall(r'[^\W\d_]{4,}', (text or '').lower()) if w not in STEM_STOP}


def restates(lede, title, share=0.6):
    """Does the lede's first clause say what the main story's headline says? A standfirst names the day's other
    stories; the main story's headline is right under it (pro-plan 3.2)."""
    first = re.split(r'[,;:–]|\sog\s', lede or '', maxsplit=1)[0]
    a, b = stems(first), stems(title)
    return len(a) >= 3 and len(a & b) / len(a) >= share


def check_lede(lede, top_title, where, problems):
    if lede and top_title and restates(lede, top_title):
        problems.append(f"{where}: its first clause says what Dagens historie's headline says ('{top_title[:70]}') – the "
                        "headline stands right under it: open with the day's other stories, as a standfirst does")


# the media groups that are news outlets (config/feeds.json): an outlet's name before a colon is its report; a
# government's own channel ('official') or the movement's ('bevægelsen') is who speaks, as a person or a state is
NEWS_GROUPS = {'dk', 'west', 'mena', 'il', 'east', 'channel'}


def check_prefix(title, outlets, labels, where, problems):
    """'X: …' where X is a news outlet: only one of the story's own outlets (whose report the claim is). An outlet that
    does not carry the story is no speaker of it (pro-plan 3.4); 'Who: what' with a person, a state or a government's
    channel ('Kreml: …') stays – `labels` holds the news outlets' names only (NEWS_GROUPS)."""
    m = re.match(r'^([^:»«"]{2,40}):\s', title or '')
    if not m:
        return
    x = m.group(1).strip().casefold()
    own = {str(o or '').casefold() for o in outlets}
    if x in labels and x not in own:
        problems.append(f"{where}: '{m.group(1)}:' names an outlet that does not carry this story – write who said or did "
                        'it, or leave the outlet out (the app names the outlet under the headline)')
