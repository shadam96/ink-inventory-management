import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'

import { InventoryPage } from '@/pages/InventoryPage'
import * as api from '@/lib/api'
import { useAuthStore, type User } from '@/store/auth'

vi.mock('@/lib/api', () => ({
  inventoryApi: { list: vi.fn(), totalCost: vi.fn() },
  systemSettingsApi: { get: vi.fn() },
}))

vi.mock('@/components/layout/Header', () => ({
  Header: ({ title }: { title: string }) => <h1>{title}</h1>,
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'he' },
  }),
}))

const row = {
  item_id: 'item-1',
  sku: 'INK-001',
  name: 'Black Ink',
  batch_number: 'BATCH-001',
  quantity_available: 10,
  unit_of_measure: 'L',
  currency: 'ILS',
  supplier: 'Supplier A',
  expiration_date: '2027-06-01',
  receipt_dates: ['2026-09-01'],
  status: 'active',
}

function renderAs(role: User['role'], costPrice: number | null, totals: Record<string, number>) {
  useAuthStore.setState({
    user: {
      id: 'u-1',
      username: 'u',
      email: 'u@test.com',
      full_name: 'U',
      role,
      is_active: true,
    },
    isAuthenticated: true,
  })
  vi.mocked(api.inventoryApi.list).mockResolvedValue({
    items: [{ ...row, cost_price: costPrice }],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
  })
  vi.mocked(api.inventoryApi.totalCost).mockResolvedValue({
    totals,
    product_count: 1,
    total_quantity: 10,
  })
  return render(
    <BrowserRouter>
      <InventoryPage />
    </BrowserRouter>
  )
}

describe('InventoryPage cost visibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.systemSettingsApi.get).mockRejectedValue(new Error('offline'))
  })

  it('hides cost columns and the inventory value card from customers', async () => {
    renderAs('customer', null, {})

    await waitFor(() => expect(screen.getByText('BATCH-001')).toBeInTheDocument())

    expect(screen.queryByText('items.costPrice')).not.toBeInTheDocument()
    expect(screen.queryByText('inventory.totalCost')).not.toBeInTheDocument()
    expect(screen.queryByText('inventory.summaryValue')).not.toBeInTheDocument()
  })

  it('shows cost columns and the inventory value card to staff', async () => {
    renderAs('manager', 25, { ILS: 250 })

    await waitFor(() => expect(screen.getByText('BATCH-001')).toBeInTheDocument())

    expect(screen.getByText('items.costPrice')).toBeInTheDocument()
    expect(screen.getByText('inventory.totalCost')).toBeInTheDocument()
    expect(screen.getByText('inventory.summaryValue')).toBeInTheDocument()
  })
})
