// Service worker: offline app shell, and notifications from the radar.
const SHELL = 'radar-shell-v3';   // a new name clears the old copies on every phone
const FILES = ['./', 'index.html', 'style.css', 'app.js', 'config.js', 'manifest.webmanifest', 'icons/icon-180.png', 'icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// App files: always ask the server first (past the phone's own cache, which the host lets keep a page for ten minutes –
// an unchanged file costs only a short 'not modified'), so updates arrive at once; the cached copy is for offline.
const fresh = req => fetch(req.url, { cache: 'no-cache', credentials: 'same-origin' }).then(r => r.redirected ? fetch(req) : r);
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // the intro's letters (Google's font sheet and file for the three letters of خبر): kept on the phone, so a start
  // has them at once
  if (e.request.method === 'GET' && (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com')) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok || r.type === 'opaque') { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); }
      return r;
    })));
    return;
  }
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // a file named with its version (style.css?v=…, app.js?v=…) never changes under that name: the copy on the phone
  // serves at once, so a start waits only for the page itself
  if (url.searchParams.has('v')) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); }
      return r;
    })));
    return;
  }
  // the page itself, its config and the wiki's files (they change only with a new version, which renames this cache):
  // the copy on the phone at once – a start never waits for the network, which on a weak connection can take seconds –
  // and the newest fetched behind it for the next time (the app also asks for the newest page when it comes back, and
  // starts afresh when that names a new version). Kept under the plain path, so ?item=… and the app's own check for
  // the newest page share one copy.
  if (e.request.mode === 'navigate' || /\/config\.js$|\/viden\/[\w-]+\.json$/.test(url.pathname)) {
    const key = url.origin + url.pathname;
    const net = fresh(e.request).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(SHELL).then(c => c.put(key, copy)); }
      return r;
    });
    e.waitUntil(net.then(() => {}, () => {}));
    e.respondWith(caches.match(key).then(hit => hit || net).catch(() => net));
    return;
  }
  e.respondWith(fresh(e.request).then(r => {
    const copy = r.clone();
    caches.open(SHELL).then(c => c.put(e.request, copy));
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});

self.addEventListener('push', e => {
  let p = {};
  try { p = e.data.json(); } catch { p = { title: 'Khabar', body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(p.title || 'Khabar', {
    // badge: the small one-colour icon Android shows in the status bar; a new note with the same tag (the overview's
    // next update) replaces the old one and still makes a sound
    body: p.body || '', tag: p.tag, renotify: Boolean(p.tag), icon: 'icons/icon-192.png', badge: 'icons/badge-96.png',
    data: { url: p.url || './' },
  }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const target = new URL(e.notification.data.url || './', self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) { if ('navigate' in c) return c.navigate(target).then(w => w && w.focus()); }
    return self.clients.openWindow(target);
  }));
});
