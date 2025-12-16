/**
 * PWA Diagnostics Script for Tender Intelligence Dashboard
 * Paste this into the browser console to diagnose PWA functionality
 */

async function diagnosePWA() {
    console.log('🔍 PWA DIAGNOSTICS REPORT');
    console.log('='.repeat(50));
    
    const report = {
        timestamp: new Date().toISOString(),
        browser: navigator.userAgent,
        tests: {}
    };
    
    // Test 1: Service Worker Support
    console.log('\n✓ TEST 1: Service Worker Support');
    if ('serviceWorker' in navigator) {
        console.log('  ✅ Service Workers are supported');
        report.tests.serviceWorkerSupport = 'PASS';
        
        try {
            const registrations = await navigator.serviceWorker.getRegistrations();
            console.log(`  📊 Found ${registrations.length} Service Worker registration(s)`);
            report.tests.registrations = registrations.length;
            
            registrations.forEach((reg, idx) => {
                console.log(`    [${idx + 1}] Scope: ${reg.scope}`);
                console.log(`        State: ${reg.installing ? 'installing' : reg.waiting ? 'waiting' : reg.active ? 'active' : 'unknown'}`);
                
                if (reg.active) {
                    console.log(`        ✅ Active Service Worker found`);
                    report.tests.activeSW = 'ACTIVE';
                } else if (reg.waiting) {
                    console.log(`        ⚠️  Service Worker waiting (update pending)`);
                    report.tests.activeSW = 'WAITING';
                } else if (reg.installing) {
                    console.log(`        🔄 Service Worker installing...`);
                    report.tests.activeSW = 'INSTALLING';
                }
            });
        } catch (e) {
            console.log(`  ❌ Error checking registrations: ${e.message}`);
            report.tests.registrations = `ERROR: ${e.message}`;
        }
    } else {
        console.log('  ❌ Service Workers are NOT supported');
        report.tests.serviceWorkerSupport = 'NOT_SUPPORTED';
    }
    
    // Test 2: Manifest Support
    console.log('\n✓ TEST 2: Web App Manifest');
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) {
        const manifestHref = manifestLink.getAttribute('href');
        console.log(`  ✅ Manifest file found: ${manifestHref}`);
        report.tests.manifestFound = manifestHref;
        
        try {
            const response = await fetch(manifestHref);
            if (response.ok) {
                const manifest = await response.json();
                console.log('  📋 Manifest content:');
                console.log(`     - Name: ${manifest.name || 'N/A'}`);
                console.log(`     - Short name: ${manifest.short_name || 'N/A'}`);
                console.log(`     - Start URL: ${manifest.start_url || 'N/A'}`);
                console.log(`     - Display: ${manifest.display || 'N/A'}`);
                console.log(`     - Icons: ${manifest.icons?.length || 0} found`);
                report.tests.manifestValid = 'VALID';
                report.tests.manifestData = {
                    name: manifest.name,
                    shortName: manifest.short_name,
                    startUrl: manifest.start_url,
                    display: manifest.display,
                    iconCount: manifest.icons?.length || 0
                };
            } else {
                console.log(`  ❌ Failed to load manifest: ${response.statusText}`);
                report.tests.manifestValid = `ERROR: ${response.statusText}`;
            }
        } catch (e) {
            console.log(`  ❌ Error loading manifest: ${e.message}`);
            report.tests.manifestValid = `ERROR: ${e.message}`;
        }
    } else {
        console.log('  ⚠️  No manifest file found (optional but recommended)');
        report.tests.manifestFound = 'NOT_FOUND';
    }
    
    // Test 3: HTTPS/Localhost Check
    console.log('\n✓ TEST 3: Security (HTTPS/Localhost)');
    if (window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log(`  ✅ Running on secure context (${window.location.origin})`);
        report.tests.secureContext = 'PASS';
    } else {
        console.log(`  ❌ NOT on secure context. Service Workers require HTTPS or localhost`);
        console.log(`     Current URL: ${window.location.origin}`);
        report.tests.secureContext = 'FAIL - Not HTTPS/localhost';
    }
    
    // Test 4: Web App Installability
    console.log('\n✓ TEST 4: Web App Installability');
    let beforeInstallPromptSupported = false;
    window.addEventListener('beforeinstallprompt', (e) => {
        beforeInstallPromptSupported = true;
        console.log('  ✅ beforeinstallprompt event is available');
        console.log('     (App can be installed to home screen)');
    });
    
    if (manifestLink) {
        console.log('  ✅ Manifest present (required for install)');
        report.tests.installable = 'LIKELY';
    } else {
        console.log('  ⚠️  No manifest - app may not be installable');
        report.tests.installable = 'UNLIKELY';
    }
    
    // Test 5: Notification Permission
    console.log('\n✓ TEST 5: Notification API');
    if ('Notification' in window) {
        console.log(`  ✅ Notification API is supported`);
        console.log(`     Current permission: ${Notification.permission}`);
        report.tests.notificationAPI = 'SUPPORTED';
        report.tests.notificationPermission = Notification.permission;
        
        if (Notification.permission === 'granted') {
            console.log('  ✅ Notifications are enabled');
        } else if (Notification.permission === 'denied') {
            console.log('  ❌ Notifications are blocked by user');
        } else {
            console.log('  ℹ️  User has not yet decided on notifications');
        }
    } else {
        console.log('  ❌ Notification API is NOT supported');
        report.tests.notificationAPI = 'NOT_SUPPORTED';
    }
    
    // Test 6: Cache API
    console.log('\n✓ TEST 6: Cache Storage');
    if ('caches' in window) {
        console.log('  ✅ Cache API is supported');
        try {
            const cacheNames = await caches.keys();
            console.log(`  📦 ${cacheNames.length} cache(s) found:`);
            cacheNames.forEach(name => {
                console.log(`     - ${name}`);
            });
            report.tests.cacheAPI = 'SUPPORTED';
            report.tests.cacheCount = cacheNames.length;
            report.tests.caches = cacheNames;
        } catch (e) {
            console.log(`  ❌ Error accessing caches: ${e.message}`);
            report.tests.cacheAPI = `ERROR: ${e.message}`;
        }
    } else {
        console.log('  ❌ Cache API is NOT supported');
        report.tests.cacheAPI = 'NOT_SUPPORTED';
    }
    
    // Test 7: LocalStorage
    console.log('\n✓ TEST 7: LocalStorage');
    try {
        const testKey = '__pwa_test__';
        localStorage.setItem(testKey, 'test');
        const testValue = localStorage.getItem(testKey);
        localStorage.removeItem(testKey);
        
        if (testValue === 'test') {
            console.log('  ✅ LocalStorage is working');
            report.tests.localStorage = 'WORKING';
        } else {
            console.log('  ❌ LocalStorage read/write failed');
            report.tests.localStorage = 'FAILED';
        }
    } catch (e) {
        console.log(`  ❌ LocalStorage error: ${e.message}`);
        report.tests.localStorage = `ERROR: ${e.message}`;
    }
    
    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('📊 SUMMARY');
    console.log('='.repeat(50));
    
    const passed = Object.values(report.tests).filter(t => 
        typeof t === 'string' && (t === 'PASS' || t.includes('✅') || t === 'SUPPORTED' || t === 'WORKING' || t === 'ACTIVE' || t === 'LIKELY')
    ).length;
    
    const total = Object.keys(report.tests).length;
    console.log(`\n✓ Tests Passed: ${passed}/${total}`);
    
    // Recommendations
    console.log('\n🎯 RECOMMENDATIONS:');
    if (report.tests.serviceWorkerSupport !== 'PASS') {
        console.log('  1. Service Workers not supported - update browser');
    }
    if (report.tests.manifestFound === 'NOT_FOUND') {
        console.log('  1. Create a manifest.json file for better PWA support');
    }
    if (report.tests.secureContext === 'FAIL - Not HTTPS/localhost') {
        console.log('  2. Service Workers require HTTPS or localhost - switch to production HTTPS URL');
    }
    if (report.tests.notificationPermission === 'denied') {
        console.log('  3. Re-enable notifications in browser settings to test notification features');
    }
    
    console.log('\n✅ Diagnostic complete! Full report:');
    console.table(report.tests);
    
    return report;
}

