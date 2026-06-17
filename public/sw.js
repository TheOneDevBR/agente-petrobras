// Service worker mínimo — stale-while-revalidate para o app shell.
// NUNCA cacheia a API (/api) — sempre rede para dados ao vivo.
const CACHE = 'agentepetrobras-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== 'GET' ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith('/api')
  ) {
    return; // deixa passar direto para a rede
  }
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      const network = fetch(event.request)
        .then((resp) => {
          if (resp && resp.status === 200) cache.put(event.request, resp.clone());
          return resp;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
