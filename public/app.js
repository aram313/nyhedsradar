// Khabar – phone app. Reads data.json written by the radar (and digest.json written by the Claude
// editor) and shows them as a compact, text-first list with thumb-reachable controls. Plain JS.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;


let data = store.get('lastData', null);
let digest = store.get('lastDigest', null);
let tab = 'top', query = '';
let copied = store.get('copied', {});                        // id -> {at, title, link, source, words}
let foreignMode = store.get('foreignMode', 'translate');      // translate | hide | original
let danish = store.get('danish', false);                      // show and copy in Danish
let overviewOpen = false;
const expanded = new Set();
const params = new URLSearchParams(location.search);
const focusId = params.get('item');
if (params.get('digest') === '1') overviewOpen = true;
const lastSeen = store.get('lastSeen', 0);                     // items found after this get a small "ny"
let shownIds = new Set();

// ---------------------------------------------------------------- learning from copies
const STOP = new Set(('og i at det er en til på som de med for af ikke der har jeg om var vi kan man den så hvad men ved skal fra eller nu også have efter blev mod over efter mere siger sagt nye ' +
  'the and of to in a is that for on are with as it this was by be has have from at they their not an or who will its but were been after says said over new more').split(' '));
const words = t => [...new Set((t.toLowerCase().match(/[\p{L}]{4,}/gu) || []).filter(w => !STOP.has(w)))];
const copiedWordSets = () => Object.values(copied).filter(c => Date.now() - c.at < 30 * 864e5).map(c => new Set(c.words));
function likeCopied(item, sets) {
  const w = words(item.origTitle || item.title);
  if (w.length < 2) return false;
  return sets.some(s => w.filter(x => s.has(x)).length >= Math.min(3, Math.ceil(w.length * 0.4)));
}
// Each copy silently tells the radar "more like this" (no extra tap; only the public headline is sent).
function learnFrom(i) {
  if (!CFG.feedbackTopic) return;
  fetch('https://ntfy.sh/' + CFG.feedbackTopic, {
    method: 'POST', body: JSON.stringify({ kind: 'up', id: i.id, title: i.origTitle || i.title, summary: (i.origSummary || i.summary || '').slice(0, 220) }),
  }).catch(() => { /* offline: local learning still applies */ });
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

// ---------------------------------------------------------------- data
const bust = url => url + (url.includes('?') ? '&' : '?') + 't=' + Date.now();
async function load(manual) {
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
  if (changed || manual) render({ fresh: true });
  else renderHeader();
}

// ---------------------------------------------------------------- what a line shows
// Danish/English as-is; other languages translated unless the user wants the original;
// with the Danish setting on, everything that has a Danish version is shown in Danish.
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary };
  if (i.foreign && foreignMode !== 'original' && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', from: i.lang, to: 'en' };
  }
  if (danish && i.title_da && !(i.foreign && foreignMode === 'original')) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', from: d.from || i.lang, to: 'da' };
  }
  return d;
}
const readable = t => !/[؀-ۿ]/.test(t || '');
function copyTextFor(d, withSummary) {
  if (!withSummary) return `${d.title}\n${d.link}`;
  const first = (d.summary || '').split(/(?<=[.!?])\s/)[0].replace(/\s*…$/, '');
  return `*${d.title}*\n${first ? first + '\n' : ''}${d.link}`;
}
function itemsFor(which) {
  if (!data) return [];
  const sets = copiedWordSets();
  let items = data.items
    .filter(i => !i.foreign || foreignMode === 'original' || (foreignMode === 'translate' && i.title_tr))
    .map(display)
    .map(i => ({ ...i, learned: !i.important && likeCopied(i, sets) }))
    .sort((a, b) => when(b) - when(a));
  // 'Vigtigste' is about the last two days; 'Alle' and search keep everything the radar still holds
  if (which === 'top') items = items.filter(i => (i.important || i.learned) && Date.now() - when(i) < 48 * 3600e3);
  if (which === 'copied') items = Object.entries(copied).sort((a, b) => b[1].at - a[1].at)
    .map(([id, c]) => { const x = data.items.find(i => i.id === id); return x ? display(x) : { id, title: c.title, link: c.link, source: c.source, found: new Date(c.at).toISOString(), summary: '', also: [] }; });
  if (which === 'search') {
    const q = query.toLowerCase();
    items = q ? items.filter(i => (i.title + ' ' + i.summary + ' ' + i.source + ' ' + (i.origTitle || '')).toLowerCase().includes(q)) : [];
  }
  return items;
}

