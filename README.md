# NEXORA ERP

## Personal 3D pets

Run `python manage.py migrate` to apply `0011_pet_3d`, then `python manage.py test myapp.test_breakroom`. Install frontend dependencies with `cd frontend && npm install`; `npm run build` produces the lazy loaded 3D renderer.

Each user can create one personal pet at **Break Room → My Pet**, choose one of seven species, edit its appearance and room, chat, interact, or delete and recreate it. **Settings → Pet** links to the pet's personal settings. The mini pet is opt in and can appear on the Dashboard or across ERP pages. Focus Mode can hide it. Chat messages remain scoped to the pet owner; the backend uses a local fallback reply adapter (`myapp/breakroom/pet_ai_service.py`) and contains no frontend API key.

The renderer uses React Three Fiber, Drei and Three.js with rigged GLB assets. Production models for the seven species and wearable items are not included yet. Until they are supplied, the UI shows an explicit missing-model state; it does not display procedural geometry as a finished pet. Asset paths, rig conventions, materials, animation clips and activation steps are documented in [`frontend/public/assets/pets/README.md`](frontend/public/assets/pets/README.md). To add a species, update `myapp/breakroom/pet_options.py` and `frontend/src/features/pet/config.ts`.

Pet API: `GET/DELETE/PATCH /api/pets/me/`, `POST /api/pets/`, `GET /api/pets/options/`, `GET /api/pets/appearance-options/`, `GET/PATCH /api/pets/settings/`, `POST /api/pets/interact/`, `POST /api/pets/chat/`, `GET/DELETE /api/pets/messages/`. The new models are `PetAppearance`, `PetSettings`, and `PetInteraction`; existing `Pet` and `PetMessage` remain in use.

## Break Room

The optional Break Room lives at `/break-room/`. Its Django API is in `myapp/breakroom/`, with models and migration `myapp/migrations/0010_break_room.py`. Run `python manage.py migrate` before opening it. Run `python manage.py test myapp.test_breakroom` to check company policy, private pet messages, and session permissions.

The module provides nature scenes, a browser audio mixer, three short games, breathing, a virtual pet with private chat, timers, reminders, and personal settings. Pet replies use a local fallback service in `myapp/breakroom/pet_service.py`; no external AI key or service is required. Scene media URLs can be supplied later through the catalog without changing the API response shape. The included images cover three environments and are reused by the scene catalog until more media is provided.

Company admins can disable the whole module, games, or pets for the selected organization. Each user controls personal preferences independently. Reminders default to off, pet chat stays separate from ERP business data, and Focus Mode suppresses prompts and the Dashboard pet.

Django REST backend with a React/TypeScript frontend in [`frontend/`](frontend/README.md).

The previous static HTML prototype has been replaced by a Vite application. Build the frontend before opening Django at `/`, or run the Vite development server on port 5173 alongside Django on port 8000. The existing REST API remains under `/api/`.

This workspace's existing `.venv` points to a Python installation that is no longer present. Recreate the virtual environment with an installed Python interpreter, install `requirements.txt`, and then run Django checks and tests.

After restoring Python, run `python manage.py migrate` to create the exchange-rate table. Authenticated clients read `GET /api/exchange-rates/`. Django refreshes TJS→USD/EUR/CNY quotes at most every three hours and keeps the last stored quotes if the provider is unavailable. The provider endpoint can be changed with the Django setting `EXCHANGE_RATE_PROVIDER_URL`; the fetch and validation logic is isolated in `myapp/exchange_rate_service.py`. Rates are reference values for Dashboard display only. Document amounts and original currencies are never rewritten by the currency selector.
