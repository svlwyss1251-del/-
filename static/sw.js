self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('expense-cache-v1').then((cache) => cache.addAll([
      '/', '/static/style.css'
    ]))
  );
});
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((resp) => resp || fetch(event.request))
  );
});