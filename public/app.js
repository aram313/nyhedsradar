// Khabar – phone app. Reads data.json (stories with their section, rank, coverage and a small picture, written
// by the radar every few minutes) and digest.json (the editor's recap of the day, written at 21: the day's most
// important movements as short 'Who: what' lines by topic, in the style of Al Jazeera's breaking wire).
// Front page = today's most important stories, then the latest recap; a tab per section – Danmark, Mellemøsten,
// Verden – and 'Live feed', everything as it comes in, compact like a ticker. Search over everything the radar has read. Plain JS.
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
const TITLES = { home: 'Khabar', latest: 'Live feed', search: 'Søg' };
// the small pictures live next to data.json on the data branch
const THUMBS = CFG.thumbUrl || (CFG.dataUrl || '').replace(/data\.json.*$/, 't/');

let data = store.get('lastData', null);
let digest = store.get('lastDigest', null);
let tab = 'home', query = '';
let shared = store.get('shared', null) || store.get('copied', {});   // id -> {at, title, link, source}
let foreignMode = store.get('foreignMode', 'translate');                 // translate | hide | original
let danish = store.get('danish', false);                                 // show and share in Danish
const expanded = new Set();                                              // opened stories
const params = new URLSearchParams(location.search);
let focusId = params.get('item');
let lastSeen = store.get('lastSeen', 0);                                 // stories found later get a small dot
const seenTab = store.get('seenTab', {});                                // when each tab was last looked at
let shownIds = new Set();
const scrollPos = {};                                                    // each tab remembers where you were
let searchIndex = null, searchState = 'idle';
let moves = null, archiveState = 'idle';                                 // earlier days, fetched on request
let goOverview = params.has('digest');                                   // a notification about the overview opens on it
let latestAll = false;
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
  if (d.toDateString() === new Date().toDateString()) return 'kl. ' + clock(iso);
  if (d.toDateString() === y.toDateString()) return 'i går kl. ' + clock(iso);
  return d.toLocaleDateString('da-DK', { weekday: 'short' }) + ' ' + clock(iso);
}
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
function dayLabel(iso) {
  const d = new Date(iso), t = new Date(), y = new Date(t);
  y.setDate(t.getDate() - 1);
  const full = d.toLocaleDateString('da-DK', { weekday: 'long', day: 'numeric', month: 'long' });
  if (d.toDateString() === t.toDateString()) return 'I dag · ' + full;
  if (d.toDateString() === y.toDateString()) return 'I går · ' + full;
  return cap(full);
}
const when = i => new Date(i.published || i.found).getTime();
const hours = i => Math.max(0, (Date.now() - when(i)) / 3600e3);
const num = n => Number(n || 0).toLocaleString('da-DK');

// ---------------------------------------------------------------- data
// 'no-cache' asks the server whether the file changed (a few bytes when it did not); the files live behind a
// cache that ignores query strings, so adding one never made them fresher
let busy = 0, offline = false;
async function load(manual) {
  busy++; document.body.classList.add('loading');
  let changed = false;
  const wasOffline = offline;
  try {
    const r = await fetch(CFG.dataUrl, { cache: 'no-cache' });
    if (!r.ok) throw new Error(r.status);
    const fresh = await r.json();
    offline = false;
    if (!data || fresh.updated !== data.updated) { changed = true; data = fresh; store.set('lastData', data); }
  } catch (e) {
    offline = true;
    if (manual) toast('Ingen forbindelse', false);
  }
  if (CFG.digestUrl) {
    try {
      const r = await fetch(CFG.digestUrl, { cache: 'no-cache' });
      if (r.ok) {
        const d = await r.json();
        const stamp = x => x && `${x.created}|${(x.topics || []).map(tp => (tp.lines || []).length + (tp.stories || []).length).join(',')}|${JSON.stringify(x.editor || '').length}`;
        if (stamp(d) !== stamp(digest)) { changed = true; moves = null; archiveState = 'idle'; digest = d; store.set('lastDigest', digest); }
      }
    } catch { /* keep the last overview */ }
  }
  if (--busy === 0) document.body.classList.remove('loading');
  if (changed || manual || offline !== wasOffline) render({ fresh: true }); else renderHeader();
}

// ---------------------------------------------------------------- what a story shows
// Danish/English as-is; other languages translated unless the user wants the original;
// with the Danish setting on, everything that has a Danish version is shown in Danish.
// channel posts open with alarm emoji and tags ('⚡️', 'Breaking |', 'عاجل |'); a headline needs none
const TAGS = new RegExp('^(?:[\\u2190-\\u2bff\\u{1f000}-\\u{1faff}\\ufe0f\\u200d\\s]'
  + '|(?:breaking|urgent|watch|video|update|just in|عاجل|متابعة|فيديو)\\s*[|:\\-–]\\s*'
  + '|(?:gaza|west bank|lebanon|lebanese|syria|syrian|yemen|yemeni|iran|iranian|iraqi|israeli|hebrew|palestinian|local|medical|security)'
  + ' sources\\s+(?!say|said|report|told|claim))+', 'iu');
const tidy = t => (t || '').replace(TAGS, '') || t;
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary, kw: i.kw || [] };
  if (i.foreign && foreignMode !== 'original' && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', from: i.lang, to: 'en', kw: i.kw_tr || [] };
  }
  if (danish && i.title_da && !(i.foreign && foreignMode === 'original')) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', from: d.from || i.lang, to: 'da', kw: i.kw_da || [] };
  }
  d.title = tidy(d.title);
  return d;
}
// the words that say who and where (the radar finds them) in bold; the rest of the headline stays plain
function bold(text, words = []) {
  const at = [], letter = /[\p{L}\p{N}]/u;
  const whole = (i, w) => !(i > 0 && letter.test(text[i - 1])) && !letter.test(text[i + w.length] || '');   // not 'Russia' in 'Russian'
  for (const w of words) {
    if (!w) continue;
    let i = text.indexOf(w);
    while (i >= 0 && (!whole(i, w) || at.some(([a, b]) => i < b && i + w.length > a))) i = text.indexOf(w, i + 1);
    if (i >= 0) at.push([i, i + w.length]);
  }
  let out = '', p = 0;
  for (const [a, b] of at.sort((x, y) => x[0] - y[0])) { out += esc(text.slice(p, a)) + '<b>' + esc(text.slice(a, b)) + '</b>'; p = b; }
  return out + esc(text.slice(p));
}
const readable = t => !/[؀-ۿ]/.test(t || '');
// the owner's hand (admin): stories removed or moved from this phone, at once, before the radar has caught up
let adminKey = store.get('adminKey', '');
const ownerGone = store.get('ownerGone', {}), ownerMoved = store.get('ownerMoved', {});
const gone = i => !!ownerGone[i.id] || (i.also || []).some(a => ownerGone[a.id]);
const visible = i => !gone(i) && (!i.foreign || foreignMode === 'original' || (foreignMode === 'translate' && i.title_tr));
// the editor (07, 15, 21) lifts stories that matter most, moves stories that landed in the wrong section and picks
// the best statements; a story is known by any of its outlets' articles, since its card may change lead
const notes = () => (digest && digest.editor) || { picks: [], moves: [], quotes: [] };
const noteFor = (list, i) => list.find(x => x.id === i.id || (i.also || []).some(a => a.id === x.id));
const secOf = i => (ownerMoved[i.id] || noteFor(notes().moves || [], i) || {}).sec || i.sec || (i.lang === 'da' ? 'dk' : 'world');
// the owner's front-page choices: what the radar published (data.owner), overlaid by this phone's own actions until a
// radar run newer than them has come in
let ownerLocal = store.get('ownerLocal', { rank: {} });
function owner() {
  const pub = (data && data.owner) || {}, since = data ? Date.parse(data.updated) : 0, fresh = x => x && x.at > since;
  const rank = { ...(pub.rank || {}) };
  for (const [id, x] of Object.entries(ownerLocal.rank || {})) if (fresh(x)) { if (x.v) rank[id] = x.v; else delete rank[id]; }
  return { quote: fresh(ownerLocal.quote) ? ownerLocal.quote.v : pub.quote || '', lead: fresh(ownerLocal.lead) ? ownerLocal.lead.v : pub.lead || '', rank };
}
const ownerRankOf = i => { const r = owner().rank; return r[i.id] || (i.also || []).map(a => r[a.id]).find(Boolean) || ''; };
const pickRank = i => {
  const o = ownerRankOf(i);
  if (o === 'up') return -1;       // raised by the owner: before the editor's picks
  if (o === 'down') return 99;     // lowered: no longer a pick
  const p = notes().picks || [], k = p.findIndex(x => x.id === i.id || (i.also || []).some(a => a.id === x.id)); return k < 0 ? 99 : k;
};
// the editor's picks first (in its order), then the radar's strongest
const withPicks = (list, n) => { const mine = list.filter(i => pickRank(i) < 99).sort((a, b) => pickRank(a) - pickRank(b));
  return [...mine, ...pick(list.filter(i => pickRank(i) === 99), n)].slice(0, n); };
