"""Every text colour of the app's eight palettes is readable on the surfaces it sits on (pro-plan 2.4, WCAG AA 4.5:1):
the page (--bg), a panel or an opened story (--fill), a selected segment (--seg-on), and the movement's ochre tint
(--ht-bg) for its own text colours. A palette change cannot slip below."""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'public' / 'style.css').read_text(encoding='utf-8')


def palettes():
    """name -> {token: '#rrggbb'}: the one light look and the one dark (since 17/10 the owner keeps only these two)."""
    base = dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{6})', re.search(r':root \{ color-scheme: light;([^}]*)\}', CSS).group(1)))
    ht = dict(re.findall(r'(--ht-[\w-]+):\s*(#[0-9a-fA-F]{6})', re.search(r':root \{ --serif:[^}]*\}', CSS).group(0)))
    dark_ht = dict(re.findall(r'(--ht-[\w-]+):\s*(#[0-9a-fA-F]{6})', re.search(r':root\[data-theme="dark"\] \{ --ht-bg[^}]*\}', CSS).group(0)))
    notion = dict(re.findall(r'(--[\w-]+):\s*(#[0-9a-fA-F]{6})', re.search(r':root\[data-theme="dark"\] \{ color-scheme: dark;([^}]*)\}', CSS).group(1)))
    return {'daempet': {**base, **ht}, 'notion': {**notion, **dark_ht}}


def lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_two_palettes_are_read():
    assert set(palettes()) == {'daempet', 'notion'}
    assert 'data-tone=' not in CSS and 'data-dark=' not in CSS        # the other palettes are gone


def test_every_text_colour_is_readable_on_its_surfaces():
    low = []
    for name, p in palettes().items():
        for fg in ('--text', '--text-2', '--text-3', '--red'):
            for bg in ('--bg', '--fill'):
                if ratio(p[fg], p[bg]) < 4.5:
                    low.append(f'{name}: {fg} on {bg} {ratio(p[fg], p[bg]):.2f}')
        for fg in ('--ht-text', '--ht-text-2', '--ht-text-3'):
            if ratio(p[fg], p['--ht-bg']) < 4.5:
                low.append(f'{name}: {fg} on --ht-bg {ratio(p[fg], p["--ht-bg"]):.2f}')
    assert not low, low
