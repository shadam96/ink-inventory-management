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
| 3 | ⬜ Open | `backend/app/api/v1/endpoints/delivery_notes.py:179` | `get_delivery_note` / `list_delivery_notes` / `get_delivery_note_pdf` never check that a note's `customer_id` matches the requesting CUSTOMER-role user's own `customer_id` — an IDOR. `inventory_view.py` scopes correctly for the same role; this endpoint doesn't. |
| 4 | ⬜ Open | `backend/app/api/v1/endpoints/picking.py:347` | `consume_item` is reachable by CUSTOMER-role users but never verifies the target `batch_id` belongs to that customer's allocated stock — lets a customer dispatch from another customer's consignment stock. |
| 5 | ⬜ Open | `backend/app/api/v1/endpoints/auth.py:29` | `/auth/login` has no rate limiting or lockout — unlimited online password-guessing against any known username. |
| 6 | ⬜ Open | `backend/app/main.py:96` + `core/config.py:81` | Global exception handler leaks raw exception text whenever `settings.is_development` is true, which is the **default** unless `ENVIRONMENT` is explicitly set — a forgotten env var leaks internal errors to any client on a 500. |
| 7 | ⬜ Open | `frontend/src/hooks/useWebSocket.ts:14` | The WebSocket singleton is never disconnected on logout, so a different user logging in on the same tab/device reuses the previous user's still-open, authenticated socket. |
| 8 | ⬜ Open | `frontend/src/pages/ReceivingPage.tsx:40` | `receiveList` (unsubmitted receiving queue) is persisted in **global** `localStorage` and never cleared on logout — one user's unsubmitted batch data leaks into the next user's session on a shared device/tablet. |

## 2. Data integrity / correctness

| # | Status | File | Issue |
|---|--------|------|-------|
| 9 | ✅ Fixed | `backend/alembic/versions/c3d4e5f6g7h8_add_customer_role_and_consumption.py:23-24` | Migration adds the new `userrole`/`movementtype` enum labels in **lowercase** (`'customer'`, `'consumption'`), but SQLAlchemy's `Enum()` columns (no `values_callable`) bind the Python member's **uppercase** `.name` by default. Result: assigning `UserRole.CUSTOMER` or recording `MovementType.CONSUMPTION` raises `invalid input value for enum` and 500s — both features are completely broken at the DB layer. |
| 10 | ⬜ Open | `backend/app/models/item.py:76` | `Item.batches` uses `cascade="all, delete-orphan"` while `Batch.item_id`'s FK is `ondelete="RESTRICT"` — the RESTRICT never fires via the ORM path. Deleting an Item cascades through all its Batches and, transitively, every Movement audit record. |
| 11 | ⬜ Open | `backend/app/services/inventory_service.py:156` | `adjust_quantity` computes its delta from an **un-locked** read of `quantity_available`, then `record_movement` re-reads the row `with_for_update()` and applies the now-stale delta to the fresh value — under concurrent writes the final quantity diverges from the intended `new_quantity`. |
| 12 | ⬜ Open | `backend/app/services/inventory_service.py:98` | `record_movement` never validates `quantity > 0` for RECEIPT/DISPATCH/CONSUMPTION/SCRAP; a negative quantity passed to a DISPATCH can **increase** stock instead of decreasing it (defense-in-depth gap — Pydantic guards the HTTP layer but not the service function itself). |
| 13 | ⬜ Open | `backend/app/services/receiving_service.py:200` | `receive_multiple` never validates `quantity > 0` before creating a batch, unlike `receive_goods` which does. |
| 14 | ⬜ Open | `backend/app/services/receiving_service.py:29` | `generate_batch_number` reads `MAX(batch_number)` with no row lock; two concurrent receipts can compute the same next sequence and hit a unique-constraint `IntegrityError`. |
| 15 | ⬜ Open | `backend/app/services/alert_service.py:164` | The duplicate-alert guard in `check_expiring_batches` always queries `alert_type == EXPIRATION_WARNING`, even on the branch that creates `EXPIRATION_CRITICAL` alerts — so the guard never matches and critical alerts/emails duplicate on every run. |
| 16 | ⬜ Open | `backend/app/services/alert_service.py:142` | `prev_threshold` is computed but never used to lower-bound the query, so the 30/60/90/120-day threshold bands overlap instead of partitioning — one batch can generate alerts at multiple severities in a single run. |
| 17 | ⬜ Open | `backend/app/services/dashboard_service.py:121` | `get_expiration_risk_map` sums `quantity_available * cost_price` across items **regardless of `item.currency`**, unlike `get_inventory_value` which correctly buckets by currency — produces a meaningless combined total as soon as two items use different currencies. |
| 18 | ⬜ Open | `backend/app/services/export_service.py:220` | `days_until_expiry or ""` treats a batch expiring **today** (`0`) as falsy, writing an empty CSV cell instead of `"0"` — indistinguishable from a missing expiration date. |
| 19 | ⬜ Open | `backend/app/api/v1/endpoints/batches.py:245` | `update_batch` increments `Batch.version` as "optimistic locking" but never compares an incoming expected version (`BatchUpdate` has no `version` field) — the mechanism is decorative; concurrent edits silently clobber each other. |
| 20 | ⬜ Open | `backend/app/main.py:29` | Scheduler start condition `if not settings.is_development or settings.environment != "test"` is a tautology (always `True`) — the intended dev/test suppression of the background scheduler never applies. |
| 21 | ⬜ Open | `backend/app/api/deps.py:37` | `get_current_user` returns **404** "User not found" for a valid-but-stale JWT (user deleted after token issuance) instead of **401** — an unusual status for an auth failure that can misroute frontend error handling. |
| 22 | ⬜ Open | `backend/alembic/versions/e5f6g7h8i9j0_customer_phone_split_and_machines.py:95` | `downgrade()` collapses `phone_primary`/`phone_secondary` back into one column via `COALESCE(phone_primary, phone_secondary)`, permanently discarding `phone_secondary` whenever both are set — data loss on any manual rollback. |
| 23 | ⬜ Open | `backend/app/models/alert.py:49` | `batch_id` and `item_id` are both nullable with no constraint enforcing "at least one must be set"; `AlertCreate` mirrors the gap — an orphan alert traceable to nothing can be created. |
| 24 | ⬜ Open | `backend/app/models/batch.py:43` | The table's `CheckConstraint` enforces `quantity_available >= 0` but not `quantity_received >= 0`. |
| 25 | ⬜ Open | `backend/app/schemas/item.py:29` | `ItemCreate`/`ItemUpdate` validate `reorder_point`/`min_stock`/`max_stock` independently (`ge=0`) with no cross-field check — `min_stock=100, max_stock=5` is accepted and breaks reorder-alert logic. |

