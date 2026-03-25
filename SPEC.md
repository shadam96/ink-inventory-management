# Ink Inventory Management System — Technical Specification

**Lino Print — מערכת ניהול מלאי דיו**
**Version:** 2.0 | **Date:** 2026-03-15 | **Status:** Active Development

---

## 1. Overview

A web-based inventory management system for ink products, built for Lino Print.
Core value: **FEFO-driven** (First Expired, First Out) batch tracking with real-time
alerts, delivery note generation, and future customer-site inventory (VMI/consignment).

**Primary language:** Hebrew (RTL). English included. i18n scaffolding for future languages.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React 19 + TypeScript + Vite + Tailwind + shadcn/ui         │
│  Hosted: Vercel (or any static host)                         │
│  SPA with PWA capabilities                                   │
├─────────────────────────────────────────────────────────────┤
│                      ↕ HTTPS + WSS                           │
├─────────────────────────────────────────────────────────────┤
│                        BACKEND                               │
│  FastAPI (Python 3.11+) + SQLAlchemy 2.0 async               │
│  Hosted: Render (free tier for dev, reads Procfile)           │
│  Single process: API + WebSocket + APScheduler               │
├─────────────────────────────────────────────────────────────┤
│                      ↕ asyncpg                               │
├─────────────────────────────────────────────────────────────┤
│                      POSTGRESQL 15+                          │
│  Hosted: Render (free 90-day PG) / Neon / Supabase           │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 No Docker

The project **does not use Docker** for development or deployment.

**Local development:**
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../env.example .env  # edit DATABASE_URL to point to local/remote PG
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # Vite dev server on :5173
```

**Deployment:**
- Backend → **Render** free tier (auto-deploys from git, reads `Procfile`)
  - Free plan: 750 hrs/month, spins down after 15 min inactivity (~30s cold start)
  - Upgrade to paid ($7/mo) when moving to production for always-on
- Frontend → **Vercel** free tier (auto-deploys from git, reads `vercel.json`)
- Database → **Render PostgreSQL** free tier (1 GB, expires after 90 days)
  - For longer dev or production: switch to **Neon** (free tier, no expiry) or Render paid PG
  - The app auto-converts `postgresql://` to `postgresql+asyncpg://` — any PG provider works

### 2.2 Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| **API Framework** | FastAPI | 0.115 | Async, auto-docs, Pydantic validation |
| **ORM** | SQLAlchemy 2.0 | 2.0.35 | Async support, mature, migration-friendly |
| **DB Driver** | asyncpg | 0.29 | Fastest async PostgreSQL driver |
| **Migrations** | Alembic | 1.13 | SQLAlchemy-native migrations |
| **Auth** | JWT (python-jose) | 3.3 | Stateless auth, access + refresh tokens |
| **Email** | aiosmtplib + Jinja2 | 3.0 / 3.1 | Async SMTP, templated HTML emails |
| **Scheduler** | APScheduler | 3.10 | In-process background jobs |
| **PDF** | ReportLab | 4.2 | Delivery note PDF generation |
| **Excel** | openpyxl | 3.1 | Export to .xlsx |
| **Frontend** | React + TypeScript | 19.2 / 5.9 | Component model, type safety |
| **Build** | Vite | 7.2 | Fast HMR, optimized builds |
| **CSS** | Tailwind CSS | 3.4 | Utility-first, RTL-friendly |
| **Components** | shadcn/ui | latest | Accessible, customizable primitives |
| **State** | Zustand | 5.0 | Minimal, no boilerplate |
| **Forms** | React Hook Form + Zod | 7.68 | Performant validation |
| **HTTP** | Axios | 1.13 | Interceptors for JWT refresh |
| **Charts** | Recharts | 3.5 | React-native charting |
| **i18n** | i18next | 25.7 | Hebrew RTL + future languages |
| **Barcode** | quagga2 | latest | Camera-based barcode scanning |
| **Offline** | IndexedDB (idb) | latest | PWA offline caching |

