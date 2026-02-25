import js from '@eslint/js';

export default [
  {
    ignores: ['node_modules/**', 'public/**', 'icons/**', 'screenshots/**', 'dist/**'],
  },
  js.configs.recommended,
  {
    files: ['js/**/*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        console: 'readonly',
        Chart: 'readonly',
        Hammer: 'readonly',
        XLSX: 'readonly',
        jspdf: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
      // Legacy modules rely on globals and generated patterns; keep lint focused on actionable issues.
      'no-undef': 'off',
    },
  },
];
