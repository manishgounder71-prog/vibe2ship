/**
 * FutureShield AI — Service Worker
 * Provides offline support, push notifications, and cache management.
 * 
 * Cache Strategy:
 * - STATIC: HTML pages, shared JS/CSS, manifest — cache on install, serve cache-first
 * - API: API responses — cache on fetch, serve network-first with cache fallback
 * - IMAGES: External images — cache on fetch, serve cache-first
 */

const SW_VERSION = 'v1.0.1';
const STATIC_CACHE = 'futureshield-static-' + SW_VERSION;
const API_CACHE = 'futureshield-api-' + SW_VERSION;
const IMAGE_CACHE = 'futureshield-images-' + SW_VERSION;

// ─── Assets to pre-cache on install ───────────────────────────────
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/dashboard.html',
  '/radar.html',
  '/simulation.html',
  '/rescue.html',
  '/twin.html',
  '/manifest.json',
  '/icon.svg',
  '/shared/fs-shared.js',
  '/shared/style.css',
  '/shared/voice-assistant.js',
  '/shared/focus-timer.js',
  '/shared/knowledge-graph.js',
  '/shared/ai-calendar.js'
];

// ─── Install Event: Pre-cache static assets ──────────────────────
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

// ─── Activate Event: Clean old caches ────────────────────────────
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames.filter(function (name) {
          return name !== STATIC_CACHE && name !== API_CACHE && name !== IMAGE_CACHE;
        }).map(function (name) {
          return caches.delete(name);
        })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

// ─── Helper: Determine if request is an API call ─────────────────
function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

// ─── Helper: Determine if request is an external image ───────────
function isExternalImage(url) {
  return url.hostname !== self.location.hostname &&
         (/\.(png|jpg|jpeg|gif|svg|webp|ico)(\?.*)?$/i.test(url.pathname) ||
          url.hostname.includes('googleusercontent.com') ||
          url.hostname.includes('cdn.jsdelivr.net'));
}

// ─── Helper: Determine if request is a static asset ──────────────
function isStaticAsset(url) {
  return PRECACHE_URLS.includes(url.pathname) ||
         /\.(html|css|js|json|svg|png|jpg|woff2?)$/i.test(url.pathname) ||
         url.pathname.startsWith('/shared/');
}

// ─── Fetch Event: Serve with caching strategy ────────────────────
self.addEventListener('fetch', function (event) {
  var requestUrl = new URL(event.request.url);

  // Skip non-GET and browser extension requests
  if (event.request.method !== 'GET' ||
      requestUrl.protocol === 'chrome-extension:' ||
      requestUrl.protocol === 'moz-extension:') {
    return;
  }

  // API requests: Network-first with cache fallback
  if (isApiRequest(requestUrl)) {
    event.respondWith(networkFirst(event.request, API_CACHE));
    return;
  }

  // External images: Cache-first with network update
  if (isExternalImage(requestUrl)) {
    event.respondWith(cacheFirst(event.request, IMAGE_CACHE));
    return;
  }

  // Static assets: Cache-first
  if (isStaticAsset(requestUrl)) {
    event.respondWith(cacheFirst(event.request, STATIC_CACHE));
    return;
  }

  // Everything else: Network-first
  event.respondWith(networkFirst(event.request, STATIC_CACHE));
});

// ─── Cache Strategies ────────────────────────────────────────────

function cacheFirst(request, cacheName) {
  return caches.open(cacheName).then(function (cache) {
    return cache.match(request).then(function (cachedResponse) {
      if (cachedResponse) {
        // Update cache in background for next time
        fetch(request).then(function (networkResponse) {
          if (networkResponse && networkResponse.status === 200) {
            cache.put(request, networkResponse);
          }
        }).catch(function () {});
        return cachedResponse;
      }
      return fetchAndCache(request, cacheName);
    });
  });
}

function networkFirst(request, cacheName) {
  return caches.open(cacheName).then(function (cache) {
    return fetch(request).then(function (networkResponse) {
      if (networkResponse && networkResponse.status === 200) {
        var cloned = networkResponse.clone();
        cache.put(request, cloned);
      }
      return networkResponse;
    }).catch(function () {
      return cache.match(request).then(function (cached) {
        return cached || new Response('Offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({ 'Content-Type': 'text/plain' })
        });
      });
    });
  });
}

function fetchAndCache(request, cacheName) {
  return fetch(request).then(function (response) {
    if (response && response.status === 200) {
      var cloned = response.clone();
      caches.open(cacheName).then(function (cache) {
        cache.put(request, cloned);
      });
    }
    return response;
  });
}

