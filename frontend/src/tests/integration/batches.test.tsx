import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { BatchesPage } from '@/pages/BatchesPage'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  batchesApi: { list: vi.fn() },
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

const batch = {
  id: 'b-1',
  batch_number: 'BATCH-001',
  item_id: 'item-1',
  item_sku: 'INK-001',
  item_name: 'Black Ink',
  quantity_available: 10,
  quantity_received: 20,
  expiration_date: '2027-06-01',
  receipt_date: '2026-09-01',
  status: 'active',
}

async function openSortSheet() {
  const user = userEvent.setup()
  render(<BatchesPage />)
  await waitFor(() => expect(api.batchesApi.list).toHaveBeenCalledTimes(1))
  await user.click(screen.getByRole('button', { name: 'batches.sortBy' }))
  const sheet = await screen.findByRole('dialog', { name: 'batches.sortBy' })
  return { user, sheet }
}

function directionButton(sheet: HTMLElement, field: string, direction: string) {
  const group = within(sheet).getByRole('group', { name: field })
  return within(group).getByRole('button', { name: direction })
}

describe('BatchesPage mobile sorting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.batchesApi.list).mockResolvedValue({
      items: [batch],
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
    })
  })

  it('sorts by the field and direction picked in the sort sheet, then closes it', async () => {
    const { user, sheet } = await openSortSheet()

    await user.click(directionButton(sheet, 'batches.quantity', 'batches.sortHighest'))

    await waitFor(() =>
      expect(api.batchesApi.list).toHaveBeenLastCalledWith({
        status_filter: 'active',
        sort_by: 'quantity_available',
        sort_order: 'desc',
      })
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('shows the default FEFO order as soonest expiry first', async () => {
    const { sheet } = await openSortSheet()

    const pressed = within(sheet).getAllByRole('button', { pressed: true })
    expect(pressed).toEqual([directionButton(sheet, 'batches.expirationDate', 'batches.sortEarliest')])
  })

  it('shows a sort chosen from the table header as the current sort', async () => {
    const user = userEvent.setup()
    render(<BatchesPage />)
    await waitFor(() => expect(api.batchesApi.list).toHaveBeenCalledTimes(1))

    await user.click(screen.getByRole('columnheader', { name: 'batches.receiptDate' }))
    await user.click(screen.getByRole('columnheader', { name: 'batches.receiptDate' }))
    await user.click(screen.getByRole('button', { name: 'batches.sortBy' }))

    const sheet = await screen.findByRole('dialog', { name: 'batches.sortBy' })
    expect(directionButton(sheet, 'batches.receiptDate', 'batches.sortLatest')).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  })
})
