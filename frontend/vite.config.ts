import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      // Control plane REST + SSE. `/api/events` is a stream — disable buffering for SSE.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
