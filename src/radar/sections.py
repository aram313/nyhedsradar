"""Which part of the app a story belongs in (Danmark, Mellemøsten, Verden) and whether it is about the
group's core subjects or light news. Words come from config/sections.json; stories the words cannot place
take the section of the most similar stories that the words did place."""
import re

import numpy as np

ARABIC = re.compile(r'[؀-ۿ]')
# words that open many headlines without saying who: never bold on their own
PLAIN = {'danmark', 'dansk', 'danske', 'danskere', 'denmark', 'danish', 'danes'}
NOT_A_SPEAKER = re.compile(r'^(?:analyse|analysis|kommentar|leder|opinion|debat|interview|live|video|watch|breaking|'
                           r'update|opdatering|nyt|se|explainer|guide|quiz|podcast)\b', re.I)
CAPITALISED = re.compile(r"^[A-ZÆØÅÄÖÜ][\w'’.-]*$")
# capitalised small words that never belong to a name next to them
SMALL = {'a', 'an', 'the', 'en', 'et', 'den', 'det', 'de', 'i', 'in', 'on', 'at', 'to', 'for', 'med', 'til', 'om', 'på',
         'af', 'og', 'and', 'efter', 'after', 'som', 'han', 'hun', 'da', 'når', 'nu', 'her'}
# English headlines in Title Case capitalise these; sentence case never does (outside the first word)
TITLE_CASE = re.compile(r'(?<!^)\b(?:With|From|Into|After|Over|About|Says|Will|That|This|Amid|Against|Under|Their)\b')


class Lexicon:
    """A word list compiled to three patterns: case-insensitive word starts, case-sensitive words (party
    names such as 'Venstre'), and Arabic words, which match anywhere because prefixes attach to them."""

    def __init__(self, words):
        ci, cs, anywhere = [], [], []
        for w in words:
            whole = w.endswith('=')
            w = w.rstrip('=')
            if ARABIC.search(w):
                anywhere.append(re.escape(w))
                continue
            pat = r'(?<!\w)' + re.escape(w) + (r'(?!\w)' if whole else '')
            (cs if any(c.isupper() for c in w) else ci).append(pat)
        self.patterns = [re.compile('|'.join(p), flags) for p, flags in
                         ((ci, re.I), (cs, 0), (anywhere, 0)) if p]

    def hits(self, text):
        return {m.group(0).lower() for rx in self.patterns for m in rx.finditer(text or '')}


