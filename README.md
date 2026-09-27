# GROOT

> Operational Intelligence for Growing Startups.

GROOT is an AI-powered operational intelligence platform designed to help growing startups detect emerging risks, investigate their root causes, understand organizational dependencies, and take corrective action with human approval.

## Vision

GROOT acts as an intelligent operating layer for a growing company.

It continuously connects information from different parts of the organization and transforms fragmented data into actionable intelligence.

### Core Loop

Understand → Investigate → Explain → Recommend → Act → Verify

## Planned Architecture

- Next.js + TypeScript
- Django
- FastAPI
- PostgreSQL + SQLAlchemy
- MongoDB
- Redis + Celery
- RAG
- LangChain
- LangGraph
- Multi-Agent System
- Browser Automation
- AI/Agent Evaluation
- Docker
- Kubernetes
- CI/CD
- Observability

## Project Status

🚧 Under active development. See [the roadmap](docs/Task.md) for implemented scope and known gaps.

## Local setup

Use Python 3.14 (verified with 3.14.4), PostgreSQL with the pgvector server
extension installed, and Redis for Celery. Run the following from the repository
root. If you already have environment files, update them from the examples instead
of overwriting them.

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip check
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

Set `POSTGRES_*` for an existing database and role you control. Django and the AI
engine read the same root `.env`; exported environment values take precedence.
The existing local defaults are database `groot_db`, user `rachit`, empty password,
and `localhost:5432`. Set your own values when these do not match your machine.
`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` default to local Redis databases
0 and 1. Keep credentials in `.env` or the process environment.

### Database prerequisites and migrations

```sh
.venv/bin/python -m ai_engine.app.db.check
```

This read-only command checks connectivity and whether `vector` is enabled in the
configured database. It exits with status 1 and setup guidance when a prerequisite
is missing. If pgvector is unavailable, install the server extension for your
PostgreSQL version. If it is available but disabled, the database owner must run
the following in the configured database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Re-run the check, then apply each service's migrations:

```sh
.venv/bin/python backend/manage.py migrate
.venv/bin/python -m alembic -c ai_engine/alembic.ini upgrade head
```

Django owns business tables; Alembic owns the embedding table. The preflight does
not install extensions or apply migrations. `/health` remains a static health
response, not a dependency readiness probe.

### Run the development services

Start PostgreSQL and Redis locally. Set `GROQ_API_KEY` for live AI answers and
`GITHUB_TOKEN` for the GitHub connector. For RAG, start Ollama and pull the
configured model (`ollama pull nomic-embed-text:latest` by default). Run these
services in separate terminals from the repository root:

```sh
.venv/bin/python backend/manage.py runserver 8000
.venv/bin/python -m uvicorn ai_engine.app.main:app --reload --port 8001
```

For the frontend, run `npm ci` and `npm run dev` from `frontend/`.
`frontend/.env.local` supplies `NEXT_PUBLIC_AI_ENGINE_URL`; the root `.env` is not
loaded by Next.js. Public variables are included in the browser build, so provider
credentials must never go there.

For Celery, run `../.venv/bin/celery -A config worker --loglevel=info` from
`backend/`. Nested document/ingestion task registration and the document-to-vector
handoff still need work; starting a worker does not establish a complete pipeline.

### Tests

```sh
.venv/bin/python -m unittest discover -s ai_engine/tests
.venv/bin/python backend/manage.py test core --noinput
```

Django tests require a PostgreSQL role allowed to create a temporary test database.
See [MEMORY.md](docs/MEMORY.md) for the latest verified results and pre-existing
failures. This setup does not resolve authentication, tenant isolation, or the
unfinished knowledge workflow.
