const CACHE_NAME = 'astro-avyug-v2';
const APP_SHELL = [
  '/',
  '/index.html',
  '/site.webmanifest',
  '/pwa-install.js',
  '/favicon-192x192.png',
  '/favicon-512x512.png',
  '/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Do not cache large review videos.
  if (url.pathname.startsWith('/videos/')) return;

  // Network-first: deployed updates are preferred; cache is only the fallback.
  event.respondWith(
    fetch(req)
      .then(response => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => {});
        }
        return response;
      })
      .catch(() => caches.match(req).then(cached => cached || caches.match('/index.html')))
  );
});
