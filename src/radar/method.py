"""Khabar's brain in the selection of news: the books' order of importance, applied by the radar before any tokens
are spent (the owner's decision of 2026-10-17: the brain only selects and weighs news – the app shows no analysis).

weigh()   gives a story the heaviest of the 13 tiers its headline shows (config/method.json): 1 the leading state
          with another power in one act (a sign of change in the international situation), 2 the leading state's
          acts, 3 a great power's acts, 4 a change in who controls a state, 5 the major issues (the Middle East
          first), 6 the campaign against the belief and the concepts, 7 instruments in use, 8 an exposure, 9 colonial
          and economic interest, 10 military acts, 11 the rest, 12 a Danish story that cannot be placed
          internationally, 13 weighed down (ceremony, light news). Which states are powers, and in which order,
          follows Hizb ut-Tahrir's newest answers (method.json '_why'): the leading state, then the weakened great
          powers, while Russia (a middle power) and China (a regional power) weigh through their dealings with the
          leading state and through the major issues; Germany and the EU are actors, not powers.
lift()    the rank points a tier adds; a story of a sharp tier also reaches the editor below the taste bar (run.py).
actors()  the states, groups and organisations a headline names (ids as in public/viden/movement-index.json, so a
          story points to the wiki), from method.json 'actors' and the wiki's own Danish names when given."""
import json
import re
from pathlib import Path

from radar.sections import Lexicon as Words

CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'method.json'
ACTOR_KINDS = {'stat', 'magt', 'gruppe', 'organisation'}   # the wiki's kinds that act in a story


class Lexicon(Words):
    """The radar's word lists, plus '*word': the word also inside a Danish compound (*aftale finds militæraftale
    and handelsaftale). A plain substring test runs first, so a list none of whose words is in the text costs
    almost nothing (the radar weighs thousands of headlines a run)."""

    def __init__(self, words):
        inner = [w[1:].rstrip('=') for w in words if w.startswith('*')]
        super().__init__([w[1:] if w.startswith('*') else w for w in words])
        if inner:
            self.patterns.append(re.compile('|'.join(re.escape(w) for w in inner), re.I))
        self.probe = sorted({w.lstrip('*').rstrip('=').lower() for w in words if w.strip('*=')})

    def hits(self, text):
        low = (text or '').lower()
        if not any(w in low for w in self.probe):
            return set()
        return super().hits(text)


class Method:
    def __init__(self, cfg=None, wiki=None):
        cfg = cfg or json.loads(CONFIG.read_text(encoding='utf-8'))
        self.leading = cfg['leading']
        self.great = set(cfg.get('great') or [])
        self.powers = set(cfg['powers'])
        self.ignore = re.compile('|'.join(re.escape(p) for p in cfg['ignore']), re.I) if cfg.get('ignore') else None
        self.act = Lexicon(cfg['act'])
        self.outward = Lexicon(cfg.get('outward') or [])   # acts aimed at other states by their nature (war, sanctions)
        self.tiers = {}
        for t, spec in cfg['tiers'].items():
            lex = self.act if spec.get('words') == 'act' else Lexicon(spec.get('words') or [])
            self.tiers[int(t)] = (spec.get('needs'), lex, Lexicon(spec.get('dk_words') or []))
        self.down = Lexicon(cfg['down']['words'])
        self.lifts = {int(k): v for k, v in (cfg.get('lift') or {}).items()}
        self.bypass_tiers = set(cfg.get('bypass_tiers') or [1, 2, 3, 4, 6])
        self.bypass_per_day = cfg.get('bypass_per_day', 20)
        self.bypass_floor = cfg.get('bypass_floor', 0)
        self.in_issue = {a for ids in (cfg.get('issues') or {}).values() for a in ids}
        names = {k: list(v) for k, v in (cfg.get('actors') or {}).items()}
        for k, v in cfg['powers'].items():
            names.setdefault(k, []).extend(v)
        # the wiki's Danish names, under the wiki's ids (public/viden/begreber-index.json), as whole words: the wiki
        # lists the inflected forms itself, and a bare 'Mali' must not find Malibu
        for k, x in ((wiki or {}).get('items') or {}).items():
            if x.get('kind') in ACTOR_KINDS:
                forms = [n.strip() for n in [x.get('name')] + list(x.get('aliases') or []) if n and len(n.strip()) >= 3]
                names.setdefault(k, []).extend(n if n.endswith('=') else n + '=' for n in forms)
        self.names = {k: Lexicon(sorted(set(v))) for k, v in names.items() if v}

    def text(self, it):
        """The headline in every version the radar has (original, English, Danish), without the 'ignore' phrases."""
        t = ' · '.join(x for x in (it.get('title'), it.get('title_tr'), it.get('title_da')) if x)
        return self.ignore.sub(' ', t) if self.ignore else t

    def actors(self, text):
        return sorted(k for k, lex in self.names.items() if lex.hits(text))

    def weigh(self, it, trivia=False, actors=None):
        """(tier, tags, powers) for one story: tags are every tier the headline shows, the tier the heaviest.
        A power's act counts when the headline also names another state, group or organisation, or when the act is
        aimed outward by its nature (war, sanctions, tariffs, troops): a British court ruling or a deal between two
        companies is no act of a great power."""
        text = self.text(it)
        actors = self.actors(text) if actors is None else actors
        powers = sorted(a for a in actors if a in self.powers)   # a power is an actor with its own weight
        dk = it.get('sec') == 'dk'
        acts = bool(self.act.hits(text))
        outward = acts and bool(self.outward.hits(text))

        def acting(power):
            return outward or bool(set(actors) - {power})

        tags = []
        for t in sorted(self.tiers):
            needs, lex, dk_lex = self.tiers[t]
            if needs == 'issue':
                hit = it.get('sec') == 'me' or bool(self.in_issue & set(actors))
            elif lex is self.act:
                hit = acts
            else:
                hit = bool(lex.hits(text)) or (dk and bool(dk_lex.hits(text)))
            if not hit:
                continue
            if needs == 'leading_and_power' and not (self.leading in powers and len(powers) >= 2):
                continue
            if needs == 'abroad' and dk and not actors:
                continue
            if needs == 'leading' and not (self.leading in powers and acting(self.leading)):
                continue
            if needs == 'great' and not any(p in self.great and acting(p) for p in powers):
                continue
            tags.append(t)
        tier = min(tags) if tags else (12 if dk else 11)
        if trivia or (tier > 4 and self.down.hits(text)):
            tier = 13
        return tier, tags, powers

    def lift(self, tier):
        return self.lifts.get(tier, 0)
