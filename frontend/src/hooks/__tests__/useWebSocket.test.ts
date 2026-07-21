import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import { useAuthStore } from '@/store/auth'

vi.mock('@/lib/websocket', () => ({
  websocketService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(() => () => {}),
    send: vi.fn(),
    isConnected: vi.fn(() => false),
  },
}))

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    useAuthStore.setState({ isAuthenticated: false, user: null })
  })

  it('connects when authenticated and disconnects when logged out', async () => {
    const { websocketService } = await import('@/lib/websocket')
    const { useWebSocket } = await import('../useWebSocket')

    window.localStorage.setItem('access_token', 'token-a')
    useAuthStore.setState({ isAuthenticated: true })

    const { rerender } = renderHook(() => useWebSocket())
    expect(websocketService.connect).toHaveBeenCalledWith('token-a')
    expect(websocketService.disconnect).not.toHaveBeenCalled()

    // Regression test: logging out must disconnect the singleton socket
    // so the next user on this tab/device doesn't reuse the previous
    // user's authenticated connection.
    act(() => {
      useAuthStore.setState({ isAuthenticated: false, user: null })
    })
    rerender()

    expect(websocketService.disconnect).toHaveBeenCalledTimes(1)
  })
})