// ─── Push Notification Event ─────────────────────────────────────
self.addEventListener('push', function (event) {
  var data = { title: 'FutureShield AI', body: 'System notification', tag: 'default', url: '/dashboard.html' };

  if (event.data) {
    try {
      var parsed = event.data.json();
      data.title = parsed.title || data.title;
      data.body = parsed.body || data.body;
      data.tag = parsed.tag || data.tag;
      data.url = parsed.url || data.url;
      data.icon = parsed.icon || '/icon.svg';
      data.badge = parsed.badge || '/icon.svg';
      data.urgency = parsed.urgency || 'normal';
      data.actions = parsed.actions || [];
      data.requireInteraction = parsed.requireInteraction || false;
      data.silent = parsed.silent || false;
      data.vibrate = parsed.vibrate || [200, 100, 200];
    } catch (e) {
      // Plain text fallback
      data.body = event.data.text();
    }
  }

  var options = {
    body: data.body,
    icon: data.icon || '/icon.svg',
    badge: data.badge || '/icon.svg',
    tag: data.tag,
    data: {
      url: data.url,
      dateOfArrival: Date.now(),
      urgency: data.urgency
    },
    actions: data.actions,
    requireInteraction: data.requireInteraction,
    silent: data.silent,
    vibrate: data.vibrate,
    renotify: true
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// ─── Notification Click Event ────────────────────────────────────
self.addEventListener('notificationclick', function (event) {
  event.notification.close();

  var targetUrl = event.notification.data && event.notification.data.url
    ? event.notification.data.url
    : '/dashboard.html';

  // Handle action buttons
  if (event.action) {
    switch (event.action) {
      case 'resolve':
        targetUrl = '/radar.html';
        break;
      case 'focus':
        targetUrl = '/dashboard.html?focus=1';
        break;
      case 'simulate':
        targetUrl = '/simulation.html';
        break;
      case 'rescue':
        targetUrl = '/rescue.html';
        break;
      case 'dismiss':
        return; // Just close the notification
    }
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
      // Focus existing tab if open
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url.indexOf(self.location.origin) === 0 && 'focus' in client) {
          return client.focus().then(function (focusedClient) {
            return focusedClient.navigate(targetUrl);
          });
        }
      }
      // Open new window
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// ─── Background Sync for offline focus sessions ──────────────────
self.addEventListener('sync', function (event) {
  if (event.tag === 'sync-focus-sessions') {
    event.waitUntil(syncFocusSessions());
  }
});

function syncFocusSessions() {
  // Retrieve pending focus sessions from IndexedDB and sync
  // This is a placeholder — full IndexedDB integration can be added
  return Promise.resolve();
}

// ─── Periodic Background Sync (for notification polling) ─────────
self.addEventListener('periodicsync', function (event) {
  if (event.tag === 'check-threats') {
    event.waitUntil(checkAndNotify());
  }
});

async function checkAndNotify() {
  try {
    var headers = {};
    try {
      var cache = await caches.open('shield-token-cache');
      var cachedResp = await cache.match('/token');
      if (cachedResp) {
        var token = await cachedResp.text();
        if (token) {
          headers['Authorization'] = 'Bearer ' + token.trim();
        }
      }
    } catch (e) {
      console.error('Error fetching token in SW:', e);
    }

    var response = await fetch('/api/notifications/check', { headers: headers });
    if (!response.ok) return;
    var data = await response.json();

    // Show threat alert notification
    if (data.threats && data.threats.length > 0) {
      var critical = data.threats.filter(function (t) { return t.urgency === 'HIGH'; });
      if (critical.length > 0) {
        self.registration.showNotification('🚨 Critical Threats Detected', {
          body: critical.length + ' high-urgency threat(s) require immediate attention.',
          icon: '/icon.svg',
          badge: '/icon.svg',
          tag: 'threat-alert',
          data: { url: '/radar.html' },
          requireInteraction: true,
          vibrate: [300, 100, 300, 100, 300]
        });
      }
    }

    // Show deadline warning notification
    if (data.deadlines && data.deadlines.length > 0) {
      self.registration.showNotification('⏰ Deadline Approaching', {
        body: data.deadlines[0].title + ' is due ' + data.deadlines[0].deadline,
        icon: '/icon.svg',
        badge: '/icon.svg',
        tag: 'deadline-warning',
        data: { url: '/dashboard.html' },
        actions: [
          { action: 'focus', title: 'Start Focus Session' },
          { action: 'simulate', title: 'Run Simulation' }
        ]
      });
    }
  } catch (e) {
    // Silent fail — will retry on next sync
  }
}

// ─── Message handler for notification triggers from client ───────
self.addEventListener('message', function (event) {
  if (event.data && event.data.type === 'SHOW_NOTIFICATION') {
    var data = event.data.payload || {};
    self.registration.showNotification(data.title || 'FutureShield AI', {
      body: data.body || '',
      icon: '/icon.svg',
      badge: '/icon.svg',
      tag: data.tag || 'notification',
      data: { url: data.url || '/dashboard.html' },
      requireInteraction: data.requireInteraction || false,
      vibrate: data.vibrate || [200, 100, 200]
    });
  }

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Log activation
console.log('[FutureShield SW] ' + SW_VERSION + ' active');