// ---------------------------------------------------------------- render
function heat(i) {
  if (i.pct == null) return 0;
  return i.pct >= 96 ? .75 : i.pct >= 90 || i.learned ? .45 : i.pct >= 85 ? .25 : .1;
}
function meta(i) {
  const m = [`<span class="s">${esc(i.source)}</span>`, `<span>${ago(i.published || i.found)}</span>`];
  if (lastSeen && i.found && new Date(i.found).getTime() > lastSeen && !copied[i.id]) m.unshift('<span class="new">ny</span>');
  if (i.big) m.push(`<span class="hot" title="Stor historie">●${i.outlets}</span>`);
  else if (i.confirmed >= 2) m.push(`<span class="ok" title="Bekræftet af ${i.confirmed} medier">✓${i.confirmed}</span>`);
  if (i.confirmed === 0) m.push('<span class="q" title="Ubekræftet: kun Telegram/YouTube">?</span>');
  if (i.to) m.push(`<span title="Oversat">${i.from === 'en' ? '' : esc(i.from)}→${i.to}</span>`);
  if ((i.also || []).length) m.push(`<span>+${i.also.length}</span>`);
  return m.join('');
}
function line(i, n, opts) {
  const done = !!copied[i.id], open = expanded.has(i.id), also = i.also || [];
  const cls = ['item', done && 'done', i.big && 'big', open && 'open',
    opts.stagger && n < 14 && 'enter', opts.fresh && shownIds.size && !shownIds.has(i.id) && 'fresh'].filter(Boolean).join(' ');
  return `<article class="${cls}" id="c-${esc(i.id)}" data-id="${esc(i.id)}" style="--i:${n}">
    <div class="swipe"><svg><use href="#i-copy"/></svg>Kopiér</div>
    <div class="row">
      <i class="heat" style="--heat:${heat(i)}"></i>
      <button class="body" data-toggle aria-expanded="${open}"><span class="h" dir="auto">${esc(i.title)}</span><span class="m">${meta(i)}</span></button>
      <button class="c" data-copy aria-label="Kopiér overskrift og link"><svg class="cp"><use href="#i-copy"/></svg><svg class="ck"><use href="#i-check"/></svg></button>
    </div>
    <div class="x"><div class="x-in"><div class="x-pad">
      ${i.summary ? `<p dir="auto">${esc(i.summary)}</p>` : ''}
      <div class="acts">
        <a class="act" href="${esc(i.link)}" target="_blank" rel="noopener"><svg><use href="#i-open"/></svg>Åbn</a>
        <button class="act" data-copy-sum><svg><use href="#i-text"/></svg>Med resumé</button>
        <button class="act primary" data-copy><svg><use href="#i-copy"/></svg>Kopiér</button>
      </div>
      ${also.length ? `<div class="also-h">Også hos</div><ul class="also">${also.map((a, k) => `<li><span><b>${esc(a.source)}</b>${foreignMode === 'original' || readable(a.title) ? ` · <span dir="auto">${esc(a.title)}</span>` : ' · på arabisk'}</span><button data-copy-also="${k}" aria-label="Kopiér"><svg><use href="#i-copy"/></svg></button></li>`).join('')}</ul>` : ''}
    </div></div></div>
  </article>`;
}

