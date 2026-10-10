import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    rollupOptions: {
      onwarn(warning, handler) {
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && warning.message.includes('use client')) return;
        handler(warning);
      },
    },
  },
  esbuild: { jsx: 'automatic' },
});
