// Nyhedsradar – phone app. Reads data.json written by the radar and shows it as a copy-friendly list.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

let data = { items: [], sources: {} };
let tab = 'top', query = '';
let copied = store.get('copied', {});
let foreignMode = store.get('foreignMode', 'translate');   // translate | hide | original         // id -> {at, title, link, source, words}
const expanded = new Set();
const focusId = new URLSearchParams(location.search).get('item');

// ---------------------------------------------------------------- learning from copies
const STOP = new Set(('og i at det er en til på som de med for af ikke der har jeg om var vi kan man den så hvad men ved skal fra eller nu også have efter blev mod over efter mere siger sagt nye ' +
  'the and of to in a is that for on are with as it this was by be has have from at they their not an or who will its but were been after says said over new more').split(' '));
const words = t => [...new Set((t.toLowerCase().match(/[\p{L}]{4,}/gu) || []).filter(w => !STOP.has(w)))];
const copiedWordSets = () => Object.values(copied).filter(c => Date.now() - c.at < 30 * 864e5).map(c => new Set(c.words));
function likeCopied(item, sets) {
  const w = words(item.title);
  if (w.length < 2) return false;
  return sets.some(s => w.filter(x => s.has(x)).length >= Math.min(3, Math.ceil(w.length * 0.4)));
}

// Each copy silently tells the radar "more like this" (no extra tap; only the public headline is sent).
function learnFrom(i) {
  if (!CFG.feedbackTopic) return;
  fetch('https://ntfy.sh/' + CFG.feedbackTopic, {
    method: 'POST', body: JSON.stringify({ kind: 'up', id: i.id, title: i.title, summary: (i.summary || '').slice(0, 220) }),
  }).catch(() => { /* offline: the local learning above still applies */ });
}

// ---------------------------------------------------------------- time
const rtf = new Intl.RelativeTimeFormat('da', { numeric: 'auto' });
function ago(iso) {
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60) return 'lige nu';
  if (s < 3600) return rtf.format(-Math.round(s / 60), 'minute');
  if (s < 86400) return rtf.format(-Math.round(s / 3600), 'hour');
  return rtf.format(-Math.round(s / 86400), 'day');
}
function dayLabel(iso) {
  const d = new Date(iso), t = new Date();
  const y = new Date(t); y.setDate(t.getDate() - 1);
  if (d.toDateString() === t.toDateString()) return 'I dag';
  if (d.toDateString() === y.toDateString()) return 'I går';
  return d.toLocaleDateString('da-DK', { weekday: 'long', day: 'numeric', month: 'long' });
}
const isRtl = s => /[؀-ۿ]/.test(s || '');

