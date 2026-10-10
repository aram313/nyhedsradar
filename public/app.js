// Nyhedsradar – phone app. Reads data.json written by the radar (and digest.json written by the
// Claude editor) and shows them as a copy-friendly list.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

let data = { items: [], sources: {} };
let digest = store.get('lastDigest', null);
let tab = 'top', query = '';
let copied = store.get('copied', {});                        // id -> {at, title, link, source, words}
let foreignMode = store.get('foreignMode', 'translate');      // translate | hide | original
let danish = store.get('danish', false);                      // show and copy in Danish
const expanded = new Set();
const params = new URLSearchParams(location.search);
const focusId = params.get('item');
let digestOpen = params.get('digest') === '1';

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
    method: 'POST', body: JSON.stringify({ kind: 'up', id: i.id, title: i.origTitle || i.title, summary: (i.origSummary || i.summary || '').slice(0, 220) }),
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
const clock = iso => new Date(iso).toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' });

// ---------------------------------------------------------------- data
const bust = url => url + (url.includes('?') ? '&' : '?') + 't=' + Date.now();
async function load(manual) {
  const btn = $('refresh');
  btn.classList.add('spin');
  try {
    const r = await fetch(bust(CFG.dataUrl), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    data = await r.json();
    store.set('lastData', data);
  } catch (e) {
    const cached = store.get('lastData', null);
    if (cached) data = cached;
    if (manual) toast('Kunne ikke hente nye nyheder');
  }
  if (CFG.digestUrl) {
    try {
      const r = await fetch(bust(CFG.digestUrl), { cache: 'no-store' });
      if (r.ok) { digest = await r.json(); store.set('lastDigest', digest); }
    } catch { /* keep the last overview */ }
  }
  btn.classList.remove('spin');
  render();
}

// ---------------------------------------------------------------- what a card shows
const LANG_NAME = { ar: 'arabisk', tr: 'tyrkisk', en: 'engelsk' };
// Danish/English as-is; other languages translated unless the user wants the original;
// with the Danish setting on, everything that has a Danish version is shown in Danish.
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary };
  if (i.foreign && foreignMode !== 'original' && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', translatedFrom: LANG_NAME[i.lang] || i.lang };
  }
  if (danish && i.title_da && !(i.foreign && foreignMode === 'original')) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', translatedFrom: d.translatedFrom || LANG_NAME[i.lang] || i.lang };
  }
  return d;
}
const readable = t => !/[؀-ۿ]/.test(t || '');
function copyTextFor(d) {
  if (!danish) return `${d.title}\n${d.link}`;
  const first = (d.summary || '').split(/(?<=[.!?])\s/)[0].replace(/\s*…$/, '');
  return `*${d.title}*\n${first ? first + '\n' : ''}${d.link}`;
}

function visibleItems() {
  const sets = copiedWordSets();
  let items = data.items
    .filter(i => !i.foreign || foreignMode === 'original' || (foreignMode === 'translate' && i.title_tr))
    .map(display)
    .map(i => ({ ...i, learned: !i.important && likeCopied(i, sets) }));
  if (tab === 'top') items = items.filter(i => i.important || i.learned);
  if (tab === 'copied') items = Object.entries(copied).sort((a, b) => b[1].at - a[1].at)
    .map(([id, c]) => { const x = data.items.find(i => i.id === id); return x ? display(x) : { id, title: c.title, link: c.link, source: c.source, found: new Date(c.at).toISOString(), summary: '', also: [] }; });
  if (query) {
    const q = query.toLowerCase();
    items = items.filter(i => (i.title + ' ' + i.summary + ' ' + i.source + ' ' + (i.origTitle || '')).toLowerCase().includes(q));
  }
  return items;
}

