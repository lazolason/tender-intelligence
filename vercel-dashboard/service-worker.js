/* eslint-disable no-restricted-globals */
const CACHE_NAME = 'tender-dashboard-v2';
const RUNTIME_CACHE = 'runtime';

// Cache static assets (app shell)
const STATIC_ASSETS = [
    './',
    '/index.html',
    '/style.css',
    '/manifest.json',
  '/icons/icon-192x192.png',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) =>
        cache.addAll(
          STATIC_ASSETS.map((url) => new Request(url, { cache: 'reload' }))
        )
      )
      .then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE)
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch: network-first for tenders.json with cache fallback; cache-first for static
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;

  // SPA/offline navigation fallback to app shell
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Network-first with cache fallback for tenders.json
  if (sameOrigin && url.pathname.endsWith('/tenders.json')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for the app shell/static assets
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          // Opportunistically cache same-origin assets for offline use
          if (sameOrigin && response && response.ok) {
            const copy = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match('/index.html'));
    })
  );
});

