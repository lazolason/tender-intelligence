/**
 * Tender Intelligence - Analytics & Insights Dashboard
 * Provides analytics, statistics, and keyword analysis
 */

class TenderAnalytics {
    constructor(tenders) {
        this.tenders = tenders;
        this.analytics = this.calculateAnalytics();
    }

    calculateAnalytics() {
        const bySource = {};
        const byDate = {};
        const byPriority = { HIGH: 0, MEDIUM: 0, LOW: 0 };
        const byCompany = {};
        const keywords = {};
        const closingDates = [];

        this.tenders.forEach(item => {
            const tender = item.tender || item;
            
            // Source breakdown
            const source = (tender.source || 'Unknown').trim();
            bySource[source] = (bySource[source] || 0) + 1;

            // Company breakdown
            const company = (tender.company || tender.category || 'Unknown').trim();
            byCompany[company] = (byCompany[company] || 0) + 1;

            // Date grouping
            if (tender.closing_date) {
                const date = tender.closing_date.split('T')[0];
                byDate[date] = (byDate[date] || 0) + 1;
                closingDates.push(new Date(tender.closing_date));
            }

            // Priority count
            const priority = (tender.priority || tender.scores?.priority || 'LOW').toUpperCase();
            byPriority[priority] = (byPriority[priority] || 0) + 1;

            // Keyword extraction
            const text = `${tender.title || ''} ${tender.description || ''} ${tender.category || ''}`.toLowerCase();
            const words = text.split(/\s+/).filter(w => w.length > 4 && !this.isStopWord(w));
            words.forEach(word => {
                keywords[word] = (keywords[word] || 0) + 1;
            });
        });

        return {
            bySource,
            byDate,
            byCompany,
            byPriority,
            keywords,
            closingDates,
            total: this.tenders.length
        };
    }

    isStopWord(word) {
        const stopWords = new Set([
            'tender', 'supply', 'services', 'provision', 'water', 'system',
            'the', 'and', 'for', 'with', 'from', 'to', 'in', 'is', 'a', 'of',
            'request', 'quotation', 'rfq', 'proposal', 'bid', 'quote', 'price'
        ]);
        return stopWords.has(word);
    }

    getTopSource() {
        const sorted = Object.entries(this.analytics.bySource)
            .sort((a, b) => b[1] - a[1]);
        return sorted[0] ? sorted[0][0] : '-';
    }

    getTopCompany() {
        const sorted = Object.entries(this.analytics.byCompany)
            .sort((a, b) => b[1] - a[1]);
        return sorted[0] ? sorted[0][0] : '-';
    }

    getAvgTendersPerWeek() {
        if (this.analytics.closingDates.length === 0) return 0;
        
        const weeks = new Set();
        this.analytics.closingDates.forEach(date => {
            const weekNum = this.getWeekNumber(date);
            weeks.add(weekNum);
        });
        
        return weeks.size > 0 ? Math.round(this.tenders.length / weeks.size) : 0;
    }

    getMostCommonDay() {
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const dayCounts = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
        
        this.analytics.closingDates.forEach(date => {
            dayCounts[date.getDay()]++;
        });
        
        const maxDay = Object.entries(dayCounts).reduce((max, [day, count]) => 
            count > max[1] ? [day, count] : max
        );
        
        return dayNames[parseInt(maxDay[0])] || '-';
    }

