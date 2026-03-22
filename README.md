# מערכת ניהול מלאי דיו | Ink Inventory Management

Inventory management system for ink products with FEFO (First Expired, First Out) tracking,
batch management, delivery notes, and real-time alerts. Built for Lino Print.

**Full technical specification:** [`SPEC.md`](SPEC.md)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (local install or remote — e.g. Render, Neon, Supabase)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
cp ../env.example .env          # edit DATABASE_URL to point to your PG instance

uvicorn app.main:app --reload --port 8000
```

On first startup the app auto-creates tables and seeds default users:
- `admin` / `admin123456` (Admin)
- `user` / `user123456` (Viewer)

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

### Tests

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
| Database | Render PostgreSQL / Neon | `DATABASE_URL` env var |

## Tech Stack

**Backend:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Alembic, JWT, APScheduler, aiosmtplib

**Frontend:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, Zustand, Recharts, i18next (Hebrew RTL)

## License

Proprietary — Lino Print
