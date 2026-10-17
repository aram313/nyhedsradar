# The owner's rule on speed and smoothness (2026-10-17)

> "Til slut skal vi optimere siden, fjerne alt unødvendigt ekstra fluff og hurtiggøre dens funktioner, så der ikke er
> nogen bottlenecks. Det skal føles smooth. I dag lagger den underligt, når man opdaterer, og animationen kan lagge på
> mobilen. Siderne kan åbne lidt langsommere end ønsket og lagger."

What he notices on his iPhone today:

1. **Refreshing lags oddly** – pulling down to refresh, and the background reload (every couple of minutes and on
   return to the app), stutters and jumps.
2. **Animations can stutter on the phone.**
3. **Pages open more slowly than they should, and lag** – tabs, an opened story, the Udvikling page.

What "done" means:

- **Measured, not guessed.** Before and after, on a phone-like profile (Chrome/Edge with the CPU slowed 4–6× and a
  mobile viewport; real iPhone checks by the owner at the end): time from start to the first useful screen; a tab
  switch; opening a story; opening Udvikling, Analyser and a wiki page; a pull-to-refresh and a background reload
  (no long task over 50 ms while the user scrolls; no layout jump); scrolling a long list and the intro (no dropped
  frames on the main thread – only transform/opacity animated).
- **Usual suspects to check first:** whole lists rebuilt with innerHTML on every reload (patch only what changed, keep
  the scroll position, render off-screen pages lazily); backdrop-filter/blur and large box-shadows on sticky bars
  (expensive on iOS while scrolling); animations of height/top/left instead of transform; many images decoding at once
  (lazy loading, `decoding="async"`, fixed sizes); JSON parsing and search indexing on the main thread at start;
  timers and listeners that keep firing; service-worker strategy (show the cached copy at once, refresh behind it);
  long lists (content-visibility or rendering in steps).
- **Fluff out, never the things the owner chose.** Remove dead code, unused styles, duplicate work and effects that do
  nothing for reading. Keep what he asked for (the intro with the Ruqaa mark – make it cheap; the outlets' initials
  tiles; the long-press admin; Del/Kopiér/Læs; the quiet motion that shows what happened) – make them cheaper instead,
  and list anything removed in plain words.
- **Respect Reduce Motion**, and make every motion short and on the compositor.

## Baseline measured on khabar.nu today (2026-10-17 01:00, a fast Windows PC, no throttling)

| What | Today |
|---|---|
| data.json | 780 KB, 624 stories |
| search.json | 1,479 KB (fetched for search) |
| summaries.json | 153 KB; digest.json 39 KB |
| DOM after start | 12,910 elements, **486 images** (the five tab pages are all drawn, Live lists every story) |
| one `render()` | 27 ms on the PC – roughly 150–250 ms on an iPhone, i.e. a visible hitch on every reload |
| localStorage write of data.json | 5 ms on the PC (synchronous; several times that on a phone), done on every changed reload |

Code that does this (public/app.js on main): `load()` fetches data, digest and summaries one after another (serial
awaits) and then calls `render({fresh: true})`, which redraws the page in view and its neighbours (`drawSoon`) with
innerHTML; `setInterval(load, 120000)` repeats it every two minutes while the user reads; `store.set('lastData', data)`
writes the whole data file to localStorage on the main thread; `JSON.stringify` compares the whole summaries and
titles objects on each reload; `.story.enter` animates every row in with a staggered delay; three sticky surfaces use
`backdrop-filter: saturate(170%) blur(20px)` (top bar, tab bar, sheet); every thumbnail carries
`filter: grayscale(1) contrast(1.06)` with a `transition: filter .4s`; the pull-to-refresh moves the whole page with
transform (fine) but the reload's re-render lands while it settles.
