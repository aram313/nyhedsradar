// Nabd – phone app. Reads data.json written by the radar (and digest.json written by the Claude
// editor) and shows them as a compact, text-first list. Plain JS, no libraries.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

let data = store.get('lastData', null);
let digest = store.get('lastDigest', null);
let tab = 'top', query = '';
let copied = store.get('copied', {});                        // id -> {at, title, link, source, words}
let foreignMode = store.get('foreignMode', 'translate');      // translate | hide | original
let danish = store.get('danish', false);                      // show and copy in Danish
let overviewOpen = new URLSearchParams(location.search).get('digest') === '1';
const expanded = new Set();
const focusId = new URLSearchParams(location.search).get('item');

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
  if (m < 60) return Math.round(m) + 'm';
  if (d.toDateString() === new Date().toDateString()) return Math.round(m / 60) + 't';
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
  try {
    const r = await fetch(bust(CFG.dataUrl), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    data = await r.json();
    store.set('lastData', data);
    if (manual) toast('Opdateret');
  } catch (e) {
    if (manual) toast('Kunne ikke hente nye nyheder');
  }
  if (CFG.digestUrl) {
    try {
      const r = await fetch(bust(CFG.digestUrl), { cache: 'no-store' });
      if (r.ok) { digest = await r.json(); store.set('lastDigest', digest); }
    } catch { /* keep the last overview */ }
  }
  render();
}

// ---------------------------------------------------------------- what a line shows
const LANG = { ar: 'ar', tr: 'tr', en: 'en' };
// Danish/English as-is; other languages translated unless the user wants the original;
// with the Danish setting on, everything that has a Danish version is shown in Danish.
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary };
  if (i.foreign && foreignMode !== 'original' && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', from: LANG[i.lang] || i.lang, to: 'en' };
  }
  if (danish && i.title_da && !(i.foreign && foreignMode === 'original')) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', from: d.from || LANG[i.lang] || i.lang, to: 'da' };
  }
  return d;
}
const readable = t => !/[؀-ۿ]/.test(t || '');
function copyTextFor(d, withSummary = danish) {
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
  // 'Vigtigste' is about the last two days; 'Alle' keeps everything the radar still holds
  if (which === 'top') items = items.filter(i => (i.important || i.learned) && Date.now() - when(i) < 48 * 3600e3);
  if (which === 'copied') items = Object.entries(copied).sort((a, b) => b[1].at - a[1].at)
    .map(([id, c]) => { const x = data.items.find(i => i.id === id); return x ? display(x) : { id, title: c.title, link: c.link, source: c.source, found: new Date(c.at).toISOString(), summary: '', also: [] }; });
  return items;
}
function visibleItems() {
  let items = itemsFor(tab);
  if (query) {
    const q = query.toLowerCase();
    items = items.filter(i => (i.title + ' ' + i.summary + ' ' + i.source + ' ' + (i.origTitle || '')).toLowerCase().includes(q));
  }
  return items;
}

