// Khabar – phone app. Reads data.json (stories with their section, rank and coverage, written by the radar
// every few minutes) and digest.json (the Claude editor's overview at 7 and 17). Shows a front page plus one
// tab per section – Danmark, Mellemøsten, Verden – and a search over everything the radar has read. Plain JS.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const wait = ms => new Promise(r => setTimeout(r, ms));

const SECTIONS = { dk: 'Danmark', me: 'Mellemøsten', world: 'Verden' };
const GROUPS = { dk: 'Danske medier', west: 'Vestlige medier', mena: 'Arabiske og muslimske medier', il: 'Israelske medier',
  channel: 'Kanaler på Telegram og YouTube' };
const GROUP_SHORT = { dk: ['dansk', 'danske'], west: ['vestligt', 'vestlige'], mena: ['arabisk/muslimsk', 'arabiske/muslimske'],
  il: ['israelsk', 'israelske'], channel: ['kanal', 'kanaler'] };
const GROUP_ORDER = ['dk', 'west', 'mena', 'il', 'channel'];
const LANG = { ar: 'arabisk', tr: 'tyrkisk', en: 'engelsk', da: 'dansk' };

let data = store.get('lastData', null);
let digest = store.get('lastDigest', null);
let tab = 'home', query = '';
let shared = store.get('shared', null) || store.get('copied', {});   // id -> {at, title, link, source}
let foreignMode = store.get('foreignMode', 'translate');                 // translate | hide | original
let danish = store.get('danish', false);                                 // show and share in Danish
let digestOpen = false;
const expanded = new Set();
const params = new URLSearchParams(location.search);
let focusId = params.get('item');
if (params.get('digest') === '1') digestOpen = true;
let lastSeen = store.get('lastSeen', 0);                                 // stories found later get a small dot
let shownIds = new Set();
const scrollPos = {};                                                    // each tab remembers where you were
let searchIndex = null, searchState = 'idle';
const readSent = new Set(store.get('readSent', []));

// ---------------------------------------------------------------- silent learning (no buttons)
// Sharing or copying a story tells the radar "more like this"; opening one says it more quietly.
// Only the public headline travels, through the private relay topic.
function learnFrom(i, kind) {
  if (!CFG.feedbackTopic) return;
  if (kind === 'read') {
    if (readSent.has(i.id)) return;
    readSent.add(i.id); store.set('readSent', [...readSent].slice(-300));
  }
  fetch('https://ntfy.sh/' + CFG.feedbackTopic, {
    method: 'POST', body: JSON.stringify({ kind, id: i.id, title: i.origTitle || i.title, summary: (i.origSummary || i.summary || '').slice(0, 220) }),
  }).catch(() => { /* offline: nothing lost but a hint */ });
}

// ---------------------------------------------------------------- time
const clock = iso => new Date(iso).toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' });
function ago(iso) {
  const m = (Date.now() - new Date(iso)) / 60000, d = new Date(iso), y = new Date();
  y.setDate(y.getDate() - 1);
  if (m < 1) return 'nu';
  if (m < 60) return Math.round(m) + ' min';
  if (d.toDateString() === new Date().toDateString()) return Math.round(m / 60) + ' t';
  if (d.toDateString() === y.toDateString()) return 'i går ' + clock(iso);
  return d.toLocaleDateString('da-DK', { weekday: 'short' }) + ' ' + clock(iso);
}
function dayLabel(iso) {
  const d = new Date(iso), t = new Date(), y = new Date(t);
  y.setDate(t.getDate() - 1);
  if (d.toDateString() === t.toDateString()) return 'I dag';
  if (d.toDateString() === y.toDateString()) return 'I går';
  return d.toLocaleDateString('da-DK', { weekday: 'long', day: 'numeric', month: 'long' });
}
const when = i => new Date(i.published || i.found).getTime();
const hours = i => Math.max(0, (Date.now() - when(i)) / 3600e3);
const num = n => Number(n || 0).toLocaleString('da-DK');

