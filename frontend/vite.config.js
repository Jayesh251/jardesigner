import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/',  // Changed from '/jardesigner/' to '/' for packaged version
  build: {
    outDir: path.resolve(__dirname, '../jardesigner/server/static'),
    emptyOutDir: true,
  },
});
