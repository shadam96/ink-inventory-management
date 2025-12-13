import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/badge'

describe('Badge Component', () => {
  it('should render badge with text', () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('should apply variant classes', () => {
    const { rerender } = render(<Badge variant="safe">Safe</Badge>)
    let badge = screen.getByText('Safe')
    expect(badge).toHaveClass('bg-status-safe')
    
    rerender(<Badge variant="warning">Warning</Badge>)
    badge = screen.getByText('Warning')
    expect(badge).toHaveClass('bg-status-warning')
    
    rerender(<Badge variant="critical">Critical</Badge>)
    badge = screen.getByText('Critical')
    expect(badge).toHaveClass('bg-status-critical')
    
    rerender(<Badge variant="expired">Expired</Badge>)
    badge = screen.getByText('Expired')
    expect(badge).toHaveClass('bg-status-expired')
  })

  it('should render default variant', () => {
    render(<Badge>Default</Badge>)
    expect(screen.getByText('Default')).toHaveClass('bg-primary')
  })
})

