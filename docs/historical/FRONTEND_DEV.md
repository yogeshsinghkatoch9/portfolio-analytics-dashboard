Front-end development quickstart

This project includes a tiny dev server using `live-server` for fast local development with live-reload.

Requirements
- Node.js (16+ recommended)
- npm

Install dev dependencies:

```bash
npm install
# or only live-server
npm run install:live
```

Start the frontend dev server (serves `frontend/` on port 5173):

```bash
npm start
```

Open `http://localhost:5173` to view the app (it will serve `frontend/index.html`).

Notes
- `live-server` supports live-reload on file changes in the `frontend/` directory.
- If you prefer another dev server (Vite/parcel), replace scripts in `package.json` accordingly.