// a story the editor moved lives only in its new section; otherwise it may also show where the radar saw it
const inSection = (i, sec) => ownerMoved[i.id] || noteFor(notes().moves || [], i) ? secOf(i) === sec : secOf(i) === sec || (i.secs || []).includes(sec);
const rankOf = i => {
  const base = i.rank ?? i.pct ?? 0, x = (ownerLocal.rank || {})[i.id];
  return data && x && x.at > Date.parse(data.updated) ? base + (x.v === 'up' ? 30 : x.v === 'down' ? -30 : 0) : base;
};
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
// a story can be found by any of its outlets' articles: its card follows whichever article leads it right now
const findStory = id => find(id) || stories().find(i => (i.also || []).some(a => a.id === id));

function shareText(d) {
  let first = (d.summary || '').split(/(?<=[.!?])\s/)[0].replace(/\s*…$/, '').trim();
  // the rest of a cut-off sentence, a link or a sign-off is no summary
  if (first.length < 20 || /^[a-zæøå]/.test(first) || /^(https?:|www\.|\[)/i.test(first)) first = '';
  return `*${d.title}*\n${first ? first + '\n' : ''}${d.link}`;
}

// ---------------------------------------------------------------- render: one story
// a row: the headline with its names in bold, one quiet line below (big story, section, outlet, time),
// a small picture at the right – or the outlet's initials where no picture exists
// DR, BT, TV2, BBC as written; QudsN → QN; Al Jazeera → AJ; Politiken → P
function monogram(name) {
  const w = String(name || '').replace(/\(.*?\)/g, '').split(/[\s\-–]+/).filter(x => x && !/^(the|of|og|and|for)$/i.test(x));
  if (!w.length) return '?';
  if (/^[A-ZÆØÅ]{2,4}$/.test(w[0])) return w[0] + (/^\d+$/.test(w[1] || '') ? w[1] : '');
  const caps = w[0].replace(/[^A-ZÆØÅ]/g, '');
  if (w.length === 1) return caps.length > 1 ? caps.slice(0, 3) : w[0][0].toUpperCase();
  return (w[0][0] + w[1][0]).toUpperCase();
}
function thumb(source, file) {
  return `<span class="th" aria-hidden="true"><b>${esc(monogram(source))}</b>${file
    ? `<img src="${esc(THUMBS + file)}" alt="" loading="lazy" decoding="async" onerror="this.remove()">` : ''}</span>`;
}
function meta(i, opts = {}) {
  const m = [];
  if (i.big && !opts.top) m.push('<span class="big">Topnyhed</span>');   // under 'Døgnets vigtigste' it goes without saying
  if (opts.tag) m.push(`<span class="sec"><i></i>${SECTIONS[secOf(i)]}</span>`);   // mixed lists say where it belongs
  m.push(`<span class="src">${esc(i.source)}</span>`);
  if (!opts.tick) m.push(`<span>${opts.clock ? 'kl. ' + clock(i.published || i.found) : ago(i.published || i.found)}</span>`);   // the ticker has its own time column
  if (i.outlets >= 3 && !opts.tag) m.push(`<span>${i.outlets} medier</span>`);
  if (i.confirmed === 0) m.push('<span class="warn">ubekræftet</span>');
  if (shared[i.id]) m.push('<span class="done">delt</span>');
  return m.join('');
}
function story(i, n, opts = {}) {
  const open = expanded.has(i.id);
  if (opts.hero) return heroStory(i, n, opts);
  const cls = ['story', opts.tick ? 'tick' : i.thumb && 'pic', i.important && 'imp', open && 'open', isNew(i) && 'new', opts.enter && n < 12 && 'enter',
    opts.fresh && shownIds.size && !shownIds.has(i.id) && 'fresh'].filter(Boolean).join(' ');
  return `<article class="${cls}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" data-sec="${secOf(i)}"${opts.tag ? ' data-tag="1"' : ''}${opts.clock ? ' data-clock="1"' : ''}${opts.top ? ' data-top="1"' : ''} style="--i:${n}">
    <button class="row" data-toggle aria-expanded="${open}">${opts.tick ? `<time class="tt">${clock(i.published || i.found)}</time>` : ''}<span class="tx"><span class="h" dir="auto">${bold(i.title, i.kw)}</span><span class="m">${meta(i, opts)}</span></span>${opts.tick ? '' : thumb(i.source, i.thumb)}</button>
    <div class="x"><div><div class="x-in">${open ? detail(i) : ''}</div></div></div></article>`;
}
// the day's lead story: its own picture big (the outlet's original, else our small copy), headline on top of it
function heroStory(i, n, opts) {
  const open = expanded.has(i.id), small = THUMBS + i.thumb;
  return `<article class="story hero${open ? ' open' : ''}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" data-sec="${secOf(i)}" data-tag="1" data-top="1" style="--i:${n}">
    <button class="hero-row" data-toggle aria-expanded="${open}"><img src="${esc(i.pic || small)}" alt="" decoding="async"
      onerror="if (this.src !== '${esc(small)}') this.src = '${esc(small)}'"><span class="hero-tx"><span class="h" dir="auto">${bold(i.title, i.kw)}</span>
      <span class="m">${meta(i, opts)}</span></span></button>
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
    const own = foreignMode === 'original' || readable(a.title);
    const title = own ? `<span dir="auto">${esc(tidy(a.title))}</span>`
      : a.title_tr ? `<span>${esc(tidy(a.title_tr))}</span> <i>oversat</i>` : `<i>overskrift på ${LANG[a.lang] || 'arabisk'}</i>`;
    return `<a href="${esc(a.link)}" target="_blank" rel="noopener"><b>${esc(a.source)}</b>${title}</a>`;
  }).join('')).join('');
  const sum = coverSummary(i.cover), more = (i.outlets || 1) - 1 - also.length;
  return `<div class="cov"><div class="cov-h">Dækning · ${i.outlets} medier</div>${sum ? `<div class="cov-sum">${sum}</div>` : ''}${rows}${more > 0
    ? `<div class="cov-more">+ ${more} ${more === 1 ? 'medie' : 'medier'} mere</div>` : ''}</div>`;
}

// ---------------------------------------------------------------- the overview of the day
// One recap per day, added to at 7, 15 and 21: the day's most important movements as short lines – 'Who: what', in the style
// of Al Jazeera's breaking wire and the group's own 'Politiske nyheder' posts – grouped by topic, newest first. It
// closes the front page and replaces the day before; earlier days wait in the archive below it.
const SHOW = 4;   // lines a topic shows before '+ n mere'
const ymd = iso => new Date(iso).toLocaleDateString('sv-SE');   // the local date as 2026-10-10
const dateDa = (ymdStr, weekday) => new Date(ymdStr + 'T12:00:00').toLocaleDateString('da-DK',
  weekday ? { weekday: 'long', day: 'numeric', month: 'long' } : { day: 'numeric', month: 'long' });
// a day from the editor; an edition from before days existed (an old copy in the phone's memory) becomes one
function dayOf(d) {
  if (!d || !d.created) return null;
  if (d.date) return d;
  const at = d.created;
  return { date: ymd(at), created: at, updates: [at], title: d.title || 'Politiske nyheder', topics: (d.topics || []).map(tp => ({
    name: tp.name, section: tp.section, lines: [
      ...(tp.stories || []).map(s => ({ who: '', text: s.headline, link: s.link, source: s.source, at, added: at, id: s.id, kind: 's', confirmed: s.confirmed })),
      ...(tp.lines || []).map(l => ({ who: l.who, text: l.text, link: l.link, source: 'Al Jazeera', at, added: at, id: l.id, kind: 'w' }))] })) };
}
const lineCount = day => day.topics.reduce((s, tp) => s + tp.lines.length, 0);
const dayOpen = new Set();     // topics opened beyond their first lines: '<date>|<name>'
const daysOpen = new Set();    // earlier days opened in the archive
function findDay(date) {
  const d = dayOf(digest);
  return d && d.date === date ? d : ((moves && moves.days) || []).map(dayOf).find(x => x && x.date === date);
}
// one line: the time at the left (a line from before midnight says so), who in bold, then what – the whole line
// opens the source; lines that came while the user was away get a small dot
function lineHtml(l, day) {
  const fresh = lastSeen && l.added && new Date(l.added).getTime() > lastSeen;
  const time = `<time>${clock(l.at)}${ymd(l.at) < day.date ? '<small>i går</small>' : ''}</time>`;
  const body = `<span>${l.who ? `<b>${esc(l.who)}:</b> ` : ''}${esc(l.text)}${l.confirmed === 0 ? ' <i>ubekræftet</i>' : ''}</span>`;
  return `<li${fresh ? ' class="new"' : ''}>${l.link ? `<a href="${esc(l.link)}" target="_blank" rel="noopener" data-line="${esc(l.id)}"${l.kind === 's' ? ' data-story="1"' : ''}>`
    : '<span>'}${time}${body}${l.link ? '</a>' : '</span>'}</li>`;
}
function dayTopic(day, tp) {
  const k = `${day.date}|${tp.name}`, all = tp.lines, open = dayOpen.has(k) || all.length <= SHOW + 1;
  return `<div class="dt" data-sec="${esc(tp.section)}"><h3><i></i>${esc(tp.name)}</h3>
    <ul class="dl">${(open ? all : all.slice(0, SHOW)).map(l => lineHtml(l, day)).join('')}</ul>${open ? ''
    : `<button class="dt-more" data-day-more="${esc(k)}">+ ${all.length - SHOW} mere</button>`}</div>`;
}
function dayBody(day) {
  return `<div class="ov-body" data-day="${esc(day.date)}">${day.topics.map(tp => dayTopic(day, tp)).join('')}
    <div class="ov-acts"><button data-day-share><svg><use href="#i-share"/></svg>Del resumé</button></div></div>`;
}
// the share text, in the format members post themselves (digest.json brings it ready for the newest day)
function dayText(day) {
  if (digest && digest.date === day.date && digest.created === day.created && digest.whatsapp) return digest.whatsapp;
  return [day.title || 'Politiske nyheder', ...day.topics.map(tp => `${tp.name}\n\n${tp.lines.map(l => `- ${l.who ? l.who + ': ' : ''}${l.text}`).join('\n\n')}`)].join('\n\n');
}
// the newest recap (written at 21, it covers the day since 21 the evening before) replaces the one before
let recapOpen = false;
function overview() {
  const day = dayOf(digest);
  if (!day || Date.now() - new Date(day.created) > 48 * 3600e3) {
    return `<section class="ov" id="overview"><div class="ov-row"><span><b>Resumé</b><small>Dagens vigtigste bevægelser – kommer kl. 7, 15 og 21</small></span></div></section>`;
  }
  const n = lineCount(day), hrs = [...new Set((day.updates || [day.created]).map(u => new Date(u).getHours()))];
  const said = hrs.length < 2 ? hrs.join('') : hrs.slice(0, -1).join(', ') + ' og ' + hrs[hrs.length - 1];
  return `<section class="ov${recapOpen ? ' open' : ''}" id="overview"><button class="ov-row" data-recap aria-expanded="${recapOpen}">
    <span><b>Resumé · ${dateDa(day.date, true)}</b><small>Dagens vigtigste bevægelser · ${n} linjer · opdateret kl. ${said}</small></span>
    <svg><use href="#i-chev"/></svg></button>${recapOpen ? dayBody(day) : ''}</section>`;
}
async function loadArchive() {
  if (archiveState === 'loading') return;
  archiveState = 'loading';
  const url = CFG.movesUrl || (CFG.digestUrl || '').replace(/digest\.json$/, 'moves.json');
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) throw new Error(r.status);
    moves = await r.json(); archiveState = 'ok';
  } catch { archiveState = 'error'; }
  if (tab === 'home') render();
}
// earlier days: one row each, opened in place
// earlier days: the last three always in view (one row each, opened in place), the rest behind 'Vis flere dage'
let archAll = false;
const topOpen = new Set();   // sections whose 'Døgnets vigtigste' is unfolded
function archive() {
  if (!moves) {
    if (archiveState === 'idle') setTimeout(loadArchive, 0);   // fetched as soon as the front page shows
    const note = archiveState === 'error' ? 'kunne ikke hente – prøv igen' : 'henter …';
    return `<div class="arch-h">Tidligere dage</div><div class="arch"><button class="arch-row" data-archive><span><small>${note}</small></span></button></div>`;
  }
  const current = dayOf(digest);
  const list = (moves.days || []).map(dayOf).filter(d => d && d.topics.length && (!current || d.date !== current.date));
  if (!list.length) return '<div class="arch-h">Tidligere dage</div><p class="explain pad">Hver dag lægges her, når den næste begynder.</p>';
  const shown = archAll ? list : list.slice(0, 3);
  return '<div class="arch-h">Tidligere dage</div>' + shown.map(day => {
    const open = daysOpen.has(day.date), n = lineCount(day);
    return `<article class="arch${open ? ' open' : ''}" data-arch="${esc(day.date)}">
      <button class="arch-row" data-arch-toggle aria-expanded="${open}"><span><b>${cap(dateDa(day.date, true))}</b>
      <small>${n} ${n === 1 ? 'linje' : 'linjer'} · ${day.topics.length} emner</small></span><svg><use href="#i-chev"/></svg></button>
      ${open ? dayBody(day) : ''}</article>`;
  }).join('') + (list.length > 3 && !archAll ? `<button class="wide soft" data-arch-all>Vis flere dage (${list.length - 3})</button>` : '');
}

// ---------------------------------------------------------------- render: pages
// headings: a block ('Døgnets vigtigste') is a large title; a day ('I dag', 'I går') is a coloured marker
// that stays at the top while its stories scroll past
const blockHead = (title, more) => `<div class="block-h"><h2><i class="live"></i>${title}</h2>${more || ''}</div>`;
function timeline(list, opts, n0 = 0) {
  let html = '', last = '', n = n0;
  [...list].sort((a, b) => when(b) - when(a)).forEach(i => {
    const d = dayLabel(i.published || i.found);
    if (d !== last) { html += `<div class="day"><span>${d}</span></div>`; last = d; }
    html += story(i, n++, opts);
  });
  return html;
}
// the front page: today's most important stories (all sections), then the latest recap of a day, then earlier days
// ---------------------------------------------------------------- front-page pieces: Lige nu, Dagens citat, the main story's timeline
let wire = null, wireState = 'idle';   // the latest short lines (Al Jazeera urgent and outlets' headlines), in Danish
async function loadWire() {
  if (wireState !== 'idle') return;
  wireState = 'loading';
  try {
    const url = CFG.linesUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'lines.json');
    const r = await fetch(url, { cache: 'no-cache' });
    wire = (await r.json()).items || [];
  } catch { wire = []; }
  wireState = 'done';
  if (tab === 'home') render();
}
// 'Lige nu': the three newest lines from established outlets (no unverified channels), with their time
function nowStrip() {
  if (!wire) { setTimeout(loadWire, 0); return '<section class="now"><div class="now-h"><i></i>Lige nu</div><p class="now-wait">henter …</p></section>'; }
  const last = wire.filter(v => (v.k === 'w' || v.k === 'h') && v.da).sort((a, b) => b.p.localeCompare(a.p)).slice(0, 3);
  if (!last.length) return '';
  return `<section class="now"><div class="now-h"><i></i>Lige nu</div><ul>${last.map(v =>
    `<li><a href="${esc(v.u)}" target="_blank" rel="noopener"><time>${clock(v.p)}</time><span>${esc(v.da)}</span><em>${esc(v.s)}</em></a></li>`).join('')}</ul></section>`;
}
// 'Dagens citat': the editor's first chosen statement, large
// The owner can hold the front page's quote and pick another: the editor's chosen statements and today's recap lines.
// A short key (from who and text) travels to the radar, which publishes it for everyone (data.json owner.quote).
const qkey = q => { let h = 0x811c9dc5; for (const c of q.who + '|' + q.text) h = Math.imul(h ^ c.codePointAt(0), 16777619) >>> 0; return h.toString(16).padStart(8, '0'); };
function quoteChoices() {
  const day = dayOf(digest), seen = new Set(), out = [];
  // when it was said: the recap line's time, or that of the wire line the editor quoted (matched by link)
  const when = new Map();
  if (day) day.topics.forEach(tp => tp.lines.forEach(l => { if (l.link && l.at) when.set(l.link, l.at); }));
  (wire || []).forEach(v => { if (v.u && !when.has(v.u)) when.set(v.u, v.p); });
  const add = (q, sec) => { if (!q.who || !q.text) return; const k = qkey(q); if (!seen.has(k)) { seen.add(k); out.push({ ...q, sec: q.sec || sec, key: k, at: q.at || when.get(q.link) || '' }); } };
  (notes().quotes || []).forEach(q => add(q));
  if (day) day.topics.forEach(tp => tp.lines.filter(l => l.kind !== 's').forEach(l => add(l, tp.section)));   // statements, not headlines
  return out.slice(0, 16);
}
function pinnedQuote() {
  const key = owner().quote;
  return key ? quoteChoices().find(q => q.key === key) || null : null;
}
function quoteOfDay(pinned) {
  const told = new Set((followTopic() || { lines: [] }).lines.map(l => l.who));   // not one the timeline already shows
  const qs = notes().quotes || [], q = pinned || qs.find(x => !told.has(x.who)) || qs[0];
  return q ? `<section class="qday" data-sec="${esc(q.sec || '')}"><div class="qday-h">Dagens citat</div>${quoteCard(q, true)}</section>` : '';
}
// 'Følg historien': the day's first topic from the recap as a small timeline, oldest first
const followTopic = () => { const day = dayOf(digest); return day && day.topics.find(t => t.lines.filter(l => l.at).length >= 3); };
// ---------------------------------------------------------------- the front page, organised by story and time
// 1. the day in a sentence, 2. the day's main story as one package: picture and
// headline, how it developed and a statement from it, 3. the rest of the day's top,
// 4. 'Lige nu' further down, 5. the sections and the recap as before.
const STOP = new Set(['angreb', 'angrebet', 'angrebene', 'amerikansk', 'israelsk', 'efter', 'under', 'siger', 'mange', 'flere', 'denne', 'dette', 'imod', 'mellem', 'omkring', 'about', 'after',
  'against', 'their', 'there', 'which', 'would', 'could', 'other', 'says', 'said', 'while', 'where', 'today']);
const stems = t => new Set((t || '').toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(w => w.length >= 5 && !STOP.has(w)).map(w => w.slice(0, 6)));
const overlap = (a, b) => { let n = 0; for (const w of a) if (b.has(w)) n++; return n; };
const topicStems = tp => stems(tp.name + ' ' + tp.lines.map(l => l.who + ' ' + l.text).join(' '));
// the story the recap's lead topic is about: the top story sharing most words with it
function mainPackage(cands) {
  const tp = followTopic();
  if (!tp) return null;
  const ts = topicStems(tp);
  let best = null, score = 1;
  for (const i of cands) {
    const sc = overlap(stems([i.title, i.origTitle, i.title_da, ...(i.also || []).map(a => a.title)].join(' ')), ts);
    if (sc > score || (sc === score && best && !best.thumb && i.thumb)) { best = i; score = sc; }
  }
  return best && { story: best, topic: tp, ts };
}
function packageQuote(pkg, told) {
  const qs = (notes().quotes || []).map(q => ({ q, sc: overlap(stems(q.who + ' ' + q.text), pkg.ts) })).filter(x => x.sc >= 3 && !told.has(x.q.who));
  qs.sort((a, b) => b.sc - a.sc);
  return qs[0] ? qs[0].q : null;
}
function storyline(tp, n = 4) {
  const lines = tp.lines.filter(l => l.at).sort((a, b) => a.at.localeCompare(b.at)).slice(-n);
  return { lines, html: `<div class="follow pkg-f"><div class="pkg-h">Sådan udviklede det sig</div><ol>${lines.map(l =>
    `<li><time>${clock(l.at)}</time><p>${l.who ? `<b>${esc(l.who)}:</b> ` : ''}${esc(l.text)}</p></li>`).join('')}</ol></div>` };
}
// today's strongest stories (the editor's picks and the owner's raised ones first)
function frontCands(all, n = 12) {
  const today = i => new Date(i.published || i.found).toDateString() === new Date().toDateString();
  let cands = all.filter(today);
  if (cands.length < 5) cands = all.filter(i => today(i) || hours(i) < 12);
  return withPicks(cands, n);
}
// the main story: the owner's choice, else the story of the recap's lead topic, else the strongest with a picture
function packageFor(story) {
  const day = dayOf(digest), st = stems([story.title, story.origTitle, story.title_da, ...(story.also || []).map(a => a.title)].join(' '));
  let best = null, score = 1;
  for (const tp of (day ? day.topics : []).filter(t => t.lines.filter(l => l.at).length >= 2)) {
    const sc = overlap(topicStems(tp), st);
    if (sc > score) { best = tp; score = sc; }
  }
  return { story, topic: best, ts: best ? topicStems(best) : st };
}
function mainChoice(top) {
  const pin = owner().lead, chosen = pin && findStory(pin);
  if (chosen) return packageFor(chosen);
  return mainPackage(top);
}
const mainStory = () => { const top = frontCands(stories()), pkg = mainChoice(top); return pkg ? pkg.story : top.find(i => i.thumb) || top[0]; };
function home(all, opts) {
  const top = frontCands(all), pkg = mainChoice(top);
  const lede = notes().lede, todayStr = new Date().toLocaleDateString('sv-SE');
  let html = `<header class="lede"><span>${cap(dateDa(todayStr, true))}</span>${lede ? `<p>${esc(lede)}</p>` : ''}</header>`;
  const lead = pkg ? pkg.story : top.find(i => i.thumb) || top[0];
  // the package's other stories about the same thing stay out of the lists below
  const same = i => pkg && i !== lead && overlap(stems([i.title, i.origTitle, i.title_da].join(' ')), pkg.ts) >= 3;
  const pin = pinnedQuote();
  let pq = null;
  if (lead) {
    // a Danish outlet's headline for the package when the story has one
    const dk = lead.lang !== 'da' && (lead.also || []).find(a => a.group === 'dk');
    const shown = dk ? { ...lead, title: dk.title, source: dk.source, kw: [] } : lead;
    html += `<section class="block top pkg" data-sec="${secOf(lead)}">${blockHead('Dagens historie')}${story(shown, 0, { ...opts, tag: true, top: true, hero: !!lead.thumb })}`;
    if (pkg && pkg.topic) {
      const tl = storyline(pkg.topic);
      pq = pin ? null : packageQuote(pkg, new Set(tl.lines.map(l => l.who)));
      html += tl.html + (pq ? `<div class="pkg-q">${quoteCard(pq, true)}</div>` : '');
    }
    html += '</section>';
  }
  const rest = top.filter(i => i !== lead && !same(i)).slice(0, 4);
  html += `<section class="block">${blockHead('Døgnets vigtigste', '<button class="more" data-go="latest">Live<svg><use href="#i-chev"/></svg></button>')}
    ${rest.map((i, n) => story(i, n + 1, { ...opts, tag: true, top: true })).join('')}</section>`;
  if (!pq) html += quoteOfDay(pin);   // no statement from the main story (or the owner picked one): the day's quote
  html += nowStrip().replace('</section>', '<button class="now-more" data-go="latest">Se alt i Live<svg><use href="#i-chev"/></svg></button></section>');
  const shown = new Set([lead, ...rest].filter(Boolean).map(i => i.id));
  const glance = Object.entries(SECTIONS).map(([sec, name]) => {
    const best = withPicks(all.filter(i => inSection(i, sec) && hours(i) < 24 && !shown.has(i.id) && !same(i)), 1)[0];
    return best ? `<button class="gl" data-go="${sec}" data-sec="${sec}"><b><i></i>${name}</b><span>${bold(best.title, best.kw)}</span><svg><use href="#i-chev"/></svg></button>` : '';
  }).join('');
  if (glance) html += `<section class="glance">${glance}</section>`;
  html += overview() + `<section class="block">${archive()}</section>`;
  const src = Object.keys(data.sources || {}).length, day = all.filter(i => hours(i) < 24).length;
  html += `<p class="foot">Khabar har læst ${num(data.scanned_24h)} nyheder fra ${src} kilder det seneste døgn<br>og valgt ${day} ud.</p>`;
  return html;
}
// a section page has a shape: one lead story big, two side by side, then the compact list – with now and then a
// statement from the day's recap set as a quote, so the page is not headline after headline
// the pair never changes shape: a tapped card is only marked, and its story opens in one panel under both
function cardStory(i, n, opts) {
  const sel = expanded.has(i.id);
  return `<article class="story card${sel ? ' sel' : ''}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" data-sec="${secOf(i)}" data-top="1" style="--i:${n}">
    <button class="card-row" data-toggle aria-expanded="${sel}"><span class="card-pic"><img src="${esc(THUMBS + i.thumb)}" alt="" loading="lazy" decoding="async"></span>
      <span class="h" dir="auto">${bold(i.title, i.kw)}</span><span class="m">${meta(i, { ...opts, top: true })}</span></button></article>`;
}
function duoBlock(duo, opts) {
  const sel = duo.find(i => expanded.has(i.id));
  return `<div class="duo-wrap"><div class="duo">${duo.map((i, n) => cardStory(i, n + 1, opts)).join('')}</div>
    <article class="story panel${sel ? ' open' : ''}"${sel ? ` data-id="${esc(sel.id)}"` : ''}><div class="x"><div><div class="x-in">${sel ? panelBody(sel) : ''}</div></div></div></article></div>`;
}
// the card cuts its headline after three lines; the panel starts with all of it
const panelBody = i => `<p class="ph" dir="auto">${bold(i.title, i.kw)}</p>` + detail(i);
function toggleCard(card) {
  const wrap = card.closest('.duo-wrap'), panel = wrap.querySelector('.panel'), was = wrap.querySelector('.story.card.sel');
  const mark = (c, on) => { c.classList.toggle('sel', on); c.querySelector('[data-toggle]').setAttribute('aria-expanded', on); on ? expanded.add(c.dataset.id) : expanded.delete(c.dataset.id); };
  if (was) mark(was, false);
  if (was === card) { panel.classList.remove('open'); return; }
  const i = find(card.dataset.id);
  if (!i) return;
  mark(card, true);
  panel.dataset.id = i.id;
  panel.querySelector('.x-in').innerHTML = panelBody(i);
  if (!was) { void panel.offsetHeight; panel.classList.add('open'); }
  keepInView(panel);
}
function quotesFor(sec) {
  const chosen = (notes().quotes || []).filter(q => q.sec === sec);
  if (chosen.length) return chosen;
  const day = dayOf(digest);
  return day ? day.topics.filter(tp => tp.section === sec).flatMap(tp => tp.lines.filter(l => l.who)) : [];
}
const quoteCard = (l, pick) => `<a class="quote"${pick ? ' data-pick' : ''} href="${esc(l.link || '#')}" target="_blank" rel="noopener"><q>${esc(l.text)}</q><span>${esc(l.who)}</span></a>`;
// 'N mere fra døgnet': a row with the hidden stories' small pictures, a chevron at the end; 'Vis færre' folds them back
function moreButton(sec, rest, fold) {
  const chev = '<svg aria-hidden="true"><use href="#i-chev"/></svg>';
  if (!fold) return `<button class="mv-b up" data-top-more="${sec}"><span>Vis færre</span>${chev}</button>`;
  return `<button class="mv-b" data-top-more="${sec}"><span class="mv-pics">${rest.slice(0, 4).map(i => i.thumb
    ? `<img src="${esc(THUMBS + i.thumb)}" alt="" onerror="this.replaceWith(document.createElement('i'))">` : '<i></i>').join('')}</span><span>${rest.length} mere fra døgnet</span>${chev}</button>`;
}
function sectionPage(sec, all, opts) {
  const list = all.filter(i => inSection(i, sec));
  if (!list.length) return '<div class="empty">Ingen historier her endnu.</div>';
  // the day's important stories; on a quiet day, the strongest few
  const imp = list.filter(i => hours(i) < 24 && i.important);
  const picked = list.filter(i => hours(i) < 24 && pickRank(i) < 99);
  const pool = [...new Set([...picked, ...(imp.length >= 3 ? imp : list.filter(i => hours(i) < 24))])];
  const top = withPicks(pool, imp.length >= 3 ? 7 : 5);
  const withPic = top.filter(i => i.thumb);
  const lead = withPic[0], duo = withPic.slice(1, 3).length === 2 ? withPic.slice(1, 3) : [];
  const rest = top.filter(i => i !== lead && !duo.includes(i));
  let html = `<section class="block top">${blockHead('Døgnets vigtigste')}`;
  if (lead) html += heroStory(lead, 0, { ...opts, top: true, tag: false });
  if (duo.length) html += duoBlock(duo, opts);
  // the rest of the day's top folds away, so the latest news follow right after the pictures
  const fold = (lead || duo.length) && !topOpen.has(sec);
  if (!fold) html += rest.map((i, n) => story(i, n + 3, { ...opts, top: true })).join('');
  if (rest.length && (lead || duo.length)) html += moreButton(sec, rest, fold);
  html += '</section>';
  // the list, with a quote from the recap after every fifth story
  const ids = new Set(top.map(i => i.id)), quotes = quotesFor(sec);
  let body = timeline(list.filter(i => !ids.has(i.id)), opts, top.length), k = 0, seen = 0;
  body = body.replace(/<\/article>/g, m => (++seen % 5 === 0 && k < quotes.length ? m + quoteCard(quotes[k++]) : m));
  return html + body;
}
// everything as it comes in, all sections mixed, newest first
function latestPage(all, opts) {
  const recent = latestAll ? all : all.filter(i => hours(i) < 24);
  let html = timeline(recent, { ...opts, tag: true, tick: true });
  if (recent.length < all.length) html += `<button class="wide soft" data-latest-all>Vis ældre (${all.length - recent.length})</button>`;
  return html;
}
// search ignores accents and Turkish letters (Erdogan finds Erdoğan); marks are set on the plain text, all at once
const fold = s => String(s || '').toLowerCase().replace(/ı/g, 'i').normalize('NFD').replace(/[̀-ͯ]/g, '');
function mark(text, terms) {
  const f = fold(text), at = [];
  if (f.length === text.length) {   // where folding changed the length, no marks rather than marks in the wrong place
    for (const t of terms) {
      for (let i = t.length > 1 ? f.indexOf(t) : -1; i >= 0; i = f.indexOf(t, i + t.length)) at.push([i, i + t.length]);
    }
  }
  let out = '', p = 0;
  for (const [a, b] of at.sort((x, y) => x[0] - y[0])) {
    if (a < p) continue;
    out += esc(text.slice(p, a)) + '<mark>' + esc(text.slice(a, b)) + '</mark>'; p = b;
  }
  return out + esc(text.slice(p));
}
function searchPage(all) {
  const q = fold(query.trim());
  const total = searchIndex ? searchIndex.items.length : (data.scanned_24h || 0);
  if (!q) return `<div class="empty">Søg i alle ${num(total)} nyheder, Khabar har læst de seneste to døgn – også dem, der ikke kom på listerne.</div>`;
  const terms = q.split(/\s+/).filter(Boolean);
  const hit = t => { const f = fold(t); return terms.every(w => f.includes(w)); };
  const inApp = all.filter(i => hit(`${i.title} ${i.summary || ''} ${i.source} ${i.origTitle || ''}`)).sort((a, b) => when(b) - when(a));
  let html = inApp.length ? `<div class="day"><span>På Khabar · ${inApp.length}</span></div>` + inApp.slice(0, 40).map((i, n) => story(i, n, { tag: true })).join('') : '';
  if (searchIndex) {
    const onApp = new Set(data.items.map(i => i.id));
    const others = searchIndex.items.filter(x => !onApp.has(x.i) && hit(`${x.t} ${x.s}`));
    if (others.length) html += `<div class="day"><span>Andre nyheder · ${others.length}</span></div>` + others.slice(0, 60).map(x =>
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
  $('status').setAttribute('aria-label', $('status').textContent + ' – tryk for at opdatere');
}
function render(opts = {}) {
  renderHeader();
  $('list').dataset.sec = SECTIONS[tab] ? tab : '';   // a section's own page takes its colour
  if (!data) { $('list').innerHTML = '<div class="skel"></div>'.repeat(8); return; }
  const all = stories();
  let html = offline ? `<p class="notice">Ingen forbindelse – viser nyhederne fra kl. ${clock(data.updated)}.</p>`
    : isStale() ? `<p class="notice">Khabar har ikke hentet nyt siden kl. ${clock(data.updated)}. Listen kan være forældet.</p>` : '';
  html += tab === 'home' ? home(all, opts) : tab === 'search' ? searchPage(all) : tab === 'latest' ? latestPage(all, opts)
    : sectionPage(tab, all, opts);
  $('list').innerHTML = `<div class="${opts.view && !reduceMotion ? 'view' : ''}">${html}</div>`;
  // new stories that arrived while the user was scrolled down: offer a pill instead of jumping
  const fresh = opts.fresh && shownIds.size ? all.filter(i => !shownIds.has(i.id)).length : 0;
  shownIds = new Set(all.map(i => i.id));
  if (fresh && scrollY > 240 && tab !== 'search') {
    $('freshPill').querySelector('span').textContent = `${fresh} ${fresh === 1 ? 'ny historie' : 'nye historier'}`;
    $('freshPill').hidden = false;
  }
  // a dot on a tab with something the user has not seen yet: a new update of the overview, or an important story
  // (a tab's dot goes once the tab has been looked at)
  const since = name => Math.max(lastSeen, seenTab[name] || 0);
  document.querySelector('.tabs [data-tab="home"]').classList.toggle('has-new',
    tab !== 'home' && !!(digest && digest.created && lastSeen && new Date(digest.created).getTime() > since('home')));
  document.querySelector('.tabs [data-tab="latest"]').classList.toggle('has-new', tab !== 'latest' &&
    all.some(i => i.found && new Date(i.found).getTime() > Math.max(since('latest'), Date.now() - 6 * 3600e3)));
  for (const sec of Object.keys(SECTIONS)) {
    document.querySelector(`.tabs [data-tab="${sec}"]`).classList.toggle('has-new', tab !== sec && all.some(i =>
      i.important && isNew(i) && secOf(i) === sec && new Date(i.found).getTime() > since(sec)));
  }
  if (focusId) openFocus(all);
  if (goOverview && tab === 'home' && $('overview')) {
    goOverview = false;
    if (!recapOpen) { recapOpen = true; render(); }
    setTimeout(() => { const o = $('overview'); if (o) scrollTo(0, o.getBoundingClientRect().top + scrollY - $('bar').offsetHeight - 8); }, 150);
  }
}
// a notification opens the app on its story: find it, open it, show it
function openFocus(all) {
  // the story may since have joined another outlet's card: then open that card
  const i = findStory(focusId);
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

// ---------------------------------------------------------------- open a story or a topic in place
function keepInView(el) {
  setTimeout(() => {
    const r = el.getBoundingClientRect(), limit = innerHeight - $('dock').offsetHeight - 12;
    if (r.bottom > limit) scrollBy({ top: Math.min(r.bottom - limit, r.top - 70), behavior: reduceMotion ? 'auto' : 'smooth' });
  }, 320);
}
function toggle(el) {
  const id = el.dataset.id, open = !el.classList.contains('open'), i = find(id);
  if (open && i) {
    el.querySelector('.x-in').innerHTML = detail(i);
    expanded.add(id);
    void el.offsetHeight;   // lay out the closed state first, so the opening animates
    el.classList.add('open');
    keepInView(el);
  } else {
    el.classList.remove('open'); expanded.delete(id);
  }
  el.querySelector('[data-toggle]').setAttribute('aria-expanded', open);
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
  if (el) { el.classList.remove('new'); el.querySelector('.m').innerHTML = meta(i, { tag: el.dataset.tag === '1', clock: el.dataset.clock === '1', top: el.dataset.top === '1', tick: el.classList.contains('tick') }); }
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
  if (t.closest('[data-recap]')) { recapOpen = !recapOpen; render(); return; }
  if (t.closest('[data-day-more]')) { dayOpen.add(t.closest('[data-day-more]').dataset.dayMore); render(); return; }
  if (t.closest('[data-day-share]')) { const d = findDay(t.closest('[data-day]').dataset.day); if (d) share(dayText(d)); return; }
  if (t.closest('[data-line]')) {   // a line that tells a story: opening it says 'more like this', quietly
    const a = t.closest('[data-line]'), r = a.dataset.story && findStory(a.dataset.line);
    if (r) learnFrom(r, 'read');
    return;
  }
  if (t.closest('[data-archive]')) { loadArchive(); return; }
  if (t.closest('[data-arch-all]')) { archAll = true; render(); return; }
  const more = t.closest('[data-top-more]');
  if (more) { const k = more.dataset.topMore; topOpen.has(k) ? topOpen.delete(k) : topOpen.add(k); render(); return; }
  if (t.closest('[data-arch-toggle]')) { const c = t.closest('[data-arch]').dataset.arch; daysOpen.has(c) ? daysOpen.delete(c) : daysOpen.add(c); render(); return; }
  if (t.closest('[data-latest-all]')) { latestAll = true; render(); return; }
  if (!el) return;
  if (t.closest('[data-share]')) share(shareText(i), i);
  else if (t.closest('[data-copy]')) { if (await copyText(shareText(i))) { toast('Kopieret'); markShared(i); } }
  else if (t.closest('[data-read]')) learnFrom(i, 'read');
  else if (t.closest('[data-toggle]')) el.classList.contains('card') ? toggleCard(el) : toggle(el);
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
addEventListener('touchcancel', () => {   // an interrupted pull must not leave the list pulled down
  if (!pull) return;
  pull = null;
  list.classList.remove('pulling'); list.style.transform = ''; ptr.style.opacity = 0; ptr.style.setProperty('--k', 0); ptr.classList.remove('ready');
});
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
  seenTab[tab] = Date.now(); seenTab[next] = Date.now(); store.set('seenTab', seenTab);
  tab = next;
  document.querySelectorAll('.tabs [data-tab]').forEach(x => x.setAttribute('aria-selected', x.dataset.tab === tab));
  $('title').textContent = TITLES[tab] || SECTIONS[tab];
  $('title').classList.remove('swap'); void $('title').offsetWidth; $('title').classList.add('swap');
  $('searchbar').hidden = tab !== 'search';
  if (tab === 'search') { loadIndex(); setTimeout(() => $('search').focus(), 60); } else $('search').blur();
  $('freshPill').hidden = true;
  render({ view: true });
  scrollTo(0, opts.top ? 0 : scrollPos[tab] || 0);
}
// everything the radar read in the last two days, fetched only when someone searches
let searchLoaded = 0;
async function loadIndex() {   // fetched again after a quarter of an hour: the app can stay open for days
  if (searchState === 'loading' || (searchIndex && Date.now() - searchLoaded < 15 * 60e3)) return;
  searchState = 'loading';
  const url = CFG.searchUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'search.json');
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) throw new Error(r.status);
    searchIndex = await r.json();
    searchLoaded = Date.now();
    searchState = 'ok';
  } catch { searchState = 'error'; }
  if (tab === 'search') render();
}
$('tabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) setTab(b.dataset.tab, { top: b.dataset.tab === tab }); });
$('openSearch').addEventListener('click', () => setTab('search', { top: true }));
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

// what counts as seen moves on only after a real break (10 minutes): a quick trip to WhatsApp to paste a story
// must not mark everything as seen
function backFromBreak() {
  const away = store.get('hiddenAt', 0);
  if (away && Date.now() - away > 10 * 60e3 && away > lastSeen) { lastSeen = away; store.set('lastSeen', lastSeen); }
}
backFromBreak();   // also when the phone closed the app in the background and it starts afresh
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { store.set('hiddenAt', Date.now()); seenTab[tab] = Date.now(); store.set('seenTab', seenTab); return; }
  backFromBreak();
  load();
});
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(renderHeader, 30000);

// ---------------------------------------------------------------- settings sheet: slides up, drag down to close
function openSheet() {
  const by = {};
  // one line per outlet name; red only after three failed runs in a row (one hiccup is no broken source)
  const named = {};
  Object.entries((data && data.sources) || {}).forEach(([n, v]) => {
    const label = v.label || n, bad = (v.failing_runs || 0) >= 3;
    if (named[label]) { named[label][1].bad = named[label][1].bad && bad; return; }
    named[label] = [label, { bad }];
    (by[v.group || 'west'] ||= []).push(named[label]);
  });
  $('sources').innerHTML = GROUP_ORDER.filter(g => by[g]).map(g => `<h4>${GROUPS[g]}</h4><ul>` + by[g].sort((a, b) => a[0].localeCompare(b[0], 'da'))
    .map(([n, v]) => `<li class="${v.bad ? 'bad' : ''}">${esc(n)}</li>`).join('') + '</ul>').join('');
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

// ---------------------------------------------------------------- the owner's hand (admin)
// Holding the logo for two seconds asks for the admin code. With it, holding a story down offers to remove it
// (irrelevant, not news, a duplicate) or move it to another section. Each action is signed with the code, so only
// the owner's phone counts: it hides here at once, for everyone at the next radar run, and the radar and the
// editor learn from it. Nobody else sees any of this.
const enc = new TextEncoder();
async function sign(text) {
  const k = await crypto.subtle.importKey('raw', enc.encode(adminKey), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return [...new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(text)))].map(b => b.toString(16).padStart(2, '0')).join('');
}
async function ownerAct(act, i, why = '', sec = '') {
  if (!CFG.feedbackTopic) return false;
  const at = String(Date.now()), m = { kind: 'admin', act, id: i.id, why, sec, at };
  try {
    m.sig = await sign(`${act}|${i.id}|${why}|${sec}|${at}`);
    return (await fetch('https://ntfy.sh/' + CFG.feedbackTopic, { method: 'POST', body: JSON.stringify(m) })).ok;
  } catch { return false; }
}
function keepOwner() {   // the radar has long caught up after three days
  for (const o of [ownerGone, ownerMoved]) for (const [k, v] of Object.entries(o)) if (Date.now() - v.at > 3 * 864e5) delete o[k];
  store.set('ownerGone', ownerGone); store.set('ownerMoved', ownerMoved);
  cache = null;
}
const applyAdmin = () => document.documentElement.classList.toggle('admin', !!adminKey);
applyAdmin(); keepOwner();
let logoHold, logoHeld = false;
const brand = document.querySelector('.brand');
brand.addEventListener('pointerdown', () => {
  clearTimeout(logoHold); logoHeld = false;
  logoHold = setTimeout(() => { logoHeld = true; openCode(); }, 1500);
});
for (const ev of ['pointerup', 'pointercancel']) brand.addEventListener(ev, () => clearTimeout(logoHold));
// a tap on the logo goes home, to the top of the front page (a long hold is the admin code, not a tap)
brand.addEventListener('click', () => { if (logoHeld) { logoHeld = false; return; } setTab('home', { top: true }); });
brand.addEventListener('keydown', e => { if (e.key === 'Enter') setTab('home', { top: true }); });
brand.addEventListener('contextmenu', e => e.preventDefault());
// the code goes in a small sheet of our own: a home-screen app may not show the browser's prompt
function openCode() {
  if (navigator.vibrate) navigator.vibrate(12);
  $('actTitle').textContent = adminKey ? 'Admin er slået til' : 'Admin-kode';
  $('actBtns').innerHTML = `<input id="adminCode" type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off"
    spellcheck="false" placeholder="xxxx-xxxx-xxxx-xxxx" aria-label="Admin-kode"><button class="wide primary" data-a="code">Gem</button>`
    + (adminKey ? '<button class="wide warn" data-a="code-off">Slå admin fra</button>' : '') + '<button class="wide soft" data-a="">Annuller</button>';
  actItem = null; $('act').hidden = false;
  requestAnimationFrame(() => { $('act').classList.add('on'); $('scrim').classList.add('on'); $('adminCode').focus(); });
}

let press = null, pressed = false, actItem = null;
const cancelPress = () => { if (press) clearTimeout(press.t); press = null; };
$('list').addEventListener('pointerdown', e => {
  const el = adminKey && (e.target.closest('[data-pick]') || e.target.closest('.story[data-id]'));
  if (!el) return;
  press = { x: e.clientX, y: e.clientY, t: setTimeout(() => {
    press = null; pressed = true; setTimeout(() => { pressed = false; }, 900);
    if (navigator.vibrate) navigator.vibrate(12);
    if (el.hasAttribute('data-pick')) openQuotes();
    else if (el.closest('.pkg') && el.classList.contains('hero')) openLead();
    else openAct(findStory(el.dataset.id));
  }, 550) };
});
$('list').addEventListener('pointermove', e => { if (press && Math.hypot(e.clientX - press.x, e.clientY - press.y) > 10) cancelPress(); });
for (const ev of ['pointerup', 'pointercancel']) $('list').addEventListener(ev, cancelPress);
addEventListener('scroll', cancelPress, { passive: true });
// the tap that ends a long press must not also open the story
$('list').addEventListener('click', e => { if (pressed) { pressed = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
$('list').addEventListener('contextmenu', e => { if (adminKey && e.target.closest('.story, [data-pick]')) e.preventDefault(); });
function showOwnerSheet(title, html, item = null) {
  $('actTitle').textContent = title;
  $('actBtns').innerHTML = html + '<button class="wide soft" data-a="">Annuller</button>';
  actItem = item; $('act').hidden = false; $('act').scrollTop = 0;
  requestAnimationFrame(() => { $('act').classList.add('on'); $('scrim').classList.add('on'); });
}
// the time a quote was said shows only here, to choose by; newest first
function openQuotes() {
  if (!wire) loadWire();
  const now = (pinnedQuote() || {}).key, list = quoteChoices().sort((a, b) => (b.at || '').localeCompare(a.at || ''));
  const when = q => (new Date(q.at).toDateString() === new Date().toDateString() ? 'kl. ' : 'i går kl. ') + clock(q.at);
  showOwnerSheet('Vælg dagens citat', `<button class="wide pickq${now ? '' : ' on'}" data-a="quote:"><b>Automatisk</b><span>Redaktørens valg</span></button>`
    + list.map(q => `<button class="wide pickq${q.key === now ? ' on' : ''}" data-a="quote:${q.key}"><q>${esc(q.text)}</q><span>${esc(q.who)}${q.at ? ` · ${when(q)}` : ''}</span></button>`).join(''));
}
// the day's main story: today's strongest stories to choose from
function openLead() {
  const cur = mainStory(), list = [cur, ...frontCands(stories(), 11).filter(i => !cur || i.id !== cur.id)].filter(Boolean).slice(0, 10);   // the one shown now first
  showOwnerSheet('Vælg dagens historie', `<button class="wide pickq${owner().lead ? '' : ' on'}" data-a="lead:"><b>Automatisk</b><span>Efter dagens resumé</span></button>`
    + list.map(i => `<button class="wide pickq${cur && i.id === cur.id ? ' on' : ''}" data-a="lead:${esc(i.id)}"><b>${esc(i.title)}</b><span>${SECTIONS[secOf(i)]} · ${ago(i.published || i.found)}${i.outlets >= 2 ? ` · ${i.outlets} medier` : ''}</span></button>`).join('')
    + (cur ? `<button class="wide" data-a="story:${esc(cur.id)}">Fjern, flyt eller prioriter denne historie</button>` : ''));
}
function openAct(i) {
  if (!i) return;
  const here = secOf(i), lift = ownerRankOf(i);
  const rank = [lift === 'up' ? ['rank:', 'Fortryd op'] : ['rank:up', 'Opprioriter'],
                lift === 'down' ? ['rank:', 'Fortryd ned'] : ['rank:down', 'Nedprioriter']];
  showOwnerSheet(i.title, `<div class="pair">${rank.map(([a, l]) => `<button class="wide" data-a="${a}">${esc(l)}</button>`).join('')}</div>`
    + [['hide:irrelevant', 'Fjern · irrelevant'], ['hide:noise', 'Fjern · ikke en nyhed'], ['hide:dup', 'Fjern · dublet'],
    ...Object.entries(SECTIONS).filter(([k]) => k !== here).map(([k, n]) => ['move:' + k, 'Flyt til ' + n])]
    .map(([a, l]) => `<button class="wide${a.startsWith('hide') ? ' warn' : ''}" data-a="${a}">${esc(l)}</button>`).join(''), i);
}
function closeAct() {
  $('act').classList.remove('on'); $('scrim').classList.remove('on');
  setTimeout(() => { if (!$('act').classList.contains('on')) $('act').hidden = true; }, 300);
}
$('scrim').addEventListener('click', closeAct);
$('act').addEventListener('click', async e => {
  const b = e.target.closest('[data-a]'), i = actItem;
  if (!b) return;
  if (b.dataset.a === 'code' || b.dataset.a === 'code-off') {
    adminKey = b.dataset.a === 'code' ? $('adminCode').value.trim().toLowerCase() : '';
    store.set('adminKey', adminKey); applyAdmin(); closeAct();
    toast(adminKey ? 'Admin slået til – hold en nyhed nede' : 'Admin slået fra');
    return;
  }
  closeAct();
  const kind = b.dataset.a.split(':')[0], val = b.dataset.a.slice(kind.length + 1);
  if (kind === 'story') { setTimeout(() => openAct(findStory(val)), 320); return; }
  if (kind === 'quote' || kind === 'lead') {
    ownerLocal[kind] = { v: val, at: Date.now() }; store.set('ownerLocal', ownerLocal); render();
    const ok = await ownerAct(kind, { id: val });
    const said = kind === 'quote' ? (val ? 'Citat valgt' : 'Citatet vælges automatisk igen') : (val ? 'Dagens historie valgt' : 'Dagens historie vælges automatisk igen');
    toast(ok ? said : 'Kunne ikke sende – prøv igen', ok);
    return;
  }
  if (kind === 'rank' && i) {
    (ownerLocal.rank ||= {})[i.id] = { v: val, at: Date.now() }; store.set('ownerLocal', ownerLocal); render();
    const ok = await ownerAct('rank', i, val);
    toast(ok ? (val === 'up' ? 'Opprioriteret' : val === 'down' ? 'Nedprioriteret' : 'Prioritering fortrudt') : 'Kunne ikke sende – prøv igen', ok);
    return;
  }
  if (!b.dataset.a || !i) return;
  const [act, arg] = b.dataset.a.split(':');
  if (act === 'hide') ownerGone[i.id] = { at: Date.now() }; else ownerMoved[i.id] = { at: Date.now(), sec: arg };
  keepOwner(); render();
  const ok = await ownerAct(act, i, act === 'hide' ? arg : '', act === 'move' ? arg : '');
  toast(ok ? (act === 'hide' ? 'Fjernet – Khabar lærer af det' : 'Flyttet til ' + SECTIONS[arg]) : 'Kunne ikke sende – prøv igen', ok);
});
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

// appearance: four light tones (Dæmpet first), four dark palettes (Notion first), and automatic / light / dark
const TONES = ['daempet', 'papir', 'klassisk', 'kolig'], DARKS = ['notion', 'grafit', 'material', 'apple'];
let tone = store.get('tone', 'daempet'), mode = store.get('mode', 'auto'), dark = store.get('dark', 'notion');
if (!TONES.includes(tone)) tone = 'daempet';   // e.g. 'blod', which no longer exists
if (!DARKS.includes(dark)) dark = 'notion';
function applyLook() {
  const d = document.documentElement;
  tone === 'daempet' ? delete d.dataset.tone : d.dataset.tone = tone;
  mode === 'auto' ? delete d.dataset.theme : d.dataset.theme = mode;
  dark === 'notion' ? delete d.dataset.dark : d.dataset.dark = dark;
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
// Android: Chrome offers to install Khabar once it qualifies; the settings keep that offer one tap away
let installEvent = null;
addEventListener('beforeinstallprompt', e => { installEvent = e; if (!$('sheet').hidden) refreshPushInfo(); });
addEventListener('appinstalled', () => { installEvent = null; $('installApp').hidden = true; });
$('installApp').addEventListener('click', async () => {
  if (!installEvent) return;
  installEvent.prompt();
  try { await installEvent.userChoice; } catch { /* closed */ }
  installEvent = null; refreshPushInfo();
});
// a phone signs up by itself: its push address goes to Khabar through the private relay (the radar picks it up
// within minutes); it is sent again once a week, so a lost one comes back on its own
async function tellKhabar(sub, kind = 'sub') {
  if (!CFG.feedbackTopic) return false;
  try {
    const r = await fetch('https://ntfy.sh/' + CFG.feedbackTopic, { method: 'POST', body: JSON.stringify({ kind, sub: sub.toJSON() }) });
    if (r.ok && kind === 'sub') store.set('phoneSent', Date.now());
    return r.ok;
  } catch { return false; }
}
async function refreshPushInfo() {
  const info = $('pushInfo'), btn = $('enablePush'), off = $('disablePush'), android = !standalone && /Android/.test(navigator.userAgent);
  btn.hidden = true; off.hidden = true;
  $('installHint').hidden = !android; $('installApp').hidden = !(android && installEvent);
  if (!standalone && /iPhone|iPad/.test(navigator.userAgent)) {
    info.innerHTML = 'Læg først Khabar på hjemmeskærmen: <b>Del</b> → <b>Føj til hjemmeskærm</b> i Safari, og åbn den derfra.';
    return;
  }
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) { info.textContent = 'Denne browser understøtter ikke notifikationer.'; return; }
  const reg = await Promise.race([navigator.serviceWorker.ready, wait(4000)]);
  if (!reg) { info.textContent = 'Notifikationer kan kun slås til i appen på hjemmeskærmen.'; return; }
  const sub = await reg.pushManager.getSubscription();
  if (sub && Notification.permission === 'granted') {
    info.textContent = 'Slået til: topnyheder, de allervigtigste nyheder og dagens resumé kl. 21. Højst ca. 15 om dagen, aldrig mellem kl. 23 og 7.';
    off.hidden = false;
  } else {
    info.textContent = 'Få besked ved topnyheder, de allervigtigste nyheder og dagens resumé.';
    btn.hidden = false;
  }
}
$('enablePush').addEventListener('click', async () => {
  try {
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') { toast('Notifikationer blev ikke tilladt', false); return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(CFG.vapidPublicKey) });
    if (await tellKhabar(sub)) { toast('Notifikationer er slået til'); refreshPushInfo(); }
    else toast('Ingen forbindelse – prøv igen om lidt', false);
  } catch (e) { toast('Det lykkedes ikke: ' + e.message, false); }
});
$('disablePush').addEventListener('click', async () => {
  const reg = await navigator.serviceWorker.ready, sub = await reg.pushManager.getSubscription();
  if (sub) { await tellKhabar(sub, 'unsub'); await sub.unsubscribe(); }
  toast('Notifikationer er slået fra'); refreshPushInfo();
});
(async () => {   // already signed up: remind Khabar once a week
  if (!('serviceWorker' in navigator) || Date.now() - store.get('phoneSent', 0) < 7 * 864e5) return;
  const reg = await Promise.race([navigator.serviceWorker.ready, wait(4000)]);
  const sub = reg && await reg.pushManager.getSubscription();
  if (sub && Notification.permission === 'granted') tellKhabar(sub);
})();

// an app, not a web page: no pinch zoom (iPhone ignores the viewport setting for pinching; CSS stops double-tap zoom)
['gesturestart', 'gesturechange'].forEach(ev => document.addEventListener(ev, e => e.preventDefault(), { passive: false }));
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
const startTab = params.get('tab');
if (startTab && (SECTIONS[startTab] || startTab === 'search' || startTab === 'latest')) setTab(startTab, { top: true });
else render({ enter: true });
load();

// ---------------------------------------------------------------- intro
// Every start: the name is written as with a reed pen – a flat nib held at an angle, in the order a calligrapher
// writes حبر: up and round the loop of ح, back along the line through the tooth of ب into the tail of ر, then the
// dot under ب, and last the red dot that makes it خ. The very first time the screen also says what Khabar is for
// and stays until 'Kom i gang'. A tap skips the short version.
(function intro() {
  const el = $('intro');
  if (!el) return;
  const first = !store.get('introSeen', false);
  const D = reduceMotion ? 0 : first ? 1.3 : 0.95;          // the main stroke's duration in seconds
  const done = () => { el.classList.add('gone'); setTimeout(() => el.remove(), 500); };
  const NS = 'http://www.w3.org/2000/svg', mask = $('inkMask');
  // the nib: a flat reed 50 wide, held at 60 degrees. Going up the first leg it moves almost along its own edge, so
  // the line is a hairline (10); from the top of the loop on it lies fuller on the paper (34, so no hair of the loop
  // shows through while it writes), and the broad part comes only as it crosses back along the line. Each step is
  // the hull of the nib where it was and where it is now, so the edges follow the nib's corners as smooth curves
  // (separate stamps would leave teeth); each shows when the pen gets there.
  const nibAt = (p, t) => [[-25, -t / 2], [25, -t / 2], [25, t / 2], [-25, t / 2]]
    .map(([x, y]) => [p.x + x * 0.5 + y * 0.866, p.y - x * 0.866 + y * 0.5]);     // rotated -60 degrees
  const hull = pts => {
    pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], up = [];
    for (const q of pts) { while (lo.length > 1 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
    for (const q of pts.reverse()) { while (up.length > 1 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  };
  // The first leg runs through the line as a thin strip: its edges are soft curves from the tail's edges below the
  // line into the leg's edges above it, so the stroke reads as one; the rest of the line's band where they cross
  // stays hidden until the pen crosses back along it (#inkBehind is the band with that strip cut out).
  const behind = document.createElementNS(NS, 'g');
  behind.setAttribute('mask', 'url(#inkBehind)'); mask.appendChild(behind);   // a mask, not a clip-path: masks are anti-aliased
  const write = (path, start, dur, thin) => {
    const L = path.getTotalLength(), n = Math.ceil(L / 1.5);
    let prev = null;
    for (let i = 0; i <= n; i++) {
      const len = L * i / n, p = path.getPointAtLength(len);
      const nib = nibAt(p, thin ? 10 + 24 * Math.min(1, Math.max(0, (len - 70) / 40)) : 26);
      const r = document.createElementNS(NS, 'polygon');
      r.setAttribute('class', 'nib'); r.setAttribute('fill', '#fff');
      r.setAttribute('points', hull(prev ? prev.concat(nib) : nib).map(q => q[0].toFixed(2) + ',' + q[1].toFixed(2)).join(' '));
      prev = nib;
      const x = Math.acos(1 - 2 * (i / n)) / Math.PI;      // the pen speeds up and slows down (sine ease)
      r.style.setProperty('--t', (start + x * dur).toFixed(3) + 's');
      (thin && len < 200 ? behind : mask).appendChild(r);
    }
  };
  const fill = at => {   // the last hair the nib missed: the whole word, settled at once when the pen lifts
    const r = document.createElementNS(NS, 'rect');
    r.setAttribute('class', 'nib'); r.setAttribute('width', 600); r.setAttribute('height', 400); r.setAttribute('fill', '#fff');
    r.style.setProperty('--t', at + 's'); mask.appendChild(r);
  };
  const start = () => {
    write($('inkPath'), 0.1, D, true);
    write($('inkDot'), 0.1 + D + 0.1, D * 0.15);
    fill(0.1 + D + 0.4);
    el.style.setProperty('--dot', (0.1 + D + 0.45).toFixed(2) + 's');
    if (first) $('introWhy').style.animationDelay = (0.1 + D + 0.8).toFixed(2) + 's';
    else { const t = setTimeout(done, (D + 1.6) * 1000); el.addEventListener('click', () => { clearTimeout(t); done(); }); }
  };
  if (first) {
    $('introWhy').hidden = false; el.setAttribute('aria-hidden', 'false');
    $('introGo').addEventListener('click', () => { store.set('introSeen', true); done(); });
  }
  // the pen needs the calligraphic letters; if they do not come within a second, the word simply shows
  let begun = false;
  const go = () => { if (!begun) { begun = true; start(); } };
  document.fonts.load('700 100px "Aref Ruqaa"', 'حبر').then(go, go);
  setTimeout(() => { if (!begun) { begun = true; fill(0); el.style.setProperty('--dot', '.1s'); start.call(null); } }, 1000);
})();
