// Service worker: offline app shell, and notifications from the radar.
const SHELL = 'radar-shell-v1';
const FILES = ['./', 'index.html', 'style.css', 'app.js', 'config.js', 'manifest.webmanifest', 'icons/icon-180.png', 'icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// App files: try the network first so updates arrive, fall back to the cached copy offline.
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => {
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
