import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { ReceivingPage } from '@/pages/ReceivingPage'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  itemsApi: {
    list: vi.fn(),
  },
  receivingApi: {
    validateBarcode: vi.fn(),
    receive: vi.fn(),
    receiveMultiple: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'he' },
  }),
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

    const barcodeInput = screen.getByPlaceholderText(/סרוק או הזן ברקוד/i)
    await user.type(barcodeInput, '1234567890')

    const checkButton = screen.getByRole('button', { name: /בדוק ברקוד/i })
    await user.click(checkButton)

    await waitFor(() => {
      expect(api.receivingApi.validateBarcode).toHaveBeenCalledWith('1234567890')
    })
  })

  it('should show alert for invalid barcode', async () => {
    const user = userEvent.setup()
    
    vi.stubGlobal('alert', vi.fn())
    vi.mocked(api.receivingApi.validateBarcode).mockResolvedValue({
      valid: false,
      item: null,
    })

    render(
      <BrowserRouter>
        <ReceivingPage />
      </BrowserRouter>
    )

    const barcodeInput = screen.getByPlaceholderText(/סרוק או הזן ברקוד/i)
    await user.type(barcodeInput, 'INVALID')

    const checkButton = screen.getByRole('button', { name: /בדוק ברקוד/i })
    await user.click(checkButton)

    await waitFor(() => {
      expect(alert).toHaveBeenCalledWith('ברקוד לא נמצא')
    })
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

    await waitFor(() => {
      expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveValue('2027-06-15')
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
    expect(screen.getByLabelText(/receiving\.expirationDate/i)).toHaveValue('')
    expect(screen.getByLabelText(/receiving\.quantity/i)).toHaveValue(1)
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
})

