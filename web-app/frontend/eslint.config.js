import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  { ignores: ['dist', 'node_modules', 'legacy'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
    },
    rules: {
      'react/jsx-uses-vars': 'error',
      ...reactHooks.configs.recommended.rules,
      'react/jsx-uses-react': 'off',
      'react/react-in-jsx-scope': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_|React',
          caughtErrors: 'none',
        },
      ],

      // Limite estrito de tamanho de arquivos em linhas para manter componentização modular
      'max-lines': [
        'error',
        {
          max: 260,
          skipBlankLines: true,
          skipComments: true,
        },
      ],
    },
    settings: {
      react: { version: '19.0' },
    },
  },
];
