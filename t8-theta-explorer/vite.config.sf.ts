import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// Single-file build: inline ALL JS, CSS, and font assets into one index.html,
// so the app is a fully self-contained, statically-hostable page.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  base: './',
  build: {
    assetsInlineLimit: 100000000, // inline every asset (incl. KaTeX fonts) as data URIs
    cssCodeSplit: false,
    chunkSizeWarningLimit: 100000,
    outDir: 'dist-sf',
  },
});
