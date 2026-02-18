# LED State API (Flask) - Docker + Render

## Endpoints
- GET  /healthz
- GET  /api/state
- POST /api/state  JSON: {"color":"#RRGGBB","count":0..8}

## Local (Docker)
Build:
  docker build -t led-api-render .

Run:
  docker run --rm -p 5000:5000 -e PORT=5000 led-api-render

Test:
  curl http://localhost:5000/healthz
  curl http://localhost:5000/api/state
  curl -X POST http://localhost:5000/api/state -H "Content-Type: application/json" -d '{"color":"#00ff88","count":5}'

## Render notes
- Bind to $PORT (Render default is 10000).
- If you need persistence for state.json across redeploys, attach a Persistent Disk and set:
    DATA_DIR=/var/data
  and mount disk at /var/data.
- Configure CORS in production:
    CORS_ORIGINS=https://tu-front.com
