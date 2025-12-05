import requests
from pathlib import Path

URL = 'http://127.0.0.1:8000/api/portfolio/export-pdf'
CSV_PATH = Path(__file__).resolve().parents[0].parent / 'sample_portfolio.csv'
OUT_PATH = Path('/tmp/Portfolio_Test_py.pdf')

print('Using file:', CSV_PATH)
with open(CSV_PATH, 'rb') as f:
    files = {'file': (CSV_PATH.name, f, 'text/csv')}
    try:
        r = requests.post(URL, files=files, timeout=120)
        print('Status:', r.status_code)
        if r.ok and r.headers.get('content-type','').startswith('application/pdf'):
            OUT_PATH.write_bytes(r.content)
            print('Saved PDF to', OUT_PATH)
        else:
            print('Response not PDF or not OK; headers:', r.headers)
            print(r.text[:1000])
    except Exception as e:
        print('Request failed:', e)
