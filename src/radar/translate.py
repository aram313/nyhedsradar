"""Offline translation of Arabic and Turkish headlines into English.

Uses the free Argos Translate models (OPUS-MT, CTranslate2 format) directly, without the
argostranslate package, which would pull in several gigabytes of PyTorch. Nothing is sent
to an online service."""
import io
import urllib.request
import zipfile
from pathlib import Path

MODELS = {
    'ar': 'https://argos-net.com/v1/translate-ar_en-1_0.argosmodel',
    'tr': 'https://argos-net.com/v1/translate-tr_en-1_5.argosmodel',
}


class Translator:
    def __init__(self, cache_dir):
        self.dir = Path(cache_dir) / 'argos'
        self.loaded = {}

    def _load(self, lang):
        if lang in self.loaded:
            return self.loaded[lang]
        import ctranslate2
        import sentencepiece
        target = self.dir / lang
        if not (target / 'ready').exists():
            req = urllib.request.Request(MODELS[lang], headers={'User-Agent': 'Mozilla/5.0 (Nyhedsradar)'})
            with urllib.request.urlopen(req, timeout=180) as r:
                zipfile.ZipFile(io.BytesIO(r.read())).extractall(target)
            (target / 'ready').write_text('ok')
        root = next(p.parent for p in target.rglob('sentencepiece.model'))
        model = (ctranslate2.Translator(str(root / 'model'), device='cpu', inter_threads=2),
                 sentencepiece.SentencePieceProcessor(model_file=str(root / 'sentencepiece.model')))
        self.loaded[lang] = model
        return model

    def __call__(self, texts, lang):
        """Translate a list of short texts. Returns None for each text that could not be translated."""
        if lang not in MODELS or not texts:
            return [None] * len(texts)
        try:
            tr, sp = self._load(lang)
            toks = [sp.encode(t[:600], out_type=str) for t in texts]
            res = tr.translate_batch(toks, beam_size=2, max_decoding_length=200)
            return [sp.decode(r.hypotheses[0]).replace('▁', ' ').strip() for r in res]
        except Exception as e:  # translation is a bonus; the radar must keep running
            print(f'translate {lang}: failed: {type(e).__name__}: {e}')
            return [None] * len(texts)
