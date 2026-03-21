/**
 * Execution Market Service Worker
 *
 * Handles offline caching, push notifications, and background sync.
 */

const CACHE_NAME = 'em-v4-20260216';
const STATIC_ASSETS = [
  '/manifest.json',
  '/offline.html',
];

const API_CACHE = 'em-api-v1';
const IMAGE_CACHE = 'em-images-v1';

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE && name !== IMAGE_CACHE)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip external requests (Supabase, etc.)
  if (url.origin !== location.origin && !url.hostname.includes('supabase')) {
    return;
  }

  // Always prefer network for SPA navigations to avoid stale app shells
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, CACHE_NAME));
    return;
  }

  // API requests - network only with cache fallback
  if (url.pathname.startsWith('/api/') || url.hostname.includes('supabase')) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Image requests - cache first
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
    return;
  }

  // Versioned assets — network first to prevent stale chunk references.
  // Vite hashes filenames so cache-first SOUNDS safe, but when the entry JS
  // changes hash, a cached old entry will request chunks that no longer exist
  // on the server, causing infinite reload loops.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(networkFirst(request, CACHE_NAME));
    return;
  }

  // Other same-origin requests - prefer network to minimize stale content
  event.respondWith(networkFirst(request, CACHE_NAME));
});

// Network first strategy
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }

    throw error;
  }
}

// Cache first strategy
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return offline page for navigation
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    throw error;
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();

  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      taskId: data.taskId,
    },
    actions: data.actions || [
      { action: 'view', title: 'View Task' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    tag: data.tag || 'em-notification',
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;
  const data = event.notification.data;

  if (action === 'dismiss') return;

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // Focus existing window if available
      for (const client of clientList) {
        if (client.url === data.url && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new window
      return clients.openWindow(data.url);
    })
  );
});

// Background sync for evidence uploads
self.addEventListener('sync', (event) => {
  if (event.tag === 'upload-evidence') {
    event.waitUntil(uploadPendingEvidence());
  }
  if (event.tag === 'sync-submissions') {
    event.waitUntil(syncPendingSubmissions());
  }
});

async function uploadPendingEvidence() {
  const db = await openDB();
  const pending = await db.getAll('pending-uploads');

  for (const item of pending) {
    try {
      const response = await fetch('/api/evidence/upload', {
        method: 'POST',
        body: item.formData,
      });

      if (response.ok) {
        await db.delete('pending-uploads', item.id);
      }
    } catch (error) {
      console.error('Background sync failed:', error);
    }
  }
}

async function syncPendingSubmissions() {
  const db = await openDB();
  const submissions = await db.getAll('pending-submissions');

  for (const submission of submissions) {
    try {
      const response = await fetch('/api/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(submission),
      });

      if (response.ok) {
        await db.delete('pending-submissions', submission.id);
      }
    } catch (error) {
      console.log('Sync failed, will retry');
    }
  }
}

// Simple IndexedDB wrapper
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('em-offline', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      resolve({
        getAll: (store) => {
          return new Promise((res, rej) => {
            const tx = db.transaction(store, 'readonly');
            const req = tx.objectStore(store).getAll();
            req.onsuccess = () => res(req.result);
            req.onerror = () => rej(req.error);
          });
        },
        delete: (store, key) => {
          return new Promise((res, rej) => {
            const tx = db.transaction(store, 'readwrite');
            const req = tx.objectStore(store).delete(key);
            req.onsuccess = () => res();
            req.onerror = () => rej(req.error);
          });
        },
      });
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('pending-uploads')) {
        db.createObjectStore('pending-uploads', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('pending-submissions')) {
        db.createObjectStore('pending-submissions', { keyPath: 'id' });
      }
    };
  });
}

// Handle skip waiting message from app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
