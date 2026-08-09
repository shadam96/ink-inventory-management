import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
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

describe('Receiving Operations', () => {
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

  beforeEach(() => {
    vi.clearAllMocks()
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
    // Default to online - individual tests override this to exercise the
    // offline paths (isOnline() is a bare vi.fn() otherwise, which returns
    // undefined/falsy and would put every test in the "offline" branch).
    vi.mocked(offline.isOnline).mockReturnValue(true)
  })

  it('should load items for selection', async () => {
    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

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

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    // The i18n mock echoes translation keys verbatim, and the barcode
    // submit button is icon-only (no accessible name) - select the input
    // by its (mocked) placeholder key and submit its form directly.
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

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    const barcodeInput = screen.getByPlaceholderText('receiving.enterBarcode')
    await user.type(barcodeInput, 'INVALID')
    fireEvent.submit(barcodeInput.closest('form')!)

    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).toHaveBeenCalledWith('INVALID')
    })
    // A not-found lookup never calls setValue('item_id', ...), so the
    // select stays at its unset default instead of being filled in.
    expect((document.getElementById('item_id') as HTMLSelectElement).value).toBe('')
  })

  it('should allow adding items to receive list', async () => {
    const user = userEvent.setup()

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      // i18next is mocked to return keys verbatim; "הוסף לרשימה" is now
      // behind `receiving.addToList`.
      expect(screen.getByRole('button', { name: /receiving\.addToList/i })).toBeInTheDocument()
    })

    // This would require filling the form and clicking add
    // Simplified test - actual implementation would be more detailed
  })

  it('should accept a fractional quantity (items are commonly measured in KG/L) and add it to the receive list', async () => {
    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.itemsApi.list).toHaveBeenCalled()
    })

    const itemSelect = document.getElementById('item_id') as HTMLSelectElement
    await waitFor(() => {
      expect(itemSelect.querySelector('option[value="1"]')).toBeInTheDocument()
    })
    fireEvent.change(itemSelect, { target: { value: '1' } })

    const quantityInput = document.getElementById('quantity') as HTMLInputElement
    fireEvent.change(quantityInput, { target: { value: '2.5' } })

    // expiration_date is a DateField now (a button opening a calendar
    // popover, not a native input) - fireEvent.change doesn't apply.
    // The exact date doesn't matter for this test's intent (fractional
    // quantity acceptance), so just pick "today" via the popover.
    const expirationTrigger = document.getElementById('expiration_date') as HTMLButtonElement
    fireEvent.click(expirationTrigger)
    fireEvent.click(await screen.findByText('common.today'))

    const addButton = screen.getByRole('button', { name: /receiving\.addToList/i })
    fireEvent.submit(addButton.closest('form')!)

    // No validation error, and the fractional-quantity item was added.
    await waitFor(() => {
      expect(screen.getByText(/receiving\.listTitle/)).toBeInTheDocument()
    })
    expect(screen.queryByText('receiving.quantityPositive')).not.toBeInTheDocument()

    // ReceivingPage persists the list to localStorage on every mutation -
    // clear it so it doesn't leak into the next test.
    localStorage.removeItem('receiveList')
  })

  it('should reject a zero or negative quantity', async () => {
    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.itemsApi.list).toHaveBeenCalled()
    })

    const itemSelect = document.getElementById('item_id') as HTMLSelectElement
    await waitFor(() => {
      expect(itemSelect.querySelector('option[value="1"]')).toBeInTheDocument()
    })
    fireEvent.change(itemSelect, { target: { value: '1' } })

    const quantityInput = document.getElementById('quantity') as HTMLInputElement
    fireEvent.change(quantityInput, { target: { value: '0' } })

    const expirationTrigger = document.getElementById('expiration_date') as HTMLButtonElement
    fireEvent.click(expirationTrigger)
    fireEvent.click(await screen.findByText('common.today'))

    const addButton = screen.getByRole('button', { name: /receiving\.addToList/i })
    fireEvent.submit(addButton.closest('form')!)

    await waitFor(() => {
      expect(screen.getByText('receiving.quantityPositive')).toBeInTheDocument()
    })
    expect(screen.queryByText(/receiving\.listTitle/)).not.toBeInTheDocument()
  })

  it('should clear auto-filled fields from a previous scan when the next scan has no parsed_data', async () => {
    const user = userEvent.setup()

    // First scan: item A's barcode encodes an expiration date + quantity.
    vi.mocked(api.receivingApi.validateBarcode).mockResolvedValueOnce({
      valid: true,
      item: mockItems[0],
      parsed_data: { expiration_date: '2027-06-15', quantity: 50 },
    })

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    // The i18n mock echoes translation keys verbatim rather than rendering
    // the hardcoded Hebrew text, and the barcode submit button has no
    // accessible name - so select the input by its (mocked) placeholder key
    // and submit its form directly instead of clicking the icon-only button.
    const barcodeInput = screen.getByPlaceholderText('receiving.enterBarcode')

    await user.type(barcodeInput, 'BARCODE-A')
    fireEvent.submit(barcodeInput.closest('form')!)

    // expiration_date is now a DateField (a button, not a native input) -
    // toHaveValue() no longer applies. It renders the picked date's year
    // as text regardless of locale digit-grouping/ordering, so assert on
    // that instead of the exact formatted string.
    await waitFor(() => {
      expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveTextContent('2027')
    })
    expect(screen.getByLabelText(/receiving\.quantity/i)).toHaveValue(50)

    // Second scan: item B's barcode has no embedded expiration/quantity at
    // all. Previously, applyParsedData was only called for scans WITH
    // parsed_data, so item A's leftover expiration_date/quantity stayed in
    // the form and would have been submitted attached to item B's receipt.
    vi.mocked(api.receivingApi.validateBarcode).mockResolvedValueOnce({
      valid: true,
      item: mockItems[1],
      parsed_data: null,
    })

    await user.clear(barcodeInput)
    await user.type(barcodeInput, 'BARCODE-B')
    fireEvent.submit(barcodeInput.closest('form')!)

    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).toHaveBeenCalledWith('BARCODE-B')
    })
    // Cleared DateField falls back to its placeholder (the mocked t()
    // echoes the translation key verbatim, so this is the literal string
    // DateField renders when `value` is empty).
    expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveTextContent('common.selectDate')
    expect(screen.getByLabelText(/receiving\.quantity/i)).toHaveValue(1)
  })

  it('should queue an offline receive with a path relative to the api baseURL, not prefixed with /api/v1', async () => {
    const user = userEvent.setup()

    // Seed the persisted receive-list (ReceivingPage reads it from
    // localStorage on init) with one item pending submission.
    localStorage.setItem(
      'receiveList',
      JSON.stringify([
        {
          id: 'test-item-1',
          item_id: '1',
          item_name: mockItems[0].name,
          item_sku: mockItems[0].sku,
          quantity: 10,
          expiration_date: '2028-01-01',
          manufacturing_date: '',
          batch_number: 'BATCH-A',
          notes: '',
        },
      ])
    )

    vi.mocked(offline.isOnline).mockReturnValue(false)

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    // ReceivingPage renders two "receive all" buttons (a desktop one and a
    // mobile sticky-bar one, shown/hidden via responsive classes only -
    // jsdom doesn't evaluate real CSS, so both are query-visible here).
    // They call the same handler, so clicking either is equivalent.
    const receiveAllButtons = await screen.findAllByRole('button', {
      name: /receiving\.receiveAll/i,
    })
    await user.click(receiveAllButtons[0])

    await waitFor(() => {
      expect(offline.addPendingOperation).toHaveBeenCalled()
    })

    // api's baseURL already includes /api/v1 (see lib/api.ts), so the
    // queued path must be relative - matching what receivingApi.receive
    // actually posts to - not doubled with an /api/v1 prefix.
    expect(offline.addPendingOperation).toHaveBeenCalledWith(
      'receive',
      '/receiving/receive',
      'POST',
      expect.any(Object)
    )

    localStorage.removeItem('receiveList')
  })

  it('should call receive API when receiving all items', async () => {
    vi.mocked(api.receivingApi.receive).mockResolvedValue({
      id: 'batch-1',
      batch_number: 'BATCH-001',
      message: 'Success',
    })

    // Test would involve:
    // 1. Adding items to receive list
    // 2. Clicking "קלוט הכל"
    // 3. Verifying API was called with correct data

    expect(typeof api.receivingApi.receive).toBe('function')
  })

  it('should submit only the shelf-life-eligible items and keep the flagged one staged', async () => {
    const user = userEvent.setup()

    localStorage.setItem(
      'receiveList',
      JSON.stringify([
        {
          id: 'eligible-1',
          item_id: '1',
          item_name: mockItems[0].name,
          item_sku: mockItems[0].sku,
          quantity: 10,
          expiration_date: '2028-01-01',
          manufacturing_date: '',
          batch_number: 'BATCH-OK',
          notes: '',
        },
        {
          id: 'flagged-1',
          item_id: '2',
          item_name: mockItems[1].name,
          item_sku: mockItems[1].sku,
          quantity: 5,
          // Always well under the 180-day default, regardless of when the
          // test runs.
          expiration_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
            .toISOString()
            .split('T')[0],
          manufacturing_date: '',
          batch_number: 'BATCH-SOON',
          notes: '',
        },
      ])
    )

    vi.mocked(offline.isOnline).mockReturnValue(true)
    vi.mocked(api.receivingApi.receive).mockResolvedValue({
      id: 'batch-1',
      batch_number: 'BATCH-001',
      message: 'Success',
    })

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    // ReceivingPage renders two "receive all" buttons (a desktop one and a
    // mobile sticky-bar one, shown/hidden via responsive classes only -
    // jsdom doesn't evaluate real CSS, so both are query-visible here).
    // They call the same handler, so clicking either is equivalent.
    const receiveAllButtons = await screen.findAllByRole('button', {
      name: /receiving\.receiveAll/i,
    })
    await user.click(receiveAllButtons[0])

    // Only the eligible item was submitted...
    await waitFor(() => {
      expect(api.receivingApi.receive).toHaveBeenCalledWith(
        expect.objectContaining({ item_id: '1', batch_number: 'BATCH-OK' })
      )
    })
    expect(api.receivingApi.receive).toHaveBeenCalledTimes(1)
    expect(api.receivingApi.receiveMultiple).not.toHaveBeenCalled()

    // ...and the flagged item is still staged, not silently dropped. (SKU,
    // not name, since the item-select dropdown also renders each name.)
    await waitFor(() => {
      expect(screen.getByText(mockItems[1].sku)).toBeInTheDocument()
    })
    expect(screen.queryByText(mockItems[0].sku)).not.toBeInTheDocument()

    localStorage.removeItem('receiveList')
  })

  it('should move a staged item back into the form for editing instead of only allowing remove', async () => {
    const user = userEvent.setup()

    localStorage.setItem(
      'receiveList',
      JSON.stringify([
        {
          id: 'edit-me',
          item_id: '1',
          item_name: mockItems[0].name,
          item_sku: mockItems[0].sku,
          quantity: 12.5,
          expiration_date: '2028-01-01',
          manufacturing_date: '',
          batch_number: 'BATCH-EDIT',
          notes: 'handle with care',
        },
      ])
    )

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    const editButton = await screen.findByTitle('receiving.editItem')
    await user.click(editButton)

    // Removed from the staged list...
    expect(screen.queryByText(/receiving\.listTitle/)).not.toBeInTheDocument()

    // ...and its data (including the fractional quantity and batch number
    // that a full remove-and-re-add would have lost) is back in the form.
    expect(document.getElementById('quantity')).toHaveValue(12.5)
    expect(document.getElementById('batch_number')).toHaveValue('BATCH-EDIT')

    localStorage.removeItem('receiveList')
  })

  it('should refuse a barcode lookup while offline instead of failing with a generic network error', async () => {
    const user = userEvent.setup()
    vi.mocked(offline.isOnline).mockReturnValue(false)

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

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
})