// Helper function to request notification permission
async function requestNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission === 'granted') {
            console.log('✅ Notifications already enabled');
            new Notification('Test Notification', {
                body: 'This is a test notification from Tender Intelligence',
                icon: '/icon-192.png'
            });
        } else if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            console.log(`Notification permission: ${permission}`);
            if (permission === 'granted') {
                new Notification('Notifications Enabled!', {
                    body: 'You will now receive tender alerts',
                    icon: '/icon-192.png'
                });
            }
        } else {
            console.log('❌ Notifications are blocked. Enable them in browser settings.');
        }
    }
}

// Helper function to check if app can be installed
function canInstallApp() {
    return new Promise((resolve) => {
        let installable = false;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            installable = true;
            console.log('✅ App is installable!');
            console.log('💡 Look for "Install" or "Add to Home Screen" option in browser menu');
            resolve(true);
        });
        
        // If event doesn't fire in 2 seconds, app is not installable
        setTimeout(() => {
            if (!installable) {
                console.log('⚠️  App may not be installable. Check PWA diagnostics.');
                resolve(false);
            }
        }, 2000);
    });
}

// Run diagnostics automatically and log to console
console.log('%c🚀 PWA Diagnostics Ready', 'color: #667eea; font-size: 16px; font-weight: bold;');
console.log('%cRun diagnosePWA() to test your PWA setup', 'color: #888; font-size: 12px;');
console.log('%cOr use: requestNotificationPermission() or canInstallApp()', 'color: #888; font-size: 12px;');