// the Claude editor's overview, shown at the top of "Vigtigste" for 12 hours
function overview() {
  if (!digest || !digest.created || Date.now() - new Date(digest.created) > 12 * 3600e3) return '';
  const items = digest.items || [];
  const fresh = digest.created !== overview.seen;
  overview.seen = digest.created;
  return `<section class="ov${overviewOpen ? '' : ' short'}${fresh && !reduceMotion ? ' enter' : ''}" id="ov">
    <div class="ov-head">Overblik <span>${esc(digest.period || '')} · kl. ${clock(digest.created)} · Claude</span></div>
    ${digest.intro && overviewOpen ? `<p class="ov-intro">${esc(digest.intro)}</p>` : ''}
    <ol>${(overviewOpen ? items : items.slice(0, 4)).map(x => `<li><a href="${esc(x.link)}" target="_blank" rel="noopener"><div><b>${esc(x.headline)}</b>${x.text ? `<small>${esc(x.text)}</small>` : ''}</div><em>${esc(x.source || '')}</em></a></li>`).join('')}</ol>
    <div class="acts">
      <button class="act" data-toggle-ov><svg><use href="#i-text"/></svg>${overviewOpen ? 'Kort' : items.length > 4 ? `Alle ${items.length} med tekst` : 'Med tekst'}</button>
      <button class="act primary" data-copy-ov><svg><use href="#i-copy"/></svg>Kopiér overblik</button>
    </div>
  </section>`;
}

const isStale = () => data && data.updated && (Date.now() - new Date(data.updated)) / 60000 > 60;
function renderHeader() {
  const stale = isStale();
  $('beat').classList.toggle('stale', !!stale);
  $('status').classList.toggle('stale', !!stale);
  const mins = data ? Math.round((Date.now() - new Date(data.updated)) / 60000) : 0;
  $('status').textContent = !data ? 'henter …' : stale ? 'ikke opdateret siden ' + clock(data.updated)
    : mins < 1 ? 'opdateret nu' : `opdateret for ${mins} min. siden`;
  const n = Object.values(copied).filter(c => Date.now() - c.at < 864e5).length;
  $('copiedBadge').hidden = !n;
  $('copiedBadge').textContent = n > 9 ? '9+' : n;
}

function render(opts = {}) {
  renderHeader();
  if (!data) { $('list').innerHTML = '<div class="skel"></div>'.repeat(7); return; }
  const items = itemsFor(tab);
  let html = isStale() ? `<p class="notice">Khabar har ikke hentet nyt siden kl. ${clock(data.updated)}. Listen kan være forældet.</p>` : '';
  if (tab === 'top') html += overview();
  if (!items.length) {
    const msg = { top: 'Ingen vigtige nyheder lige nu.<br>Khabar holder øje.', copied: 'Det, du kopierer, samles her.',
      search: query ? 'Intet matcher søgningen.' : `Søg i ${itemsFor('all').length} nyheder fra de seneste tre døgn.`, all: 'Ingen nyheder endnu.' }[tab];
    html += `<div class="empty"><svg viewBox="0 0 120 24"><path d="M2 14h30l5-9 7 16 8-20 6 13h60" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>${msg}</div>`;
  }
  let last = '';
  items.forEach((i, n) => {
    const d = dayLabel(i.published || i.found);
    if (d !== last && tab !== 'copied' && tab !== 'search') { html += `<div class="day">${d}</div>`; last = d; }
    html += line(i, n, opts);
  });
  // new lines that arrived while the user was scrolled down: offer a pill instead of jumping
  const newIds = opts.fresh && shownIds.size ? items.filter(i => !shownIds.has(i.id)).length : 0;
  const viewCls = opts.anim && !reduceMotion ? `view${typeof opts.anim === 'string' ? ' from-' + opts.anim : ''}` : '';
  $('list').innerHTML = `<div class="${viewCls}">${html}</div>`;
  shownIds = new Set(items.map(i => i.id));
  if (newIds && scrollY > 240) { $('freshPill').querySelector('span').textContent = `${newIds} ${newIds === 1 ? 'ny' : 'nye'}`; $('freshPill').hidden = false; }
  if (focusId && !render.focused) {
    const el = $('c-' + focusId);
    if (el) { render.focused = true; expanded.add(focusId); el.classList.add('open'); el.scrollIntoView({ block: 'center' }); }
  }
}