### 2.3 Database Schema

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    users     │     │    items     │     │  locations   │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (UUID PK) │     │ id (UUID PK) │     │ id (UUID PK) │
│ username     │     │ sku          │     │ warehouse    │
│ email        │     │ name         │     │ shelf        │
│ hashed_pass  │     │ description  │     │ position     │
│ full_name    │     │ supplier     │     │ location_code│
│ role (enum)  │     │ unit_of_meas │     │ is_active    │
│ is_active    │     │ cost_price   │     └──────┬───────┘
│ notif_email  │     │ reorder_point│            │
│ email_notif  │     │ min_stock    │            │
│  _enabled    │     │ max_stock    │            │
└──────────────┘     └──────┬───────┘            │
                            │                    │
                     ┌──────┴───────┐            │
                     │   batches    ├────────────┘
                     ├──────────────┤
                     │ id (UUID PK) │
                     │ batch_number │  ← auto: GR-YYMMDD-XXX
                     │ item_id (FK) │
                     │ qty_available│
                     │ receipt_date │
                     │ expiration_  │
                     │   date       │  ← MANDATORY
                     │ status (enum)│  ← ACTIVE / DEPLETED / SCRAP
                     │ location_id  │
                     │ version      │  ← optimistic locking
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────┴──────┐ ┌───┴────────┐ ┌──┴───────────┐
       │  movements  │ │   alerts   │ │delivery_note │
       ├─────────────┤ ├────────────┤ │   _items     │
       │ id          │ │ id         │ ├──────────────┤
       │ batch_id FK │ │ alert_type │ │ id           │
       │ user_id  FK │ │ severity   │ │ dn_id FK     │
       │ movement_   │ │ batch_id FK│ │ item_id FK   │
       │   type(enum)│ │ item_id FK │ │ batch_id FK  │
       │ quantity    │ │ message    │ │ quantity     │
       │ qty_before  │ │ is_read    │ └──────┬───────┘
       │ qty_after   │ │ is_dismiss │        │
       │ reference   │ └────────────┘ ┌──────┴───────┐
       │ notes       │                │delivery_notes│
       └─────────────┘                ├──────────────┤
                                      │ id           │
       Movement types:                │ dn_number    │
       RECEIPT, DISPATCH,             │ customer_id  │
       ADJUSTMENT, SCRAP,             │ status (enum)│
       TRANSFER                       │ is_consign   │
                                      └──────────────┘
       ┌──────────────┐
       │  customers   │               DN statuses:
       ├──────────────┤               DRAFT → ISSUED →
       │ id (UUID PK) │               DELIVERED → INVOICED
       │ name         │               (or CANCELLED)
       │ email        │
       │ phone        │
       │ address      │
       │ is_vmi       │  ← for future CSI module
       └──────────────┘
```

**User Roles:**
- `ADMIN` — full access, system settings, user management
- `MANAGER` — inventory management, reports, alerts, delivery notes
- `WAREHOUSE_WORKER` — receiving, picking, location updates
- `VIEWER` — read-only dashboard and reports

### 2.4 Authentication Flow

```
Login → POST /auth/login (username + password)
      ← { access_token (30 min), refresh_token (7 days) }

API call → Authorization: Bearer <access_token>

On 401 → POST /auth/refresh (refresh_token)
        ← { new access_token }
        → retry original request

Axios interceptor handles refresh automatically.
```

### 2.5 Real-time Architecture

```
Client connects: WS /ws?token=<jwt>
Server authenticates JWT, adds to ConnectionManager

Events broadcasted:
  - alert:new        → new alert created
  - alert:updated    → alert read/dismissed
  - dashboard:update → inventory changed (receive/pick/adjust)
  - batch:status     → batch status changed (expired, scrap)

