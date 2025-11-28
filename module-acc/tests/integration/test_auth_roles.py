import pytest


def test_viewer_cannot_create_account(client, viewer_headers):
    headers = {**viewer_headers}
    payload = {"code": "130", "name": "Forbidden", "account_type": "asset"}
    resp = client.post('/accounts/', json=payload, headers=headers)
    assert resp.status_code in (401, 403)


def test_accountant_can_create_but_not_delete(client, accountant_headers):
    headers = {**accountant_headers}
    payload = {"code": "131", "name": "AcctCanCreate", "account_type": "asset"}
    resp = client.post('/accounts/', json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    acc_id = data.get('id')
    # Accountant shouldn't be allowed to delete
    del_resp = client.delete(f'/accounts/{acc_id}', headers=headers)
    assert del_resp.status_code in (401, 403)


def test_admin_full_access(client, admin_headers):
    headers = {**admin_headers}
    payload = {"code": "140", "name": "AdminAcc", "account_type": "asset"}
    resp = client.post('/accounts/', json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    acc_id = data.get('id')
    # Admin can delete
    del_resp = client.delete(f'/accounts/{acc_id}', headers=headers)
    assert del_resp.status_code == 200
