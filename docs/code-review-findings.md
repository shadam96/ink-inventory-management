# Code Review Findings — Full Codebase Audit (2026-07-20)

Full-codebase review (no PR/diff existed at review time) of the FastAPI backend
(`backend/`) and React/TypeScript frontend (`frontend/`). Six review agents ran
independently across backend services, backend API/core, backend
models/migrations, frontend lib/hooks/store, frontend pages/components, and a
cross-cutting cleanup pass. Every correctness/security candidate below was
independently re-verified against the actual code; verdicts are noted.

Status column: ✅ **Fixed** in this pass · ⬜ **Open**

---

## 1. Security

| # | Status | File | Issue |
|---|--------|------|-------|
| 1 | ✅ Fixed | `backend/app/api/v1/endpoints/auth.py:117` | `/register` has no auth dependency and accepts a client-supplied `role`, letting anyone self-provision an **ADMIN** account. |
| 2 | ✅ Fixed | `backend/app/api/v1/endpoints/websocket.py:48` | Connections with a missing/invalid JWT are accepted as `"anonymous"` instead of rejected, and `broadcast()` sends live inventory/alert/batch data to every connection, including anonymous ones. |
| 3 | ✅ Fixed | `backend/app/api/v1/endpoints/delivery_notes.py:179` | `get_delivery_note` / `list_delivery_notes` / `get_delivery_note_pdf` never check that a note's `customer_id` matches the requesting CUSTOMER-role user's own `customer_id` — an IDOR. `inventory_view.py` scopes correctly for the same role; this endpoint doesn't. |
| 4 | ✅ Fixed | `backend/app/api/v1/endpoints/picking.py:347` | `consume_item` is reachable by CUSTOMER-role users but never verifies the target `batch_id` belongs to that customer's allocated stock — lets a customer dispatch from another customer's consignment stock. |
| 5 | ✅ Fixed | `backend/app/api/v1/endpoints/auth.py:29` | `/auth/login` has no rate limiting or lockout — unlimited online password-guessing against any known username. |
| 6 | ✅ Fixed | `backend/app/main.py:96` + `core/config.py:81` | Global exception handler leaks raw exception text whenever `settings.is_development` is true, which is the **default** unless `ENVIRONMENT` is explicitly set — a forgotten env var leaks internal errors to any client on a 500. |
| 7 | ✅ Fixed | `frontend/src/hooks/useWebSocket.ts:14` | The WebSocket singleton is never disconnected on logout, so a different user logging in on the same tab/device reuses the previous user's still-open, authenticated socket. |
| 8 | ✅ Fixed | `frontend/src/pages/ReceivingPage.tsx:40` | `receiveList` (unsubmitted receiving queue) is persisted in **global** `localStorage` and never cleared on logout — one user's unsubmitted batch data leaks into the next user's session on a shared device/tablet. |

## 2. Data integrity / correctness