// ---------------------------------------------------------------- render
function card(i) {
  const badges = [];
  if (i.big) badges.push(`<span class="badge big">Stor historie · ${i.outlets} medier</span>`);
  else if (i.important) badges.push('<span class="badge top">Meget relevant</span>');
  else if (i.learned) badges.push('<span class="badge top">Ligner det du kopierer</span>');
  if (i.confirmed === 0) badges.push('<span class="badge warn">Ubekræftet · kun Telegram/YouTube</span>');
  else if (i.confirmed >= 2 && !i.big) badges.push(`<span class="badge ok">Bekræftet af ${i.confirmed} medier</span>`);
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

// the Claude editor's overview, shown at the top of "Vigtigste" for 12 hours
function digestCard() {
  if (!digest || !digest.created || Date.now() - new Date(digest.created) > 12 * 3600e3) return '';
  const items = digest.items || [];
  return `<article class="card digest" id="digest">
    <div class="meta"><span class="src">Dagens overblik · ${esc(digest.period || '')}</span><span>kl. ${clock(digest.created)}</span><span class="badge">Skrevet af Claude</span></div>
    ${digest.intro ? `<p class="summary intro">${esc(digest.intro)}</p>` : ''}
    <ol class="digest-list${digestOpen ? '' : ' short'}">${items.map(x =>
      `<li><b>${esc(x.headline)}</b>${x.text ? ` – ${esc(x.text)}` : ''} <a href="${esc(x.link)}" target="_blank" rel="noopener">${esc(x.source || 'Læs')}</a></li>`).join('')}</ol>
    <div class="actions">
      <button class="copy" data-copy-digest="1">Kopiér hele overblikket</button>
      <button class="open" data-toggle-digest="1">${digestOpen ? 'Vis mindre' : 'Vis alle'}</button>
    </div>
  </article>`;
}

function staleBanner() {
  if (!data.updated) return '';
  const mins = (Date.now() - new Date(data.updated)) / 60000;
  return mins > 60 ? `<p class="stale">Radaren har ikke opdateret siden kl. ${clock(data.updated)}. Nyhederne herunder kan være forældede.</p>` : '';
}

function render() {
  $('updated').textContent = data.updated ? 'Opdateret ' + ago(data.updated) : 'Henter …';
  const items = visibleItems();
  let html = staleBanner() + (tab === 'top' && !query ? digestCard() : '');
  if (!items.length) {
    html += `<p class="empty">${tab === 'copied' ? 'Du har ikke kopieret noget endnu.' : query ? 'Ingen nyheder matcher søgningen.' : 'Ingen nyheder lige nu.'}</p>`;
  }
  let last = '';
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
  if (e.target.closest('[data-copy-digest]')) {
    const text = digest.whatsapp || (digest.items || []).map(x => `*${x.headline}*\n${x.text || ''}\n${x.link}`).join('\n\n');
    if (await copyText(text)) toast('Overblikket er kopieret');
  } else if (e.target.closest('[data-toggle-digest]')) {
    digestOpen = !digestOpen; render();
  } else if (c) {
    const raw = data.items.find(x => x.id === c.dataset.copy);
    const i = raw ? display(raw) : (copied[c.dataset.copy] && { id: c.dataset.copy, ...copied[c.dataset.copy] });
    if (!i) return;
    if (await copyText(copyTextFor(i))) {
      copied[i.id] = { at: Date.now(), title: i.title, link: i.link, source: i.source, words: words(i.origTitle || i.title) };
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
    info.textContent = 'Notifikationer er slået til på denne telefon. Du får besked ved store historier, de allervigtigste nyheder og dagens overblik kl. 7 og 17 (højst ca. 15 om dagen, ikke mellem kl. 23 og 7).';
    showCode(sub);
  } else {
    info.textContent = 'Få besked ved store historier, de allervigtigste nyheder og dagens overblik – højst ca. 15 om dagen og aldrig mellem kl. 23 og 7.';
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
$('danish').checked = danish;
$('danish').addEventListener('change', e => { danish = e.target.checked; store.set('danish', danish); render(); });
$('closeSettings').addEventListener('click', () => $('settings').close());

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
const cachedData = store.get('lastData', null);
if (cachedData) { data = cachedData; render(); }
load();