// ---------------------------------------------------------------- render
function heat(i) {
  if (i.big) return 1;
  if (i.pct == null) return 0;
  return i.pct >= 96 ? .7 : i.pct >= 90 ? .45 : i.learned ? .45 : i.pct >= 85 ? .25 : .1;
}
function line(i) {
  const done = !!copied[i.id];
  const open = expanded.has(i.id);
  const m = [`<span class="s">${esc(i.source)}</span>`, `<span>${ago(i.published || i.found)}</span>`];
  if (i.big) m.push(`<span class="hot" title="Stor historie">●${i.outlets}</span>`);
  else if (i.confirmed >= 2) m.push(`<span class="ok" title="Bekræftet af ${i.confirmed} medier">✓${i.confirmed}</span>`);
  if (i.confirmed === 0) m.push('<span class="q" title="Ubekræftet: kun Telegram/YouTube">?</span>');
  if (i.to) m.push(`<span title="Oversat">${i.from === 'en' ? '' : esc(i.from)}→${i.to}</span>`);
  if (done) m.push('<span class="cp">kopieret</span>');
  const also = i.also || [];
  return `<article class="item${done ? ' done' : ''}${i.big ? ' big' : ''}" id="c-${esc(i.id)}">
    <div class="swipe"><svg><use href="#i-copy"/></svg>Kopiér</div>
    <div class="row" data-swipe="${esc(i.id)}">
      <i class="heat" style="--heat:${heat(i)}"></i>
      <div class="body">
        <button class="h" data-open="${esc(i.id)}" dir="auto" aria-expanded="${open}">${esc(i.title)}</button>
        <div class="m">${m.join('')}${also.length && !open ? `<span>+${also.length}</span>` : ''}</div>
        ${open ? `<div class="x">
          ${i.summary ? `<p dir="auto">${esc(i.summary)}</p>` : ''}
          <div class="acts">
            <a href="${esc(i.link)}" target="_blank" rel="noopener">Åbn artikel ↗</a>
            <button data-copy="${esc(i.id)}">Kopiér</button>
            <button data-copy-sum="${esc(i.id)}">Kopiér med resumé</button>
          </div>
          ${also.length ? `<ul class="also">${also.map((a, k) => `<li><span><b>${esc(a.source)}</b>${foreignMode === 'original' || readable(a.title) ? ` · <span dir="auto">${esc(a.title)}</span>` : ' · på arabisk'}</span><button data-copy-also="${esc(i.id)}:${k}" aria-label="Kopiér"><svg><use href="#i-copy"/></svg></button></li>`).join('')}</ul>` : ''}
        </div>` : ''}
      </div>
      <button class="c" data-copy="${esc(i.id)}" aria-label="Kopiér"><svg><use href="#i-${done ? 'check' : 'copy'}"/></svg></button>
    </div>
  </article>`;
}

// the Claude editor's overview, shown at the top of "Vigtigste" for 12 hours
function overview() {
  if (!digest || !digest.created || Date.now() - new Date(digest.created) > 12 * 3600e3) return '';
  const items = digest.items || [];
  return `<section class="ov${overviewOpen ? '' : ' short'}">
    <div class="ov-head">Overblik <span>${esc(digest.period || '')} · ${clock(digest.created)}</span><button data-copy-ov>Kopiér</button></div>
    ${digest.intro && overviewOpen ? `<p class="ov-intro">${esc(digest.intro)}</p>` : ''}
    <ol>${items.map(x => `<li><div><a href="${esc(x.link)}" target="_blank" rel="noopener"><b>${esc(x.headline)}</b></a>${x.text ? `<small>${esc(x.text)}</small>` : ''}</div><em>${esc(x.source || '')}</em></li>`).join('')}</ol>
    <button class="ov-more" data-toggle-ov>${overviewOpen ? 'Vis kort' : 'Vis med tekst'}</button>
  </section>`;
}

const isStale = () => data && data.updated && (Date.now() - new Date(data.updated)) / 60000 > 60;
function renderHeader() {
  const stale = isStale();
  $('pulse').classList.toggle('stale', !!stale);
  $('status').classList.toggle('stale', !!stale);
  const mins = data ? Math.round((Date.now() - new Date(data.updated)) / 60000) : 0;
  $('status').textContent = !data ? 'henter …' : stale ? 'ikke opdateret siden ' + clock(data.updated)
    : mins < 1 ? 'opdateret nu' : `opdateret for ${mins} min. siden`;
  $('n-top').textContent = data ? itemsFor('top').length : '';
  $('n-all').textContent = data ? itemsFor('all').length : '';
  const n = Object.keys(copied).length;
  $('n-copied').textContent = n || '';
}

