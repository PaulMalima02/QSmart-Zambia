/* QSMART Zambia service worker — offline shell + installable PWA */
const CACHE = 'qsmart-v2';
const ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/auth.js',
  '/static/manifest.webmanifest',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // Network-first for API-ish / dynamic routes; cache-first for static
  const url = new URL(req.url);
  const isStatic =
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('jsdelivr.net') ||
    url.hostname.includes('unpkg.com');

  if (isStatic) {
    e.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            if (res && res.status === 200) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
      )
    );
    return;
  }

  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200 && url.origin === self.location.origin) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then(
          (cached) =>
            cached ||
            new Response(
              'You are offline. QSMART Zambia — reconnect to sync queues and queries.',
              { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } }
            )
        )
      )
  );
});
