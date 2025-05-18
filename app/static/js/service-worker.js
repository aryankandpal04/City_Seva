// CitySeva Service Worker for PWA functionality

const CACHE_NAME = 'cityseva-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/styles.css',
    '/static/js/scripts.js',
    '/static/img/favicon.svg',
    '/static/img/favicon.ico',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    '/citizen/dashboard',
    '/citizen/complaints',
    '/citizen/notifications',
    '/citizen/profile',
    '/static/js/service-worker.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://code.jquery.com/jquery-3.6.0.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    const cacheWhitelist = [CACHE_NAME];
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
        .then(() => self.clients.claim())
    );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests and API endpoints
    if (event.request.method !== 'GET' || 
        event.request.url.includes('/api/') || 
        event.request.url.includes('maps.googleapis.com')) {
        return;
    }
    
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Clone the response before using it
                const responseToCache = response.clone();
                
                // Don't cache non-success responses
                if (!response.ok) throw Error('Not 2xx response');
                
                // Cache successful responses
                caches.open(CACHE_NAME)
                    .then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                
                return response;
            })
            .catch(() => {
                // Fallback to cache if network fails
                return caches.match(event.request)
                    .then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        
                        // If not in cache, try to return the default offline page
                        return caches.match('/static/offline.html');
                    });
            })
    );
});

// Background sync for offline form submissions
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-complaints') {
        event.waitUntil(
            syncComplaints()
        );
    }
});

// Handle push notifications
self.addEventListener('push', (event) => {
    let data = {};
    
    try {
        data = event.data.json();
    } catch (e) {
        data = {
            title: 'CitySeva Notification',
            body: event.data ? event.data.text() : 'New update available'
        };
    }
    
    const options = {
        body: data.body || '',
        icon: '/static/img/icon-192.png',
        badge: '/static/img/notification-badge.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/'
        }
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});

// Function to sync stored offline complaints
async function syncComplaints() {
    try {
        const db = await openIndexedDB();
        const offlineComplaints = await getOfflineComplaints(db);
        
        const failedItems = [];
        
        for (const complaint of offlineComplaints) {
            try {
                // Attempt to post the complaint
                const response = await fetch('/api/complaints', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(complaint)
                });
                
                if (response.ok) {
                    // If successful, remove from IndexedDB
                    await deleteComplaint(db, complaint.id);
                } else {
                    failedItems.push(complaint);
                }
            } catch (error) {
                failedItems.push(complaint);
            }
        }
        
        // If we still have failed items, throw an error to retry the sync
        if (failedItems.length > 0) {
            throw new Error('Some complaints failed to sync');
        }
        
        return true;
    } catch (error) {
        throw error;
    }
}

// IndexedDB helper functions
function openIndexedDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('cityseva-db', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offline-complaints')) {
                db.createObjectStore('offline-complaints', { keyPath: 'id' });
            }
        };
    });
}

function getOfflineComplaints(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction('offline-complaints', 'readonly');
        const store = transaction.objectStore('offline-complaints');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

function deleteComplaint(db, id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction('offline-complaints', 'readwrite');
        const store = transaction.objectStore('offline-complaints');
        const request = store.delete(id);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
} 