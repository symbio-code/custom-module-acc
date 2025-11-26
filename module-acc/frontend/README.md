Frontend scaffold for module-acc

- Layouts: `frontend/layouts/*.html`
- Components: `frontend/components/*` (sidebar, header, table, form_field, modal, pagination)
- Pages: `frontend/pages/*` and `frontend/pages/reports/*`

Usage

- Serve templates from your web framework (FastAPI/Jinja2, Flask, etc.) and point routes to render these templates.
- `index.html` boots the app and uses HTMX to load `/dashboard` into the page.

HTMX

- Links in the sidebar include `hx-get` + `hx-target="#content"` to load pages into the main content area without a full page reload.

Next steps

- Wire routes on the backend to return the page templates (e.g., `/dashboard` -> `frontend/pages/dashboard.html`).
- Populate table `rows` context variables from backend handlers.