class Sections:
    def __init__(self, cfg):
        self.names = cfg['names']
        self.keys = list(self.names)
        self.lex = {k: Lexicon(cfg['keywords'][k]) for k in self.keys}
        self.core = Lexicon(cfg.get('core', []))
        self.core_dk = Lexicon(cfg.get('core_dk', []))
        self.trivia = Lexicon(cfg.get('trivia', []))
        self.local = Lexicon(cfg.get('local', []))

    def signals(self, item):
        """Word evidence for one article: title words count double, summary words once."""
        title, summary = item['title'], (item.get('summary') or '')[:400]
        out = {'named': False}   # does the headline itself name a place, party or actor?
        for k in self.keys:
            th = self.lex[k].hits(title)
            out[k] = 2 * len(th) + len(self.lex[k].hits(summary) - th)
            out['named'] = out['named'] or bool(th)
        out['core'] = bool(self.core.hits(title)) * 2 + bool(self.core.hits(summary))
        out['core_dk'] = bool(self.core_dk.hits(title)) * 2 + bool(self.core_dk.hits(summary))
        out['trivia'] = bool(self.trivia.hits(title))
        out['local'] = bool(self.local.hits(title))
        return out

    def keywords(self, title, most=3):
        """The words that say who and where in a headline, for the app to set in bold: the speaker of a
        'Who: what' headline, and the places, parties, people and organisations of the section word lists,
        widened to whole words and to the capitalised words next to them (Pia Olsen Dyhr, Gaza City)."""
        title = title or ''
        title_case = bool(TITLE_CASE.search(title))
        spans = []
        m = re.match(r'^([^:]{2,60}):\s+\S', title)
        who = m.group(1).split() if m else []
        if (who and len(who) <= 5 and not NOT_A_SPEAKER.match(m.group(1))   # 'Yaqoub Ali: …', 'Kreml: …'
                and all(CAPITALISED.match(w) or w.lower() in ('og', 'and', 'of', 'al', 'bin', 'el') for w in who)):
            spans.append((0, len(m.group(1)), 2))
        hits = []
        for k in self.keys:
            for rx in self.lex[k].patterns:
                for hit in rx.finditer(title):
                    a, b = hit.span()
                    while b < len(title) and (title[b].isalnum() or title[b] == '-'):
                        b += 1
                    hits.append((a, b))
        starts = {a for a, _ in hits}
        for a, b in hits:
            if not title_case:   # the capitalised words around a name belong to it (not the next name)
                a, b = self._widen(title, a, b, starts)
            if title[a:b].lower() not in PLAIN:
                spans.append((a, b, 1 + (' ' in title[a:b])))
        spans.sort(key=lambda s: (s[0], -s[1]))
        merged = []
        for a, b, w in spans:
            if merged and a < merged[-1][1]:
                pa, pb, pw = merged[-1]
                merged[-1] = (pa, max(pb, b), max(pw, w))
                continue
            merged.append((a, b, w))
        out, seen = [], set()
        for a, b, w in sorted(merged, key=lambda s: (-s[2], s[0])):   # speakers and longer names first
            if title[a:b].lower() not in seen and len(out) < most:
                seen.add(title[a:b].lower())
                out.append((a, b))
        return [title[a:b] for a, b in sorted(out)]

    @staticmethod
    def _widen(title, a, b, starts, most=4):
        def name_word(w):
            return CAPITALISED.match(w) and w.lower().strip('.') not in SMALL
        while len(title[a:b].split()) < most:
            m = re.search(r"([\w'’-]+)\s+$", title[:a])
            if not m or not name_word(m.group(1)) or m.start(1) in starts:
                break
            a = m.start(1)
        while len(title[a:b].split()) < most:
            m = re.match(r"\s+([\w'’-]+)", title[b:])
            if not m or not name_word(m.group(1)) or b + m.start(1) in starts:
                break
            b += m.end(1)
        return a, b

    def place(self, stories, emb, hint):
        """stories: list of member lists (dicts with 'source', 'lang', 'sig'); emb: one vector per story.
        hint: source -> section hint from feeds.json ('dk', 'abroad', 'me', 'world').
        Returns one list of sections per story, strongest first (empty never: everything gets a home)."""
        scores = []
        for members in stories:
            sc = {k: 0.0 for k in self.keys}
            for m in members:
                for k in self.keys:
                    sc[k] += min(m['sig'][k], 6)   # one wordy summary must not outvote the other outlets
                h = hint.get(m['source'])
                if h == 'dk':
                    sc['dk'] += 2
                elif h == 'abroad':
                    sc['dk'] -= 3
                elif h in sc:
                    sc[h] += 1
            scores.append({k: max(v, 0.0) for k, v in sc.items()})
        placed = [self._pick(sc) for sc in scores]

        # stories without telling words: take the section of the closest stories the words did place
        known = [i for i, p in enumerate(placed) if p and max(scores[i].values()) >= 2]
        if known:
            ref = emb[known]
            for i, p in enumerate(placed):
                if p and max(scores[i].values()) >= 2:
                    continue
                if self._home_debate(stories[i], hint):
                    placed[i] = ['dk']
                    continue
                sims = ref @ emb[i]
                top = np.argsort(-sims)[:7]
                vote = {}
                for j in top:
                    if sims[j] >= 0.5:
                        sec = placed[known[j]][0]
                        vote[sec] = vote.get(sec, 0) + float(sims[j])
                lead = stories[i][0]
                if lead.get('lang') == 'da' and hint.get(lead['source']) != 'abroad':
                    vote['dk'] = vote.get('dk', 0) + 0.8   # Danish news without telling words is mostly domestic
                else:
                    vote.pop('dk', None)   # a foreign-language story is about Denmark only if it says so
                if vote and max(vote.values()) >= 1.0:
                    placed[i] = [max(vote, key=vote.get)]
        for i, p in enumerate(placed):
            if not p:   # last resort: where the language and the source usually point
                lead = stories[i][0]
                h = hint.get(lead['source'])
                placed[i] = ['dk' if lead.get('lang') == 'da' and h != 'abroad'
                             else 'me' if lead.get('lang') in ('ar', 'tr') or h == 'me' else 'world']
        return placed

    @staticmethod
    def _home_debate(members, hint):
        """A Danish article about Islam and Muslims, immigration or Danish politics that names no other country is
        Danish news, however much it resembles stories from abroad (a BT debate piece on Muslims in Denmark once
        landed in Mellemøsten because its nearest neighbours were Middle East stories about Islam)."""
        return (all(m.get('lang') == 'da' and hint.get(m['source']) != 'abroad' for m in members)
                and max(m['sig']['core_dk'] for m in members) >= 2)

    def _pick(self, sc):
        top = max(sc.values())
        if top < 1:
            return []
        return sorted((k for k in self.keys if sc[k] >= max(2, 0.5 * top)), key=lambda k: -sc[k]) or \
            [max(sc, key=sc.get)]
