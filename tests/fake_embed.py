"""A tiny stand-in for the real language model so the pipeline can be tested offline.
Each word is hashed into one of 384 dimensions; texts sharing words end up close."""
import re
import zlib

import numpy as np


class FakeEmbedder:
    def __init__(self, model=None):
        pass

    def __call__(self, texts):
        m = np.zeros((len(texts), 384), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r'\w{3,}', t.lower()):
                m[i, zlib.crc32(w.encode()) % 384] += 1
        return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)