Frontend: useWebSocket hook → updates Zustand store → React re-renders
NotificationBell component shows unread count + dropdown
```

### 2.6 Background Jobs (APScheduler)

| Job | Schedule | What it does |
|-----|----------|-------------|
| Expiration check | Daily 6:00 AM | Scans batches approaching expiration thresholds (120/90/60/30 days). Creates alerts. Auto-marks expired batches as SCRAP. |
| Low stock check | Every 4 hours | Compares item stock vs reorder_point. Creates alerts for items below threshold. |
| Dead stock check | Weekly (Sun 2 AM) | Finds batches with no outbound movement for 180+ days. Creates alerts. |

All thresholds configurable via environment variables.

---

## 3. Internationalization (i18n)

### Current state
- Hebrew (`he.json`) — only language, ~160 translation keys
- i18next configured with `lng: 'he'`, `fallbackLng: 'he'`
- No English locale file exists
- RTL handled via Tailwind `dir="rtl"` on root

### Target state
- **Hebrew** — primary, complete coverage
- **English** — secondary, complete coverage
- **Scaffolding** — adding a new language = adding `xx.json` + one line in config
- Language selector in settings page
- User language preference saved to user profile (DB)
- Backend error messages also i18n-aware (Hebrew/English)
- Email templates: Hebrew and English variants
- PDF delivery notes: language matches customer preference
- Date/number formatting locale-aware (`Intl.DateTimeFormat`, `Intl.NumberFormat`)

### Implementation

```
frontend/src/i18n/
├── index.ts           ← i18next config, language detection, fallback chain
├── locales/
│   ├── he.json        ← Hebrew (primary, complete)
│   ├── en.json        ← English (secondary, complete)
│   └── [xx.json]      ← future languages
```

```typescript
// i18n/index.ts — target config
i18n.use(initReactI18next).use(LanguageDetector).init({
  resources: { he: { translation: he }, en: { translation: en } },
  lng: savedUserPreference || 'he',
  fallbackLng: 'he',
  interpolation: { escapeValue: false },
  // RTL detection
  react: { useSuspense: false },
})
```

**RTL handling rules:**
- Root `<html dir="rtl" lang="he">` toggled by language
- Tailwind `rtl:` variant for layout-specific overrides
- All `ml-*` / `mr-*` replaced with `ms-*` / `me-*` (logical properties)
- Tables, forms, sidebars, charts — all must respond to direction
- Icons that imply direction (arrows, chevrons) must flip

---

## 4. Modules — Detailed Specification

Each module below lists: what the PDF requires, what's built, and what's missing.

Status legend: ✅ Done | 🔧 Partial | ❌ Not started

---

### Module 1: Inventory Management (ניהול מלאי בסיסי)

**PDF requirement:** CRUD items (supplier, SKU, description, unit, batch, expiry, cost).
Batch tracking per receipt. Movement audit trail. Storage location tracking.

| Feature | Status | Notes |
|---------|--------|-------|
| Item CRUD (SKU, name, supplier, unit, cost) | ✅ | `items` table, full API + UI |
| Batch creation on receipt | ✅ | Auto-number `GR-YYMMDD-XXX` |
| Batch → expiration date (mandatory) | ✅ | Validated: cannot be in the past |
| Batch → quantity tracking | ✅ | `quantity_available` updated on every movement |
| Movement audit trail | ✅ | `movements` table: RECEIPT, DISPATCH, ADJUSTMENT, SCRAP, TRANSFER |
| Optimistic locking on batch | ✅ | `version` column prevents concurrent update conflicts |
| Location management | ✅ | `locations` table: warehouse / shelf / position |
| Batch → location assignment | ✅ | FK on batch, assignable during receiving |
| Barcode scan for item lookup | ✅ | quagga2 camera scanner + manual entry fallback |
| Location label printing | ❌ | PDF says: "print location label with batch, SKU, expiry" |
| Purchase order matching | ❌ | PDF says: "show matching open POs for item" — no PO model exists |

**What's missing for full PDF compliance:**
1. **Location label printing** — generate a printable label (PDF or ZPL) with batch number, SKU, expiration date for physical placement on shelf
2. **Purchase order module** — the receiving page should show matching open POs. This requires a `purchase_orders` table and a receiving ↔ PO linking flow. *Deprioritized — can work without POs initially.*

---

### Module 2: FEFO/FIFO Shelf Life Control (בקרת חיי מדף)

**PDF requirement:** FEFO dispatch (nearest expiry first). Proactive expiration alerts
at configurable thresholds (120/90/60/30 days). Expired stock auto-moves to "Scrap" status.
Scrap reporting with value impact.

| Feature | Status | Notes |
|---------|--------|-------|
| FEFO picking suggestions | ✅ | `FEFOEngine.suggest_batches_for_picking()` sorts by expiry ASC |
| FEFO violation warnings | ✅ | Warns if user picks a batch that isn't the nearest-expiry |
| Block dispatch of expired batches | ✅ | Hard block with error message |
| Configurable alert thresholds | ✅ | Env vars: `ALERT_THRESHOLD_120/90/60/30` |
| Auto expiration alerts | ✅ | APScheduler daily job scans all active batches |
| Auto scrap on expiry | ✅ | Batch status → SCRAP when `expiration_date < today` |
| Scrap value reporting | 🔧 | Movements record scrap, but no dedicated scrap value report page |
| Expiration color coding | ✅ | Green (>6mo), Yellow (30-90d), Red (0-30d), Black (expired) |

**What's missing:**
1. **Scrap value report** — a dedicated report showing: total scrapped value (cost_price × qty), by item, by time period. Currently the data exists in movements but there's no aggregated report UI.

---

### Module 3: Operations & Documents (תפעול ומסמכים)

**PDF requirement:** Auto-generate delivery notes on dispatch. DN must include:
customer details, items, quantities, batch numbers, expiry dates.
Print/digital send. Goods receipt module with barcode/manual entry.

| Feature | Status | Notes |
|---------|--------|-------|
| Delivery note creation (auto on pick) | ✅ | Draft DN created, items linked with batch details |
| DN sequential numbering | ✅ | Auto-incremented |
| DN includes customer, items, qty, batch, expiry | ✅ | All fields on DN and DN items |
| DN status workflow | ✅ | DRAFT → ISSUED → DELIVERED → INVOICED (or CANCELLED) |
| DN PDF export | ✅ | ReportLab PDF generation |
| DN email to customer | ✅ | Async SMTP via email_service |
| DN search and history | ✅ | Paginated list with filters |
| Goods receipt with barcode scan | ✅ | Camera + manual, auto batch numbering |
| Goods receipt with qty + expiry + batch + location | ✅ | All mandatory fields validated |
| GRN document (Goods Receipt Note) | ❌ | PDF says: generate GRN with timestamp and user ID |
| Short expiry warning on receipt | ✅ | Alert if expiry < configurable threshold |
| Manager approval for short expiry | 🔧 | Warning shown but no approval workflow (accept/reject by manager) |

**What's missing:**
1. **GRN document** — when goods are received, generate a formal "Goods Receipt Note" PDF with: receipt date, user who received, items, batches, quantities. Currently the movement record exists but no printable GRN.
2. **Manager approval flow for short-expiry receipt** — when expiry is too close, the system warns but doesn't enforce manager sign-off. Could be a simple "requires MANAGER role to confirm" check.

---

### Module 4: Dashboard & Alerts (לוח מחוונים והתראות)

**PDF requirement:** Graphical dashboard as home page. KPIs: total inventory value,
inventory utilization rate, items below minimum. Risk map by expiration (color gauge).
Minimum threshold alerts. Email/notification for 30-day expiry. Dead stock report.

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard is home page | ✅ | Default route after login |
| KPIs: inventory value | ✅ | Sum of (cost_price × qty) across active batches |
| KPIs: items in stock count | ✅ | |
| KPIs: items below minimum | ✅ | Compared against `reorder_point` |
| Expiration risk map (color gauge) | ✅ | Green/Yellow/Red/Black distribution |
| Inventory distribution (pie chart) | ✅ | By item, Recharts |
| Movement trend (bar chart) | ✅ | Receipts vs dispatches over time |
| Top expiring batches list | ✅ | Top 10 nearest expiry |
| Reorder point alerts | ✅ | Alert when stock < reorder_point |
| Alert → create draft PO | ❌ | No PO module |
| Email alerts for 30-day expiry | ✅ | email_service + scheduler |
| Daily/weekly scheduled email reports | 🔧 | Scheduler exists, weekly report template exists, but scheduling is basic |
| Dead stock report | 🔧 | Alert generated, but no dedicated report page with cost + location |
| Inventory utilization rate (turnover) | ❌ | KPI mentioned in PDF but not calculated |
| Notification bell (real-time) | ✅ | WebSocket-driven, unread count badge, dropdown |

**What's missing:**
1. **Inventory turnover rate KPI** — (dispatched qty / average stock qty) over a period
2. **Dead stock dedicated report page** — show batches with no outbound movement for 180+ days, with cost and location, filterable
3. **PO creation from alert** — requires PO module (future)

---

### Module 5: Customer Site Inventory — CSI (ניהול מלאי אצל לקוח קצה)

**PDF says:** "In the future" — but the spec is detailed. VMI (Vendor Managed Inventory).
Track ink held at customer sites. Proactive replenishment. Consignment transfers.
Customer portal for consumption reporting.

| Feature | Status | Notes |
|---------|--------|-------|
| `is_vmi_customer` flag on customer | ✅ | Field exists in DB |
| `is_consignment` flag on delivery note | ✅ | Field exists in DB |
| Customer site as location type | ❌ | Locations are warehouse-only currently |
| Min/Max per customer-item combo | ❌ | No `customer_item_config` table |
| Consignment transfer DN type | ❌ | Flag exists but no distinct workflow |
| VMI dashboard (customer inventory view) | ❌ | No separate dashboard |
| Customer consumption reporting (portal) | ❌ | No customer-facing UI |
| CSV/Excel import for customer consumption | ❌ | |
| Auto replenishment suggestion | ❌ | |
| Customer portal: view batches + expiry | ❌ | |
| Billing report: actual consumption vs consignment | ❌ | |

**This is the largest unbuilt module.** It requires:

1. **Data model additions:**
   - `customer_locations` — a location type that links to a customer
   - `customer_item_config` — min/max stock per customer per item
   - Extend `delivery_notes` with consignment-specific fields

2. **Backend services:**
   - `vmi_service.py` — replenishment logic, consumption tracking
   - Customer-facing API endpoints (limited scope, possibly separate auth)

3. **Frontend pages:**
   - VMI Dashboard (manager view: all customer inventories)
   - Customer Portal (customer-facing: their stock, consumption reporting)
   - Replenishment suggestion workflow

4. **Reports:**
   - Customer consumption report (for billing)
   - Consignment vs invoiced inventory report

---

## 5. Implementation Phases

### Phase 1-6: DONE ✅

Everything listed as ✅ or 🔧 above is built and functional.
Core system is operational: items, batches, FEFO, receiving, picking, delivery notes,
alerts, dashboard, email, WebSocket, scheduler, barcode scanning, PWA, offline support.

### Phase 7: Reports & Analytics (next)

| # | Feature | Priority |
|---|---------|----------|
| 7.1 | Reports page with date range filters | High |
| 7.2 | Inventory valuation report (by item, by location, over time) | High |
| 7.3 | Scrap/waste report (value lost to expiration) | High |
| 7.4 | Dead stock report page (no movement > N days, with cost) | High |
| 7.5 | Stock movement report (inbound/outbound, turnover rate) | Medium |
| 7.6 | Batch traceability (full lifecycle: receipt → dispatch → customer) | Medium |
| 7.7 | FEFO compliance metrics (% picked in FEFO order) | Low |
| 7.8 | Customer analytics (sales by customer, delivery frequency) | Low |
| 7.9 | Inventory turnover KPI on dashboard | Medium |

### Phase 8: Production Hardening

| # | Feature | Priority |
|---|---------|----------|
| 8.1 | English locale (`en.json`) — complete translation | High |
| 8.2 | Language selector in settings + user preference in DB | High |
| 8.3 | RTL audit — all components work correctly in both directions | High |
| 8.4 | GRN document generation (PDF on goods receipt) | Medium |
| 8.5 | Location label printing (PDF/browser print) | Medium |
| 8.6 | Manager approval flow for short-expiry receipt | Low |
| 8.7 | Rate limiting on API | Medium |
| 8.8 | CI/CD pipeline (GitHub Actions: lint, test, deploy) | High |
| 8.9 | Security audit (input sanitization, CORS, headers) | High |

### Phase 9: CSI / VMI Module

| # | Feature | Priority |
|---|---------|----------|
| 9.1 | Customer location type + customer_item_config table | High |
| 9.2 | Consignment transfer workflow (DN type) | High |
| 9.3 | VMI dashboard (all customer inventories at a glance) | High |
| 9.4 | Auto replenishment suggestions (when customer stock < min) | High |
| 9.5 | Customer portal — limited login, view stock + expiry | Medium |
| 9.6 | Customer consumption reporting (manual entry or CSV upload) | Medium |
| 9.7 | Billing report — actual consumption for invoicing | Medium |
| 9.8 | "Company-owned, customer-held" inventory classification in reports | Medium |

---

## 6. Environment Variables

```bash
# ---- Database ----
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
# Render (and most providers) give postgresql:// — the app auto-converts to postgresql+asyncpg://

