/**
 * Tender Intelligence - Advanced Filtering & Search
 * Multi-select filters, smart search, and saved searches
 */

class AdvancedFilters {
    constructor() {
        this.activeFilters = {
            sources: new Set(),
            priorities: new Set(),
            companies: new Set(),
            categories: new Set(),
            dateRange: { start: null, end: null },
            searchTerm: '',
            savedSearches: this.loadSavedSearches()
        };
        
        this.allTenders = [];
        this.onFilterChange = null; // Callback for when filters change
    }

    loadSavedSearches() {
        try {
            const saved = localStorage.getItem('ti_saved_searches');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            console.warn('Failed to load saved searches:', e);
            return [];
        }
    }

    saveSearch(name, filters = null) {
        const filtersToSave = filters || { ...this.activeFilters };
        
        // Convert Sets to Arrays for JSON serialization
        const serializable = {
            sources: [...filtersToSave.sources],
            priorities: [...filtersToSave.priorities],
            companies: [...filtersToSave.companies],
            categories: [...filtersToSave.categories],
            dateRange: filtersToSave.dateRange,
            searchTerm: filtersToSave.searchTerm
        };
        
        this.activeFilters.savedSearches.push({
            name,
            filters: serializable,
            date: new Date().toISOString()
        });
        
        try {
            localStorage.setItem('ti_saved_searches', JSON.stringify(this.activeFilters.savedSearches));
        } catch (e) {
            console.warn('Failed to save search:', e);
        }
    }

    loadSearch(searchName) {
        const saved = this.activeFilters.savedSearches.find(s => s.name === searchName);
        if (!saved) return false;
        
        // Restore filters from saved search
        this.activeFilters.sources = new Set(saved.filters.sources || []);
        this.activeFilters.priorities = new Set(saved.filters.priorities || []);
        this.activeFilters.companies = new Set(saved.filters.companies || []);
        this.activeFilters.categories = new Set(saved.filters.categories || []);
        this.activeFilters.dateRange = saved.filters.dateRange || { start: null, end: null };
        this.activeFilters.searchTerm = saved.filters.searchTerm || '';
        
        return true;
    }

    deleteSavedSearch(searchName) {
        this.activeFilters.savedSearches = this.activeFilters.savedSearches.filter(s => s.name !== searchName);
        try {
            localStorage.setItem('ti_saved_searches', JSON.stringify(this.activeFilters.savedSearches));
        } catch (e) {
            console.warn('Failed to delete search:', e);
        }
    }

    setTenders(tenders) {
        this.allTenders = tenders;
    }

    toggleFilter(type, value) {
        if (this.activeFilters[type] instanceof Set) {
            if (this.activeFilters[type].has(value)) {
                this.activeFilters[type].delete(value);
            } else {
                this.activeFilters[type].add(value);
            }
            
            if (this.onFilterChange) {
                this.onFilterChange(this.getFilteredTenders());
            }
        }
    }

    setDateRange(start, end) {
        this.activeFilters.dateRange = { start, end };
        if (this.onFilterChange) {
            this.onFilterChange(this.getFilteredTenders());
        }
    }

    setSearchTerm(term) {
        this.activeFilters.searchTerm = term.toLowerCase().trim();
        if (this.onFilterChange) {
            this.onFilterChange(this.getFilteredTenders());
        }
    }

    clearAllFilters() {
        this.activeFilters.sources.clear();
        this.activeFilters.priorities.clear();
        this.activeFilters.companies.clear();
        this.activeFilters.categories.clear();
        this.activeFilters.dateRange = { start: null, end: null };
        this.activeFilters.searchTerm = '';
        
        if (this.onFilterChange) {
            this.onFilterChange(this.getFilteredTenders());
        }
    }

    getFilteredTenders() {
        return this.applyFilters(this.allTenders);
    }

