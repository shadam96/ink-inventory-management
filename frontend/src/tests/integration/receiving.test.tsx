import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { toast } from 'sonner'
import { ReceivingPage } from '@/pages/ReceivingPage'
import * as api from '@/lib/api'
import * as offline from '@/lib/offline'

vi.mock('@/lib/api', () => ({
  // NotificationBell (rendered inside <Header>, which ReceivingPage
  // renders) imports the default axios instance directly for its own
  // alert fetch - stub it too so that unrelated fetch doesn't error.
  default: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
  },
  itemsApi: {
    list: vi.fn(),
  },
  receivingApi: {
    validateBarcode: vi.fn(),
    receive: vi.fn(),
    receiveMultiple: vi.fn(),
  },
  systemSettingsApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    // dir() is used by DirectionalIcon.tsx (ChevronStart/ChevronEnd, now
    // rendered by DateField's month-nav) - matches the 'he' language above.
    i18n: { language: 'he', dir: () => 'rtl' },
  }),
}))

vi.mock('@/lib/offline', () => ({
  isOnline: vi.fn(),
  addPendingOperation: vi.fn(),
}))

const mockItems = [
  {
    id: '1',
    sku: 'INK-001',
    name: 'דיו שחור',
    supplier: 'ספק א',
    unit_of_measure: 'ליטר',
    cost_price: 100,
  },
  {
    id: '2',
    sku: 'INK-002',
    name: 'דיו כחול',
    supplier: 'ספק ב',
    unit_of_measure: 'ליטר',
    cost_price: 120,
  },
]

// Local-calendar "YYYY-MM-DD" n days from today - a hardcoded date would
// eventually drift under the shelf-life threshold and break these tests.
function isoDateInDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const FAR_EXPIRY = isoDateInDays(400)

interface StagedRow {
  id: string
  item_id: string
  item_name: string
  item_sku: string
  quantity: number
  expiration_date: string
  manufacturing_date: string
  batch_number: string
  notes: string
}

function stagedRow(id: string, overrides: Partial<StagedRow> = {}): StagedRow {
  return {
    id,
    item_id: mockItems[0].id,
    item_name: mockItems[0].name,
    item_sku: mockItems[0].sku,
    quantity: 10,
    expiration_date: FAR_EXPIRY,
    manufacturing_date: '',
    batch_number: '',
    notes: '',
    ...overrides,
  }
}

// ReceivingPage reads the staged list from localStorage on mount and
// writes it back on every change - that persisted copy is what survives a
// reload or navigating away, so tests assert on it directly.
const seedList = (...rows: StagedRow[]) => localStorage.setItem('receiveList', JSON.stringify(rows))
const storedList = (): StagedRow[] => JSON.parse(localStorage.getItem('receiveList') ?? '[]')

const renderPage = () =>
  render(
    <BrowserRouter>
      <ReceivingPage />
    </BrowserRouter>
  )

function stagedRows(): HTMLElement[] {
  const list = screen.queryByRole('list', { name: /receiving\.listTitle/ })
  return list ? within(list).getAllByRole('listitem') : []
}

function rowFor(batchNumber: string): HTMLElement {
  const row = stagedRows().find((r) => r.textContent?.includes(batchNumber))
  if (!row) throw new Error(`No staged row for batch ${batchNumber}`)
  return row
}

const quantityInput = () => document.getElementById('quantity') as HTMLInputElement
const batchInput = () => document.getElementById('batch_number') as HTMLInputElement
const itemSelect = () => document.getElementById('item_id') as HTMLSelectElement
const addButton = () => screen.getByRole('button', { name: /receiving\.addToList/ })
const updateButton = () => screen.getByRole('button', { name: /receiving\.updateItem/ })

