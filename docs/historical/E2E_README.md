Playwright E2E tests

Prerequisites:
- Node.js and npm
- Start the backend API: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Start the frontend dev server: `npm start` (serves on http://localhost:5173)

Install dependencies and Playwright browsers:

```bash
npm install
npm run install:playwright
```

Run tests:

```bash
npx playwright test
```

Notes:
- Tests assume the backend API is available at `http://localhost:8000`.
- Playwright will generate an HTML report in `playwright-report/` on completion.

CI instructions:

- The repository includes a GitHub Actions workflow at `.github/workflows/playwright-e2e.yml` that:
	- Installs Python dependencies from `backend/requirements.txt`.
	- Starts the backend using `uvicorn` from the virtualenv (assumes `.venv` exists in runner or adjust accordingly).
	- Installs Node dependencies and Playwright browsers, starts the frontend dev server via `npm start` and runs `npx playwright test`.
	- Uploads the Playwright HTML report as an artifact named `playwright-report`.

Notes about CI runner environment:
- The workflow assumes a Python virtual environment is available at `.venv`. If your CI environment doesn't use a pre-created venv, modify the `Start backend` step to use `python -m uvicorn backend.main:app` after installing deps.
- If the frontend script or port differs, update `npm start` or the port in the workflow.
