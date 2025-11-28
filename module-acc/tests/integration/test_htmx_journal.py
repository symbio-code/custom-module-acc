import pytest
from datetime import date


def test_journal_new_page(client, admin_headers):
    headers = {**admin_headers}
    resp = client.get('/journal/new', headers=headers)
    assert resp.status_code == 200
    assert 'text/html' in resp.headers.get('content-type', '')


def test_create_journal_via_api(client, accountant_headers):
    headers = {**accountant_headers}
    payload = {
        "entry": {"date": date.today().isoformat(), "description": "HTMX API JE"},
        "lines": [
            {"account_code": "100", "debit": 300.0, "credit": 0.0},
            {"account_code": "400", "debit": 0.0, "credit": 300.0}
        ]
    }
    resp = client.post('/journal/', json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('id') is not None
