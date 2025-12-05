"""
API-based end-to-end flow script:
1. POST /api/v2/import/smart with sample CSV
2. Build and POST /api/v2/portfolio to save the portfolio
3. POST /api/portfolio/export-pdf with portfolio_id and client_name
4. Save returned PDF to /tmp/E2E_Portfolio_Report.pdf

Run with the project's venv Python:
    env PYTHONPATH="$(pwd)" \
    .venv/bin/python scripts/e2e_api_flow.py
"""
import requests
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
API = 'http://127.0.0.1:8000'
CSV = ROOT / 'sample_portfolio.csv'
OUT = Path('/tmp/E2E_Portfolio_Report.pdf')

if not CSV.exists():
    print('sample CSV not found at', CSV)
    sys.exit(1)

print('1) Uploading CSV to import endpoint...')
with open(CSV, 'rb') as f:
    r = requests.post(f'{API}/api/v2/import/smart', files={'file': (CSV.name, f, 'text/csv')}, timeout=60)
print('Import status:', r.status_code)
if not r.ok:
    print('Import failed:', r.text[:1000])
    sys.exit(2)
resp = r.json()
holdings = resp.get('holdings')
if not holdings:
    print('No holdings returned from import; response:', resp)
    sys.exit(3)

# Build payload for save
payload = {
    'name': 'E2E Test Portfolio',
    'holdings': []
}
for h in holdings:
    payload['holdings'].append({
        'ticker': (h.get('Symbol') or h.get('ticker') or '').upper(),
        'quantity': float(h.get('Quantity') or h.get('quantity') or h.get('qty') or 0),
        'price': float(h.get('Price ($)') or h.get('price') or 0),
        'cost_basis': float(h.get('Principal ($)') or h.get('cost_basis') or 0),
        'metadata': {'description': h.get('Description') or h.get('description') or ''}
    })

print('2) Saving portfolio via API...')
rs = requests.post(f'{API}/api/v2/portfolio', json=payload, timeout=30)
print('Save status:', rs.status_code)
if not rs.ok:
    print('Save failed:', rs.text[:1000])
    sys.exit(4)
created = rs.json()
portfolio_id = created.get('id')
print('Created portfolio id:', portfolio_id)

print('3) Requesting PDF export using portfolio_id...')
with requests.Session() as s:
    files = {'portfolio_id': (None, str(portfolio_id)), 'client_name': (None, 'E2E Client')}
    r2 = s.post(f'{API}/api/portfolio/export-pdf', files=files, timeout=120)
    print('Export status:', r2.status_code)
    if not r2.ok:
        print('Export failed:', r2.text[:200])
        sys.exit(5)
    # Save PDF
    OUT.write_bytes(r2.content)
    print('Saved PDF to', OUT)

print('E2E flow completed successfully')
