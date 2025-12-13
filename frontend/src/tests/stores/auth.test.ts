import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/store/auth'
import axios from 'axios'

vi.mock('axios')

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    })
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should set user and token on successful login', async () => {
      const mockResponse = {
        data: {
          access_token: 'test-token',
          token_type: 'bearer',
        },
      }
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse)

      const store = useAuthStore.getState()
      await store.login('testuser', 'password123')

      expect(localStorage.getItem('access_token')).toBe('test-token')
      expect(store.token).toBe('test-token')
    })

    it('should throw error on failed login', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new Error('Invalid credentials'))

      const store = useAuthStore.getState()
      await expect(store.login('wrong', 'wrong')).rejects.toThrow()
    })
  })

  describe('logout', () => {
    it('should clear user, token, and localStorage', () => {
      // Setup initial state
      useAuthStore.setState({
        user: { id: '1', username: 'test', email: 'test@test.com', role: 'admin' },
        token: 'test-token',
        isAuthenticated: true,
      })
      localStorage.setItem('access_token', 'test-token')

      // Logout
      const store = useAuthStore.getState()
      store.logout()

      // Verify state is cleared
      expect(store.user).toBeNull()
      expect(store.token).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('fetchUser', () => {
    it('should fetch and set user data', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'manager',
        is_active: true,
      }

      vi.mocked(axios.get).mockResolvedValueOnce({ data: mockUser })
      localStorage.setItem('access_token', 'test-token')

      const store = useAuthStore.getState()
      await store.fetchUser()

      expect(store.user).toEqual(mockUser)
      expect(store.isAuthenticated).toBe(true)
    })

    it('should logout if token is invalid', async () => {
      vi.mocked(axios.get).mockRejectedValueOnce({ response: { status: 401 } })
      localStorage.setItem('access_token', 'invalid-token')

      const store = useAuthStore.getState()
      await store.fetchUser()

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })
})