// ---------------------------------------------------------------- data
const bust = url => url + (url.includes('?') ? '&' : '?') + 't=' + Date.now();
let busy = 0;
async function load(manual) {
  busy++; document.body.classList.add('loading');
  let changed = false;
  try {
    const r = await fetch(bust(CFG.dataUrl), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    const fresh = await r.json();
    changed = !data || fresh.updated !== data.updated;
    data = fresh;
    store.set('lastData', data);
  } catch (e) {
    if (manual) toast('Kunne ikke hente nye nyheder', false);
  }
  if (CFG.digestUrl) {
    try {
      const r = await fetch(bust(CFG.digestUrl), { cache: 'no-store' });
      if (r.ok) {
        const d = await r.json();
        changed = changed || !digest || d.created !== digest.created;
        digest = d; store.set('lastDigest', digest);
      }
    } catch { /* keep the last overview */ }
  }
  if (--busy === 0) document.body.classList.remove('loading');
  if (changed || manual) render({ fresh: true }); else renderHeader();
}

// ---------------------------------------------------------------- what a story shows
// Danish/English as-is; other languages translated unless the user wants the original;
// with the Danish setting on, everything that has a Danish version is shown in Danish.
// channel posts open with alarm emoji and tags ('⚡️', 'Breaking |', 'عاجل |'); a headline needs none
const TAGS = new RegExp('^(?:[\\u2190-\\u2bff\\u{1f000}-\\u{1faff}\\ufe0f\\u200d\\s]'
  + '|(?:breaking|urgent|watch|video|update|just in|عاجل|متابعة|فيديو)\\s*[|:\\-–]\\s*'
  + '|(?:gaza|west bank|lebanon|syria|yemen|iran|israeli|hebrew|palestinian) sources\\s+(?!say|said|report|told|claim))+', 'iu');
const tidy = t => (t || '').replace(TAGS, '') || t;
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary };
  if (i.foreign && foreignMode !== 'original' && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', from: i.lang, to: 'en' };
  }
  if (danish && i.title_da && !(i.foreign && foreignMode === 'original')) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', from: d.from || i.lang, to: 'da' };
  }
  d.title = tidy(d.title);
  return d;
}
const readable = t => !/[؀-ۿ]/.test(t || '');
const visible = i => !i.foreign || foreignMode === 'original' || (foreignMode === 'translate' && i.title_tr);
const secOf = i => i.sec || (i.lang === 'da' ? 'dk' : 'world');
const inSection = (i, sec) => secOf(i) === sec || (i.secs || []).includes(sec);
const rankOf = i => i.rank ?? i.pct ?? 0;
const hot = i => rankOf(i) - 1.5 * Math.min(48, hours(i)) - (i.confirmed === 0 ? 6 : 0);   // strong, recent, confirmed first
// the best n stories, at most one per source, so one busy channel never fills a whole block
function pick(list, n) {
  const out = [], seen = new Set(), rest = [];
  for (const i of [...list].sort((a, b) => hot(b) - hot(a))) {
    if (out.length === n) break;
    if (seen.has(i.source)) { rest.push(i); continue; }
    seen.add(i.source); out.push(i);
  }
  return out.concat(rest.slice(0, n - out.length));
}
const isNew = i => lastSeen && i.found && new Date(i.found).getTime() > lastSeen && !shared[i.id];
let cache = null;
function stories() {
  if (!data) return [];
  if (cache && cache.src === data && cache.mode === foreignMode + danish) return cache.list;
  const list = data.items.filter(visible).map(display);
  cache = { src: data, mode: foreignMode + danish, list, byId: new Map(list.map(i => [i.id, i])) };
  return list;
}
const find = id => (stories(), cache && cache.byId.get(id));

function shareText(d) {
  const first = (d.summary || '').split(/(?<=[.!?])\s/)[0].replace(/\s*…$/, '');
  return `*${d.title}*\n${first ? first + '\n' : ''}${d.link}`;
}