    applyFilters(tenders) {
        return tenders.filter(tenderItem => {
            const tender = tenderItem.tender || tenderItem;
            
            // Source filter
            if (this.activeFilters.sources.size > 0) {
                const source = (tender.source || '').trim();
                if (!this.activeFilters.sources.has(source)) return false;
            }

            // Priority filter
            if (this.activeFilters.priorities.size > 0) {
                const priority = (tender.priority || tender.scores?.priority || '').toUpperCase();
                if (!this.activeFilters.priorities.has(priority)) return false;
            }

            // Company filter
            if (this.activeFilters.companies.size > 0) {
                const company = (tender.company || tender.category || '').trim();
                if (!this.activeFilters.companies.has(company)) return false;
            }

            // Category filter
            if (this.activeFilters.categories.size > 0) {
                const tenderCategories = tenderItem.classification?.categories || [];
                const hasMatchingCategory = tenderCategories.some(cat => 
                    this.activeFilters.categories.has(cat)
                );
                if (!hasMatchingCategory) return false;
            }

            // Date range filter
            if (this.activeFilters.dateRange.start || this.activeFilters.dateRange.end) {
                const closingDate = tender.closing_date ? new Date(tender.closing_date) : null;
                if (!closingDate) return false;
                
                if (this.activeFilters.dateRange.start) {
                    const startDate = new Date(this.activeFilters.dateRange.start);
                    if (closingDate < startDate) return false;
                }
                
                if (this.activeFilters.dateRange.end) {
                    const endDate = new Date(this.activeFilters.dateRange.end);
                    if (closingDate > endDate) return false;
                }
            }

            // Search term filter
            if (this.activeFilters.searchTerm) {
                const searchFields = [
                    tender.ref,
                    tender.title,
                    tender.description,
                    tender.source,
                    tender.client,
                    tender.category,
                    ...(tenderItem.classification?.categories || [])
                ].map(field => (field || '').toLowerCase());
                
                const matches = searchFields.some(field => 
                    field.includes(this.activeFilters.searchTerm)
                );
                
                if (!matches) return false;
            }

            return true;
        });
    }

    getUniqueValues(tenders, field) {
        const values = new Set();
        tenders.forEach(item => {
            const tender = item.tender || item;
            let value;
            
            switch(field) {
                case 'source':
                    value = (tender.source || '').trim();
                    break;
                case 'priority':
                    value = (tender.priority || tender.scores?.priority || '').toUpperCase();
                    break;
                case 'company':
                    value = (tender.company || tender.category || '').trim();
                    break;
                case 'categories':
                    (item.classification?.categories || []).forEach(cat => values.add(cat));
                    return;
                default:
                    value = tender[field];
            }
            
            if (value) values.add(value);
        });
        
        return Array.from(values).sort();
    }

    getActiveFilterCount() {
        let count = 0;
        count += this.activeFilters.sources.size;
        count += this.activeFilters.priorities.size;
        count += this.activeFilters.companies.size;
        count += this.activeFilters.categories.size;
        if (this.activeFilters.dateRange.start || this.activeFilters.dateRange.end) count++;
        if (this.activeFilters.searchTerm) count++;
        return count;
    }
}

// Smart search patterns and queries
class SmartSearch {
    static patterns = {
        closingToday: /\b(today|closes today)\b/i,
        closingThisWeek: /\b(this week|week)\b/i,
        closingNextWeek: /\b(next week)\b/i,
        closingSoon: /\b(urgent|soon|closing soon)\b/i,
        highPriority: /\b(high priority|critical|urgent)\b/i,
        specificSource: /\b(eskom|transnet|rand water|treasury|sanral|umgeni)\b/i,
        specificCompany: /\b(tes|phakathi)\b/i
    };

    static getDaysUntil(dateStr) {
        if (!dateStr) return null;
        const closing = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        closing.setHours(0, 0, 0, 0);
        return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
    }

    static applySmartFilters(tenders, query) {
        const lowerQuery = query.toLowerCase().trim();
        
        // Check for smart patterns
        if (this.patterns.closingToday.test(lowerQuery)) {
            return tenders.filter(item => {
                const tender = item.tender || item;
                return this.getDaysUntil(tender.closing_date) === 0;
            });
        }
        
        if (this.patterns.closingThisWeek.test(lowerQuery)) {
            return tenders.filter(item => {
                const tender = item.tender || item;
                const days = this.getDaysUntil(tender.closing_date);
                return days !== null && days >= 0 && days <= 7;
            });
        }
        
        if (this.patterns.closingNextWeek.test(lowerQuery)) {
            return tenders.filter(item => {
                const tender = item.tender || item;
                const days = this.getDaysUntil(tender.closing_date);
                return days !== null && days >= 7 && days <= 14;
            });
        }
        
        if (this.patterns.closingSoon.test(lowerQuery)) {
            return tenders.filter(item => {
                const tender = item.tender || item;
                const days = this.getDaysUntil(tender.closing_date);
                return days !== null && days >= 0 && days <= 3;
            });
        }
        
        if (this.patterns.highPriority.test(lowerQuery)) {
            return tenders.filter(item => {
                const tender = item.tender || item;
                const priority = (tender.priority || tender.scores?.priority || '').toUpperCase();
                return priority === 'HIGH';
            });
        }
        
        // Standard text search
        return tenders.filter(item => {
            const tender = item.tender || item;
            const searchFields = [
                tender.ref,
                tender.title,
                tender.description,
                tender.source,
                tender.client,
                tender.category
            ].map(field => (field || '').toLowerCase());
            
            return searchFields.some(field => field.includes(lowerQuery));
        });
    }
}

// Export for use in main script
window.AdvancedFilters = AdvancedFilters;
window.SmartSearch = SmartSearch;
