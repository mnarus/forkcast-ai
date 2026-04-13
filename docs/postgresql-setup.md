# PostgreSQL Setup

This repo supports PostgreSQL for the Django backend.

## 1. Install Python dependencies

From the repo root:

```powershell
venv\Scripts\pip install -r requirements.txt
```

## 2. Create your backend env file

Copy [backend/.env.example](/C:/Users/Michelle/Repos/forkcast-ai/backend/.env.example) to `backend/.env` and adjust values if needed.

## 3. Start PostgreSQL

If you have Docker Desktop running:

```powershell
docker compose up -d postgres
```

This starts a local PostgreSQL server on `localhost:5432` with:

- database: `forkcast_ai`
- username: `forkcast`
- password: `forkcast`

## 4. Run migrations

From the `backend` directory:

```powershell
..\venv\Scripts\python manage.py migrate
```

## 5. Run the backend

```powershell
..\venv\Scripts\python manage.py runserver
```

## Notes

- Django reads environment variables from `backend/.env`.
- SQLite remains available only as an explicit fallback by setting `USE_SQLITE=true`.
- If you already have a local PostgreSQL install, you can skip Docker and point the env vars at that instance instead.