    getWeekNumber(date) {
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() + 4 - (d.getDay() || 7));
        const yearStart = new Date(d.getFullYear(), 0, 1);
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }

    getTopKeywords(limit = 20) {
        return Object.entries(this.analytics.keywords)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([word]) => word);
    }

    getKeywordCloud(limit = 20) {
        const keywords = Object.entries(this.analytics.keywords)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit);
        
        if (keywords.length === 0) return [];
        
        const maxCount = keywords[0][1];
        const minCount = keywords[keywords.length - 1][1];
        const range = maxCount - minCount || 1;
        
        return keywords.map(([word, count]) => {
            const normalizedSize = (count - minCount) / range;
            const size = 0.8 + normalizedSize * 1.2; // Size between 0.8rem and 2rem
            const opacity = 0.5 + normalizedSize * 0.5; // Opacity between 0.5 and 1.0
            
            return { word, count, size, opacity };
        });
    }

    getPriorityDistribution() {
        return this.analytics.byPriority;
    }

    getSourceDistribution() {
        return this.analytics.bySource;
    }

    getCompanyDistribution() {
        return this.analytics.byCompany;
    }

    renderKeywordCloud() {
        const keywords = this.getKeywordCloud();
        
        return keywords.map(({ word, size, opacity }) => 
            `<span style="
                font-size: ${size}rem; 
                opacity: ${opacity}; 
                margin: 8px; 
                display: inline-block;
                color: #667eea;
                font-weight: ${opacity > 0.75 ? '600' : '400'};
                cursor: pointer;
                transition: all 0.2s;
                border-radius: 8px;
                padding: 4px 8px;
                "
                onmouseover="this.style.background='rgba(102,126,234,0.2)'; this.style.transform='scale(1.1)';"
                onmouseout="this.style.background='transparent'; this.style.transform='scale(1)';
                ">${word}</span>`
        ).join('');
    }

    renderPriorityChart() {
        const { HIGH, MEDIUM, LOW } = this.analytics.byPriority;
        const total = HIGH + MEDIUM + LOW;
        
        if (total === 0) return '<p style="color: #888;">No priority data available</p>';
        
        const highPct = Math.round((HIGH / total) * 100);
        const mediumPct = Math.round((MEDIUM / total) * 100);
        const lowPct = Math.round((LOW / total) * 100);
        
        return `
            <div style="display: flex; gap: 4px; margin-top: 10px; height: 24px; border-radius: 12px; overflow: hidden; background: rgba(255,255,255,0.05);">
                <div style="width: ${highPct}%; background: #ff6b6b; position: relative;" title="HIGH: ${HIGH}">
                    ${highPct > 10 ? `<span style="color: white; font-size: 0.75rem; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);">${highPct}%</span>` : ''}
                </div>
                <div style="width: ${mediumPct}%; background: #feca57; position: relative;" title="MEDIUM: ${MEDIUM}">
                    ${mediumPct > 10 ? `<span style="color: #333; font-size: 0.75rem; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);">${mediumPct}%</span>` : ''}
                </div>
                <div style="width: ${lowPct}%; background: #48dbfb; position: relative;" title="LOW: ${LOW}">
                    ${lowPct > 10 ? `<span style="color: #333; font-size: 0.75rem; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);">${lowPct}%</span>` : ''}
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 12px; font-size: 0.85rem;">
                <span>🔴 HIGH: <strong>${HIGH}</strong></span>
                <span>🟡 MEDIUM: <strong>${MEDIUM}</strong></span>
                <span>🔵 LOW: <strong>${LOW}</strong></span>
            </div>
        `;
    }

    renderSourceStats() {
        const entries = Object.entries(this.analytics.bySource)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8);
        
        if (entries.length === 0) return '<p style="color: #888;">No source data available</p>';
        
        const maxCount = Math.max(...entries.map(e => e[1]));
        
        return entries.map(([source, count]) => {
            const width = Math.round((count / maxCount) * 100);
            return `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 0.9rem;">
                        <span style="color: #ccc;">${source}</span>
                        <span style="color: #667eea; font-weight: 600;">${count}</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); border-radius: 8px; height: 8px; overflow: hidden;">
                        <div style="width: ${width}%; height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    generateSummary() {
        return {
            totalTenders: this.analytics.total,
            topSource: this.getTopSource(),
            topCompany: this.getTopCompany(),
            avgTendersPerWeek: this.getAvgTendersPerWeek(),
            mostCommonDay: this.getMostCommonDay(),
            highPriority: this.analytics.byPriority.HIGH,
            mediumPriority: this.analytics.byPriority.MEDIUM,
            lowPriority: this.analytics.byPriority.LOW
        };
    }
}

// Export for use in main script
window.TenderAnalytics = TenderAnalytics;
