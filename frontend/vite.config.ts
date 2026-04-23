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
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
      // Django serves uploaded files (template logos, contract PDFs,
      // QR assets) under /media/. Without this proxy the SPA's
      // <img src="/media/..."> would hit the Vite dev server and 404.
      "/media": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
})
