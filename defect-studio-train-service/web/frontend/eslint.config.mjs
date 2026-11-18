import config from '@defect-studio/eslint-config/react';

export default [
  ...config,
  {
    // Node CommonJS tooling (e.g. the Storybook test-runner setup) runs outside the
    // app bundle, so it needs Node + test-runner globals the browser preset lacks.
    files: ['**/*.cjs'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: {
        require: 'readonly',
        module: 'writable',
        exports: 'writable',
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        beforeEach: 'readonly',
      },
    },
  },
];
