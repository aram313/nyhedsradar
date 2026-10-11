# App icon and mark

The mark is خبر in Aref Ruqaa (the reed-pen hand of the intro animation), written as ح with a red dot over it.
The app icons are white on near-black (#111) with the red dot; the Android status-bar badge is all white on transparent.
The header logo in `public/index.html` is the same mark as an inline SVG (font loaded from Google Fonts, text subset).

The PNGs are drawn in the browser, because they need the font:

1. `py scripts/icon/save_server.py public/icons` (keeps running; writes the PNGs it receives)
2. `py -m http.server 8765 --directory public` and copy `scripts/icon/make-icon.html` to `public/icon-export.html`
3. Open http://localhost:8765/icon-export.html (add `?preview` to only look). The title ends with `DONE` when
   icon-512/192/180, maskable-512/192 and badge-96 are saved.
