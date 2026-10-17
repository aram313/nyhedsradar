// Khabar – phone app. Reads app.json (the stories Live admits, with their section, rank, coverage and a small picture,
// written by the radar every few minutes; data.json, the whole pool, when it is missing), digest.json (the editor's
// lede, picks and recap of the day: the day's most important movements as short 'Who: what' lines by topic, in the
// style of Al Jazeera's breaking wire), summaries.json (the editor's summaries and its informative headline for every
// story) and front.json (the front page the editor composed).
// Five tabs: Forside (the editor's front page), Live (every story of all sections, the newest or the most important
// first), Kalender (the planned events ahead – elections, summits, rate meetings, deadlines and Danish dates:
// calendar.json from the radar, kalender.json from the editor), Økonomi (the economy page, energi/, in a frame) and
// Analyser (Hizb ut-Tahrir's answers to political questions, newest first). The map (Kort) is shelved since 17/10. A
// page's own options (sort, filters, kinds, window) sit in one dock above the tabs, within the thumb's reach; the top bar keeps only Gemt, search and settings. Concepts named in the news open
// a wiki page compiled only from those answers (public/viden). The app shows no analysis of its own: the movement's
// text is always attributed and set in its own face. Search over everything the radar has read. Plain JS.
const CFG = window.RADAR_CONFIG || {};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const wait = ms => new Promise(r => setTimeout(r, ms));
// work that can wait for a quiet moment (the phone's copy of the news, the pages beside the one in view)
const idle = cb => (window.requestIdleCallback ? requestIdleCallback(cb, { timeout: 3000 }) : setTimeout(cb, 600));
// the news files as the server sent them: a file that has not changed is not read again, and the phone keeps the very
// text it got (no stringify of a large object, and written in a quiet moment, not in the middle of a reload)
const rawOf = k => { try { return localStorage.getItem(k) || ''; } catch { return ''; } };
const parse = (t, d) => { try { return (t && JSON.parse(t)) ?? d; } catch { return d; } };
const keepRaw = (k, text) => idle(() => { try { localStorage.setItem(k, text); } catch { /* full, or a private window */ } });

const SECTIONS = { dk: 'Danmark', me: 'Mellemøsten', world: 'Verden' };
const GROUPS = { dk: 'Danske medier', west: 'Vestlige medier', mena: 'Arabiske og muslimske medier', il: 'Israelske medier',
  east: 'Russiske, kinesiske og indiske medier', official: 'Regeringers egne kanaler', channel: 'Kanaler på Telegram og YouTube',
  'bevægelsen': 'Bevægelsens egne kanaler' };
const GROUP_SHORT = { dk: ['dansk', 'danske'], west: ['vestligt', 'vestlige'], mena: ['arabisk/muslimsk', 'arabiske/muslimske'],
  il: ['israelsk', 'israelske'], east: ['østligt', 'østlige'], official: ['regeringskanal', 'regeringskanaler'], channel: ['kanal', 'kanaler'],
  'bevægelsen': ['fra bevægelsen', 'fra bevægelsen'] };
const GROUP_ORDER = ['dk', 'west', 'mena', 'il', 'east', 'official', 'channel', 'bevægelsen'];
const LANG = { ar: 'arabisk', tr: 'tyrkisk', en: 'engelsk', da: 'dansk' };
const TITLES = { home: 'Khabar.nu', latest: 'Live', kalender: 'Kalender', okonomi: 'Økonomi', analyses: 'Analyser', search: 'Søg', threads: 'Udvikling', svar: 'Svar',
  begreb: 'Leksikon', begreber: 'Leksikon', gemt: 'Gemt' };
// the tab whose options the dock above the tabs shows (paintOpts)
let dockTab = '';
// the small pictures live next to data.json on the data branch
const THUMBS = CFG.thumbUrl || (CFG.dataUrl || '').replace(/data\.json.*$/, 't/');

const RAW = { news: rawOf('lastData'), digest: rawOf('lastDigest'), sums: rawOf('lastSummaries'), front: rawOf('lastFront'), moves: rawOf('lastMoves') };
idle(() => { try { localStorage.removeItem('lastSums'); localStorage.removeItem('lastTitles'); } catch { /* nothing kept */ } });   // the old copies (before 17/10)
let data = slim(parse(RAW.news, null));
let digest = parse(RAW.digest, null);
let { sums, titles } = readSummaries(parse(RAW.sums, null));   // story id -> the editor's summary {text, paywall}; article id -> its headline
let tab = 'home', query = '';
let shared = store.get('shared', null) || store.get('copied', {});   // id -> {at, title, link, source}
// Gem (pro-plan 5.1): what the reader saved on this phone, newest first – a story with its snapshot (so it opens offline
// and after it has left Live), an answer by its number, a wiki page by its id. Nothing leaves the phone.
// A save must outlive every update of the app (the owner, 18/10: 'en bruger aldrig mister sine gemte'): the list is read
// leniently – an entry it cannot use is skipped, never the whole list –, a second copy ('saved-bak') stands in when the
// first cannot be read, and once something is saved the phone is asked to keep the app's storage (storage.persist:
// silent in Safari and Chrome; Firefox would show a prompt, so it is not asked there)
const okSave = x => !!x && typeof x === 'object' && ['s', 'a', 'b'].includes(x.k) && x.id != null && x.id !== '';
let saved = (() => { for (const key of ['saved', 'saved-bak']) { const v = store.get(key, null);
  if (Array.isArray(v)) return v.filter(okSave).map(x => ({ ...x, id: String(x.id) })); } return []; })();   // [{k: 's'|'a'|'b', id, at, …}]
const keepStorage = () => { try { const st = navigator.storage;
  if (st && st.persist && !/Firefox\//.test(navigator.userAgent)) st.persisted().then(p => p || st.persist()).catch(() => {}); } catch { /* old browser */ } };
const storeSaved = () => { store.set('saved', saved); store.set('saved-bak', saved); if (saved.length) keepStorage(); };
const isSaved = (k, id) => saved.some(x => x.k === k && x.id === String(id));
let foreignMode = store.get('foreignMode', 'translate');                 // translate | hide | original
let danish = store.get('danish', true);                                  // show and share in Danish (the standard)
let front = parse(RAW.front, null);                                      // the front page the editor composed (front.json)
const expanded = new Set();                                              // opened stories
const params = new URLSearchParams(location.search);
let focusId = params.get('item');
let lastSeen = store.get('lastSeen', 0);                                 // stories found later get a small dot
const seenTab = store.get('seenTab', {});                                // when each tab was last looked at
let shownIds = new Set();
// the tabs are pages side by side in one horizontal scroller (#list): the phone itself carries a swipe from one to the
// next, and each page keeps its own place
const list = $('list');
const pageEl = t => list.querySelector(`.page[data-tab="${t}"]`);
const cur = () => pageEl(tab);
const pg$ = id => { const p = cur(); return p && p.querySelector('#' + CSS.escape(id)); };   // on the page one sees
let touching = false, paging = false, scrubbing = false;                 // a finger on the pages; the pager moving; on the tab bar
let searchIndex = null, searchState = 'idle';
// the earlier days (moves.json): the phone keeps its copy, so the developments across days are on the very first screen
// (fetched afresh a moment after the start, and after each new edition)
let moves = parse(RAW.moves, null), archiveState = 'idle', movesAt = 0;
let goOverview = params.has('digest');                                   // a notification about the overview opens on it
let latestAll = false;
const udOpen = new Set(params.get('forlob') ? [params.get('forlob')] : []);   // developments unfolded on the Udvikling page
let udFocus = '', pendingThr = '';   // the development the Udvikling page was opened for (its address), and one to show
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
    method: 'POST', body: JSON.stringify({ kind, id: i.id, title: i.origTitle || i.title, summary: (i.origSummary || i.summary || '').slice(0, 220), ...(adminKey ? { me: 1 } : {}) }),
  }).catch(() => { /* offline: nothing lost but a hint */ });
}

// ---------------------------------------------------------------- how much Khabar is used (the owner's statistics)
// Nothing the user sees, nothing stored for it, no number that follows a person: an opening says from the home screen
// or a browser, which kind of phone, the phone's time zone and language, and how it came; going to the background
// says for how long it was open, which tabs were looked at and how many stories opened. The owner's phone is left out.
const visitOs = /iPhone|iPad|iPod/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1) ? 'ios'
  : /Android/.test(navigator.userAgent) ? 'android' : 'other';
function cameVia() {
  const r = document.referrer || '', ua = navigator.userAgent;
  if (params.has('n') || params.has('digest')) return 'push';   // a notification's link carries n=1 (a shared ?item= does not)
  if (/whatsapp/i.test(r)) return 'whatsapp';
  if (/facebook|messenger|orca|instagram/i.test(r) || /FBAN|FBAV|FB_IAB|Instagram/.test(ua)) return 'facebook';
  if (/google/i.test(r)) return 'google';
  if (/mms|messag|sms/i.test(r)) return 'sms';
  return r && !r.startsWith(location.origin) ? 'web' : 'direct';
}
function relay(body) {
  if (!CFG.feedbackTopic || adminKey) return;
  fetch('https://ntfy.sh/' + CFG.feedbackTopic, { method: 'POST', body: JSON.stringify(body), keepalive: true }).catch(() => {});
}
let visit = null;   // this opening: when it began, the tabs looked at, the stories opened
function countVisit(via, first = false) {
  let tz = '';
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch { /* an old phone */ }
  relay({ kind: 'visit', app: matchMedia('(display-mode: standalone)').matches || navigator.standalone === true ? 1 : 0, os: visitOs,
    tz, lang: (navigator.language || '').slice(0, 2).toLowerCase(), via, ...(first ? { first: 1 } : {}) });
  visit = { at: Date.now(), tabs: { [tab]: 1 }, opened: 0 };
}
function countLeave() {
  if (!visit) return;
  relay({ kind: 'leave', secs: Math.round((Date.now() - visit.at) / 1000), tabs: visit.tabs, opened: visit.opened });
  visit = null;
}

// ---------------------------------------------------------------- time
// One formatter per format, made once: toLocaleTimeString with options builds a new one at every call, and a list of
// eighty rows called it some three hundred times (a tenth of a second on a phone)
const FMT = {
  time: new Intl.DateTimeFormat('da-DK', { hour: '2-digit', minute: '2-digit' }),
  wd: new Intl.DateTimeFormat('da-DK', { weekday: 'short' }),
  full: new Intl.DateTimeFormat('da-DK', { weekday: 'long', day: 'numeric', month: 'long' }),
  dm: new Intl.DateTimeFormat('da-DK', { day: 'numeric', month: 'long' }),
  wdl: new Intl.DateTimeFormat('da-DK', { weekday: 'long' }),
  ymd: new Intl.DateTimeFormat('sv-SE'),
  my: new Intl.DateTimeFormat('da-DK', { month: 'long', year: 'numeric' }),   // the calendar's months
  mon: new Intl.DateTimeFormat('da-DK', { month: 'short' }),
  dk: (() => { try { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Copenhagen' }); } catch { return new Intl.DateTimeFormat('sv-SE'); } })(),
  num: new Intl.NumberFormat('da-DK'),
};
const clock = iso => FMT.time.format(new Date(iso));
const dkYmd = d => FMT.dk.format(d);   // the Danish day, as 2026-10-17
const dayKey = d => d.getFullYear() * 400 + d.getMonth() * 32 + d.getDate();   // the local day, cheaply
const yesterday = () => { const y = new Date(); y.setDate(y.getDate() - 1); return y; };
// One time format everywhere (pro-plan 2.9): 'nu', '4 min' up to nine minutes, then 'kl. 10.16' today, 'i går kl. 21.34',
// 'lør. kl. 23.32' within the week and '12/10' after it. Time columns show only '10.16'.
function stamp(iso) {
  const d = new Date(iso), m = (Date.now() - d) / 60000;
  if (m < 1) return 'nu';
  if (m < 10) return Math.floor(m) + ' min';
  const k = dayKey(d);
  if (k === dayKey(new Date())) return 'kl. ' + clock(iso);
  if (k === dayKey(yesterday())) return 'i går kl. ' + clock(iso);
  if (Date.now() - d < 6 * 864e5) return FMT.wd.format(d) + ' kl. ' + clock(iso);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
// the day and the time, always both (Live's 'Vigtigste', where the order is not by time): '17/10 kl. 12.03'
const fullStamp = iso => { const d = new Date(iso); return `${d.getDate()}/${d.getMonth() + 1} kl. ${clock(iso)}`; };
// when something is from, said after 'fra' or 'siden': 'kl. 10.53', 'i går kl. 21.34', 'lør. kl. 23.32', '12/10' – never
// 'nu' or minutes
const fromWhen = iso => { const s = stamp(iso); return s === 'nu' || s.endsWith(' min') ? 'kl. ' + clock(iso) : s; };
// a day row in a timeline: 'I dag', 'I går', 'Torsdag' within the week, else 'Torsdag 8. oktober'
function dayName(iso) {
  const d = new Date(iso), k = dayKey(d);
  if (k === dayKey(new Date())) return 'I dag';
  if (k === dayKey(yesterday())) return 'I går';
  return cap(Date.now() - d < 6 * 864e5 ? FMT.wdl.format(d) : FMT.full.format(d));
}
function dayLabel(iso) {
  const d = new Date(iso), k = dayKey(d), full = FMT.full.format(d);
  if (k === dayKey(new Date())) return 'I dag · ' + full;
  if (k === dayKey(yesterday())) return 'I går · ' + full;
  return cap(full);
}
const when = i => new Date(i.published || i.found).getTime();
const hours = i => Math.max(0, (Date.now() - when(i)) / 3600e3);
const num = n => FMT.num.format(Number(n || 0));

// ---------------------------------------------------------------- data
// 'no-cache' asks the server whether the file changed (a few bytes when it did not); the files live behind a
// cache that ignores query strings, so adding one never made them fresher
let busy = 0, offline = false, redrawAfterLoad = false;
// Live and the front page's pool: the radar's slim app.json (the stories Live admits, with only what the app reads);
// data.json – the whole pool of candidates – when app.json is missing
const getText = async url => { const r = await fetch(url, { cache: 'no-cache' }); if (!r.ok) throw new Error(r.status); return r.text(); };
async function loadNews() {
  if (CFG.appUrl) { try { return await getText(CFG.appUrl); } catch { /* not there yet: the whole pool */ } }
  return getText(CFG.dataUrl);
}
// data.json, when it stands in for app.json, is the radar's whole pool: Live shows only what the radar admitted (each
// story's `live`) and the big stories the editor did not drop – as app.json would; before the radar drew a line (no
// `live` in the file) everything
function slim(d) {
  if (!d || !Array.isArray(d.items) || !d.live || typeof d.live !== 'object' || !d.items.some(i => i.live)) return d;
  const drop = new Set(d.live.drop || []);
  d.items = d.items.filter(i => i.live || (i.big && ![i.id, ...(i.members || [])].some(x => drop.has(x))));
  return d;
}
const FRONT_URL = () => CFG.frontUrl || (CFG.digestUrl || '').replace(/digest\.json$/, 'front.json');
// the editor's summaries and its headline of every story: a headline is filed under the story's id with its other
// articles (members), so it still finds the story when another outlet's article leads it; the newest one wins
function readSummaries(all) {
  const t = {}, at = {};
  for (const [k, v] of Object.entries((all && all.titles) || {})) {
    if (!v || !v.title) continue;
    for (const id of [k, ...(v.members || [])]) if (!t[id] || String(v.at || '') > at[id]) { t[id] = v.title; at[id] = String(v.at || ''); }
  }
  return { sums: (all && all.items) || {}, titles: t };
}
async function load(manual) {
  busy++; document.body.classList.add('loading');
  let changed = false;
  const wasOffline = offline;
  // the files are asked for side by side, not one after another
  const dig = CFG.digestUrl;
  const [news, dg, sm, fr] = await Promise.allSettled([loadNews(), dig ? getText(dig) : null,
    dig ? getText(CFG.summariesUrl || dig.replace(/digest\.json$/, 'summaries.json')) : null,
    dig ? fetch(FRONT_URL(), { cache: 'no-cache' }).then(r => r.ok ? r.text() : r.status === 404 ? 'null' : Promise.reject(r.status)) : null]);
  // a file the same as last time is neither read nor drawn again (most reloads: the radar writes every five minutes)
  const fresh = (k, res) => res.status === 'fulfilled' && typeof res.value === 'string' && res.value !== RAW[k] ? res.value : null;
  netLoaded = true;
  if (news.status === 'fulfilled') {
    offline = false;
    const t = fresh('news', news), d = t && slim(parse(t, null));
    if (d && Array.isArray(d.items)) { RAW.news = t; data = d; changed = true; keepRaw('lastData', t); }
  } else {
    offline = true;
    if (manual) toast('Ingen forbindelse', false);
  }
  const td = fresh('digest', dg), d = td && parse(td, null);
  if (d) {   // else: keep the last overview; the earlier days again only when they were fetched before this edition
    RAW.digest = td; digest = d; changed = true; keepRaw('lastDigest', td);
    if (archiveState !== 'loading' && Date.now() - movesAt > 60e3) setTimeout(loadArchive, 0);   // the last copy shows meanwhile
  }
  const ts = fresh('sums', sm), all = ts && parse(ts, null);
  if (all) {   // the editor's summaries and headlines (summaries.json next to digest.json)
    RAW.sums = ts; ({ sums, titles } = readSummaries(all)); titlesVer++; changed = true; keepRaw('lastSummaries', ts);
  }
  const tf = dig && fresh('front', fr);
  if (tf) {   // the front page the editor composed (front.json; none: the fixed one)
    const f = parse(tf, null);
    RAW.front = tf; front = f && Array.isArray(f.blocks) ? f : null; changed = true; keepRaw('lastFront', tf);
  }
  if (--busy === 0) document.body.classList.remove('loading');
  need('ans');   // the editor's filed answers: looked for again after a quarter of an hour
  // the calendar (the front page's 'Det sker snart' and the Kalender tab): asked again at its own pace, at once by hand
  if (manual) for (const k of ['cal', 'kal']) if (vd[k] && vd[k].state !== 'loading') vd[k].at = 0;
  need('cal'); need('kal');
  if (changed || manual || offline !== wasOffline || redrawAfterLoad) { redrawAfterLoad = false; renderSoon({ fresh: true, keep: true }); } else renderHeader();
}
// a reload's drawing waits while a finger is on the screen or the page still moves, so a scroll is never interrupted
let lastScroll = 0, renderT = 0, renderOpts = null;
function renderSoon(opts) {
  clearTimeout(renderT);
  renderOpts = { ...(renderOpts || {}), ...(opts || {}) };   // two calls waiting draw once, with both wishes
  if (touching || paging || scrubbing || pull || performance.now() - lastScroll < 300) { renderT = setTimeout(renderSoon, 250); return; }
  const o = renderOpts;
  renderOpts = null;
  render(o);
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
// A curiosity headline withholds the news instead of stating it (the owner's rule of 2026-10-17): a question, 'Derfor …',
// 'Se …', 'Her er …', 'Sådan …', 'Det skal du vide', a label before a colon, a line that only names who speaks, a
// quotation with no one named after it. The radar's own test (src/radar/headlines.py), Danish and English.
const CUR_OPEN = /^(?:derfor|se\b|se:|her er|her får|sådan|det skal du vide|hvorfor|hvad|hvem|hvordan|hvornår|hvis du|du skal|du kan|tjek|test dig|quiz|overblik|kommentar|analyse|leder|debat|klumme|interview|essay|why|how|what|who|when|where|which|is|are|can|could|should|would|will|does|do|did|has|have|here'?s|here is|here are|this is|these are|that'?s|watch|explainer|explained|analysis|opinion|comment|editorial|op-ed|inside|the blogs|q&a|podcast|in pictures|in photos|photos|video)\b/iu;
const CUR_LABEL = /^(?:[\p{L}\p{N}_]+\s)?(?:fund|chok|afsløring|drama|kaos|skandale|overraskelse|vending|nyhed|besked|opråb|analyse|analysis|kommentar|comment|opinion|leder|debat|explainer|overblik|live|watch|video|blog)\s*:/iu;
const CUR_TEASE = /(?:\bog det er ikke godt\b|\bdet er derfor\b|\bher er grunden\b|\bundrer sig\b|\bdu ikke vidste\b|\bsådan gør du\b|\bdet betyder det\b|\bhere'?s why\b|\bhere'?s what\b|\bwhat we know\b|\bwhat to know\b|\byou need to know\b|\bwhat it means\b|\band why\b|\bthis is why\b|\bthe reason\b|\bmight surprise\b|\bnever guess\b)/iu;
const CUR_TAIL = /\s[-–]\s(?:opinion|analysis|comment|editorial|op-ed|udtalelse|analyse|kommentar)\s*$/iu;
const CUR_SPEAKER = /[«»"“”’'][,.]?\s*(?:[:,–-]\s*\S+\s+\S+|(?:\S+\s+){0,4}(?:says|said|tells|told|warns|siger|sagde|fortæller|advarer)\b)/u;
function curious(title) {
  const t = String(title || '').trim();
  if (!t) return true;
  if (/\?\s*[»"“”'’]?\s*$/u.test(t)) return true;
  if (t.includes('?') && /^(?:kan|skal|vil|er|har|bliver|får|bør|må)\b/iu.test(t)) return true;   // 'Kan Europa stole på USA? …'
  const first = t.split(/\s+/)[0], bare = first.replace(/^[.,:]+|[.,:]+$/g, '');
  const acronym = first === first.toUpperCase() && first !== first.toLowerCase() && bare.length >= 2;   // 'WHO advarer …'
  if ((CUR_OPEN.test(t) && !acronym) || CUR_LABEL.test(t) || CUR_TEASE.test(t) || CUR_TAIL.test(t)) return true;
  if (t.endsWith(':')) return true;   // only who speaks, nothing of what was said
  if ('»"“”\'‘’„«'.includes(t[0]) && !CUR_SPEAKER.test(t.slice(1))) return true;
  return false;
}
// A teaser is the outlet's own introduction; some carry what is none: a call to action at the end ('Følg udviklingen i
// krigen her.'), a link, a picture's caption with its credit and the page's markup before the real teaser. The radar
// cleans them at intake (clean_teaser in src/radar/headlines.py) – keep the two alike; this catches the phone's copies.
const CTA = /\s*(?:(?:Følg|Se|Læs|Hør|Lyt)\b[^.!?]{0,80}?\b(?:her|live|nedenfor)\b\s*[.!:]?|(?:Læs mere|Læs også|Læs hele artiklen|Se videoen|Se video|Se billederne|Read more|Continue reading|Click here|Watch the video|Watch video|Watch live)\b[^.!?]{0,60}?[.!:…]?|The post .{1,200}? appeared first on .{1,80}?\.?|\[(?:…|\.\.\.|&hellip;)\])\s*$/iu;
const LEAD_TAG = /^(?:live|video|watch|se video|breaking)\s*[:|–-]\s*/iu;
const URL_RX = /\s*(?:https?:\/\/|www\.)\S+/giu;
const CREDIT = /^.{0,400}?\[[^\]]{0,80}(?:agency|\bAA\b|anadolu|getty|afp|reuters|\bAP\b|screengrab|photo|foto|epa|ritzau|scanpix|–)[^\]]{0,80}\]\s*"?(?:\s*[\w-]+="[^"]*")*\s*\/?>?\s*/iu;
const MARKUP = /^[^<>]{0,300}?"?\s*(?:[\w-]+="[^"]*"\s*)+\/?>\s*/u;
const CAPTION = /\b(?:is|are) seen\b|\bpictured\b|\bgives a speech\b|\bposes? for\b|\b(?:on|in) (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b/iu;
const STEM_STOP = new Set(['that', 'this', 'with', 'from', 'have', 'their', 'there', 'which', 'about', 'after', 'over', 'into', 'som',
  'ikke', 'efter', 'under', 'siger', 'blev', 'være', 'været', 'eller', 'også', 'deres', 'mens']);
const stems4 = t => new Set((String(t || '').toLowerCase().match(/[\p{L}]{4,}/gu) || []).filter(w => !STEM_STOP.has(w)).map(w => w.slice(0, 5)));
function cleanTeaser(text, title = '') {
  let t = String(text || '').replace(/\s+/g, ' ').trim();
  if (!t) return '';
  const m = t.match(CREDIT) || t.match(MARKUP);
  if (m) t = t.slice(m[0].length).replace(/^[\s"]+|[\s"]+$/g, '');
  t = t.replace(LEAD_TAG, '').replace(URL_RX, '').trim();
  for (let k = 0; k < 3; k++) { const cut = t.replace(CTA, '').trim(); if (cut === t) break; t = cut; }
  if (title) {
    const [first, ...rest] = t.split(/(?<=[.!?])\s+/);
    if (CAPTION.test(first) && overlap(stems4(first), stems4(title)) < 2) t = rest.join(' ');
  }
  return t.length >= 20 ? t : '';
}
// a teaser's first sentence, as a share or a summary line carries it (none when it is the rest of a cut sentence,
// a link or a sign-off)
function firstSentence(text) {
  const s = String(text || '').split(/(?<=[.!?])\s+(?=[\p{Lu}\p{N}»"“(])/u)[0].replace(/\s*…$/, '').trim();
  return s.length < 20 || /^[\p{Ll}]/u.test(s) || /^(https?:|www\.|\[)/i.test(s) ? '' : s;
}
// a curiosity headline's stand-in until the editor has written one: the first sentence of the teaser, shortened at a
// word boundary (none when the teaser has no plain sentence of its own)
const HEAD_MAX = 120;
function teaserHead(text) {
  let t = tidy(String(text || '')).replace(/\s+/g, ' ').trim();
  t = t.replace(/^.{0,90}?\((?:Reuters|AP|AFP|Ritzau|Anadolu)\)\s*[-–—]\s*/u, '');   // a wire's dateline
  const s = ((t.match(/^.+?[.!?](?=\s+["»“(]?[\p{Lu}\p{N}]|$)/u) || [t])[0]).trim();
  if (s.length < 25 || /^[\p{Ll}]/u.test(s) || /^(?:https?:|www\.)/i.test(s) || curious(s)) return null;
  const plain = s.replace(/[.!]$/, '');
  if (plain.length <= HEAD_MAX) return { title: plain, rest: t.slice(s.length).trim(), cut: false };
  // too long: end with the main clause, before a clause that only adds to it (', hvilket …', ', som …'), where one is
  let clause = -1;
  for (const m of plain.slice(0, HEAD_MAX).matchAll(/,\s(?:hvilket|hvorefter|som|der|hvor|mens|efter at|fordi|selvom|which|who|where|while|after|as)\s/gu)) if (m.index >= 50) clause = m.index;
  if (clause > 0) return { title: plain.slice(0, clause), rest: '', cut: true };
  const at = plain.lastIndexOf(' ', HEAD_MAX - 2);
  return { title: plain.slice(0, at > 60 ? at : HEAD_MAX - 2).replace(/[\s,;:–-]+$/, '') + ' …', rest: '', cut: true };
}
// The owner's house style (17/10): Israel's name in lower case inside curly quotes, every form – “israel”, “israels”,
// “israelske”. The editor's text comes so from his tool (voice.quote_israel in scripts/voice.py – keep the two alike);
// the app writes the Danish headlines and teasers of the outlets and the machine the same way. The outlet's original
// headline in the credit line and Hizb ut-Tahrir's texts are quoted as they are.
const ISR_Q = /[“"»„](israel[\p{L}\p{N}_]*)[”"«“]/giu, ISR_B = /(?<![\p{L}\p{N}_“/.:#=])(israel[\p{L}\p{N}_]*)(?![\p{L}\p{N}_”/])/giu;
const quoteIsrael = t => (!t || typeof t !== 'string' || !/israel/i.test(t) || /^https?:\/\//.test(t) ? t
  : t.replace(ISR_Q, (_, w) => `“${w.toLowerCase()}”`).replace(ISR_B, (_, w) => `“${w.toLowerCase()}”`));
// the editor's headline for a story: filed under any of its articles (its id, its members, its other outlets'); one of an
// earlier round that is a curiosity headline itself ('Hvorfor …?', 'Analyse: …') gives way, until the editor writes it anew
const edOk = t => (t && !curious(t) ? t : '');
const edTitle = i => edOk(titles[i.id]) || (i.members || []).map(m => edOk(titles[m])).find(Boolean) || (i.also || []).map(a => edOk(titles[a.id])).find(Boolean) || '';
// What a story is called: the editor's informative headline first (Danish outlets too); else the outlet's – in Danish,
// the machine's, where the phone shows Danish; a plain curiosity headline gives way to its teaser's first sentence.
// `how` says where the headline came from: 'ed' the editor, 'mt' the machine's translation, '' the outlet's own;
// `teased` that the teaser stands in for a curiosity headline.
function display(i) {
  let d = { ...i, origTitle: i.title, origSummary: i.summary, kw: i.kw || [], how: '', teased: false, kind: i.kind || (isComment(i) ? 'kommentar' : '') };
  const keepOrig = i.foreign && foreignMode === 'original';
  if (i.foreign && !keepOrig && i.title_tr) {
    d = { ...d, title: i.title_tr, summary: i.summary_tr || '', from: i.lang, to: 'en', kw: i.kw_tr || [], how: 'mt' };
  }
  const ed = edTitle(i);
  if (ed && (danish || i.lang === 'da') && !keepOrig) {
    const kw = i.lang === 'da' ? d.kw : [...new Set([...(i.kw_da || []), ...(i.kw || [])])];
    d = { ...d, title: ed, summary: i.lang === 'da' ? i.summary : danish ? i.summary_da || '' : d.summary, from: i.lang, to: 'da', kw, how: 'ed' };
  } else if (danish && i.title_da && !keepOrig) {
    d = { ...d, title: i.title_da, summary: i.summary_da || '', from: d.from || i.lang, to: 'da', kw: i.kw_da || [], how: 'mt' };
  }
  d.title = tidy(d.title);
  d.summary = cleanTeaser(d.summary, d.title);   // no call to action, link or picture caption (the phone's older copies)
  if (d.how !== 'ed' && curious(tidy(['da', 'en'].includes(i.lang) ? i.title : i.title_tr || ''))) {
    // the teaser in the language shown, else the outlet's own (a headline that says the news beats one that hides it)
    const own = !d.summary && i.summary && readable(i.summary) && cleanTeaser(i.summary, i.title);
    const th = teaserHead(d.summary) || (own ? teaserHead(own) : null);
    // no teaser to stand in: another outlet's plain headline (Danish first, else English), with that outlet and its link
    const alt = !th && ['da', 'en'].map(l => (i.also || []).find(a => a.lang === l && a.title && !curious(tidy(a.title)))).find(Boolean);
    if (th) d = { ...d, title: th.title, summary: th.cut ? d.summary || own || '' : th.rest, teased: true };
    else if (alt) d = { ...d, title: tidy(alt.title), origTitle: alt.title, source: alt.source || d.source, link: alt.link || d.link, kw: [], teased: true, how: '', to: alt.lang };
  }
  if (d.how === 'ed' || (d.to || i.lang) === 'da') {   // a Danish headline: the house style for Israel's name
    d = { ...d, title: quoteIsrael(d.title), summary: quoteIsrael(d.summary), kw: (d.kw || []).map(quoteIsrael) };
  }
  if (d.how === 'ed') {   // 'Reuters: …' – the outlet is said once, in the meta line under the headline (never twice in a row)
    const m = d.title.match(/^([^:»«"]{2,40}):\s+(\S.*)$/u), x = m && outletKey(m[1]);
    if (x) {
      // another outlet that carries the story: the row names and opens that outlet's report
      const alt = x !== outletKey(d.source) && (i.also || []).find(a => outletKey(a.source) === x);
      if (alt) d = { ...d, source: alt.source, link: alt.link || d.link, title: cap(m[2]) };
      // the row's own outlet, or a news outlet that does not carry it: the name goes. A government's channel ('Kreml',
      // 'Det Hvide Hus'), a state or a person is who speaks and stays – a claim is always attributed
      else if (x === outletKey(d.source) || outletNames().has(x)) d = { ...d, title: cap(m[2]) };
    }
  }
  return d;
}
// an outlet's name as the app compares it: 'The Guardian' is 'guardian', 'Quds News (arabisk)' is 'quds news', and the
// agencies' long names are their short ones
const OUTLET_ALIAS = { 'associated press': 'ap', 'agence france presse': 'afp', 'agence france-presse': 'afp', 'bbc news': 'bbc', 'b t': 'bt' };
const outletKey = s => { const k = fold(String(s || '').replace(/\s*\(.*?\)\s*/g, ' ')).replace(/[^\p{L}\p{N}]+/gu, ' ').trim().replace(/^the /, '');
  return OUTLET_ALIAS[k] || k; };
// commentary, not news: the outlet's opinion section or the headline's own label (the radar marks it, kind: 'kommentar';
// this reads the phone's older copies the same way – keep it like commentary() in src/radar/headlines.py)
const COMMENT_PATH = /\/(?:kommentar\w*|kommentatorer|debat\w*|opinions?|analyse\w*|analysis|leder\w*|blogs?|meninger|klummer?|comment(?:isfree)?|op-?ed)(?:\/|$|\?)/i;
const COMMENT_LABEL = /^(?:kommentar|analyse|analysis|leder|debat|klumme|opinion|comment|editorial|op-ed)\s*:/i;
const isComment = i => {
  const path = String(i.link || '').replace(/^\w+:\/\/[^/]*/, '');
  return COMMENT_PATH.test(path) || COMMENT_LABEL.test(i.title || '') || CUR_TAIL.test(i.title || '');
};
// the news outlets' names (not governments' own channels or the movement's: who speaks there is a speaker, not a report)
const NEWS_GROUPS = new Set(['dk', 'west', 'mena', 'il', 'east', 'channel']);
let outletMemo = null;
const outletNames = () => (outletMemo && outletMemo.src === (data && data.sources) ? outletMemo
  : (outletMemo = { src: data && data.sources, set: new Set(Object.entries((data && data.sources) || {})
    .filter(([, v]) => NEWS_GROUPS.has(v.group || 'west')).flatMap(([k, v]) => [outletKey(v.label || k), outletKey(k)])) })).set;
// the words that say who and where (the radar finds them) in bold; the rest of the headline stays plain
function boldRanges(text, words = []) {
  const at = [], letter = /[\p{L}\p{N}]/u;
  const whole = (i, w) => !(i > 0 && letter.test(text[i - 1])) && !letter.test(text[i + w.length] || '');   // not 'Russia' in 'Russian'
  for (const w of words || []) {
    if (!w) continue;
    let i = text.indexOf(w);
    while (i >= 0 && (!whole(i, w) || at.some(r => i < r.b && i + w.length > r.a))) i = text.indexOf(w, i + 1);
    if (i >= 0) at.push({ a: i, b: i + w.length });
  }
  return at;
}
// a text with its bold words and its links to the wiki (each a range; a link never inside another, bold inside a link)
function markup(text, links = [], bolds = []) {
  text = String(text ?? '');
  if (!links.length && !bolds.length) return esc(text);
  const pts = [...new Set([0, text.length, ...links.flatMap(r => [r.a, r.b]), ...bolds.flatMap(r => [r.a, r.b])])].sort((x, y) => x - y);
  let out = '', open = null;
  for (let k = 0; k < pts.length - 1; k++) {
    const p = pts[k], q = pts[k + 1], L = links.find(r => r.a <= p && q <= r.b) || null;
    if (L !== open) {
      if (open) out += '</a>';
      if (L) out += `<a class="bg" href="?begreb=${encodeURIComponent(L.id)}" data-begreb="${esc(L.id)}">`;
      open = L;
    }
    const seg = esc(text.slice(p, q));
    out += bolds.some(r => r.a <= p && q <= r.b) ? `<b>${seg}</b>` : seg;
  }
  return out + (open ? '</a>' : '');
}
const bold = (text, words = []) => markup(text, [], boldRanges(text, words));
const readable = t => !/[؀-ۿ]/.test(t || '');

// ---------------------------------------------------------------- the wiki: the concepts named in the news
// public/viden holds a page for every state, power, group, issue and concept Hizb ut-Tahrir's answers read, compiled only
// from those answers (always attributed; the newest answer governs). The small index (the names and the Danish forms the
// news uses) comes at the start, a page's text only when one opens. A name links where it is plain text – the lede, an
// opened story, the recap's lines, an answer's note – never inside a button or a link: its first mention in a block, at
// most three in a block, a whole word (with a possessive s), the case as the page says.
const VIDEN = CFG.videnUrl || 'viden/';
const KINDS = { stat: 'Stat', magt: 'Magt', gruppe: 'Gruppe', sag: 'Sag', begreb: 'Begreb', aftale: 'Aftale', sted: 'Sted',
  organisation: 'Organisation', proces: 'Proces' };
const LINK_SKIP = new Set(['danmark']);   // named in every Danish story, and its page holds one answer
// the wiki's files and the movement's answers: fetched when first needed (again after a failure at most every ten
// minutes); the two that grow – the editor's answers.json and the radar's analyses.json – again after a quarter of an hour
const vd = {};
// the two small files the first screen needs (the wiki's names, the answers' index) are kept on the phone too, so the
// links and the answer line are in the very first screen instead of pushing it down when they come; fetched afresh
// behind it, and drawn again only when they changed
const VKEEP = { bix: 'viden-bix', mix: 'viden-mix' };
for (const [k, key] of Object.entries(VKEEP)) { const t = rawOf(key), v = parse(t, null); if (v) vd[k] = { v, raw: t, state: 'idle', at: 0 }; }
const VFILES = {
  bix: () => VIDEN + 'begreber-index.json', bfull: () => VIDEN + 'begreber.json',
  mix: () => VIDEN + 'movement-index.json', mfull: () => VIDEN + 'movement.json',
  ans: () => CFG.answersUrl || (CFG.digestUrl || '').replace(/digest\.json$/, 'answers.json'),
  txt: () => CFG.analysesUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'analyses.json'),
  map: () => CFG.mapUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'map.json'),   // the shelved Kort tab's events
  // the Kalender tab: the radar's planned events (data branch) and the editor's own from the news (digest branch)
  cal: () => CFG.calendarUrl || (CFG.dataUrl || '').replace(/data\.json$/, 'calendar.json'),
  kal: () => CFG.kalenderUrl || (CFG.digestUrl || '').replace(/digest\.json$/, 'kalender.json'),
};
// the calendar changes a few times a day (the editor's entries sooner); the shelved map's events followed the news's cycle
const VFRESH = { ans: 15 * 60e3, txt: 15 * 60e3, map: 90e3, cal: 30 * 60e3, kal: 10 * 60e3 };
const V = k => (vd[k] && vd[k].v) || null;
function need(k) {
  const x = vd[k] ||= { v: null, state: 'idle', at: 0 }, age = Date.now() - x.at;
  if (x.state === 'loading') return x.v;
  if (x.state === 'idle' || (x.state === 'ok' ? VFRESH[k] && age > VFRESH[k] : age > 10 * 60e3)) {
    const url = VFILES[k]();
    if (!url) { x.state = 'error'; x.at = Date.now(); return x.v; }
    x.state = 'loading';
    // a file asked for again that has not changed (the answers every quarter of an hour) draws nothing again
    getText(url).then(t => ({ t, v: t === x.raw ? undefined : JSON.parse(t) }))
      .then(({ t, v }) => { const news = v !== undefined; if (news) { x.v = v; if (VFRESH[k] || VKEEP[k]) x.raw = t; if (VKEEP[k]) keepRaw(VKEEP[k], t); } x.state = 'ok'; return news; },
        () => { x.state = x.v ? 'ok' : 'error'; return true; })
      .then(news => { x.at = Date.now(); if (news) vLoaded(k); });
  }
  return x.v;
}
const waiting = k => !vd[k] || (!vd[k].v && vd[k].state !== 'ok' && vd[k].state !== 'error');
// a file came: the pages that show it are drawn again (the one in view at once), the answer lines filled in place
function vLoaded(k) {
  if (k === 'bix') lk = null;
  if (k === 'bix' || k === 'mix' || k === 'ans') fillAnswerRefs();
  // (search and Gemt too: a search's answers found through the wiki come with its whole file, a saved answer with the index)
  const pages = { bix: ['home', 'latest', 'threads', 'analyses', 'svar', 'begreb', 'begreber', 'search', 'gemt'], mix: ['analyses', 'svar', 'begreb', 'search', 'gemt'],
    ans: ['analyses', 'svar', 'begreb', 'search', 'gemt'], txt: ['analyses', 'svar'], mfull: ['svar'],
    bfull: ['begreb', 'svar', 'search', ...(anQuery ? ['analyses'] : [])], map: ['kort'], cal: ['kalender', 'home'], kal: ['kalender', 'home'] }[k] || [];
  if (k === 'cal' || k === 'kal') calGen++;   // the merged calendar is worked out again
  if (k === 'bix' && busy) { redrawAfterLoad = true; return; }   // the news are on their way: their drawing takes the links along
  if (pages.length) redrawPages(pages);
  if (data && (k === 'mix' || k === 'ans')) renderDots(stories());
  if (k === 'mix' && tab === 'analyses') prefetchLibrary();   // its build is known now
}
// the linker: every page's Danish forms (and, but for an issue, its name) as two patterns, one keeping case and one not,
// the longest form first, so 'krigen i Ukraine' wins over 'Ukraine'
let lk = null;
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function linker() {
  const ix = V('bix');
  if (!ix) return null;
  if (lk) return lk;
  const forms = { cs: new Map(), ci: new Map() };
  for (const [id, e] of Object.entries(ix.items || {})) {
    if (LINK_SKIP.has(id)) continue;
    const names = [...(e.aliases || []), ...(e.kind === 'sag' ? [] : [String(e.name || '').replace(/\s*\(.*\)$/, '')])];
    for (const n of names) {
      if (!n || n.length < 2) continue;
      const m = e.case_sensitive ? forms.cs : forms.ci, key = e.case_sensitive ? n : n.toLowerCase();
      if (!m.has(key)) m.set(key, { id, n });
    }
  }
  const rx = (m, flags) => m.size ? new RegExp('(' + [...m.values()].map(x => x.n).sort((a, b) => b.length - a.length).map(reEsc).join('|')
    + ")(?:s|'s|’s|')?(?![\\p{L}\\p{N}_])", flags) : null;
  lk = { cs: rx(forms.cs, 'gu'), ci: rx(forms.ci, 'giu'), forms };
  return lk;
}
// an outlet's name is no mention of the place or state in it ('Jerusalem Post', 'Times of Israel')
let maskMemo = null;
function outletMask() {
  const src = data && data.sources;
  if (maskMemo && maskMemo.src === src) return maskMemo.rx;
  const names = [...new Set(Object.entries(src || {}).map(([k, v]) => String(v.label || k).replace(/\s*\(.*?\)\s*/g, ' ').trim())
    .concat(['Jerusalem Post', 'Times of Israel', 'Jerusalem Daily', 'Iran International', 'Kurdistan24', 'Syria TV']))]
    .filter(n => n.length >= 4 && /\s/.test(n)).sort((a, b) => b.length - a.length);
  maskMemo = { src, rx: names.length ? new RegExp(names.map(reEsc).join('|'), 'g') : null };
  return maskMemo.rx;
}
// the pages a text names: [{a, b, id}] in reading order, never two over one another, none inside an outlet's name
function scan(text) {
  const L = linker();
  if (!L || !text) return [];
  const found = [], letter = /[\p{L}\p{N}_-]/u;
  for (const [rx, m, lower] of [[L.cs, L.forms.cs, false], [L.ci, L.forms.ci, true]]) {
    if (!rx) continue;
    for (const x of text.matchAll(rx)) {
      if (x.index > 0 && letter.test(text[x.index - 1])) continue;
      const f = m.get(lower ? x[1].toLowerCase() : x[1]);
      if (f) found.push({ a: x.index, b: x.index + x[0].length, id: f.id });
    }
  }
  const mask = outletMask(), masked = mask ? [...text.matchAll(mask)].map(x => [x.index, x.index + x[0].length]) : [];
  found.sort((x, y) => x.a - y.a || (y.b - y.a) - (x.b - x.a));
  const out = [];
  let end = -1;
  for (const f of found) {
    if (f.a < end || masked.some(([p, q]) => f.a < q && f.b > p)) continue;
    out.push(f); end = f.b;
  }
  return out;
}
// a block of text (one story, one topic, one note): each page linked once, at most three
const linkSession = (max = 3) => ({ used: new Set(), n: 0, max });
// the broadest pages (in more than BROAD answers: USA, Storbritannien) take a slot only after the specific names of the
// block – in a lede 'USA' should not take the first of three links ahead of Houthierne or Hormuz
const BROAD = 150;
function pickLinks(text, sess) {
  const out = [];
  if (!sess) return out;
  const ix = (V('bix') || {}).items || {}, found = scan(text);
  const broad = f => (ix[f.id] || {}).n_answers > BROAD;
  for (const f of [...found.filter(f => !broad(f)), ...found.filter(broad)]) {
    if (sess.n >= sess.max) break;
    if (sess.used.has(f.id)) continue;
    sess.used.add(f.id); sess.n++; out.push(f);
  }
  return out.sort((x, y) => x.a - y.a);
}
const rich = (text, sess, kw) => markup(text, pickLinks(String(text ?? ''), sess), kw ? boldRanges(String(text ?? ''), kw) : []);
const nameOf = id => { const e = ((V('bix') || {}).items || {})[id]; return e ? e.name : cap(String(id || '').replace(/-/g, ' ')); };
const subj = id => String(id || '').replace(/-sagen$/, '');   // a page's subject in the movement layer ('iran-sagen' is the issue 'iran')
const pageOf = s => { const it = (V('bix') || {}).items || {}; return it[s] ? s : it[s + '-sagen'] ? s + '-sagen' : ''; };

// ---------------------------------------------------------------- Hizb ut-Tahrir's answers to political questions
// One list, newest first: the movement layer's 321 answers 2003-2026 (viden/movement-index.json: the Danish title, the
// question and the subjects each reads, the most central first), the editor's newer ones (answers.json on the digest
// branch: the same with their readings and begreber), and the newest the radar has found that nobody has filed yet
// (data.json 'analyses': the original title and the link).
const dSlash = iso => { const [y, m, d] = String(iso || '').slice(0, 10).split('-').map(Number); return y && m && d ? `${d}/${m}/${y}` : ''; };
const cleanTitle = t => cap(String(t || '').replace(/^\s*(?:updated\s+|opdateret\s+)?(?:ameer'?s\s+)?(?:answer to (?:a )?questions?|questions? and answers?|q\s*&\s*a|svar på (?:et )?(?:politiske? )?spørgsmål|spørgsmål og svar)\s*(?:\((?:opdateret|updated)\)\s*)?[:\-–]?\s*/i, '').trim()) || 'Svar på spørgsmål';
// an original title the app shows before the Danish one comes says 'Israel', Khabar's own word
const ourWords = t => String(t || '').replace(/\b(?:the\s+)?(?:Jewish|Zionist)\s+(?:Entity|State)\b/gi, 'Israel');
let ansMemo = null, ansGen = 0;
function answers() {
  const mix = V('mix'), filed = V('ans'), found = (data && data.analyses) || [], fk = found.map(x => x.id + '@' + x.date).join(',');
  if (ansMemo && ansMemo.mix === mix && ansMemo.filed === filed && ansMemo.fk === fk) return ansMemo;
  ansGen++;
  const by = new Map(), get = nr => { nr = String(nr); if (!by.has(nr)) by.set(nr, { nr, issues: [], states: [], powers: [] }); return by.get(nr); };
  for (const [nr, a] of Object.entries((mix && mix.answers) || {})) Object.assign(get(nr), { date: a.date, da: a.title_da, q: a.question_da,
    issues: a.issues || [], states: a.states || [], powers: a.powers || [], layer: true });
  for (const [nr, a] of Object.entries((filed && filed.items) || {})) {
    const o = get(nr);
    Object.assign(o, { date: a.date || o.date, da: a.title_da || o.da, q: a.question_da || o.q, note: a.note_da || '', url: a.url || '',
      readings: a.readings || [], begreber: a.begreber || [], filed: true });
  }
  for (const x of found) { const o = get(x.id); o.orig = x.title; o.date = o.date || x.date; o.url = o.url || x.url; }
  const list = [...by.values()].filter(o => o.da || o.orig).map(o => ({ ...o, date: String(o.date || '').slice(0, 10),
    title: cleanTitle(o.da || ourWords(o.orig)), fresh: !o.layer }));
  const num = o => +String(o.nr).replace(/\D/g, '') || 0;
  list.sort((a, b) => b.date.localeCompare(a.date) || num(b) - num(a));
  ansMemo = { mix, filed, fk, list, by: new Map(list.map(a => [a.nr, a])) };
  return ansMemo;
}
// what an answer is about: its subjects, weighted by place (its first issue, state and power weigh most)
function aboutOf(a) {
  if (a.about) return a.about;
  const m = new Map(), put = (s, w) => { s = subj(s); if (s && (m.get(s) || 0) < w) m.set(s, w); };
  const W = [1, 0.6, 0.35, 0.2];
  for (const l of [a.issues, a.states, a.powers]) (l || []).forEach((s, k) => put(s, W[k] ?? 0.1));
  (a.begreber || []).forEach(s => put(s, 0.8));
  (a.readings || []).forEach(r => { String(r.subject || '').split('--').forEach(s => put(s, 0.8)); if (r.object) put(r.object, 0.4); });
  return (a.about = m);
}
// the area an answer belongs to, for its row: its first issue's name (the issue of a state is the state's name)
// the area an answer belongs to (its first issue; the issue of a state is the state): its subject's id, cached on the
// answer once the wiki's names are here
const areaIdOf = a => {
  if (a.areaB) return a.areaId;
  const kind = id => (((V('bix') || {}).items || {})[id] || {}).kind;
  // an answer the editor filed has no issues or states: the page its title names, else its first reading's subject
  // (its begreber run A–Å, so their first 'sag' is no area – the Yemen answer is no 'Afghanistan og Pakistan')
  const own = a.filed && !(a.issues || []).length ? (scan(a.title)[0] || {}).id || subj(String(((a.readings || [])[0] || {}).subject || '').split('--')[0]) : '';
  const s = (a.issues || [])[0] || (a.states || [])[0] || own || (a.begreber || []).find(id => kind(id) === 'sag')
    || (a.begreber || []).find(id => kind(id) === 'stat') || subj(((a.readings || [])[0] || {}).subject || '').split('--')[0] || (a.begreber || [])[0];
  a.areaB = !!V('bix');
  return (a.areaId = s ? subj(s) : '');
};
const areaName = id => (id ? nameOf(pageOf(id) || id).replace(/-sagen$/, '').replace(/\s*\(.*\)$/, '') : '');
const areaOf = a => areaName(areaIdOf(a));
// The amir's answer on a story's subject – one line under the story, or none (none is better than a loose one).
// A story names its subjects in its headline (and the radar's actors, the recap topic's name: they weigh 1) and in its
// summary (½). An answer is about the subjects its title names, the first its question names and its main issue; the
// rest its question names it touches. An answer qualifies when a subject of the story's headline that is not in nearly
// every answer (like the USA) is one it is about, a second signal agrees – another subject (the broad ones only from its
// title) or two words the story and the answer's title and question share – and it is at most three years old (a current
// reading governs). The more specific and the newer the better: a year older weighs about a third.
const GEN = new Set(['hvord', 'hvorfo', 'hvilke', 'ifølge', 'blive', 'bliver', 'andre', 'deres', 'havde', 'skulle', 'kunne', 'ville', 'samme',
  'siden', 'første', 'større', 'største', 'stadig', 'måske', 'derfor', 'fordi', 'selvom', 'gennem', 'landet', 'lande', 'staten', 'stater',
  'regeri', 'præsid', 'minist', 'politi', 'situat', 'udvikl', 'spørgs', 'betyde', 'mulige', 'nuvære', 'senest', 'bagved', 'virkel', 'realit',
  'trump', 'trumps', 'putin', 'putins']);
// a filed answer is about the subjects its readings read and its title names – its begreber (twenty for the Yemen answer
// of 27/9/2026: Iran, Pakistan, Tyrkiet …) only touch, else it would take the line from stories it is not about
const answerCore = a => a.core ||= new Set([...scan(a.title).map(f => subj(f.id)), ...scan(a.q || '').slice(0, 1).map(f => subj(f.id)),
  ...(a.issues || []).slice(0, 1), ...((a.states || [])[0] && a.states[0] === (a.issues || [])[0] ? [a.states[0]] : []),
  ...(a.readings || []).flatMap(r => String(r.subject || '').split('--')).filter(Boolean).map(subj)]);
const answerTouches = a => a.touches ||= new Set([...scan(a.q || '').map(f => subj(f.id)), ...(a.begreber || []).map(subj)]);
const answerWords = a => a.words ||= new Set([...stems(a.title + ' ' + (a.q || ''))].filter(w => !GEN.has(w)));
function storySubjects(i, extra = '') {
  const m = new Map();
  for (const id of i.actors || []) if (!LINK_SKIP.has(id)) m.set(subj(id), 1);
  for (const t of [i.title, i.title_da, extra]) for (const f of scan(t || '')) m.set(subj(f.id), 1);
  for (const t of [i.summary_da, (sumOf(i) || {}).text]) for (const f of scan(t || '')) if (!m.has(subj(f.id))) m.set(subj(f.id), 0.5);
  return m;
}
// a story about one state's own affairs (an election, a court, its parliament) gets a line only when a second, specific
// subject of its headline agrees
const DOMESTIC = /\b(?:valg(?:et|kamp\w*|ene)?|genvalg|skæbnevalg|meningsmåling\w*|domstol\w*|retten|retssag\w*|dom(?:men)?|højesteret|parlament\w*|knesset|koalition\w*|regeringsdannels\w*|partiet|partier|election|court|poll)\b/i;
// a report of the dead and wounded names the place and the side every day: its line needs a specific second subject
const REPORT = /\b(?:dræb\w*|såre[dt]\w*|omkom\w*|døde|dødstal\w*|killed|wounded|injured|kills)\b/i;
const SPECIFIC = 1.8;   // a subject in fewer answers than this (idf) is specific: Israel, Iran, Rusland, Kina are in many
function answerFor(i, extra = '') {
  const A = answers(), ix = V('bix');
  if (!A.list.length || !ix) return null;
  const S = [...storySubjects(i, extra)];
  if (!S.length) return null;
  const N = A.list.length + 1, now = Date.now();
  const idf = s => { const p = pageOf(s), n = p ? ix.items[p].n_answers || 0 : 0; return Math.log((N + 1) / (n + 1)); };
  const own = new Set(S.flatMap(([s]) => { const p = pageOf(s), e = p && ix.items[p]; return e ? [...stems([e.name, ...(e.aliases || [])].join(' '))] : []; }));
  const sw = new Set([...stems([i.title, i.title_da, i.summary_da, (sumOf(i) || {}).text, extra].join(' '))].filter(w => !own.has(w) && !GEN.has(w)));
  const head = [i.title, i.title_da].join(' '), strict = DOMESTIC.test(head) || REPORT.test(head);
  let best = null, bestV = 0;
  for (const a of A.list) {
    const age = Math.max(0, now - Date.parse(a.date + 'T12:00:00Z')) / 864e5;
    if (age > 3 * 365) break;   // the list runs newest first
    const core = answerCore(a), touches = answerTouches(a);
    const anchor = S.filter(([s, w]) => w === 1 && idf(s) > 0.5 && core.has(s)).sort((x, y) => idf(y[0]) - idf(x[0]))[0];
    if (!anchor) continue;
    const inCore = S.filter(([s]) => core.has(s)), inQ = S.filter(([s]) => !core.has(s) && touches.has(s) && idf(s) > 0.5);
    const words = [...answerWords(a)].filter(w => sw.has(w));
    // the second signal: another subject of the headline (never only the summary's) that the answer is about, or that
    // it touches and few answers name – or two words the story and the answer share. A story of one state's own affairs
    // or a report of the dead needs a specific second subject.
    const second = S.filter(([s, w]) => s !== anchor[0] && w === 1 && (core.has(s) || (touches.has(s) && idf(s) > SPECIFIC)));
    if (strict ? !second.some(([s]) => idf(s) > SPECIFIC) : !second.length && words.length < 2) continue;
    const sc = inCore.reduce((x, [s, w]) => x + w * Math.max(0.3, idf(s)), 0) + 0.5 * inQ.reduce((x, [s, w]) => x + w * idf(s), 0) + 0.6 * words.length;
    const v = sc * Math.exp(-age / 365);
    if (v > bestV) { bestV = v; best = a; }
  }
  return best;
}
// every block of the movement's says whose and when once, in its label: 'Hizb ut-Tahrirs svar · d/m/åååå' (its texts are
// plain Danish without 'Ifølge …' – the owner, 2026-10-17: "det står over det hele"); a block of several answers' texts
// gives each row its own date (htDate)
const htLabel = (date, extra = '') => `<div class="ht-who"><b>Hizb ut-Tahrirs svar</b>${date ? ` · ${esc(dSlash(date))}` : ''}${extra}</div>`;
const htDate = date => date ? `<time class="ht-d">${esc(dSlash(date))}</time>` : '';
// 'Hizb ut-Tahrirs svar: <title> · d/m/åååå' – one quiet line to the answer reader
// (whose and when on the first row, so a long title or a large text size never cuts the date off)
const answerLine = a => `<button class="ht-line" data-svar="${esc(a.nr)}"><span class="ht-tx"><span class="ht-k"><b>Hizb ut-Tahrirs svar</b>`
  + ` · ${esc(dSlash(a.date))}</span><span class="ht ht-t">${esc(a.title)}</span></span><svg><use href="#i-chev"/></svg></button>`;
// the line under a story: at once when the files are here, else a quiet place that is filled when they come
function answerRef(i, extra = '', skip = '') {
  const a = V('bix') && V('mix') ? answerFor(i, extra) : null;
  if (a && !String(skip).split(',').includes(a.nr)) return `<div class="ans-ref">${answerLine(a)}</div>`;
  return V('bix') && V('mix') ? '' : `<div class="ans-ref" data-ans-for="${esc(i.id)}"${extra ? ` data-ans-x="${esc(extra)}"` : ''}${skip ? ` data-ans-skip="${esc(skip)}"` : ''}></div>`;
}
// a quiet place is filled in where it stands; one above the reader moves nothing in view. An empty place is not drawn
// (no box to measure), so where it stands is told by what comes before it
function fillIn(el, html, edge) {
  const ref = el.offsetParent ? el : el.previousElementSibling || el.parentElement;
  const above = (el.offsetParent ? ref.getBoundingClientRect().top : ref.getBoundingClientRect().bottom) < edge;
  const h0 = el.offsetHeight, pg = el.closest('.page');
  el.innerHTML = html;
  if (above && pg && el.offsetHeight !== h0) pg.scrollTop += el.offsetHeight - h0;
}
function fillAnswerRefs() {
  if (!V('bix') || !V('mix')) return;
  const edge = $('bar').getBoundingClientRect().bottom;
  for (const el of list.querySelectorAll('[data-ans-for]')) {
    const i = findStory(el.dataset.ansFor), a = i && answerFor(i, el.dataset.ansX || '');
    el.removeAttribute('data-ans-for');
    if (a && el.dataset.ansMain) frontAns.add(a.nr);   // the main story's answer: an opened story does not say it again
    fillIn(el, a && !String(el.dataset.ansSkip || '').split(',').includes(a.nr) ? answerLine(a) : '', edge);
  }
  // the answer the editor set on the front page, by its number
  for (const el of list.querySelectorAll('[data-ans-nr]')) {
    const a = answers().by.get(el.dataset.ansNr);
    if (!a && (waiting('mix') || waiting('ans'))) continue;
    el.removeAttribute('data-ans-nr');
    fillIn(el, a ? answerLine(a) : '', edge);
  }
}
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
// A card is known by its lead article's id, and the lead changes when a better outlet joins the story. The card then
// keeps what the reader had: opened, its other outlets unfolded, seen (no glow, not counted as new), shared, and its row –
// renamed in place, not built again with its picture.
const carried = new Map();   // a card's id now -> {from: its id before, found: when the story was first found}
function carryOver(before, after) {
  const was = new Map(), had = new Set(before.map(i => i.id)), has = new Set(after.map(i => i.id));
  for (const i of before) for (const k of [i.id, ...(i.members || []), ...(i.also || []).map(a => a.id)]) if (!was.has(k)) was.set(k, i);
  for (const i of after) {
    if (had.has(i.id)) continue;
    const p = [...(i.members || []), ...(i.also || []).map(a => a.id)].map(k => was.get(k)).find(p => p && !has.has(p.id));
    if (!p) continue;
    carried.set(i.id, { from: p.id, found: (carried.get(p.id) || {}).found || p.found });
    carried.delete(p.id);
    for (const set of [expanded, covOpen, shownIds]) if (set.has(p.id)) { set.delete(p.id); set.add(i.id); }
    if (shared[p.id] && !shared[i.id]) shared[i.id] = shared[p.id];
    for (const el of list.querySelectorAll('#' + CSS.escape('s-' + p.id))) { el.id = 's-' + i.id; el.dataset.id = i.id; }
  }
}
const firstFound = i => (carried.get(i.id) || {}).found || i.found;
const isNew = i => lastSeen && firstFound(i) && new Date(firstFound(i)).getTime() > lastSeen && !shared[i.id];
let cache = null;
let titlesVer = 0;
function stories() {
  if (!data) return [];
  const mode = foreignMode + danish + titlesVer;
  if (cache && cache.src === data && cache.mode === mode) return cache.list;
  const items = data.items.filter(visible).map(display);
  if (cache && cache.src !== data) carryOver(cache.list, items);
  cache = { src: data, mode, list: items, byId: new Map(items.map(i => [i.id, i])) };
  return items;
}
const find = id => (stories(), cache && cache.byId.get(id));
// a story can be found by any of its outlets' articles: its card follows whichever article leads it right now
const findStory = id => id && (find(id) || stories().find(i => (i.members || []).includes(id) || (i.also || []).some(a => a.id === id)));

// What is shared is what the reader sees: the headline shown, the first sentence of the editor's summary (else of the
// cleaned teaser), the outlet's link, and a link back to the story in Khabar
const itemUrl = id => `khabar.nu/?item=${encodeURIComponent(id)}`;
function shareText(d) {
  const ed = sumOf(d), first = firstSentence(ed && ed.text) || firstSentence(cleanTeaser(d.summary, d.title));
  return `*${d.title}*\n${first ? first + '\n' : ''}${d.link}\n\nvia ${itemUrl(d.id)}`;
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
// a story's small picture; where it has none, or it cannot be loaded, the outlet's initials on a quiet tile. The page
// remembers a picture that failed (it is never asked for again, so a reload does not undo the fallback) and one that
// has loaded in view (drawn without 'lazy' after, so a reload finds the row as it stands)
const badPics = new Set(), nearPics = new Set();
function picFailed(img, fallback) {
  badPics.add(img.getAttribute('src'));
  if (fallback && !badPics.has(fallback)) img.setAttribute('src', fallback); else img.remove();
}
// Dagens historie's picture (the owner, 17/10: "Kan dagens historie ikke få et billede?"): the story's own full-size
// picture (`pic`: the feed's or the outlet's og:image, else another outlet's – the radar never takes one from an
// unverified channel), never the small copy blown up and never an initials tile; none, or one that failed: the text lead
const leadPic = i => [i.pic].find(x => x && /^https?:\/\//.test(x) && !badPics.has(x)) || '';
function leadPicFailed(img) {
  badPics.add(img.getAttribute('src'));   // remembered: a reload draws the text lead
  const art = img.closest('.story'), box = img.closest('.lead-pic'), sec = img.closest('.block.top');
  if (box) box.remove();
  if (art) art.classList.remove('lp');
  if (sec) sec.classList.add('text');
}
function thumb(source, file) {
  const src = file && THUMBS + file, ok = src && !badPics.has(src);
  return `<span class="th" aria-hidden="true"><b>${esc(monogram(source))}</b>${ok
    ? `<img src="${esc(src)}" alt="" width="64" height="64"${nearPics.has(src) ? '' : ' loading="lazy"'} decoding="async" onerror="picFailed(this)">` : ''}</span>`;
}
// The meta line: 'Kommentar' or the rationed 'Høj betydning', the section (on mixed lists), the outlet – never cut –, the
// time; the line breaks between its items, never inside one, and never starts with '·'
function meta(i, opts = {}) {
  const m = [];
  if (i.kind === 'kommentar') m.push('<span class="kind">Kommentar</span>');
  else if (!opts.top && topNow().has(i.id)) m.push('<span class="big">Høj betydning</span>');   // in a chosen block it goes without saying
  // mixed lists say where it belongs; a list of mostly one section says it only on the story from another
  if (opts.tag && secOf(i) !== opts.msec) m.push(`<span class="sec"><i></i>${SECTIONS[secOf(i)]}</span>`);
  m.push(`<span class="src">${esc(i.source)}</span>`);
  if (!opts.tick) m.push(`<span class="tm">${isNew(i) ? '<i class="nd"></i>' : ''}${opts.full ? fullStamp(i.published || i.found) : stamp(i.published || i.found)}</span>`);   // the ticker has its own time column
  if (i.outlets >= 3) m.push(`<span>${i.outlets} medier</span>`);   // one rule everywhere: three outlets and more
  if (i.confirmed === 0) m.push('<span class="warn">ubekræftet</span>');
  if (shared[i.id]) m.push('<span class="done">delt</span>');
  return m.join('');
}
// 'Høj betydning' (called 'Topnyhed' until 18/10, the owner: 'måske topnyhed termet burde ændres til høj betydning'):
// at most five stories at a time, chosen by weight, where the coverage weighs least (the owner, 18/10: 'stor dækning
// burde vægte mindre end redaktørens valg eller bøgernes tungeste kategorier'). Points: the editor's first three picks
// (or the owner's raise) 4, another pick 3; the books' heaviest tiers (1–4 and Danish policy on Islam and Muslims, 6) 2;
// a big story – the coverage – 1. A story needs 2 points, so coverage alone never makes it high; a tier without the
// editor needs a confirmed story. A pick holds for 24 hours, the rest for twelve – hours since it was published, not
// the calendar day, so a story of 23.30 keeps it past midnight. Ties: the editor's order, then rank. No commentary.
// src/radar/run.py's top_now is the same – keep the two alike (the notifications say 'Høj betydning' by it).
const TOP_MAX = 5, TOP_HOURS = 12, PICK_HOURS = 24;
const HEAVY = new Set([1, 2, 3, 4, 6]);
const heavy = i => HEAVY.has(+i.tier);
function topScore(i) {
  if (i.kind === 'kommentar') return 0;
  const p = pickRank(i), ed = p < 99;
  if (hours(i) >= (ed ? PICK_HOURS : TOP_HOURS)) return 0;
  if (!ed && i.confirmed === 0) return 0;
  return (p < 3 ? 4 : ed ? 3 : 0) + (heavy(i) ? 2 : 0) + (i.big ? 1 : 0);
}
// a story's weight in Live, shown as the calendar shows its events' (the owner, 18/10: 'fremhæve dem med høj betydning
// medium og lav som vi har gjort på kalenderen'): 3 – 'Høj betydning' (topNow), a soft red ground and a red edge; 2 – the
// red edge without the ground: an editor's pick, a story of the books' heaviest tiers, or a big story; 1 – the rest,
// quiet. A commentary is never weighted.
const weightOf = i => i.kind === 'kommentar' ? 1 : topNow().has(i.id) ? 3
  : pickRank(i) < 99 || heavy(i) || i.big ? 2 : 1;
let topMemo = null;
function topNow() {
  const all = stories(), at = Math.floor(Date.now() / 600e3);   // worked out again every ten minutes, or with the news
  if (topMemo && topMemo.list === all && topMemo.at === at && topMemo.dg === digest && topMemo.own === ownerLocal) return topMemo.set;
  const top = all.map(i => [i, topScore(i)]).filter(([, n]) => n >= 2)
    .sort(([a, x], [b, y]) => y - x || pickRank(a) - pickRank(b) || rankOf(b) - rankOf(a)).map(([i]) => i);
  topMemo = { list: all, at, dg: digest, own: ownerLocal, set: new Set(top.slice(0, TOP_MAX).map(i => i.id)) };
  return topMemo.set;
}
// A row is not one button: the button that opens it lies under the whole row, and the headline and its line lie on top
// of it, letting a tap through – so an opened story's headline can carry links to the wiki without a link inside a button.
function story(i, n, opts = {}) {
  const open = expanded.has(i.id);
  if (opts.hero) return heroStory(i, n, opts);
  const w = opts.tick ? weightOf(i) : 1;   // Live's rows show their weight
  const cls = ['story', opts.tick ? 'tick' : 'pic', opts.lead && 'lead', opts.lead && opts.pic && 'lp', i.important && 'imp', w > 1 && 'w' + w, open && 'open', isNew(i) && 'new'].filter(Boolean).join(' ');
  // Dagens historie's picture: large above its headline (opts.pic, from leadPic); one that fails leaves the text lead
  const lp = opts.lead && opts.pic ? `<span class="lead-pic" aria-hidden="true"><img src="${esc(opts.pic)}" alt="" decoding="async" fetchpriority="high" referrerpolicy="no-referrer" onerror="leadPicFailed(this)"></span>` : '';
  return `<article class="${cls}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" data-sec="${secOf(i)}"${opts.tag ? ' data-tag="1"' : ''}${opts.msec ? ` data-msec="${opts.msec}"` : ''}${opts.clock ? ' data-clock="1"' : ''}${opts.top ? ' data-top="1"' : ''}${opts.home ? ' data-home="1"' : ''}>
    <div class="row"><button class="hit" data-toggle aria-expanded="${open}" aria-label="${esc(rowLabel(i, opts))}"></button>${lp}${opts.tick ? `<time class="tt" aria-hidden="true">${isNew(i) ? '<i class="nd"></i>' : ''}${clock(i.published || i.found)}</time>` : ''}<span class="tx"${open ? '' : ' aria-hidden="true"'}><span class="h" dir="auto">${headHtml(i, open)}</span><span class="m">${meta(i, opts)}</span></span>${opts.tick ? rowSave(i) : thumb(i.source, i.thumb)}</div>
    <div class="x"><div><div class="x-in">${open ? detail(i, detailOpts(i, opts)) : ''}</div></div></div></article>`;
}
// Live's rows carry the bookmark at their right (the owner, 17/10: "gør det samme for 'Live' oversigten"): saved
// without opening the story, and one sees which are saved; it sits beside the row's button, never inside it
const rowSave = i => { const on = isSaved('s', i.id);
  return `<button class="st-save${on ? ' on' : ''}" data-save aria-pressed="${on}" aria-label="${on ? 'Gemt' : 'Gem'}"><svg aria-hidden="true"><use href="#i-${on ? 'saved' : 'save'}"/></svg></button>`; };
// what a screen reader says for a row: the headline once, then the outlet, the time and its label
const rowLabel = (i, opts = {}) => [i.title + '.', [i.source, stamp(i.published || i.found), i.kind === 'kommentar' ? 'Kommentar'
  : !opts.top && topNow().has(i.id) ? 'Høj betydning' : opts.tick && weightOf(i) === 2 ? 'Middel betydning' : '', isNew(i) ? 'ny' : ''].filter(Boolean).join(', ')].join(' ');
// an opened story on the front page does not say the answer again that the page shows already (pro-plan 3.4)
const frontAns = new Set();
const detailOpts = (i, opts = {}) => (opts.home ? { skip: [...frontAns].join(',') } : {});
// the day's lead story: its own picture big (the outlet's original, else our small copy), headline on top of it
function heroStory(i, n, opts) {
  const open = expanded.has(i.id), small = i.thumb ? THUMBS + i.thumb : '';
  const src = [i.pic, small].find(x => x && !badPics.has(x)) || '';
  shownAs.set(i.id, i);
  return `<article class="story hero${open ? ' open' : ''}" id="s-${esc(i.id)}" data-id="${esc(i.id)}" data-sec="${secOf(i)}" data-tag="1" data-top="1"${opts.home ? ' data-home="1"' : ''}>
    <div class="hero-row">${src ? `<img src="${esc(src)}" alt="" decoding="async"
      onerror="picFailed(this, '${esc(src === small ? '' : small)}')">` : ''}<button class="hit" data-toggle aria-expanded="${open}" aria-label="${esc(rowLabel(i, opts))}"></button><span class="hero-tx"><span class="h" dir="auto">${headHtml(i, open)}</span>
      <span class="m">${meta(i, opts)}</span></span></div>
    <div class="x"><div><div class="x-in">${open ? detail(i, { noAns: true, ...detailOpts(i, opts) }) : ''}</div></div></div></article>`;
}
// An opened story is short: the editor's summary (or the outlet's own teaser while there is none), the three actions,
// the amir's answer on its subject if there is one, and two small buttons – the development it belongs to, and the other
// outlets' headlines, folded until asked for. The headline and the summary link the wiki's pages they name (one block).
const covOpen = new Set();
const sumOf = i => [i.id, ...(i.also || []).map(a => a.id)].map(k => sums[k]).find(Boolean);
// an opened story is one block: its headline and its summary share the three links (the headline's are counted first)
const headHtml = (i, open) => open ? rich(i.title, linkSession(), i.kw) : bold(i.title, i.kw);
// the main story may wear a Danish outlet's headline: opening it later links the words it shows
const shownAs = new Map();
const asShown = el => (el.dataset.home && shownAs.get(el.dataset.id)) || find(el.dataset.id);
const storySession = i => { const s = linkSession(); pickLinks(i.title, s); return s; };
function detail(i, o = {}) {
  const ed = sumOf(i), text = ed ? ed.text : i.summary;
  const saved = isSaved('s', i.id);
  return `${text ? `<p class="sum" dir="auto">${rich(text, storySession(i))}</p>` : ''}${creditLine(i, ed)}
    <div class="acts">
      <a class="act primary" href="${esc(i.link)}" target="_blank" rel="noopener" data-read><svg><use href="#i-open"/></svg>Læs</a>
      <button class="act" data-share><svg><use href="#i-share"/></svg>Del</button>
      <button class="act" data-copy><svg><use href="#i-copy"/></svg>Kopiér</button>
      <button class="act sq${saved ? ' on' : ''}" data-save aria-label="${saved ? 'Gemt' : 'Gem'}" aria-pressed="${saved}"><svg><use href="#i-${saved ? 'saved' : 'save'}"/></svg></button>
    </div>${o.noAns ? '' : answerRef(i, '', o.skip || '')}${wikiChips(i, text)}${moreRow(i)}${covOpen.has(i.id) ? coverage(i) : ''}${oilRow([i.title, i.origTitle, text].join(' '))}`;
}
// one quiet credit line under the summary: what it rests on, the machine's translation, the outlet's own headline
// where the one shown is another (the editor's, the teaser's first sentence, a translation); two lines, a tap shows all
const sameText = (a, b) => fold(a).replace(/[^\p{L}\p{N}]+/gu, ' ').trim() === fold(b).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
function creditLine(i, ed) {
  const parts = [];
  if (ed && ed.paywall) parts.push('Resumé ud fra overskrifter og indledninger');
  const orig = tidy(i.origTitle || ''), lang = LANG[i.lang] || i.lang;
  if (orig && !sameText(orig, i.title)) {
    if (i.how === 'mt' && !i.teased) parts.push(`Maskinoversat fra ${esc(lang)}`);
    parts.push(`Original${i.lang && i.lang !== 'da' && !(i.how === 'mt' && !i.teased) ? ` på ${esc(lang)}` : ''}: <span dir="auto">»${esc(orig)}«</span>`);
  }
  return parts.length ? `<p class="credit" data-credit>${parts.join(' · ')}</p>` : '';
}
// the wiki's pages an opened story names (its headline first, then its summary): at most three, as quiet ochre chips
function wikiChips(i, text) {
  if (!V('bix')) return '';
  const ids = [...new Set([...scan(i.title), ...scan(text || '')].map(f => f.id))].slice(0, 3);
  return ids.length ? `<div class="wk-chips st-chips">${ids.map(id => `<a class="chip ht-chip" href="?begreb=${encodeURIComponent(id)}" data-begreb="${esc(id)}">${chipName(id)}</a>`).join('')}</div>` : '';
}
// oil and fuel: the prices one quiet row away – the Økonomi tab (khabar.nu/energi inside the app)
const OIL = /\b(?:olie\w*|benzin\w*|diesel\w*|brændstof\w*|brent|opec\w*|hormuz\w*|oil|petrol|gasoline|crude)\b/iu;
const energyRow = () => '<a class="qrow" href="?tab=okonomi" data-okonomi><span>Olie og brændstof – priser nu</span><svg><use href="#i-chev"/></svg></a>';
const oilRow = text => (OIL.test(text || '') ? energyRow() : '');
function moreRow(i) {
  const t = threadFor(i), n = (i.outlets || 1) - 1;
  const follow = t ? `<button class="mini" data-follow="${t.key}"><svg class="ic"><use href="#i-thread"/></svg><span>Udvikling: ${esc(t.name)}</span><svg class="go"><use href="#i-chev"/></svg></button>` : '';
  const cov = (i.also || []).length ? `<button class="mini${covOpen.has(i.id) ? ' on' : ''}" data-cov aria-expanded="${covOpen.has(i.id)}">Andre medier<em>${n}</em><svg class="chev"><use href="#i-chev"/></svg></button>` : '';
  return follow || cov ? `<div class="mini-row">${follow}${cov}</div>` : '';
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
const ymd = iso => FMT.ymd.format(new Date(iso));   // the local date as 2026-10-10
const dateDa = (ymdStr, weekday) => (weekday ? FMT.full : FMT.dm).format(new Date(ymdStr + 'T12:00:00'));
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
const liveIdOf = l => { const i = l.id && findStory(l.id); return i ? i.id : ''; };
// a line's words lie over the link that opens it (the whole line is still one tap), so the wiki's names in it can link
const lineLabel = l => (l.who ? l.who + ': ' : '') + l.text;
function lineHtml(l, day, sess) {
  const fresh = lastSeen && l.added && new Date(l.added).getTime() > lastSeen;
  const time = `<time>${clock(l.at)}${ymd(l.at) < day.date ? '<small>i går</small>' : ''}</time>`;
  const body = `<span>${l.who ? `<b>${esc(l.who)}:</b> ` : ''}${rich(l.text, sess)}${l.confirmed === 0 ? ' <i>ubekræftet</i>' : ''}</span>`;
  const live = liveIdOf(l);   // a story the app has opens in Live; anything else at its source
  const hit = l.link || live ? `<a class="hit" href="${esc(l.link || '#')}" target="_blank" rel="noopener" data-line="${esc(l.id)}"${l.kind === 's' ? ' data-story="1"' : ''}${live ? ` data-live="${esc(live)}"` : ''} aria-label="${esc(lineLabel(l))}"></a>` : '';
  return `<li class="${[fresh && 'new', hit && 'tap'].filter(Boolean).join(' ')}">${hit}<span class="ln">${time}${body}</span></li>`;
}
function dayTopic(day, tp) {
  const k = `${day.date}|${tp.name}`, all = tp.lines, open = dayOpen.has(k) || all.length <= SHOW + 1, sess = linkSession();
  return `<div class="dt" data-sec="${esc(tp.section)}"><h3><i></i>${esc(tp.name)}</h3>
    <ul class="dl">${(open ? all : all.slice(0, SHOW)).map(l => lineHtml(l, day, sess)).join('')}</ul>${open ? ''
    : `<button class="dt-more" data-day-more="${esc(k)}">Vis ${all.length - SHOW} mere</button>`}</div>`;
}
function dayBody(day) {
  return `<div class="ov-body" data-day="${esc(day.date)}">${day.topics.map(tp => dayTopic(day, tp)).join('')}
    <div class="ov-acts"><button data-day-share><svg aria-hidden="true"><use href="#i-share"/></svg>Del resumé</button></div></div>`;
}
// the share text, in the format members post themselves (digest.json brings it ready for the newest day)
function dayText(day) {
  if (digest && digest.date === day.date && digest.created === day.created && digest.whatsapp) return digest.whatsapp + '\n\nvia khabar.nu';
  return [day.title || 'Politiske nyheder', ...day.topics.map(tp => `${tp.name}\n\n${tp.lines.map(l => `- ${l.who ? l.who + ': ' : ''}${l.text}`).join('\n\n')}`), 'via khabar.nu'].join('\n\n');
}
async function loadArchive() {
  if (archiveState === 'loading') return;
  archiveState = 'loading'; movesAt = Date.now();
  const url = CFG.movesUrl || (CFG.digestUrl || '').replace(/digest\.json$/, 'moves.json');
  let changed = false;
  try {
    const t = await getText(url);
    if (t !== RAW.moves) { const m = JSON.parse(t); RAW.moves = t; moves = m; changed = true; keepRaw('lastMoves', t); }
    archiveState = 'ok';
  } catch { archiveState = moves ? 'ok' : 'error'; changed = !moves; }
  if (changed) staleOn(['home', 'threads', 'search']);
}
// earlier days: one row each, opened in place
// earlier days: the last three always in view (one row each, opened in place), the rest behind 'Vis flere dage'
let archAll = false;
function archive() {
  if (!moves) {
    if (archiveState === 'idle') setTimeout(loadArchive, 0);   // fetched as soon as the front page shows
    const note = archiveState === 'error' ? 'kunne ikke hente – prøv igen' : 'henter …';
    return `<h2 class="grp">Tidligere dage</h2><div class="arch"><button class="arch-row" data-archive><span><small>${note}</small></span></button></div>`;
  }
  const current = dayOf(digest);
  const list = (moves.days || []).map(dayOf).filter(d => d && d.topics.length && (!current || d.date !== current.date));
  if (!list.length) return '<h2 class="grp">Tidligere dage</h2><p class="explain pad">Hver dag lægges her, når den næste begynder.</p>';
  const shown = archAll ? list : list.slice(0, 3);
  return '<h2 class="grp">Tidligere dage</h2>' + shown.map(day => {
    const open = daysOpen.has(day.date), n = lineCount(day);
    return `<article class="arch${open ? ' open' : ''}" data-arch="${esc(day.date)}">
      <button class="arch-row" data-arch-toggle aria-expanded="${open}"><span><b>${cap(dateDa(day.date, true))}</b>
      <small>${updWord(n)} · ${day.topics.length} ${day.topics.length === 1 ? 'udvikling' : 'udviklinger'}</small></span><svg aria-hidden="true"><use href="#i-chev"/></svg></button>
      ${open ? dayBody(day) : ''}</article>`;
  }).join('') + (list.length > 3 && !archAll ? `<button class="qbtn" data-arch-all>Vis flere dage (${list.length - 3})</button>` : '');
}

/// ---------------------------------------------------------------- render: pages
// headings: a block ('Døgnets vigtigste') is a large title with its 'more' link right-aligned in the same row (44 px);
// a day in Live is a light pill that stays under the top bar while its stories scroll past – the two never look alike.
// Only the front page's Live block carries the red dot.
const moreLink = (label, go, attr = '') => `<button class="more" data-go="${go}"${attr}>${label}<svg aria-hidden="true"><use href="#i-chev"/></svg></button>`;
// (the Live dot after its title, so every block title starts at the same left edge)
const blockHead = (title, more = '', live = false) => `<div class="block-h"><h2>${title}${live ? '<i class="live" aria-hidden="true"></i>' : ''}</h2>${more}</div>`;
function timeline(list, opts, n0 = 0) {
  let html = '', last = '', n = n0;
  [...list].sort((a, b) => when(b) - when(a)).forEach(i => {
    const d = dayLabel(i.published || i.found);
    if (d !== last) { html += `<div class="day" role="heading" aria-level="2"><span>${d}</span></div>`; last = d; }
    html += story(i, n++, opts);
  });
  return html;
}
// the front page: today's most important stories (all sections), then the latest recap of a day, then earlier days
// ---------------------------------------------------------------- front-page pieces: Live, Dagens citat, the main story's timeline
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
  staleOn(['home']);
}
// 'Live' on the front page: the newest stories of the Live list (established outlets, no commentary), with the
// headlines the app shows; a tap opens the story there. The front page's one red dot.
function nowStrip(n = 3, used = null) {   // used: the stories the page shows already (a story in one block only)
  const last = stories().filter(i => i.confirmed !== 0 && i.kind !== 'kommentar' && !(used && used.has(i.id))).sort((a, b) => when(b) - when(a)).slice(0, n);
  if (used) last.forEach(i => used.add(i.id));
  if (!last.length) return '';
  return `<section class="block now">${blockHead('Live', moreLink('Se alt', 'latest'), true)}<ul>${last.map(i =>
    `<li><button data-live="${esc(i.id)}" aria-label="${esc(rowLabel(i))}"><time aria-hidden="true">${clock(i.published || i.found)}</time><span dir="auto" aria-hidden="true">${bold(i.title, i.kw)}</span><em aria-hidden="true">${esc(i.source)}</em></button></li>`).join('')}</ul></section>`;
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
  return q ? quoteBlock(q) : '';
}
const quoteBlock = q => `<section class="block qday" data-sec="${esc(q.sec || '')}">${blockHead('Dagens citat')}${quoteCard(q, true)}</section>`;
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
// a step that is a story in the app opens it in Live; a statement only on the wire opens its source. The step's tap is a
// real button or link under the whole row (iPhone does not always pass a tap on plain text on to the page); its words
// lie on top and let the tap through, but for the wiki's names in them, which open their page.
// The step ends with a small mark of where it leads: the story in Live (›) or the source outside (↗), the app's icons.
const stepHtml = (l, extra = '', cls = '', sess = null) => {
  const live = liveIdOf(l), mark = live ? 'chev' : l.link ? 'open' : '';
  const inner = `<time>${clock(l.at)}</time><p>${l.who ? `<b>${esc(l.who)}:</b> ` : ''}${rich(l.text, sess)}${mark ? `&#8288;<svg class="to" aria-hidden="true"><use href="#i-${mark}"/></svg>` : ''}</p>`;
  if (live) return `<li class="go ${cls}">${extra}<button class="hit" data-live="${esc(live)}" aria-label="${esc(lineLabel(l))}"></button>${inner}</li>`;
  if (l.link) return `<li class="src ${cls}">${extra}<a class="hit" href="${esc(l.link)}" target="_blank" rel="noopener" aria-label="${esc(lineLabel(l))}"></a>${inner}</li>`;
  return `<li class="${cls}">${extra}${inner}</li>`;
};
// a timeline newest first, with a quiet day row where the day changes ('I går', 'Torsdag'): a step from before
// midnight says so
function stepsWithDays(lines, sess, cls = l => '') {
  let html = '', day = dayKey(new Date());
  for (const l of lines) {
    const k = dayKey(new Date(l.at));
    if (k !== day) { day = k; html += `<li class="tl-day" role="heading" aria-level="3">${esc(dayName(l.at))}</li>`; }
    html += stepHtml(l, '', cls(l), sess);
  }
  return html;
}
// the main story's development: its two newest updates under a label that names the development and opens it, then
// 'Hele udviklingen ›' when it has more; on the front page without the wiki's underlines (they are in the opened stories
// and on the Udvikling page)
function storyline(tp, n = 2) {
  const lines = newestFirst(tp.lines).slice(0, n), more = tp.lines.length > n, key = tp.key || thrKey(tp.name);
  // its own section's colour, as on Udvikling and in search – never the story's it sits under
  return { lines, html: `<div class="follow pkg-f" data-sec="${esc(tp.section || '')}"><button class="pkg-h" data-follow="${key}"><span>Udvikling: ${esc(tp.name)}</span>`
    + `<svg aria-hidden="true"><use href="#i-chev"/></svg></button><ol>${stepsWithDays(lines, null)}</ol>`
    + (more ? `<button class="tl-all" data-follow="${key}">Hele udviklingen<svg aria-hidden="true"><use href="#i-chev"/></svg></button>` : '') + '</div>' };
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
// 'Følg udviklingen' on the front page: the developments that moved last (not the main story's own, which shows its
// steps above); a tap opens one on the Udvikling page, where the recap and the earlier days are too
function followStrip(skip) {
  if (!moves && archiveState === 'idle') setTimeout(loadArchive, 0);   // the developments run across days
  const list = threads().filter(t => !skip || t.name.trim().toLowerCase() !== skip.name.trim().toLowerCase()).slice(0, 3);
  return list.length ? folBlock(list) : '';
}
const folBlock = list => `<section class="block fol-b">${blockHead('Følg udviklingen', moreLink('Alle', 'threads'))}<div class="fol">${folRows(list)}</div></section>`;
// one word set (pro-plan 2.9): a development ('udvikling') has updates ('opdateringer'); it is 'fulgt i 8 dage'
const updWord = n => `${n} ${n === 1 ? 'opdatering' : 'opdateringer'}`;
const thrParts = t => [t.days > 1 ? `fulgt i ${t.days} dage` : updWord(t.lines.length), `senest ${stamp(t.last)}`];
// a meta line of parts (the section with its dot first): it breaks between its parts, never inside one
const metaLine = (sec, parts, cls = '') => `<span class="m ${cls}">${sec ? `<span class="sec"><i></i>${esc(sec)}</span>` : ''}${parts.map(p => `<span>${p}</span>`).join('')}</span>`;
const folRows = list => list.map(t => { const l = t.lines[t.lines.length - 1];
  return `<button class="fol-row" data-follow="${t.key}" data-sec="${esc(t.section || '')}">${metaLine(SECTIONS[t.section], thrParts(t), 'fol-m')}`
    + `<b>${esc(t.name)}</b><span class="fol-l">${l.who ? `<em>${esc(l.who)}:</em> ` : ''}${esc(l.text)}</span><svg aria-hidden="true"><use href="#i-chev"/></svg></button>`; }).join('');

// ---------------------------------------------------------------- the front page the editor composed
// The editor composes the front page at each update by its own taste and the brain (front.json on the digest branch,
// the owner's rule of 2026-10-17): which blocks, in what order, which stories, what a block is called. The app draws the
// blocks with its own pieces in its own look – the main story's card with its timeline, compact rows, the developments,
// the quote, the amir's answer, the Live preview, one line of reality. A block it cannot draw (an unknown kind, a story
// no longer in Live) is left out; a composition that is missing, cannot be read or is older than six hours between 06
// and 24 gives way to the fixed front page below.
const FRONT_KINDS = new Set(['top', 'liste', 'udvikling', 'citat', 'svar', 'live', 'linje']);
function dkHour() {
  try { return +new Intl.DateTimeFormat('da-DK', { hour: 'numeric', hourCycle: 'h23', timeZone: 'Europe/Copenhagen' }).format(new Date()); }
  catch { return new Date().getHours(); }
}
function frontNow() {
  const f = front;
  if (!f || !Array.isArray(f.blocks) || !f.blocks.some(b => b && FRONT_KINDS.has(b.kind))) return null;
  const age = Date.now() - Date.parse(f.updated || '');
  // older than six hours between 06 and 24; at night the evening's holds, but never one older than twelve hours
  if (Number.isNaN(age) || age > 12 * 3600e3 || (age > 6 * 3600e3 && dkHour() >= 6)) return null;
  return f;
}
const threadNamed = name => name && allThreads().find(t => t.key === thrKey(String(name)));
// Denmark only when it matters (the owner, 17/10: "danmark er ikke så vigtig behøver ikke fylde så meget medmindre det
// er vigtige historier"): a Danish story matters on the front page when it is big, when Live holds it as Danish politics
// on Islam, Muslims, integration or foreign policy (`live: 'dk'`), or when it is among the day's five strongest (the
// editor's picks first, then rank). Live and the radar keep their Danish rules; this is the front page's.
const FRONT_MAX = 6;   // blocks after the lede, whatever the composition says
const dayTops = () => new Set(frontCands(stories().filter(i => i.kind !== 'kommentar'), 5).map(i => i.id));
// a Danish story matters when it is among the day's five strongest, or big and Danish politics on Islam, Muslims,
// integration or foreign policy (the radar's 'dk' protection) – 'big' alone is a third of Live on a busy day
// (17/10 later the same day, the owner: "danmark er heller ikke såå vigtigt, kun kæmpe nyheder skal ramme forsiden for
// danmark": a Danish story reaches the front page only when it is big and among the day's five strongest)
const dkMatters = (i, tops) => !!i && !!i.big && tops.has(i.id);
// The front page's fixed order (the owner, 17/10: "hvorfor er citat i bunden på forside, synes godt tingene kunne
// sorteres bedre"): Dagens historie, the day's quote right under it, the news blocks in the editor's order, Hizb
// ut-Tahrir's answer, a line, 'Det sker snart', the developments, Live – whatever order the composition gives. A list
// whose stories are all Danish and none of them very big is left off the front page (it is in Live).
const FRONT_RANK = { top: 0, citat: 1, liste: 2, svar: 3, linje: 4, udvikling: 6, live: 7 };
const CAL_RANK = 5;   // 'Det sker snart' sits between the news and the developments
function frontOrder(blocks) {
  const tops = dayTops(), out = [];
  for (const b of blocks || []) {
    if (!b) continue;
    const list = b.kind === 'liste' ? (b.stories || []).map(x => findStory(String(x || ''))).filter(Boolean) : [];
    if (list.length && list.every(i => secOf(i) === 'dk') && !list.some(i => dkMatters(i, tops))) continue;
    out.push(b);
  }
  return out.map((b, k) => [b, k]).sort((x, y) => (FRONT_RANK[x[0].kind] ?? 4) - (FRONT_RANK[y[0].kind] ?? 4) || x[1] - y[1]).map(x => x[0]);
}
function composedHome(all, opts, f) {
  const used = new Set();
  const take = id => { const i = findStory(String(id || '')); if (!i || used.has(i.id)) return null; used.add(i.id); return i; };
  // the owner's own choice of the main story (held on the front page) leads the first main block
  const pin = owner().lead && findStory(owner().lead);
  let html = '', n = 0, filled = 0, tops = 0, drawn = 0, calPut = false;
  // the answer the editor set in a block of its own is not said again under a main story, nor in an opened story
  const svarSet = String((f.blocks.find(b => b && b.kind === 'svar') || {}).nr || '');
  if (svarSet) frontAns.add(svarSet);
  for (const b of frontOrder(f.blocks)) {
    if (!calPut && (FRONT_RANK[b.kind] ?? 4) > CAL_RANK && html) { calPut = true; html += calBlock(); }   // before the developments
    if (!b || !FRONT_KINDS.has(b.kind)) continue;
    if (drawn >= FRONT_MAX) break;   // overskuelighed før fuldstændighed: at most six blocks, whatever the composition
    const before = html.length;
    if (b.kind === 'top') {
      const first = !tops, i = take(first && pin ? pin.id : b.story);
      if (!i) continue;   // its story left Live: the next main block is the day's story
      tops++;
      // the editor's headline for the front page; the owner's pick wears its own
      const t = first && pin && pin.id !== (findStory(b.story) || {}).id ? '' : String(b.title || '');
      const shown = t ? { ...i, title: t, kw: [...new Set([...(i.kw || []), ...(i.kw_da || [])])] } : i;
      shownAs.set(i.id, shown);   // opened, shared or saved, it is the headline the front page shows
      // its picture large above the headline: Dagens historie always when it has one, a second main story unless the
      // editor chose a text lead
      const pic = first || b.picture !== false ? leadPic(i) : '';
      html += `<section class="block top pkg${pic ? '' : ' text'}" data-sec="${secOf(i)}">${first ? blockHead('Dagens historie') : ''}`
        + story(shown, n++, { ...opts, tag: true, top: true, lead: true, pic });
      // the development under the story is the story's own: the editor's timeline when its name shares a subject with
      // the story's headline (or the editor filed this very story in it), else the development the story belongs to by
      // the same test – else none: a timeline of another development is worse than none
      let tp = threadNamed(b.timeline) || (first && pin ? packageFor(i).topic : null);
      if (tp && !topicOf(shown, tp)) { const t2 = threadFor(i); tp = t2 && topicOf(shown, t2) ? t2 : null; }
      // the amir's answer on the main story's subject, directly under it (not under the 'with' stories below); the
      // development's name helps find it only when the development is the story's own
      html += mainAnswer(i, tp ? tp.name : '', svarSet);
      if (tp && tp.lines.filter(l => l.at).length) html += storyline(tp).html;
      for (const x of (b.with || [])) { const w = take(x); if (w) { html += story(w, n++, { ...opts, tag: true, top: true }); break; } }   // one more at most
      html += '</section>';
      filled++;
    } else if (b.kind === 'liste') {
      // the editor's order, but a story of the last 24 hours never waits behind an older one under 'Alle' (the owner,
      // 17/10: "Hvordan kan en frisk historie blive gemt under vis flere ift en der er over 24 timer gammel?")
      const named = (b.stories || []).map(take).filter(Boolean);
      const all = [...named.filter(i => hours(i) < 24), ...named.filter(i => hours(i) >= 24)];
      if (!all.length) continue;
      // three stories (a quiet Danish block two), then 'Alle ›' unfolds the rest in place
      const key = 'front|' + (b.title || ''), most = b.dkQuiet ? 2 : 3, list = unfolded.has(key) ? all : all.slice(0, most);
      const more = all.length > most ? `<button class="more" data-unfold="${esc(key)}" aria-expanded="${unfolded.has(key)}">${unfolded.has(key) ? 'Færre' : 'Alle<svg aria-hidden="true"><use href="#i-chev"/></svg>'}</button>` : '';
      // 'billeder': the first story with the outlet's own picture is set large, the rest as rows; a list of one
      // section ('Danmark') does not say the section on every row, and a list of mostly one only on the other ones
      const big = b.style === 'billeder' ? list.find(i => i.pic) : null, tag = new Set(list.map(secOf)).size > 1;
      const msec = tag ? mainSec(list) : '';
      html += `<section class="block f-list${unfolded.has(key) ? ' unf' : ''}">${blockHead(esc(b.title || ''), more)}`
        + (big ? story(big, n++, { ...opts, tag, msec, top: true, hero: true }) : '')
        + list.filter(i => i !== big).map(i => story(i, n++, { ...opts, tag, msec, top: true })).join('') + '</section>';
      filled++;
    } else if (b.kind === 'udvikling') {
      const list = (b.topics || []).map(threadNamed).filter(Boolean).slice(0, 3);
      if (!moves && archiveState === 'idle') setTimeout(loadArchive, 0);   // the developments run across days
      if (list.length) html += folBlock(list);
    } else if (b.kind === 'citat') {
      const q = pinnedQuote() || (b.who && b.text ? b : (notes().quotes || []).find(x => x.id === b.quote));
      if (q) html += quoteBlock(q);
    } else if (b.kind === 'svar') {
      need('mix'); need('ans');
      const a = answers().by.get(String(b.nr || ''));
      if (a) html += `<div class="ans-ref f-svar">${answerLine(a)}</div>`;
      else if (waiting('mix') || waiting('ans')) html += `<div class="ans-ref f-svar" data-ans-nr="${esc(b.nr || '')}"></div>`;
    } else if (b.kind === 'live') {
      // the newest stories no other block shows (also those a later block names)
      const named = f.blocks.flatMap(x => x && x.kind === 'top' ? [x.story, ...(x.with || [])] : x && x.kind === 'liste' ? x.stories || [] : [])
        .map(x => findStory(String(x || ''))).filter(Boolean).map(i => i.id);
      const skip = new Set([...used, ...named]), strip = nowStrip(Math.max(1, Math.min(10, +b.n || 3)), skip);
      for (const id of skip) if (!named.includes(id)) used.add(id);
      html += strip;
    } else if (b.kind === 'linje' && b.text) {
      html += `<p class="f-line">${esc(String(b.text))}</p>`;   // the front page's texts without the wiki's underlines
    }
    if (html.length > before) drawn++;
  }
  if (!calPut && html) html += calBlock();
  if (filled && !tops) {   // no main block left to draw: the day's main story leads, as on the fixed page
    const m = [mainStory(), ...frontCands(all)].find(i => i && !used.has(i.id));
    if (m) {
      const pic = leadPic(m);
      html = `<section class="block top pkg${pic ? '' : ' text'}" data-sec="${secOf(m)}">${blockHead('Dagens historie')}`
        + story(m, n++, { ...opts, tag: true, top: true, lead: true, pic }) + mainAnswer(m, '', svarSet) + '</section>' + html;
    }
  }
  return filled ? html : null;   // a composition with none of its stories left: the fixed page
}
// Does a development belong to a story? Its name and the story's headline (the shown one, its lead article's and the
// Danish one – not the other outlets' headlines, not the development's lines) share a specific subject: a wiki page both
// name (never one in nearly every answer, like the USA) or a word of the name; the actors every story names (Trump,
// Putin) are no shared subject. 'Iran og angrebet' is not the story of Trump's pause of the Russia sanctions.
const headStems = i => new Set([...stems([i.title, i.origTitle, i.title_da].join(' '))].filter(w => !GEN.has(w)));
function topicFits(i, tp) {
  if (!tp || !tp.name) return false;
  const ix = (V('bix') || {}).items || {}, broad = id => LINK_SKIP.has(id) || (ix[id] || {}).n_answers > BROAD;
  const subs = t => new Set(scan(t || '').map(f => f.id).filter(id => !broad(id)).map(subj));
  const head = subs([i.title, i.origTitle, i.title_da].filter(Boolean).join(' · '));
  for (const a of i.actors || []) if (!broad(a)) head.add(subj(a));
  if ([...subs(tp.name)].some(s => head.has(s))) return true;
  return overlap(new Set([...stems(tp.name)].filter(w => !GEN.has(w))), headStems(i)) >= 1;
}
// the editor filed this very story (one of its articles) as a line of the development
const filedIn = (i, tp) => { const ids = new Set([i.id, ...(i.members || []), ...(i.also || []).map(a => a.id)]); return tp.lines.some(l => ids.has(l.id)); };
const topicOf = (i, tp) => !!tp && (filedIn(i, tp) || topicFits(i, tp));
// the section most of a list's stories are in (more than half), or none
function mainSec(list) {
  const n = {};
  for (const i of list) n[secOf(i)] = (n[secOf(i)] || 0) + 1;
  const [s, c] = Object.entries(n).sort((a, b) => b[1] - a[1])[0] || [];
  return c > list.length / 2 ? s : '';
}
// the main story's answer line: at once when the files are here (and remembered, so an opened story on the page does
// not say it again), else a quiet place filled when they come
function mainAnswer(i, extra, skip) {
  const ready = V('bix') && V('mix'), a = ready ? answerFor(i, extra) : null;
  if (a && !String(skip).split(',').includes(a.nr)) { frontAns.add(a.nr); return `<div class="ans-ref">${answerLine(a)}</div>`; }
  return ready ? '' : `<div class="ans-ref" data-ans-for="${esc(i.id)}" data-ans-main="1"${extra ? ` data-ans-x="${esc(extra)}"` : ''}${skip ? ` data-ans-skip="${esc(skip)}"` : ''}></div>`;
}
// ---------------------------------------------------------------- the lede's parts open their stories (the owner, 17/10)
// "øverste titel skal linke til de forskellige nyheder": the lede is cut where its clauses meet (', ', ' mens ', ' og ',
// ';', ' – '); a part of fewer than three words joins its neighbour. Each part opens the story it names: the editor's
// `lede_ids` (one story id per part, in order; '' for none) when the update gave them, else the story that shares the
// part's distinctive words – names and places first, the words most stories share left out –, looked for among the
// front page's stories first, then in all of Live. Neighbouring parts about one story are one link; a part without a
// story stays plain text. Keep `lede_parts` in scripts/editor.py alike.
const LEDE_CUT = /(,\s+(?:og|mens)\s+|,\s+|;\s*|\s+–\s+|\s+mens\s+|\s+og\s+)/u;
const ledeWords = s => s.split(/\s+/).filter(w => /[\p{L}\p{N}]/u.test(w)).length;
function ledeParts(text) {
  const bits = String(text || '').trim().split(LEDE_CUT), out = [];
  for (let k = 0; k < bits.length; k += 2) {
    const p = { t: bits[k], sep: k ? bits[k - 1] : '' };
    if (out.length && ledeWords(p.t) < 3) out[out.length - 1].t += p.sep + p.t;
    else out.push(p);
  }
  if (out.length > 1 && ledeWords(out[0].t) < 3) { out[1] = { t: out[0].t + out[1].sep + out[1].t, sep: '' }; out.shift(); }
  return out.filter(p => p.t);
}
// the words a part names, each with its weight: a name (a capital, or a wiki page the part names) 2, another word of
// five letters or more 1; compared by their first six letters, so 'Ruslands' is 'Rusland'
const LEDE_STOP = new Set(['efter', 'under', 'siger', 'sagde', 'mange', 'flere', 'denne', 'dette', 'disse', 'imod', 'mellem', 'omkring',
  'blandt', 'igen', 'endnu', 'stadig', 'allerede', 'kalder', 'mens', 'samtidig', 'første', 'andre', 'anden', 'hvor', 'havde', 'bliver',
  'blevet', 'skulle', 'kunne', 'ville', 'være', 'været', 'over', 'langs', 'store', 'stort', 'større', 'nyt', 'nye', 'dagen', 'døgnet',
  'efterhånden', 'there', 'their', 'which', 'after', 'while', 'today']);
const ledeStem = w => w.toLowerCase().slice(0, 6);
function ledeKeys(text, wiki = []) {
  const keys = new Map();
  for (const w of String(text || '').split(/[^\p{L}\p{N}]+/u)) {
    const lw = w.toLowerCase();
    if (!w || LEDE_STOP.has(lw)) continue;
    const name = /^\p{Lu}/u.test(w) && (lw.length >= 3 || w === w.toUpperCase());
    if (!name && lw.length < 5) continue;
    const k = ledeStem(w);
    keys.set(k, Math.max(keys.get(k) || 0, name ? 2 : 1));
  }
  for (const id of wiki) keys.set('#' + id, 2);
  return keys;
}
// a story's words: its headlines (the shown one, its lead article's, the Danish one, the other outlets'), its bold words
// and the wiki's pages it names
const ledeStoryKeys = (i, wiki) => {
  const text = [i.title, i.origTitle, i.title_da, ...(i.also || []).map(a => a.title), ...(i.kw || []), ...(i.kw_da || [])].filter(Boolean).join(' · ');
  return new Set([...text.split(/[^\p{L}\p{N}]+/u).filter(w => w.length >= 2).map(ledeStem),
    ...[...(i.actors || []), ...wiki(text)].map(id => '#' + id)]);
};
// parts: ledeParts(text); front: the front page's stories in its order; live: all of Live; ids: the editor's lede_ids;
// byId: a story by its id (any of its articles); wiki: the wiki page ids a text names
function ledeLinks(text, front, live, ids = null, byId = () => null, wiki = () => []) {
  const parts = ledeParts(text), pool = [...new Map([...front, ...live].filter(Boolean).map(i => [i.id, i])).values()];
  const keysOf = new Map(pool.map(i => [i.id, ledeStoryKeys(i, wiki)]));
  const df = new Map();
  for (const ks of keysOf.values()) for (const k of ks) df.set(k, (df.get(k) || 0) + 1);
  const N = pool.length, common = k => N >= 8 && df.get(k) > N / 4;
  const best = (keys, list) => {
    let top = null, score = 0;
    for (const i of list) {
      const ks = keysOf.get(i.id);
      let sc = 0, hits = 0, named = false;
      for (const [k, w] of keys) {
        if (!ks.has(k) || common(k)) continue;
        hits++; named ||= w === 2; sc += w * Math.log(1 + N / df.get(k));
      }
      if ((named || hits >= 2) && sc > score + 1e-9) { top = i; score = sc; }
    }
    return score >= 2.5 ? top : null;
  };
  const frontIds = new Set(front.filter(Boolean).map(i => i.id)), inFront = pool.filter(i => frontIds.has(i.id));
  const out = [];
  parts.forEach((p, k) => {
    let id = null;
    const given = Array.isArray(ids) ? ids[k] : undefined;
    if (given === '' || given === null) id = null;   // the editor: this part names no story
    else {
      const g = typeof given === 'string' ? byId(given) : null;
      if (g) id = g.id;
      else { const keys = ledeKeys(p.t, wiki(p.t)); id = (best(keys, inFront) || best(keys, pool) || {}).id || null; }
    }
    const last = out[out.length - 1];
    if (last && id && last.id === id) last.t += p.sep + p.t;
    else out.push({ ...p, id });
  });
  return out;
}
// the lede as one paragraph: each part with a story a real link to it (no paragraph is a button), its closing stop
// outside the link
function ledeHtml(lede, front, ids) {
  const wiki = t => scan(t).map(f => f.id).filter(id => !LINK_SKIP.has(id));
  // the first part – the day's heaviest news – is the headline of the page; the rest runs on after it, a step quieter
  // (the rest begins on its own line: without the word that joined it – ', ', ' mens ', ' og ' – and with a capital)
  const parts = ledeLinks(lede, front, stories(), ids, findStory, wiki).map((p, n) => n === 1 ? { ...p, sep: '', t: cap(p.t.replace(/^[\s,;–-]+/u, '')) } : p).map(p => {
    if (!p.id) return esc(p.sep + p.t);
    const [, words, stop] = p.t.match(/^([\s\S]*?)([.!?…]*)$/u);
    return `${esc(p.sep)}<a class="lede-a" href="?item=${encodeURIComponent(p.id)}" data-lede="${esc(p.id)}">${esc(words)}</a>${esc(stop)}`;
  });
  return parts.length ? `<span class="lede-h">${parts[0]}</span>${parts.length > 1 ? `<span class="lede-r">${parts.slice(1).join('')}</span>` : ''}` : '';
}
// a part of the lede tapped: its story on the front page opens in place, in view; one the page does not show opens in
// Live, as a link with ?item= does
function ledeGo(id) {
  const i = findStory(id);
  if (!i) return;
  const el = tab === 'home' && pg$('s-' + i.id);
  if (!el) { openInLive(i.id); return; }
  if (!el.classList.contains('open')) toggle(el);
  cancelAnimationFrame(moveT);   // no pinning of the row where it was: it comes up under the bar
  scrollToEl(el, 8);
  setTimeout(() => { if (!touching && el.isConnected) scrollToEl(el, 8); }, 150);   // rows above it laid out by now
}
// the stories a front page shows, in its order: its rows and its Live strip
const pageStories = html => [...new Set([...html.matchAll(/(?:id="s-|data-live=")([^"]+)"/g)].map(m => m[1]))].map(id => find(id) || findStory(id));
// the head of the front page: the date with 'Del overblik' (the day's overview as a WhatsApp text), the editor's lede
// whole – what informs is never cut (the editor keeps it to about 25 words), its parts the ways to their stories –, and
// after a long break one line of what came meanwhile
function ledeHead(lede, body = '', ids = null) {
  const todayStr = FMT.ymd.format(new Date());
  return `<header class="lede"><div class="lede-d"><span>${cap(dateDa(todayStr, true))}</span>`
    + `<button class="lede-share" data-brief aria-label="Del dagens overblik"><svg aria-hidden="true"><use href="#i-share"/></svg><span aria-hidden="true">Del overblik</span></button></div>`
    + (lede ? `<p class="lede-t">${ledeHtml(lede, pageStories(body), ids)}</p>` : '') + catchUpLine() + '</header>' + installCard();
}
// the foot: what Khabar read and chose (the prices live in the Økonomi tab)
function homeFoot(all) {
  const src = Object.keys(data.sources || {}).length, day = all.filter(i => hours(i) < 24).length;
  return `<p class="foot">Khabar har læst ${num(data.scanned_24h)} nyheder fra ${src} kilder det seneste døgn og valgt ${day} ud.</p>`;
}
function home(all, opts) {
  opts = { ...opts, home: true };
  frontAns.clear();
  const f = frontNow(), composed = f && composedHome(all, opts, f);
  // the lede's parts link the stories the page shows: the page is drawn first
  if (composed) return ledeHead(f.lede || notes().lede, composed, f.lede ? f.lede_ids : notes().lede_ids) + composed + homeFoot(all);
  frontAns.clear();
  return fixedHome(all, opts);
}
// the fixed front page, while the editor has composed none today: the day's main story as a package, the rest of the
// day's top, Danish stories only when they matter, the developments, the day's quote, Live
function fixedHome(all, opts) {
  const news = all.filter(i => i.kind !== 'kommentar'), top = frontCands(news), pkg = mainChoice(top);
  let html = '';
  const lead = pkg ? pkg.story : top.find(i => i.thumb) || top[0];
  // the package's other stories about the same thing stay out of the lists below
  const same = i => pkg && i !== lead && overlap(stems([i.title, i.origTitle, i.title_da].join(' ')), pkg.ts) >= 3;
  const pin = pinnedQuote();
  let pq = null, own = null;
  if (lead) {
    // a Danish outlet's headline for the package when the story has one
    const dk = lead.lang !== 'da' && lead.how !== 'ed' && (lead.also || []).find(a => a.group === 'dk' && !curious(a.title));
    const shown = dk ? { ...lead, title: dk.title, origTitle: dk.title, source: dk.source, kw: [] } : lead;
    html += `<section class="block top pkg${leadPic(lead) ? '' : ' text'}" data-sec="${secOf(lead)}">${blockHead('Dagens historie')}${story(shown, 0, { ...opts, tag: true, top: true, lead: true, pic: leadPic(lead) })}`;
    // one quiet line when the amir has answered on the main story's subject (its own words, and the recap topic's name
    // when that topic is the story's own); the topic's timeline only then too
    own = pkg && pkg.topic && topicOf(lead, pkg.topic) ? pkg.topic : null;
    html += mainAnswer(lead, own ? own.name : '', '');
    if (own) {
      const tl = storyline(pkg.topic);
      pq = pin ? null : packageQuote(pkg, new Set(tl.lines.map(l => l.who)));
      html += tl.html + (pq ? `<div class="pkg-q">${quoteCard(pq, true)}</div>` : '');
    }
    html += '</section>';
  }
  if (!pq) html += quoteOfDay(pin);   // the day's quote right under Dagens historie (the owner, 17/10), when it had none
  const rest = top.filter(i => i !== lead && !same(i)).slice(0, 3);
  html += `<section class="block">${blockHead('Døgnets vigtigste', moreLink('Alle', 'latest'))}
    ${rest.map((i, n) => story(i, n + 1, { ...opts, tag: true, top: true })).join('')}</section>`;
  // 'Danmark' only when a Danish story matters (big, Danish politics on Islam and Muslims, or among the day's five
  // strongest), and then its two strongest such stories not shown above
  const onPage = new Set([lead, ...rest].filter(Boolean).map(i => i.id)), tops = dayTops();
  const dk = pick(news.filter(i => secOf(i) === 'dk' && i.confirmed !== 0 && hours(i) < 24 && !onPage.has(i.id) && !same(i) && dkMatters(i, tops)), 2);
  if (dk.length) html += `<section class="block">${blockHead('Danmark')}${dk.map((i, n) => story(i, n + 5, { ...opts, tag: false, top: true })).join('')}</section>`;
  dk.forEach(i => onPage.add(i.id));
  html += calBlock();   // 'Det sker snart' between the news and the developments
  html += followStrip(own);   // not the main story's own development again
  html += nowStrip(3, onPage);
  return ledeHead(notes().lede, html, notes().lede_ids) + html + homeFoot(all);
}
// a statement from the recap, set as a quote (the front page's 'Dagens citat' and the main story's)
const quoteCard = (l, pick) => `<a class="quote"${pick ? ' data-pick' : ''} href="${esc(l.link || '#')}" target="_blank" rel="noopener"><q>${esc(l.text)}</q><span>${esc(l.who)}</span></a>`;

// ---------------------------------------------------------------- Mens du var væk (pro-plan 5.3)
// After three hours away, one line under the lede says what came meanwhile – counts only, each a way in: Live with the
// new rows marked, the development that moved most, the new answer. It fades after the first scroll or tab change and
// stores nothing new (it reads the time the app was put away, which the phone keeps already).
const CATCH_AFTER = 3 * 3600e3;
let catchUp = null;   // {since: ms} while the line is shown
function noteBreak(away) { if (away && Date.now() - away >= CATCH_AFTER) catchUp = { since: away }; }
function catchUpLine() {
  if (!catchUp || catchUp.done || !data) return '';
  const since = catchUp.since, fresh = stories().filter(i => firstFound(i) && Date.parse(firstFound(i)) > since);
  const tops = fresh.filter(i => topNow().has(i.id)).length;
  const moved = threads().map(t => ({ t, n: t.lines.filter(l => l.added && Date.parse(l.added) > since).length })).filter(x => x.n).sort((a, b) => b.n - a.n)[0];
  const ans = answers().list.filter(a => a.fresh && !ansSeen.has(a.nr));
  const parts = [];
  if (fresh.length) parts.push(`<button data-go="latest">${fresh.length} ${fresh.length === 1 ? 'ny' : 'nye'}</button>`);
  if (tops) parts.push(`<button data-go="latest">${tops} med høj betydning</button>`);
  if (moved) parts.push(`<button data-follow="${moved.t.key}">${updWord(moved.n)} i ${esc(moved.t.name)}</button>`);
  if (ans.length) parts.push(`<button data-svar="${esc(ans[0].nr)}">${ans.length} ${ans.length === 1 ? 'nyt svar' : 'nye svar'}</button>`);
  if (!parts.length) return '';
  // each count carries its '·' before it (style.css), so a wrapped line never starts with one
  return `<p class="catch" id="catchUp"><span>Siden ${esc(fromWhen(new Date(since).toISOString()))}:</span>${parts.join('')}</p>`;
}
function fadeCatchUp() {
  if (!catchUp || catchUp.done) return;
  catchUp.done = true;
  const el = pageEl('home').querySelector('#catchUp');
  if (el) el.classList.add('fade');   // opacity only; the next drawing leaves it out
}

// ---------------------------------------------------------------- the iPhone install hint (pro-plan 3.11)
// On iPhone in Safari, not from the home screen, one quiet card at the top of Forside from the second visit on, once:
// notifications need the app on the home screen. Remembered on the phone; no consent prompt.
const iosSafari = visitOs === 'ios' && !(matchMedia('(display-mode: standalone)').matches || navigator.standalone === true);
let iosHint = iosSafari && store.get('introSeen', false) && !store.get('iosHint', 0);
// remembered as shown only once the front page was in view with it (a visit that came on a link straight to a story or
// an answer never saw it), or when it is closed
const hintSeen = () => { if (iosHint === true && tab === 'home' && !introOn()) { store.set('iosHint', Date.now()); iosHint = 'seen'; } };
const installCard = () => (iosHint ? `<div class="hint-card" id="iosHint"><a href="guide.html#iphone"><span>Læg Khabar på hjemmeskærmen for at få notifikationer · <b>Sådan</b></span><svg aria-hidden="true"><use href="#i-chev"/></svg></a>`
  + '<button data-hint-x aria-label="Luk"><svg aria-hidden="true"><use href="#i-x"/></svg></button></div>' : '');

// ---------------------------------------------------------------- Del dagens overblik (pro-plan 5.4)
// The day's top stories as a WhatsApp text in the group's own form: the date, the lede, up to five stories with their
// outlet and link, 'via khabar.nu'. One story from each of the editor's blocks in the front page's order (the main story
// first, then each list's first), so no block of the day drops out; then the blocks' next stories. Only headlines that
// are checked or the outlet's own Danish words: the editor's, or a Danish outlet's plain headline – never a machine
// translation, a teaser standing in or a curiosity headline. Never analysis, never commentary.
const TRACKING = /^(?:utm_\w+|referrer|ref|ref_src|cmpid|xtor|at_\w+|fbclid|gclid|ocid|mc_\w+|smid|src)$/i;
function cleanLink(u) {
  try {
    const x = new URL(u);
    for (const k of [...x.searchParams.keys()]) if (TRACKING.test(k)) x.searchParams.delete(k);
    return x.toString().replace(/\?$/, '');
  } catch { return u; }
}
const briefOk = i => i && i.kind !== 'kommentar' && (i.how === 'ed' || (i.lang === 'da' && !i.how && !i.teased && !curious(i.title)));
function briefText() {
  const f = frontNow(), lede = (f && f.lede) || notes().lede || '', rows = [], seen = new Set();
  const put = (i, title) => { if (i && !seen.has(i.id) && rows.length < 5) { seen.add(i.id); rows.push({ i, title: title || i.title }); return true; } return false; };
  const blocks = f ? f.blocks.filter(b => b && (b.kind === 'top' || b.kind === 'liste')) : [];
  const ids = b => (b.kind === 'top' ? b.with || [] : b.stories || []).map(x => findStory(String(x || '')));
  for (const b of blocks) {   // one from each block
    const main = b.kind === 'top' && findStory(String(b.story || ''));
    if (main && (b.title || briefOk(main)) && put(main, b.title)) continue;
    put(ids(b).find(i => i && !seen.has(i.id) && briefOk(i)));
  }
  for (const b of blocks) for (const i of ids(b)) if (briefOk(i)) put(i);   // then each block's next stories
  for (const i of frontCands(stories())) if (briefOk(i)) put(i);   // no composition today: the day's strongest
  return [`*Dagens nyheder – ${dateDa(FMT.ymd.format(new Date()), true)}*`, lede,
    rows.map(x => `- *${x.title}* (${x.i.source}) ${cleanLink(x.i.link)}`).join('\n\n'), 'via khabar.nu'].filter(Boolean).join('\n\n');
}
// Live is one list (the owner, 18/10: 'Nyheder skal have én fane, ingen "seneste" og "vigtigste"'): everything as it
// comes in, all sections mixed, newest first, each row showing its weight (weightOf) – the old choice 'Vigtigste' is gone
// three filters (the owner, 17/10: "3 nemme filtre … verden mellemøsten og danmark"): one tap shows one section, a tap on
// it again all of Live; for the visit only, so Live never opens filtered
let liveSec = '';
// 'Kun vigtige' (the owner, 18/10: 'en knap der frasorterer alt med lav betydning på kalender og nyheder'): Live and the
// Kalender without what is of low weight; remembered on the phone, and the page says so at its top with a way back
let liveImp = !!store.get('liveImp', false);
const impChip = (on, attr) => `<button class="chip imp-chip${on ? ' on' : ''}" ${attr} aria-pressed="${on}"><i class="imp-i" aria-hidden="true"></i>Kun vigtige</button>`;
const impNote = (n, attr) => `<p class="imp-note">Kun høj og middel betydning${n ? ` · ${n} skjult` : ''}<button class="qbtn" ${attr}>Vis alt</button></p>`;
// the dock's row for Live (the options within the thumb's reach): 'Kun vigtige', then the three sections
function liveOpts() {
  return `<div class="o-row live-secs" id="o-live-f" role="group" aria-label="Vis kun">${impChip(liveImp, 'data-live-imp')}${['dk', 'me', 'world'].map(k =>
    `<button class="chip${liveSec === k ? ' on' : ''}" data-live-sec="${k}" aria-pressed="${liveSec === k}"><i class="sd" data-sec="${k}"></i>${SECTIONS[k]}</button>`).join('')}</div>`;
}
function latestPage(all, opts) {
  const gone = focusMissing ? stateBlock('gone', 'Historien er ikke længere i Live.', [['Søg efter den', `data-find-item="${esc(focusMissing)}"`], ['Luk', 'data-gone-x']]) : '';
  if (liveSec) all = all.filter(i => secOf(i) === liveSec);
  // the count says what the list in view hides (the last 24 hours, or all once 'Vis ældre' was tapped)
  let note = '';
  if (liveImp) { const n = (latestAll ? all : all.filter(i => hours(i) < 24)).length; all = all.filter(i => weightOf(i) > 1);
    note = impNote(n - (latestAll ? all : all.filter(i => hours(i) < 24)).length, 'data-live-imp'); }
  const recent = latestAll ? all : all.filter(i => hours(i) < 24);
  let html = gone + note + timeline(recent, { ...opts, tag: !liveSec, tick: true });
  if (recent.length < all.length) html += `<button class="qbtn" data-latest-all>Vis ældre (${all.length - recent.length})</button>`;
  return html;
}
// search ignores accents and Turkish letters (Erdogan finds Erdoğan); marks are set on the plain text, all at once
const fold = s => String(s || '').toLowerCase().replace(/ı/g, 'i').normalize('NFD').replace(/[̀-ͯ]/g, '');
// a search word is found where a word starts ('iran' finds 'Iran' and 'Irans', not 'Mirán')
const LETTER = /[\p{L}\p{N}]/u;
const startsAt = (f, i) => i === 0 || !LETTER.test(f[i - 1]);
const hasWord = (f, w) => { for (let i = f.indexOf(w); i >= 0; i = f.indexOf(w, i + 1)) if (startsAt(f, i)) return true; return false; };
function mark(text, terms) {
  const f = fold(text), at = [];
  if (f.length === text.length) {   // where folding changed the length, no marks rather than marks in the wrong place
    for (const t of terms) {
      for (let i = t.length > 1 ? f.indexOf(t) : -1; i >= 0; i = f.indexOf(t, i + 1)) if (startsAt(f, i)) { at.push([i, i + t.length]); i += t.length - 1; }
    }
  }
  let out = '', p = 0;
  for (const [a, b] of at.sort((x, y) => x[0] - y[0])) {
    if (a < p) continue;
    out += esc(text.slice(p, a)) + '<mark>' + esc(text.slice(a, b)) + '</mark>'; p = b;
  }
  return out + esc(text.slice(p));
}
// ---------------------------------------------------------------- Følg udviklingen
// A development is one of the editor's recap topics followed across the days it ran (the editor continues a topic
// by its exact name): its headline is the topic's name, its steps the recap's 'Who: what' lines, oldest first.
const thrKey = name => qkey({ who: 'tråd', text: name.trim().toLowerCase() });
// worked out once per edition and archive (the front page asks for it in every block that names a development)
let thrMemo = null;
function allThreads() {
  if (thrMemo && thrMemo.digest === digest && thrMemo.moves === moves) return thrMemo.list;
  const list = buildThreads();
  thrMemo = { digest, moves, list };
  return list;
}
function buildThreads() {
  const days = [dayOf(digest), ...((moves && moves.days) || [])].filter(Boolean), seenDay = new Set(), by = new Map();
  for (const d of days) {
    if (seenDay.has(d.date)) continue;
    seenDay.add(d.date);
    for (const tp of d.topics) {
      const k = tp.name.trim().toLowerCase();
      const t = by.get(k) || { key: thrKey(k), name: tp.name, section: tp.section, lines: [] };
      t.lines.push(...tp.lines.filter(l => l.at));
      by.set(k, t);
    }
  }
  return [...by.values()].map(t => {
    const seen = new Set();
    t.lines = t.lines.filter(l => { const id = l.id || l.text; if (seen.has(id)) return false; seen.add(id); return true; })
      .sort((a, b) => a.at.localeCompare(b.at));
    t.last = t.lines.length ? t.lines[t.lines.length - 1].at : '';
    t.days = new Set(t.lines.map(l => dayKey(new Date(l.at)))).size;   // 'fulgt i 8 dage'
    return t;
  }).filter(t => t.lines.length).sort((a, b) => b.last.localeCompare(a.last));
}
let thr2 = null;
const threads = () => (thr2 && thr2.all === allThreads() ? thr2 : (thr2 = { all: allThreads(), list: allThreads().filter(t => t.lines.length >= 2) })).list;   // a development has at least two steps
// the development a story belongs to: one of its lines is the story, or it shares enough words with it
function threadFor(i) {
  const ids = new Set([i.id, ...(i.also || []).map(a => a.id)]), list = threads();
  const direct = list.find(t => t.lines.some(l => ids.has(l.id)));
  if (direct) return direct;
  // otherwise only a close match: five or more shared names and words (a passing 'Gaza' or 'Israel' is not enough),
  // and a name that shares a subject with the story's headline
  const st = stems([i.title, i.origTitle, i.title_da, ...(i.also || []).map(a => a.title)].join(' '));
  let best = null, score = 4;
  for (const t of list.slice(0, 30)) {
    const sc = overlap(stems(t.name + ' ' + t.lines.map(l => l.who + ' ' + l.text).join(' ')), st);
    if (sc > score && topicFits(i, t)) { best = t; score = sc; }
  }
  return best;
}
// The Udvikling page holds the editor's lines once (the recap and the developments were two views of the same lines;
// the owner had them merged, 2026-10-11): the day's topics in the editor's order, each a card with the day's updates,
// newest first, that unfolds into the whole development across the days – today and the two days before at first, then
// twenty more at a time; below, the developments the day has not touched; at the bottom the earlier days as whole
// recaps, to read or share. Each card shares itself as a WhatsApp text with a link back to it (?forlob=…).
const newestFirst = ls => [...ls].filter(l => l.at).sort((a, b) => b.at.localeCompare(a.at));
const lineNew = l => lastSeen && l.added && new Date(l.added).getTime() > lastSeen;
function udSteps(lines, marks) {
  const sess = linkSession();   // one development is one block of text: each name links once, at most three
  const cls = l => (lineNew(l) ? 'new' : '');
  return `<ol class="thr-steps ud-steps">${marks ? stepsWithDays(lines, sess, cls) : lines.map(l => stepHtml(l, '', cls(l), sess)).join('')}</ol>`;
}
// the first lines of an unfolded course: today and the two days before (at least SHOW lines)
function recentCourse(all) {
  const days = [];
  for (const l of all) { const k = dayKey(new Date(l.at)); if (!days.includes(k)) days.push(k); if (days.length > 3) break; }
  const keep = new Set(days.slice(0, 3));
  return Math.max(Math.min(SHOW, all.length), all.filter(l => keep.has(dayKey(new Date(l.at)))).length);
}
// one development; `tp` is its topic in the day shown at the top, whose lines show before it is unfolded
function udCard(t, tp) {
  const open = udOpen.has(t.key), all = newestFirst(t.lines);
  const today = tp ? newestFirst(tp.lines) : [], first = today.slice(0, SHOW);
  const hidden = tp ? all.length - first.length : all.length - 1, last = all[0];
  const meta = metaLine(SECTIONS[t.section], tp ? [`${today.length} ${today.length === 1 ? 'ny' : 'nye'} i dag`, ...(t.days > 1 ? [`fulgt i ${t.days} dage`] : [])]
    : thrParts(t), 'thr-m');
  // unfolded, a long course shows its last three days first, then twenty more at a time (the button keeps its place)
  const sk = `ud|${t.key}`, shownN = open ? Math.min(all.length, recentCourse(all) + (steps[sk] ? steps[sk] - STEP : 0)) : 0;
  const body = open ? udSteps(all.slice(0, shownN), t.days > 1) : tp ? udSteps(first, false) : '';
  const left = all.length - shownN;
  const more = !hidden ? '' : open ? (left > 0 ? '' : 'Vis mindre') : t.days > 1 ? `Hele forløbet · ${t.days} dage` : `+ ${hidden} mere`;
  const head = `${meta}<h3>${esc(t.name)}</h3>${!tp && !open && last ? `<p class="thr-last">${last.who ? `<b>${esc(last.who)}:</b> ` : ''}${esc(last.text)}</p>` : ''}`;
  const older = open && left > 0 ? `<button class="qbtn" data-step="${esc(sk)}">Vis ${Math.min(STEP, left)} ældre · ${left} tilbage</button>` : '';
  return `<article class="thr ud${open ? ' open' : ''}" id="thr-${t.key}" data-sec="${esc(t.section || '')}">${hidden
    ? `<button class="thr-head" data-thr="${t.key}" aria-expanded="${open}">${head}<svg aria-hidden="true"><use href="#i-chev"/></svg></button>` : `<div class="thr-head">${head}</div>`}
    ${body}${older}<div class="ud-foot">${more && (open || tp) ? `<button class="ud-more" data-thr="${t.key}">${more}</button>` : '<span></span>'}`
    + `<span class="ud-acts"><button data-thr-share="${t.key}"><svg aria-hidden="true"><use href="#i-share"/></svg>Del</button>`
    + `<button data-thr-copy="${t.key}"><svg aria-hidden="true"><use href="#i-copy"/></svg>Kopiér</button></span></div></article>`;
}
// a development as a WhatsApp text: its name, today's updates (else its newest), at most six, and the way back to it
function thrText(t) {
  const all = newestFirst(t.lines), today = all.filter(l => dayKey(new Date(l.at)) === dayKey(new Date()));
  const lines = (today.length ? today : all).slice(0, 6).map(l => `- ${clock(l.at)} ${lineLabel(l)}`);
  return [`*${t.name}*`, lines.join('\n'), `via khabar.nu/?forlob=${t.key}`].join('\n\n');
}
let udAll = false;
function threadsPage() {
  if (!moves && archiveState === 'idle') setTimeout(loadArchive, 0);
  const day = dayOf(digest), shown = day && day.topics.length && Date.now() - new Date(day.created) < 48 * 3600e3 ? day : null;
  const by = new Map(allThreads().map(t => [t.key, t]));
  const lede = (frontNow() || {}).lede || notes().lede;
  let html;
  if (shown) {
    const today = shown.date === FMT.ymd.format(new Date());
    html = `<header class="ud-top" data-day="${esc(shown.date)}"><span><b>${today ? 'I dag' : cap(dateDa(shown.date, true))}</b>`
      + `<small>Resumé kl. ${clock(shown.created)}</small><small>${updWord(lineCount(shown))}</small></span>`
      + '<button class="ud-share" data-day-share><svg aria-hidden="true"><use href="#i-share"/></svg>Del resumé</button></header>'
      + (lede && today ? `<p class="ud-lede">${rich(lede, linkSession())}</p>` : '')
      + shown.topics.map(tp => { const t = by.get(thrKey(tp.name)); return t ? udCard(t, tp) : ''; }).join('');
  } else {
    html = '<header class="ud-top"><span><b>Udvikling</b><small>Dagens vigtigste udviklinger – opdateres løbende fra morgen til aften</small></span></header>';
  }
  const todays = new Set(shown ? shown.topics.map(tp => thrKey(tp.name)) : []);
  const rest = threads().filter(t => !todays.has(t.key));
  if (rest.length) html += `<h2 class="grp ud-h">${shown ? 'Fulgt de seneste dage' : 'Udviklinger'}</h2>`
    + (udAll ? rest : rest.slice(0, 8)).map(t => udCard(t, null)).join('')
    + (rest.length > 8 && !udAll ? `<button class="qbtn" data-ud-all>Vis flere (${rest.length - 8})</button>` : '');
  if (!shown && !rest.length) html += stateBlock('empty', 'Ingen udviklinger at følge endnu.', [['Se Live', 'data-go="latest"']]);
  return html + `<section class="block ud-arch">${archive()}</section>`;
}
// ---------------------------------------------------------------- one search (pro-plan 5.2)
// One field for news, developments, Hizb ut-Tahrir's answers and the wiki's pages, with a scope (Alle · Nyheder · Svar ·
// Begreber) preset by the page one came from. Results come in groups: the pages as ochre chips, the developments, the
// answers (the best three and 'Alle n svar'), the stories in Live, and everything else the radar read in two days
// (headlines that are one story folded into one row). Empty: the last searches on this phone, the pages today's news
// names most, the developments that moved last, and what is saved.
const SCOPES = [['alle', 'Alle'], ['nyheder', 'Nyheder'], ['svar', 'Svar'], ['begreber', 'Leksikon']];
let searchScope = 'alle';
let recentQ = (() => { const v = store.get('recentQ', []); return Array.isArray(v) ? v.slice(0, 5) : []; })();
function rememberQuery() {
  const q = query.trim();
  if (q.length < 2) return;
  recentQ = [q, ...recentQ.filter(x => fold(x) !== fold(q))].slice(0, 5);
  idle(() => store.set('recentQ', recentQ));
}
// the wiki's pages today's news names most (Danish names, each once)
function popularPages(all) {
  if (!V('bix')) return [];
  const n = new Map();
  for (const i of all.filter(x => hours(x) < 24)) for (const id of new Set([...scan(i.title), ...scan(i.title_da || '')].map(f => f.id))) n.set(id, (n.get(id) || 0) + 1);
  return [...n.entries()].filter(([id]) => !LINK_SKIP.has(id)).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([id]) => id);
}
const scopeSeg = () => `<div class="seg four scope" role="radiogroup" aria-label="Søg i">${SCOPES.map(([v, l]) =>
  `<button role="radio" data-scope="${v}" aria-checked="${searchScope === v}">${l}</button>`).join('')}</div>`;
const sugRow = t => `<button class="sug-row" data-follow="${t.key}" data-sec="${esc(t.section || '')}"><i></i><span>${esc(t.name)}</span><em>${t.days > 1 ? `fulgt i ${t.days} dage` : updWord(t.lines.length)}</em><svg aria-hidden="true"><use href="#i-chev"/></svg></button>`;
function searchHome(all) {
  let html = '';
  if (recentQ.length) html += `<h2 class="grp">Seneste søgninger</h2><div class="sug">${recentQ.map(q => `<button class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join('')}</div>`;
  const pop = popularPages(all);
  if (pop.length) html += `<h2 class="grp">Populært nu</h2><div class="sug">${pop.map(id => `<button class="chip" data-q="${esc(nameOf(id).replace(/-sagen$/, ''))}">${chipName(id)}</button>`).join('')}</div>`;
  const ths = threads().slice(0, 3);
  if (ths.length && searchScope !== 'svar' && searchScope !== 'begreber') html += `<h2 class="grp">Udviklinger</h2><div class="sug-th">${ths.map(sugRow).join('')}</div>`;
  return html;
}
// the wiki's pages a query names (from three letters): names and Danish forms, the best first
function pagesFor(q) {
  const ix = V('bix');
  if (!ix || q.length < 3) return [];
  return Object.entries(ix.items || {}).map(([id, e]) => {
    const names = [e.name, ...(e.aliases || [])].map(fold), starts = names.some(n => n.startsWith(q)), has = starts || names.some(n => n.includes(q));
    return has ? { id, score: (starts ? 1000 : 0) + (e.n_answers || 0) } : null;
  }).filter(Boolean).sort((a, b) => b.score - a.score).map(p => p.id);
}
// headlines that are one story (the same first six words) fold into one row
function foldRepeats(rows) {
  const out = [], seen = new Map();
  for (const x of rows) {
    const k = [...stems4(x.da || x.t)].slice(0, 6).join(' ');
    if (k && seen.has(k)) { seen.get(k).n++; continue; }
    const row = { x, n: 1 }; out.push(row); if (k) seen.set(k, row);
  }
  return out;
}
function searchPage(all) {
  const q = fold(query.trim());
  if (!q) return scopeSeg() + searchHome(all);
  const terms = q.split(/\s+/).filter(Boolean), sc = searchScope, news = sc === 'alle' || sc === 'nyheder';
  const hit = t => { const f = fold(t); return terms.every(w => hasWord(f, w)); };
  let html = scopeSeg(), found = 0;
  // the wiki's pages, as ochre chips (a short row first: a name one searched for is a page one may want)
  if (sc === 'alle' || sc === 'begreber') {
    const pages = pagesFor(q);
    if (pages.length) { found += pages.length; html += `<h2 class="grp">Leksikon</h2>${chips(pages.slice(0, sc === 'begreber' ? 40 : 6), 'search|pages', sc === 'begreber' ? 40 : 6).replace('class="wk-chips"', 'class="wk-chips ht-chips"')}`; }
  }
  // the news first, in a news app: the developments, then the stories in Live (the first five under Alle)
  if (news) {
    const ths = threads().filter(t => hit(t.name + ' ' + t.lines.map(l => lineLabel(l)).join(' '))).slice(0, 4);
    if (ths.length) { found += ths.length; html += `<h2 class="grp">Udviklinger</h2><div class="sug-th">${ths.map(sugRow).join('')}</div>`; }
    const inApp = all.filter(i => hit(`${i.title} ${i.summary || ''} ${i.source} ${i.origTitle || ''}`)).sort((a, b) => when(b) - when(a));
    const n = sc === 'alle' ? 5 : 40;
    if (inApp.length) {
      found += inApp.length;
      html += `<h2 class="grp">På Khabar · ${inApp.length}</h2>` + inApp.slice(0, n).map((i, k) => story(i, k, { tag: true })).join('')
        + (inApp.length > n ? `<button class="qbtn" data-scope="nyheder">Alle ${inApp.length} nyheder</button>` : '');
    }
  }
  // Hizb ut-Tahrir's answers: the best three (all of them under the Svar scope) – those that name it in their title, then
  // in their question, then those that find it through a page they read ('via Khilafah'), each the newest first – and
  // the way to the rest in Analyser
  if (sc === 'alle' || sc === 'svar') {
    need('mix'); need('ans'); need('bfull');
    const tier = a => { const m = anMatch(a, terms); if (!m.ok) return -1; const t = fold(a.title + ' ' + (a.orig || '')); return terms.every(w => t.includes(w)) ? 0 : m.via ? 2 : 1; };
    const hits = answers().list.map(a => ({ a, t: tier(a) })).filter(x => x.t >= 0).sort((x, y) => x.t - y.t).map(x => x.a);   // stable: newest first within
    if (hits.length) {
      found += hits.length;
      const n = sc === 'svar' ? 40 : 3;
      html += `<h2 class="grp">Hizb ut-Tahrirs svar · ${hits.length}</h2><div class="rd-list">${hits.slice(0, n).map(a => anRow(a, terms)).join('')}</div>`
        + (hits.length > n ? `<button class="qbtn" data-an-q="${esc(query.trim())}">Alle ${hits.length} svar i Analyser</button>` : '');
    } else if (sc === 'svar' && waiting('mix')) html += loadingBlock('Henter svarene …');
  }
  // everything else the radar read in two days (in Danish where it has a Danish headline): ten, then the rest on a tap
  if (news) {
    if (searchIndex) {
      const onApp = new Set(data.items.map(i => i.id));
      const others = foldRepeats(searchIndex.items.filter(x => !onApp.has(x.i) && hit(`${x.t} ${x.da || ''} ${x.s}`)));
      if (others.length) {
        found += others.length;
        const ok = 'search|others', shownN = unfolded.has(ok) ? 60 : 10;
        html += `<h2 class="grp">Andre nyheder · ${others.length}</h2>` + others.slice(0, shownN).map(({ x, n }) => { const t = danish && x.da ? x.da : x.t;
          return `<a class="hit" href="${esc(x.u)}" target="_blank" rel="noopener"><b dir="auto">${mark(t, terms)}</b><span>${esc(x.s)} · ${stamp(x.p)}${n > 1 ? ` · ${n} medier` : ''}</span></a>`; }).join('')
          + (others.length > shownN && shownN < 60 ? `<button class="qbtn" data-unfold="${ok}">Vis flere (${others.length - shownN})</button>` : '');
      }
    } else html += searchState === 'error' ? stateBlock('error', 'Kunne ikke hente alle nyheder – viser kun dem på Khabar.', [['Prøv igen', 'data-search-retry']])
      : loadingBlock('Henter alle nyheder …');
  }
  if (!found && (searchIndex || sc === 'svar' || sc === 'begreber')) {
    html += stateBlock('empty', sc === 'nyheder' || sc === 'alle' ? `Ingen nyheder de seneste to døgn om »${esc(query.trim())}«.` : `Intet om »${esc(query.trim())}«.`,
      [...(sc !== 'svar' ? [[`Se svarene om »${esc(query.trim())}«`, 'data-scope="svar"']] : []), ['Leksikon A–Å', 'data-begreber']]);
  }
  return html;
}

// ---------------------------------------------------------------- Analyser: Hizb ut-Tahrir's political answers
// One compact title line, then a strip that stays under the bar: the search field, and one sideways row of chips – the
// wiki's A–Å, the areas by number of answers (a filter in place, remembered on the phone) and the years (a jump to their
// band). The newest on top (the editor's filed ones, the radar's newest), then the movement layer's 321 by year. A row:
// the Danish title, and one line – the date and the area (an answer one opened is drawn quieter).
let anQuery = '', anT = 0;
// an area's page id, or '' for all: a filter for this visit only (a reader back days later sees all the answers)
let anArea = '';
idle(() => { try { localStorage.removeItem('anArea'); } catch { /* nothing kept */ } });   // kept on the phone before 17/10
const unfolded = new Set();   // lists unfolded on a wiki page or in an answer: '<page or answer>|<part>'
let apMemo = null;
function answerPages() {   // answer -> the wiki's pages that hold it (from the whole wiki, once it is here)
  const bf = V('bfull');
  if (!bf) return new Map();
  if (apMemo && apMemo.bf === bf) return apMemo.m;
  const m = new Map();
  for (const [id, e] of Object.entries(bf.items || {})) for (const nr of e.answers || []) { if (!m.has(nr)) m.set(nr, []); m.get(nr).push(id); }
  apMemo = { bf, m };
  return m;
}
// why an answer matches a search: in its own words (title, question, original title), or only through a page it reads
// ('via Khilafah')
function anMatch(a, terms) {
  const own = a.own ||= fold([a.title, a.q || '', a.orig || ''].join(' '));
  if (terms.every(w => own.includes(w))) return { ok: true, via: '' };
  const bf = V('bfull');
  if (!a.names || a.namesB !== !!bf) {   // the pages it reads: each its name and the forms that find it
    a.names = [...aboutOf(a).keys()].map(s => { const n = nameOf(pageOf(s) || s); return { n, f: fold(n) }; });
    for (const id of answerPages().get(a.nr) || []) a.names.push({ n: bf.items[id].name, f: fold([bf.items[id].name, ...(bf.items[id].aliases || [])].join(' ')) });
    a.namesB = !!bf;
  }
  const all = own + ' ' + a.names.map(x => x.f).join(' ');
  if (!terms.every(w => all.includes(w))) return { ok: false };
  const via = a.names.find(x => terms.some(w => x.f.includes(w) && !own.includes(w)));
  return { ok: true, via: via ? via.n.replace(/-sagen$/, '').replace(/\s*\(.*\)$/, '') : '' };
}
// the phrase of the question that matched, under the title (one line)
function qSnippet(a, terms) {
  const q = a.q || '', f = fold(q);
  if (!q || f.length !== q.length || terms.every(w => fold(a.title).includes(w))) return '';
  const at = Math.min(...terms.map(w => f.indexOf(w)).filter(x => x >= 0));
  if (!Number.isFinite(at)) return '';
  const from = Math.max(0, q.lastIndexOf(' ', Math.max(0, at - 40)));
  return `<span class="an-q ht">${from > 0 ? '… ' : ''}${mark(q.slice(from).trim(), terms)}</span>`;
}
const ansRead = new Set(store.get('ansRead', []));   // the answers opened on this phone: their rows are drawn quieter
function markRead(nr) {
  if (ansRead.has(nr)) return;
  ansRead.add(nr);
  idle(() => store.set('ansRead', [...ansRead].slice(-400)));
}
// a row of the answers: the link to the answer, and beside it – never inside it – the bookmark (the owner, 17/10: "en
// 'gem' knap til højre på listen over analyser, så man ikke skal trykke sig ind på dem og så man kan se hvilke man har gemt")
const anRow = (a, terms) => { const area = areaOf(a), m = terms && terms.length ? anMatch(a, terms) : null, on = isSaved('a', a.nr);
  return `<div class="an-item"><a class="an-row${ansRead.has(a.nr) ? ' read' : ''}" href="?svar=${encodeURIComponent(a.nr)}" data-svar="${esc(a.nr)}"><b class="ht">${terms && terms.length ? mark(a.title, terms) : esc(a.title)}</b>`
    + (terms && terms.length ? qSnippet(a, terms) : '')
    + `<span>${esc(dSlash(a.date))}${area ? ' · ' + esc(area) : ''}${m && m.via ? ` · via ${esc(m.via)}` : ''}${a.fresh && !a.da ? ' · endnu kun på engelsk' : ''}</span></a>`
    + `<button class="an-save${on ? ' on' : ''}" data-ksave="a:${esc(a.nr)}" aria-pressed="${on}" aria-label="${on ? 'Gemt' : 'Gem'}: ${esc(a.title)}"><svg aria-hidden="true"><use href="#i-${on ? 'saved' : 'save'}"/></svg></button></div>`; };
// the areas the answers belong to, by number of answers (worked out once per list)
let areaMemo = null;
function anAreas() {
  const A = answers();
  if (areaMemo && areaMemo.gen === ansGen && areaMemo.bix === V('bix')) return areaMemo.list;
  const n = new Map();
  for (const a of A.list) { const id = areaIdOf(a); if (id) n.set(id, (n.get(id) || 0) + 1); }
  areaMemo = { gen: ansGen, bix: V('bix'), list: [...n.entries()].sort((x, y) => y[1] - x[1]) };
  return areaMemo.list;
}
function anCounts() {
  const layer = answers().list.filter(a => a.layer);
  return { n: answers().list.length, span: layer.length ? `${layer[layer.length - 1].date.slice(0, 4)}–${layer[0].date.slice(0, 4)}` : '' };
}
function analysesPage() {
  const c = anCounts();
  return `<header class="an-top"><h1 class="ht">Hizb ut-Tahrirs svar</h1><small>${c.n ? `${c.n} svar${c.span ? ' · ' + c.span : ''}` : ''}</small></header>`
    + `<div class="an-strip" id="anStrip"><div class="an-qw"><svg aria-hidden="true"><use href="#i-search"/></svg><input id="anQ" type="search" enterkeyhint="search" autocomplete="off"`
    + ` placeholder="Søg i svarene" aria-label="Søg i svarene" value="${esc(anQuery)}"></div></div>`
    + `<div class="an-list">${analysesList()}</div>`;
}
// the dock's row for Analyser: the wiki, the areas (a filter) and the years (a jump); what is saved is one tap away in
// the bar. The search field stays under the bar: the dock goes while the keyboard is up, and the field must not go with it
const anOpts = (t = tab) => `<div class="o-row an-chips" id="o-an" role="radiogroup" aria-label="Vis">${anChips(t)}</div>`;
// the dock: one toggle, Svar · Leksikon (the owner, 18/10: 'Burde begreber a-å ikke hedde … opslagsværk og være lidt
// mere fremtrædende' – he chose 'Leksikon' and the toggle): the answers' list, or the A–Å of the pages compiled from
// them; the same toggle shows on both, no filter beside it (17/10: 'skal der ikke være filter i bunden')
function anChips(t = tab) {
  const lex = t === 'begreber';
  return `<button class="chip${lex ? '' : ' on'}" role="radio" aria-checked="${!lex}" data-an-view="svar">Svar</button>`
    + `<button class="chip ht-chip${lex ? ' on' : ''}" role="radio" aria-checked="${lex}" data-an-view="leksikon">Leksikon</button>`;
}
function analysesList() {
  need('mix'); need('ans');
  const A = answers();
  if (!A.list.length) return waiting('mix') ? loadingBlock('Henter svarene …') : retry('svarene', 'mix', 'ans');
  const terms = fold(anQuery.trim()).split(/\s+/).filter(Boolean);
  if (terms.length) need('bfull');   // an answer is found by the concepts it reads too
  let shown = terms.length ? A.list.filter(a => anMatch(a, terms).ok) : A.list;
  if (anArea) shown = shown.filter(a => areaIdOf(a) === anArea);
  let html = '';
  // a query that names a page: that page first ('Khilafah · Begreb · 18 svar ›')
  const page = terms.length ? pagesFor(fold(anQuery.trim()))[0] : '';
  if (page) { const e = V('bix').items[page]; html += `<button class="qrow ht-row" data-begreb="${esc(page)}"><span><b>${esc(nameOf(page).replace(/-sagen$/, ' – sagen'))}</b> · ${esc(KINDS[e.kind] || e.kind)} · ${e.n_answers} svar</span><svg aria-hidden="true"><use href="#i-chev"/></svg></button>`; }
  if (anArea && !terms.length && pageOf(anArea)) html += `<button class="qrow ht-row" data-begreb="${esc(pageOf(anArea))}"><span>Siden om <b>${esc(areaName(anArea))}</b></span><svg aria-hidden="true"><use href="#i-chev"/></svg></button>`;
  if (!shown.length) return html + stateBlock('empty', `Intet svar matcher »${esc(anQuery.trim())}«${anArea ? ` om ${esc(areaName(anArea))}` : ''}.`,
    [...(anArea ? [['Alle områder', 'data-area=""']] : []), ['Søg i nyhederne', `data-search-q="${esc(anQuery.trim())}"`]]);
  if (terms.length || anArea) html += `<p class="an-n">${shown.length} svar</p>`;
  const fresh = shown.filter(a => a.fresh);
  if (fresh.length) html += '<div class="day an-y" role="heading" aria-level="2"><span>Nye svar</span></div>' + fresh.map(a => anRow(a, terms)).join('');
  let y = '';
  for (const a of shown) {
    if (a.fresh) continue;
    const yr = a.date.slice(0, 4);
    if (yr !== y) { y = yr; html += `<div class="day an-y" id="an-y-${esc(yr)}" role="heading" aria-level="2"><span>${esc(yr)}</span></div>`; }
    html += anRow(a, terms);
  }
  return html;
}
// the answers the phone has seen in Analyser: a new one puts a dot on the tab until the tab is looked at
const ansSeen = new Set(store.get('ansSeen', []));
const unseenAnswer = () => answers().list.some(a => a.fresh && !ansSeen.has(a.nr));
function markAnswersSeen() {
  const fresh = answers().list.filter(a => a.fresh).map(a => a.nr);
  if (fresh.every(nr => ansSeen.has(nr))) return;
  fresh.forEach(nr => ansSeen.add(nr)); store.set('ansSeen', [...ansSeen].slice(-100));
}
// the library on the phone (pro-plan 5.1): after the first visit to Analyser the answers' and the wiki's whole files
// are fetched in a quiet moment (the service worker keeps them), so saved answers and pages open offline – not on a
// phone that saves data or on a slow connection
// Once per build of the library, not at every visit: the service worker keeps the files, so they are only fetched (not
// read – 1.7 MB of JSON is parsed when a page needs it, never as a stutter on a slow phone), and the phone remembers
// for which build it did (the index's 'built')
let libAsked = false;
function prefetchLibrary() {
  if (libAsked) return;
  const c = navigator.connection || {}, built = (V('mix') || {}).built || '';
  if (c.saveData || /2g/.test(c.effectiveType || '') || !built || !('serviceWorker' in navigator)) return;   // asked again once the index is here
  libAsked = true;
  if (store.get('libFor', '') === built) return;
  idle(() => Promise.all(['mfull', 'bfull'].map(k => fetch(VFILES[k]()).then(r => (r.ok ? r.arrayBuffer() : Promise.reject(r.status)))))
    .then(() => store.set('libFor', built), () => { libAsked = false; }));
}

// ---------------------------------------------------------------- the answer reader
// The byline with its date, area and the original (the page's one label); the Danish title and the question under it;
// Del · Kopiér · Gem as one quiet row; one ochre panel with 'Svaret kort' and what the answer reads (its subjects open
// their wiki pages, a hairline between them); a quiet row to a newer answer on the same subject; its concepts, the
// earlier answers it cites and the later ones that cite it, today's stories on its subject, its text when the app holds
// it (folded behind 'Læs hele svaret'). Everything that is the movement's is set in its face (17/10: "uoverskuelig").
let svarNr = params.get('svar') || '';
const SHOW_READS = 6;
// each paragraph finds its own direction (an English answer opens with the Arabic basmala)
const paras = text => String(text || '').trim().split(/\n\s*\n+/).map(b => {
  const t = b.trim();
  return t.length < 90 && !/[.!?»"”):;]$/.test(t) ? `<h4 dir="auto">${esc(t)}</h4>` : `<p dir="auto">${esc(t).replace(/\n/g, '<br>')}</p>`;
}).join('');
// a subject of the layer by its page ('rusland--usa' is two)
const subjLinks = s => String(s || '').split('--').map(p => { const pg = pageOf(p);
  return pg ? `<a class="bg sj" href="?begreb=${encodeURIComponent(pg)}" data-begreb="${esc(pg)}">${esc(nameOf(pg))}</a>` : `<span class="sj">${esc(nameOf(p))}</span>`; }).join(' og ');
// what this answer reads: only readings that are this answer's own (a reading over several answers belongs to the newest
// of them), each said once – one that repeats 'Svaret kort' or another reading is folded away (the texts are plain
// Danish without 'Ifølge …': the words compared are the reading's own)
const sig = t => new Set(String(t || '').toLowerCase().match(/[\p{L}\p{N}]{4,}/gu) || []);
const like = (x, y) => { let n = 0; for (const w of x) if (y.has(w)) n++; return n / Math.max(1, Math.min(x.size, y.size)); };
function readingsOf(a, full, note = '') {
  const said = [sig(note)], out = [];
  const keep = (s, text) => { const g = sig(text); if (said.some(x => like(g, x) >= 0.6)) return; said.push(g); out.push({ s, text }); };
  if (a.readings && a.readings.length) { for (const r of a.readings) if (r.text_da) keep(r.subject, r.text_da); return out; }
  if (!full) return [];
  const ab = aboutOf(a), rows = [];
  for (const [s, list] of Object.entries(full.readings || {})) for (const r of list) if (r.nr === a.nr) rows.push({ s, text: r.text_da });
  const weight = s => Math.max(0, ...s.split('--').map(p => ab.get(p) || 0));
  rows.sort((x, y) => weight(y.s) - weight(x.s));
  for (const r of rows) keep(r.s, r.text);
  return out;
}
const KIND_ORDER = ['begreb', 'aftale', 'proces', 'sted', 'organisation', 'gruppe', 'sag', 'magt', 'stat'];
// the pages as quiet chips, the first ten and the rest behind one more ('slack': how many over the first are shown
// rather than folded; the answer reader shows four at most)
const SHOW_CHIPS = 10, SHOW_SVAR_CHIPS = 4;
// a chip names its page; an issue page also says it is the issue ('Iran · sag'), so it is never taken for the state's
const chipName = id => { const e = ((V('bix') || {}).items || {})[id]; return e && e.kind === 'sag' && /-sagen$/.test(e.name || '')
  ? `${esc(e.name.replace(/-sagen$/, ''))}<small> · sag</small>` : esc(nameOf(id)); };
const chips = (ids, key, max = SHOW_CHIPS, slack = 2) => { const all = unfolded.has(key), shown = all || ids.length <= max + slack ? ids : ids.slice(0, max);
  return `<div class="wk-chips">${shown.map(id => `<a class="chip" href="?begreb=${encodeURIComponent(id)}" data-begreb="${esc(id)}">${chipName(id)}</a>`).join('')}`
    + (shown.length < ids.length ? `<button class="chip more" data-unfold="${esc(key)}">+ ${ids.length - shown.length}</button>` : '') + '</div>'; };
// a file that could not be fetched (offline, a hiccup) is said as such, with another try – never 'findes ikke'
const failed = (...ks) => ks.some(k => vd[k] && vd[k].state === 'error' && !vd[k].v);
// One designed message for every state (pro-plan 2.7): empty, offline, error, not found – one line and a way on
function stateBlock(kind, text, actions = []) {
  return `<div class="state ${kind}" role="status">${kind === 'offline' ? '<svg aria-hidden="true"><use href="#i-offline"/></svg>' : ''}<p>${text}</p>`
    + (actions.length ? `<div class="state-acts">${actions.map(([label, attr]) => `<button class="qbtn" ${attr}>${label}</button>`).join('')}</div>` : '') + '</div>';
}
const loadingBlock = text => `<div class="state loading" role="status"><p>${text}</p></div>`;
// with no network the same message as on the news pages (the same cause, the same words and icon), else a hiccup
const netDown = () => offline || navigator.onLine === false;
const retry = (what, ...ks) => stateBlock(netDown() ? 'offline' : 'error', netDown() ? `Ingen forbindelse. ${cap(what)} kommer, så snart telefonen er på nettet.`
  : `Kunne ikke hente ${what} lige nu.`, [['Prøv igen', `data-retry="${ks.join(',')}"`]]);
// Del · Kopiér · Gem for an answer or a page (the same buttons as a story's)
const knowActs = (kind, id) => { const on = isSaved(kind, id);
  return `<div class="acts know-acts"><button class="act" data-kshare="${kind}:${esc(id)}"><svg aria-hidden="true"><use href="#i-share"/></svg>Del</button>`
    + `<button class="act" data-kcopy="${kind}:${esc(id)}"><svg aria-hidden="true"><use href="#i-copy"/></svg>Kopiér</button>`
    + `<button class="act${on ? ' on' : ''}" data-ksave="${kind}:${esc(id)}" aria-pressed="${on}"><svg aria-hidden="true"><use href="#i-${on ? 'saved' : 'save'}"/></svg>${on ? 'Gemt' : 'Gem'}</button></div>`; };
// the first sentences of a text, at most n characters, ending at a sentence
function sentences(text, n) {
  const parts = String(text || '').split(/(?<=[.!?])\s+/), out = [];
  for (const p of parts) { if ((out.join(' ') + ' ' + p).trim().length > n && out.length) break; out.push(p); }
  return out.join(' ').trim();
}
// an answer as a WhatsApp text: its title, its label ('Hizb ut-Tahrirs svar · d/m/åååå' – the texts are plain, so the
// label says whose), the first sentences of 'Svaret kort', the original and the way back to it in Khabar
function svarText(a) {
  const mv = a.layer && V('mfull') && (V('mfull').answers || {})[a.nr], note = a.note || (mv && mv.note_da) || '', url = a.url || (mv && mv.url) || '';
  return [`*${a.title}*`, `Hizb ut-Tahrirs svar · ${dSlash(a.date)}`, note ? sentences(note, 400) : '', url ? `Originalen: ${url}` : '', `via khabar.nu/?svar=${a.nr}`].filter(Boolean).join('\n\n');
}
// the later answers that cite this one (the layer's own citations, read the other way)
let citedMemo = null;
function citedBy(nr) {
  const full = V('mfull');
  if (!full) return [];
  if (!citedMemo || citedMemo.full !== full) {
    const m = new Map();
    for (const [k, x] of Object.entries(full.answers || {})) for (const c of x.cites_nrs || []) { const s = String(c); if (!m.has(s)) m.set(s, []); m.get(s).push(k); }
    citedMemo = { full, m };
  }
  return (citedMemo.m.get(String(nr)) || []).map(k => answers().by.get(k)).filter(Boolean).sort((x, y) => y.date.localeCompare(x.date));
}
// today's stories whose answer line is this answer (answerFor read the other way), at most four
let newsMemo = null;
function newsFor(a) {
  if (!data) return [];
  const all = stories();
  if (!newsMemo || newsMemo.list !== all || newsMemo.gen !== ansGen || newsMemo.bix !== V('bix')) {   // each story's answer, once per news
    const by = new Map();
    for (const i of all) { if (hours(i) >= 24 || i.kind === 'kommentar') continue; const x = answerFor(i); if (x) { if (!by.has(x.nr)) by.set(x.nr, []); by.get(x.nr).push(i); } }
    newsMemo = { list: all, gen: ansGen, bix: V('bix'), by };
  }
  return (newsMemo.by.get(a.nr) || []).sort((x, y) => when(y) - when(x)).slice(0, 4);
}
// a compact news row for the knowledge pages: time, the headline as the app shows it with its names in bold, the dot
// and the outlet; a tap opens it in Live
const newsRow = i => `<li data-sec="${secOf(i)}"><button data-live="${esc(i.id)}" aria-label="${esc(rowLabel(i))}"><time aria-hidden="true">${clock(i.published || i.found)}</time>`
  + `<span dir="auto" aria-hidden="true">${bold(i.title, i.kw)}</span><em aria-hidden="true"><i></i>${esc(i.source)}</em></button></li>`;
// a time column crosses a day only under a day row ('I går'), as every timeline does
const newsRows = list => { let day = dayKey(new Date()), out = '';
  for (const i of list) { const k = dayKey(new Date(i.published || i.found)); if (k !== day) { day = k; out += `<li class="nl-day" role="heading" aria-level="3">${esc(dayName(i.published || i.found))}</li>`; } out += newsRow(i); }
  return out; };
const newsList = (list, title, id = '') => `<section class="block now k-news"${id ? ` id="${id}"` : ''}><h2 class="grp">${title}</h2><ul>${newsRows(list)}</ul></section>`;
function svarPage() {
  need('mix'); need('ans');
  const A = answers(), a = A.by.get(String(svarNr));
  if (!a) return waiting('mix') || waiting('ans') ? loadingBlock('Henter svaret …')
    : failed('mix') ? retry('svaret', 'mix', 'ans') : stateBlock('gone', 'Svaret findes ikke.', [['Alle svar', 'data-go="analyses"'], ['Søg', 'data-go="search" data-scope="svar"']]);
  markRead(a.nr);
  const full = a.layer ? need('mfull') : null, mv = full && (full.answers || {})[a.nr], bf = need('bfull');
  const texts = a.fresh ? need('txt') : null, area = areaOf(a), orig = a.orig ? cleanTitle(ourWords(a.orig)) : '', url = a.url || (mv && mv.url);
  // the byline is a meta line: it breaks between its items, never with a '·' left at a line's end; its first item is the
  // page's one label, whose and when ('Hizb ut-Tahrirs svar · d/m/åååå', kept on one line)
  let h = `<header class="rd-top"><span class="m rd-by"><span>Hizb ut-Tahrirs svar · ${esc(dSlash(a.date))}</span>${area ? `<span>${esc(area)}</span>` : ''}`
    + `${url ? `<span><a class="rd-src" href="${esc(url)}" target="_blank" rel="noopener">Originalen<svg aria-hidden="true"><use href="#i-open"/></svg></a></span>` : ''}</span>`
    + `<h1 class="ht">${esc(a.title)}</h1>${orig && a.da ? `<p class="rd-orig" dir="auto" lang="en">${esc(orig)}</p>` : ''}`
    // the question right under the title: the movement's words in its face, plain on the page (the byline is its label)
    + `${a.q ? `<p class="ht rd-q">${esc(a.q)}</p>` : ''}</header>${knowActs('a', a.nr)}`;
  // the answer itself in ONE ochre panel: 'Svaret kort', then what it reads, subject by subject, each under a hairline
  // (the byline above is the page's one label, so the panel carries none of its own)
  const note = a.note || (mv && mv.note_da) || '';
  const reads = readingsOf(a, full, note), rk = `svar|${a.nr}|reads`, allReads = unfolded.has(rk);
  const groups = new Map();
  for (const r of allReads ? reads : reads.slice(0, SHOW_READS)) { if (!groups.has(r.s)) groups.set(r.s, []); groups.get(r.s).push(r.text); }
  if (note || reads.length) h += `<section class="ht-box rd-ans">${note ? `<h2 class="ht-l">Svaret kort</h2><p class="ht">${rich(note, linkSession())}</p>` : ''}`
    + [...groups].map(([sj, texts]) => `<div class="rd-r"><div class="rd-s">${subjLinks(sj)}</div>${texts.map(t => `<p class="ht">${esc(t)}</p>`).join('')}</div>`).join('')
    + (reads.length > SHOW_READS ? `<button class="ht-more" data-unfold="${esc(rk)}">${allReads ? 'Vis færre' : `Alle ${reads.length} læsninger`}</button>` : '') + '</section>';
  if (!note && a.layer && waiting('mfull')) h += loadingBlock('Henter svaret …');
  else if (!note && a.layer && failed('mfull')) h += retry('svarets tekst', 'mfull');
  // a newer answer on the same subject governs: one quiet row to it under the panel
  const areaId = areaIdOf(a), newer = areaId && A.list.find(x => x.date > a.date && areaIdOf(x) === areaId);
  if (newer) h += `<button class="qrow rd-newer" data-svar="${esc(newer.nr)}"><span>Nyeste svar om ${esc(area)}: <b>${esc(newer.title)}</b> · ${esc(dSlash(newer.date))}</span>`
    + `<svg aria-hidden="true"><use href="#i-chev"/></svg></button>`;
  // the pages it uses, the central first (the subjects of its readings, its area), at most SHOW_SVAR_CHIPS before '+ n'
  const central = new Set([...reads.flatMap(r => String(r.s || '').split('--')), ...(a.issues || []).slice(0, 1), ...(a.states || []).slice(0, 1)].map(x => pageOf(x) || x));
  const pages = [...new Set([...(answerPages().get(a.nr) || []), ...(a.begreber || []).filter(id => ((V('bix') || {}).items || {})[id])])]
    .sort((x, y) => central.has(y) - central.has(x) || KIND_ORDER.indexOf(((V('bix') || {}).items[x] || {}).kind) - KIND_ORDER.indexOf(((V('bix') || {}).items[y] || {}).kind) || nameOf(x).localeCompare(nameOf(y), 'da'));
  if (pages.length) h += `<h2 class="grp rd-h">I leksikonet</h2>${chips(pages, `svar|${a.nr}|pages`, SHOW_SVAR_CHIPS, 0)}`;
  const cites = ((mv && mv.cites_nrs) || []).map(nr => A.by.get(String(nr))).filter(Boolean);
  if (cites.length) h += `<h2 class="grp rd-h">Svaret henviser til</h2><div class="rd-list">${cites.map(c => anRow(c)).join('')}</div>`;
  const later = citedBy(a.nr);
  if (later.length) h += `<h2 class="grp rd-h">Senere svar, der henviser hertil</h2><div class="rd-list">${later.slice(0, 6).map(c => anRow(c)).join('')}</div>`;
  const news = newsFor(a);
  if (news.length) h += newsList(news, 'I nyhederne nu');
  const held = texts && (texts.items || []).find(x => String(x.id) === a.nr && x.text);
  if (held) {
    // the text without its own heading lines (the title, 'Answer to Question')
    const same = x => fold(x).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
    let text = String(held.text).trim();
    for (let k = 0; k < 3 && text; k++) {
      const first = text.split(/\n\s*\n/)[0];
      if (first.length > 300 || !first.split('\n').every(l => !same(l) || same(l) === same(held.title || '') || same(l) === same(orig)
        || /^(?:updated )?(?:ameer s )?(?:answer to (?:a )?questions?|questions? and answers?|q a)$/.test(same(l)))) break;
      text = text.slice(text.indexOf(first) + first.length).trim();
    }
    // folded behind one quiet row (the byline's 'Originalen' is the way to the source)
    const tk = `svar|${a.nr}|text`, open = unfolded.has(tk);
    h += `<button class="qrow rd-more" data-unfold="${esc(tk)}" aria-expanded="${open}"><svg class="rd-ic" aria-hidden="true"><use href="#i-book"/></svg><span>${open ? 'Skjul hele svaret' : 'Læs hele svaret'}</span>`
      + `<svg class="rd-chev" aria-hidden="true"><use href="#i-chev"/></svg></button>`;
    if (open) h += `<section class="ht-box rd-text"><h2 class="ht-l">Svaret på engelsk</h2><div class="ht" lang="en">${paras(text)}</div></section>`;
  } else if (a.fresh && waiting('txt')) h += loadingBlock('Henter svarets tekst …');
  else if (enHas(a.nr)) {
    // the whole answer in English from the static layer (the owner, 17/10: "hele teksten … på engelsk"): fetched only
    // when the reader unfolds it; one the archive had only in Arabic is marked as translated
    const tk = `svar|${a.nr}|en`, open = unfolded.has(tk);
    if (!open && enTexts[a.nr] === false) delete enTexts[a.nr];   // folded after a failure: asked again when unfolded
    const en = open ? enText(a.nr) : null;
    h += `<button class="qrow rd-more" data-unfold="${esc(tk)}" aria-expanded="${open}"><svg class="rd-ic" aria-hidden="true"><use href="#i-book"/></svg><span>${open ? 'Skjul hele svaret' : 'Læs hele svaret (engelsk)'}</span>`
      + `<svg class="rd-chev" aria-hidden="true"><use href="#i-chev"/></svg></button>`;
    if (open && en) h += `<section class="ht-box rd-text"><h2 class="ht-l">Svaret på engelsk${en.translated ? ' · oversat fra arabisk' : ''}</h2><div class="ht" lang="en">${paras(en.text)}</div></section>`;
    else if (open && en === null) h += loadingBlock('Henter svarets tekst …');
    else if (open) h += stateBlock('error', 'Teksten kunne ikke hentes. Fold den sammen og åbn den igen for at prøve igen.', []);
  }
  return h;
}
// the whole English texts: which answers have one (viden/svar-en/index.json, asked for once) and each text as it is opened
let enIdx = null, enIdxAsked = false;
const enTexts = {};
function enHas(nr) {
  if (!enIdxAsked) {
    enIdxAsked = true;
    fetch(VIDEN + 'svar-en/index.json').then(r => r.ok ? r.json() : null).then(j => { enIdx = new Set((j && j.nrs) || []); if (enIdx.size) render(); }, () => {});
  }
  return !!enIdx && enIdx.has(String(nr));
}
function enText(nr) {
  const k = String(nr);
  if (k in enTexts) return enTexts[k];   // the text, false for a failure, or null while it comes
  enTexts[k] = null;
  fetch(VIDEN + `svar-en/${encodeURIComponent(k)}.json`).then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(j => { enTexts[k] = j && j.text ? j : false; render(); }, () => { enTexts[k] = false; render(); });
  return null;
}

// ---------------------------------------------------------------- a wiki page: one state, power, group, issue or concept
// Its name and kind with a contents row of what the page holds and its paired page (a state and its issue); Del ·
// Kopiér · Gem; the lead (the newest answer governs) and today's stories that name it; 'Gennem årene' (its readings,
// newest first, folded to five, each with the date of its answer as the way to it); for a state its relations; the
// answers about it; the pages related to it. Everything on it is the movement's, each block labelled whose and when
// once (the lead its answer's date; a row of the years and a relation each its own date); the page only gathers.
let begrebId = params.get('begreb') || '';
const SHOW_TL = 5, SHOW_ANS = 6, SHOW_NEWS = 3, STEP = 20;
// a long list unfolds twenty at a time ('Vis 20 mere'), then folds back – the USA's 313 answers are no 44,000 px page
const steps = {};
const stepOf = k => steps[k] || STEP;
const moreBtn = (k, n, open, first, cls) => !open ? `<button class="${cls}" data-unfold="${esc(k)}">${first}</button>`
  : stepOf(k) < n ? `<button class="${cls}" data-step="${esc(k)}">Vis ${Math.min(STEP, n - stepOf(k))} mere · ${n - stepOf(k)} tilbage</button>`
    + `<button class="${cls} fold" data-unfold="${esc(k)}">Vis færre</button>` : `<button class="${cls}" data-unfold="${esc(k)}">Vis færre</button>`;
function mentions(i, id) {
  const s = subj(id);
  if ((i.actors || []).some(x => x === id || x === s)) return true;
  return [i.title, i.title_da, i.summary_da].some(t => t && scan(t).some(f => f.id === id));
}
const pageTitle = x => (x.kind === 'sag' && /-sagen$/.test(x.name || '') ? `${x.name.replace(/-sagen$/, '')} – sagen` : x.name);
// a page as a WhatsApp text: its name, the lead's first two sentences under its label (the lead is plain Danish, so
// the label says whose and when: 'Hizb ut-Tahrirs svar · d/m/åååå'), the way back to it
function begrebText(id) {
  const ix = V('bix'), e = (V('bfull') || { items: {} }).items[id], x = e || (ix && ix.items[id]);
  if (!x) return '';
  const lead = e && e.lead_da ? e.lead_da.split(/(?<=[.!?])\s+/).slice(0, 2).join(' ') : '';
  const who = lead ? `Hizb ut-Tahrirs svar${e.lead_date ? ` · ${dSlash(e.lead_date)}` : ''}` : '';
  return [`*${pageTitle(x)}*`, who, lead, `via khabar.nu/?begreb=${encodeURIComponent(id)}`].filter(Boolean).join('\n\n');
}
function begrebPage() {
  const ix = need('bix'), bf = need('bfull'), id = begrebId;
  const head = ix && (ix.items || {})[id], e = bf && (bf.items || {})[id], x = e || head;
  if (!x) return waiting('bix') || waiting('bfull') ? loadingBlock('Henter …')
    : failed('bix', 'bfull') ? retry('siden', 'bix', 'bfull')
      : stateBlock('gone', 'Siden findes ikke.', [['Søg efter den', `data-search-q="${esc(String(id).replace(/-/g, ' '))}" data-scope="begreber"`], ['Leksikon A–Å', 'data-begreber']]);
  const A = answers();
  const n = e ? new Set([...(e.answers || []).map(String), ...A.list.filter(a => a.fresh && (a.begreber || []).includes(id)).map(a => a.nr)]).size : head.n_answers;
  // the paired page: a state and its issue ('Iran' and 'Iran – sagen')
  const pairId = /-sagen$/.test(id) ? id.replace(/-sagen$/, '') : id + '-sagen', pair = ix && ix.items[pairId];
  let h = `<header class="wk-top"><span class="thr-meta">${esc(KINDS[x.kind] || x.kind)} · ${n} svar</span><h1>${esc(pageTitle(x))}</h1>`;
  if (!e) return h + '</header>' + (waiting('bfull') ? loadingBlock('Henter siden …') : retry('siden', 'bfull'));
  // the editor's new answers (after the static layer) are on the page at once: their readings of it lead its timeline,
  // and they lead its answers – the next build of the wiki takes them in for good. The newest answer governs: a filed
  // reading of the page's own subject that is newer than the lead is the lead now, the built lead under it
  const s0 = subj(id), newer = A.list.filter(a => a.fresh && ((a.begreber || []).includes(id)
    || (a.readings || []).some(r => String(r.subject || '').split('--').includes(s0))));
  const govern = newer.filter(a => a.date > String(e.lead_date || '')).flatMap(a => (a.readings || [])
    .filter(r => r.text_da && r.subject === s0).map(r => ({ a, text: r.text_da })))[0];
  const tlAll0 = [...newer.flatMap(a => (a.readings || []).filter(r => r.text_da && String(r.subject || '').split('--').includes(s0))
    .map(r => ({ date: a.date, nr: a.nr, text_da: r.text_da }))), ...(e.timeline || [])];
  // 'Gennem årene' leaves out the row of the lead's own answer that says what the lead says (the count still has it)
  const leadSig = sig(e.lead_da || ''), tl = tlAll0.filter(r => !(String(r.nr) === String(e.lead_nr) && like(sig(r.text_da), leadSig) >= 0.6));
  const rel = e.relations || [], ans = [...new Set([...newer.map(a => a.nr), ...(e.answers || []).map(String)])].map(nr => A.by.get(nr)).filter(Boolean);
  const news = data ? stories().filter(i => hours(i) < 24 && mentions(i, id)).sort((p, q) => when(q) - when(p)) : [];
  // the contents row: what the page holds, each a jump to its part
  const toc = [[tlAll0.length, 'Forløb', 'wk-s-tl'], [rel.length, 'Forhold', 'wk-s-rel'], [ans.length, 'Svar', 'wk-s-ans'], [news.length, 'Nyheder', 'wk-s-news']].filter(t => t[0]);
  if (toc.length > 1) h += `<nav class="wk-toc" aria-label="Indhold">${toc.map(([c, l, to]) => `<button class="chip" data-toc="${to}">${l}<small>${c}</small></button>`).join('')}</nav>`;
  if (pair) h += `<button class="qrow pair" data-begreb="${esc(pairId)}"><span>${esc(pageTitle(pair))} · ${pair.n_answers} svar</span><svg aria-hidden="true"><use href="#i-chev"/></svg></button>`;
  h += `</header>${knowActs('b', id)}`;
  // the lead's answer to open (its date is the block's label)
  const goBtn = la => la ? `<button class="ht-go" data-svar="${esc(la.nr)}"><span class="ht">${esc(la.title)}</span>`
    + `<svg aria-hidden="true"><use href="#i-chev"/></svg></button>` : '';
  if (govern) h += `<section class="ht-box wk-lead">${htLabel(govern.a.date)}<p class="ht">${esc(govern.text)}</p>${goBtn(govern.a)}</section>`;
  if (e.lead_da) h += `<section class="ht-box wk-lead${govern ? ' wk-was' : ''}">${htLabel(e.lead_date, govern ? ' · før det nyeste svar' : '')}`
    + `<p class="ht">${esc(e.lead_da)}</p>${goBtn(e.lead_nr && A.by.get(String(e.lead_nr)))}</section>`;
  // today's news that names the page, right under the lead
  if (news.length) {
    const nk = `${id}|news`, newsAll = unfolded.has(nk);
    h += newsList(newsAll ? news : news.slice(0, SHOW_NEWS), 'I nyhederne nu', 'wk-s-news').replace('</section>', (news.length > SHOW_NEWS
      ? `<button class="qbtn" data-unfold="${esc(nk)}">${newsAll ? 'Vis færre' : `Alle ${news.length} fra det seneste døgn`}</button>` : '') + '</section>');
  }
  const tk = `${id}|tl`, tlAll = unfolded.has(tk);
  if (tl.length) {
    // the block's one label says whose; each row its answer's date as the way to it (the rows are of many answers,
    // newest first, under their years), the reading plain text under it
    let y = '', rows = '';
    for (const r of tl.slice(0, tlAll ? stepOf(tk) : SHOW_TL)) {
      const yr = String(r.date || '').slice(0, 4);
      if (yr !== y) { y = yr; rows += `<li class="wk-y" role="heading" aria-level="3">${esc(yr)}</li>`; }
      rows += `<li><button class="wk-r" data-svar="${esc(r.nr)}" aria-label="Svaret af ${esc(dSlash(r.date))}">${htDate(r.date)}<svg aria-hidden="true"><use href="#i-chev"/></svg></button>`
        + `<p class="ht">${esc(r.text_da)}</p></li>`;
    }
    h += `<h2 class="grp rd-h" id="wk-s-tl">Gennem årene</h2>`
      + (e.history_da ? `<section class="ht-box wk-hist">${htLabel('', ' · forløbet')}<p class="ht">${esc(e.history_da)}</p></section>` : '')
      + `<section class="ht-box wk-tl">${htLabel('')}<ol>${rows}</ol>`
      + (tl.length > SHOW_TL ? moreBtn(tk, tl.length, tlAll, `Hele forløbet · ${tlAll0.length}`, 'ht-more') : '') + '</section>';
  }
  const rkk = `${id}|rel`, relAll = unfolded.has(rkk);
  if (rel.length) h += `<h2 class="grp rd-h" id="wk-s-rel">Forhold</h2><section class="ht-box rd-reads">${htLabel('')}<ul>${(relAll ? rel : rel.slice(0, SHOW_TL)).map(r =>
    `<li><div class="rd-s">${subjLinks(r.with)}${r.date ? ` · ${htDate(r.date)}` : ''}</div><p class="ht">${esc(r.text_da)}</p></li>`).join('')}</ul>`
    + (rel.length > SHOW_TL ? `<button class="ht-more" data-unfold="${esc(rkk)}">${relAll ? 'Vis færre' : `Alle ${rel.length} forhold`}</button>` : '') + '</section>';
  const ak = `${id}|ans`, ansAll = unfolded.has(ak);
  if (ans.length) h += `<h2 class="grp rd-h" id="wk-s-ans">Svar om emnet</h2><div class="rd-list">${ans.slice(0, ansAll ? stepOf(ak) : SHOW_ANS).map(a => anRow(a)).join('')}</div>`
    + (ans.length > SHOW_ANS ? moreBtn(ak, ans.length, ansAll, `Alle ${ans.length} svar`, 'qbtn') : '');
  const related = (e.related || []).filter(r => ((ix || {}).items || {})[r]);
  if (related.length) h += `<h2 class="grp rd-h">Relaterede begreber</h2>${chips(related, `${id}|related`)}`;
  return h;
}
// the wiki's index: every page A–Å, with a filter by kind, the most used pages first as chips, a state's issue as a
// second line under it, and the letters in a strip that stays under the bar
// every page belongs to one group: the wiki's nine kinds in six (the states, the actors – powers, groups and
// organisations –, the places, the issues and processes, the concepts, the agreements)
const AZ_KINDS = [['', 'Alle', []], ['stat', 'Stater', ['stat']], ['aktor', 'Aktører', ['magt', 'gruppe', 'organisation']], ['sted', 'Steder', ['sted']],
  ['sag', 'Sager', ['sag', 'proces']], ['begreb', 'Begreber', ['begreb']], ['aftale', 'Aftaler', ['aftale']]];
let azKind = '';
function begreberPage() {
  const ix = need('bix');
  if (!ix) return waiting('bix') ? loadingBlock('Henter …') : retry('begreberne', 'bix');
  const all = Object.entries(ix.items || {}).map(([id, e]) => ({ id, ...e }));
  const kinds = new Set((AZ_KINDS.find(k => k[0] === azKind) || AZ_KINDS[0])[2]);
  // an issue sits under its state ('Iran' – '– sagen · 31 svar'), unless the filter shows the issues themselves
  const nested = new Set(azKind ? [] : all.filter(e => e.kind === 'sag' && ix.items[e.id.replace(/-sagen$/, '')] && /-sagen$/.test(e.id)).map(e => e.id));
  const items = all.filter(e => !nested.has(e.id) && (!azKind || kinds.has(e.kind))).sort((a, b) => a.name.localeCompare(b.name, 'da'));
  let h = `<header class="ud-top"><span><b>Leksikon A–Å</b><small>${all.length} opslag, samlet alene fra Hizb ut-Tahrirs svar</small></span></header>`;
  h += `<nav class="an-chips az-kinds" aria-label="Slags">${AZ_KINDS.map(([v, l, ks]) => { const n = v ? all.filter(e => ks.includes(e.kind)).length : 0;
    return `<button class="chip${azKind === v ? ' on' : ''}" data-az-kind="${v}" aria-pressed="${azKind === v}">${l}${n ? `<small>${n}</small>` : ''}</button>`; }).join('')}</nav>`;
  if (!azKind) {
    const top = all.filter(e => !nested.has(e.id)).sort((a, b) => (b.n_answers || 0) - (a.n_answers || 0)).slice(0, 8).map(e => e.id);
    h += `<h2 class="grp">Mest brugt</h2>${chips(top, 'az|top', 8).replace('class="wk-chips"', 'class="wk-chips ht-chips"')}`;
  }
  const letters = [...new Set(items.map(e => e.name.charAt(0).toLocaleUpperCase('da')))];
  // the letters as the iPhone's contacts have them (the owner, 18/10): all of them, still, in a thin column at the
  // right; a finger held on it and slid runs through the letters, a large letter in the middle says where (azScrub)
  h += `<nav class="az-idx" aria-label="Gå til bogstav">${letters.map(l => `<button data-az-l="${esc(l)}" aria-label="${esc(l)}">${esc(l)}</button>`).join('')}</nav>`;
  let L = '';
  for (const e of items) {
    const l = e.name.charAt(0).toLocaleUpperCase('da');
    // the jump's mark sits before its band: a band that sticks under the bar reports where it sticks, not where it lies
    if (l !== L) { L = l; h += `<i class="az-at" id="az-${esc(l)}" aria-hidden="true"></i><h2 class="grp az">${esc(l)}</h2>`; }
    const sub = nested.has(e.id + '-sagen') ? ix.items[e.id + '-sagen'] : null;
    h += `<div class="az-item"><button class="az-row" data-begreb="${esc(e.id)}"><b>${esc(pageTitle(e))}</b><small>${esc(KINDS[e.kind] || e.kind)} · ${e.n_answers} svar</small></button>`
      + (sub ? `<button class="az-sub" data-begreb="${esc(e.id + '-sagen')}">– sagen · ${sub.n_answers} svar</button>` : '') + '</div>';
  }
  return h;
}

// ---------------------------------------------------------------- Gemt: what the reader saved (pro-plan 5.1)
// A side page: the saved stories from their snapshots (they open offline and after they left Live; one still in Live
// opens there), the saved answers and pages from the library on the phone. Newest first; nothing leaves the phone.
const SAVE_MAX = 200;
function snapshot(i) {
  const ed = sumOf(i);
  return { k: 's', id: i.id, at: Date.now(), title: display(i).title,   // the headline the reader saw, in Danish
    source: i.source, time: i.published || i.found, link: i.link, sec: secOf(i),
    summary: (ed && ed.text) || i.summary || '', also: (i.also || []).slice(0, 5).map(a => ({ source: a.source, title: a.title_tr || a.title, link: a.link })) };
}
function toggleSave(k, id, i = null) {
  id = String(id);
  const on = isSaved(k, id);
  saved = on ? saved.filter(x => !(x.k === k && x.id === id)) : [k === 's' ? snapshot(i) : { k, id, at: Date.now() }, ...saved].slice(0, SAVE_MAX);
  idle(storeSaved);   // nothing is sent anywhere: a save stays on the phone
  if (!on && k !== 's') prefetchLibrary();
  paintSaved();
  if (on) toast('Fjernet fra Gemt'); else toast('Gemt på telefonen', true, tab === 'gemt' ? null : ['Se Gemt', () => openSide('gemt')]);
  return !on;
}
// the bar's bookmark: filled once something is saved; it opens Gemt from every page
function paintSaved() {
  const b = $('openSaved');
  if (!b) return;
  b.querySelector('use').setAttribute('href', saved.length ? '#i-saved' : '#i-save');
  b.setAttribute('aria-label', saved.length ? `Gemt, ${saved.length}` : 'Gemt');
}
// a saved story as a quiet row like Live's: the headline, two lines of its summary, the outlet and the time; a tap opens
// it in Live while it is there, else the outlet's article; the filled bookmark at the right takes it out of Gemt
const svBtn = (k, id, title) => `<button class="an-save on" data-unsave="${k}:${esc(id)}" aria-pressed="true" aria-label="Fjern fra Gemt: ${esc(title)}"><svg aria-hidden="true"><use href="#i-saved"/></svg></button>`;
const savedStory = x => {
  const live = findStory(x.id), title = live ? display(live).title : quoteIsrael(x.title);   // the headline Live shows
  const open = live ? `href="?item=${encodeURIComponent(live.id)}" data-live="${esc(live.id)}"` : `href="${esc(x.link)}" target="_blank" rel="noopener"`;
  const meta = [x.source, stamp(x.time), live ? '' : 'ikke længere i Live'].filter(Boolean).map(esc).join(' · ');
  return `<div class="an-item sv-item" data-sec="${esc(x.sec || '')}" data-saved="${esc(x.id)}"><a class="an-row sv-s" ${open}><b>${esc(title)}</b>`
    + (x.summary ? `<span class="sv-sum">${esc(x.summary)}</span>` : '') + `<span>${meta}</span></a>${svBtn('s', x.id, title)}</div>`;
};
// Flyt til en anden telefon (the owner, 18/10: the saves go along to a new phone – no account, no id): the list goes as a
// link the reader sends to themself and opens on the other phone (or in the home screen's app after Safari: on an
// iPhone the two keep apart). The saves ride in the link's #fragment, which a browser never sends to a server, packed
// with deflate where the browser has it ('z'), else plain ('j'); a story keeps its headline, outlet, time, link and
// section – its summary stays behind, so the link stays short. Opened, the saves are added to the phone's own.
const b64u = bytes => { let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); };
const unb64u = t => Uint8Array.from(atob(t.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
const viaStream = async (bytes, S) => new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new S('deflate-raw'))).arrayBuffer());
async function moveLink() {
  const list = saved.map(x => x.k === 's' ? { k: 's', id: x.id, at: x.at, title: x.title, source: x.source, time: x.time, link: x.link, sec: x.sec } : { k: x.k, id: x.id, at: x.at });
  const raw = new TextEncoder().encode(JSON.stringify(list));
  let tag = 'j', bytes = raw;
  if (window.CompressionStream) try { bytes = await viaStream(raw, CompressionStream); tag = 'z'; } catch { bytes = raw; tag = 'j'; }
  return `${location.origin}${location.pathname}?gemt=1#flyt=${tag}${b64u(bytes)}`;
}
// made while Gemt is drawn, so a tap shares at once (a phone lets a share sheet open only straight from the tap)
let moveUrl = '', moveKey = '';
function readyMove() {
  const k = saved.map(x => x.k + ':' + x.id).join('|');
  if (k === moveKey) return;
  moveKey = k; moveUrl = '';
  moveLink().then(u => { if (moveKey === k) moveUrl = u; }).catch(() => {});
}
async function takeMove() {
  const m = /^#flyt=([jz])([A-Za-z0-9_-]+)$/.exec(location.hash);
  if (!m) return;
  history.replaceState(history.state, '', location.pathname + location.search);   // the saves leave the address at once
  try {
    let bytes = unb64u(m[2]);
    if (m[1] === 'z') bytes = await viaStream(bytes, DecompressionStream);
    moveGot = JSON.parse(new TextDecoder().decode(bytes)).filter(okSave).map(x => ({ ...x, id: String(x.id) }));
  } catch { toast('Linket kunne ikke læses', false); return; }
  // the owner, 18/10: 'tilføj til eksisterende' or 'erstat eksisterende' when the link is opened – it may come from
  // oneself or from someone else; a phone with nothing saved takes them at once
  if (!saved.length) { useMove('add'); return; }
  const n = moveGot.length;
  showOwnerSheet(`${n} ${n === 1 ? 'gemt' : 'gemte'} i linket`, `<button class="wide primary" data-a="flyt:add">Tilføj til mine gemte</button>`
    + `<button class="wide" data-a="flyt:replace">Erstat mine ${saved.length} gemte</button>`, null, 'Gemte fra et link');
}
let moveGot = null;
function useMove(how) {
  const got = moveGot || [];
  moveGot = null;
  const fresh = how === 'replace' ? got : got.filter(x => !isSaved(x.k, x.id));
  saved = (how === 'replace' ? [...got] : [...saved, ...fresh]).sort((a, b) => (b.at || 0) - (a.at || 0)).slice(0, SAVE_MAX);
  storeSaved(); paintSaved(); render();
  toast(how === 'replace' ? `Dine gemte er nu linkets ${saved.length}` : fresh.length ? `${fresh.length} lagt ind i dine gemte` : 'Alt i linket var allerede gemt');
}
function gemtPage() {
  const s = saved.filter(x => x.k === 's'), an = saved.filter(x => x.k === 'a'), bg = saved.filter(x => x.k === 'b');
  // the bar says 'Gemt'; the page only how much, on this phone. The answers first, then the news, then the wiki's pages
  // (the owner, 18/10: 'analyser bør også være over nyheder'); one bookmark on every row, the one that takes it out
  if (!saved.length) return stateBlock('empty', 'Intet gemt endnu.', [['Til Live', 'data-go="latest"']]);
  let h = `<p class="an-n sv-n">${saved.length} gemt på denne telefon</p>`;
  if (an.length) {
    need('mix'); need('ans');
    const A = answers(), rows = an.map(x => A.by.get(x.id)).filter(Boolean);
    h += `<h2 class="grp">Analyser · ${an.length}</h2>` + (rows.length ? `<div class="rd-list">${rows.map(a => anRow(a)).join('')}</div>`
      : waiting('mix') ? loadingBlock('Henter svarene …') : retry('svarene', 'mix', 'ans'));
  }
  if (s.length) h += `<h2 class="grp">Nyheder · ${s.length}</h2><div class="rd-list">${s.map(savedStory).join('')}</div>`;
  if (bg.length) {
    need('bix');
    const ix = V('bix');
    h += `<h2 class="grp">Leksikon · ${bg.length}</h2>` + (ix ? `<div class="rd-list">${bg.filter(x => ix.items[x.id]).map(x => { const e = ix.items[x.id];
      return `<div class="an-item"><a class="an-row" href="?begreb=${encodeURIComponent(x.id)}" data-begreb="${esc(x.id)}"><b>${esc(pageTitle(e))}</b><span>${esc(KINDS[e.kind] || e.kind)} · ${e.n_answers} svar</span></a>${svBtn('b', x.id, pageTitle(e))}</div>`; }).join('')}</div>`
      : waiting('bix') ? loadingBlock('Henter …') : retry('begreberne', 'bix'));
  }
  readyMove();
  // the link shared, or copied to paste anywhere (the owner, 18/10: 'burde også give et link man kan kopiere')
  return h + `<div class="sv-move"><h2 class="sv-move-h">Del eller flyt dine gemte</h2>`
    + `<p class="sv-move-t">Send linket til dig selv på en ny telefon eller til en anden. Den, der åbner det, kan tilføje dem til sine gemte eller erstatte dem. De ligger kun i linket.</p>`
    + `<div class="acts know-acts"><button class="act" data-move="share"><svg aria-hidden="true"><use href="#i-share"/></svg>Del</button>`
    + `<button class="act" data-move="copy"><svg aria-hidden="true"><use href="#i-copy"/></svg>Kopiér link</button></div></div>`;
}
const isStale = () => data && data.updated && (Date.now() - new Date(data.updated)) / 60000 > 60;
// the bar's status: the time of the news with a small refresh mark (a tap reloads); 'offline · 10.53' while the phone's
// copy shows; 'ingen forbindelse' when there is none. Old news: only the box on the page says it, the bar stays quiet.
function renderHeader(busyText = '') {
  $('dot').classList.toggle('stale', !!isStale() || offline);   // grey while the news are old or the phone is offline: the red dot is the live signal
  // offline: the offline mark before the copy's time ('⊘ 10.53'), or before 'offline' with no copy – short, so the bar's
  // title and its three buttons keep their room at every text size; the words are in the label a screen reader reads
  const st = $('status'), text = busyText || (!data ? (offline ? 'offline' : 'henter …') : clock(data.updated));
  const icon = busyText ? '' : offline ? 'offline' : data ? 'refresh' : '';
  if (st.dataset.t !== text + icon) { st.dataset.t = text + icon; st.innerHTML = `${icon ? `<svg aria-hidden="true"><use href="#i-${icon}"/></svg>` : ''}<span>${esc(text)}</span>`; }
  st.classList.toggle('off', offline);
  st.setAttribute('aria-label', (data ? `${offline ? 'Ingen forbindelse. ' : ''}Nyhederne er fra ${fromWhen(data.updated)}` : offline ? 'Ingen forbindelse' : text) + ' – tryk for at opdatere');
}
// the movement's pages (Analyser, an answer, the wiki) need no news: they are drawn before the news have come, and
// say nothing about the news being old
const OWN = { analyses: analysesPage, svar: svarPage, begreb: begrebPage, begreber: begreberPage, gemt: gemtPage, kalender: kalenderPage };
// the news pages before any news is on the phone: skeleton rows for at most four seconds, then a message and a way on
const bootAt = Date.now();
function noNews() {
  if (!offline && Date.now() - bootAt < 4000) return '<div class="skel"></div>'.repeat(8);
  const off = offline && navigator.onLine === false;
  return stateBlock(off ? 'offline' : 'error', off ? 'Ingen forbindelse. Nyhederne kommer, så snart telefonen er på nettet.'
    : offline ? 'Kunne ikke hente nyhederne lige nu.' : 'Nyhederne er længe om at komme.', [['Prøv igen', 'data-reload']]);
}
function pageHtml(t, all, opts = {}) {
  if (OWN[t]) return OWN[t]();
  // the same words as everywhere else for the same cause, with the day when the copy is from another day
  const note = offline ? `<p class="notice off"><svg aria-hidden="true"><use href="#i-offline"/></svg><span>Ingen forbindelse – viser nyhederne fra ${fromWhen(data.updated)}.</span></p>`
    : isStale() ? `<p class="notice"><svg aria-hidden="true"><use href="#i-clock"/></svg><span>Khabar har ikke hentet nyt siden ${fromWhen(data.updated)}. Listen kan være forældet.</span></p>` : '';
  return note + (t === 'home' ? home(all, opts) : t === 'search' ? searchPage(all) : t === 'latest' ? latestPage(all, opts) : threadsPage());
}
// what the pages show changes with the data and the user's choices; each page notes the state it was drawn from
let ver = 0;
// Analyser and the wiki's index show no news: drawn again only when what they show has changed (not at every reload)
const vstate = k => (vd[k] || {}).state || '';
const SIG = { analyses: () => [answers() && ansGen, !!V('bix'), anQuery, anArea, saved.length, unfolded.has('an|areas'), ansRead.size, vstate('bfull'), vstate('mix'), vstate('ans')].join('|'),
  begreber: () => [!!V('bix'), vstate('bix'), azKind].join('|'),
  // the calendar: its files, the reader's choices, the day – and, with an event open, the news that name it
  kalender: () => [calGen, vstate('cal'), vstate('kal'), calF, calImp, calPast, [...calOpen].join(','), calFocus, calGone, dkYmd(new Date()),
    calOpen.size ? `${titlesVer}|${data && data.updated}` : ''].join('|') };
// The pages are patched, not rebuilt: the new page is laid out as a fragment and set against what stands. A row that
// has not changed keeps its very elements – its picture, its place, nothing to lay out again –, a changed one gets only
// its changed words and attributes, a new one is put in. A reload that brings two stories touches two rows.
function morph(from, to, added) {
  const keyed = new Map();
  for (let n = from.firstChild; n; n = n.nextSibling) if (n.nodeType === 1 && n.id) keyed.set(n.id, n);
  let at = from.firstChild;
  for (let n = to.firstChild; n;) {
    const next = n.nextSibling;
    let m = null;
    if (n.nodeType === 1 && n.id) { m = keyed.get(n.id) || null; if (m && m.tagName !== n.tagName) m = null; if (m) keyed.delete(n.id); }
    else if (at && at.nodeType === n.nodeType && !(at.nodeType === 1 && (at.id || at.tagName !== n.tagName))) m = at;
    if (!m) { from.insertBefore(n, at); if (n.nodeType === 1) added.push(n); }
    else {
      if (m === at) at = at.nextSibling; else from.insertBefore(m, at);
      if (m.nodeType !== 1) { if (m.nodeValue !== n.nodeValue) m.nodeValue = n.nodeValue; }
      else if (!m.isEqualNode(n)) {
        for (const a of [...m.attributes]) if (!n.hasAttribute(a.name)) m.removeAttribute(a.name);
        for (const a of n.attributes) if (m.getAttribute(a.name) !== a.value) m.setAttribute(a.name, a.value);
        if (m.tagName !== 'INPUT') morph(m, n, added);   // a field keeps what is typed in it
      }
    }
    n = next;
  }
  while (at) { const x = at.nextSibling; from.removeChild(at); at = x; }
}
// the reader's place: the first row (or block with a name) below the top bar stays where it stood when rows come or go
// above it – the page moves only by the reader's hand
function placeOf(pg) {
  const edge = $('bar').getBoundingClientRect().bottom;
  for (const el of pg.querySelectorAll('[id]')) { const top = el.getBoundingClientRect().top; if (top >= edge) return { id: el.id, top }; }
  return null;
}
function restorePlace(pg, a) {
  const el = a && pg.querySelector('#' + CSS.escape(a.id));
  if (!el) return;
  const d = el.getBoundingClientRect().top - a.top;
  if (Math.abs(d) >= 0.5) pg.scrollTop += d;
}
function draw(t, opts = {}) {
  const pg = pageEl(t);
  if (!pg) return;
  pg.dataset.ver = ver;
  if (t === dockTab) paintOpts(t);   // the page's options in the dock above the tabs
  if (t === 'okonomi') { okPage(pg); return; }   // the economy page in its frame, made when first shown
  const sig = SIG[t] ? SIG[t]() : '';
  if (sig && pg.dataset.sig === sig) return;
  pg.dataset.sig = sig;
  // Analyser keeps its search field (and the keyboard) while its list is drawn again
  const keep = t === 'analyses' && pg.querySelector('#anQ') && pg.querySelector('.an-list');
  if (keep) {
    const inp = pg.querySelector('#anQ');
    if (inp && document.activeElement !== inp && !anT && inp.value !== anQuery) inp.value = anQuery;   // a search brought from elsewhere
    keep.innerHTML = analysesList();
    const c = anCounts(), top = pg.querySelector('.an-top small');
    if (top) top.textContent = c.n ? `${c.n} svar${c.span ? ' · ' + c.span : ''}` : '';
    return;
  }
  const html = !data && !OWN[t] ? noNews() : `<div>${pageHtml(t, data ? stories() : [], opts)}</div>`;
  const place = opts.keep && t === tab && pg.scrollTop > 0 ? placeOf(pg) : null, added = [];
  if (pg.firstElementChild && !pg.firstElementChild.classList.contains('skel') && !pg.firstElementChild.classList.contains('state')) {
    const tpl = document.createElement('template');
    tpl.innerHTML = html;
    morph(pg, tpl.content, added);
  } else pg.innerHTML = html;
  if (place) restorePlace(pg, place);
  // a tab chosen or a side page opened fades in (opacity only); a row that is really new rises in once and glows
  if (opts.view && !reduceMotion && pg.firstElementChild) pg.firstElementChild.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease-out' });
  if (opts.fresh && shownIds.size && !reduceMotion) {
    for (const el of added) for (const s of el.matches('article.story') ? [el] : el.querySelectorAll('article.story')) {
      if (shownIds.has(s.dataset.id)) continue;
      s.classList.add('fresh');
      const end = e => { if (e.animationName === 'glow') { s.classList.remove('fresh'); s.removeEventListener('animationend', end); } };
      s.addEventListener('animationend', end);
    }
  }
  pictures(pg);
  edgesIn(pg);
  if (t === 'analyses') watchStrip(pg);
  if (t === 'begreber') azWatch(pg);
  // a calendar event a link or the front page named: brought just below the bar once drawn (the tab in view)
  // (and again while the files and the news that follow redraw it for two seconds, until the reader's finger takes over)
  if (t === 'kalender' && t === tab) calAimAt(pg);
  if (t === 'threads' && pendingThr) { const card = pg.querySelector('#' + CSS.escape('thr-' + pendingThr)); if (card) { pendingThr = ''; requestAnimationFrame(() => scrollToEl(card, 12)); } }
}
// Analyser's strip stays under the bar; its year bands stick under the strip (its height measured when it changes)
let stripWatch = null;
function watchStrip(pg) {
  const el = pg.querySelector('#anStrip');
  if (!el || (stripWatch && stripWatch.el === el)) return;
  if (stripWatch) stripWatch.ro.disconnect();
  const ro = new ResizeObserver(() => pg.style.setProperty('--strip', el.offsetHeight + 'px'));
  ro.observe(el);
  stripWatch = { el, ro };
}
// the pages beside the one in view are drawn again in a quiet moment (never while a finger is on the screen, the pages
// move or the intro writes), so a swipe always finds its neighbour ready; a page never drawn gets drawn too
let drawT = 0;
const introOn = () => document.documentElement.classList.contains('intro-on');
const handBusy = () => touching || paging || scrubbing || pull || performance.now() - lastScroll < 300;
function drawSoon() {
  clearTimeout(drawT);
  drawT = setTimeout(function step() {
    if (ASIDE.has(tab)) return;
    if (handBusy() || introOn()) { drawT = setTimeout(step, 250); return; }
    const i = SWIPE_TABS.indexOf(tab);
    // the page in view first (a swipe may have brought one drawn before the last change), then its neighbours
    const t = [tab, SWIPE_TABS[i - 1], SWIPE_TABS[i + 1]].find(x => x && +pageEl(x).dataset.ver !== ver) || SWIPE_TABS.find(x => !pageEl(x).dataset.ver);
    if (!t) return;
    idle(() => {
      if (handBusy() || ASIDE.has(tab)) { drawT = setTimeout(step, 250); return; }
      if (+pageEl(t).dataset.ver !== ver) draw(t, { keep: t === tab });
      drawT = setTimeout(step, 40);
    });
  }, 120);
}
// something only some pages show has changed: draw the page in view if it is one of them, the rest in a quiet moment
function staleOn(tabs) { if (tabs.includes(tab)) renderSoon({ keep: true }); else { ver++; drawSoon(); } }
// a file of the wiki or the answers came: only the pages that show it are drawn again – the one in view at once, in
// place (an answer line or a link that arrives above what one reads moves nothing)
let redrawT = 0;
const redrawFor = new Set();
function redrawPages(tabs) {
  for (const t of tabs) { const p = pageEl(t); if (p && p.dataset.ver) p.dataset.ver = -1; redrawFor.add(t); }
  clearTimeout(redrawT);
  (function now() {   // never under a finger or a scroll that still moves
    if (handBusy()) { redrawT = setTimeout(now, 250); return; }
    if (redrawFor.has(tab) && (data || OWN[tab] || tab === 'okonomi')) draw(tab, { keep: true });
    redrawFor.clear();
    drawSoon();
  })();
}
// pictures: the first ones on a page load at once (on a page beside the one in view too, so a swipe shows them), the
// rest as the page scrolls near them – the browser's own lazy loading does not look ahead inside a page that scrolls
// by itself
const picWatch = new Map();
function pictures(pg) {
  let io = picWatch.get(pg);
  if (!io) {
    io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { nearPics.add(e.target.getAttribute('src')); e.target.removeAttribute('loading'); io.unobserve(e.target); } }),
      { root: pg, rootMargin: '1200px 0px' });
    picWatch.set(pg, io);
  }
  io.disconnect();
  pg.querySelectorAll('img[loading="lazy"]').forEach(img => io.observe(img));
}
function render(opts = {}) {
  renderHeader();
  ver++;
  draw(tab, opts);
  drawSoon();
  if (!data) return;
  const all = stories();
  // new stories that arrived while the user was scrolled down: offer a pill instead of jumping
  const fresh = opts.fresh && shownIds.size ? all.filter(i => !shownIds.has(i.id)).length : 0;
  shownIds = new Set(all.map(i => i.id));
  if (fresh && cur().scrollTop > 240 && (tab === 'home' || tab === 'latest')) {   // the news pages only
    $('freshPill').querySelector('span').textContent = `${fresh} ${fresh === 1 ? 'ny historie' : 'nye historier'}`;
    $('freshPill').hidden = false;
  }
  if (fresh) say(`${fresh} ${fresh === 1 ? 'ny historie' : 'nye historier'}`);   // read aloud, never shown
  renderDots(all);
  hintSeen();
  if (focusId) openFocus(all);
  if (goOverview && data) {   // a notification about the recap: open it, on the Udvikling page
    goOverview = false;
    if (tab !== 'threads') openSide('threads'); else { render(); cur().scrollTop = 0; }
  }
}
// a dot on a tab with something the user has not seen yet: a new update of the overview, or an important story
// (a tab's dot goes once the tab has been looked at)
function renderDots(all) {
  const since = name => Math.max(lastSeen, seenTab[name] || 0);
  document.querySelector('.tabs [data-tab="home"]').classList.toggle('has-new',
    tab !== 'home' && !!(digest && digest.created && lastSeen && new Date(digest.created).getTime() > since('home')));
  document.querySelector('.tabs [data-tab="latest"]').classList.toggle('has-new', tab !== 'latest' &&
    all.some(i => firstFound(i) && new Date(firstFound(i)).getTime() > Math.max(since('latest'), Date.now() - 6 * 3600e3)));
  // Analyser: a new answer of the amir's the phone has not seen there yet
  if (tab === 'analyses') markAnswersSeen();
  document.querySelector('.tabs [data-tab="analyses"]').classList.toggle('has-new', tab !== 'analyses' && unseenAnswer());
}
// a place on the page in view, just below the top bar
function scrollToEl(el, gap = 8) {
  const p = cur();
  if (p && el) p.scrollTo(0, el.getBoundingClientRect().top - p.getBoundingClientRect().top + p.scrollTop - $('bar').offsetHeight - gap);
}
// a story in a list with day bands: its headline just below the band that stays under the top bar
const storyGap = () => { const d = cur() && cur().querySelector('.day'); return 8 + (d ? d.offsetHeight : 0); };
// a notification opens the app on its story: find it, open it, show it
// a quiet word for a screen reader (the new stories a reload brought), in a live region nobody sees
function say(text) { const el = $('srStatus'); if (el) { el.textContent = ''; setTimeout(() => { el.textContent = text; }, 60); } }
// a story a link or a notification names that has left Live since: said so, with a way to find it
let focusMissing = '', netLoaded = false;
function openFocus(all) {
  // the story may since have joined another outlet's card: then open that card
  const i = findStory(focusId);
  if (!i) {
    if (netLoaded) { focusMissing = focusId; focusId = null; if (tab !== 'latest') setTab('latest', { top: true }); else draw('latest'); }
    return;
  }
  focusId = null;
  if (!pg$('s-' + i.id)) { openInLive(i.id); return; }   // not on the page in view: in Live, opened
  expanded.add(i.id);
  const el = pg$('s-' + i.id);
  if (!el.classList.contains('open')) openRow(el, asShown(el) || i);
  setTimeout(() => {   // jump straight there, headline just below the top bar
    scrollToEl(pg$('s-' + i.id), storyGap());
  }, 150);
}
// a row opens: its summary and actions, and its headline's links to the wiki
const rowDetail = (el, i) => detail(i, { noAns: el.classList.contains('hero'), ...detailOpts(i, { home: !!el.dataset.home }) });
function openRow(el, i) {
  el.querySelector('.x-in').innerHTML = rowDetail(el, i);
  const h = el.querySelector('.h'), tx = el.querySelector('.tx');
  if (h) h.innerHTML = headHtml(i, true);
  if (tx) tx.removeAttribute('aria-hidden');   // opened: its headline's links to the wiki are read too
  const tg = el.querySelector('[data-toggle]');
  if (tg) tg.setAttribute('aria-expanded', true);
  el.classList.add('open');   // laid out at once; its contents fade in (style.css)
}

// ---------------------------------------------------------------- open a story or a topic in place
// The page moves only by the app's own hand: the browser's scroll anchoring is off on the pages (iPhone now anchors
// too, which doubled the app's own correction – the page leapt up, then crawled back down), and its smooth scrolling
// is not used here (on iPhone it can crawl). A short motion of our own instead, which a finger on the page stops.
let moveT = 0;
function movePage(dy, ms = 240) {
  const p = cur(), from = p.scrollTop, t0 = performance.now();
  cancelAnimationFrame(moveT);
  if (reduceMotion || !dy) { p.scrollTop = from + dy; return; }
  const step = now => {
    if (touching) return;
    const k = Math.min(1, (now - t0) / ms);
    p.scrollTop = from + dy * (1 - Math.pow(1 - k, 3));
    if (k < 1) moveT = requestAnimationFrame(step);
  };
  moveT = requestAnimationFrame(step);
}
// a story stays where it was tapped while the ones above it fold (at once; a frame or two more for the rows that only
// now come into sight and are laid out)
function pin(el, top, ms = 140) {
  const p = cur(), t0 = performance.now();
  cancelAnimationFrame(moveT);
  const step = now => {
    if (touching || !el.isConnected) return;
    const d = el.getBoundingClientRect().top - top;
    if (Math.abs(d) >= 0.5) p.scrollTop += d;
    if (now - t0 < ms) moveT = requestAnimationFrame(step);
  };
  step(t0);
}
// a list folded back: its button stays under the finger while the page is drawn again (the rows above it shrink away)
function keepPlace(btn, redraw) {
  const key = btn.dataset.unfold, top = btn.getBoundingClientRect().top;
  redraw();
  const p = cur(), same = p && [...p.querySelectorAll('[data-unfold]')].find(b => b.dataset.unfold === key);
  if (same) p.scrollTop += same.getBoundingClientRect().top - top;
}
// an opened story that reaches past the tabs comes up just enough – never with its headline under the top bar
function keepInView(el) {
  setTimeout(() => {
    if (touching || !el.isConnected) return;
    const r = el.getBoundingClientRect(), limit = innerHeight - $('dock').offsetHeight - 12;
    if (r.bottom > limit) movePage(Math.max(0, Math.min(r.bottom - limit, r.top - $('bar').offsetHeight - 8)));
  }, 90);
}
// one thing open at a time: opening a story folds the others back; those above it close at once and the page moves
// with them, so the story one tapped stays where it is
function foldOthers(keep) {
  const others = [...cur().querySelectorAll('.story.open')].filter(o => o !== keep && !o.contains(keep) && !keep.contains(o));
  if (!others.length) return;
  const before = keep.getBoundingClientRect().top;
  for (const o of others) {
    o.classList.remove('open'); expanded.delete(o.dataset.id);
    const tg = o.querySelector('[data-toggle]'); if (tg) tg.setAttribute('aria-expanded', false);
  }
  pin(keep, before);
}
// every story's root is Live's chronological list: references elsewhere open the story there, opened and in view
function openInLive(id) {
  const i = findStory(id);
  if (!i) return;
  if (!latestAll && hours(i) >= 24) latestAll = true;
  if (liveImp && weightOf(i) < 2) liveImp = false;   // a story of low weight opened from elsewhere: Live shows all again
  expanded.clear(); expanded.add(i.id);
  ver++;   // the story opened is a change: Live drawn ahead of time is drawn again, with it open
  if (tab === 'latest') render(); else setTab('latest', { top: true });
  scrollToEl(pg$('s-' + i.id), storyGap());   // the page is laid out by now: straight there, headline just below the day band
}
function toggle(el) {
  const id = el.dataset.id, open = !el.classList.contains('open'), i = asShown(el);
  if (open) foldOthers(el);
  if (open && i) {
    if (visit) visit.opened++;
    expanded.add(id);
    openRow(el, i);
    keepInView(el);
  } else {
    el.classList.remove('open'); expanded.delete(id);
    const tx = el.querySelector('.tx'); if (tx && !el.classList.contains('hero')) tx.setAttribute('aria-hidden', 'true');
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
// a calm confirmation above the tabs; one with a way on ('Gemt på telefonen · Se Gemt') stays a little longer and can
// be tapped
let toastTimer, toastAct = null;
function toast(msg, good = true, action = null) {
  $('toastText').textContent = msg;
  $('toast').querySelector('svg').style.display = good ? '' : 'none';
  const b = $('toastAct');
  toastAct = action && action[1];
  b.hidden = !action; if (action) b.querySelector('span').textContent = action[0];
  $('toast').classList.toggle('acts', !!action);
  $('toast').classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), action ? 3200 : 1700);
}
$('toastAct').addEventListener('click', () => { const f = toastAct; toastAct = null; $('toast').classList.remove('show'); if (f) f(); });
function markShared(i) {
  shared[i.id] = { at: Date.now(), title: i.title, link: i.link, source: i.source };
  for (const [k, v] of Object.entries(shared)) if (Date.now() - v.at > 30 * 864e5) delete shared[k];
  store.set('shared', shared);
  for (const el of list.querySelectorAll('#' + CSS.escape('s-' + i.id))) {   // on every page that shows it
    el.classList.remove('new'); el.querySelector('.m').innerHTML = meta(i, { tag: el.dataset.tag === '1', msec: el.dataset.msec || '', clock: el.dataset.clock === '1', top: el.dataset.top === '1', tick: el.classList.contains('tick') });
  }
  learnFrom(i, 'share');
}
// the phone's own share sheet (WhatsApp is one tap away there); copying is the fallback
async function share(text, i) {
  if (navigator.share) {
    try { await navigator.share({ text }); if (i) markShared(i); return; } catch (e) { if (e.name === 'AbortError') return; }
  }
  if (await copyText(text)) { toast('Kopieret – sæt ind i WhatsApp'); if (i) markShared(i); }
}

async function onTap(e) {
  const t = e.target, el = t.closest('[data-id]'), i = el && asShown(el);   // what is shared is the headline one sees
  const ld = t.closest('[data-lede]');   // a part of the lede: its story, opened
  if (ld) { e.preventDefault(); ledeGo(ld.dataset.lede); return; }
  // the wiki and the movement's answers: a name in a text, a subject, an answer's line or row, the index of the pages
  const bg = t.closest('[data-begreb]');
  if (bg) { e.preventDefault(); openSide('begreb', bg.dataset.begreb); return; }
  const sv = t.closest('[data-svar]');
  if (sv) { e.preventDefault(); openSide('svar', sv.dataset.svar); return; }
  if (t.closest('[data-begreber]')) { openSide('begreber'); return; }
  const av = t.closest('[data-an-view]');   // Analyser's toggle: the answers' list or the Leksikon
  if (av) {
    if (av.dataset.anView === 'leksikon') { if (tab !== 'begreber') openSide('begreber'); }
    else if (tab !== 'analyses') { backStack.length = 0; leaveSides(); setTab('analyses'); }
    return;
  }
  const uf = t.closest('[data-unfold]');
  if (uf) {   // a list on a wiki page or in an answer unfolds in place; folded back, its button stays under the finger
    const k = uf.dataset.unfold, was = unfolded.has(k);
    was ? unfolded.delete(k) : unfolded.add(k);
    delete steps[k];
    if (was) keepPlace(uf, render); else render();
    return;
  }
  const st = t.closest('[data-step]');   // twenty more of a long list, the button kept under the finger
  if (st) { const k = st.dataset.step; steps[k] = stepOf(k) + STEP; const y = cur().scrollTop; render(); cur().scrollTop = y; return; }
  const rt = t.closest('[data-retry]');   // a file that failed: asked for again at once
  if (rt) {
    for (const k of rt.dataset.retry.split(',')) { if (vd[k] && vd[k].state === 'error') vd[k].state = 'idle'; need(k); }
    rt.disabled = true; rt.textContent = 'Henter …';
    return;
  }
  const yj = t.closest('[data-year]');   // Analyser's years (A–Å's letters: azScrub)
  if (yj) {   // the year's band sticks under the strip: aim below both
    const band = pg$('an-y-' + yj.dataset.year), strip = pg$('anStrip');
    if (band) scrollToEl(band.nextElementSibling || band, 8 + band.offsetHeight + (strip ? strip.offsetHeight : 0));
    return;
  }
  if (t.closest('[data-reload]')) { renderHeader('henter …'); load(true); return; }
  if (t.closest('[data-brief]')) { share(briefText()); return; }   // Del dagens overblik
  if (t.closest('[data-hint-x]')) { iosHint = false; store.set('iosHint', Date.now()); const h = pg$('iosHint'); if (h) h.remove(); return; }
  const cr = t.closest('[data-credit]');
  if (cr) { cr.classList.toggle('full'); return; }   // the credit line in full
  const sq = t.closest('[data-search-q]');   // a search for what a page or a list did not have
  if (sq) { query = sq.dataset.searchQ; $('search').value = query; if (sq.dataset.scope) searchScope = sq.dataset.scope; setTab('search', { top: true }); render(); return; }
  const scp = t.closest('[data-scope]');
  if (scp) { searchScope = scp.dataset.scope; if (tab !== 'search') setTab('search', { top: true }); else { render(); cur().scrollTop = 0; } return; }
  const aq = t.closest('[data-an-q]');   // all the answers a search found, in Analyser
  if (aq) { anQuery = aq.dataset.anQ; setTab('analyses', { top: true }); draw('analyses'); return; }
  const ar = t.closest('[data-area]');   // Analyser's area filter: the list in place, remembered on the phone
  if (ar) {
    anArea = ar.dataset.area;
    if (tab !== 'analyses') { setTab('analyses', { top: true }); return; }
    draw('analyses');
    const row = $('opts').querySelector('.an-chips'), on = row && row.querySelector('.chip.on');
    if (on) row.scrollLeft = Math.max(0, on.offsetLeft - 16);   // the chosen area in view in its row
    const l = pg$('anStrip'), lst = cur().querySelector('.an-list');
    if (l && lst && lst.getBoundingClientRect().top < l.getBoundingClientRect().bottom) scrollToEl(lst, l.offsetHeight);
    return;
  }
  const azk = t.closest('[data-az-kind]');
  if (azk) { azKind = azk.dataset.azKind; render(); return; }
  const toc = t.closest('[data-toc]');   // a wiki page's contents row: its part just below the bar
  if (toc) { const sec = pg$(toc.dataset.toc); if (sec) scrollToEl(sec, 8); return; }
  const ths = t.closest('[data-thr-share]') || t.closest('[data-thr-copy]');   // a development as a WhatsApp text
  if (ths) {
    const th = allThreads().find(x => x.key === (ths.dataset.thrShare || ths.dataset.thrCopy));
    if (th) { const txt = thrText(th); if (ths.dataset.thrShare) share(txt); else if (await copyText(txt)) toast('Kopieret'); }
    return;
  }
  const ks = t.closest('[data-kshare]') || t.closest('[data-kcopy]');   // an answer or a wiki page as a WhatsApp text
  if (ks) {
    const [k, id] = (ks.dataset.kshare || ks.dataset.kcopy).split(':'), a = k === 'a' ? answers().by.get(id) : null;
    const txt = k === 'a' ? (a ? svarText(a) : '') : begrebText(id);
    if (txt) { if (ks.dataset.kshare) share(txt); else if (await copyText(txt)) toast('Kopieret'); }
    return;
  }
  const kv = t.closest('[data-ksave]') || t.closest('[data-unsave]');   // Gem for an answer or a page; Fjern on Gemt
  if (kv) {
    const [k, id] = (kv.dataset.ksave || kv.dataset.unsave).split(':'), on = toggleSave(k, id, findStory(id));
    // the rows' bookmarks change at once (a list that keeps its search field is not drawn again)
    document.querySelectorAll(`.an-save[data-ksave="${CSS.escape(k + ':' + id)}"]`).forEach(b => {
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on);
      b.setAttribute('aria-label', (on ? 'Gemt' : 'Gem') + b.getAttribute('aria-label').replace(/^Gemt?/, ''));
      b.querySelector('use').setAttribute('href', on ? '#i-saved' : '#i-save');
    });
    render(); return;
  }
  const oks = t.closest('[data-ok-sec]');   // Økonomi's topic in the dock: the frame jumps there
  if (oks) { okCur = oks.dataset.okSec; paintOpts(); okJump(okCur); return; }
  const mv = t.closest('[data-move]');   // Gemt's 'Del eller flyt dine gemte': the link with the saves, shared or copied
  if (mv) {
    const url = moveUrl || await moveLink();
    if (mv.dataset.move === 'copy') { if (await copyText(url)) toast('Linket er kopieret'); }
    else share(`${saved.length} gemte fra Khabar – åbn linket for at lægge dem ind:\n${url}`);
    return;
  }
  const fi = t.closest('[data-find-item]');   // a story that left Live: looked for among everything the radar read
  if (fi) { focusMissing = ''; findGone(fi.dataset.findItem); return; }
  if (t.closest('[data-gone-x]')) { focusMissing = ''; render(); return; }
  if (t.closest('[data-search-retry]')) { searchState = 'idle'; searchLoaded = 0; loadIndex(); render(); return; }
  if (t.closest('[data-go]')) {
    const g = t.closest('[data-go]'), go = g.dataset.go;
    if (SIDE.has(go)) openSide(go); else setTab(go, { top: true });
    return;
  }
  if (t.closest('[data-cov]') && el) {
    covOpen.has(el.dataset.id) ? covOpen.delete(el.dataset.id) : covOpen.add(el.dataset.id);
    const i2 = asShown(el) || findStory(el.dataset.id), box = el.querySelector('.x-in');
    if (i2 && box) box.innerHTML = rowDetail(el, i2);
    return;
  }
  const live = t.closest('[data-live]');
  if (live) { e.preventDefault(); openInLive(live.dataset.live); return; }   // 'Lige nu', a development's step, a recap line
  const follow = t.closest('[data-follow]');
  if (follow) { openSide('threads', follow.dataset.follow); return; }   // the development, unfolded, at its own address
  const thr = t.closest('[data-thr]');
  if (thr) {   // unfold a development; folding it back keeps its card where the finger was
    const k = thr.dataset.thr, card = pg$('thr-' + k), was = udOpen.has(k);
    was ? udOpen.delete(k) : udOpen.add(k); render();
    if (was && card && card.getBoundingClientRect().top < 0) scrollToEl(pg$('thr-' + k), 12);
    return;
  }
  if (t.closest('[data-ud-all]')) { udAll = true; render(); return; }
  const chip = t.closest('[data-q]');
  if (chip) { query = chip.dataset.q + ' '; $('search').value = query; $('search').focus({ preventScroll: true }); render(); cur().scrollTop = 0; return; }
  if (t.closest('[data-day-more]')) { dayOpen.add(t.closest('[data-day-more]').dataset.dayMore); render(); return; }
  if (t.closest('[data-day-share]')) { const d = findDay(t.closest('[data-day]').dataset.day); if (d) share(dayText(d)); return; }
  if (t.closest('[data-line]') && !t.closest('[data-live]')) {   // a line that tells a story: opening it says 'more like this', quietly
    const a = t.closest('[data-line]'), r = a.dataset.story && findStory(a.dataset.line);
    if (r) learnFrom(r, 'read');
    return;
  }
  if (t.closest('[data-archive]')) { loadArchive(); return; }
  if (t.closest('[data-arch-all]')) { archAll = true; render(); return; }
  if (t.closest('[data-arch-toggle]')) { const c = t.closest('[data-arch]').dataset.arch; const was = daysOpen.has(c); daysOpen.clear(); if (!was) { daysOpen.add(c); expanded.clear(); } render();
    if (!was) scrollToEl(cur().querySelector(`[data-arch="${CSS.escape(c)}"]`), 8);   // the opened day starts at the top
    return; }
  if (t.closest('[data-latest-all]')) { latestAll = true; render(); return; }
  if (t.closest('[data-cal-f], [data-cal-imp], [data-cal-past], [data-cal], [data-cal-go], [data-cal-share], [data-cal-copy]') && await calTap(t)) return;
  const lsec = t.closest('[data-live-sec]');
  if (lsec) { liveSec = liveSec === lsec.dataset.liveSec ? '' : lsec.dataset.liveSec; expanded.clear(); render(); cur().scrollTop = 0; return; }
  if (t.closest('[data-live-imp]')) { liveImp = !liveImp; store.set('liveImp', liveImp); expanded.clear(); render(); cur().scrollTop = 0; return; }
  if (!el) return;
  const sb = t.closest('[data-save]');
  if (sb && i) {   // the bookmark: the story kept on the phone with what it shows
    const on = toggleSave('s', i.id, i);
    // every bookmark of the story changes: the row's and the opened story's
    document.querySelectorAll(`[id="s-${CSS.escape(i.id)}"] [data-save]`).forEach(b => {
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.setAttribute('aria-label', on ? 'Gemt' : 'Gem');
      b.querySelector('use').setAttribute('href', on ? '#i-saved' : '#i-save');
    });
    return;
  }
  if (t.closest('[data-share]')) share(shareText(i), i);
  else if (t.closest('[data-copy]')) { if (await copyText(shareText(i))) { toast('Kopieret'); markShared(i); } }
  else if (t.closest('[data-read]')) learnFrom(i, 'read');
  else if (t.closest('[data-toggle]')) toggle(el);
}
$('list').addEventListener('click', onTap);
$('opts').addEventListener('click', onTap);   // the page's options in the dock: the same buttons, the same ways
$('freshPill').addEventListener('click', () => { $('freshPill').hidden = true; cur().scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); });
// the page in view scrolls (scroll events do not bubble: caught on their way down)
function onPageScroll() {
  const y = cur() ? cur().scrollTop : 0;
  if (y < 120 && !$('freshPill').hidden) $('freshPill').hidden = true;
  $('bar').classList.toggle('scrolled', y > 4);
  if (catchUp && !catchUp.done && tab === 'home' && y > 80) fadeCatchUp();
}
document.addEventListener('scroll', e => { lastScroll = performance.now(); if (e.target === cur()) onPageScroll(); }, { capture: true, passive: true });

// ---------------------------------------------------------------- pull down to refresh: the logo answers
// The list follows the pull; far enough down, the red dot of the logo in the top bar swells, and when one lets go it
// signals with the intro's hairline rings while the news loads – the name is not shown twice.
let pull = null;
const PULL = 130;   // a deliberate pull refreshes; a little extra drag at the top (to see the date) does not
const logo = document.querySelector('.brand .logo');
addEventListener('touchstart', e => {
  const pg = e.target.closest && e.target.closest('.page');
  if (pg && pg === cur() && pg.scrollTop <= 0 && tab !== 'search' && !paging && !e.target.closest('.k-box')) pull = { pg, x: e.touches[0].clientX, y: e.touches[0].clientY, d: 0 };
}, { passive: true });
addEventListener('touchmove', e => {
  if (!pull) return;
  const pg = pull.pg, dx = e.touches[0].clientX - pull.x;
  pull.d = e.touches[0].clientY - pull.y;
  if (!pull.lock && Math.hypot(dx, pull.d) > 10) pull.lock = Math.abs(pull.d) > Math.abs(dx) ? 'y' : 'x';
  if (pull.lock === 'x') { pull = null; pg.classList.remove('pulling'); pg.style.transform = ''; logo.classList.remove('ready'); return; }   // a sideways swipe
  if (pull.lock !== 'y') return;
  if (pull.d <= 0 || pg.scrollTop > 0) { pg.style.transform = ''; return; }
  pg.classList.add('pulling');
  pg.style.transform = `translateY(${(110 * (1 - Math.exp(-pull.d / 170))).toFixed(1)}px)`;
  logo.classList.toggle('ready', pull.d >= PULL);
}, { passive: true });
// Økonomi's page scrolls inside its frame, so it has its own pull (18/10, the owner: 'man kan ikke hive ned for at
// opdatere økonomi siden'); the logo answers it as it answers the app's own
window.khabarOkReady = on => logo.classList.toggle('ready', !!on);
window.khabarOkRefresh = async run => {
  logo.classList.add('blink');
  const t0 = performance.now();
  try { await run(); } catch { /* the page says it itself */ }
  const ring = 1400, spent = performance.now() - t0;
  await wait(Math.max(1, Math.ceil(spent / ring)) * ring - spent);
  logo.classList.remove('blink');
};
addEventListener('touchcancel', () => {   // an interrupted pull must not leave the page pulled down
  if (!pull) return;
  const pg = pull.pg;
  pull = null;
  pg.classList.remove('pulling'); pg.style.transform = ''; logo.classList.remove('ready');
});
addEventListener('touchend', async () => {
  if (!pull) return;
  const go = pull.lock === 'y' && pull.d >= PULL, pg = pull.pg;
  pull = null;
  pg.classList.remove('pulling');
  pg.classList.add('settling');
  logo.classList.remove('ready');
  if (go) {   // the page waits a little way down until the dot has signalled to the end of a full ring
    pg.style.transform = 'translateY(48px)';
    logo.classList.add('blink');
    const t0 = performance.now();
    await load(true);
    const ring = 1400, spent = performance.now() - t0;
    await wait(Math.max(1, Math.ceil(spent / ring)) * ring - spent);
    logo.classList.remove('blink');
  }
  pg.style.transform = '';
  setTimeout(() => pg.classList.remove('settling'), 420);
});

// ---------------------------------------------------------------- the dock: a page's own options within the thumb's reach
// The owner, 17/10: "man skal let med tommelfingeren kunne trykke frem og tilbage på de der forskellige knapper eller
// valgmuligheder, der er under hver side". One shared dock above the tabs (#opts, inside the fixed .dock, so --dock and
// the safe area count it): one or two rows of chips and segments that scroll sideways when they overflow, solid like the
// bar (no blur), gone while the keyboard is up (the tabs go too) and on side pages, search and the front page. The
// pages' bottom room is --dock, measured from the whole dock, so nothing hides under it, and an opened story's buttons
// come up above it (keepInView measures the dock). The top bar keeps only the logo and title, Gemt, search and settings.
// Live: the sort and the three filters; Kalender: the kinds and the window; Analyser: its chip row.
function paintOpts(t = tab) {
  const box = $('opts');
  if (!box) return;
  const html = t === 'analyses' || t === 'begreber' ? anOpts(t) : ASIDE.has(t) ? '' : t === 'latest' ? liveOpts() : t === 'kalender' ? calOpts() : t === 'okonomi' ? okOpts() : '';
  const was = dockTab;
  dockTab = t;
  if (box.hidden !== !html) box.hidden = !html;
  box.dataset.for = html ? t : '';
  if (!html) { if (box.firstChild) box.textContent = ''; return; }
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  morph(box, tpl.content, []);   // a row's own element stays, so a chip row keeps its sideways place
  edgesIn(box);
  const pair = new Set([was, t]).size === 1 || (['analyses', 'begreber'].includes(was) && ['analyses', 'begreber'].includes(t));   // the toggle stays put
  if (!pair && !reduceMotion) box.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 160, easing: 'ease-out' });
}

// ---------------------------------------------------------------- Økonomi: the economy page in the app (the owner, 17/10:
// "Kan du gøre kort separat fra priser, lav det til en femte fane"). energi/?embed=1 in a same-origin frame that fills
// the page, made the first time the tab is shown (or a swipe heads for it): the page hides its own bar and back link and
// follows the app's look and text size live (it watches the app's <html>). khabar.nu/energi stays a page of its own.
function okPage(pg) {
  if (!pg) return;
  if (pg.querySelector('iframe')) return;
  pg.innerHTML = netDown() ? `<div>${stateBlock('offline', 'Ingen forbindelse. Priserne kommer, så snart telefonen er på nettet.', [['Prøv igen', 'data-okframe']])}</div>`
    : '<div class="ok-pr"><iframe src="energi/?embed=1" title="Økonomi – olie, brændstof og markeder"></iframe></div>';
}
// its topics in the app's dock (18/10, the owner: after 'Råvarer' on a phone the frame's own dock could not be tapped
// until one scrolled up – a fixed element inside a frame): the frame tells the topics and the one in view, a chip asks
// the frame to jump; the chosen chip is kept in view inside its row
let okTopics = [], okCur = '';
window.khabarOk = (topics, current) => {
  if (topics) okTopics = topics;
  if (current) okCur = current;
  if (dockTab !== 'okonomi' && tab !== 'okonomi') return;
  paintOpts();
  const row = $('o-ok'), on = row && row.querySelector('[aria-current="true"]');
  if (on && row.scrollWidth > row.clientWidth + 1) row.scrollTo({ left: on.offsetLeft - (row.clientWidth - on.offsetWidth) / 2, behavior: reduceMotion ? 'auto' : 'smooth' });
};
const okOpts = () => okTopics.length ? `<nav class="o-row" id="o-ok" aria-label="Emner">${okTopics.map(([id, l]) =>
  `<button class="chip${id === okCur ? ' on' : ''}" data-ok-sec="${esc(id)}" aria-current="${id === okCur}">${esc(l)}</button>`).join('')}</nav>` : '';
function okJump(id) {
  const f = pageEl('okonomi') && pageEl('okonomi').querySelector('iframe');
  try { f.contentWindow.okJump(id); } catch { /* the frame is not ready */ }
}
// the oil row of a story, the settings' 'Mere' and ?tab=priser (kept as an alias of ?tab=okonomi): the Økonomi tab
function openOkonomi() {
  if (!$('sheet').hidden) closeSheet();
  setTab('okonomi', { top: true });
}

// ---------------------------------------------------------------- Kalender: the planned events ahead (the owner, 17/10:
// "en kalender, som viser fremtidige begivenheder … man kan se i kalenderen, hvad der skal til at ske snart, af planlagte
// begivenheder", "den skal have en fane for sig selv"; the Islamic dates left out at his wish the same day). Two files merged:
// calendar.json (the radar's, data branch: elections, summits, the Fed's and the ECB's rate meetings, Danish dates and
// the fixed dates of config/calendar.json – src/radar/calendar.py) and kalender.json (the editor's own entries from the news, digest
// branch: deadlines, talks, votes, rulings). The editor's entry wins on the same date and title. Reality only: a date,
// what happens, where, one factual line on why it matters and the source – never a forecast. The top: a red fly title
// and one serif line naming what comes next; 'Det sker snart' (the next seven days with their countdown); then month by
// month; 'Tidligere' (the last 30 days) folded at the foot. The dock holds the kinds and the window.
const CAL_KINDS = { valg: 'Valg', 'topmøde': 'Topmøde', centralbank: 'Centralbank', frist: 'Frist', retssag: 'Retssag',
  forhandling: 'Forhandling', dansk: 'Danmark', andet: 'Andet' };
const CAL_FILTERS = [['', 'Alle'], ['valg', 'Valg'], ['top', 'Topmøder'], ['bank', 'Centralbanker'], ['frist', 'Frister'],
  ['dk', 'Danmark']];
const CAL_DOT = { valg: 'valg', top: 'topmøde', bank: 'centralbank', frist: 'frist', dk: 'dansk' };
const calIn = (f, e) => !f || (f === 'valg' ? e.kind === 'valg' : f === 'top' ? e.kind === 'topmøde' : f === 'bank' ? e.kind === 'centralbank'
  : f === 'frist' ? ['frist', 'retssag', 'forhandling', 'andet'].includes(e.kind)
    : f === 'dk' ? e.kind === 'dansk' || fold(e.place) === 'danmark' : true);
let calF = '', calPast = false, calGen = 0, calMemo = null, calPend = '', calGone = '';
// everything ahead is shown (the owner, 18/10: 'kalender skal ikke have en sortering med måneder, men skal som standard
// vise "alt"'); 'Kun vigtige' hides the events of low weight – remembered on the phone, like Live's
const calWOf = e => (e.kind === 'centralbank' ? 1 : e.w === 3 || e.w === 2 ? e.w : 1);   // a rate decision is quiet (18/10)
let calImp = !!store.get('calImp', false);
const calOpen = new Set();                         // events opened (their why, source and stories)
let calFocus = params.get('kalender') || '';       // ?kalender=<id>: the tab opens at that event
// a day as a number (days since 1970), from 'YYYY-MM-DD' or 'YYYY-MM' (its first day); the Danish today
const calDay = s => Date.UTC(+s.slice(0, 4), s.length > 4 ? +s.slice(5, 7) - 1 : 0, s.length > 7 ? +s.slice(8, 10) : 1) / 864e5;
const calToday = () => calDay(dkYmd(new Date()));
const calExact = e => e.date.length > 7;
// a year alone (18/10): an annual meeting or an election whose day is not set – 'i løbet af 2027', after its December
const calYear = e => e.date.length === 4;
// the last day an event lasts: its end, its day, or – a month only – the month's last day
const calEnd = e => (calExact(e) ? calDay(e.end && e.end.length > 7 ? e.end : e.date) : calYear(e) ? Date.UTC(+e.date, 11, 31) / 864e5
  : Date.UTC(+e.date.slice(0, 4), +e.date.slice(5, 7), 0) / 864e5);
// a month-only date sorts after the month's exact days
const calKey = e => (calExact(e) ? calDay(e.date) : calEnd(e) + (calYear(e) ? 0.75 : 0.5));
const calOk = e => !!e && typeof e.id === 'string' && /^\d{4}(?:-\d{2}(?:-\d{2})?)?$/.test(String(e.date || '')) && !!e.title;
const calNorm = s => fold(s).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
// the two files as one list, worked out once per file and day; the editor's entry wins on the same date and title
function calItems() {
  const day = calToday();
  if (calMemo && calMemo.gen === calGen && calMemo.day === day) return calMemo.list;
  const ed = ((V('kal') || {}).items || []).filter(calOk).map(e => ({ ...e, ed: true }));
  const mine = new Set(ed.map(e => e.date + '|' + calNorm(e.title))), ids = new Set(ed.map(e => e.id));
  const src = ((V('cal') || {}).items || []).filter(e => calOk(e) && !ids.has(e.id) && !mine.has(e.date + '|' + calNorm(e.title)));
  const list = [...src, ...ed].map(e => ({ ...e, kind: CAL_KINDS[e.kind] ? e.kind : 'andet', title: quoteIsrael(String(e.title)),
    why: quoteIsrael(String(e.why || '')), place: quoteIsrael(String(e.place || '')) })).sort((a, b) => calKey(a) - calKey(b));
  calMemo = { gen: calGen, day, list };
  return list;
}
const calFind = id => calItems().find(e => e.id === id);
// 'i dag', 'i morgen', 'om 5 dage' – or 'i gang' for a summit already under way
const calCount = (e, today) => { const n = calDay(e.date) - today; return n < 0 ? 'i gang' : n === 0 ? 'i dag' : n === 1 ? 'i morgen' : `om ${n} dage`; };
const calDate = s => new Date((s.length > 7 ? s : s.length > 4 ? s + '-01' : s + '-01-01') + 'T12:00:00');
// the day as a share and a meta line say it: '17/10' (a month only: 'november 2026')
const calDm = e => (calExact(e) ? `${+e.date.slice(8, 10)}/${+e.date.slice(5, 7)}` : calYear(e) ? `i løbet af ${e.date}` : FMT.my.format(calDate(e.date)));
const calUntil = e => (e.end && e.end.length > 7 && e.end !== e.date ? `til ${FMT.dm.format(calDate(e.end))}` : '');
// the next 48 hours are the one red: the kind's dot of an event today or tomorrow
const calNear = (e, today) => calExact(e) && calEnd(e) >= today && calDay(e.date) - today <= 1;
// one event as a row: the day large in tabular figures and its weekday small, the title, one quiet line – the kind with
// its calm dot, the place, 'til …', 'forventet' – and, opened, the why, the source and the stories
function calRow(e, today, o = {}) {
  const d = calDate(e.date), open = !o.front && calOpen.has(e.id), near = calNear(e, today);
  const day = calExact(e) ? `<b>${d.getDate()}</b><small>${esc(FMT.wd.format(d))}</small>`
    : calYear(e) ? `<b class="mo">${esc(e.date)}</b><small>år</small>` : `<b class="mo">${esc(FMT.mon.format(d))}</b><small>måned</small>`;
  const parts = [...(o.count && calExact(e) ? [`<span class="cn">${calCount(e, today)}</span>`] : []),   // a month alone has no countdown
    `<span class="ck${near ? ' near' : ''}" data-k="${esc(e.kind)}"><i></i>${esc(CAL_KINDS[e.kind])}</span>`,
    ...(e.place ? [`<span>${esc(e.place)}</span>`] : []), ...(calUntil(e) ? [`<span>${calUntil(e)}</span>`] : []),
    ...(e.approx ? ['<span>forventet</span>'] : [])];
  const label = `${calExact(e) ? FMT.full.format(d) : FMT.my.format(d)}: ${e.title}${e.place ? ', ' + e.place : ''}${e.approx ? ', forventet' : ''}${e.w === 3 ? ', høj betydning' : ''}${o.count ? ', ' + calCount(e, today) : ''}`;
  const hit = o.front ? `<button class="hit" data-cal-go="${esc(e.id)}" aria-label="${esc(label)}"></button>`
    : `<button class="hit" data-cal="${esc(e.id)}" aria-expanded="${open}" aria-label="${esc(label)}"></button>`;
  // the weight (17/10): 3 a soft red ground, a red edge and 'Høj betydning'; 2 the red edge without the ground (18/10)
  const w = calWOf(e);
  // the front page's 'Vigtige datoer' holds only these: its title says it, the row does not (the owner, 18/10)
  if (w === 3 && !o.front) parts.unshift('<span class="cw">Høj betydning</span>');
  return `<div class="ce${open ? ' open' : ''}${w > 1 ? ' w' + w : ''}" id="${o.front ? 'cf-' : 'ce-'}${esc(e.id)}"><div class="row">${hit}<span class="cd" aria-hidden="true">${day}</span>`
    + `<span class="tx" aria-hidden="true"><span class="h">${esc(e.title)}</span><span class="m">${parts.join('')}</span></span></div>`
    + (open ? calDetail(e) : '') + '</div>';
}
// an opened event: one factual line on why it matters, the source, Del · Kopiér and the stories in Live that name it
function calDetail(e) {
  const st = calStories(e);
  return `<div class="ce-x">${e.why ? `<p class="ce-why">${esc(e.why)}</p>` : ''}`
    + (st.length ? `<ul class="ce-st" aria-label="I nyhederne">${st.map(i => `<li><button data-live="${esc(i.id)}"><span dir="auto">${bold(i.title, i.kw)}</span><em>${esc(i.source)} · ${stamp(i.published || i.found)}</em></button></li>`).join('')}</ul>` : '')
    + `<div class="acts know-acts">${e.link ? `<a class="act" href="${esc(e.link)}" target="_blank" rel="noopener">Kilde<svg aria-hidden="true"><use href="#i-chev"/></svg></a>` : ''}`
    + `<button class="act" data-cal-share="${esc(e.id)}"><svg aria-hidden="true"><use href="#i-share"/></svg>Del</button>`
    + `<button class="act" data-cal-copy="${esc(e.id)}"><svg aria-hidden="true"><use href="#i-copy"/></svg>Kopiér</button></div></div>`;
}
// the stories in Live that name an event: the editor's own ids first, then those whose headline shares its subject – the
// place and a word of the title, or two words of the title
const calStems = t => new Set((String(t || '').toLowerCase().match(/[\p{L}\p{N}]{4,}/gu) || []).map(w => w.slice(0, 6)));
function calStories(e) {
  const out = [], seen = new Set();
  for (const id of e.ids || []) { const i = findStory(id); if (i && !seen.has(i.id)) { seen.add(i.id); out.push(i); } }
  const ts = calStems(e.title), place = calNorm(e.place.replace(/[“”]/g, ''));
  for (const i of stories()) {
    if (out.length >= 3) break;
    if (seen.has(i.id) || !ts.size) continue;
    const text = [i.title, i.origTitle, i.title_da].join(' '), n = overlap(calStems(text), ts);
    const at = place && place.length >= 3 && (' ' + calNorm(text) + ' ').includes(' ' + place);
    if (n >= 2 || (n >= 1 && at)) { seen.add(i.id); out.push(i); }
  }
  return out;
}
// the share: '17/10 · Midtvejsvalg i USA – <why> – via khabar.nu/?kalender=<id>'
const calText = e => `${calDm(e)} · ${e.title}${e.place && !e.title.includes(e.place) ? ` (${e.place})` : ''}${e.why ? ' – ' + e.why : ''} – via khabar.nu/?kalender=${encodeURIComponent(e.id)}`;
function kalenderPage() {
  need('cal'); need('kal');
  const today = calToday(), all = calItems();
  if (!all.length) {
    if (waiting('cal')) return loadingBlock('Henter kalenderen …');
    if (failed('cal')) return retry('kalenderen', 'cal', 'kal');
  }
  // ?kalender=<id>: that event opened, in the list whatever the filter and window, and brought into view once drawn
  if (calFocus && (V('cal') || failed('cal')) && !waiting('kal')) {
    const e = calFind(calFocus);
    if (e) { calOpen.add(e.id); calF = calIn(calF, e) ? calF : ''; if (calImp && calWOf(e) < 2) calImp = false; if (calEnd(e) < today) calPast = true; calPend = e.id; }
    else calGone = calFocus;
    calFocus = '';
  }
  const shown = all.filter(e => calIn(calF, e) && (!calImp || calWOf(e) > 1)), up = shown.filter(e => calEnd(e) >= today);
  const soon = up.filter(e => calExact(e) && calDay(e.date) - today <= 7), soonIds = new Set(soon.map(e => e.id));
  const later = up.filter(e => !soonIds.has(e.id));
  const past = shown.filter(e => calEnd(e) < today && calEnd(e) >= today - 30).reverse();
  const next = up.find(e => calExact(e) && calDay(e.date) >= today) || up.find(e => calExact(e));   // not one under way
  const name = (CAL_FILTERS.find(f => f[0] === calF) || CAL_FILTERS[0])[1];
  let h = `<header class="cal-top" id="cal-top"><p class="cal-fly">Kalender${calF ? ' · ' + esc(name) : ''}</p>`
    + `<h2 class="cal-next">${next ? `Næste: ${esc(next.title)} ${calCount(next, today)}` : 'Intet planlagt foreløbig'}</h2></header>`;
  if (calGone) h += `<p class="notice" id="cal-gone"><svg aria-hidden="true"><use href="#i-clock"/></svg><span>Begivenheden er ikke længere i kalenderen.</span></p>`;
  h += `<section class="block cal-soon" id="cal-soon">${blockHead('Det sker snart')}`
    + (soon.length ? soon.map(e => calRow(e, today, { count: true })).join('') : '<p class="cal-none">Intet planlagt de næste syv dage.</p>') + '</section>';
  let month = '';
  for (const e of later) {
    const m = e.date.slice(0, 7);   // a year alone gets its own band after its December
    if (m !== month) { h += `${month ? '</section>' : ''}<section class="cal-mo" id="cal-m-${m}"><h3 class="cal-mh">${esc(m.length === 4 ? `Senere i ${m} · dato ikke fastsat` : cap(FMT.my.format(calDate(m))))}</h3>`; month = m; }
    h += calRow(e, today);
  }
  if (month) h += '</section>';
  else if (!soon.length) h += stateBlock('empty', `Intet planlagt${calF ? ' af den slags' : ''}${calImp ? ' af høj eller middel betydning' : ''}.`, calImp ? [['Vis alle', 'data-cal-imp']] : []);
  if (past.length) {
    h += `<section class="cal-past" id="cal-past"><button class="qbtn cal-pb" data-cal-past aria-expanded="${calPast}">Tidligere<small> · de seneste 30 dage</small></button>`
      + (calPast ? past.map(e => calRow(e, today)).join('') : '') + '</section>';
  }
  return h + '<p class="foot">Datoerne er planlagte og kan blive flyttet.</p>';
}
// an event a link or the front page named, brought just below the bar and its month (drawn: its rows out of sight are
// laid out late – content-visibility –, so it is aimed at again a moment later, and at every redraw for two seconds)
let calAim = null;
function calAimAt(pg) {
  if (calPend && pg.querySelector('#' + CSS.escape('ce-' + calPend))) { calAim = { id: calPend, until: performance.now() + 2000 }; calPend = ''; }
  if (!calAim || performance.now() > calAim.until) { calAim = null; return; }
  const ev = pg.querySelector('#' + CSS.escape('ce-' + calAim.id));
  if (!ev) return;
  const go = () => {
    if (touching || !ev.isConnected || !calAim) { calAim = null; return; }
    const mh = ev.closest('.cal-mo') && ev.closest('.cal-mo').querySelector('.cal-mh');
    scrollToEl(ev, 8 + (mh ? mh.offsetHeight : 0));
  };
  requestAnimationFrame(go); setTimeout(go, 320);
  // the headline's serif comes beside the page and reflows the top when it lands: aimed at once more then
  if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', () => { if (calAim && performance.now() < calAim.until + 4000) go(); }, { once: true });
}
list.addEventListener('touchstart', () => { calAim = null; }, { passive: true });   // the reader's own hand wins
// the tab came into view: a link's event is looked for as soon as the files are there
function calShown() { if (calFocus || calPend) redrawPages(['kalender']); }
// 'Vigtige datoer' on the front page (until 18/10 'Det sker snart'): the events of high weight of the next three months, after the second block
// the page draws, 'Alle ›' to the tab; none in the fortnight: no block
function calBlock() {
  need('cal'); need('kal');
  // 'Vigtige datoer' (the owner, 18/10: 'burde tage 3 måneders højt vigtige begivenheder i rækkefølge, maks 4. glem middel
  // vigtighed. og måske en anden titel end "sker snart"'): the events of high weight of the next three months, in their
  // order (a month alone after its days; a year alone is no date), at most four
  const today = calToday(), list = calItems().filter(e => !calYear(e) && calWOf(e) === 3 && calEnd(e) >= today && calDay(e.date) - today <= 92).slice(0, 4);
  if (!list.length) return '';
  return `<section class="block cal-b" id="cal-front">${blockHead('Vigtige datoer', moreLink('Alle', 'kalender'))}`
    + `<div class="cal-rows">${list.map(e => calRow(e, today, { front: true, count: true })).join('')}</div></section>`;
}
// the dock: one toggle, Vigtige · Alle (the owner, 18/10: 'filter kun være "Vigtige" og "alle" og det skal være en
// toggle'), as Live's chips – 'Vigtige' with the weights' short red edge (the owner: 'stadig kan have en rød accent …
// følge stilen som resten af siderne, f.eks på live'); the kinds' chips are gone – the kind shows by its dot on a row
function calOpts() {
  return `<div class="o-row cal-tog" id="o-cal-k" role="radiogroup" aria-label="Vis">`
    + `<button class="chip imp-chip${calImp ? ' on' : ''}" role="radio" data-cal-imp="1" aria-checked="${calImp}"><i class="imp-i" aria-hidden="true"></i>Vigtige</button>`
    + `<button class="chip${calImp ? '' : ' on'}" role="radio" data-cal-imp="0" aria-checked="${!calImp}">Alle</button></div>`;
}
// the calendar's own taps, in the page, on the front page and in the dock (onTap sends them here)
async function calTap(t) {
  const f = t.closest('[data-cal-f]'), w = t.closest('[data-cal-imp]'), r = t.closest('[data-cal]'), go = t.closest('[data-cal-go]');
  const sh = t.closest('[data-cal-share]') || t.closest('[data-cal-copy]');
  if (f) { calF = f.dataset.calF; calGone = ''; render(); cur().scrollTop = 0; return true; }
  if (w) {   // the toggle's side, or the page's 'Vis alt'
    const v = w.dataset.calImp, next = v === '1' ? true : v === '0' ? false : !calImp;
    if (next !== calImp) { calImp = next; store.set('calImp', calImp); calGone = ''; render(); cur().scrollTop = 0; }
    return true;
  }
  if (t.closest('[data-cal-past]')) { calPast = !calPast; render(); return true; }
  if (go) { calOpen.add(go.dataset.calGo); calPend = go.dataset.calGo; calF = ''; ver++; if (tab === 'kalender') render(); else setTab('kalender', { top: true }); return true; }
  if (r) {   // an event opens in place, one at a time; the row stays under the finger
    const id = r.dataset.cal, was = calOpen.has(id), row = r.closest('.ce'), top = row ? row.getBoundingClientRect().top : 0;
    calOpen.clear();
    if (!was) calOpen.add(id);
    render();
    const el = pg$('ce-' + id);
    if (el && row) cur().scrollTop += el.getBoundingClientRect().top - top;
    if (!was && el) keepInView(el);
    return true;
  }
  if (sh) {
    const e = calFind(sh.dataset.calShare || sh.dataset.calCopy);
    if (e) { if (sh.dataset.calShare) share(calText(e)); else if (await copyText(calText(e))) toast('Kopieret'); }
    return true;
  }
  return false;
}

// ---------------------------------------------------------------- Kort: the attacks and fighting in the news, on a map
// SHELVED since 17/10 at the owner's wish ("kassere kortvisningen, eller gemme den"): kept here, but nothing calls it.
// The owner's wish (17/10): a tab of its own, 'a kind of live OSINT with a map and the latest attacks, a little like
// LiveUAmap'. map.json (src/radar/osint.py, on the data branch) holds the radar's stories that say something violent
// happened, placed where their headline says, newest first, 72 hours, one event per place, kind and three hours. The
// map (Leaflet from cdnjs with its cluster plugin, fetched the first time the tab is in view or a swipe heads for it,
// never at the start) fills the page above the dock and stays put while the list scrolls under it; the dock holds the
// zones (a tap flies there and keeps the list to the zone), the time window and the kinds. Zoomed out, events that lie
// close together are one quiet numbered bubble (sized by the count, a red ring only with an event of the last hour);
// a tap on one zooms in, or fans its events out at the closest zoom. A drag on the map pans the map (Leaflet's
// touch-action: none), never the pages; the page around it swipes as every tab does.
const KKINDS = { luft: 'Luftangreb', drone: 'Drone', missil: 'Missil og raket', artilleri: 'Artilleri', eksplosion: 'Eksplosion',
  'sø': 'Til søs', kamp: 'Kampe', angreb: 'Angreb' };
const kGlyph = k => 'k-' + (k === 'sø' ? 'so' : KKINDS[k] ? k : 'angreb');
const KWIN = [[6, '6 timer'], [24, '24 timer'], [72, '3 døgn']];
// the zones (the owner, 17/10: "hvis man trykker på de forskellige zoner, så … flyver til forskellige steder"): each its
// boxes [south, west, north, east]; an event belongs to the first zone that holds it; a tap flies to the zone's boxes
const KZONES = [
  ['gaza', 'Gaza', [[31.21, 34.2, 31.6, 34.58]]],
  ['vb', 'Vestbredden', [[31.33, 34.93, 32.56, 35.6]]],
  ['ls', 'Libanon/Syrien', [[32.6, 35.0, 37.35, 42.4]]],
  ['ii', 'Irak/Iran', [[29.0, 38.8, 39.8, 61.0], [24.0, 48.5, 29.0, 61.0]]],
  ['jr', 'Jemen/Rødehavet', [[12.0, 41.5, 19.5, 54.5], [15.0, 37.5, 22.0, 42.6]]],
  ['ur', 'Ukraine/Rusland', [[43.0, 22.0, 61.0, 52.0]]],
  ['af', 'Afrika', [[-35, -18, 37.3, 32.3], [-35, 32.3, 22.0, 37.5], [-12, 37.5, 12.0, 52.0], [12.0, 37.5, 15.0, 41.5]]],
];
const kZoneOf = e => (KZONES.find(([, , bs]) => bs.some(([s, w, n, o]) => e.la >= s && e.la <= n && e.lo >= w && e.lo <= o)) || [''])[0];
const kZoneName = z => (KZONES.find(x => x[0] === z) || [, ''])[1];
let kWin = (v => (KWIN.some(w => w[0] === v) ? v : 24))(store.get('kortWin', 24));
let kKind = '', kZone = '', kSel = '', kSeen = false, kUser = false;   // a kind and a zone for the visit; the chosen event; seen; the reader moved the map
let kMap = null, kLayer = null, kTiles = null, kDark = null, kMarks = [], kOf = null, kDrawn = '', kBuilt = '', kLeaf = 'idle';
const LEAFLET = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/';
const CLUSTER = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/';
// CARTO's tiles need a key since September 2026 (free for non-commercial use; a person requests it at
// carto.com/basemaps/apikey, pages.yml writes it from the repository variable CARTO_KEY). Without one the map uses
// OpenStreetMap's own tiles, greyed (and turned dark with the app), so it stays as quiet
const OSM = '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';
const CARTO = OSM + ', © <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>';
const kLive = e => Date.now() - new Date(e.p) < 3600e3;   // an event of the last hour: the red 'live' ring
const kWhere = e => `${KKINDS[e.k] || 'Angreb'}, ${e.pl}${e.ca ? ' (omtrentlig placering)' : ''}`;
// Leaflet's files, each asked for once (again only after it failed), the style before the app's own so ours wins
const leafParts = {};
function leafPart(tag, attrs) {
  const key = attrs.href || attrs.src;
  return leafParts[key] ||= new Promise((res, rej) => {
    const el = Object.assign(document.createElement(tag), attrs);
    el.crossOrigin = 'anonymous';
    el.onload = res;
    el.onerror = () => { el.remove(); delete leafParts[key]; rej(new Error(tag)); };
    if (tag === 'link') document.head.insertBefore(el, document.querySelector('link[href^="style.css"]')); else document.head.appendChild(el);
  });
}
// (not 'leaflet': Leaflet's own file takes that global name for itself)
function loadLeaflet() {
  if (kLeaf !== 'ok') kLeaf = 'loading';
  return Promise.all([
    leafPart('link', { rel: 'stylesheet', href: LEAFLET + 'leaflet.min.css', integrity: 'sha256-tXCrvaljxgtN5LT/Syb5Mm9T+yzPFGH98JVcoJT7JTk=' }),
    leafPart('script', { src: LEAFLET + 'leaflet.min.js', async: true, integrity: 'sha256-XJrs/DDkVkUZ29zdzFOkGCJ9zHVo5hnpdi3c7HYJ7Uc=' }),
  ]).then(loadCluster).then(() => { kLeaf = 'ok'; return window.L; }, e => { kLeaf = 'error'; throw e; });
}
// the clusters (Leaflet.markercluster 1.5.3): asked for only once Leaflet is there (the plugin extends Leaflet's L);
// without them the markers stand alone and the map still works
function loadCluster() {
  return Promise.all([
    leafPart('link', { rel: 'stylesheet', href: CLUSTER + 'MarkerCluster.css', integrity: 'sha256-YU3qCpj/P06tdPBJGPax0bm6Q1wltfwjsho5TR4+TYc=' }),
    leafPart('script', { src: CLUSTER + 'leaflet.markercluster.js', async: true, integrity: 'sha256-Hk4dIpcqOSb0hZjgyvFOP+cEmDXUKKNE/tT542ZbNQg=' }),
  ]).catch(() => null);
}
// a swipe on its way to the tab: its file and Leaflet start, so the map is there when the page stands still
function kortWarm() {
  kSeen = true;
  need('map');
  loadLeaflet().catch(() => {});
}
// the tab came into view (a tap, a swipe, a link)
function kortShown() {
  kSeen = true;
  need('map');
  kortPage(pageEl('kort'));
}
// the window's events, newest first, each story once
function kEvents() {
  const m = V('map'), since = Date.now() - kWin * 3600e3, seen = new Set();
  return ((m && Array.isArray(m.events)) ? m.events : [])
    .filter(e => e && e.i && Number.isFinite(e.la) && Number.isFinite(e.lo) && new Date(e.p).getTime() >= since && !seen.has(e.i) && seen.add(e.i))
    .sort((a, b) => new Date(b.p) - new Date(a.p));
}
// on the map: the window's events of the kind chosen; in the list: those of the zone chosen too
const kShown = () => { const all = kEvents(); return kKind ? all.filter(e => e.k === kKind) : all; };
const kListed = () => { const s = kShown(); return kZone ? s.filter(e => kZoneOf(e) === kZone) : s; };
// The page is built once and then filled in parts: the map keeps its elements (a patch of the whole page would take
// Leaflet's away), the list is patched row by row (morph), and a file the same as last time draws nothing
function kortPage(pg) {
  if (!pg) return;
  if (!pg.querySelector('.k-wrap')) {
    pg.innerHTML = '<div class="k-wrap"><div class="k-box" role="region" aria-label="Kort over angreb og kampe"><div class="k-map"></div><div class="k-msg"></div><div class="k-card" hidden></div></div>'
      + '<p class="k-n"></p><div class="k-list"></div></div>';
    kDrawn = ''; kOf = null;
  }
  if (tab === 'kort') kMapUp(pg);
  kortFill(pg);
}
// the map: Leaflet when first needed; with no network or no Leaflet a quiet line in its place and another try
function kMapUp(pg) {
  if (kMap) { kMap.invalidateSize({ pan: false }); return; }
  const msg = pg.querySelector('.k-msg');
  if (kLeaf === 'error') {
    msg.innerHTML = `<p>${netDown() ? 'Ingen forbindelse. Kortet kommer, så snart telefonen er på nettet.' : 'Kortet kunne ikke vises lige nu.'}</p>`
      + '<button class="qbtn" data-kleaf>Prøv igen</button>';
    return;
  }
  msg.innerHTML = '';
  loadLeaflet().then(Lf => { if (!kMap) kInit(Lf, pg); }, () => { if (tab === 'kort') kMapUp(pg); });
}
function kInit(Lf, pg) {
  const el = pg.querySelector('.k-map');
  if (!el || !el.offsetWidth) return;   // the view is hidden: when it is shown
  kMap = Lf.map(el, { zoomControl: false, attributionControl: false, worldCopyJump: true, minZoom: 2, maxZoom: 12, zoomSnap: 0.5,
    fadeAnimation: !reduceMotion, zoomAnimation: !reduceMotion, markerZoomAnimation: !reduceMotion, inertia: !reduceMotion });
  kMap.setView([29, 40], 4, { animate: false });   // the Middle East until the events give the view
  Lf.control.attribution({ position: 'bottomright', prefix: false }).addTo(kMap);   // '© OpenStreetMap © CARTO', small
  // events close together: one bubble with their count (a wide reach zoomed out, so the world shows a handful); a tap
  // zooms in, at the closest zoom it fans them out; Reduce Motion: no animation
  kLayer = (Lf.markerClusterGroup ? Lf.markerClusterGroup({ showCoverageOnHover: false, zoomToBoundsOnClick: true, spiderfyOnMaxZoom: true,
    removeOutsideVisibleBounds: true, animate: !reduceMotion, animateAddingMarkers: false, maxClusterRadius: z => (z <= 4 ? 72 : z <= 7 ? 52 : 36),
    spiderfyDistanceMultiplier: 1.4, spiderLegPolylineOptions: { weight: 1, color: '#8f8f8c', opacity: 0.8 }, iconCreateFunction: kClusterIcon })
    : Lf.layerGroup()).addTo(kMap);
  kMap.on('click', () => kPick(''));
  for (const ev of ['touchstart', 'mousedown', 'wheel']) el.addEventListener(ev, () => { kUser = true; }, { passive: true });
  new ResizeObserver(() => { if (kMap) kMap.invalidateSize({ pan: false }); }).observe(el);   // the dock's rows change the room above it
  kortLook();
  pg.querySelector('.k-msg').innerHTML = '';
  kBuilt = ''; kDrawn = '';
  kortFill(pg);
}
// a bubble: a quiet circle with the count, larger with more events; a red ring only when one is of the last hour
function kClusterIcon(c) {
  const ms = c.getAllChildMarkers(), n = ms.length, live = ms.some(m => m.options.kLive);
  const s = n < 5 ? 32 : n < 15 ? 38 : n < 40 ? 44 : 50;
  return window.L.divIcon({ className: 'kci', iconSize: [s, s], iconAnchor: [s / 2, s / 2],
    html: `<span class="kc" style="--kc:${s}px" role="img" aria-label="${n} hændelser – tryk for at se dem"><b>${n}</b>${live ? '<i class="live-dot"></i>' : ''}</span>` });
}
// The map's ground: OpenFreeMap's vector map (OpenStreetMap's data, free and without a key), drawn by MapLibre inside
// Leaflet, so the app writes the names itself – in Danish where OpenStreetMap has a Danish name, else English – and
// never names Israel (the owner, 17/10: "Kan du fjerne navnet israel på kortet"). Without WebGL, or when its files do
// not come, the German OpenStreetMap server's pictures (with their own names) stand in.
const MAPLIBRE = 'https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.0/dist/';
const OFM = '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> © <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">OpenMapTiles</a> · ' + OSM;
const NO_NAME = ['Israel', 'ישראל', 'إسرائيل', 'State of Israel'];
// the towns of Palestine under their names from before the occupation (the owner, 17/10: "Til byerne skal du bruge de
// originale navne før besættelsen"), matched on OpenStreetMap's English name; config/map-places.json names the map's
// events the same way
const ORIGINAL = {
  'Tel Aviv-Yafo': 'Yafa', 'Tel Aviv': 'Yafa', 'Jaffa': 'Yafa', 'Jerusalem': 'al-Quds', 'Eilat': 'Umm al-Rashrash',
  'Ashkelon': 'Asqalan', 'Ashdod': 'Isdud', 'Beersheba': "Bir al-Sab'", "Be'er Sheva": "Bir al-Sab'", 'Sderot': 'Najd',
  'Kiryat Shmona': 'al-Khalisa', 'Netanya': 'Umm Khalid', 'Lod': 'al-Lydd', 'Ramla': 'al-Ramla', 'Acre': 'Akka',
  'Akko': 'Akka', 'Safed': 'Safad', 'Tiberias': 'Tabariyya', 'Nazareth': 'al-Nasira', "Beit She'an": 'Baysan',
  'Afula': 'al-Fula', 'Rishon LeZion': 'Uyun Qara', 'Petah Tikva': 'Mulabbis', 'Rehovot': 'Duran', 'Herzliya': 'Jalil',
  'Kfar Saba': 'Kafr Saba', 'Yavne': 'Yibna', 'Bat Yam': 'Tall al-Rish', 'Holon': 'Tall al-Rish', 'Hadera': 'al-Khudayra',
  'Golan Heights': 'al-Jawlan', 'Negev': 'al-Naqab', 'Dead Sea': 'Det Døde Hav',
};
const kName = ['case', ['any', ...['name', 'name:en', 'name:da', 'name:latin'].map(k => ['in', ['coalesce', ['get', k], ''], ['literal', NO_NAME]])], '',
  ['match', ['coalesce', ['get', 'name:en'], ['get', 'name:latin'], ''], ...Object.entries(ORIGINAL).flat(),
    ['coalesce', ['get', 'name:da'], ['get', 'name:en'], ['get', 'name:latin'], ['get', 'name']]]];
let kVector = null;   // null: not tried; a promise while loading; false: not possible here
function loadVector() {
  if (kVector !== null) return kVector || Promise.reject(new Error('no vector'));
  const gl = (() => { try { return !!document.createElement('canvas').getContext('webgl2'); } catch { return false; } })();
  if (!gl) { kVector = false; return Promise.reject(new Error('no webgl')); }
  return kVector = Promise.all([
    leafPart('link', { rel: 'stylesheet', href: MAPLIBRE + 'maplibre-gl.css', integrity: 'sha384-Nq6PQ+9vJPvw7U/VfDELyrWoGQMsy0gi6QShhaSrGzkpF5KkM40csg2leky+YMTd' }),
    leafPart('script', { src: MAPLIBRE + 'maplibre-gl.js', async: true, integrity: 'sha384-GfxBM9x46BaAFxtCq39Fxir8fNZ4VDnwgfi6Kzi5/F1tAFsm0amuuV8kd+Pxzuf/' }),
  ]).then(() => leafPart('script', { src: 'https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.3/leaflet-maplibre-gl.js', async: true,
    integrity: 'sha384-LIxE/QjpJKC2A91yD40ZisdYtFbgAjl58jqpo9/MUZNgwhqsTfzwrTlqv6nDdzzB' }))
    .catch(e => { kVector = false; throw e; });
}
const kStyles = {};
function kStyle(dark) {   // OpenFreeMap's style with the app's names on every label
  return kStyles[dark] ||= fetch(`https://tiles.openfreemap.org/styles/${dark ? 'dark' : 'positron'}`).then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(st => {
      for (const l of st.layers || []) if (l.type === 'symbol' && l.layout && l.layout['text-field'] && /name/.test(JSON.stringify(l.layout['text-field']))) l.layout['text-field'] = kName;
      return st;
    }, e => { delete kStyles[dark]; throw e; });
}
// light or dark tiles with the app's look (the setting, else the phone's)
const kDarkNow = () => { const th = document.documentElement.dataset.theme; return th === 'dark' || (th !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches); };
function kortLook() {
  const Lf = window.L;
  if (!kMap || !Lf) return;
  const dark = kDarkNow();
  if (kTiles && dark === kDark) return;
  kDark = dark;
  const put = layer => { if (kDark !== dark || !kMap) return; if (kTiles) kTiles.remove(); kTiles = layer; kTiles.addTo(kMap); };
  const raster = () => CFG.cartoKey
    ? Lf.tileLayer(`https://basemaps.cartocdn.com/rastertiles/${dark ? 'dark_all' : 'light_all'}/{z}/{x}/{y}.png?key=${encodeURIComponent(CFG.cartoKey)}`,
      { maxZoom: 20, attribution: CARTO })
    // OpenStreetMap's German server: place names in Latin letters (Kairo, Damaskus, Teheran), close to Danish
    : Lf.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', { maxZoom: 18, attribution: OSM, className: dark ? 'k-osm dark' : 'k-osm' });
  loadVector().then(() => kStyle(dark)).then(style => {
    if (!Lf.maplibreGL) throw new Error('no plugin');
    put(Lf.maplibreGL({ style, attribution: OFM, interactive: false }));
  }).catch(() => put(raster()));
}
// (when the map returns: matchMedia('(prefers-color-scheme: dark)').addEventListener('change', kortLook) – the tiles' look)
// a marker and a row's glyph: the kind in a small circle; an approximate place a dashed ring, the last hour a red one
const kBadge = (e, live) => `<span class="km${e.ca ? ' ca' : ''}" data-k="${kGlyph(e.k).slice(2)}"><svg aria-hidden="true"><use href="#${kGlyph(e.k)}"/></svg>${live ? '<i class="live-dot"></i>' : ''}</span>`;
function kRow(e) {
  const live = kLive(e), n = e.n || 1;
  const meta = `<span class="src">${esc(e.s)}</span><span>${live ? '<i class="nd"></i>' : ''}${stamp(e.p)}</span>${n >= 3 ? `<span>${n} medier</span>` : ''}`
    + (e.ca ? '<span>omtrentlig placering</span>' : '');
  return `<div class="ke${e.i === kSel ? ' on' : ''}" id="ke-${esc(e.i)}"><div class="row"><button class="hit" data-kev="${esc(e.i)}" aria-label="${esc(`${kWhere(e)}: ${quoteIsrael(e.t)} – ${e.s}, ${stamp(e.p)}`)}"></button>`
    + `${kBadge(e, live)}<span class="tx" aria-hidden="true"><b class="k-pl">${esc(e.pl)}</b><span class="h" dir="auto">${esc(quoteIsrael(e.t))}</span><span class="m">${meta}</span></span></div></div>`;
}
// the dock's two rows for Kort: the zones with their counts in the window (a tap flies there), then the window and – with
// two kinds or more – the kinds as a quiet filter for the visit
function kortOpts() {
  const all = kEvents(), zc = {};
  for (const e of all) { const z = kZoneOf(e); if (z) zc[z] = (zc[z] || 0) + 1; }
  const inZone = kZone ? all.filter(e => kZoneOf(e) === kZone) : all, count = {};
  for (const e of inZone) count[e.k] = (count[e.k] || 0) + 1;
  const ks = Object.keys(KKINDS).filter(k => count[k]);
  const zones = [...KZONES.map(([id, name]) => [id, name, zc[id] || 0]), ['', 'Hele kortet', all.length]];
  return `<div class="o-row" id="o-kort-z" role="radiogroup" aria-label="Område">${zones.map(([id, name, n]) =>
    `<button class="chip${id === kZone ? ' on' : ''}${n ? '' : ' nil'}" role="radio" aria-checked="${id === kZone}" data-kzone="${id}">${esc(name)}<small>${n}</small></button>`).join('')}</div>`
    + `<div class="o-row" id="o-kort-t"><span class="o-grp" role="radiogroup" aria-label="Tidsrum">${KWIN.map(([h, l]) =>
      `<button class="chip${h === kWin ? ' on' : ''}" role="radio" aria-checked="${h === kWin}" data-kwin="${h}">${l}</button>`).join('')}</span>`
    + (ks.length < 2 ? '' : `<i class="sep" aria-hidden="true"></i><span class="o-grp" role="group" aria-label="Type">${ks.map(k =>
      `<button class="chip${k === kKind ? ' on' : ''}" data-kkind="${esc(k)}" aria-pressed="${k === kKind}"><svg aria-hidden="true"><use href="#${kGlyph(k)}"/></svg>${KKINDS[k]}<small>${count[k]}</small></button>`).join('')}</span>`)
    + '</div>';
}
// the Kort view's parts: the count, the rows and the markers (the options are the dock's)
function kortFill(pg) {
  if (!pg || !pg.querySelector('.k-wrap')) return;
  const all = kEvents();
  if (kKind && !all.some(e => e.k === kKind)) kKind = '';
  const shown = kKind ? all.filter(e => e.k === kKind) : all, listed = kZone ? shown.filter(e => kZoneOf(e) === kZone) : shown;
  if (kSel && !shown.some(e => e.i === kSel)) { kSel = ''; kCard(null); }
  if (dockTab === 'kort') paintOpts('kort');
  const sig = [vstate('map'), kSeen, kWin, kKind, kZone, !!kMap, listed.map(e => stamp(e.p) + (kLive(e) ? '!' : '')).join(',')].join('|');
  if (sig === kDrawn && kOf === V('map')) return;
  kDrawn = sig; kOf = V('map');
  const n = listed.length, zn = kZoneName(kZone);
  pg.querySelector('.k-n').textContent = n ? `${n} ${n === 1 ? 'hændelse' : 'hændelser'}${zn ? ' i ' + zn : ''} · seneste ${fromWhen(listed[0].p)}` : '';
  const win = (KWIN.find(w => w[0] === kWin) || KWIN[1])[1];
  const html = !V('map') ? (failed('map') ? retry('kortet', 'map') : loadingBlock('Henter kortet …'))
    : !n ? stateBlock('empty', `Ingen angreb eller kampe${zn ? ' i ' + zn : ''} i nyhederne de seneste ${win}.`,
      [...(kWin < 72 ? [['Se 3 døgn', 'data-kwin="72"']] : []), ...(kZone ? [['Hele kortet', 'data-kzone=""']] : [])])
    : listed.map(kRow).join('');
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  morph(pg.querySelector('.k-list'), tpl.content, []);
  if (kMap && kMarkers(shown) && !kUser) kFit(shown);
}
// the markers, drawn again only when the events or their red rings changed (the reader's view and choice stay); with
// the cluster plugin they go in as one batch, and a marker that comes out of a bubble is marked again when chosen
function kMarkers(shown) {
  const Lf = window.L, key = shown.map(e => e.i + (kLive(e) ? '!' : '')).join(',');
  if (!Lf || key === kBuilt) return false;
  kBuilt = key;
  kLayer.clearLayers();
  kMarks = [];
  const ms = [];
  for (const e of [...shown].reverse()) {   // the oldest first, so the newest lies on top
    const m = Lf.marker([e.la, e.lo], { icon: Lf.divIcon({ className: 'kmi', html: kBadge(e, kLive(e)), iconSize: [26, 26], iconAnchor: [13, 13] }),
      keyboard: true, riseOnHover: false, zIndexOffset: e.i === kSel ? 1000 : 0, kLive: kLive(e) });
    m.on('click', () => kPick(e.i, 'map'));
    m.on('add', () => kPaint(m, e));
    ms.push(m);
    kMarks.push({ e, m });
  }
  if (kLayer.addLayers) kLayer.addLayers(ms); else ms.forEach(m => m.addTo(kLayer));
  return true;
}
function kPaint(m, e) {
  const el = m.getElement(), b = el && el.firstElementChild;
  if (!b) return;
  el.setAttribute('aria-label', `${kWhere(e)}: ${quoteIsrael(e.t)}`);
  b.classList.toggle('on', e.i === kSel);
}
// the default view holds the window's events; one far away does not zoom the map out to the world – the view holds the
// events near the middle of them when those are most, else all ('Hele kortet' flies there; Reduce Motion: no flight)
const kDist = ([a, b], [c, d]) => { const r = Math.PI / 180; return 6371 * Math.hypot((d - b) * r * Math.cos((a + c) / 2 * r), (c - a) * r); };
function kFit(shown, fly) {
  const Lf = window.L;
  if (!kMap || !Lf) return;
  if (!shown.length) { kMap.setView([29, 40], 4, { animate: false }); return; }
  const mid = xs => xs.slice().sort((x, y) => x - y)[xs.length >> 1], c = [mid(shown.map(e => e.la)), mid(shown.map(e => e.lo))];
  const near = shown.filter(e => kDist(c, [e.la, e.lo]) < 2500), use = near.length >= Math.ceil(shown.length * 0.6) ? near : shown;
  const b = Lf.latLngBounds(use.map(e => [e.la, e.lo]));
  if (fly && !reduceMotion) kMap.flyToBounds(b, { padding: [32, 32], maxZoom: 6, duration: 0.8 });
  else kMap.fitBounds(b, { padding: [32, 32], maxZoom: 6, animate: false });
}
// a zone chosen in the dock: the map flies to its boxes (Reduce Motion: straight there) and the list keeps to it;
// 'Hele kortet' gives the default view back
function kZoneTo(z) {
  kZone = KZONES.some(x => x[0] === z) ? z : '';
  if (kSel) kPick('');
  kDrawn = '';
  const pg = pageEl('kort');
  pg.scrollTop = 0;
  kortFill(pg);
  const chip = $('opts').querySelector(`[data-kzone="${kZone}"]`), row = chip && chip.parentElement;   // the chosen zone in view in its row
  if (row) { const c = chip.getBoundingClientRect(), r = row.getBoundingClientRect(); if (c.left < r.left || c.right > r.right) row.scrollLeft += c.left - r.left - 12; }
  if (!kMap || !window.L) return;
  const zn = KZONES.find(x => x[0] === kZone);
  if (!zn) { kUser = false; kFit(kShown(), true); return; }
  kUser = true;   // the zone's view stays until the reader chooses another
  const b = window.L.latLngBounds(zn[2].flatMap(([s, w, n, o]) => [[s, w], [n, o]]));
  if (reduceMotion) kMap.fitBounds(b, { padding: [12, 12], animate: false }); else kMap.flyToBounds(b, { padding: [12, 12], duration: 0.8 });
}
// one event chosen – from its row (the map flies there and opens its bubble; Reduce Motion: no flight) or its marker
// (its row is marked and a small card shows over the map's foot); '' lets go
function kPick(id, from) {
  const pg = pageEl('kort'), e = id ? kShown().find(x => x.i === id) : null;
  kSel = e ? id : '';
  pg.querySelectorAll('.ke.on').forEach(x => x.classList.remove('on'));
  const row = e && pg.querySelector('#' + CSS.escape('ke-' + id));
  if (row) row.classList.add('on');
  for (const { e: x, m } of kMarks) {
    const b = m.getElement() && m.getElement().firstElementChild, on = x.i === kSel;
    if (b && b.classList.contains('on') !== on) b.classList.toggle('on', on);
    m.setZIndexOffset(on ? 1000 : 0);
  }
  kCard(e);
  if (e && from === 'map' && kMap) {   // a marker the card would cover moves up into view
    const room = pg.querySelector('.k-card').offsetTop - 24, y = kMap.latLngToContainerPoint([e.la, e.lo]).y;
    if (y > room) { kUser = true; kMap.panBy([0, y - room / 2], { animate: !reduceMotion }); }
  }
  if (!e || from !== 'row' || !kMap) return;
  kUser = true;
  const z = Math.max(kMap.getZoom(), 7), mk = kMarks.find(x => x.e.i === id);
  const open = () => { if (mk && kLayer.zoomToShowLayer && !mk.m.getElement() && kSel === id) kLayer.zoomToShowLayer(mk.m, () => kPaint(mk.m, e)); };
  if (reduceMotion) { kMap.setView([e.la, e.lo], z, { animate: false }); open(); }
  else { kMap.once('moveend', open); kMap.flyTo([e.la, e.lo], z, { duration: 0.7 }); }
}
function kCard(e) {
  const c = pageEl('kort').querySelector('.k-card');
  if (!c) return;
  c.hidden = !e;
  c.innerHTML = !e ? '' : '<button class="k-x" data-kclose aria-label="Luk"><svg aria-hidden="true"><use href="#i-x"/></svg></button>'
    + `<p class="k-ct" dir="auto">${esc(quoteIsrael(e.t))}</p><div class="m"><span><b>${esc(e.pl)}</b></span><span>${kLive(e) ? '<i class="nd"></i>' : ''}${stamp(e.p)}</span>`
    + `<span class="src">${esc(e.s)}</span>${e.ca ? '<span>omtrentlig placering</span>' : ''}</div><div class="acts">`
    + (e.u ? `<a class="act" href="${esc(e.u)}" target="_blank" rel="noopener"><svg aria-hidden="true"><use href="#i-open"/></svg>Læs</a>` : '')
    + `<button class="act" data-kopen="${esc(e.i)}">Åbn historien</button></div>`;
}
// 'Åbn historien': as a ?item= link does – the story opened in Live, or said to have left it with a way to find it
function kOpenStory(id) {
  focusId = id;
  if (data) openFocus(stories()); else setTab('latest', { top: true });
}
// the Kort tab's own buttons, in its page or in the dock
function kortTap(t) {
  const pg = pageEl('kort'), w = t.closest('[data-kwin]'), k = t.closest('[data-kkind]'), z = t.closest('[data-kzone]'), ev = t.closest('[data-kev]');
  if (z) kZoneTo(z.dataset.kzone);
  else if (w) {   // another window: its events and a view that holds them; the window shown again: the view back
    const h = +w.dataset.kwin;
    if (h !== kWin) { kWin = h; store.set('kortWin', h); }
    kUser = !!kZone; kBuilt = ''; kDrawn = '';
    kortFill(pg);
  } else if (k) { kKind = kKind === k.dataset.kkind ? '' : k.dataset.kkind; kUser = !!kZone; kBuilt = ''; kortFill(pg); }
  else if (ev) kPick(ev.dataset.kev, 'row');
  else if (t.closest('[data-kclose]')) kPick('');
  else if (t.closest('[data-kopen]')) kOpenStory(t.closest('[data-kopen]').dataset.kopen);
  else if (t.closest('[data-kleaf]')) { kLeaf = 'idle'; kMapUp(pg); }
}
list.addEventListener('click', e => {
  const t = e.target, ok = t.closest('[data-okonomi]');
  if (ok) { e.preventDefault(); openOkonomi(); return; }
  if (t.closest('[data-okframe]')) { pageEl('okonomi').innerHTML = ''; okPage(pageEl('okonomi')); return; }
});
// (when the map returns, its taps: the page's '.page[data-tab="kort"]' and the dock's (dataset.for 'kort') go to
// kortTap, Escape lets go of a chosen event (kPick('')), and 'online' tries Leaflet again (kMapUp))
$('sheet').addEventListener('click', e => { if (e.target.closest('[data-okonomi]')) { e.preventDefault(); openOkonomi(); } });
addEventListener('online', () => {
  const ok = pageEl('okonomi');
  if (ok && !ok.querySelector('iframe') && ok.firstElementChild) { ok.innerHTML = ''; if (tab === 'okonomi') okPage(ok); }
});

// ---------------------------------------------------------------- swipe left and right between the tabs
// The tabs lie side by side as pages in one horizontal scroller that snaps to whole pages, so the phone itself carries
// the swipe: the page follows the finger exactly, a flick turns it with the phone's own speed and easing, at the first
// and last tab it gives a little and springs back, and a swipe up or down stays a scroll of the page. Nothing is drawn
// or swapped while it moves (the neighbours are drawn beforehand), so nothing can hop. The pill in the tab bar and the
// title follow along; once the pages stand still, the page in view is the tab.
// Forside · Live · Kalender · Økonomi · Analyser (the pages lie in this order in #list; the map's Kort is shelved)
const SWIPE_TABS = ['home', 'latest', 'kalender', 'okonomi', 'analyses'];
// pages over the tabs, reached from a button or a link and left by a tab or the logo (with its back mark): Udvikling,
// an answer of the amir's, a wiki page, the wiki's index and what is saved; search lies beside the tabs in its own way
const SIDE = new Set(['threads', 'svar', 'begreb', 'begreber', 'gemt']);
// the tab a side page belongs to: it stays selected while the side page is in view (an answer, a page, A–Å: Analyser)
const HOME_OF = { threads: 'home', svar: 'analyses', begreb: 'analyses', begreber: 'analyses', gemt: '' };
const ASIDE = new Set(['search', ...SIDE]);
let settleT = 0, jumping = false, backTo = 'home';   // jumping: the pages moved by a tap on a tab, not by a finger
// the side pages one came through (a story's concept, its answer, an earlier answer …): the logo goes back through them
const backStack = [];
const sideArg = t => t === 'svar' ? svarNr : t === 'begreb' ? begrebId : t === 'threads' ? udFocus : '';
// The phone's own back (Android's button and gesture, a browser's swipe) goes the app's way back: every side page
// opened is a step in the browser's history, and stepping back there is stepping back here. A tab chosen from a side
// page takes those steps away again; the address names the page in view and nothing older.
const BASE = location.pathname + (params.get('dev') ? `?dev=${encodeURIComponent(params.get('dev'))}` : '');
let sideDepth = 0, unwinding = false;
// the address names the page in view: ?svar=, ?begreb=, ?forlob= (a development), ?digest=1 (Udvikling), ?gemt=1
const sideUrl = (t, arg) => {
  const q = t === 'svar' ? `svar=${encodeURIComponent(arg)}` : t === 'begreb' ? `begreb=${encodeURIComponent(arg)}`
    : t === 'threads' ? (arg ? `forlob=${encodeURIComponent(arg)}` : 'digest=1') : t === 'gemt' ? 'gemt=1' : '';
  return q ? BASE + (BASE.includes('?') ? '&' : '?') + q : BASE;
};
try { history.replaceState({ khabar: 'base' }, '', BASE); } catch {}
function openSide(t, arg = '') {
  arg = String(arg || '');
  if (SIDE.has(tab)) {
    if (t === tab && sideArg(t) === arg) { cur().scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); return; }
    backStack.push({ t: tab, arg: sideArg(tab), y: cur().scrollTop });
    if (backStack.length > 40) backStack.shift();
  }
  if (t === 'svar') svarNr = arg; else if (t === 'begreb') begrebId = arg; else if (t === 'threads') { udFocus = arg; if (arg) { udOpen.add(arg); pendingThr = arg; } }
  try { history.pushState({ khabar: 'side', t, arg }, '', sideUrl(t, arg)); sideDepth++; } catch {}
  if (t === tab) { render({ view: true }); if (!pendingThr) cur().scrollTop = 0; } else setTab(t, { top: true });
}
// the logo's back mark: one step back in the browser's history when the side page is a step there, else at once
function goBack() {
  if (sideDepth > 0) { history.back(); return; }
  stepBack();
}
addEventListener('popstate', () => {
  if (unwinding) { unwinding = false; return; }
  if (sideDepth > 0) { sideDepth--; stepBack(); }
});
// a tab from a side page: the side pages' steps leave the browser's history too
function leaveSides() {
  if (sideDepth > 0) { unwinding = true; const n = sideDepth; sideDepth = 0; history.go(-n); }
}
function stepBack() {
  const b = backStack.pop();
  if (!b) { setTab(backTo || 'home'); return; }
  if (b.t === 'svar') svarNr = b.arg; else if (b.t === 'begreb') begrebId = b.arg; else if (b.t === 'threads') udFocus = b.arg;
  pendingThr = '';
  if (b.t === tab) render({ view: true }); else setTab(b.t);
  cur().scrollTop = b.y;
}
list.addEventListener('touchstart', () => { cancelAnimationFrame(glide); touching = true; jumping = false; list.style.scrollSnapType = ''; }, { passive: true });
for (const ev of ['touchend', 'touchcancel']) addEventListener(ev, () => {
  touching = false;
  if (paging) { clearTimeout(settleT); settleT = setTimeout(settle, 140); }
}, { passive: true });
// the title and the tab's bold label follow the page that fills most of the screen, already while it moves
// the tab that is selected: the page in view, or the tab a side page belongs to (an answer, a page, A–Å: Analyser)
const tabOf = t => (SIDE.has(t) ? HOME_OF[t] : t);
const markTabs = t => document.querySelectorAll('.tabs [data-tab]').forEach(x => { const on = String(x.dataset.tab === tabOf(t)); if (x.getAttribute('aria-selected') !== on) x.setAttribute('aria-selected', on); });
const showTitle = t => {
  const s = TITLES[t] || SECTIONS[t];
  if ($('title').textContent !== s) $('title').textContent = s;
  markTabs(t);
};
// a screen reader reads only the page in view: the others are hidden from it (an attribute, no layout)
function hidePages() {
  for (const p of list.querySelectorAll('.page')) { const off = String(p.dataset.tab !== tab); if (p.getAttribute('aria-hidden') !== off) p.setAttribute('aria-hidden', off); }
}
list.addEventListener('scroll', () => {
  if (ASIDE.has(tab) || scrubbing) return;   // sliding along the tab bar places the pill itself
  if (!jumping) paging = true;   // a finger or a trackpad; a tap on a tab has placed the pill itself
  if (paging) {
    const n = SWIPE_TABS.length, k = Math.max(0, Math.min(n - 1, list.scrollLeft / list.clientWidth)), i = Math.min(n - 2, Math.floor(k));
    pillBetween(SWIPE_TABS[i], SWIPE_TABS[i + 1], k - i);
    showTitle(SWIPE_TABS[Math.round(k)]);
    paintOpts(SWIPE_TABS[Math.round(k)]);   // the dock's options follow the page that fills most of the screen
    if (Math.abs(k - SWIPE_TABS.indexOf('kalender')) < 1) { need('cal'); need('kal'); }   // on its way: the calendar's files
    if (Math.abs(k - SWIPE_TABS.indexOf('okonomi')) < 1) okPage(pageEl('okonomi'));   // on its way: the frame starts
  }
  clearTimeout(settleT); settleT = setTimeout(settle, 140);
}, { passive: true });
if ('onscrollend' in window) list.addEventListener('scrollend', () => { clearTimeout(settleT); settle(); });
function settle() {
  if (touching || scrubbing || ASIDE.has(tab)) return;   // a finger still holds the pages
  const W = list.clientWidth, i = Math.round(list.scrollLeft / W);
  if (Math.abs(list.scrollLeft - i * W) > 2) {   // stopped between two pages: the snap points take it home (or, failing that, we do)
    if (list.style.scrollSnapType) list.style.scrollSnapType = ''; else list.scrollTo({ left: i * W, behavior: reduceMotion ? 'auto' : 'smooth' });
    clearTimeout(settleT); settleT = setTimeout(settle, 400); return;
  }
  list.style.scrollSnapType = '';
  const t = SWIPE_TABS[i];
  paging = false; jumping = false;
  if (t && t !== tab) setTab(t, { swipe: true }); else { placePill(tab, true); showTitle(tab); paintOpts(tab); }
}
// a tab chosen by a tap (or a link to another tab): the pages go straight there; the pill glides, the page fades in
function showPage(t) {
  const i = SWIPE_TABS.indexOf(t);
  if (i >= 0 && Math.abs(list.scrollLeft - i * list.clientWidth) > 1) { jumping = true; list.scrollLeft = i * list.clientWidth; }
}
addEventListener('resize', () => { if (!ASIDE.has(tab)) showPage(tab); });

// ---------------------------------------------------------------- tabs + search
function setTab(next, opts = {}) {
  if (next === tab) {
    if (tab === 'search') $('search').focus({ preventScroll: true }); else cur().scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    return;
  }
  seenTab[tab] = Date.now(); seenTab[next] = Date.now(); store.set('seenTab', seenTab);
  const was = tab;
  if (was === 'search') rememberQuery();   // the search one leaves is one of the last five
  tab = next;
  if (visit) visit.tabs[tab] = (visit.tabs[tab] || 0) + 1;
  markTabs(tab);
  fadeCatchUp();
  if (focusMissing && tab !== 'latest') focusMissing = '';
  placePill(tab, true);
  $('title').textContent = TITLES[tab] || SECTIONS[tab];
  // a swipe has its own motion; a tap lets the new title come up (opacity and transform only, no forced layout)
  if (!opts.swipe && !reduceMotion) $('title').animate([{ opacity: 0, transform: 'translateY(4px)' }, { opacity: 1, transform: 'none' }], { duration: 280, easing: 'cubic-bezier(.16, 1, .3, 1)' });
  $('searchbar').hidden = tab !== 'search';
  // searching: the field sits under the top bar, the page stands still and only the results scroll, so the phone has
  // no reason to push the page up when the keyboard comes
  document.documentElement.classList.toggle('searching', tab === 'search');
  document.documentElement.classList.toggle('aside', SIDE.has(tab));
  $('openSaved').classList.toggle('on', tab === 'gemt'); $('openSearch').classList.toggle('on', tab === 'search');
  document.querySelectorAll('.page.side').forEach(p => p.classList.toggle('on', p.dataset.tab === tab));
  if (SIDE.has(tab) && !ASIDE.has(was)) backTo = was;
  if (!SIDE.has(tab)) { backStack.length = 0; leaveSides(); }   // a tab: the way back starts afresh
  if (tab === 'analyses') { markAnswersSeen(); prefetchLibrary(); }
  if (tab === 'search') { loadIndex(); cur().scrollTop = 0; setTimeout(() => $('search').focus({ preventScroll: true }), 60); } else $('search').blur();
  hidePages();
  $('freshPill').hidden = true;
  paintOpts(tab);
  if (tab === 'kalender') { need('cal'); need('kal'); calShown(); }
  if (tab === 'okonomi') okPage(pageEl('okonomi'));
  if (opts.swipe) {   // the page is in view already, drawn beforehand: only what is around it follows
    if (!cur().dataset.ver) draw(tab);
    if (data) renderDots(stories());
    drawSoon();
  } else {
    // a tab page drawn since the last change (the neighbours are drawn ahead) is only shown, not drawn again
    if (!SIDE.has(tab) && tab !== 'search' && +cur().dataset.ver === ver) {
      if (!reduceMotion && cur().firstElementChild) cur().firstElementChild.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease-out' });
      if (data) renderDots(stories());
      drawSoon();
    } else render({ view: true });
    if (opts.top) cur().scrollTop = 0;
    showPage(tab);
  }
  onPageScroll();
  hintSeen();
}
// a story that has left Live: its headline is looked for among everything the radar read in two days
async function findGone(id) {
  setTab('search', { top: true });
  await loadIndex();
  const x = searchIndex && searchIndex.items.find(y => y.i === id);
  query = x ? (danish && x.da) || x.t : ''; $('search').value = query; searchScope = 'nyheder';
  render();
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
$('tabs').addEventListener('click', e => {
  if (scrubbed) { scrubbed = false; return; }   // a slide along the bar has chosen already
  const b = e.target.closest('[data-tab]'); if (b) setTab(b.dataset.tab, { top: b.dataset.tab === tab });
});

// ---------------------------------------------------------------- the tab bar: one pill that glides
// The selected tab is marked by one pill behind its icon. It glides to a tapped tab, follows a page swipe part of the
// way, and one can put a finger on the bar and slide along it: the pill follows the finger, the tab under it lights
// up (a light tick on phones that have it), and lifting the finger opens that tab.
const tabsEl = $('tabs'), pill = document.createElement('i');
pill.className = 'tab-pill'; pill.setAttribute('aria-hidden', 'true'); tabsEl.prepend(pill);
const tabBtn = t => tabsEl.querySelector(`[data-tab="${t}"]`);
// the pill's place under each tab's icon, relative to the bar: measured once (and again when the bar changes size), so
// neither a tap nor a swipe makes the browser lay out the page to ask
let pillPos = null;
function pillX(t) {
  if (!pillPos) {
    const n = tabsEl.getBoundingClientRect();
    if (!n.width) return null;   // the tabs are hidden (the keyboard is up)
    pillPos = {};
    for (const b of tabsEl.querySelectorAll('[data-tab]')) {
      const r = b.querySelector('svg').getBoundingClientRect();
      pillPos[b.dataset.tab] = { x: r.left - n.left + r.width / 2 - pill.offsetWidth / 2, y: r.top - n.top + r.height / 2 - pill.offsetHeight / 2 };
    }
  }
  return tabBtn(t) ? pillPos[t] || null : null;
}
new ResizeObserver(() => { pillPos = null; placePill(tab, false); }).observe(tabsEl);
function movePill(x, y, animate) {
  pill.style.transition = animate && !reduceMotion ? 'transform .38s cubic-bezier(.3,1.25,.4,1)' : 'none';
  pill.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0)`;
  pill.style.opacity = 1;
}
function placePill(t, animate) {
  const p = pillX(tabOf(t));
  if (p) movePill(p.x, p.y, animate); else pill.style.opacity = 0;   // the search page and Gemt have no tab
}
addEventListener('resize', () => { pillPos = null; placePill(tab, false); });
requestAnimationFrame(() => placePill(tab, false));
setTimeout(() => { pillPos = null; placePill(tab, false); }, 300);   // once the fonts have set the labels
// a page swipe takes the pill along between the two tabs
function pillBetween(a, b, k) {
  const p = pillX(a), q = pillX(b);
  if (p && q) movePill(p.x + (q.x - p.x) * k, p.y, false);
}
let scrub = null, scrubbed = false;
const tabAt = x => { const bs = [...tabsEl.querySelectorAll('[data-tab]')].filter(b => !b.hidden);
  return bs.reduce((best, b) => { const r = b.getBoundingClientRect(), d = Math.abs(x - (r.left + r.width / 2)); return !best || d < best.d ? { b, d } : best; }, null).b; };
tabsEl.addEventListener('touchstart', e => { scrub = { x: e.touches[0].clientX, moved: false, over: tab }; }, { passive: true });
tabsEl.addEventListener('touchmove', e => {
  if (!scrub) return;
  const x = e.touches[0].clientX;
  if (!scrub.moved && Math.abs(x - scrub.x) < 8) return;
  scrub.moved = true;
  e.preventDefault();
  const bs = [...tabsEl.querySelectorAll('[data-tab]')].filter(b => !b.hidden), n = tabsEl.getBoundingClientRect();
  const first = pillX(bs[0].dataset.tab), last = pillX(bs[bs.length - 1].dataset.tab);
  const px = Math.min(last.x, Math.max(first.x, x - n.left - pill.offsetWidth / 2));
  movePill(px, first.y, false);
  // the pages follow along: as far between two tabs as the pill is (no snapping while the finger leads them)
  if (!ASIDE.has(tab)) {
    if (!scrubbing) { scrubbing = true; list.style.scrollSnapType = 'none'; }
    list.scrollLeft = (px - first.x) / Math.max(1, last.x - first.x) * (bs.length - 1) * list.clientWidth;
  }
  const over = tabAt(x).dataset.tab;
  if (over !== scrub.over) {
    scrub.over = over;
    tabsEl.querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('scrub', b.dataset.tab === over));
    if (scrubbing) showTitle(over);
    if (navigator.vibrate) navigator.vibrate(4);
  }
}, { passive: false });
tabsEl.addEventListener('touchend', () => {
  if (!scrub) return;
  const { moved, over } = scrub;
  scrub = null;
  tabsEl.querySelectorAll('.scrub').forEach(b => b.classList.remove('scrub'));
  if (!moved) return;   // a plain tap: the click does it
  scrubbed = true; setTimeout(() => { scrubbed = false; }, 400);
  if (!scrubbing) { if (over !== tab) setTab(over, { top: false }); else placePill(tab, true); return; }   // from the search page
  glideTo(over);
});
tabsEl.addEventListener('touchcancel', () => { scrub = null; tabsEl.querySelectorAll('.scrub').forEach(b => b.classList.remove('scrub')); if (scrubbing) glideTo(tab); else placePill(tab, true); });
// the finger lifts: the pages snap to the nearest tab – the one under the finger – in a fifth of a second, and that is
// the tab (as after a swipe). Our own short motion, not the browser's smooth scrolling, which on iPhone can crawl.
let glide = 0;
function glideTo(t) {
  scrubbing = false;
  cancelAnimationFrame(glide);
  const W = list.clientWidth, from = list.scrollLeft, to = Math.max(0, SWIPE_TABS.indexOf(t)) * W;
  const ms = reduceMotion ? 0 : Math.round(140 + 80 * Math.min(1, Math.abs(to - from) / W));
  placePill(t, true); showTitle(t);
  jumping = true;   // the pill is placed; the pages only follow
  const t0 = performance.now();
  const step = now => {
    const k = ms ? Math.min(1, (now - t0) / ms) : 1;
    list.scrollLeft = from + (to - from) * (1 - Math.pow(1 - k, 3));   // fast, then easing in
    if (k < 1) { glide = requestAnimationFrame(step); return; }
    list.style.scrollSnapType = '';
    clearTimeout(settleT); settle();
  };
  step(t0);
}
// the bar's magnifier opens the one search with the scope that fits the page: Svar from the movement's pages
$('openSearch').addEventListener('click', () => { if (tab !== 'search') searchScope = ['analyses', 'svar', 'begreb', 'begreber'].includes(tab) ? 'svar' : 'alle'; setTab('search', { top: true }); });
// the bar's bookmark opens what is saved, from every page
$('openSaved').addEventListener('click', () => openSide('gemt'));
paintSaved();
let typing;
$('search').addEventListener('input', e => { clearTimeout(typing); typing = setTimeout(() => { query = e.target.value; render(); }, 60); });
$('search').addEventListener('keydown', e => { if (e.key === 'Enter') $('search').blur(); });
$('searchClear').addEventListener('click', () => { query = ''; $('search').value = ''; $('search').focus({ preventScroll: true }); render(); });
// Analyser's own search field: only its list is drawn again, so the field keeps its keyboard
list.addEventListener('input', e => {
  if (e.target.id !== 'anQ') return;
  clearTimeout(anT);
  anT = setTimeout(() => {
    anT = 0;
    anQuery = e.target.value;
    const pg = pageEl('analyses'), l = pg.querySelector('.an-list');
    if (l) l.innerHTML = analysesList();
    if (dockTab === 'analyses') paintOpts('analyses');
  }, 80);
});
list.addEventListener('keydown', e => { if (e.target.id === 'anQ' && e.key === 'Enter') e.target.blur(); });
$('status').addEventListener('click', () => { renderHeader('opdaterer …'); load(true); });

// keep the dock (search field + tabs) right above the keyboard, and tell the layout how tall the visible part is.
// On iPhone the page can slide under an open keyboard when it is scrolled, so this follows the visible area's every
// move (scroll as well as resize); --vvh is the height one can actually see, which in the browsers inside Messenger
// or a text message is less than the screen (their own bars cover the rest)
const vv = window.visualViewport;
let vvFrame = 0;
function syncViewport() {
  vvFrame = 0;
  const h = vv ? vv.height : innerHeight, kb = vv ? Math.max(0, innerHeight - vv.height - vv.offsetTop) : 0;
  const root = document.documentElement.style;
  root.setProperty('--kb', kb + 'px');
  root.setProperty('--vvh', h + 'px');
  document.body.classList.toggle('keyboard', kb > 40);
}
const queueViewport = () => { if (!vvFrame) vvFrame = requestAnimationFrame(syncViewport); };
if (vv) { vv.addEventListener('resize', queueViewport); vv.addEventListener('scroll', queueViewport); }
addEventListener('resize', queueViewport);
syncViewport();
setTimeout(loadArchive, 1500);   // the earlier days: for 'Følg udviklingen' across days
if (params.get('q')) { query = params.get('q'); $('search').value = query; }
new ResizeObserver(() => document.documentElement.style.setProperty('--dock', $('dock').offsetHeight + 'px')).observe($('dock'));

// what counts as seen moves on only after a real break (10 minutes): a quick trip to WhatsApp to paste a story
// must not mark everything as seen
function backFromBreak() {
  const away = store.get('hiddenAt', 0);
  noteBreak(away);   // three hours and more: 'Mens du var væk' under the lede
  if (away && Date.now() - away > 10 * 60e3 && away > lastSeen) { lastSeen = away; store.set('lastSeen', lastSeen); }
}
backFromBreak();   // also when the phone closed the app in the background and it starts afresh
// a new version of the app: phones keep it open in the background for days, so on coming back it asks for the newest
// page and, if that names other files than the ones running, starts afresh with them (once per version)
const myVer = ((document.querySelector('script[src*="app.js"]') || {}).src || '').split('v=')[1];
async function checkVersion() {
  try {
    const v = ((await (await fetch('./', { cache: 'no-cache' })).text()).match(/app\.js\?v=([\w-]+)/) || [])[1];
    if (!v || !myVer || v === myVer || sessionStorage.getItem('reloadedFor') === v) return;
    sessionStorage.setItem('reloadedFor', v);
    location.reload();
  } catch { /* offline: the version one has will do */ }
}
// iPhone draws the app in light and in dark for its app switcher while it is away, and the phone may switch look on
// its own: no colour may glide back in front of the user
let stillT = 0;
function holdStill(ms) {
  document.documentElement.classList.add('still');
  clearTimeout(stillT);
  if (ms) stillT = setTimeout(() => document.documentElement.classList.remove('still'), ms);
}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => holdStill(document.hidden ? 0 : 600));
let awaySince = 0;
document.addEventListener('visibilitychange', () => {
  holdStill(document.hidden ? 0 : 600);
  if (document.hidden) { store.set('hiddenAt', Date.now()); seenTab[tab] = Date.now(); store.set('seenTab', seenTab); awaySince = Date.now(); countLeave(); return; }
  backFromBreak();
  if (catchUp && !catchUp.done && tab === 'home') staleOn(['home']);
  load();
  checkVersion();
  if (Date.now() - awaySince > 30 * 60e3) countVisit('resume');   // back after half an hour or more: a new opening
  else visit = { at: Date.now(), tabs: {}, opened: 0 };            // a short trip (to WhatsApp, say): the same one goes on
});
setInterval(() => { if (!document.hidden) load(); }, 120000);
setInterval(renderHeader, 30000);
// the network comes back: the news at once (a first start without a connection fills in by itself), every file that
// could not be fetched again, and a notification choice that could not be sent
addEventListener('online', () => load(true));
addEventListener('online', () => { for (const [k, x] of Object.entries(vd)) if (x.state === 'error') { x.state = 'idle'; need(k); } resendWant(); });
setTimeout(() => { if (!data) render(); }, 4100);   // the skeleton rows show at most four seconds

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
  $('adminStats').hidden = !adminKey;
  if (adminKey) showStats();
  // the library on the phone: the answers and the wiki, once both whole files have come
  const built = (V('mix') || {}).built;
  $('libHint').hidden = !(built && store.get('libFor', '') === built);
  if (built) $('libHint').textContent = `Svarene og begreberne er gemt på telefonen · opdateret ${dSlash(built).replace(/\/\d{4}$/, '')}`;
  $('sheet').hidden = false;
  $('sheetScroll').scrollTop = 0;
  void $('sheet').offsetHeight;
  $('sheet').classList.add('on'); $('scrim').classList.add('on');
  refreshPushInfo();
}
// ---------------------------------------------------------------- the owner's statistics (in the settings, admin only)
// The radar keeps the counts encrypted with a key made from the admin code (stats.py); only this phone can read them.
const ZONES = { 'Europe/Copenhagen': 'Danmark', 'Atlantic/Faroe': 'Færøerne', 'America/Nuuk': 'Grønland', 'America/Godthab': 'Grønland',
  'Europe/Stockholm': 'Sverige', 'Europe/Oslo': 'Norge', 'Europe/Helsinki': 'Finland', 'Europe/Berlin': 'Tyskland', 'Europe/Amsterdam': 'Holland',
  'Europe/Brussels': 'Belgien', 'Europe/Paris': 'Frankrig', 'Europe/London': 'Storbritannien', 'Europe/Dublin': 'Irland', 'Europe/Vienna': 'Østrig',
  'Europe/Zurich': 'Schweiz', 'Europe/Madrid': 'Spanien', 'Europe/Rome': 'Italien', 'Europe/Warsaw': 'Polen', 'Europe/Istanbul': 'Tyrkiet',
  'Asia/Gaza': 'Palæstina', 'Asia/Hebron': 'Palæstina', 'Asia/Jerusalem': 'Palæstina/Israel', 'Asia/Amman': 'Jordan', 'Asia/Beirut': 'Libanon',
  'Asia/Damascus': 'Syrien', 'Asia/Baghdad': 'Irak', 'Asia/Riyadh': 'Saudi-Arabien', 'Asia/Dubai': 'Emiraterne', 'Asia/Qatar': 'Qatar',
  'Asia/Kuwait': 'Kuwait', 'Asia/Bahrain': 'Bahrain', 'Asia/Muscat': 'Oman', 'Asia/Aden': 'Yemen', 'Asia/Tehran': 'Iran', 'Asia/Kabul': 'Afghanistan',
  'Asia/Karachi': 'Pakistan', 'Asia/Kolkata': 'Indien', 'Asia/Dhaka': 'Bangladesh', 'Asia/Jakarta': 'Indonesien', 'Asia/Kuala_Lumpur': 'Malaysia',
  'Africa/Cairo': 'Egypten', 'Africa/Casablanca': 'Marokko', 'Africa/Tunis': 'Tunesien', 'Africa/Algiers': 'Algeriet', 'Africa/Tripoli': 'Libyen',
  'Africa/Khartoum': 'Sudan', 'Africa/Mogadishu': 'Somalia', 'Africa/Nairobi': 'Kenya', 'America/New_York': 'USA', 'America/Chicago': 'USA',
  'America/Los_Angeles': 'USA', 'America/Toronto': 'Canada' };
const LANGS = { da: 'Dansk', ar: 'Arabisk', en: 'Engelsk', tr: 'Tyrkisk', ur: 'Urdu', so: 'Somali', fa: 'Persisk', ps: 'Pashto', ku: 'Kurdisk',
  de: 'Tysk', sv: 'Svensk', nb: 'Norsk', no: 'Norsk', nn: 'Norsk', fr: 'Fransk', bs: 'Bosnisk', sq: 'Albansk', es: 'Spansk', it: 'Italiensk' };
const VIA_NAMES = { push: 'En notifikation', whatsapp: 'WhatsApp', facebook: 'Facebook / Messenger', google: 'Google', sms: 'En sms',
  web: 'Andre sider', direct: 'Direkte (ikon eller bogmærke)' };
const TAB_NAMES = { home: 'Forside', dk: 'Danmark', me: 'Mellemøsten', world: 'Verden', threads: 'Udvikling', latest: 'Live', search: 'Søg',
  analyses: 'Analyser', svar: 'Et svar', begreb: 'Leksikon', begreber: 'Leksikon A–Å' };
async function loadStats() {
  const url = CFG.statsUrl || (CFG.dataUrl || '').replace(/data\.json.*$/, 'stats.enc');
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error('none');
  const raw = Uint8Array.from(atob((await r.text()).trim()), c => c.charCodeAt(0));
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('khabar-stats|' + adminKey.trim().toLowerCase()));
  const key = await crypto.subtle.importKey('raw', hash, 'AES-GCM', false, ['decrypt']);
  let plain;
  try { plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: raw.slice(0, 12) }, key, raw.slice(12)); } catch { throw new Error('key'); }
  return JSON.parse(new TextDecoder().decode(plain));
}
async function showStats() {
  const box = $('adminStats');
  box.innerHTML = '<h3>Statistik · kun for dig</h3><p class="hint">Henter …</p>';
  try { box.innerHTML = statsHtml(await loadStats()); } catch (e) {
    box.innerHTML = '<h3>Statistik · kun for dig</h3><p class="hint">' + (e.message === 'key'
      ? 'Statistikken kunne ikke låses op med din admin-kode.'
      : e.message === 'none' ? 'Ingen statistik endnu – den kommer med radarens næste kørsel efter de første besøg.'
      : 'Kunne ikke hente statistikken lige nu.') + '</p>';
  }
}
function statsHtml(st) {
  const fmt = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Copenhagen' });   // YYYY-MM-DD, the Danish day
  const keys = n => [...Array(n)].map((_, k) => fmt.format(new Date(Date.now() - k * 864e5))).reverse();
  const D = st.days || {}, day = k => D[k] || {};
  const sum = (ds, f) => ds.reduce((a, d) => a + (d[f] || 0), 0);
  const merge = (ds, f) => ds.reduce((m, d) => { for (const [k, v] of Object.entries(d[f] || {})) m[k] = (m[k] || 0) + v; return m; }, {});
  const total = o => Object.values(o).reduce((a, b) => a + b, 0);
  const today = day(keys(1)[0]), w = keys(7).map(day), m = keys(30).map(day), all = Object.values(D);
  const n = x => Number(x || 0).toLocaleString('da-DK');
  const pct = (a, b) => b ? Math.round(100 * a / b) + ' %' : '–';
  const rows = (pairs, of) => pairs.map(([label, v]) => `<div class="st-row"><span>${esc(label)}</span><span>${n(v)} · ${pct(v, of)}</span>`
    + `<em><i style="width:${of ? Math.round(100 * v / of) : 0}%"></i></em></div>`).join('');
  const ranked = (obj, name, k = 6) => Object.entries(Object.entries(obj).reduce((a, [key, v]) => { const l = name(key); a[l] = (a[l] || 0) + v; return a; }, {}))
    .sort((a, b) => b[1] - a[1]).slice(0, k);
  let h = '<h3>Statistik · kun for dig</h3>';
  if (!all.length) return h + '<p class="hint">Ingen åbninger talt endnu. De kommer, når radaren har kørt efter de første besøg (hvert 5. minut).</p>';
  const wOpens = sum(w, 'opens');
  h += `<div class="st-big"><div><b>${n(today.opens)}</b><span>åbninger i dag</span></div><div><b>${n(wOpens)}</b><span>7 dage</span></div>`
    + `<div><b>${n(sum(m, 'opens'))}</b><span>30 dage</span></div></div>`;
  h += `<p class="hint">Nye brugere: <b>${n(today.new)}</b> i dag · <b>${n(sum(w, 'new'))}</b> på 7 dage · <b>${n(sum(all, 'new'))}</b> i alt.`
    + ` Notifikationer: <b>${n(st.phones)}</b> telefoner.</p>`;
  // the last 14 days, today the darkest
  const k14 = keys(14), top14 = Math.max(1, ...k14.map(k => day(k).opens || 0));
  h += '<h4 class="st-h">Åbninger pr. dag</h4><div class="st-bars">' + k14.map((k, i) => { const v = day(k).opens || 0;
    return `<i class="${i === 13 ? 'on' : ''}" style="height:${Math.max(2, Math.round(80 * v / top14))}%"><b>${v || ''}</b></i>`; }).join('') + '</div>'
    + '<div class="st-axis">' + k14.map(k => `<span>${'smtotfl'[new Date(k + 'T12:00').getDay()]}</span>`).join('') + '</div>';
  // the hours of the day (7 days)
  const hours = [...Array(24)].map((_, i) => w.reduce((a, d) => a + ((d.h || [])[i] || 0), 0)), topH = Math.max(1, ...hours);
  const peak = hours.indexOf(Math.max(...hours)), hh = x => String(x).padStart(2, '0');
  h += `<h4 class="st-h">Hvornår (7 dage)${wOpens ? ` – mest kl. ${hh(peak)}–${hh((peak + 1) % 24)}` : ''}</h4>`
    + '<div class="st-bars hours">' + hours.map(v => `<i style="height:${Math.max(2, Math.round(100 * v / topH))}%"></i>`).join('') + '</div>'
    + '<div class="st-axis hours"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div>';
  if (wOpens) {
    h += '<h4 class="st-h">Hvordan (7 dage)</h4>' + rows([['Fra hjemmeskærmen', sum(w, 'app')], ['I en browser', wOpens - sum(w, 'app')]], wOpens)
      + rows([['iPhone', sum(w, 'ios')], ['Android', sum(w, 'android')], ['Andet', sum(w, 'other')]].filter(r => r[1]), wOpens);
    const tz = merge(w, 'tz');
    if (total(tz)) h += '<h4 class="st-h">Land – efter telefonens tidszone</h4>' + rows(ranked(tz, z => ZONES[z] || z.split('/').pop().replace(/_/g, ' ')), total(tz));
    const lang = merge(w, 'lang');
    if (total(lang)) h += '<h4 class="st-h">Telefonens sprog</h4>' + rows(ranked(lang, l => LANGS[l] || l), total(lang));
    const via = merge(w, 'via');
    delete via.resume;
    if (total(via)) h += '<h4 class="st-h">Kom ind via</h4>' + rows(ranked(via, v => VIA_NAMES[v] || v), total(via));
  }
  const secs = sum(w, 'secs');
  if (sum(w, 'stays')) {
    const tabs = merge(w, 'tabs'), per = x => n(Math.round(x / Math.max(1, wOpens) * 10) / 10);
    h += `<h4 class="st-h">Tid i appen (7 dage)</h4><p class="hint">I alt <b>${n(Math.round(secs / 60))} min</b> · ca. <b>${per(secs / 60)} min</b> pr. åbning`
      + ` · <b>${per(sum(w, 'opened'))}</b> historier foldet ud pr. åbning.</p>`;
    if (total(tabs)) h += '<h4 class="st-h">Faner der bliver set</h4>' + rows(ranked(tabs, t => TAB_NAMES[t] || t, 7), total(tabs));
  }
  const top = w.reduce((a, d) => { for (const [id, [title, r, s]] of Object.entries(d.top || {})) { const x = a[id] ||= [title, 0, 0]; x[1] += r; x[2] += s; } return a; }, {});
  const best = Object.values(top).sort((a, b) => (b[1] + 2 * b[2]) - (a[1] + 2 * a[2])).slice(0, 8);
  if (best.length) h += '<h4 class="st-h">Mest læste og delte (7 dage)</h4><ol class="st-top">' + best.map(([title, r, s]) =>
    `<li><span dir="auto">${esc(title)}</span><small>${r ? `${n(r)} læst` : ''}${r && s ? ' · ' : ''}${s ? `${n(s)} delt` : ''}</small></li>`).join('') + '</ol>';
  const since = st.since ? new Date(st.since + 'T12:00').toLocaleDateString('da-DK', { day: 'numeric', month: 'long' }) : '';
  return h + '<p class="hint st-foot">Tallene er åbninger, ikke personer – telefonerne gemmer intet til det, og ingen mærker noget. Land kommer af '
    + 'telefonens tidszone (hvor i Danmark kan ikke ses uden at spørge brugeren). Din egen telefon tælles ikke med.'
    + `${since ? ` Talt siden ${since}.` : ''}${st.updated ? ` Opdateret kl. ${clock(st.updated)}.` : ''}</p>`;
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
const goHome = () => (SIDE.has(tab) ? goBack() : setTab('home', { top: true }));   // from a side page: back
brand.addEventListener('click', () => { if (logoHeld) { logoHeld = false; return; } goHome(); });
brand.addEventListener('keydown', e => { if (e.key === 'Enter') goHome(); });
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
const READING = '.sum, .lede-t, .ht-box p.ht, .rd-q, .rd-reads p.ht, .rd-text .ht, .wk-lead p.ht, .wk-tl p.ht';   // text one may select (style.css)
$('list').addEventListener('pointerdown', e => {
  const el = adminKey && !e.target.closest(READING) && (e.target.closest('[data-pick]') || e.target.closest('.story[data-id]'));
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
document.addEventListener('scroll', cancelPress, { capture: true, passive: true });
// the tap that ends a long press must not also open the story
$('list').addEventListener('click', e => { if (pressed) { pressed = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
$('list').addEventListener('contextmenu', e => { if (adminKey && !e.target.closest(READING) && e.target.closest('.story, [data-pick]')) e.preventDefault(); });

// the middle mouse button on a PC scrolls the page, as browsers do on ordinary pages (they do not on our fixed pager):
// hold it and move, or click it and move – the further from where it began, the faster; any click or Esc stops it.
// It works anywhere in the window, also beside the app's column on a wide screen, and so does the wheel.
let auto = null, swallow = false;
const ownScroller = el => {   // something under the mouse that scrolls by itself (a sheet, a box) – leave it be
  for (; el && el !== document.body; el = el.parentElement) {
    if (el.classList.contains('page')) return null;
    if (el.scrollHeight > el.clientHeight + 2 && /auto|scroll/.test(getComputedStyle(el).overflowY)) return el;
  }
  return null;
};
const pageFree = () => !$('scrim').classList.contains('on');
// A sideways row of chips fades out at the side where more lies beyond it (the owner, 18/10: 'den vandrette scrollbare
// emneliste fader ikke ud i siderne, burde den gøre på alle sider'); worked out when a row is drawn and as it scrolls
const SIDEWAYS = '.o-row, .an-chips';
function edges(row) {
  const more = row.scrollWidth > row.clientWidth + 1, x = row.scrollLeft, end = row.scrollWidth - row.clientWidth;
  row.classList.toggle('fade-l', more && x > 2);
  row.classList.toggle('fade-r', more && x < end - 2);
}
const edgesIn = root => { for (const r of root.querySelectorAll(SIDEWAYS)) edges(r); };
document.addEventListener('scroll', e => { const el = e.target; if (el instanceof Element && el.matches(SIDEWAYS)) edges(el); }, { capture: true, passive: true });
addEventListener('resize', () => edgesIn(document));
// A–Å's letters show once the list itself is reached – not beside the header and the most used pages above it (the
// owner, 18/10: 'ser lidt uprofessionelt ud med alfabetet i højre side, ligner en eftertanke')
let azIO = null;
function azWatch(pg) {
  const first = pg.querySelector('.az-at'), idx = pg.querySelector('.az-idx');
  if (azIO) azIO.disconnect();
  if (!first || !idx) return;
  azIO = new IntersectionObserver(es => { for (const e of es) idx.classList.toggle('on', e.boundingClientRect.top < innerHeight * 0.55); },
    { threshold: [0, 1], rootMargin: '0px 0px -45% 0px' });
  azIO.observe(first);
}
// A–Å's letter column (the owner, 18/10: 'ligesom når man scroller i en telefonbog på iphone … holde fingeren nede og
// slide … et stort bogstav på midten som fader ud efter et halv sekund når man står stille med fingeren'): a press
// jumps to its letter, a slide runs through them, each step at once (no smooth scroll); the large letter fades half a
// second after the last change, also while the finger rests. Keyboard: Enter on a letter.
let azAt = '', azFade = null, azDrag = null;
function azGo(l) {
  if (!l || l === azAt) return;
  azAt = l;
  const band = pg$('az-' + l);
  if (band) scrollToEl(band, 0);
  let b = $('azBubble');
  if (!b) { b = document.createElement('div'); b.id = 'azBubble'; b.className = 'az-bubble'; b.setAttribute('aria-hidden', 'true'); document.body.append(b); }
  b.textContent = l; b.classList.add('on');
  clearTimeout(azFade);
  azFade = setTimeout(() => b.classList.remove('on'), 500);
}
function azFrom(e) {
  const box = azDrag, bs = box && [...box.querySelectorAll('[data-az-l]')];
  if (!bs || !bs.length) return;
  const y = e.clientY, hit = bs.find(b => { const r = b.getBoundingClientRect(); return y >= r.top && y < r.bottom; })
    || (y < bs[0].getBoundingClientRect().top ? bs[0] : bs[bs.length - 1]);
  azGo(hit.dataset.azL);
}
document.addEventListener('pointerdown', e => {
  const box = e.target.closest('.az-idx');
  if (!box) return;
  e.preventDefault();   // no text selection, no tap on the row under it
  azDrag = box; azAt = '';
  try { box.setPointerCapture(e.pointerId); } catch { /* an old browser */ }
  azFrom(e);
});
document.addEventListener('pointermove', e => { if (azDrag) azFrom(e); });
const azEnd = () => { azDrag = null; };
document.addEventListener('pointerup', azEnd);
document.addEventListener('pointercancel', azEnd);
document.addEventListener('click', e => {   // a keyboard's Enter on a letter (a finger's tap went through pointerdown)
  const b = e.target.closest('[data-az-l]');
  if (b && e.detail === 0) { azAt = ''; azGo(b.dataset.azL); }
});
addEventListener('wheel', e => {
  if (e.ctrlKey || !pageFree() || e.target.closest('#list') || ownScroller(e.target)) return;   // the page under the mouse scrolls itself
  const k = e.deltaMode === 1 ? 40 : e.deltaMode === 2 ? innerHeight : 1;
  // Økonomi scrolls inside its frame: the wheel beside the column moves the frame's page (18/10, the owner)
  const fr = tab === 'okonomi' && pageEl('okonomi') && pageEl('okonomi').querySelector('iframe');
  if (fr) { try { fr.contentWindow.scrollBy(0, e.deltaY * k); } catch { /* not ready */ } return; }
  cur().scrollTop += e.deltaY * k;
}, { passive: true });
function stopAuto() { auto = null; document.documentElement.classList.remove('autoscroll'); }
function autoStep() {
  if (!auto) return;
  const d = auto.y - auto.y0, a = Math.abs(d) - 12;
  if (a > 0) auto.page.scrollTop += Math.sign(d) * Math.pow(a / 9, 1.35);
  requestAnimationFrame(autoStep);
}
addEventListener('mousedown', e => {   // any button stops it, and that click does nothing else
  if (!auto) return;
  stopAuto(); swallow = true; addEventListener('mouseup', () => setTimeout(() => { swallow = false; }), { once: true }); e.preventDefault(); e.stopImmediatePropagation();
}, true);
addEventListener('mousedown', e => {
  if (e.button !== 1 || e.target.closest('a') || !pageFree() || ownScroller(e.target)) return;   // a link keeps 'open in a new tab'
  e.preventDefault();
  auto = { y0: e.clientY, y: e.clientY, moved: false, page: cur() };
  document.documentElement.classList.add('autoscroll');
  requestAnimationFrame(autoStep);
});
addEventListener('mousemove', e => { if (auto) { auto.y = e.clientY; if (Math.abs(auto.y - auto.y0) > 12) auto.moved = true; } });
addEventListener('mouseup', e => { if (auto && e.button === 1 && auto.moved) stopAuto(); });   // held and moved: let go to stop
addEventListener('keydown', e => { if (auto && e.key === 'Escape') stopAuto(); });
addEventListener('blur', () => { if (auto) stopAuto(); });
addEventListener('click', e => { if (swallow) { swallow = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
function showOwnerSheet(title, html, item = null, label = 'Admin') {
  $('actTitle').textContent = title; $('act').setAttribute('aria-label', label);
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
    + list.map(i => `<button class="wide pickq${cur && i.id === cur.id ? ' on' : ''}" data-a="lead:${esc(i.id)}"><b>${esc(i.title)}</b><span>${SECTIONS[secOf(i)]} · ${stamp(i.published || i.found)}${i.outlets >= 2 ? ` · ${i.outlets} medier` : ''}</span></button>`).join('')
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
  if (kind === 'flyt') { useMove(val); return; }   // a link's saves: added or in place of the phone's own
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
// the size of the news text: as the phone's own setting (iPhone's text size), or the reader's choice here. It scales
// the text of the pages only (every font size there is multiplied by --ts), not the bars or the settings
let textSize = store.get('textSize', 'auto');
function phoneText() {
  if (!CSS.supports('font', '-apple-system-body')) return 1;   // elsewhere the browser scales by itself
  const s = document.createElement('span');
  s.style.cssText = 'font:-apple-system-body;position:absolute;visibility:hidden';
  s.textContent = 'x';
  document.body.appendChild(s);
  const px = parseFloat(getComputedStyle(s).fontSize);
  s.remove();
  return px ? Math.min(1.6, Math.max(0.85, px / 17)) : 1;   // 17 is iPhone's standard size
}
// The size reaches everything: the pages at the chosen size, the bar, the tabs and the sheets up to 1.2 (as iOS caps its
// bars) – --ts is set on the page's root, and the chrome reads it capped (style.css)
function applyTextSize() {
  const ts = textSize === 'auto' ? phoneText() : +textSize || 1;
  document.documentElement.style.setProperty('--tsu', ts.toFixed(3));
  list.classList.toggle('ts-l', ts >= 1.15);   // large text: a closed headline gets a third line (the row's height holds it)
  document.querySelectorAll('#sizeSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === textSize));
}
$('sizeSeg').addEventListener('click', e => { const b = e.target.closest('[data-v]'); if (b) { textSize = b.dataset.v; store.set('textSize', textSize); applyTextSize(); } });
applyTextSize();
document.addEventListener('visibilitychange', () => { if (!document.hidden && textSize === 'auto') applyTextSize(); });   // changed on the phone meanwhile
$('danish').addEventListener('change', e => { danish = e.target.checked; store.set('danish', danish); render(); });
function paintSeg() { document.querySelectorAll('#foreignSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === foreignMode)); }
$('foreignSeg').addEventListener('click', e => {
  const b = e.target.closest('[data-v]'); if (!b) return;
  foreignMode = b.dataset.v; store.set('foreignMode', foreignMode); paintSeg(); render();
});
paintSeg();

// appearance: one light look (Dæmpet) and one dark (Notion) since 17/10 – the owner: "Skær farvetemaet med til to, de
// primære mørk og lys" – and automatic / light / dark
let mode = store.get('mode', 'auto');
function applyLook() {
  const d = document.documentElement;
  delete d.dataset.tone; delete d.dataset.dark;
  mode === 'auto' ? delete d.dataset.theme : d.dataset.theme = mode;
  document.querySelectorAll('#modeSeg [data-v]').forEach(b => b.setAttribute('aria-checked', b.dataset.v === mode));
  const bg = getComputedStyle(d).getPropertyValue('--bg').trim();
  document.querySelectorAll('meta[name="theme-color"]').forEach(m => m.setAttribute('content', bg));
  const cs = document.querySelector('meta[name="color-scheme"]');
  if (cs) cs.content = mode === 'light' ? 'light' : mode === 'dark' ? 'dark' : 'light dark';
}
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
// the kinds of notification the reader chose (pro-plan 5.5): kept on the phone and sent with its own push address – no
// other id, no prompt beyond the phone's own
const PUSH_KINDS = ['top', 'digest', 'svar'];
let pushWant = (() => { const v = store.get('pushWant', null); return Array.isArray(v) ? v.filter(k => PUSH_KINDS.includes(k)) : PUSH_KINDS.slice(); })();
async function tellKhabar(sub, kind = 'sub') {
  if (!CFG.feedbackTopic) return false;
  try {
    const r = await fetch('https://ntfy.sh/' + CFG.feedbackTopic, { method: 'POST', body: JSON.stringify({ kind, sub: sub.toJSON(), ...(kind === 'sub' ? { want: pushWant } : {}) }) });
    if (r.ok && kind === 'sub') { store.set('phoneSent', Date.now()); store.set('pushWant', pushWant); store.set('wantDirty', 0); }
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
  const on = !!(sub && Notification.permission === 'granted');
  $('pushKinds').hidden = !on;
  document.querySelectorAll('#pushKinds [data-want]').forEach(x => { x.checked = pushWant.includes(x.dataset.want); });
  if (on) {
    info.textContent = 'Vælg, hvad du vil have besked om. Aldrig mellem kl. 23 og 7.';
    off.hidden = false;
  } else {
    info.textContent = 'Få besked ved nyheder med høj betydning, dagens resumé og nye svar fra Hizb ut-Tahrir – du vælger selv hvilke.';
    btn.hidden = false;
  }
}
// a switch: the choice is kept on the phone and goes to Khabar with the phone's push address
document.getElementById('pushKinds').addEventListener('change', async e => {
  const x = e.target.closest('[data-want]');
  if (!x) return;
  pushWant = PUSH_KINDS.filter(k => (k === x.dataset.want ? x.checked : pushWant.includes(k)));
  store.set('pushWant', pushWant);
  const reg = await Promise.race([navigator.serviceWorker.ready, wait(4000)]), sub = reg && await reg.pushManager.getSubscription();
  // not sent (offline): kept as unsent, and sent the moment the phone is on the net again, or at the next start
  if (sub && !(await tellKhabar(sub))) { store.set('wantDirty', 1); toast('Ingen forbindelse – valget sendes, når du er på nettet', false); }
});
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
// Already signed up: the phone's address and its choice go to Khabar again once a week (a lost one comes back), at once
// when a choice could not be sent, and once for a phone that signed up before the three switches (Khabar has it with
// two kinds; the switches show three) – at the start, when the app comes back and when the network does
if (store.get('pushWant', null) === null) store.set('wantDirty', 1);
let resending = false;
async function resendWant() {
  if (resending || !('serviceWorker' in navigator) || typeof Notification === 'undefined' || navigator.onLine === false) return;
  if (!store.get('wantDirty', 0) && Date.now() - store.get('phoneSent', 0) < 7 * 864e5) return;
  resending = true;
  try {
    const reg = await Promise.race([navigator.serviceWorker.ready, wait(4000)]);
    const sub = reg && reg.pushManager && await reg.pushManager.getSubscription();
    if (sub && Notification.permission === 'granted') await tellKhabar(sub);
    else store.set('wantDirty', 0);   // not signed up: nothing to send
  } catch { /* the next start tries again */ } finally { resending = false; }
}
setTimeout(resendWant, 2500);
document.addEventListener('visibilitychange', () => { if (!document.hidden) resendWant(); });

// an app, not a web page: no pinch zoom (iPhone ignores the viewport setting for pinching; CSS stops double-tap zoom)
['gesturestart', 'gesturechange'].forEach(ev => document.addEventListener(ev, e => e.preventDefault(), { passive: false }));
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
// links into the app: the old section tabs (?tab=dk|me|world, from notifications and shortcuts) open Live; a wiki page or
// an answer opens over the front page
// the shelved map's ?tab=kort opens the front page; ?kalender=<id> opens the Kalender tab at that event
const START = { dk: 'latest', me: 'latest', world: 'latest', latest: 'latest', kalender: 'kalender', kort: 'home', okonomi: 'okonomi', priser: 'okonomi', search: 'search', analyses: 'analyses' };
const startTab = params.get('kalender') ? 'kalender' : START[params.get('tab')];
need('bix'); need('mix');   // the wiki's small index (the names the news link) and the answers' (the line under a story)
takeMove();   // a 'Flyt til en anden telefon' link: its saves added to this phone's
addEventListener('hashchange', () => { if (location.hash.startsWith('#flyt=')) { takeMove(); openSide('gemt'); } });   // one opened in a running app
if (params.get('begreb')) openSide('begreb', params.get('begreb'));
else if (params.get('svar')) openSide('svar', params.get('svar'));
else if (params.get('forlob')) { goOverview = false; openSide('threads', params.get('forlob')); }   // a shared development
else if (params.has('gemt')) openSide('gemt');
else if (startTab && startTab !== 'home') setTab(startTab, { top: true });
else render();
hidePages();
load();
setTimeout(() => need('ans'), 700);   // the editor's filed answers
// a link into the app (a shared story, answer, page or development, a notification) skips the intro (index.html); a
// first visitor who came that way has seen the app when they leave it, and is counted at once
const DEEP = ['item', 'svar', 'begreb', 'forlob', 'digest', 'tab', 'gemt', 'kalender'].some(k => params.has(k));
if (store.get('introSeen', false)) setTimeout(() => countVisit(cameVia()), 1500);   // a first visit counts at 'Kom i gang'
else if (DEEP) {
  setTimeout(() => countVisit(cameVia(), true), 1500);
  addEventListener('pagehide', () => store.set('introSeen', true), { once: true });
  document.addEventListener('visibilitychange', () => { if (document.hidden) store.set('introSeen', true); }, { once: true });
}

// ---------------------------------------------------------------- the pen: خبر written with a reed (the intro and pull to refresh)
// The nib: a flat reed 50 wide, held at 60 degrees. Going up the first leg it moves almost along its own edge, so the
// line is a hairline (10); from the top of the loop on it lies fuller on the paper (34, so no hair of the loop shows
// through while it writes), and the broad part comes only as it crosses back along the line. Each step is the hull of
// the nib where it was and where it is now, so the edges follow the nib's corners as smooth curves (separate stamps
// would leave teeth). The first leg runs through the line as a thin strip whose edges curve on from the tail into the
// leg; the rest of the line's band where they cross waits (in a mask: masks are anti-aliased, clip-paths are not)
// until the pen crosses back along it. The order is the calligrapher's: up and round the loop of ح, back through the
// tooth of ب into the tail of ر, then the dot under ب; the red dot that makes it خ comes last.
const NS = 'http://www.w3.org/2000/svg';
const nibAt = (p, t) => [[-25, -t / 2], [25, -t / 2], [25, t / 2], [-25, t / 2]]
  .map(([x, y]) => [p.x + x * 0.5 + y * 0.866, p.y - x * 0.866 + y * 0.5]);     // rotated -60 degrees
const hull = pts => {
  pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], up = [];
  for (const q of pts) { while (lo.length > 1 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of pts.reverse()) { while (up.length > 1 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0, -1).concat(up.slice(0, -1));
};
// the pen's polygons in writing order: {p (the hull's points), s (0 the word, 1 the dot under ب), x (0..1 along its
// stroke, eased), b (1: drawn behind the line's band)}. The path is fixed, so this is worked out once and kept on the
// phone; the path is asked for every fourth point only (asking is slow on a phone), the points between laid on the
// straight line – on the tightest curve, the loop of ح, a third of a pixel from it at most.
const INK_KEY = 'ink1';
function penGeometry(path1, path2) {
  const src = path1.getAttribute('d') + '|' + path2.getAttribute('d'), kept = parse(rawOf(INK_KEY), null);
  if (kept && kept.src === src && Array.isArray(kept.p)) return kept.p;
  const out = [], K = 4;
  [[path1, true], [path2, false]].forEach(([path, thin], s) => {
    const L = path.getTotalLength(), n = Math.ceil(L / 1.5), at = [];
    for (let i = 0; i <= n; i += K) at[i] = path.getPointAtLength(L * i / n);
    if (!at[n]) at[n] = path.getPointAtLength(L);
    const point = i => {
      if (at[i]) return at[i];
      const a = i - i % K, b = Math.min(n, a + K), k = (i - a) / (b - a);
      return { x: at[a].x + (at[b].x - at[a].x) * k, y: at[a].y + (at[b].y - at[a].y) * k };
    };
    let prev = null;
    for (let i = 0; i <= n; i++) {
      const len = L * i / n, nib = nibAt(point(i), thin ? 10 + 24 * Math.min(1, Math.max(0, (len - 70) / 40)) : 26);
      out.push({ p: hull(prev ? prev.concat(nib) : nib).map(q => q[0].toFixed(2) + ',' + q[1].toFixed(2)).join(' '), s,
        x: +(Math.acos(1 - 2 * (i / n)) / Math.PI).toFixed(4), b: thin && len < 200 ? 1 : 0 });   // the pen speeds up and slows down
      prev = nib;
    }
  });
  idle(() => { try { localStorage.setItem(INK_KEY, JSON.stringify({ src, p: out })); } catch { /* a private window: worked out again next time */ } });
  return out;
}
// The polygons the pen lays down within one frame (a sixtieth of a second) are one shape: the same writing, seen frame
// by frame, from some seventy shapes instead of six hundred and fifty, each shown when the pen gets there.
function penStrokes(mask, behind, path1, path2, D) {
  const groups = [];
  let g = null;
  for (const q of penGeometry(path1, path2)) {
    const t = q.s ? 0.1 + D + 0.1 + q.x * D * 0.15 : 0.1 + q.x * D, f = Math.floor(t * 60);
    if (!g || g.f !== f || g.b !== q.b || g.s !== q.s) groups.push(g = { f, b: q.b, s: q.s, t, d: '' });
    g.d += 'M' + q.p.replace(/ /g, 'L') + 'Z';
  }
  const into = [document.createDocumentFragment(), document.createDocumentFragment()];
  for (const x of groups) {
    const r = document.createElementNS(NS, 'path');
    r.setAttribute('class', 'nib'); r.setAttribute('fill', '#fff'); r.setAttribute('d', x.d);
    r.style.setProperty('--t', x.t.toFixed(3) + 's');
    into[x.b].appendChild(r);
  }
  mask.appendChild(into[0]); behind.appendChild(into[1]);
}
const fullInk = mask => {   // the last hair the nib missed: the whole word, once the pen lifts
  const r = document.createElementNS(NS, 'rect');
  r.setAttribute('class', 'nib'); r.setAttribute('width', 600); r.setAttribute('height', 400); r.setAttribute('fill', '#fff');
  mask.appendChild(r); return r;
};

// ---------------------------------------------------------------- intro
// Every start: the name is written as with a reed pen. The very first time the screen also says what Khabar is for
// and stays until 'Kom i gang'. A tap skips the short version.
(function intro() {
  const el = $('intro');
  if (document.documentElement.classList.contains('intro-skip')) { if (el) el.remove(); return; }   // back within hours
  setTimeout(() => document.documentElement.classList.remove('intro-on'), 6000);   // never keep the tabs hidden
  if (!el) return document.documentElement.classList.remove('intro-on');
  const first = !store.get('introSeen', false);
  const D = reduceMotion ? 0 : first ? 1.3 : 0.95;          // the main stroke's duration in seconds
  const done = () => { el.classList.add('gone'); document.documentElement.classList.remove('intro-on'); setTimeout(() => el.remove(), 500); };
  const mask = $('inkMask'), behind = document.createElementNS(NS, 'g');
  behind.setAttribute('mask', 'url(#inkBehind)'); mask.appendChild(behind);
  const start = () => {
    penStrokes(mask, behind, $('inkPath'), $('inkDot'), D);
    fullInk(mask).style.setProperty('--t', (0.1 + D + 0.4) + 's');
    el.style.setProperty('--dot', (0.1 + D + 0.45).toFixed(2) + 's');
    if (first) $('introWhy').style.animationDelay = (0.1 + D + 0.8).toFixed(2) + 's';
    else { const t = setTimeout(done, (D + 1.6) * 1000); el.addEventListener('click', () => { clearTimeout(t); done(); }); }
  };
  if (first) {
    $('introWhy').hidden = false; el.setAttribute('aria-hidden', 'false');
    $('introGo').addEventListener('click', () => { store.set('introSeen', true); countVisit(cameVia(), true); done(); });
  }
  // the pen needs the calligraphic letters. They come with Google's font sheet, which loads beside the page (it no
  // longer holds up the start): first the sheet, then the letters – asking for the letters before the sheet is in
  // finds no such font and would let the pen write over letters that are not there yet. If they have not come within
  // two and a half seconds, the word simply shows.
  let begun = false;
  const go = () => { if (!begun) { begun = true; start(); } };
  const plain = () => { if (!begun) { begun = true; fullInk(mask).style.setProperty('--t', '0s'); el.style.setProperty('--dot', '.1s'); start(); } };
  const sheet = document.querySelector('link[href*="fonts.googleapis"]');
  new Promise(res => {
    if (!sheet || (sheet.sheet && sheet.media === 'all')) return res();
    sheet.addEventListener('load', () => setTimeout(res), { once: true });   // its own onload has made it count by then
    sheet.addEventListener('error', res, { once: true });
  }).then(() => {
    void getComputedStyle(document.documentElement).fontFamily;   // the page takes in the new sheet's font
    return document.fonts.load('700 100px "Aref Ruqaa"', 'حبر');
  }).then(faces => (faces.length ? go() : plain()), plain);
  setTimeout(plain, 2500);
})();