function render() {
  renderHeader();
  if (!data) { $('list').innerHTML = '<p class="empty">Henter nyheder …</p>'; return; }
  const items = visibleItems();
  let html = isStale() ? `<p class="notice">Nabd har ikke hentet nyt siden ${clock(data.updated)}. Listen kan være forældet.</p>` : '';
  if (tab === 'top' && !query) html += overview();
  if (!items.length) html += `<p class="empty">${tab === 'copied' ? 'Det, du kopierer, samles her.' : query ? 'Intet matcher søgningen.' : 'Ingen vigtige nyheder lige nu.'}</p>`;
  let last = '';
  for (const i of items) {
    const d = dayLabel(i.published || i.found);
    if (d !== last && tab !== 'copied') { html += `<div class="day">${d}</div>`; last = d; }
    html += line(i);
  }
  $('list').innerHTML = html;
  if (focusId && !render.focused) {
    const el = $('c-' + focusId);
    if (el) { render.focused = true; expanded.add(focusId); el.scrollIntoView({ block: 'center' }); }
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
function toast(msg) {
  $('toast').textContent = msg; $('toast').classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 1500);
}
async function copyItem(id, withSummary) {
  const raw = data && data.items.find(x => x.id === id);
  const i = raw ? display(raw) : (copied[id] && { id, ...copied[id] });
  if (!i || !(await copyText(copyTextFor(i, withSummary || danish)))) return;
  copied[id] = { at: Date.now(), title: i.title, link: i.link, source: i.source, words: words(i.origTitle || i.title) };
  store.set('copied', copied);
  render();
  toast('Kopieret');
  learnFrom(i);
}

$('list').addEventListener('click', async e => {
  const t = e.target;
  const hit = sel => t.closest(sel);
  if (hit('[data-copy-ov]')) {
    const text = digest.whatsapp || (digest.items || []).map(x => `*${x.headline}*\n${x.text || ''}\n${x.link}`).join('\n\n');
    if (await copyText(text)) toast('Overblikket er kopieret');
  } else if (hit('[data-toggle-ov]')) {
    overviewOpen = !overviewOpen; render();
  } else if (hit('[data-copy-sum]')) {
    copyItem(hit('[data-copy-sum]').dataset.copySum, true);
  } else if (hit('[data-copy]')) {
    copyItem(hit('[data-copy]').dataset.copy);
  } else if (hit('[data-copy-also]')) {
    const [id, k] = hit('[data-copy-also]').dataset.copyAlso.split(':');
    const x = data.items.find(i => i.id === id).also[+k];
    if (await copyText(`${x.title}\n${x.link}`)) toast('Kopieret');
  } else if (hit('[data-open]')) {
    const id = hit('[data-open]').dataset.open;
    expanded.has(id) ? expanded.delete(id) : expanded.add(id);
    render();
  }
});

// ---------------------------------------------------------------- swipe right to copy
let sw = null;
$('list').addEventListener('touchstart', e => {
  const row = e.target.closest('[data-swipe]');
  if (!row || e.touches.length > 1) return;
  sw = { row, id: row.dataset.swipe, x: e.touches[0].clientX, y: e.touches[0].clientY, dx: 0, mode: null };
}, { passive: true });
$('list').addEventListener('touchmove', e => {
  if (!sw) return;
  const dx = e.touches[0].clientX - sw.x, dy = e.touches[0].clientY - sw.y;
  if (!sw.mode) {
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
    sw.mode = dx > 0 && Math.abs(dx) > Math.abs(dy) * 1.4 ? 'swipe' : 'scroll';
    if (sw.mode === 'swipe') sw.row.classList.add('dragging');
  }
  if (sw.mode !== 'swipe') return;
  sw.dx = Math.max(0, dx);
  sw.row.style.transform = `translateX(${sw.dx < 80 ? sw.dx : 80 + (sw.dx - 80) * 0.3}px)`;
}, { passive: true });
$('list').addEventListener('touchend', () => {
  if (!sw) return;
  const { row, id, dx, mode } = sw;
  sw = null;
  if (mode !== 'swipe') return;
  row.classList.remove('dragging');
  row.style.transform = '';
  if (dx > 80) copyItem(id);
});

// ---------------------------------------------------------------- pull down to refresh (status line shows it)
let pull = null;
addEventListener('touchstart', e => { if (scrollY <= 0 && !e.target.closest('dialog')) pull = { y: e.touches[0].clientY, d: 0 }; }, { passive: true });
addEventListener('touchmove', e => {
  if (!pull) return;
  pull.d = e.touches[0].clientY - pull.y;
  if (scrollY > 0) { pull = null; return; }
  if (pull.d > 70) $('status').textContent = 'slip for at opdatere';
}, { passive: true });
addEventListener('touchend', () => {
  if (!pull) return;
  const go = pull.d > 70;
  pull = null;
  if (go) { $('status').textContent = 'opdaterer …'; load(true); }
});

// ---------------------------------------------------------------- header controls
$('tabs').addEventListener('click', e => {
  const b = e.target.closest('[data-tab]'); if (!b) return;
  if (b.dataset.tab === tab) { scrollTo({ top: 0, behavior: 'smooth' }); return; }
  tab = b.dataset.tab;
  document.querySelectorAll('#tabs [data-tab]').forEach(x => x.setAttribute('aria-selected', x === b));
  render(); scrollTo(0, 0);
});
$('searchBtn').addEventListener('click', () => {
  $('tabs').hidden = true; $('searchbar').hidden = false; $('search').focus();
});
$('searchClose').addEventListener('click', () => {
  query = ''; $('search').value = ''; $('searchbar').hidden = true; $('tabs').hidden = false; render();
});
$('search').addEventListener('input', e => { query = e.target.value.trim(); render(); });
$('status').addEventListener('click', () => { $('status').textContent = 'opdaterer …'; load(true); });
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(renderHeader, 30000);

// ---------------------------------------------------------------- settings + notifications
const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
function b64ToBytes(s) {
  const p = '='.repeat((4 - s.length % 4) % 4), b = atob((s + p).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(b, c => c.charCodeAt(0));
}
async function refreshPushInfo() {
  const info = $('pushInfo'), btn = $('enablePush');
  btn.hidden = true;
  if (!standalone && /iPhone|iPad/.test(navigator.userAgent)) {
    info.innerHTML = 'Læg først Nabd på hjemmeskærmen: <b>Del</b> → <b>Føj til hjemmeskærm</b> i Safari, og åbn den derfra.';
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
    if (perm !== 'granted') { toast('Notifikationer blev ikke tilladt'); return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(CFG.vapidPublicKey) });
    showCode(sub); $('enablePush').hidden = true;
    $('pushInfo').textContent = 'Næsten færdig – send koden herunder til Claude.';
  } catch (e) { toast('Det lykkedes ikke: ' + e.message); }
});
$('copyPushCode').addEventListener('click', async () => { if (await copyText($('pushCodeText').value)) toast('Koden er kopieret'); });
$('openSettings').addEventListener('click', () => {
  const src = Object.entries((data && data.sources) || {});
  $('srcCount').textContent = src.length || '–';
  const L = (data && data.learned) || {};
  $('scanned').textContent = data && data.scanned_24h ? `Seneste døgn: ${data.scanned_24h.toLocaleString('da-DK')} nye nyheder vurderet. Lært af ${(L.community || 0).toLocaleString('da-DK')} indlæg fra miljøets kilder, ${L.big || 0} store historier og ${L.copied || 0} kopieringer.` : '';
  $('sources').innerHTML = src.sort((a, b) => a[0].localeCompare(b[0], 'da'))
    .map(([n, v]) => `<li class="${v.ok ? '' : 'bad'}">${esc(n)}</li>`).join('');
  $('settings').showModal();
  refreshPushInfo();
});
$('settings').addEventListener('click', e => { if (e.target === $('settings')) $('settings').close(); });
document.querySelectorAll('input[name="foreign"]').forEach(r => {
  r.checked = r.value === foreignMode;
  r.addEventListener('change', () => { foreignMode = r.value; store.set('foreignMode', foreignMode); render(); });
});
$('danish').checked = danish;
$('danish').addEventListener('change', e => { danish = e.target.checked; store.set('danish', danish); render(); });
$('closeSettings').addEventListener('click', () => $('settings').close());

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
render();
load();
