import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // 127.0.0.1, not "localhost": uvicorn's default bind is IPv4-only, but
      // on many Windows/Node setups "localhost" resolves to the IPv6 ::1
      // first, which uvicorn isn't listening on — proxy requests get
      // ECONNREFUSED even though the backend is up and reachable via IPv4.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
