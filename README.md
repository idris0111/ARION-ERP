# NEXORA ERP

Django REST backend with a React/TypeScript frontend in [`frontend/`](frontend/README.md).

The previous static HTML prototype has been replaced by a Vite application. Build the frontend before opening Django at `/`, or run the Vite development server on port 5173 alongside Django on port 8000. The existing REST API remains under `/api/`.

This workspace's existing `.venv` points to a Python installation that is no longer present. Recreate the virtual environment with an installed Python interpreter, install `requirements.txt`, and then run Django checks and tests.
