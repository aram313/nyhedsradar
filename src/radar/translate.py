"""Offline translation: Arabic and Turkish headlines into English, English into Danish.

Uses the free Argos Translate models (OPUS-MT, CTranslate2 format) directly, without the
argostranslate package, which would pull in several gigabytes of PyTorch. Nothing is sent
to an online service. Packages come with one of two word splitters: a SentencePiece model
(Arabic, Turkish) or Moses tokenisation plus subword BPE codes (English-Danish)."""
import html
import io
import re
import urllib.request
import zipfile
from pathlib import Path

MODELS = {
    ('ar', 'en'): 'https://argos-net.com/v1/translate-ar_en-1_0.argosmodel',
    ('tr', 'en'): 'https://argos-net.com/v1/translate-tr_en-1_5.argosmodel',
    ('en', 'da'): 'https://argos-net.com/v1/translate-en_da-1_9.argosmodel',
}


def tidy(text):
    """Clean model output: entities, unknown-token marks, doubled spaces."""
    text = html.unescape(html.unescape(text.replace('▁', ' ')))
    text = re.sub(r'\s*⁇\s*', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return re.sub(r'\s{2,}', ' ', text).strip(' :-–')


class SentencePieceSplitter:
    def __init__(self, path):
        import sentencepiece
        self.sp = sentencepiece.SentencePieceProcessor(model_file=str(path))

    def encode(self, text):
        return self.sp.encode(text, out_type=str)

    def decode(self, tokens):
        return self.sp.decode(tokens)


class MosesBpeSplitter:
    def __init__(self, codes, src, tgt):
        from sacremoses import MosesDetokenizer, MosesTokenizer
        from subword_nmt.apply_bpe import BPE
        self.tok, self.detok = MosesTokenizer(lang=src), MosesDetokenizer(lang=tgt)
        with open(codes, encoding='utf-8') as f:
            self.bpe = BPE(f)

    def encode(self, text):
        words = self.tok.tokenize(text, aggressive_dash_splits=True, escape=True)
        return self.bpe.segment_tokens(words)

    def decode(self, tokens):
        words = ' '.join(tokens).replace('@@ ', '').removesuffix('@@').split()
        return self.detok.detokenize(words, unescape=True)


class Translator:
    def __init__(self, cache_dir):
        self.dir = Path(cache_dir) / 'argos'
        self.loaded = {}

    def _load(self, pair):
        if pair in self.loaded:
            return self.loaded[pair]
        import ctranslate2
        target = self.dir / f'{pair[0]}_{pair[1]}'
        if not (target / 'ready').exists():
            req = urllib.request.Request(MODELS[pair], headers={'User-Agent': 'Mozilla/5.0 (Nyhedsradar)'})
            with urllib.request.urlopen(req, timeout=180) as r:
                zipfile.ZipFile(io.BytesIO(r.read())).extractall(target)
            (target / 'ready').write_text('ok')
        root = next(p.parent.parent for p in target.rglob('model.bin'))
        if (root / 'sentencepiece.model').exists():
            splitter = SentencePieceSplitter(root / 'sentencepiece.model')
        else:
            splitter = MosesBpeSplitter(root / 'bpe.model', *pair)
        model = (ctranslate2.Translator(str(root / 'model'), device='cpu', inter_threads=2), splitter)
        self.loaded[pair] = model
        return model

    def __call__(self, texts, lang, to='en'):
        """Translate a list of short texts. Returns None for each text that could not be translated."""
        pair = (lang, to)
        if pair not in MODELS or not texts:
            return [None] * len(texts)
        try:
            tr, splitter = self._load(pair)
            # separators and emoji are unknown to the model and come back as '⁇'
            prep = [re.sub(r'\s+', ' ', re.sub(r'[|•⭕🔴⚡️🆘📌‼️⁉️]+', ' ', t[:600])).strip(' :-–') for t in texts]
            toks = [splitter.encode(t) for t in prep]
            res = tr.translate_batch(toks, beam_size=2, max_decoding_length=200)
            return [tidy(splitter.decode(r.hypotheses[0])) if t else '' for r, t in zip(res, prep)]
        except Exception as e:  # translation is a bonus; the radar must keep running
            print(f'translate {lang}->{to}: failed: {type(e).__name__}: {e}')
            return [None] * len(texts)