// ---------------------------------------------------------------- render: one story
function meta(i) {
  const m = [];
  if (i.big) m.push('<span class="big">Stor historie</span>');
  m.push(`<span class="src">${esc(i.source)}</span>`, `<span>${ago(i.published || i.found)}</span>`);
  if (i.outlets >= 2) m.push(`<span>${i.outlets} medier</span>`);
  if (i.confirmed === 0) m.push('<span class="warn">ubekræftet</span>');
  if (i.to) m.push('<span>oversat</span>');
  if (shared[i.id]) m.push('<span>delt</span>');
  return m.join('');
}
function story(i, n, opts = {}) {
  const open = expanded.has(i.id);
  const cls = ['story', i.important && 'imp', open && 'open', isNew(i) && 'new', opts.enter && n < 12 && 'enter',
    opts.fresh && shownIds.size && !shownIds.has(i.id) && 'fresh'].filter(Boolean).join(' ');
  return `<article class="${cls}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" style="--i:${n}">
    <button class="row" data-toggle aria-expanded="${open}"><span class="h" dir="auto">${esc(i.title)}</span><span class="m">${meta(i)}</span></button>
    <div class="x"><div><div class="x-in">${open ? detail(i) : ''}</div></div></div></article>`;
}
function detail(i) {
  const note = i.to ? `<p class="tr-note">Maskinoversat fra ${LANG[i.from] || i.from}</p>` : '';
  return `${i.summary ? `<p class="sum" dir="auto">${esc(i.summary)}</p>` : ''}${note}
    <div class="acts">
      <a class="act primary" href="${esc(i.link)}" target="_blank" rel="noopener" data-read><svg><use href="#i-open"/></svg>Læs</a>
      <button class="act" data-share><svg><use href="#i-share"/></svg>Del</button>
      <button class="act" data-copy><svg><use href="#i-copy"/></svg>Kopiér</button>
    </div>${coverage(i)}`;
}
function coverSummary(cover) {
  return GROUP_ORDER.filter(g => cover && cover[g]).map(g => `${cover[g]} ${GROUP_SHORT[g][cover[g] === 1 ? 0 : 1]}`).join(' · ');
}
// who else carries the story, grouped by kind of media, so different framings sit side by side
function coverage(i) {
  const also = i.also || [];
  if (!also.length) return '';
  const by = {};
  also.forEach(a => (by[a.group || 'west'] ||= []).push(a));
  const rows = GROUP_ORDER.filter(g => by[g]).map(g => `<div class="cov-g">${GROUPS[g]}</div>` + by[g].map(a => {
    const title = foreignMode === 'original' || readable(a.title) ? `<span dir="auto">${esc(a.title)}</span>`
      : `<i>overskrift på ${LANG[a.lang] || 'arabisk'}</i>`;
    return `<a href="${esc(a.link)}" target="_blank" rel="noopener"><b>${esc(a.source)}</b>${title}</a>`;
  }).join('')).join('');
  const sum = coverSummary(i.cover);
  return `<div class="cov"><div class="cov-h">Dækning · ${i.outlets} medier</div>${sum ? `<div class="cov-sum">${sum}</div>` : ''}${rows}</div>`;
}

// ---------------------------------------------------------------- render: the editor's overview
function digestCard() {
  if (!digest || !digest.created || Date.now() - new Date(digest.created) > 14 * 3600e3) return '';
  const items = digest.items || [];
  const shownN = digestOpen ? items.length : Math.min(4, items.length);
  return `<section class="digest" id="digest">
    <div class="digest-h"><b>Overblik${digest.period ? ' · ' + esc(digest.period) : ''}</b><span>Claude · kl. ${clock(digest.created)}</span></div>
    ${digest.intro ? `<p class="intro">${esc(digest.intro)}</p>` : ''}
    <ol>${items.slice(0, shownN).map(x => `<li><a href="${esc(x.link)}" target="_blank" rel="noopener"><div><b>${esc(x.headline)}</b>${digestOpen && x.text ? `<small>${esc(x.text)}</small>` : ''}<em>${SECTIONS[x.section] ? SECTIONS[x.section] + ' · ' : ''}${esc(x.source || '')}</em></div></a></li>`).join('')}</ol>
    <div class="acts">
      <button class="act" data-digest-toggle>${digestOpen ? 'Kortere' : items.length > 4 ? `Alle ${items.length} med tekst` : 'Med tekst'}</button>
      <button class="act primary" data-digest-share><svg><use href="#i-share"/></svg>Del overblik</button>
    </div></section>`;
}
function digestText() {
  return digest.whatsapp || (digest.items || []).map(x => `*${x.headline}*\n${x.text || ''}\n${x.link}`).join('\n\n');
}