// ---------------------------------------------------------------- data
async function load(manual) {
  const btn = $('refresh');
  btn.classList.add('spin');
  try {
    const r = await fetch(CFG.dataUrl + (CFG.dataUrl.includes('?') ? '&' : '?') + 't=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    data = await r.json();
    store.set('lastData', data);
  } catch (e) {
    const cached = store.get('lastData', null);
    if (cached) data = cached;
    if (manual) toast('Kunne ikke hente nye nyheder');
  } finally {
    btn.classList.remove('spin');
  }
  render();
}

// ---------------------------------------------------------------- render
const LANG_NAME = { ar: 'arabisk', tr: 'tyrkisk' };
// what the card shows: Danish/English as-is, other languages translated unless the user wants the original
function display(i) {
  if (!i.foreign || foreignMode === 'original' || !i.title_tr) return i;
  return { ...i, title: i.title_tr, summary: i.summary_tr || '', translatedFrom: LANG_NAME[i.lang] || i.lang };
}
const readable = t => !/[؀-ۿ]/.test(t || '');
function visibleItems() {
  const sets = copiedWordSets();
  let items = data.items.map(display)
    .filter(i => !i.foreign || (foreignMode === 'original' || (foreignMode === 'translate' && i.title_tr)))
    .map(i => ({ ...i, learned: !i.important && likeCopied(i, sets) }));
  if (tab === 'top') items = items.filter(i => i.important || i.learned);
  if (tab === 'copied') items = Object.entries(copied).sort((a, b) => b[1].at - a[1].at)
    .map(([id, c]) => data.items.find(i => i.id === id) || { id, title: c.title, link: c.link, source: c.source, found: new Date(c.at).toISOString(), summary: '', also: [] });
  if (query) {
    const q = query.toLowerCase();
    items = items.filter(i => (i.title + ' ' + i.summary + ' ' + i.source).toLowerCase().includes(q));
  }
  return items;
}

function card(i) {
  const badges = [];
  if (i.big) badges.push(`<span class="badge big">Stor historie · ${i.outlets} medier</span>`);
  else if (i.important) badges.push('<span class="badge top">Meget relevant</span>');
  else if (i.learned) badges.push('<span class="badge top">Ligner det du kopierer</span>');
  if (i.translatedFrom) badges.push(`<span class="badge">Oversat fra ${esc(i.translatedFrom)}</span>`);
  const isCopied = !!copied[i.id];
  const also = i.also || [];
  return `<article class="card" id="c-${esc(i.id)}">
    <div class="meta"><span class="src">${esc(i.source)}</span><span>${ago(i.published || i.found)}</span>${badges.join('')}</div>
    <p class="title" dir="auto">${esc(i.title)}</p>
    ${i.summary ? `<p class="summary" dir="auto">${esc(i.summary)}</p>` : ''}
    <div class="actions">
      <button class="copy${isCopied ? ' done' : ''}" data-copy="${esc(i.id)}">${isCopied ? 'Kopieret ✓' : 'Kopiér'}</button>
      <a class="open" href="${esc(i.link)}" target="_blank" rel="noopener">Åbn</a>
    </div>
    ${also.length ? `<button class="more" data-more="${esc(i.id)}">${expanded.has(i.id) ? 'Skjul' : `Også hos ${also.length} ${also.length === 1 ? 'anden kilde' : 'andre kilder'}`}</button>` : ''}
    ${also.length && expanded.has(i.id) ? `<ul class="also">${also.map((a, n) =>
      `<li><span><b>${esc(a.source)}</b>${foreignMode === 'original' || readable(a.title) ? ` · <span dir="auto">${esc(a.title)}</span>` : ' · <i>på arabisk</i>'}</span><button data-copy-also="${esc(i.id)}:${n}">Kopiér</button></li>`).join('')}</ul>` : ''}
  </article>`;
}

function render() {
  $('updated').textContent = data.updated ? 'Opdateret ' + ago(data.updated) : 'Henter …';
  const items = visibleItems();
  if (!items.length) {
    $('list').innerHTML = `<p class="empty">${tab === 'copied' ? 'Du har ikke kopieret noget endnu.' : query ? 'Ingen nyheder matcher søgningen.' : 'Ingen nyheder lige nu.'}</p>`;
    return;
  }
  let html = '', last = '';
  for (const i of items) {
    const d = dayLabel(i.published || i.found);
    if (d !== last && tab !== 'copied') { html += `<div class="day">${d}</div>`; last = d; }
    html += card(i);
  }
  $('list').innerHTML = html;
  if (focusId && !render.focused) {
    const el = $('c-' + focusId);
    if (el) { render.focused = true; el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2500); }
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
  const t = $('toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 1600);
}

$('list').addEventListener('click', async e => {
  const c = e.target.closest('[data-copy]'), m = e.target.closest('[data-more]'), a = e.target.closest('[data-copy-also]');
  if (c) {
    const raw = data.items.find(x => x.id === c.dataset.copy);
    const i = raw ? display(raw) : (copied[c.dataset.copy] && { id: c.dataset.copy, ...copied[c.dataset.copy] });
    if (!i) return;
    if (await copyText(`${i.title}\n${i.link}`)) {
      copied[i.id] = { at: Date.now(), title: i.title, link: i.link, source: i.source, words: words(i.title) };
      store.set('copied', copied);
      c.classList.add('done'); c.textContent = 'Kopieret ✓';
      toast('Kopieret – klar til WhatsApp');
      learnFrom(i);
    }
  } else if (a) {
    const [id, n] = a.dataset.copyAlso.split(':');
    const x = data.items.find(i => i.id === id).also[+n];
    if (await copyText(`${x.title}\n${x.link}`)) { a.textContent = '✓'; toast('Kopieret'); }
  } else if (m) {
    expanded.has(m.dataset.more) ? expanded.delete(m.dataset.more) : expanded.add(m.dataset.more);
    render();
  }
});

document.querySelector('.tabs').addEventListener('click', e => {
  const b = e.target.closest('[data-tab]'); if (!b) return;
  tab = b.dataset.tab;
  document.querySelectorAll('.tabs button').forEach(x => x.setAttribute('aria-selected', x === b));
  render(); scrollTo(0, 0);
});
$('search').addEventListener('input', e => { query = e.target.value.trim(); render(); });
$('refresh').addEventListener('click', () => load(true));
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(() => { $('updated').textContent = data.updated ? 'Opdateret ' + ago(data.updated) : ''; }, 30000);

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
    info.innerHTML = 'Læg først appen på hjemmeskærmen: tryk på <b>Del</b>-knappen i Safari og vælg <b>Føj til hjemmeskærm</b>. Åbn den derfra, så kan notifikationer slås til.';
    return;
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) { info.textContent = 'Denne browser understøtter ikke notifikationer.'; return; }
  const reg = await Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(r, 4000))]);
  if (!reg) { info.textContent = 'Notifikationer kan ikke slås til i denne browser. Åbn appen fra hjemmeskærmen på din iPhone.'; return; }
  const sub = await reg.pushManager.getSubscription();
  if (sub && Notification.permission === 'granted') {
    info.textContent = 'Notifikationer er slået til på denne telefon. Du får besked ved store historier og de allervigtigste nyheder (højst ca. 15 om dagen, ikke mellem kl. 23 og 7).';
    showCode(sub);
  } else {
    info.textContent = 'Få besked ved store historier og de allervigtigste nyheder – højst ca. 15 om dagen og aldrig mellem kl. 23 og 7.';
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
  const src = Object.entries(data.sources || {});
  $('srcCount').textContent = src.length || '–';
  const L = data.learned || {};
  $('scanned').textContent = data.scanned_24h ? `Det seneste døgn er ${data.scanned_24h.toLocaleString('da-DK')} nye nyheder blevet vurderet. Lige nu har radaren selv lært af ${(L.community || 0).toLocaleString('da-DK')} indlæg fra miljøets egne kilder, ${L.big || 0} store historier og ${L.copied || 0} kopieringer.` : '';
  $('sources').innerHTML = src.sort((a, b) => a[0].localeCompare(b[0], 'da'))
    .map(([n, v]) => `<li class="${v.ok ? '' : 'bad'}" title="${v.ok ? 'Virker' : 'Kunne ikke hentes ved sidste kørsel'}">${esc(n)}</li>`).join('');
  $('settings').showModal();
  refreshPushInfo();
});
document.querySelectorAll('input[name="foreign"]').forEach(r => {
  r.checked = r.value === foreignMode;
  r.addEventListener('change', () => { foreignMode = r.value; store.set('foreignMode', foreignMode); render(); });
});
$('closeSettings').addEventListener('click', () => $('settings').close());

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
const cached = store.get('lastData', null);
if (cached) { data = cached; render(); }
load();