// The barcode submit button is icon-only (no accessible name), so type
// into the input - found by its echoed placeholder key - and submit its form.
async function scan(
  user: UserEvent,
  code: string,
  item: object,
  parsedData: object | null = { expiration_date: FAR_EXPIRY }
) {
  vi.mocked(api.receivingApi.validateBarcode).mockResolvedValueOnce({
    valid: true,
    item,
    parsed_data: parsedData,
  })
  const input = screen.getByPlaceholderText('receiving.enterBarcode')
  await user.type(input, code)
  fireEvent.submit(input.closest('form')!)
  // A successful lookup clears the barcode field.
  await waitFor(() => expect(input).toHaveValue(''))
}

async function setQuantity(user: UserEvent, value: number) {
  await user.clear(quantityInput())
  await user.type(quantityInput(), String(value))
}

const startEditing = (user: UserEvent, batchNumber: string) =>
  user.click(within(rowFor(batchNumber)).getByTitle('receiving.editItem'))

// ReceivingPage renders two "receive all" buttons (a desktop one and a
// mobile sticky-bar one, shown/hidden via responsive classes only - jsdom
// doesn't evaluate real CSS, so both are query-visible here). They call
// the same handler, so clicking either is equivalent.
async function clickReceiveAll(user: UserEvent) {
  const [button] = await screen.findAllByRole('button', { name: /receiving\.receiveAll/ })
  await user.click(button)
}