## 3. Frontend correctness

| # | Status | File | Issue |
|---|--------|------|-------|
| 26 | ✅ Fixed | `frontend/src/pages/ReceivingPage.tsx:101` | `applyParsedData` only **sets** fields present in a newly scanned barcode's `parsed_data` and never clears fields left from a previous scan — scanning item A (with embedded expiration/quantity) then item B (plain barcode) submits item B under item A's leftover expiration date and quantity. |
| 27 | ⬜ Open | `frontend/src/pages/ReceivingPage.tsx` + `PickingPage.tsx` (offline queue) | Offline-queued operations store a path like `/api/v1/receiving/multiple` that, combined with axios's `baseURL` (already `.../api/v1`), doubles the prefix on replay — every queued offline receive/pick 404s and is **silently dropped** after retries, losing the user's offline work. |
| 28 | ⬜ Open | `frontend/src/lib/api.ts:32` | The 401 interceptor has no single-flight lock; concurrent 401s trigger independent `/auth/refresh` calls, which can race and log the user out even though a valid refreshed session exists. |
| 29 | ⬜ Open | `frontend/src/lib/offline.ts:219` | `syncPendingOperations` compares `operation.retryCount` against a stale in-memory snapshot taken before `incrementRetryCount` persists its own increment — the real cutoff is 4 failed attempts, not the documented 3. |
| 30 | ⬜ Open | `frontend/src/lib/websocket.ts:71` | `disconnect()` doesn't clear `this.token`; the async `onclose` handler bound before disconnect can still fire afterward and trigger an unwanted reconnect using the stale token. |
| 31 | ⬜ Open | `frontend/src/App.tsx:44` | `StaffRoute` checks `user?.role`, but the persisted auth store only rehydrates `isAuthenticated` (not `user`) — on page reload a customer-role user can briefly render/fetch staff-only routes before the async `fetchUser()` resolves and redirects. |
| 32 | ⬜ Open | `frontend/src/hooks/useWebSocket.ts:22` | Reconnect logic reuses the token captured at the original `connect()` call; after `api.ts` silently rotates the access token via refresh, a dropped socket reconnects with the stale token and can fail every attempt. |
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

## Fixed in this pass (top 3 by severity)

1. **#1 — Open admin self-registration** (`auth.py`)
2. **#2 — Unauthenticated WebSocket broadcast** (`websocket.py` / `core/websocket.py`)
3. **#9 — Enum case mismatch breaking customer-role & consumption-tracking** (migration + models)

See commit history / diff for the actual changes. Everything else in this
document remains open and is prioritized roughly in the order listed within
each section.

## Note on repo hygiene

`frontend/.env` and `backend/test.db` are already committed in the remote git
history (`origin/main`). `.env` in particular may contain secrets — worth
rotating any real credentials it holds and scrubbing it from history
(`git filter-repo` or BFG) since simply deleting it in a new commit does not
remove it from prior commits.
