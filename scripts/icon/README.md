# App icon ("Varmt papir")

The icon is drawn in the browser, because it needs the Lalezar font and a paper grain.

1. `py scripts/icon/save_server.py public/icons` (keeps running; writes the PNGs it receives)
2. `py -m http.server 8765 --directory public` and copy `scripts/icon/make-icon.html` to `public/icon-export.html`
3. Open http://localhost:8765/icon-export.html. The title ends with `DONE` when icon-512/192/180.png are saved.