describe('Receiving Operations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    vi.mocked(api.itemsApi.list).mockResolvedValue({
      items: mockItems,
      total: 2,
      page: 1,
      page_size: 100,
    })
    vi.mocked(api.systemSettingsApi.get).mockResolvedValue({
      usd_to_ils: 3.7,
      eur_to_ils: 4.0,
      try_to_ils: 0.11,
      min_shelf_life_days: 180,
      updated_at: new Date().toISOString(),
    })
    vi.mocked(api.receivingApi.receive).mockResolvedValue({})
    vi.mocked(api.receivingApi.receiveMultiple).mockResolvedValue({})
    // Default to online - individual tests override this to exercise the
    // offline paths (isOnline() is a bare vi.fn() otherwise, which returns
    // undefined/falsy and would put every test in the "offline" branch).
    vi.mocked(offline.isOnline).mockReturnValue(true)
  })

  it('should load items for selection', async () => {
    renderPage()

    await waitFor(() => {
      expect(api.itemsApi.list).toHaveBeenCalled()
    })
  })

  it('should validate barcode', async () => {
    const user = userEvent.setup()

    vi.mocked(api.receivingApi.validateBarcode).mockResolvedValue({
      valid: true,
      item: mockItems[0],
    })

    renderPage()

    const barcodeInput = screen.getByPlaceholderText('receiving.enterBarcode')
    await user.type(barcodeInput, '1234567890')
    fireEvent.submit(barcodeInput.closest('form')!)

    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).toHaveBeenCalledWith('1234567890')
    })
  })

  it('should not fill the form when the barcode is not found', async () => {
    const user = userEvent.setup()

    vi.mocked(api.receivingApi.validateBarcode).mockResolvedValue({
      valid: false,
      item: null,
    })

    renderPage()

    const barcodeInput = screen.getByPlaceholderText('receiving.enterBarcode')
    await user.type(barcodeInput, 'INVALID')
    fireEvent.submit(barcodeInput.closest('form')!)

    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).toHaveBeenCalledWith('INVALID')
    })
    // A not-found lookup never calls setValue('item_id', ...), so the
    // select stays at its unset default instead of being filled in.
    expect(itemSelect().value).toBe('')
  })

  it('should let the browser accept a whole-liter scanned quantity', async () => {
    // Regression: the input had step=1 with min=0.001, and a number input's
    // step counts from its min - so the only "valid" values were 0.001,
    // 1.001, 2.001, ... and the browser's own constraint validation blocked
    // adding a scanned box quantity like 10 L. fireEvent.submit bypasses
    // that validation, so check the input's validity state directly.
    renderPage()

    for (const value of ['1', '10', '20', '200']) {
      fireEvent.change(quantityInput(), { target: { value } })
      expect(quantityInput().validity.valid).toBe(true)
    }
  })

  it('should reject a fractional quantity (scanned boxes are always whole liters)', async () => {
    renderPage()

    await waitFor(() => {
      expect(itemSelect().querySelector('option[value="1"]')).toBeInTheDocument()
    })
    fireEvent.change(itemSelect(), { target: { value: '1' } })
    fireEvent.change(quantityInput(), { target: { value: '2.5' } })

    // expiration_date is a DateField (a button opening a calendar popover,
    // not a native input) - fireEvent.change doesn't apply. The exact date
    // doesn't matter for this test's intent, so just pick "today".
    fireEvent.click(document.getElementById('expiration_date')!)
    fireEvent.click(await screen.findByText('common.today'))

    fireEvent.submit(addButton().closest('form')!)

    await waitFor(() => {
      expect(screen.getByText('receiving.quantityInteger')).toBeInTheDocument()
    })
    expect(stagedRows()).toHaveLength(0)
  })

  it('should reject a zero or negative quantity', async () => {
    renderPage()

    await waitFor(() => {
      expect(itemSelect().querySelector('option[value="1"]')).toBeInTheDocument()
    })
    fireEvent.change(itemSelect(), { target: { value: '1' } })
    fireEvent.change(quantityInput(), { target: { value: '0' } })

    fireEvent.click(document.getElementById('expiration_date')!)
    fireEvent.click(await screen.findByText('common.today'))

    fireEvent.submit(addButton().closest('form')!)

    await waitFor(() => {
      expect(screen.getByText('receiving.quantityPositive')).toBeInTheDocument()
    })
    expect(stagedRows()).toHaveLength(0)
  })

  it('should clear auto-filled fields from a previous scan when the next scan has no parsed_data', async () => {
    const user = userEvent.setup()
    renderPage()

    // First scan: item A's barcode encodes an expiration date + quantity.
    await scan(user, 'BARCODE-A', mockItems[0], { expiration_date: '2027-06-15', quantity: 50 })

    // expiration_date is a DateField (a button, not a native input) -
    // toHaveValue() doesn't apply. It renders the picked date's year as
    // text regardless of locale digit-grouping/ordering, so assert on that.
    expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveTextContent('2027')
    expect(quantityInput()).toHaveValue(50)

    // Second scan: item B's barcode has no embedded expiration/quantity at
    // all. Previously, applyParsedData was only called for scans WITH
    // parsed_data, so item A's leftover expiration_date/quantity stayed in
    // the form and would have been submitted attached to item B's receipt.
    await scan(user, 'BARCODE-B', mockItems[1], null)

    // Cleared DateField falls back to its placeholder (the mocked t()
    // echoes the translation key verbatim).
    expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveTextContent('common.selectDate')
    expect(quantityInput()).toHaveValue(1)
  })

  it('should queue an offline receive with a path relative to the api baseURL, not prefixed with /api/v1', async () => {
    const user = userEvent.setup()
    seedList(stagedRow('a', { batch_number: 'LOT-A' }))
    vi.mocked(offline.isOnline).mockReturnValue(false)

    renderPage()
    await clickReceiveAll(user)

    // api's baseURL already includes /api/v1 (see lib/api.ts), so the
    // queued path must be relative - matching what receivingApi.receive
    // actually posts to - not doubled with an /api/v1 prefix.
    await waitFor(() => {
      expect(offline.addPendingOperation).toHaveBeenCalledWith(
        'receive',
        '/receiving/receive',
        'POST',
        expect.any(Object)
      )
    })
  })

  it('should submit only the shelf-life-eligible items and keep the others staged', async () => {
    const user = userEvent.setup()
    const eligible = stagedRow('eligible', { batch_number: 'LOT-OK' })
    // Well under the 180-day default, regardless of when the test runs.
    const tooSoon = stagedRow('too-soon', { item_id: '2', item_sku: 'INK-002', batch_number: 'LOT-SOON', expiration_date: isoDateInDays(30) })
    // An unreadable date can't be shown to be eligible - it must stay
    // staged too, not vanish because it was neither sent nor "flagged".
    const unreadable = stagedRow('unreadable', { batch_number: 'LOT-BAD', expiration_date: 'not-a-date' })
    seedList(eligible, tooSoon, unreadable)

    renderPage()
    await clickReceiveAll(user)

    await waitFor(() => {
      expect(api.receivingApi.receive).toHaveBeenCalledWith(
        expect.objectContaining({ item_id: '1', batch_number: 'LOT-OK' })
      )
    })
    expect(api.receivingApi.receive).toHaveBeenCalledTimes(1)
    expect(api.receivingApi.receiveMultiple).not.toHaveBeenCalled()

    await waitFor(() => expect(storedList()).toEqual([tooSoon, unreadable]))
    expect(stagedRows()).toHaveLength(2)
  })

  it('should refuse a barcode lookup while offline instead of failing with a generic network error', async () => {
    const user = userEvent.setup()
    vi.mocked(offline.isOnline).mockReturnValue(false)

    renderPage()

    const barcodeInput = screen.getByPlaceholderText('receiving.enterBarcode')
    await user.type(barcodeInput, 'BARCODE-X')
    fireEvent.submit(barcodeInput.closest('form')!)

    // No Toaster is mounted in this test tree, so the toast copy itself
    // isn't asserted here - the behavior that matters is that the lookup
    // never hits the network while offline.
    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).not.toHaveBeenCalled()
    })
  })

  describe('receive list', () => {
    const rowA = stagedRow('a', { batch_number: 'LOT-A' })
    const rowB = stagedRow('b', {
      item_id: '2',
      item_name: mockItems[1].name,
      item_sku: mockItems[1].sku,
      quantity: 5,
      batch_number: 'LOT-B',
    })

    it('adds a scanned box to the list and keeps it across a reload', async () => {
      const user = userEvent.setup()
      const { unmount } = renderPage()

      await scan(user, 'BOX-1', mockItems[0], {
        expiration_date: FAR_EXPIRY,
        quantity: 20,
        supplier_batch_number: 'LOT-A',
      })
      await user.click(addButton())

      await waitFor(() => expect(stagedRows()).toHaveLength(1))
      expect(within(rowFor('LOT-A')).getByText('INK-001')).toBeInTheDocument()
      // The form is cleared for the next box.
      expect(quantityInput()).toHaveValue(1)
      expect(batchInput()).toHaveValue('')

      unmount()
      renderPage()
      expect(stagedRows()).toHaveLength(1)
      expect(storedList()).toEqual([
        expect.objectContaining({ item_id: '1', quantity: 20, batch_number: 'LOT-A', expiration_date: FAR_EXPIRY }),
      ])
    })

    it('adds a scanned item even when it is missing from the loaded item catalog', async () => {
      // The dropdown only loads the first page of items; a barcode can
      // still resolve to one beyond it. Adding it used to silently no-op.
      const user = userEvent.setup()
      const beyondFirstPage = { id: '3', sku: 'INK-003', name: 'דיו צהוב', supplier: 'ספק ג', unit_of_measure: 'ליטר' }
      renderPage()

      await scan(user, 'BOX-3', beyondFirstPage)
      await user.click(addButton())

      await waitFor(() => expect(stagedRows()).toHaveLength(1))
      expect(within(stagedRows()[0]).getByText('INK-003')).toBeInTheDocument()
    })

    it('combines another box of a batch already in the list into that row', async () => {
      const user = userEvent.setup()
      seedList(rowA, rowB)
      renderPage()

      await scan(user, 'BOX-2', mockItems[0], { expiration_date: FAR_EXPIRY, quantity: 10, supplier_batch_number: 'LOT-A' })
      await user.click(addButton())

      await waitFor(() => expect(storedList()).toEqual([{ ...rowA, quantity: 20 }, rowB]))
      expect(stagedRows()).toHaveLength(2)
    })

    it.each([
      ['a different item', mockItems[1], FAR_EXPIRY],
      ['a different expiration date', mockItems[0], isoDateInDays(500)],
    ])('refuses to combine a box into a batch row with %s', async (_, item, expiration) => {
      // One batch is one item with one expiry - a mismatch is a data-entry
      // mistake, not another box of the same batch.
      const user = userEvent.setup()
      seedList(rowA)
      renderPage()

      await scan(user, 'BOX-2', item, { expiration_date: expiration, supplier_batch_number: 'LOT-A' })
      await user.click(addButton())

      expect(await screen.findByText('receiving.batchNumberConflict')).toBeInTheDocument()
      expect(storedList()).toEqual([rowA])
    })

    it('never combines boxes that have no batch number', async () => {
      const user = userEvent.setup()
      seedList(stagedRow('no-batch'))
      renderPage()

      await scan(user, 'BOX-2', mockItems[0])
      await user.click(addButton())

      await waitFor(() => expect(stagedRows()).toHaveLength(2))
    })

    it('combines an edited row into the row that already has its new batch number', async () => {
      // e.g. a mistyped lot number corrected to one that is already listed
      const user = userEvent.setup()
      seedList(rowA, stagedRow('typo', { batch_number: 'LOT-4', quantity: 4 }))
      renderPage()

      await startEditing(user, 'LOT-4')
      await user.clear(batchInput())
      await user.type(batchInput(), 'LOT-A')
      await user.click(updateButton())

      await waitFor(() => expect(storedList()).toEqual([{ ...rowA, quantity: 14 }]))
      expect(addButton()).toBeInTheDocument()
    })

    it('edits a row in place: it stays listed while being edited and is updated at the same position', async () => {
      const user = userEvent.setup()
      seedList(rowA, rowB)
      renderPage()

      await startEditing(user, 'LOT-A')

      expect(stagedRows()).toHaveLength(2)
      expect(rowFor('LOT-A')).toHaveAttribute('aria-current', 'true')
      expect(quantityInput()).toHaveValue(10)
      expect(batchInput()).toHaveValue('LOT-A')

      // Keeping its own batch number is not a "duplicate" of itself.
      await setQuantity(user, 12)
      await user.click(updateButton())

      await waitFor(() => expect(storedList()).toEqual([{ ...rowA, quantity: 12 }, rowB]))
      expect(stagedRows()).toHaveLength(2)
      expect(addButton()).toBeInTheDocument()
    })

    type LeaveEdit = (ctx: { user: UserEvent; unmount: () => void }) => Promise<unknown> | void

    it.each<[string, LeaveEdit]>([
      ['editing another row', ({ user }) => startEditing(user, 'LOT-B')],
      ['cancelling', ({ user }) => user.click(screen.getByRole('button', { name: 'common.cancel' }))],
      ['scanning another box', ({ user }) => scan(user, 'BOX-9', mockItems[1])],
      ['reloading the page', ({ unmount }) => { unmount(); renderPage() }],
    ])('keeps every row intact when an unsaved edit is abandoned by %s', async (_, leaveEdit) => {
      const user = userEvent.setup()
      seedList(rowA, rowB)
      const { unmount } = renderPage()

      await startEditing(user, 'LOT-A')
      await setQuantity(user, 99)
      await leaveEdit({ user, unmount })

      await waitFor(() => expect(stagedRows()).toHaveLength(2))
      expect(storedList()).toEqual([rowA, rowB])
    })

    it('leaves edit mode when the row being edited is removed', async () => {
      const user = userEvent.setup()
      seedList(rowA, rowB)
      renderPage()

      await startEditing(user, 'LOT-A')
      await user.click(within(rowFor('LOT-A')).getByTitle('common.delete'))

      expect(storedList()).toEqual([rowB])
      expect(addButton()).toBeInTheDocument()
      expect(quantityInput()).toHaveValue(1)
      expect(batchInput()).toHaveValue('')
    })

    it('saves an edit even when the item catalog failed to load', async () => {
      // Offline or a failed fetch leaves the dropdown empty; the staged
      // row already knows its item, so the edit must not depend on it.
      vi.mocked(api.itemsApi.list).mockRejectedValue(new Error('Network Error'))
      const user = userEvent.setup()
      seedList(rowA)
      renderPage()

      await startEditing(user, 'LOT-A')
      expect(itemSelect()).toHaveValue('1')
      await setQuantity(user, 12)
      await user.click(updateButton())

      await waitFor(() => expect(storedList()).toEqual([{ ...rowA, quantity: 12 }]))
    })

    it('receives every row in one request, including manufacturing dates, then clears the list', async () => {
      const user = userEvent.setup()
      const manufactured = isoDateInDays(-30)
      seedList({ ...rowA, manufacturing_date: manufactured }, rowB)
      renderPage()

      await clickReceiveAll(user)

      await waitFor(() => expect(stagedRows()).toHaveLength(0))
      expect(api.receivingApi.receiveMultiple).toHaveBeenCalledWith({
        items: [
          expect.objectContaining({ item_id: '1', quantity: 10, batch_number: 'LOT-A', manufacturing_date: manufactured }),
          expect.objectContaining({ item_id: '2', quantity: 5, batch_number: 'LOT-B', manufacturing_date: undefined }),
        ],
      })
      expect(localStorage.getItem('receiveList')).toBeNull()
    })

    it('keeps every row staged and shows the server error when receiving fails', async () => {
      const user = userEvent.setup()
      const toastError = vi.spyOn(toast, 'error')
      vi.mocked(api.receivingApi.receiveMultiple).mockRejectedValue({
        response: { data: { detail: 'מספר אצווה LOT-A כבר קיים' } },
      })
      seedList(rowA, rowB)
      renderPage()

      await clickReceiveAll(user)

      await waitFor(() => expect(toastError).toHaveBeenCalledWith('מספר אצווה LOT-A כבר קיים'))
      expect(storedList()).toEqual([rowA, rowB])
      expect(stagedRows()).toHaveLength(2)
    })

    it('refuses to receive while a row is being edited, so unsaved changes are not skipped', async () => {
      const user = userEvent.setup()
      const toastError = vi.spyOn(toast, 'error')
      seedList(rowA, rowB)
      renderPage()

      await startEditing(user, 'LOT-A')
      await clickReceiveAll(user)

      expect(toastError).toHaveBeenCalledWith('receiving.finishEditFirst')
      expect(api.receivingApi.receive).not.toHaveBeenCalled()
      expect(api.receivingApi.receiveMultiple).not.toHaveBeenCalled()
      expect(storedList()).toEqual([rowA, rowB])
    })

    it('locks the list and the form while a receive is in flight', async () => {
      // The request already carries every row's values - a box combined
      // into a row mid-request would leave with that row, never received.
      const user = userEvent.setup()
      let finishReceive!: (value: unknown) => void
      vi.mocked(api.receivingApi.receiveMultiple).mockReturnValue(
        new Promise((resolve) => { finishReceive = resolve })
      )
      seedList(rowA, rowB)
      renderPage()

      await clickReceiveAll(user)
      expect(addButton()).toBeDisabled()
      expect(within(rowFor('LOT-A')).getByTitle('receiving.editItem')).toBeDisabled()
      expect(within(rowFor('LOT-B')).getByTitle('common.delete')).toBeDisabled()

      finishReceive({})

      await waitFor(() => expect(stagedRows()).toHaveLength(0))
      expect(addButton()).toBeEnabled()
    })
  })
})
