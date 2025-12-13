import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from '@/store/ui'

describe('UI Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    useUIStore.setState({
      sidebarOpen: true,
    })
  })

  describe('toggleSidebar', () => {
    it('should toggle sidebar state', () => {
      const store = useUIStore.getState()
      
      expect(store.sidebarOpen).toBe(true)
      
      store.toggleSidebar()
      expect(useUIStore.getState().sidebarOpen).toBe(false)
      
      store.toggleSidebar()
      expect(useUIStore.getState().sidebarOpen).toBe(true)
    })
  })

  describe('setSidebarOpen', () => {
    it('should set sidebar to specific state', () => {
      const store = useUIStore.getState()
      
      store.setSidebarOpen(false)
      expect(useUIStore.getState().sidebarOpen).toBe(false)
      
      store.setSidebarOpen(true)
      expect(useUIStore.getState().sidebarOpen).toBe(true)
    })
  })
})

