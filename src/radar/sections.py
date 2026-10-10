"""Which part of the app a story belongs in (Danmark, Mellemøsten, Verden) and whether it is about the
group's core subjects or light news. Words come from config/sections.json; stories the words cannot place
take the section of the most similar stories that the words did place."""
import re

import numpy as np

ARABIC = re.compile(r'[؀-ۿ]')


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

    def _pick(self, sc):
        top = max(sc.values())
        if top < 1:
            return []
        return sorted((k for k in self.keys if sc[k] >= max(2, 0.5 * top)), key=lambda k: -sc[k]) or \
            [max(sc, key=sc.get)]
