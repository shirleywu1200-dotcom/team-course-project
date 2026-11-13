/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 開發時把 /api 轉給本機後端（只綁 127.0.0.1）。
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8000" } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    environmentOptions: { jsdom: { url: "http://localhost:3000" } },
  },
});
