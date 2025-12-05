# CI/CD Guide

## Overview

This project includes a comprehensive CI/CD setup using GitHub Actions:

- **Automated Testing**: Playwright E2E tests on every push and PR
- **Backend Validation**: Python unit tests (pytest)
- **Service Health Checks**: Verifies backend API and frontend dev server start correctly
- **Artifact Storage**: HTML test reports uploaded and retained for 30 days

---

## GitHub Actions Workflow

### File Location
`.github/workflows/playwright-e2e.yml`

### Triggers
- Push to `main` or `master` branches
- Pull requests to `main` or `master` branches

### Workflow Steps

#### 1. Setup Environment
```yaml
- Checkout repository
- Set up Python 3.11
- Create Python virtual environment
- Upgrade pip
```

#### 2. Install Dependencies
```yaml
- Install Python packages from backend/requirements.txt
- Set up Node.js 18
- Install npm dependencies (npm ci)
- Install Playwright browsers with system dependencies
```

#### 3. Start Services
```yaml
- Start backend API (uvicorn) on port 8000
- Start frontend dev server (live-server) on port 5173
- Wait for both services to be ready (curl health checks)
```

#### 4. Run Tests
```yaml
- Execute: npx playwright test --reporter=html
- Timeout: 30 minutes
- Reporter: HTML (generates playwright-report/)
```

#### 5. Upload Artifacts
```yaml
- Artifact name: playwright-report
- Path: playwright-report/
- Retention: 30 days
- Condition: always() [even if tests fail]
```

---

## Running Tests Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Virtual environment activated

### Backend Unit Tests

```bash
# Activate venv
source .venv/bin/activate

# Run tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_portfolio_api.py::test_portfolio_crud_cycle -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html
```

### Frontend E2E Tests

**Terminal 1 (Backend):**
```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend Dev Server):**
```bash
npm start
```

**Terminal 3 (Run Tests):**
```bash
# Install Playwright (first time only)
npm run install:playwright

# Run tests
npx playwright test

# Run tests with UI
npx playwright test --ui

# Run specific test
npx playwright test --grep "save"

# Run in headed mode (show browser)
npx playwright test --headed
```

---

## CI Artifacts & Reports

### Where to Find Reports

1. **GitHub Actions Tab**
   - Go to repository → Actions tab
   - Select `Playwright E2E` workflow
   - Click the specific run
   - Scroll to "Artifacts" section
   - Download `playwright-report`

2. **Local Playwright Report**
   After running `npx playwright test`, view with:
   ```bash
   npx playwright show-report
   ```

### Report Contents
- Test results summary (passed/failed/skipped)
- Timeline of each test
- Screenshots and videos (if configured)
- Errors and stack traces for failed tests

---

## Troubleshooting CI Failures

### Backend Fails to Start
**Error**: `backend_uvicorn.log` shows import errors

**Solutions**:
```bash
# 1. Verify requirements.txt
cat backend/requirements.txt

# 2. Reinstall dependencies locally
source .venv/bin/activate
pip install -r backend/requirements.txt --force-reinstall

# 3. Check Python version matches (3.11+)
python --version

# 4. Run backend locally to test
uvicorn backend.main:app --reload
```

### Frontend Fails to Start
**Error**: `frontend_dev.log` shows port in use or npm error

**Solutions**:
```bash
# 1. Check npm is installed
npm --version

# 2. Reinstall node modules
rm -rf node_modules package-lock.json
npm install

# 3. Test locally
npm start

# 4. Verify port 5173 is free
lsof -i :5173
```

### Playwright Tests Fail
**Error**: Tests timeout or browser fails to launch

**Solutions**:
```bash
# 1. Ensure backend is responding
curl http://127.0.0.1:8000/

# 2. Ensure frontend is responding
curl http://127.0.0.1:5173/

# 3. Reinstall Playwright
npm run install:playwright

# 4. Run with debug output
PWDEBUG=1 npx playwright test --headed
```

---

## Extending CI

### Add Another Workflow

1. Create `.github/workflows/your-workflow.yml`:

```yaml
name: Your Workflow Name

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  your-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      # Add your steps...
```

2. Common actions:
   - `actions/checkout@v4` - Clone repo
   - `actions/setup-python@v4` - Set up Python
   - `actions/setup-node@v4` - Set up Node
   - `actions/upload-artifact@v4` - Upload artifacts

### Add Linting

```yaml
- name: Lint Python
  run: |
    source .venv/bin/activate
    pip install flake8 black
    black --check backend tests
    flake8 backend tests
```

### Add Type Checking

```yaml
- name: Type Check
  run: |
    source .venv/bin/activate
    pip install mypy
    mypy backend
```

---

## Best Practices

### For Local Development
1. Run tests before pushing:
   ```bash
   python -m pytest tests/ -v
   npx playwright test
   ```

2. Use pre-commit hooks (optional):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

3. Test full CI locally with act:
   ```bash
   # Install act: https://github.com/nektos/act
   act -j e2e
   ```

### For CI/CD
1. Keep workflows simple and focused
2. Use reasonable timeouts (30+ minutes for full suite)
3. Pin action versions (`@v4` not `@latest`)
4. Upload artifacts for debugging
5. Use secrets for sensitive data (API keys, tokens)

### For Debugging
1. Add debug output to workflow:
   ```yaml
   - run: echo "Debug info here"
   ```

2. View full logs in GitHub Actions UI
3. SSH into runner (optional with act-tmate)
4. Reproduce locally first before pushing changes

---

## Performance Optimization

### Caching Dependencies

```yaml
- name: Cache Python deps
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements.txt') }}
    restore-keys: ${{ runner.os }}-pip-

- name: Cache Node deps
  uses: actions/cache@v3
  with:
    path: node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('package-lock.json') }}
    restore-keys: ${{ runner.os }}-node-
```

### Matrix Testing (Optional)

Run tests on multiple Python/Node versions:

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
        node-version: ['18', '20']
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
```

---

## Monitoring & Notifications

### Failed Workflow Notifications
- GitHub sends email on workflow failure
- Configure in Settings → Actions → Notifications

### Manual Workflow Trigger
You can manually trigger workflows from Actions tab (if configured with `workflow_dispatch`):

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python -m pytest tests/ -v` | Run all backend tests |
| `npx playwright test` | Run all E2E tests |
| `npx playwright test --ui` | Run E2E with browser UI |
| `npx playwright show-report` | View HTML report |
| `npm run install:playwright` | Install browsers for testing |

---

**Last Updated**: December 4, 2025
**Workflow File**: `.github/workflows/playwright-e2e.yml`
**Documentation**: `DEPLOYMENT.md`, `QUICK_START.md`, `E2E_README.md`