| # | Status | File | Issue |
|---|--------|------|-------|
| 9 | ✅ Fixed | `backend/alembic/versions/c3d4e5f6g7h8_add_customer_role_and_consumption.py:23-24` | Migration adds the new `userrole`/`movementtype` enum labels in **lowercase** (`'customer'`, `'consumption'`), but SQLAlchemy's `Enum()` columns (no `values_callable`) bind the Python member's **uppercase** `.name` by default. Result: assigning `UserRole.CUSTOMER` or recording `MovementType.CONSUMPTION` raises `invalid input value for enum` and 500s — both features are completely broken at the DB layer. |
| 10 | ✅ Fixed | `backend/app/models/item.py:76` | `Item.batches` uses `cascade="all, delete-orphan"` while `Batch.item_id`'s FK is `ondelete="RESTRICT"` — the RESTRICT never fires via the ORM path. Deleting an Item cascades through all its Batches and, transitively, every Movement audit record. |
| 11 | ✅ Fixed | `backend/app/services/inventory_service.py:156` | `adjust_quantity` computes its delta from an **un-locked** read of `quantity_available`, then `record_movement` re-reads the row `with_for_update()` and applies the now-stale delta to the fresh value — under concurrent writes the final quantity diverges from the intended `new_quantity`. |
| 12 | ⬜ Open | `backend/app/services/inventory_service.py:98` | `record_movement` never validates `quantity > 0` for RECEIPT/DISPATCH/CONSUMPTION/SCRAP; a negative quantity passed to a DISPATCH can **increase** stock instead of decreasing it (defense-in-depth gap — Pydantic guards the HTTP layer but not the service function itself). |
| 13 | ⬜ Open | `backend/app/services/receiving_service.py:200` | `receive_multiple` never validates `quantity > 0` before creating a batch, unlike `receive_goods` which does. |
| 14 | ⬜ Open | `backend/app/services/receiving_service.py:29` | `generate_batch_number` reads `MAX(batch_number)` with no row lock; two concurrent receipts can compute the same next sequence and hit a unique-constraint `IntegrityError`. |
| 15 | ✅ Fixed | `backend/app/services/alert_service.py:164` | The duplicate-alert guard in `check_expiring_batches` always queries `alert_type == EXPIRATION_WARNING`, even on the branch that creates `EXPIRATION_CRITICAL` alerts — so the guard never matches and critical alerts/emails duplicate on every run. |
| 16 | ✅ Fixed | `backend/app/services/alert_service.py:142` | `prev_threshold` is computed but never used to lower-bound the query, so the 30/60/90/120-day threshold bands overlap instead of partitioning — one batch can generate alerts at multiple severities in a single run. |
| 17 | ⬜ Open | `backend/app/services/dashboard_service.py:121` | `get_expiration_risk_map` sums `quantity_available * cost_price` across items **regardless of `item.currency`**, unlike `get_inventory_value` which correctly buckets by currency — produces a meaningless combined total as soon as two items use different currencies. |
| 18 | ⬜ Open | `backend/app/services/export_service.py:220` | `days_until_expiry or ""` treats a batch expiring **today** (`0`) as falsy, writing an empty CSV cell instead of `"0"` — indistinguishable from a missing expiration date. |
| 19 | ✅ Fixed | `backend/app/api/v1/endpoints/batches.py:245` | `update_batch` increments `Batch.version` as "optimistic locking" but never compares an incoming expected version (`BatchUpdate` has no `version` field) — the mechanism is decorative; concurrent edits silently clobber each other. |
| 20 | ✅ Fixed | `backend/app/main.py:29` | Scheduler start condition `if not settings.is_development or settings.environment != "test"` is a tautology (always `True`) — the intended dev/test suppression of the background scheduler never applies. |
| 21 | ⬜ Open | `backend/app/api/deps.py:37` | `get_current_user` returns **404** "User not found" for a valid-but-stale JWT (user deleted after token issuance) instead of **401** — an unusual status for an auth failure that can misroute frontend error handling. |
| 22 | ⬜ Open | `backend/alembic/versions/e5f6g7h8i9j0_customer_phone_split_and_machines.py:95` | `downgrade()` collapses `phone_primary`/`phone_secondary` back into one column via `COALESCE(phone_primary, phone_secondary)`, permanently discarding `phone_secondary` whenever both are set — data loss on any manual rollback. |
| 23 | ⬜ Open | `backend/app/models/alert.py:49` | `batch_id` and `item_id` are both nullable with no constraint enforcing "at least one must be set"; `AlertCreate` mirrors the gap — an orphan alert traceable to nothing can be created. |
| 24 | ⬜ Open | `backend/app/models/batch.py:43` | The table's `CheckConstraint` enforces `quantity_available >= 0` but not `quantity_received >= 0`. |
| 25 | ⬜ Open | `backend/app/schemas/item.py:29` | `ItemCreate`/`ItemUpdate` validate `reorder_point`/`min_stock`/`max_stock` independently (`ge=0`) with no cross-field check — `min_stock=100, max_stock=5` is accepted and breaks reorder-alert logic. |

