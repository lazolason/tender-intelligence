// PWA Diagnostics Module
(function() {
    'use strict';
    
    window.diagnosePWA = async function() {
        console.log('%c🔍 PWA DIAGNOSTICS REPORT', 'color: #667eea; font-weight: bold; font-size: 14px;');
        console.log('='.repeat(50));
        
        // Test 1: Service Worker
        if ('serviceWorker' in navigator) {
            console.log('✅ Service Workers SUPPORTED');
            try {
                const regs = await navigator.serviceWorker.getRegistrations();
                console.log(`   Found ${regs.length} registration(s)`);
            } catch(e) {
                console.log('   Error: ' + e.message);
            }
        } else {
            console.log('❌ Service Workers NOT SUPPORTED');
        }
        
        // Test 2: Manifest
        const manifest = document.querySelector('link[rel="manifest"]');
        if (manifest) {
            console.log('✅ Web App Manifest FOUND');
            console.log('   ' + manifest.getAttribute('href'));
        } else {
            console.log('⚠️  No manifest file');
        }
        
        // Test 3: Secure Context
        if (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
            console.log('✅ Secure context (HTTPS/Localhost)');
        } else {
            console.log('❌ NOT secure - URL: ' + location.href);
        }
        
        // Test 4: Notifications
        if ('Notification' in window) {
            console.log('✅ Notifications API SUPPORTED');
            console.log('   Permission: ' + Notification.permission);
        } else {
            console.log('❌ Notifications NOT supported');
        }
        
        // Test 5: Cache API
        if ('caches' in window) {
            console.log('✅ Cache API SUPPORTED');
            try {
                const names = await caches.keys();
                console.log(`   ${names.length} cache(s)`);
            } catch(e) {
                console.log('   Error: ' + e.message);
            }
        } else {
            console.log('❌ Cache API NOT supported');
        }
        
        // Test 6: LocalStorage
        try {
            localStorage.setItem('__test__', '1');
            localStorage.removeItem('__test__');
            console.log('✅ LocalStorage WORKING');
        } catch(e) {
            console.log('❌ LocalStorage ERROR: ' + e.message);
        }
        
        // Test 7: IndexedDB
        if ('indexedDB' in window) {
            console.log('✅ IndexedDB SUPPORTED');
        } else {
            console.log('⚠️  IndexedDB NOT supported');
        }
        
        console.log('='.repeat(50));
        console.log('%c✨ Diagnostics complete!', 'color: #00ff88; font-weight: bold;');
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