// ---------------------------------------------------------------- copy
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
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 1600);
}
async function copyItem(id, withSummary) {
  const raw = data && data.items.find(x => x.id === id);
  const i = raw ? display(raw) : (copied[id] && { id, ...copied[id] });
  if (!i || !(await copyText(copyTextFor(i, withSummary || danish)))) return;
  copied[id] = { at: Date.now(), title: i.title, link: i.link, source: i.source, words: words(i.origTitle || i.title) };
  store.set('copied', copied);
  const el = $('c-' + id);
  if (el) {
    el.classList.add('done'); el.querySelector('.new')?.remove();
    el.classList.add('just-copied'); setTimeout(() => el.classList.remove('just-copied'), 1000);
    if (!reduceMotion) {   // a red newspaper stamp lands on the line
      const st = document.createElement('span'); st.className = 'stamp'; st.textContent = 'Kopieret';
      el.querySelector('.row').append(st); setTimeout(() => st.remove(), 1500);
    }
  }
  renderHeader();
  toast(withSummary || danish ? 'Kopieret med resumé' : 'Kopieret');
  learnFrom(i);
}

$('list').addEventListener('click', async e => {
  const t = e.target, el = t.closest('[data-id]'), id = el && el.dataset.id;
  if (t.closest('[data-copy-ov]')) {
    const text = digest.whatsapp || (digest.items || []).map(x => `*${x.headline}*\n${x.text || ''}\n${x.link}`).join('\n\n');
    if (await copyText(text)) toast('Overblikket er kopieret');
  } else if (t.closest('[data-toggle-ov]')) {
    overviewOpen = !overviewOpen;
    $('ov').outerHTML = overview();
  } else if (t.closest('[data-copy-sum]')) {
    copyItem(id, true);
  } else if (t.closest('[data-copy]')) {
    copyItem(id);
  } else if (t.closest('[data-copy-also]')) {
    const x = data.items.find(i => i.id === id).also[+t.closest('[data-copy-also]').dataset.copyAlso];
    if (await copyText(`${x.title}\n${x.link}`)) toast('Kopieret');
  } else if (t.closest('[data-toggle]')) {
    const open = el.classList.toggle('open');
    open ? expanded.add(id) : expanded.delete(id);
    el.querySelector('[data-toggle]').setAttribute('aria-expanded', open);
  }
});
$('freshPill').addEventListener('click', () => { $('freshPill').hidden = true; scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); });
addEventListener('scroll', () => {
  if (scrollY < 120) $('freshPill').hidden = true;
  $('top').classList.toggle('scrolled', scrollY > 8);
}, { passive: true });

// ---------------------------------------------------------------- swipe right to copy
let sw = null;
$('list').addEventListener('touchstart', e => {
  const row = e.target.closest('.row');
  if (!row || e.touches.length > 1) return;
  sw = { row, item: row.closest('[data-id]'), x: e.touches[0].clientX, y: e.touches[0].clientY, dx: 0, mode: null };
}, { passive: true });
$('list').addEventListener('touchmove', e => {
  if (!sw) return;
  const dx = e.touches[0].clientX - sw.x, dy = e.touches[0].clientY - sw.y;
  if (!sw.mode) {
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
    sw.mode = dx > 0 && Math.abs(dx) > Math.abs(dy) * 1.4 ? 'swipe' : 'scroll';
    if (sw.mode === 'swipe') { sw.row.classList.add('dragging'); sw.item.classList.add('swiping'); }
  }
  if (sw.mode !== 'swipe') return;
  sw.dx = Math.max(0, dx);
  sw.row.style.transform = `translateX(${sw.dx < 90 ? sw.dx : 90 + (sw.dx - 90) * 0.3}px)`;
  sw.item.classList.toggle('armed', sw.dx > 90);
}, { passive: true });
$('list').addEventListener('touchend', () => {
  if (!sw) return;
  const { row, item, dx, mode } = sw;
  sw = null;
  if (mode !== 'swipe') return;
  row.classList.remove('dragging');
  row.style.transform = '';
  item.classList.remove('armed');
  setTimeout(() => item.classList.remove('swiping'), 420);   // after the row has slid back
  if (dx > 90) copyItem(item.dataset.id);
});

