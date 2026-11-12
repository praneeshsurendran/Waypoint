import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import hooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

// Dependency rules apply equally to aliases and relative imports.
const restrict = (...patterns) => ({
  'no-restricted-imports': [
    'error',
    { patterns: patterns.filter((pattern) => pattern.group.length) },
  ],
})
const layer = (groups, message) => ({ group: groups, message })
const noPages = layer(
  ['@/app/*/*-routes', '@/app/router/**', '@/app/*/*Page*', '**/*Page*', '**/*-routes'],
  'Reusable UI must not import page implementations or route registries.',
)
const noAdapters = layer(
  [
    '@/infrastructure/adapters/**',
    '@/infrastructure/storage/**',
    '**/infrastructure/adapters/**',
    '**/infrastructure/storage/**',
  ],
  'UI uses query hooks, shared contracts, and session integrations.',
)
const boundaries = [
  {
    files: ['src/app/**/*.{ts,tsx}'],
    ignores: ['src/app/providers/**'],
    rules: restrict(
      noAdapters,
      layer(
        ['@tanstack/react-query', '@/api/endpoints/**', '@/api/client/apiClient'],
        'Pages compose query hooks; HTTP operations and query configuration live outside pages.',
      ),
    ),
  },

  {
    files: [
      'src/types/**/*.ts',
      'src/services/**/*.ts',
      'src/utils/**/*.ts',
      'src/schemas/**/*.ts',
      'src/mappers/**/*.ts',
    ],
    rules: restrict(
      layer(
        [
          'dexie',
          '@/api/**',
          '@/infrastructure/**',
          '@/app/**',
          '@/components/**',
          '@/hooks/**',
          '@/queries/**',
          '**/infrastructure/**',
        ],
        'Types, services, and utilities stay independent of transport, storage, pages, and React hooks.',
      ),
    ),
  },
  ...['atoms', 'molecules', 'organisms', 'templates'].map((category, index, categories) => ({
    files: [`src/components/${category}/**/*.{ts,tsx}`],
    rules: restrict(
      noPages,
      noAdapters,
      layer(
        categories
          .slice(index + 1)
          .flatMap((higher) => [`@/components/${higher}/**`, `**/components/${higher}/**`]),
        'Atomic components depend only on their category or lower categories.',
      ),
    ),
  })),
  {
    files: ['src/components/atoms/**/*.{ts,tsx}'],
    rules: restrict(
      noPages,
      noAdapters,
      layer(
        [
          '@/components/molecules/**',
          '@/components/organisms/**',
          '@/components/templates/**',
          '@/queries/**',
          '@/api/**',
          '@/app/**',
        ],
        'Atoms are presentation primitives without server operations or application dependencies.',
      ),
    ),
  },
  {
    files: ['src/api/**/*.{ts,tsx}'],
    rules: restrict(
      layer(
        [
          'react',
          'react-*',
          '@tanstack/react-query',
          '@/components/**',
          '@/app/**',
          '@/queries/**',
          '@/infrastructure/adapters/**',
        ],
        'API contains transport; types own DTOs and adapters coordinate persistence and mapping.',
      ),
    ),
  },
]

export default tseslint.config(
  {
    ignores: [
      'dist',
      'src/api/generated/**',
      'tools/contracts/node_modules/**',
      'node_modules',
      '.npm-cache',
      '.playwright',
      'playwright-report',
      'test-results',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { 'react-hooks': hooks },
    rules: { ...hooks.configs.recommended.rules },
  },
  ...boundaries,
  { files: ['**/*.js'], languageOptions: { globals: globals.node } },
  {
    files: ['public/delivery-notifications.js'],
    languageOptions: { globals: globals.serviceworker },
  },
  { files: ['tools/*.mjs'], languageOptions: { globals: { ...globals.node, ...globals.browser } } },
)
