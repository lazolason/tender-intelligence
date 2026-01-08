/**
 * Test setup for Vitest
 */

import { beforeEach, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/dom';
import '@testing-library/jest-dom';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = String(value);
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index) => {
      return Object.keys(store)[index] || null;
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ tenders: [] })
  })
);

// Mock Chart.js
global.Chart = vi.fn(() => ({
  update: vi.fn(),
  destroy: vi.fn()
}));

// Mock Hammer.js
global.Hammer = {
  Manager: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    destroy: vi.fn()
  }))
};