// ---------------------------------------------------------------- render: pages
function home(all, opts) {
  const used = new Set();
  let html = '', n = 0;
  // breaking: big stories of the last hours, and very fresh important ones
  const now = all.filter(i => (i.big && hours(i) < 4) || (i.important && hours(i) < 1.5)).sort((a, b) => hot(b) - hot(a)).slice(0, 3);
  if (now.length) {
    html += '<div class="label now">Netop nu</div>' + now.map(i => story(i, n++, opts)).join('');
    now.forEach(i => used.add(i.id));
  }
  html += digestCard();
  for (const sec of Object.keys(SECTIONS)) {
    const list = all.filter(i => inSection(i, sec));
    const top = pick(list.filter(i => secOf(i) === sec && !used.has(i.id) && hours(i) < 24), 4);
    top.forEach(i => used.add(i.id));
    html += `<section class="block"><div class="block-h"><h2>${SECTIONS[sec]}</h2>`
      + `<button class="more" data-go="${sec}">Alle ${list.length}<svg><use href="#i-chev"/></svg></button></div>`
      + (top.map(i => story(i, n++, opts)).join('') || '<p class="empty">Intet nyt her det seneste døgn.</p>') + '</section>';
  }
  const src = Object.keys(data.sources || {}).length;
  html += `<p class="foot">Khabar har læst ${num(data.scanned_24h)} nyheder fra ${src} kilder det seneste døgn<br>og valgt ${all.length} ud til dig.</p>`;
  return html;
}
function sectionPage(sec, all, opts) {
  const list = all.filter(i => inSection(i, sec));
  if (!list.length) return '<div class="empty">Ingen historier her endnu.</div>';
  const top = pick(list.filter(i => hours(i) < 24), 5);
  const ids = new Set(top.map(i => i.id));
  let html = top.length ? '<div class="label">Vigtigst lige nu</div>' + top.map((i, n) => story(i, n, opts)).join('') : '';
  let last = '', n = top.length;
  list.filter(i => !ids.has(i.id)).sort((a, b) => when(b) - when(a)).forEach(i => {
    const d = dayLabel(i.published || i.found);
    if (d !== last) { html += `<div class="label">${d}</div>`; last = d; }
    html += story(i, n++, opts);
  });
  return html;
}
function mark(text, terms) {
  let out = esc(text);
  for (const t of terms) if (t.length > 1) out = out.replace(new RegExp(esc(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), m => `<mark>${m}</mark>`);
  return out;
}
function searchPage(all) {
  const q = query.trim().toLowerCase();
  const total = searchIndex ? searchIndex.items.length : (data.scanned_24h || 0);
  if (!q) return `<div class="empty">Søg i alle ${num(total)} nyheder, Khabar har læst de seneste to døgn – også dem, der ikke kom på listerne.</div>`;
  const terms = q.split(/\s+/).filter(Boolean);
  const hit = t => terms.every(w => t.includes(w));
  const inApp = all.filter(i => hit(`${i.title} ${i.summary || ''} ${i.source} ${i.origTitle || ''}`.toLowerCase())).sort((a, b) => when(b) - when(a));
  let html = inApp.length ? `<div class="label">På Khabar · ${inApp.length}</div>` + inApp.slice(0, 40).map((i, n) => story(i, n)).join('') : '';
  if (searchIndex) {
    const onApp = new Set(data.items.map(i => i.id));
    const others = searchIndex.items.filter(x => !onApp.has(x.i) && hit(`${x.t} ${x.s}`.toLowerCase()));
    if (others.length) html += `<div class="label">Andre nyheder · ${others.length}</div>` + others.slice(0, 60).map(x =>
      `<a class="hit" href="${esc(x.u)}" target="_blank" rel="noopener"><b dir="auto">${mark(x.t, terms)}</b><span>${esc(x.s)} · ${ago(x.p)}</span></a>`).join('');
  } else {
    html += `<p class="foot">${searchState === 'error' ? 'Kunne ikke hente alle nyheder – viser kun dem på Khabar.' : 'Henter alle nyheder …'}</p>`;
  }
  return html || `<div class="empty">Intet matcher »${esc(query)}«.</div>`;
}

const isStale = () => data && data.updated && (Date.now() - new Date(data.updated)) / 60000 > 60;
function renderHeader() {
  const stale = isStale();
  $('dot').classList.toggle('stale', !!stale);
  $('status').classList.toggle('stale', !!stale);
  $('status').textContent = !data ? 'henter …' : stale ? 'ikke opdateret siden ' + clock(data.updated) : 'opdateret ' + clock(data.updated);
}
function render(opts = {}) {
  renderHeader();
  if (!data) { $('list').innerHTML = '<div class="skel"></div>'.repeat(8); return; }
  const all = stories();
  let html = isStale() ? `<p class="notice">Khabar har ikke hentet nyt siden kl. ${clock(data.updated)}. Listen kan være forældet.</p>` : '';
  html += tab === 'home' ? home(all, opts) : tab === 'search' ? searchPage(all) : sectionPage(tab, all, opts);
  $('list').innerHTML = `<div class="${opts.view && !reduceMotion ? 'view' : ''}">${html}</div>`;
  // new stories that arrived while the user was scrolled down: offer a pill instead of jumping
  const fresh = opts.fresh && shownIds.size ? all.filter(i => !shownIds.has(i.id)).length : 0;
  shownIds = new Set(all.map(i => i.id));
  if (fresh && scrollY > 240 && tab !== 'search') {
    $('freshPill').querySelector('span').textContent = `${fresh} ${fresh === 1 ? 'ny historie' : 'nye historier'}`;
    $('freshPill').hidden = false;
  }
  // a dot on a section tab when it holds an important story the user has not seen yet
  for (const sec of Object.keys(SECTIONS)) {
    document.querySelector(`.tabs [data-tab="${sec}"]`).classList.toggle('has-new', tab !== sec && all.some(i => i.important && isNew(i) && secOf(i) === sec));
  }
  if (focusId) openFocus(all);
}
// a notification opens the app on its story: find it, open it, show it
function openFocus(all) {
  const i = all.find(x => x.id === focusId);
  if (!i) return;
  focusId = null;
  expanded.add(i.id);
  if (!$('s-' + i.id)) setTab(secOf(i), { top: true });   // its own section shows it already opened
  const el = $('s-' + i.id);
  if (!el) return;
  if (!el.classList.contains('open')) { el.querySelector('.x-in').innerHTML = detail(i); el.classList.add('open'); }
  setTimeout(() => {   // jump straight there, headline just below the top bar
    const at = $('s-' + i.id);
    if (at) scrollTo(0, at.getBoundingClientRect().top + scrollY - $('bar').offsetHeight - 8);
  }, 150);
}

// ---------------------------------------------------------------- open a story in place
function toggle(el) {
  const id = el.dataset.id, open = !el.classList.contains('open'), i = find(id);
  if (open && i) {
    el.querySelector('.x-in').innerHTML = detail(i);
    expanded.add(id);
    void el.offsetHeight;   // lay out the closed state first, so the opening animates
    el.classList.add('open');
    // keep the opened story's buttons in view
    setTimeout(() => {
      const r = el.getBoundingClientRect(), limit = innerHeight - $('dock').offsetHeight - 12;
      if (r.bottom > limit) scrollBy({ top: Math.min(r.bottom - limit, r.top - 70), behavior: reduceMotion ? 'auto' : 'smooth' });
    }, 320);
  } else {
    el.classList.remove('open'); expanded.delete(id);
  }
  el.querySelector('.row').setAttribute('aria-expanded', open);
}

// ---------------------------------------------------------------- share and copy
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch {
    const ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, text.length);
    const ok = document.execCommand('copy'); ta.remove(); return ok;
  }
}
let toastTimer;
function toast(msg, good = true) {
  $('toastText').textContent = msg;
  $('toast').querySelector('svg').style.display = good ? '' : 'none';
  $('toast').classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 1700);
}
function markShared(i) {
  shared[i.id] = { at: Date.now(), title: i.title, link: i.link, source: i.source };
  for (const [k, v] of Object.entries(shared)) if (Date.now() - v.at > 30 * 864e5) delete shared[k];
  store.set('shared', shared);
  const el = $('s-' + i.id);
  if (el) { el.classList.remove('new'); el.querySelector('.m').innerHTML = meta(i); }
  learnFrom(i, 'share');
}
// the phone's own share sheet (WhatsApp is one tap away there); copying is the fallback
async function share(text, i) {
  if (navigator.share) {
    try { await navigator.share({ text }); if (i) markShared(i); return; } catch (e) { if (e.name === 'AbortError') return; }
  }
  if (await copyText(text)) { toast('Kopieret – sæt ind i WhatsApp'); if (i) markShared(i); }
}

