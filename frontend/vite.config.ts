import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    server: {
      watch: {
        ignored: ["**/public/assets/videoplayback.m4a"],
      },
      proxy: {
        "/api": env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
      },
    },
  };
});
