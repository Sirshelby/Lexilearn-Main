import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the API runs separately on :8000. Proxying keeps it
    // same-origin, so the refresh cookie works exactly like in production.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
