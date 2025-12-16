/* eslint-disable no-restricted-globals */
const CACHE_NAME = 'tender-dashboard-v1';
const API_CACHE = 'tender-dashboard-api-v1';
const META_CACHE = 'tender-dashboard-meta-v1';
const API_TTL_MS = 60 * 60 * 1000; // 1 hour

const urlsToCache = [
  '/',
  '/index.html',
  '/style.css',
  '/tenders.json',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/screenshots/desktop.png',
  '/screenshots/mobile.png',
];

async function safeAddAll(cache, urls) {
  await Promise.all(
    urls.map(async (u) => {
      try {
        await cache.add(new Request(u, { cache: 'reload' }));
      } catch {
        // ignore missing URLs in some hosting paths
      }
    })
  );
}

async function putMeta(url, timeMs) {
  const cache = await caches.open(META_CACHE);
  await cache.put(
    new Request(url + '::meta'),
    new Response(JSON.stringify({ timeMs }), { headers: { 'content-type': 'application/json' } })
  );
}

async function getMeta(url) {
  const cache = await caches.open(META_CACHE);
  const res = await cache.match(new Request(url + '::meta'));
  if (!res) return null;
  try {
    const json = await res.json();
    return typeof json?.timeMs === 'number' ? json.timeMs : null;
  } catch {
    return null;
  }
}

async function cacheResponseWithTime(cacheName, request, response) {
  const cache = await caches.open(cacheName);
  const timeIso = new Date().toISOString();
  const blob = await response.clone().blob();
  const headers = new Headers(response.headers);
  headers.set('x-sw-cache-time', timeIso);
  const wrapped = new Response(blob, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
  await cache.put(request, wrapped);
  await putMeta(request.url, Date.now());
  return wrapped;
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;
  const res = await fetch(request);
  if (res && res.ok) await cache.put(request, res.clone());
  return res;
}

async function networkFirstTenders(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) return await cacheResponseWithTime(API_CACHE, request, res);
    throw new Error('Bad response');
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error('Offline and no cache');
  }
}

async function networkFirstApiWithTtl(request) {
  const cache = await caches.open(API_CACHE);
  const cached = await cache.match(request);
  const meta = await getMeta(request.url);
  const fresh = meta ? Date.now() - meta < API_TTL_MS : false;
  if (cached && fresh) return cached;

  try {
    const res = await fetch(request);
    if (res && res.ok) return await cacheResponseWithTime(API_CACHE, request, res);
    if (cached) return cached;
    return res;
  } catch {
    if (cached) return cached;
    throw new Error('Offline and no cache');
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await safeAddAll(cache, urlsToCache);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.map((k) => {
          if (![CACHE_NAME, API_CACHE, META_CACHE].includes(k)) return caches.delete(k);
          return Promise.resolve();
        })
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;

  // SPA/offline navigation fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          return await fetch(request);
        } catch {
          const cache = await caches.open(CACHE_NAME);
          return (await cache.match('/index.html')) || (await cache.match('/')) || Response.error();
        }
      })()
    );
    return;
  }

  // Network-first for tenders.json (fallback to cache)
  if (sameOrigin && url.pathname.endsWith('/tenders.json')) {
    event.respondWith(networkFirstTenders(request));
    return;
  }

  // Cache-first for static assets
  if (sameOrigin && ['style', 'script', 'image', 'font'].includes(request.destination)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Cache API/JSON responses with TTL (1h)
  const acceptsJson = (request.headers.get('accept') || '').includes('application/json');
  const isJson = url.pathname.endsWith('.json') || acceptsJson;
  if (sameOrigin && isJson) {
    event.respondWith(networkFirstApiWithTtl(request));
    return;
  }
});
