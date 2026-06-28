import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
  root: ".",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "fs-shared": path.resolve(__dirname, "shared/fs-shared.js"),
        auth: path.resolve(__dirname, "shared/auth.js"),
        ui: path.resolve(__dirname, "shared/ui.js"),
        demo: path.resolve(__dirname, "shared/demo.js"),
        "voice-assistant": path.resolve(__dirname, "shared/voice-assistant.js"),
        "focus-timer": path.resolve(__dirname, "shared/focus-timer.js"),
        "knowledge-graph": path.resolve(__dirname, "shared/knowledge-graph.js"),
        "ai-calendar": path.resolve(__dirname, "shared/ai-calendar.js"),
      },
      output: {
        // Deterministic filenames for predictable script-tag references
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
    cssCodeSplit: false,
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8080",
    },
  },
});
