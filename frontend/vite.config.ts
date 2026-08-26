import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: mode === "demo" ? "demo.html" : "index.html"
    }
  },
  server: {
    port: 5173
  }
}));
