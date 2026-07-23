# מערכת ניהול מלאי דיו | Ink Inventory Management

Inventory management system for ink products with FEFO (First Expired, First Out) tracking,
batch management, delivery notes, and real-time alerts. Built for Lino Print.

**Full technical specification:** [`SPEC.md`](SPEC.md)

## Quick Start

### Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **PostgreSQL database** — one of:
  - [Neon](https://neon.tech) (free, serverless, recommended for dev)
  - [Render PostgreSQL](https://render.com) (free 90 days)
  - Local PostgreSQL install

### 1. Clone

```bash
git clone https://github.com/shadam96/ink-inventory-management.git
cd ink-inventory-management
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment:
venv\Scripts\activate         # Windows (CMD/PowerShell)
# source venv/bin/activate    # Linux/Mac/Git Bash

pip install -r requirements.txt
```

Create the `.env` file:

```bash
cp ../env.example .env
```

Edit `.env` and set your `DATABASE_URL`:

```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
```

> If your provider gives a `postgresql://` URL (most do), the app converts it
> to `postgresql+asyncpg://` automatically — either format works.

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup the app auto-creates all tables. To seed default users, set `ADMIN_SEED_PASSWORD` and `USER_SEED_PASSWORD` env vars in your `.env` file before starting. This creates:
- `admin` (Admin role)
- `user` (Viewer role)

Verify: open http://localhost:8000/health — should return `{"status":"healthy"}`.

### 3. Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and log in.

### 4. Verify

| URL | What |
|-----|------|
| http://localhost:5173 | App UI |
| http://localhost:8000/health | Backend health check |
| http://localhost:8000/docs | API documentation (Swagger) |

## Environment Variables

Copy `env.example` to `backend/.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes (production) | JWT signing key, min 32 chars |
| `ENVIRONMENT` | No | `development` (default) or `production` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `RESEND_API_KEY` | No | Email notifications via Resend ([setup guide](EMAIL_SETUP_GUIDE.md)) |

See [`SPEC.md`](SPEC.md) for the full list.

## Tests

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test
```

## Deployment

| Service | Provider | Config |
|---------|----------|--------|
| Backend | Render (free tier) | `backend/Procfile` |
| Frontend | Vercel | `frontend/vercel.json` |
| Database | Neon / Render PostgreSQL | `DATABASE_URL` env var |

## Tech Stack

**Backend:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Alembic, JWT, APScheduler, aiosmtplib

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, Zustand, Recharts, i18next (Hebrew RTL)

## License

Proprietary — Lino Print
