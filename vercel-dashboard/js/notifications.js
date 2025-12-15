/**
 * Tender Intelligence - Real-time Notifications Manager
 * Handles browser notifications for urgent tenders
 */

class NotificationManager {
    constructor() {
        this.permission = 'Notification' in window ? Notification.permission : 'denied';
        this.urgentTenders = new Set();
        this.checkInterval = null;
    }

    async requestPermission() {
        if (!('Notification' in window)) {
            console.warn('Browser does not support notifications');
            return false;
        }

        if (this.permission === 'default') {
            this.permission = await Notification.requestPermission();
        }
        
        return this.permission === 'granted';
    }

    showNotification(title, options = {}) {
        if (this.permission === 'granted') {
            const notification = new Notification(title, {
                icon: '/icon-192.png',
                badge: '/icon-96.png',
                ...options
            });

            // Handle notification click
            notification.onclick = (event) => {
                event.preventDefault();
                window.focus();
                if (options.data?.url) {
                    window.open(options.data.url, '_blank');
                }
                notification.close();
            };

            return notification;
        }
        return null;
    }

    checkUrgentTenders(tenders) {
        if (!tenders || !Array.isArray(tenders)) return;

        const now = new Date();
        const urgentThreshold = 3; // days

        tenders.forEach(tenderItem => {
            const tender = tenderItem.tender || tenderItem;
            const tenderId = tender.ref || tender.id;
            
            if (!tenderId || this.urgentTenders.has(tenderId)) return;

            const days = this.getDaysUntil(tender.closing_date);
            const priority = (tender.priority || tender.scores?.priority || '').toUpperCase();
            
            // Notify for HIGH priority tenders closing soon
            if (days !== null && days <= urgentThreshold && days >= 0 && priority === 'HIGH') {
                const title = days === 0 ? '🔴 URGENT: Tender Closes TODAY!' : 
                             days === 1 ? '🔴 URGENT: Tender Closes TOMORROW!' :
                             `⚠️ Urgent Tender Alert - ${days} Days Left`;
                
                const body = `${tender.ref || 'Unknown Ref'}: ${(tender.title || '').substring(0, 80)}${tender.title?.length > 80 ? '...' : ''}`;

                this.showNotification(title, {
                    body: body,
                    tag: tenderId,
                    requireInteraction: days <= 1, // Keep notification visible for immediate deadlines
                    data: { 
                        url: tender.url, 
                        ref: tender.ref,
                        closingDate: tender.closing_date
                    },
                    vibrate: [200, 100, 200] // Vibration pattern for mobile
                });

                this.urgentTenders.add(tenderId);
                
                // Store in localStorage to persist across sessions
                this.saveNotifiedTenders();
            }
        });
    }

    getDaysUntil(dateStr) {
        if (!dateStr) return null;
        const closing = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        closing.setHours(0, 0, 0, 0);
        return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
    }

    setupAutoCheck(tenders, intervalMinutes = 30) {
        // Initial check
        this.checkUrgentTenders(tenders);

        // Setup periodic checking
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }

        this.checkInterval = setInterval(() => {
            this.checkUrgentTenders(tenders);
        }, intervalMinutes * 60 * 1000);
    }

    stopAutoCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    saveNotifiedTenders() {
        try {
            localStorage.setItem('ti_notified_tenders', JSON.stringify([...this.urgentTenders]));
        } catch (e) {
            console.warn('Failed to save notified tenders:', e);
        }
    }

    loadNotifiedTenders() {
        try {
            const stored = localStorage.getItem('ti_notified_tenders');
            if (stored) {
                this.urgentTenders = new Set(JSON.parse(stored));
            }
        } catch (e) {
            console.warn('Failed to load notified tenders:', e);
        }
    }

    clearOldNotifications() {
        // Clear notifications for tenders that have already closed
        const tendersArray = [...this.urgentTenders];
        // Note: We'd need access to tender data to check closing dates
        // This is a placeholder for future enhancement
        this.urgentTenders.clear();
        this.saveNotifiedTenders();
    }

    getStatus() {
        return {
            permission: this.permission,
            enabled: this.permission === 'granted',
            notifiedCount: this.urgentTenders.size,
            autoCheckActive: this.checkInterval !== null
        };
    }
}

// Export for use in main script
window.NotificationManager = NotificationManager;