// ---------------------------------------------------------------- pull down to refresh: the red dot becomes an ink drop
let pull = null;
addEventListener('touchstart', e => {
  if (scrollY <= 0 && !e.target.closest('.sheet, .dock')) pull = { y: e.touches[0].clientY, d: 0 };
}, { passive: true });
addEventListener('touchmove', e => {
  if (!pull) return;
  pull.d = e.touches[0].clientY - pull.y;
  if (pull.d <= 0 || scrollY > 0) { $('list').style.transform = ''; $('ptr').style.opacity = 0; return; }
  const k = Math.min(1, pull.d / 90);
  $('list').classList.add('pulling');
  $('list').style.transform = `translateY(${Math.min(120, pull.d * 0.8)}px)`;
  $('ptr').style.opacity = Math.min(1, k * 1.4);
  $('ptr').style.setProperty('--k', k);
  $('ptr').classList.toggle('ready', k >= 1);
}, { passive: true });
addEventListener('touchend', async () => {
  if (!pull) return;
  const go = pull.d > 90;
  pull = null;
  $('list').classList.remove('pulling');
  $('ptr').classList.remove('ready');
  if (go) {
    $('list').style.transform = 'translateY(78px)';
    $('ptr').classList.add('rippling');
    document.body.classList.add('refreshing');
    await Promise.all([load(true), new Promise(r => setTimeout(r, 1100))]);
    document.body.classList.remove('refreshing');
    $('ptr').classList.remove('rippling');
  }
  $('list').style.transform = '';
  $('ptr').style.opacity = 0;
  $('ptr').style.setProperty('--k', 0);
});

// ---------------------------------------------------------------- tab bar + search
function moveIndicator() {
  const b = document.querySelector(`.tabbar [data-tab="${tab}"]`);
  $('tabInd').style.transform = `translateX(${b.offsetLeft + b.offsetWidth / 2}px)`;
}
function setTab(next) {
  if (next === tab) { scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); return; }
  const order = ['top', 'all', 'copied', 'search'];
  const dir = order.indexOf(next) > order.indexOf(tab) ? 'right' : 'left';
  tab = next;
  document.querySelectorAll('.tabbar [data-tab]').forEach(x => x.setAttribute('aria-selected', x.dataset.tab === tab));
  moveIndicator();
  $('searchbar').hidden = tab !== 'search';
  if (tab === 'search') setTimeout(() => $('search').focus(), 60);
  else $('search').blur();
  $('freshPill').hidden = true;
  render({ anim: dir, stagger: true });
  scrollTo(0, 0);
}
$('tabbar').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) setTab(b.dataset.tab); });
$('search').addEventListener('input', e => { query = e.target.value.trim(); render(); });
$('searchClear').addEventListener('click', () => { query = ''; $('search').value = ''; $('search').focus(); render(); });
$('status').addEventListener('click', () => { $('status').textContent = 'opdaterer …'; load(true); });

// keep the dock (search field + tabs) right above the keyboard, and tell the layout how tall it is
const vv = window.visualViewport;
if (vv) vv.addEventListener('resize', () => {
  const kb = Math.max(0, innerHeight - vv.height - vv.offsetTop);
  document.documentElement.style.setProperty('--kb', kb + 'px');
});
new ResizeObserver(() => document.documentElement.style.setProperty('--dock', $('dock').offsetHeight + 'px')).observe($('dock'));
addEventListener('resize', moveIndicator);

