const CACHE_NAME = 'astro-avyug-v1';
const APP_SHELL = ['/', '/index.html', '/site.webmanifest', '/favicon.png', '/android-chrome-192x192.png', '/android-chrome-512x512.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Do not cache large review videos; keep page loads fast and avoid filling device storage.
  if (url.pathname.startsWith('/videos/')) return;

  event.respondWith(
    fetch(req).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => {});
      return response;
    }).catch(() => caches.match(req).then(r => r || caches.match('/index.html')))
  );
});
