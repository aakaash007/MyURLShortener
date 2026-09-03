# LinkMint

LinkMint is a full-stack URL shortener built with FastAPI, PostgreSQL, SQLAlchemy,
Alembic, and a responsive browser interface. It validates HTTP/HTTPS destinations,
creates secure random Base62 codes, and returns explicit HTTP 302 redirects.

## Architecture

```text
Browser → FastAPI → SQLAlchemy → PostgreSQL
            ├── POST /links
            ├── GET /{short_code}
            └── static browser interface
```

PostgreSQL is the durable source of truth. The `short_code` primary key makes code
allocation concurrency-safe: a rare collision is rejected by the database and retried.

## Local setup

Requirements: Python 3.11+, Docker, and Docker Compose.

```powershell
cd "$HOME\Desktop\MyProjects\MyURLShortener"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
docker compose up -d postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Open the frontend at `http://127.0.0.1:8000` and API documentation at
`http://127.0.0.1:8000/docs`.

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string |
| `PUBLIC_BASE_URL` | Public HTTPS origin used in generated short links |
| `CORS_ORIGINS` | Comma-separated origins for a separately hosted frontend |
| `ENVIRONMENT` | `development`, `testing`, or `production` |
| `LINK_CREATION_LIMIT` | Maximum creations per client in each rate-limit window |
| `RATE_LIMIT_WINDOW_SECONDS` | Rolling rate-limit window length |

Never commit `.env` or a deployed database password.

## API examples

Create a short link:

```powershell
curl.exe -X POST http://127.0.0.1:8000/links `
  -H "Content-Type: application/json" `
  -d '{"target_url":"https://example.com/articles?id=42"}'
```

Example `201 Created` response:

```json
{
  "short_code": "aZ3kP9q",
  "short_url": "http://127.0.0.1:8000/aZ3kP9q",
  "target_url": "https://example.com/articles?id=42"
}
```

Check the redirect without following it:

```powershell
curl.exe -i http://127.0.0.1:8000/aZ3kP9q
```

Health probes are available at `/health` and `/ready`.

Creation requests are rate-limited per client. URLs containing embedded credentials
are rejected, and browser responses include restrictive security headers.

## Quality checks

```powershell
pytest
ruff check app tests migrations scripts
ruff format --check app tests migrations scripts
```

The unit/API suite uses an isolated test-only SQLAlchemy database. Production and
development settings reject non-PostgreSQL database URLs.

## Database migrations

Create a migration after changing the SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Review every generated migration before applying it.

## Free deployment path

1. Push this project to a GitHub repository.
2. Create a free Neon PostgreSQL project and copy its pooled connection string.
3. Create a free Render Web Service from the repository.
4. Render reads `render.yaml`; set `DATABASE_URL` and `PUBLIC_BASE_URL` as secrets.
5. Set `PUBLIC_BASE_URL` to the final `https://<service>.onrender.com` address.

The frontend is served by FastAPI, so one Render service hosts both frontend and
backend. Render's free filesystem is ephemeral, but all link data remains in Neon.
Free services can sleep or enforce usage limits and therefore do not provide a
commercial uptime guarantee.
