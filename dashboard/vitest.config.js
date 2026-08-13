import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

const dashboardDir = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        'dist/',
        'public/',
        'icons/',
        'screenshots/',
      ],
    },
  },
  resolve: {
    alias: {
      '@': resolve(dashboardDir, './js'),
    },
  },
});
