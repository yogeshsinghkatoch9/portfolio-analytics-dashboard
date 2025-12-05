# Docker quickstart

This project includes a `Dockerfile.backend` and `docker-compose.yml` for running the backend and a static frontend via `nginx`.

Build and start services:

```bash
cd /path/to/portfolio-analytics-dashboard
docker-compose up -d --build
```

Developer quick commands (provided via `Makefile`):

```bash
make build    # docker-compose build
make up       # docker-compose up -d --build
make down     # docker-compose down
make logs     # follow logs
make ps       # show container status
```

Notes:
- Backend: `http://localhost:8000`
- Frontend (when using docker-compose): `http://localhost:3000`
- If you have a local uvicorn already running on port 8000, stop it first (`pkill -f uvicorn`).
