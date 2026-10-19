import { createServer } from "../../../frontend/node_modules/vite/dist/node/index.js";
import { fileURLToPath } from "node:url";
const server = await createServer({
  root: fileURLToPath(new URL("../../../frontend", import.meta.url)), configFile: false,
  server: { host: "127.0.0.1", port: 51208, strictPort: true,
    proxy: { "/api": "http://127.0.0.1:58208", "/health": "http://127.0.0.1:58208" } },
});
await server.listen();
server.printUrls();
