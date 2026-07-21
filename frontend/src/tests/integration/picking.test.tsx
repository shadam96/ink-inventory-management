import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

import { PickingPage } from '@/pages/PickingPage'
import * as api from '@/lib/api'
import { useAuthStore } from '@/store/auth'

vi.mock('@/lib/api', () => ({
  itemsApi: { list: vi.fn() },
  customersApi: { list: vi.fn() },
  pickingApi: { suggestBatches: vi.fn(), consume: vi.fn() },
  receivingApi: { validateBarcode: vi.fn() },
}))

vi.mock('@/lib/offline', () => ({
  isOnline: () => true,
  addPendingOperation: vi.fn(),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'he' },
  }),
}))

const mockItem = {
  id: 'item-1',
  sku: 'INK-001',
  name: 'Black Ink',
  supplier: 'Supplier A',
  unit_of_measure: 'L',
  cost_price: 100,
  min_stock: 5,
  total_quantity_available: 100,
}

function renderPickingPage() {
  return render(
    <BrowserRouter>
      <PickingPage />
    </BrowserRouter>
  )
}

describe('PickingPage (admin view)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: 'admin-1',
        username: 'admin',
        email: 'admin@test.com',
        full_name: 'Admin',
        role: 'admin',
        is_active: true,
      },
      isAuthenticated: true,
    })

    vi.mocked(api.itemsApi.list).mockResolvedValue({
      items: [mockItem],
      total: 1,
      page: 1,
      page_size: 100,
    })
    vi.mocked(api.customersApi.list).mockResolvedValue({ items: [] })
  })

  it('shows a toast when fetching items fails instead of silently leaving an empty list', async () => {
    vi.mocked(api.itemsApi.list).mockRejectedValue(new Error('network error'))
    const { toast } = await import('sonner')
    const toastErrorSpy = vi.spyOn(toast, 'error')

    renderPickingPage()

    await waitFor(() => {
      expect(toastErrorSpy).toHaveBeenCalledWith('picking.fetchItemsError')
    })
  })

  it('applies only the response for the most recently requested quantity, ignoring a slower stale response', async () => {
    const user = userEvent.setup()

    const stockBatch = {
      batch_id: 'batch-1',
      batch_number: 'BATCH-001',
      suggested_quantity: 150,
      quantity_available: 200,
      expiration_date: '2027-01-01',
      days_until_expiration: 300,
      warning_level: 'safe',
    }

    // Response for quantity=1 resolves AFTER the response for quantity=150
    // (out-of-order arrival) - the stale one must not win.
    vi.mocked(api.pickingApi.suggestBatches).mockImplementation(
      async (_itemId: string, quantity: number) => {
        if (quantity === 1) {
          await new Promise((resolve) => setTimeout(resolve, 50))
          return { suggestions: [], total_available: 1, can_fulfill: false }
        }
        return { suggestions: [stockBatch], total_available: 150, can_fulfill: true }
      }
    )

    renderPickingPage()

    await waitFor(() => {
      expect(document.getElementById('item_id')).toBeInTheDocument()
      expect(api.itemsApi.list).toHaveBeenCalled()
    })

    const itemSelect = document.getElementById('item_id') as HTMLSelectElement
    await waitFor(() => {
      expect(itemSelect.querySelector('option[value="item-1"]')).toBeInTheDocument()
    })
    await user.selectOptions(itemSelect, 'item-1')

    const quantityInput = document.getElementById('quantity') as HTMLInputElement
    await user.clear(quantityInput)
    await user.type(quantityInput, '1')
    // Give the (slow) request for "1" a chance to be issued before typing more.
    await new Promise((resolve) => setTimeout(resolve, 5))
    await user.clear(quantityInput)
    await user.type(quantityInput, '150')

    await waitFor(() => {
      expect(api.pickingApi.suggestBatches).toHaveBeenCalledWith('item-1', 150)
    })

    // Wait past the slow "1" response's resolution time to make sure it
    // doesn't clobber state after arriving late.
    await new Promise((resolve) => setTimeout(resolve, 100))

    // The "150" response has can_fulfill=true; the stale "1" response has
    // can_fulfill=false. If the stale response won, this would show
    // "picking.insufficientStock" instead.
    expect(screen.getByText('picking.canFulfill')).toBeInTheDocument()
    expect(screen.queryByText('picking.insufficientStock')).not.toBeInTheDocument()
  })
})
