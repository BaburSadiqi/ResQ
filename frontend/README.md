# ResQ frontend

React, TypeScript, Vite, Leaflet, and Recharts client for the ResQ catalog API.

## Run locally

1. Start the backend from `backend` (after configuring PostgreSQL and ingesting catalog data):

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

2. In a second terminal, configure and start the frontend:

   ```powershell
   cd frontend
   Copy-Item .env.example .env
   npm install
   npm run dev
   ```

`VITE_API_BASE_URL` centralizes the backend origin. Leave it blank during local development: Vite proxies `/api` to `http://127.0.0.1:8000`, avoiding a browser cross-origin request. Override the proxy destination with `VITE_API_PROXY_TARGET` if the backend listens elsewhere. Set `VITE_API_BASE_URL` to the deployed backend origin when the client is served separately (and configure that backend to allow the client's origin). The frontend calls the API's real `/api/v1` routes. Build a production bundle with `npm run build`.

The map uses OpenStreetMap raster tiles and requires internet access for tiles. Keep the visible OpenStreetMap attribution in the map, and follow the tile usage policy for `tile.openstreetmap.org`; it is intended for normal interactive map use, not bulk or offline downloads. The map displays only records returned by the configured ResQ API; an empty catalog is shown as an empty state rather than fabricated data.