$('list').addEventListener('click', async e => {
  const t = e.target, el = t.closest('[data-id]'), i = el && find(el.dataset.id);
  if (t.closest('[data-go]')) { setTab(t.closest('[data-go]').dataset.go, { top: true }); return; }
  if (t.closest('[data-digest-share]')) { share(digestText()); return; }
  if (t.closest('[data-digest-toggle]')) { digestOpen = !digestOpen; $('digest').outerHTML = digestCard(); return; }
  if (!el) return;
  if (t.closest('[data-share]')) share(shareText(i), i);
  else if (t.closest('[data-copy]')) { if (await copyText(shareText(i))) { toast('Kopieret'); markShared(i); } }
  else if (t.closest('[data-read]')) learnFrom(i, 'read');
  else if (t.closest('[data-toggle]')) toggle(el);
});
$('freshPill').addEventListener('click', () => { $('freshPill').hidden = true; scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); });
addEventListener('scroll', () => {
  if (scrollY < 120) $('freshPill').hidden = true;
  $('bar').classList.toggle('scrolled', scrollY > 4);
}, { passive: true });

// ---------------------------------------------------------------- pull down to refresh: a quiet ring
let pull = null;
const list = $('list'), ptr = $('ptr');
addEventListener('touchstart', e => {
  if (scrollY <= 0 && tab !== 'search' && !e.target.closest('.sheet, .dock')) pull = { y: e.touches[0].clientY, d: 0 };
}, { passive: true });
addEventListener('touchmove', e => {
  if (!pull) return;
  pull.d = e.touches[0].clientY - pull.y;
  if (pull.d <= 0 || scrollY > 0) { list.style.transform = ''; ptr.style.opacity = 0; return; }
  list.classList.add('pulling');
  list.style.transform = `translateY(${(110 * (1 - Math.exp(-pull.d / 170))).toFixed(1)}px)`;
  ptr.style.opacity = Math.min(1, pull.d / 36);
  ptr.style.setProperty('--k', Math.min(1, pull.d / 84).toFixed(3));
  ptr.classList.toggle('ready', pull.d >= 84);
}, { passive: true });
addEventListener('touchend', async () => {
  if (!pull) return;
  const go = pull.d >= 84;
  pull = null;
  list.classList.remove('pulling');
  list.classList.add('settling');
  if (go) {
    list.style.transform = 'translateY(50px)';
    ptr.classList.remove('ready'); ptr.classList.add('spin'); ptr.style.opacity = 1;
    await Promise.all([load(true), wait(650)]);
    ptr.classList.remove('spin');
  }
  list.style.transform = ''; ptr.style.opacity = 0; ptr.style.setProperty('--k', 0);
  setTimeout(() => list.classList.remove('settling'), 420);
});