document.addEventListener('visibilitychange', () => {
  if (document.hidden) store.set('lastSeen', Date.now());
  else load();
});
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(renderHeader, 30000);

// ---------------------------------------------------------------- "Mere" sheet: slides up, drag down to close
function openSheet() {
  const src = Object.entries((data && data.sources) || {});
  $('srcCount').textContent = src.length || '–';
  const L = (data && data.learned) || {};
  $('scanned').textContent = data && data.scanned_24h ? `Seneste døgn: ${data.scanned_24h.toLocaleString('da-DK')} nye nyheder vurderet. Lært af ${(L.community || 0).toLocaleString('da-DK')} indlæg fra miljøets kilder, ${L.big || 0} store historier og ${L.copied || 0} kopieringer.` : '';
  $('sources').innerHTML = src.sort((a, b) => a[0].localeCompare(b[0], 'da')).map(([n, v]) => `<li class="${v.ok ? '' : 'bad'}">${esc(n)}</li>`).join('');
  $('sheet').hidden = false;
  $('sheetScroll').scrollTop = 0;
  requestAnimationFrame(() => requestAnimationFrame(() => { $('sheet').classList.add('on'); $('scrim').classList.add('on'); }));
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
  const fast = drag.d > 40 && Date.now() - drag.t < 250;
  const close = drag.d > 120 || fast;
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

// appearance: five tones of the same look, and automatic / light / dark
let tone = store.get('tone', 'papir'), mode = store.get('mode', 'auto');
function applyLook() {
  const d = document.documentElement;
  tone === 'papir' ? delete d.dataset.tone : d.dataset.tone = tone;
  mode === 'auto' ? delete d.dataset.theme : d.dataset.theme = mode;
  document.querySelectorAll('#toneSeg [data-tone]').forEach(b => b.setAttribute('aria-checked', b.dataset.tone === tone));
  document.querySelectorAll('#modeSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === mode));
  const meta = getComputedStyle(d).getPropertyValue('--bg').trim();
  document.querySelectorAll('meta[name="theme-color"]').forEach(m => m.setAttribute('content', meta));
}
$('toneSeg').addEventListener('click', e => { const b = e.target.closest('[data-tone]'); if (b) { tone = b.dataset.tone; store.set('tone', tone); applyLook(); } });
$('modeSeg').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) { mode = b.dataset.v; store.set('mode', mode); applyLook(); } });
if (!new URLSearchParams(location.search).get('tone')) applyLook();

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
  const reg = await Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(r, 4000))]);
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
renderHeader();
moveIndicator();
async function opening() {
  const sp = $('splash');
  let skipped = false;
  const finish = () => {
    if (skipped) return; skipped = true;
    sp.remove(); document.body.classList.remove('opening');
    render({ stagger: true });
  };
  if (reduceMotion || sessionStorage.getItem('opened')) { finish(); return; }
  sessionStorage.setItem('opened', '1');
  document.body.classList.add('opening');
  sp.addEventListener('click', finish);
  const wait = ms => new Promise(r => setTimeout(r, ms));
  await Promise.race([document.fonts.load('132px "Lalezar"', 'حبر'), wait(900)]);
  sp.classList.add('write'); await wait(720);
  if (skipped) return;
  sp.classList.add('drop'); await wait(620);
  if (skipped) return;
  // FLIP the big logo onto the small one in the header
  const from = sp.querySelector('.splash-logo').getBoundingClientRect(), to = document.querySelector('.top .logo').getBoundingClientRect();
  const sc = to.height / from.height;
  sp.querySelector('.splash-logo').style.transform =
    `translate(${to.left + to.width / 2 - (from.left + from.width / 2)}px, ${to.top + to.height / 2 - (from.top + from.height / 2)}px) scale(${sc})`;
  sp.classList.add('fly');
  await wait(560);
  finish();
}
opening().catch(() => { $('splash')?.remove(); document.body.classList.remove('opening'); render({ stagger: true }); });
load();
