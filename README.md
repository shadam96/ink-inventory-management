# מערכת ניהול מלאי דיו | Ink Inventory Management System

A comprehensive inventory management system for ink products with FEFO (First Expired, First Out) tracking, batch management, and real-time alerts.

## Features

- **Batch Tracking**: Full traceability of ink batches with expiration dates
- **FEFO Logic**: Automatic suggestions for picking based on expiration dates
- **Real-time Alerts**: Proactive notifications for expiring batches, low stock, and dead stock
- **Delivery Notes**: Generate and track delivery documents with batch numbers
- **Dashboard**: Visual KPIs, inventory distribution charts, and risk indicators
- **Multi-language**: Hebrew (RTL) and English support
- **PWA Ready**: Offline support and mobile-optimized UI

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL 15+
- Redis 7+
- Alembic (migrations)
- JWT Authentication

### Frontend
- React 18+ with TypeScript
- Vite
- shadcn/ui + Tailwind CSS
- Zustand (state management)
- React Hook Form + Zod
- Recharts (data visualization)
- i18next (Hebrew RTL support)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### 1. Clone and Setup

```bash
# Clone the repository
cd inventory-management

# Copy environment file
cp env.example .env
# Edit .env with your settings
```

### 2. Start with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Or for local development:
cd backend
alembic upgrade head
```

### 4. Create Admin User

```bash
# Via API (after starting the server)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@linoprint.com",
    "full_name": "מנהל מערכת",
    "password": "securepassword123",
    "role": "admin"
  }'
```

### 5. Access the Application

- **Frontend UI**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### 6. Create Test Users

```powershell
# Admin user
$json = '{"username":"admin","email":"admin@lino.com","full_name":"Admin User","password":"admin123456","role":"admin"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($json)) -ContentType "application/json; charset=utf-8"
```

Available test credentials:
- **admin** / admin123456 (full access)
- **manager** / manager123 (inventory management)
- **warehouse** / warehouse123 (operations)
- **viewer** / viewer123 (read-only)

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx aiosqlite

# Run tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `SECRET_KEY` | JWT secret key (min 32 chars) | - |
| `ENVIRONMENT` | development/production | development |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | 30 |
| `ALERT_THRESHOLD_*` | Days before expiration alerts | 120, 90, 60, 30 |
| `DEAD_STOCK_DAYS` | Days for dead stock detection | 180 |

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/auth/register` - Register user

### Items
- `GET /api/v1/items` - List items (paginated, filterable)
- `POST /api/v1/items` - Create item
- `GET /api/v1/items/{id}` - Get item
- `PUT /api/v1/items/{id}` - Update item
- `DELETE /api/v1/items/{id}` - Delete item

### Batches
- `GET /api/v1/batches` - List batches (FEFO sorted)
- `GET /api/v1/batches/{id}` - Get batch
- `PUT /api/v1/batches/{id}` - Update batch
- `GET /api/v1/batches/expiring-soon` - Expiring batches
- `POST /api/v1/batches/{id}/mark-scrap` - Mark as scrap

### Locations
- `GET /api/v1/locations` - List locations
- `POST /api/v1/locations` - Create location
- `GET /api/v1/locations/{id}` - Get location
- `PUT /api/v1/locations/{id}` - Update location
- `DELETE /api/v1/locations/{id}` - Delete location

### Customers
- `GET /api/v1/customers` - List customers
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Deactivate customer

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access to all features |
| `manager` | CRUD on items, batches, customers, locations |
| `warehouse_worker` | Receive goods, pick orders, update batches |
| `viewer` | Read-only access |

## Database Schema

```
users          - Authentication and authorization
items          - Ink products (SKU, supplier, prices)
batches        - Batch tracking with expiration dates
movements      - Audit trail for inventory changes
locations      - Warehouse storage locations
customers      - Customer management
delivery_notes - Dispatch documentation
alerts         - System notifications
```

## Project Structure

```
inventory-management/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Config, DB, security
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI app
│   ├── alembic/           # DB migrations
│   ├── tests/             # Pytest tests
│   └── requirements.txt
├── frontend/              # React app (Phase 2+)
├── docker-compose.yml
└── README.md
```

## License

Proprietary - LinoPrint © 2024


