// PWA Diagnostics Module
(function() {
    'use strict';
    
    window.diagnosePWA = async function() {
        const results = {
            timestamp: new Date().toISOString(),
            tests: {}
        };
        
        // Test 1: Service Worker
        if ('serviceWorker' in navigator) {
            try {
                const regs = await navigator.serviceWorker.getRegistrations();
                results.tests.serviceWorker = { 
                    supported: true, 
                    registrations: regs.length,
                    status: '✅ SUPPORTED'
                };
            } catch(e) {
                results.tests.serviceWorker = { 
                    supported: true, 
                    error: e.message,
                    status: '⚠️ SUPPORTED but error getting registrations'
                };
            }
        } else {
            results.tests.serviceWorker = { 
                supported: false,
                status: '❌ NOT SUPPORTED'
            };
        }
        
        // Test 2: Manifest
        const manifest = document.querySelector('link[rel="manifest"]');
        results.tests.manifest = manifest ? {
            found: true,
            href: manifest.getAttribute('href'),
            status: '✅ FOUND'
        } : {
            found: false,
            status: '⚠️ NOT FOUND'
        };
        
        // Test 3: Secure Context
        const isSecure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        results.tests.secureContext = {
            secure: isSecure,
            protocol: location.protocol,
            hostname: location.hostname,
            status: isSecure ? '✅ SECURE' : '❌ NOT SECURE'
        };
        
        // Test 4: Notifications
        if ('Notification' in window) {
            results.tests.notifications = {
                supported: true,
                permission: Notification.permission,
                status: `✅ SUPPORTED (${Notification.permission})`
            };
        } else {
            results.tests.notifications = {
                supported: false,
                status: '❌ NOT SUPPORTED'
            };
        }
        
        // Test 5: Cache API
        if ('caches' in window) {
            try {
                const names = await caches.keys();
                results.tests.cacheAPI = {
                    supported: true,
                    caches: names.length,
                    cacheNames: names,
                    status: `✅ SUPPORTED (${names.length} cache(s))`
                };
            } catch(e) {
                results.tests.cacheAPI = {
                    supported: true,
                    error: e.message,
                    status: '⚠️ SUPPORTED but error accessing caches'
                };
            }
        } else {
            results.tests.cacheAPI = {
                supported: false,
                status: '❌ NOT SUPPORTED'
            };
        }
        
        // Test 6: LocalStorage
        try {
            localStorage.setItem('__test__', '1');
            localStorage.removeItem('__test__');
            results.tests.localStorage = {
                working: true,
                status: '✅ WORKING'
            };
        } catch(e) {
            results.tests.localStorage = {
                working: false,
                error: e.message,
                status: '❌ ERROR'
            };
        }
        
        // Test 7: IndexedDB
        results.tests.indexedDB = {
            supported: 'indexedDB' in window,
            status: ('indexedDB' in window) ? '✅ SUPPORTED' : '❌ NOT SUPPORTED'
        };
        
        // Print pretty summary
        console.table(results.tests);
        console.log('📊 Full Results:', results);
        
        return results;
    };
    
    // Helper: Request notification permission
    window.requestNotificationPermission = async function() {
        if (!('Notification' in window)) {
            console.log('❌ Notifications not supported');
            return;
        }
        
        if (Notification.permission === 'granted') {
            console.log('✅ Notifications already enabled');
            new Notification('Tender Intelligence', {
                body: 'Notifications are working!',
                icon: '/icon-192.png'
            });
        } else if (Notification.permission !== 'denied') {
            const perm = await Notification.requestPermission();
            console.log('Permission: ' + perm);
        } else {
            console.log('❌ Notifications blocked');
        }
    };
    
    // Ready message
    console.log('%c✨ Type: diagnosePWA()', 'color: #667eea; font-size: 12px;');
    
})();
