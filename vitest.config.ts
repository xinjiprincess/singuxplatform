import { createRequire } from 'module';
import path from 'path';
import { configDefaults, defineConfig } from 'vitest/config';

const require = createRequire(import.meta.url);
const reactJsxRuntime = require.resolve('react/jsx-runtime');
const reactJsxDevRuntime = require.resolve('react/jsx-dev-runtime');
const umiEntry = require.resolve('@umijs/max');

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setupTests.ts',
    exclude: [
      ...configDefaults.exclude,
      'tests/**/*[Vv]2*.test.{ts,tsx}',
      // tests/*.test.cjs 是给 node:test 用的（跑真实的 shell 更新脚本），
      // vitest 收进来只会得到 No test suite found。用 npm run test:node 执行。
      'tests/**/*.test.cjs',
    ],
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'react/jsx-runtime': reactJsxRuntime,
      'react/jsx-dev-runtime': reactJsxDevRuntime,
      umi: umiEntry,
    },
    css: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'react/jsx-runtime': reactJsxRuntime,
      'react/jsx-dev-runtime': reactJsxDevRuntime,
      umi: umiEntry,
    },
    dedupe: ['react', 'react-dom'],
  },
});
