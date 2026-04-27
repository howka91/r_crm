import { fileURLToPath, URL } from "node:url"

import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    watch: {
      // In Docker on Windows the default file-watching is unreliable; poll.
      usePolling: true,
      interval: 500,
    },
    // Proxy /api/* to the backend container. Lets the SPA call a
    // same-origin relative URL (`/api/v1/...`) regardless of whether the
    // browser reaches Vite via `localhost:5173` or a LAN IP like
    // `192.168.1.121:5173` — the hardcoded host goes away.
    proxy: {
      // Keep the original Host header (no changeOrigin) so Django's
      // request.build_absolute_uri() returns SPA-reachable URLs like
      // http://localhost:5173/media/... instead of http://backend:8000/...
      // which the browser cannot resolve.
      "/api": {
        target: "http://backend:8000",
      },
      "/media": {
        target: "http://backend:8000",
      },
    },
  },
})
