import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ItemDialog } from '../ItemDialog'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

describe('ItemDialog', () => {
  const mockOnSubmit = vi.fn()
  const mockOnOpenChange = vi.fn()

  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    onSubmit: mockOnSubmit,
  }

  it('should render create mode', () => {
    render(<ItemDialog {...defaultProps} />)
    expect(screen.getByText('items.add')).toBeInTheDocument()
  })

  it('should render edit mode with item data', () => {
    const item = {
      id: '1',
      sku: 'INK-001',
      name: 'Test Ink',
      supplier: 'Test Supplier',
      unit_of_measure: 'Liter',
      cost_price: 100,
      reorder_point: 10,
      min_stock: 5,
      max_stock: 100,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    render(<ItemDialog {...defaultProps} item={item} />)
    expect(screen.getByText('items.edit')).toBeInTheDocument()
    expect(screen.getByDisplayValue('INK-001')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test Ink')).toBeInTheDocument()
  })

  it('should validate required fields', async () => {
    render(<ItemDialog {...defaultProps} />)
    const user = userEvent.setup()
    
    const submitButton = screen.getByText('common.save')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/מק"ט נדרש/)).toBeInTheDocument()
    })
  })

  it('should call onSubmit with form data', async () => {
    mockOnSubmit.mockResolvedValue(undefined)
    render(<ItemDialog {...defaultProps} />)
    const user = userEvent.setup()

    // Fill form
    await user.type(screen.getByLabelText(/items.sku/), 'INK-002')
    await user.type(screen.getByLabelText(/items.name/), 'New Ink')
    await user.type(screen.getByLabelText(/items.supplier/), 'Supplier')
    await user.type(screen.getByLabelText(/items.unit/), 'Liter')
    await user.type(screen.getByLabelText(/items.costPrice/), '150')

    const submitButton = screen.getByText('common.save')
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          sku: 'INK-002',
          name: 'New Ink',
          supplier: 'Supplier',
        })
      )
    })
  })

  it('should disable SKU field in edit mode', () => {
    const item = {
      id: '1',
      sku: 'INK-001',
      name: 'Test Ink',
      supplier: 'Test Supplier',
      unit_of_measure: 'Liter',
      cost_price: 100,
      reorder_point: 10,
      min_stock: 5,
      max_stock: 100,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    render(<ItemDialog {...defaultProps} item={item} />)
    const skuInput = screen.getByDisplayValue('INK-001')
    expect(skuInput).toBeDisabled()
  })
})

