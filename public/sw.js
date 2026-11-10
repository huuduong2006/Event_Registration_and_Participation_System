// Cache phần giao diện tĩnh để mở app nhanh. API luôn đi thẳng lên server (check-in cần dữ liệu thật).
const CACHE = 'checkin-shell-v1';
const SHELL = ['/', '/style.css', '/app.js', '/vendor/html5-qrcode/html5-qrcode.min.js'];
self.addEventListener('install', (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))));
self.addEventListener('activate', (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))));
self.addEventListener('fetch', (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.pathname.startsWith('/api/')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