# ---- Security ----
SECRET_KEY=<random-string-min-32-chars>
ENVIRONMENT=production  # or development

# ---- JWT ----
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ---- CORS ----
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173

# ---- Alert Thresholds (days before expiry) ----
ALERT_THRESHOLD_120=120
ALERT_THRESHOLD_90=90
ALERT_THRESHOLD_60=60
ALERT_THRESHOLD_30=30

# ---- Dead Stock ----
DEAD_STOCK_DAYS=180

# ---- Email (SMTP) ----
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app-specific-password
EMAIL_FROM=noreply@linoprint.com

# ---- Frontend (Vite env) ----
VITE_API_URL=https://your-backend.onrender.com/api/v1
VITE_WS_URL=wss://your-backend.onrender.com/ws
```

---

## 7. API Route Map

All routes prefixed with `/api/v1`.

| Method | Path | Module | Auth |
|--------|------|--------|------|
| POST | `/auth/login` | Auth | No |
| POST | `/auth/refresh` | Auth | No |
| POST | `/auth/register` | Auth | Admin |
| GET | `/auth/me` | Auth | Yes |
| GET | `/items` | Items | Yes |
| POST | `/items` | Items | Manager+ |
| GET/PUT/DELETE | `/items/{id}` | Items | Manager+ |
| GET | `/batches` | Batches | Yes |
| GET | `/batches/{id}` | Batches | Yes |
| PUT | `/batches/{id}/mark-scrap` | Batches | Manager+ |
| PUT | `/batches/{id}/adjust-location` | Batches | Worker+ |
| GET/POST/PUT/DELETE | `/locations` | Locations | Manager+ |
| POST | `/receiving/receive` | Receiving | Worker+ |
| POST | `/receiving/receive-multiple` | Receiving | Worker+ |
| POST | `/receiving/validate-barcode` | Receiving | Worker+ |
| GET | `/receiving/batch-suggestions` | Receiving | Worker+ |
| GET | `/picking/suggestions/{item_id}` | Picking | Worker+ |
| POST | `/picking/validate/{batch_id}` | Picking | Worker+ |
| POST | `/picking/pick` | Picking | Worker+ |
| GET | `/picking/available-items` | Picking | Worker+ |
| GET/POST | `/delivery-notes` | DNs | Manager+ |
| GET/PUT | `/delivery-notes/{id}` | DNs | Manager+ |
| POST | `/delivery-notes/{id}/issue` | DNs | Manager+ |
| POST | `/delivery-notes/{id}/deliver` | DNs | Manager+ |
| GET | `/delivery-notes/{id}/pdf` | DNs | Yes |
| POST | `/delivery-notes/bulk-email` | DNs | Manager+ |
| GET | `/movements` | Movements | Yes |
| POST | `/movements/adjust` | Movements | Manager+ |
| GET/POST/PUT/DELETE | `/customers` | Customers | Manager+ |
| GET | `/alerts` | Alerts | Yes |
| PUT | `/alerts/{id}/read` | Alerts | Yes |
| PUT | `/alerts/{id}/dismiss` | Alerts | Yes |
| GET | `/dashboard/kpis` | Dashboard | Yes |
| GET | `/dashboard/distribution` | Dashboard | Yes |
| GET | `/dashboard/movements` | Dashboard | Yes |
| GET | `/dashboard/top-expiring` | Dashboard | Yes |
| GET/PUT | `/settings/user-preferences` | Settings | Yes |
| POST | `/settings/test-email` | Settings | Yes |
| WS | `/ws` | WebSocket | JWT in query param |

---

## 8. Frontend Page Map

| Route | Page | Description |
|-------|------|-------------|
| `/login` | LoginPage | JWT auth, redirects to `/` on success |
| `/` | DashboardPage | Home. KPIs, charts, risk map, top expiring |
| `/items` | ItemsPage | Item CRUD, search, filter, pagination |
| `/batches` | BatchesPage | Batch list, filter by item/status/expiry, FEFO sort |
| `/receiving` | ReceivingPage | Goods receipt workflow, barcode scan, batch creation |
| `/picking` | PickingPage | FEFO picking, batch suggestions, barcode verify |
| `/delivery-notes` | DeliveryNotesPage | DN management, status workflow, PDF, email |
| `/customers` | CustomersPage | Customer CRUD, VMI flag |
| `/alerts` | AlertsPage | Alert center, severity filter, mark read/dismiss |
| `/settings` | SettingsPage | Preferences, email notifications, theme, language |

**Layout:** `AppLayout` wraps all authenticated pages. Contains `Header` (with
`NotificationBell`) and `Sidebar` (collapsible). Mobile: bottom nav via `MobileNav`.

---

## 9. Key Business Rules

1. **Expiration date is mandatory** on every batch. Cannot be in the past at time of receipt.
2. **FEFO is enforced** — the system always suggests the nearest-expiry batch first. Picking a non-FEFO batch shows a warning but is allowed (with audit trail).
3. **Expired batches cannot be dispatched.** Hard block, not just a warning.
4. **Expired batches auto-scrap** — the daily scheduler marks them as SCRAP and creates a movement record.
5. **Batch numbers auto-generated** if not provided: `GR-YYMMDD-XXX` (e.g., `GR-260315-001`).
6. **Every inventory change creates a movement** — full audit trail with before/after quantities, user ID, timestamp.
7. **Delivery notes must include batch numbers and expiry dates** — this is a legal/compliance requirement per the PDF spec.
8. **Default users** are seeded on first startup if `ADMIN_SEED_PASSWORD` and `USER_SEED_PASSWORD` env vars are set: `admin` (ADMIN), `user` (VIEWER).
9. **Alert thresholds** are configurable but default to 120/90/60/30 days before expiry.
10. **Dead stock** = no outbound movement for 180+ days (configurable).