## 3. Frontend correctness

| # | Status | File | Issue |
|---|--------|------|-------|
| 26 | ✅ Fixed | `frontend/src/pages/ReceivingPage.tsx:101` | `applyParsedData` only **sets** fields present in a newly scanned barcode's `parsed_data` and never clears fields left from a previous scan — scanning item A (with embedded expiration/quantity) then item B (plain barcode) submits item B under item A's leftover expiration date and quantity. |
| 27 | ✅ Fixed | `frontend/src/pages/ReceivingPage.tsx` + `PickingPage.tsx` (offline queue) | Offline-queued operations store a path like `/api/v1/receiving/multiple` that, combined with axios's `baseURL` (already `.../api/v1`), doubles the prefix on replay — every queued offline receive/pick 404s and is **silently dropped** after retries, losing the user's offline work. |
| 28 | ✅ Fixed | `frontend/src/lib/api.ts:32` | The 401 interceptor has no single-flight lock; concurrent 401s trigger independent `/auth/refresh` calls, which can race and log the user out even though a valid refreshed session exists. |
| 29 | ⬜ Open | `frontend/src/lib/offline.ts:219` | `syncPendingOperations` compares `operation.retryCount` against a stale in-memory snapshot taken before `incrementRetryCount` persists its own increment — the real cutoff is 4 failed attempts, not the documented 3. |
| 30 | ✅ Fixed | `frontend/src/lib/websocket.ts:71` | `disconnect()` doesn't clear `this.token`; the async `onclose` handler bound before disconnect can still fire afterward and trigger an unwanted reconnect using the stale token. |
| 31 | ⬜ Open | `frontend/src/App.tsx:44` | `StaffRoute` checks `user?.role`, but the persisted auth store only rehydrates `isAuthenticated` (not `user`) — on page reload a customer-role user can briefly render/fetch staff-only routes before the async `fetchUser()` resolves and redirects. |
| 32 | ✅ Fixed | `frontend/src/hooks/useWebSocket.ts:22` | Reconnect logic reuses the token captured at the original `connect()` call; after `api.ts` silently rotates the access token via refresh, a dropped socket reconnects with the stale token and can fail every attempt. |
| 33 | ⬜ Open | `frontend/src/pages/ReceivingPage.tsx:22` | `receiveSchema.quantity` is `z.number().min(1, ...)` with no `.int()` (picking schemas do use `.int()`), allowing fractional receiving quantities like `2.5`. |
| 34 | ⬜ Open | `frontend/src/components/ItemDialog.tsx:136`, `CustomerDialog.tsx:119` | Dialog dismissal via Escape/overlay-click isn't gated by `isSubmitting` (only the Cancel button is) — closing mid-save and reopening for a different entity can let the stale request's success callback reset/close the new form. |
| 35 | ⬜ Open | `frontend/src/components/BarcodeScanner.tsx:150` | The scanning effect depends on unmemoized `onScan`/`onClose` callbacks recreated every parent render — any parent re-render while the scanner is open tears down and restarts the camera; `stop()` isn't awaited before the next `start()`. |
| 36 | ⬜ Open | `frontend/src/pages/PickingPage.tsx:125` | `fetchSuggestions` fires on every keystroke with no request cancellation/sequencing — an out-of-order response for an earlier-typed quantity can overwrite state from a later, faster response. |
| 37 | ⬜ Open | `frontend/src/pages/PickingPage.tsx:141` | `fetchItems`/`fetchCustomers` failures are only `console.error`'d with no user-facing error — indistinguishable from a legitimately empty items/customers list. |

## 4. Cleanup / duplication (lower priority — outranked by the above)

