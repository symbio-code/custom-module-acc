# custom-module-acc

## Testing

- Run the full test suite from the `module-acc` folder:

```bash
cd module-acc && pytest -q
```

- The test suite uses a per-test database engine and the test fixtures in `tests/conftest.py` override the application database engine so the `TestClient` and tests share the same database instance.

- Current authentication behavior: the project currently authenticates by verifying a password against users in the database (tests create a single user per scenario). For production usage it's recommended to refactor authentication to require both `username` and `password` (this is planned as an optional follow-up change).

If you'd like me to proceed with the `username`+`password` refactor now, I can implement it in a separate branch and update routes and tests accordingly.
# custom-module-acc