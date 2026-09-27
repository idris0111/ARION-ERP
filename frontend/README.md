# NEXORA ERP frontend

React + TypeScript + Vite interface for the Django REST API in the repository root. The UI uses Tailwind design tokens, Radix/shadcn-style primitives, Lucide, Recharts, TanStack Query, Axios, React Hook Form and Zod.

## Development

Run Django on `http://127.0.0.1:8000` with its existing API, then in `frontend/`:

```powershell
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` and `/swagger` to Django. Log in with an existing ERP account. The UI does not contain demonstration business records.

## Production build served by Django

```powershell
cd frontend
npm.cmd install
npm.cmd run build
cd ..
python manage.py runserver
```

Django serves the React shell at `/` and module routes. The compiled files are served at `/static/frontend/` through `STATICFILES_DIRS` in development. For deployment, run `collectstatic` and configure the production web server to serve `STATIC_ROOT`. `frontend/dist` is generated and intentionally not committed. Django returns a clear 503 response when the frontend has not been built.

## API integration

- `src/api/client.ts` holds the Axios instance, JWT login/refresh and request helpers.
- `src/app/resources.ts` maps Django endpoints to navigation, tables and forms.
- `src/services/access.ts` mirrors existing role classes for UI visibility; Django remains the authority for access control.
- Selecting a company sends `X-Organization-ID`. The Django tenancy layer validates membership and scopes lists and reports.
- Pages use live API data; empty and error states are shown when no records are available.

## Current backend constraints

The frontend follows existing Django models and endpoints. The backend has no separate invoice, attendance, split-payment, granular permission-matrix, or report-PDF API yet. Reports support browser Print / Save as PDF. POS uses one payment account per sale; a split-payment UI is not enabled until the API can represent it safely. Large list views are capped at 500 records by the current API page size; server-side filtering and pagination should be expanded for bigger deployments.