- **Expiration-risk thresholds** (days → critical/warning/caution) are reimplemented independently in `fefo_engine.py`, `dashboard_service.py`, `inventory_service.py`, and `receiving_service.py` with inconsistent cutoffs (30/60/90 vs 30/60/180).
- **"Available stock for an item"** computation duplicated 5× across `dashboard_service.py`, `alert_service.py`, `inventory_service.py`.
- **`except ValueError as e: raise HTTPException(400, str(e))`** repeated 8× across `picking.py`, `receiving.py`, `delivery_notes.py` — candidate for a shared exception handler/dependency.
- **Sequential document-number generation** duplicated between `receiving_service.py` and `document_service.py`.
- `settings.py`'s `send_test_email` does an inline role check instead of using the existing `RequireManager`/`ManagerUser` dependency.
- `dashboard_service.get_kpi_summary` triggers 3-4 overlapping full-table scans of Items+Batches that could be computed from one fetch.
- Four near-identical email-dispatch methods in `alert_service.py` duplicate the recipient-loop/try-except boilerplate.
- `inventory_view.py` compares `current_user.role == "customer"` (raw string) instead of the `UserRole` enum used elsewhere.
- `dashboard_service.get_expiration_risk_map` rebuilds the same bucket structure `fefo_engine.get_expiration_summary` already builds.

---

## Fixed so far

**Pass 1 (top 3 by severity):**
1. **#1 — Open admin self-registration** (`auth.py`)
2. **#2 — Unauthenticated WebSocket broadcast** (`websocket.py` / `core/websocket.py`)
3. **#9 — Enum case mismatch breaking customer-role & consumption-tracking** (migration + models)

**Pass 2 (next 3 by severity):**
4. **#3 — Delivery-note IDOR** (`delivery_notes.py`) — `get_delivery_note`, `list_delivery_notes`, and `get_delivery_note_pdf` now reject/scope access for CUSTOMER-role users to their own `customer_id`, matching the pattern already used in `inventory_view.py`. Tests added in `test_delivery_notes.py`.
5. **#4 — Picking consume_item IDOR** (`picking.py`) — `consume_item` now verifies, for CUSTOMER-role callers, that the target batch was actually dispatched to their `customer_id` via a `DeliveryNoteItem`/`DeliveryNote` join, returning 403 otherwise. Tests added in `test_picking.py`.
6. **#26 — Barcode-scan stale data leakage** (`ReceivingPage.tsx`) — `applyParsedData` now clears `expiration_date`/`manufacturing_date`/`quantity`/`batch_number` back to defaults for any field the current scan doesn't provide, instead of only setting fields present in `parsed_data`. Also fixed a null-vs-undefined bug introduced while writing this fix (the backend can return `parsed_data: null`, which a naive default parameter doesn't catch). Regression test added in `receiving.test.tsx`.

**Pass 3 (next 3 by severity):**
7. **#10 — Item-delete cascade destroys audit trail** (`item.py` / `inventory.py`) — removed `cascade="all, delete-orphan"` from `Item.batches` so the DB's `ondelete="RESTRICT"` on `batches.item_id` actually fires instead of being bypassed by the ORM. `delete_item` now blocks deletion whenever the item has *any* batches (not just active ones), since depleted/expired batches still carry historical Movement records. Tests added in `test_items.py`.
8. **#11 — `adjust_quantity` race condition** (`inventory_service.py`) — the initial batch read now uses `with_for_update()` so the row lock is held from the moment the adjustment delta is computed, not just inside `record_movement`'s internal re-read; this closes the window where a concurrent movement could land between the two reads and make the final quantity diverge from the caller's intended `new_quantity`. Service-level test added in `test_movements.py` (the concurrent-write race itself isn't mechanically testable under the SQLite test backend, which silently ignores `FOR UPDATE`).
9. **#27 — Offline queue posts to the wrong URL** (`ReceivingPage.tsx`, `PickingPage.tsx`) — queued offline receive/dispatch operations now use paths relative to `api`'s `baseURL` (`/receiving/receive`, `/receiving/receive-multiple`, `/picking/dispatch`), matching what `receivingApi`/`pickingApi` actually call, instead of a hardcoded `/api/v1/...` prefix that doubled the base URL and 404s on every replay. Regression test added in `receiving.test.tsx`.

