import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

import { StaffRoute } from '../App'
import { useAuthStore } from '@/store/auth'

/**
 * Regression test: StaffRoute checked `user?.role`, but the persisted auth
 * store only rehydrates `isAuthenticated` (not `user`) - on a page reload
 * a customer-role user could briefly render/fetch staff-only routes
 * before the async fetchUser() resolved and redirected. StaffRoute must
 * render nothing while user is still null but we believe we're
 * authenticated, instead of assuming "not a customer".
 */

function renderStaffRoute() {
  return render(
    <MemoryRouter initialEntries={['/items']}>
      <Routes>
        <Route
          path="/items"
          element={
            <StaffRoute>
              <div>staff-only content</div>
            </StaffRoute>
          }
        />
        <Route path="/picking" element={<div>picking page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('StaffRoute', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ user: null, isAuthenticated: false })
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders nothing while authenticated but user has not loaded yet', () => {
    localStorage.setItem('access_token', 'token-a')
    useAuthStore.setState({ isAuthenticated: true, user: null })

    const { container } = renderStaffRoute()

    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByText('staff-only content')).not.toBeInTheDocument()
  })

  it('renders staff-only content once the user loads and is not a customer', () => {
    localStorage.setItem('access_token', 'token-a')
    useAuthStore.setState({
      isAuthenticated: true,
      user: {
        id: '1',
        username: 'admin',
        email: 'admin@test.com',
        full_name: 'Admin',
        role: 'admin',
        is_active: true,
      },
    })

    renderStaffRoute()

    expect(screen.getByText('staff-only content')).toBeInTheDocument()
  })

  it('redirects a customer-role user away from staff-only routes', () => {
    localStorage.setItem('access_token', 'token-a')
    useAuthStore.setState({
      isAuthenticated: true,
      user: {
        id: '2',
        username: 'cust',
        email: 'cust@test.com',
        full_name: 'Customer',
        role: 'customer',
        is_active: true,
      },
    })

    renderStaffRoute()

    expect(screen.getByText('picking page')).toBeInTheDocument()
    expect(screen.queryByText('staff-only content')).not.toBeInTheDocument()
  })
})
