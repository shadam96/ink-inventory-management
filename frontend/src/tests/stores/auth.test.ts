import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/lib/api'

// The store calls the configured authApi wrapper (lib/api.ts), not raw
// axios - mock that directly instead of the axios module.
vi.mock('@/lib/api', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}))

describe('Auth Store', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should set the user and mark authenticated on successful login', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({
        access_token: 'test-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
      })
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'admin' as const,
        is_active: true,
      }
      vi.mocked(authApi.me).mockResolvedValueOnce(mockUser)

      await useAuthStore.getState().login('testuser', 'password123')

      expect(localStorage.getItem('access_token')).toBe('test-token')
      expect(localStorage.getItem('refresh_token')).toBe('test-refresh-token')
      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).toEqual(mockUser)
    })

    it('should throw and record an error on failed login', async () => {
      vi.mocked(authApi.login).mockRejectedValueOnce({
        response: { data: { detail: 'Invalid credentials' } },
      })

      await expect(
        useAuthStore.getState().login('wrong', 'wrong')
      ).rejects.toBeTruthy()

      expect(useAuthStore.getState().error).toBe('Invalid credentials')
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  describe('logout', () => {
    it('should clear user, auth state, and localStorage', () => {
      useAuthStore.setState({
        user: { id: '1', username: 'test', email: 'test@test.com', full_name: 'Test', role: 'admin', is_active: true },
        isAuthenticated: true,
      })
      localStorage.setItem('access_token', 'test-token')
      localStorage.setItem('refresh_token', 'test-refresh-token')

      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
    })

    it('should clear the unsubmitted receiving-queue draft (shared-device leak fix)', () => {
      // receiveList is a global (non-user-scoped) localStorage key; without
      // clearing it on logout, the next user on a shared device would see
      // and could submit this user's leftover draft receiving items.
      localStorage.setItem(
        'receiveList',
        JSON.stringify([{ id: '1', item_id: 'x', quantity: 5 }])
      )

      useAuthStore.getState().logout()

      expect(localStorage.getItem('receiveList')).toBeNull()
    })
  })

  describe('fetchUser', () => {
    it('should fetch and set user data', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'manager' as const,
        is_active: true,
      }
      vi.mocked(authApi.me).mockResolvedValueOnce(mockUser)

      await useAuthStore.getState().fetchUser()

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('should clear the user if the token is invalid', async () => {
      vi.mocked(authApi.me).mockRejectedValueOnce({ response: { status: 401 } })

      await useAuthStore.getState().fetchUser()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })
})