**Pass 4 (next 10 by severity):**
10. **#5 — No login rate limiting** (`auth.py`, `models/user.py`) — added `failed_login_attempts`/`locked_until` columns (migration `f7g8h9i0j1k2`) and lockout logic in `/auth/login`: after 5 consecutive failed attempts the account locks for 15 minutes (429), resetting on any successful login. Tests added in `test_auth.py`.
11. **#6 — Exception-detail leak on misconfiguration** (`main.py`) — the global exception handler no longer sends `str(exc)` to the client at all (previously gated on `settings.is_development`, which defaults to `True`); full details now go to the server log via `logger.exception(...)` instead.
12. **#15 & #16 — Duplicate/overlapping expiration alerts** (`alert_service.py`) — `check_expiring_batches`'s threshold bands now partition batches by days-until-expiration (via a `prev_days` lower bound) instead of overlapping, and the dedup guard checks the actual `alert_type` for the current band instead of a hardcoded `EXPIRATION_WARNING`. Also switched the "already alerted" check from a dialect-fragile `func.date(created_at) == today` (works on Postgres, not reliably on SQLite) to "no matching alert that isn't yet dismissed," which is both portable and avoids re-alerting daily for a batch nobody has acted on. Tests added in `test_alerts.py`.
13. **#19 — Decorative optimistic locking on batches** (`schemas/batch.py`, `batches.py`) — `BatchUpdate` gained an optional `version` field; `update_batch` now returns 409 if it doesn't match the row's current version. While adding tests for this, also fixed a pre-existing, untested bug in the same endpoint: `db.refresh(batch)` expired the `item`/`location` relationships without reloading them, so accessing `batch.inventory_value` (a property that reads `self.item.cost_price`) during response serialization raised `MissingGreenlet` on every real (non-SQLite) update — replaced with a fresh eager-loaded re-fetch. Tests added in new `test_batches.py`.
14. **#7, #30, #32 — WebSocket session/token lifecycle** (`websocket.ts`, `useWebSocket.ts`) — three related fixes: (a) `disconnect()` now clears `this.token` so an async `onclose` arriving after an intentional disconnect can't schedule a reconnect with stale credentials; (b) reconnection now re-reads the token from `localStorage` instead of reusing the value captured at the original `connect()` call, so it survives `api.ts` silently rotating the token on refresh; (c) `useWebSocket`'s effect now calls `disconnect()` when `isAuthenticated` flips to false (logout), instead of only ever connecting and never tearing down. Tests added in new `websocket.test.ts` and `useWebSocket.test.ts`.
15. **#8 — receiveList leaks across users on a shared device** (`store/auth.ts`) — `logout()` now also removes the `receiveList` localStorage key, alongside the existing token cleanup. Test added in `stores/auth.test.ts`.
16. **#28 — 401 refresh has no single-flight lock** (`lib/api.ts`) — concurrent 401s now share one in-flight `/auth/refresh` call via a module-level `refreshPromise`, instead of each firing an independent refresh that can race if the backend rotates refresh tokens on use. Test added in new `api-refresh.test.ts`.

See commit history / diff for the actual changes. Everything else in this
document remains open and is prioritized roughly in the order listed within
each section.

## Note on repo hygiene

`frontend/.env` and `backend/test.db` are already committed in the remote git
history (`origin/main`). `.env` in particular may contain secrets — worth
rotating any real credentials it holds and scrubbing it from history
(`git filter-repo` or BFG) since simply deleting it in a new commit does not
remove it from prior commits.
