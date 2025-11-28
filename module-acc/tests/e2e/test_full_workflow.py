import pytest
from datetime import date


def test_full_accounting_workflow(client, admin_headers, accountant_headers):
    # 1) Create COA (top-level account)
    headers_admin = {**admin_headers}
    resp = client.post('/accounts/', json={"code": "160", "name": "Test Sales", "account_type": "revenue"}, headers=headers_admin)
    assert resp.status_code == 200
    acc = resp.json()
    assert acc.get('id') is not None

    # 2) Create JE (accountant)
    headers_acct = {**accountant_headers}
    today = date.today().isoformat()
    payload = {
        "entry": {"date": today, "description": "E2E Sale"},
        "lines": [
            {"account_code": "100", "debit": 700.0, "credit": 0.0},
            {"account_code": "160", "debit": 0.0, "credit": 700.0}
        ]
    }
    je_resp = client.post('/journal/', json=payload, headers=headers_acct)
    assert je_resp.status_code == 200
    je = je_resp.json()
    je_id = je.get('id')
    assert je_id is not None

    # 3) Post JE to ledger
    post_resp = client.post(f'/ledger/post/{je_id}', headers=headers_acct)
    assert post_resp.status_code == 200
    assert post_resp.json().get('status') in ('posted',)

    # 4) Get trial balance, ensure balanced
    from_date = date.today().isoformat()
    to_date = date.today().isoformat()
    tb_resp = client.get(f'/report/trial-balance?from_date={from_date}&to_date={to_date}', headers=headers_acct)
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb.get('balanced') is True

    # 5) Get profit & loss totals
    pl_resp = client.get(f'/report/profit-loss?from_date={from_date}&to_date={to_date}', headers=headers_acct)
    assert pl_resp.status_code == 200
    pl = pl_resp.json()
    # after the sale above, revenue should reflect the amount
    assert pl.get('total_revenue', 0) >= 700.0