// ---------------------------------------------------------------- tabs + search
function setTab(next, opts = {}) {
  if (next === tab) {
    if (tab === 'search') $('search').focus(); else scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    return;
  }
  scrollPos[tab] = scrollY;
  tab = next;
  document.querySelectorAll('.tabs [data-tab]').forEach(x => x.setAttribute('aria-selected', x.dataset.tab === tab));
  const title = tab === 'home' ? 'Khabar' : tab === 'search' ? 'Søg' : SECTIONS[tab];
  $('title').textContent = title;
  $('title').classList.remove('swap'); void $('title').offsetWidth; $('title').classList.add('swap');
  $('searchbar').hidden = tab !== 'search';
  if (tab === 'search') { loadIndex(); setTimeout(() => $('search').focus(), 60); } else $('search').blur();
  $('freshPill').hidden = true;
  render({ view: true });
  scrollTo(0, opts.top ? 0 : scrollPos[tab] || 0);
}
// everything the radar read in the last two days, fetched only when someone searches
async function loadIndex() {
  if (searchIndex || searchState === 'loading') return;
  searchState = 'loading';
  const url = CFG.searchUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'search.json');
  try {
    const r = await fetch(bust(url), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    searchIndex = await r.json();
    searchState = 'ok';
  } catch { searchState = 'error'; }
  if (tab === 'search') render();
}
$('tabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) setTab(b.dataset.tab, { top: b.dataset.tab === tab }); });
let typing;
$('search').addEventListener('input', e => { clearTimeout(typing); typing = setTimeout(() => { query = e.target.value; render(); }, 120); });
$('search').addEventListener('keydown', e => { if (e.key === 'Enter') $('search').blur(); });
$('searchClear').addEventListener('click', () => { query = ''; $('search').value = ''; $('search').focus(); render(); });
$('status').addEventListener('click', () => { $('status').textContent = 'opdaterer …'; load(true); });

// keep the dock (search field + tabs) right above the keyboard, and tell the layout how tall it is
const vv = window.visualViewport;
if (vv) vv.addEventListener('resize', () => {
  const kb = Math.max(0, innerHeight - vv.height - vv.offsetTop);
  document.documentElement.style.setProperty('--kb', kb + 'px');
  document.body.classList.toggle('keyboard', kb > 40);
});
new ResizeObserver(() => document.documentElement.style.setProperty('--dock', $('dock').offsetHeight + 'px')).observe($('dock'));

document.addEventListener('visibilitychange', () => {
  if (document.hidden) store.set('lastSeen', Date.now());
  else { lastSeen = store.get('lastSeen', lastSeen); load(); }
});
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(renderHeader, 30000);

// ---------------------------------------------------------------- settings sheet: slides up, drag down to close
function howText() {
  const src = Object.keys((data && data.sources) || {}).length || 61, L = (data && data.learned) || {};
  return `<p>Khabar læser <b>${src} kilder</b> hvert femte minut: danske, vestlige, arabiske og israelske medier og miljøets egne kanaler.${data && data.scanned_24h ? ` Det seneste døgn er ${num(data.scanned_24h)} nyheder vurderet.` : ''}</p>
    <p><b>Sektioner.</b> Hver historie lander i Danmark, Mellemøsten eller Verden ud fra de steder, partier og personer, den nævner. Kan ordene ikke afgøre det, ser Khabar på, hvor lignende historier hører til.</p>
    <p><b>Rækkefølge.</b> Tre ting tæller: hvor meget historien ligner det, gruppen har delt (ca. 6.500 links), hvor mange medier der dækker den, og om den handler om kerneemnerne – politik, Palæstina, islam og muslimer, krig og magt. Dansk politik får et ekstra løft, fordi gruppens links mest handler om udlandet. Vejr, sport, kongehus og lokale ulykker trækkes ned.</p>
    <p><b>Samme historie</b> fra flere medier samles på én linje. Åbn den og se, hvordan danske, vestlige, arabiske og israelske medier dækker den. <b>Ubekræftet</b> betyder, at den kun findes på Telegram eller YouTube indtil videre.</p>
    <p><b>Khabar lærer af sig selv</b> – fra miljøets egne kilder (${num(L.community)}), store historier (${num(L.big)}) og det, du deler (${num(L.copied)}) og læser (${num(L.read)}). Claude skriver overblikket kl. 7 og 17 og tjekker kilderne hver morgen.</p>`;
}
function openSheet() {
  $('how').innerHTML = howText();
  const by = {};
  Object.entries((data && data.sources) || {}).forEach(([n, v]) => (by[v.group || 'west'] ||= []).push([n, v]));
  $('sources').innerHTML = GROUP_ORDER.filter(g => by[g]).map(g => `<h4>${GROUPS[g]}</h4><ul>` + by[g].sort((a, b) => a[0].localeCompare(b[0], 'da'))
    .map(([n, v]) => `<li class="${v.ok ? '' : 'bad'}">${esc(n)}</li>`).join('') + '</ul>').join('');
  $('sheet').hidden = false;
  $('sheetScroll').scrollTop = 0;
  void $('sheet').offsetHeight;
  $('sheet').classList.add('on'); $('scrim').classList.add('on');
  refreshPushInfo();
}
function closeSheet() {
  $('sheet').classList.remove('on', 'dragging');
  $('sheet').style.removeProperty('--drag');
  $('scrim').classList.remove('on');
  setTimeout(() => { if (!$('sheet').classList.contains('on')) $('sheet').hidden = true; }, 460);
}
$('openSettings').addEventListener('click', openSheet);
$('scrim').addEventListener('click', closeSheet);
$('closeSheet').addEventListener('click', closeSheet);
let drag = null;
$('sheet').addEventListener('touchstart', e => {
  const onGrip = e.target.closest('#sheetGrip');
  if (onGrip || $('sheetScroll').scrollTop <= 0) drag = { y: e.touches[0].clientY, d: 0, t: Date.now(), grip: !!onGrip };
}, { passive: true });
$('sheet').addEventListener('touchmove', e => {
  if (!drag) return;
  drag.d = e.touches[0].clientY - drag.y;
  if (drag.d <= 0 || (!drag.grip && $('sheetScroll').scrollTop > 0)) { drag.d = 0; return; }
  $('sheet').classList.add('dragging');
  $('sheet').style.setProperty('--drag', drag.d + 'px');
}, { passive: true });
$('sheet').addEventListener('touchend', () => {
  if (!drag) return;
  const close = drag.d > 120 || (drag.d > 40 && Date.now() - drag.t < 250);
  drag = null;
  $('sheet').classList.remove('dragging');
  if (close) closeSheet(); else $('sheet').style.removeProperty('--drag');
});

// settings
$('danish').checked = danish;
$('danish').addEventListener('change', e => { danish = e.target.checked; store.set('danish', danish); render(); });
function paintSeg() { document.querySelectorAll('#foreignSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === foreignMode)); }
$('foreignSeg').addEventListener('click', e => {
  const b = e.target.closest('[data-v]'); if (!b) return;
  foreignMode = b.dataset.v; store.set('foreignMode', foreignMode); paintSeg(); render();
});
paintSeg();

// appearance: five light tones, four dark palettes, and automatic / light / dark
let tone = store.get('tone', 'papir'), mode = store.get('mode', 'auto'), dark = store.get('dark', 'grafit');
function applyLook() {
  const d = document.documentElement;
  tone === 'papir' ? delete d.dataset.tone : d.dataset.tone = tone;
  mode === 'auto' ? delete d.dataset.theme : d.dataset.theme = mode;
  dark === 'grafit' ? delete d.dataset.dark : d.dataset.dark = dark;
  document.querySelectorAll('#darkSeg [data-dark]').forEach(b => b.setAttribute('aria-checked', b.dataset.dark === dark));
  document.querySelectorAll('#toneSeg [data-tone]').forEach(b => b.setAttribute('aria-checked', b.dataset.tone === tone));
  document.querySelectorAll('#modeSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === mode));
  const bg = getComputedStyle(d).getPropertyValue('--bg').trim();
  document.querySelectorAll('meta[name="theme-color"]').forEach(m => m.setAttribute('content', bg));
}
$('toneSeg').addEventListener('click', e => { const b = e.target.closest('[data-tone]'); if (b) { tone = b.dataset.tone; store.set('tone', tone); applyLook(); } });
$('darkSeg').addEventListener('click', e => { const b = e.target.closest('[data-dark]'); if (b) { dark = b.dataset.dark; store.set('dark', dark); applyLook(); } });
$('modeSeg').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) { mode = b.dataset.v; store.set('mode', mode); applyLook(); } });
if (!params.get('tone')) applyLook();

// notifications
const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
function b64ToBytes(s) {
  const p = '='.repeat((4 - s.length % 4) % 4), b = atob((s + p).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(b, c => c.charCodeAt(0));
}
async function refreshPushInfo() {
  const info = $('pushInfo'), btn = $('enablePush');
  btn.hidden = true;
  if (!standalone && /iPhone|iPad/.test(navigator.userAgent)) {
    info.innerHTML = 'Læg først Khabar på hjemmeskærmen: <b>Del</b> → <b>Føj til hjemmeskærm</b> i Safari, og åbn den derfra.';
    return;
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) { info.textContent = 'Denne browser understøtter ikke notifikationer.'; return; }
  const reg = await Promise.race([navigator.serviceWorker.ready, wait(4000)]);
  if (!reg) { info.textContent = 'Notifikationer kan kun slås til i appen på hjemmeskærmen.'; return; }
  const sub = await reg.pushManager.getSubscription();
  if (sub && Notification.permission === 'granted') {
    info.textContent = 'Slået til: store historier, de allervigtigste nyheder og overblikket kl. 7 og 17. Højst ca. 15 om dagen, aldrig mellem kl. 23 og 7.';
    showCode(sub);
  } else {
    info.textContent = 'Få besked ved store historier, de allervigtigste nyheder og overblikket.';
    btn.hidden = false;
  }
}
function showCode(sub) {
  $('pushCode').hidden = false;
  $('pushCodeText').value = 'NYHEDSRADAR-PUSH:' + btoa(JSON.stringify(sub));
}
$('enablePush').addEventListener('click', async () => {
  try {
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') { toast('Notifikationer blev ikke tilladt', false); return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(CFG.vapidPublicKey) });
    showCode(sub); $('enablePush').hidden = true;
    $('pushInfo').textContent = 'Næsten færdig – send koden herunder til Claude.';
  } catch (e) { toast('Det lykkedes ikke: ' + e.message, false); }
});
$('copyPushCode').addEventListener('click', async () => { if (await copyText($('pushCodeText').value)) toast('Koden er kopieret'); });

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
const startTab = params.get('tab');
if (startTab && (SECTIONS[startTab] || startTab === 'search')) setTab(startTab, { top: true });
else render({ enter: true });
load();
