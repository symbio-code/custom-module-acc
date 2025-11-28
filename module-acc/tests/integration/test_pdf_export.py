import pytest
from datetime import date


def test_trial_balance_pdf_export(client, accountant_headers):
    try:
        import weasyprint  # type: ignore
    except Exception:
        pytest.skip("WeasyPrint not installed in test environment")

    headers = {**accountant_headers}
    from_date = date.today().isoformat()
    to_date = date.today().isoformat()
    resp = client.get(f'/report/trial-balance/pdf?from_date={from_date}&to_date={to_date}', headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get('content-type') == 'application/pdf'
    assert resp.content and len(resp.content) > 10
