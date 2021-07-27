const cacheName = 'v1';
// Call Install Event
self.addEventListener('install', () => {
});

// Call Activate Event
self.addEventListener('activate', e => {
    e.waitUntil(async function () {
        if (self.registration.navigationPreload) {
            await self.registration.navigationPreload.enable();
        }
    })
    // Remove unwanted caches
    e.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== cacheName) {
                        console.log('NNR: obliterating the unwanted...');
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
});

// Call Fetch Event
self.addEventListener('fetch', e => {
    fetch(e.request).then(async function(response) {
        if (!response.ok) {
            const cachedResponse = await caches.match(e.request);
            if (cachedResponse)
                e.respondWith(response);
        }
        else {
            caches.open(cacheName).then(cache => cache.put(e.request, response));
        }
        e.respondWith(response)
    });
})
