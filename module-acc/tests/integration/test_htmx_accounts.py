import pytest


def test_accounts_new_fragment(client, admin_headers):
    # HTMX fragment endpoint requires admin/accountant role
    headers = {**admin_headers, 'hx-request': 'true'}
    resp = client.get('/accounts/new', headers=headers)
    assert resp.status_code == 200
    # Should return HTML fragment
    assert 'text/html' in resp.headers.get('content-type', '')


def test_accounts_create_htmx_redirect(client, admin_headers):
    headers = {**admin_headers, 'hx-request': 'true'}
    payload = {"code": "120", "name": "Receivable", "account_type": "asset"}
    resp = client.post('/accounts/', json=payload, headers=headers)
    assert resp.status_code == 200
    # HTMX endpoints return HX-Redirect header on success
    assert 'HX-Redirect' in resp.headers or 'hx-redirect' in resp.headers
