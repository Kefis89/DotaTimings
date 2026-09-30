// При обновлении index.html увеличь номер версии, чтобы телефоны подтянули новую версию.
const CACHE = 'dota-timer-v17';
const FILES = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png',
  './sounds/bounty.wav', './sounds/power.wav', './sounds/wisdom.wav', './sounds/tormentor.wav'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // Страница: сначала сеть (чтобы получать обновления), без сети — из кэша
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).then(r => {
      const copy = r.clone(); caches.open(CACHE).then(c => c.put('./index.html', copy)); return r;
    }).catch(() => caches.match('./index.html')));
    return;
  }
  // Safari просит аудио кусками (Range) и не проигрывает целый ответ 200 из кэша — отдаём 206
  if (e.request.headers.has('range')) {
    e.respondWith(caches.match(e.request.url).then(hit => {
      const m = hit && /bytes=(\d*)-(\d*)/.exec(e.request.headers.get('range'));
      if (!m) return fetch(e.request);
      return hit.arrayBuffer().then(buf => {
        const start = m[1] ? +m[1] : 0, end = m[2] ? Math.min(+m[2], buf.byteLength - 1) : buf.byteLength - 1;
        return new Response(buf.slice(start, end + 1), { status: 206, headers: {
          'Content-Type': hit.headers.get('Content-Type') || 'audio/wav',
          'Content-Range': 'bytes ' + start + '-' + end + '/' + buf.byteLength,
          'Content-Length': String(end - start + 1)
        } });
      });
    }));
    return;
  }
  // Остальное (иконки, шрифты): сначала кэш
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    if (r.ok || r.type === 'opaque') {
      if (url.origin === location.origin || /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
        const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy));
      }
    }
    return r;
  })));
});
