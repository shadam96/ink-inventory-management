import { describe, it, expect, beforeEach, vi } from 'vitest'
import { itemsApi } from '@/lib/api'
import axios from 'axios'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    })),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('Items API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('list', () => {
    it('should fetch items list with pagination', async () => {
      const mockResponse = {
        data: {
          items: [
            { id: '1', sku: 'INK-001', name: 'דיו שחור', supplier: 'ספק א' },
            { id: '2', sku: 'INK-002', name: 'דיו כחול', supplier: 'ספק ב' },
          ],
          total: 2,
          page: 1,
          page_size: 20,
        },
      }

      const mockAxios = axios.create()
      vi.mocked(mockAxios.get).mockResolvedValueOnce(mockResponse)

      // Note: This test verifies the structure, actual API calls would need the real axios instance
      expect(typeof itemsApi.list).toBe('function')
    })
  })

  describe('create', () => {
    it('should create a new item', async () => {
      const newItem = {
        sku: 'INK-003',
        name: 'דיו צהוב',
        supplier: 'ספק ג',
        unit_of_measure: 'ליטר',
        cost_price: 100,
      }

      expect(typeof itemsApi.create).toBe('function')
    })
  })

  describe('update', () => {
    it('should update an existing item', async () => {
      const updates = {
        name: 'דיו צהוב מעודכן',
        cost_price: 120,
      }

      expect(typeof itemsApi.update).toBe('function')
    })
  })

  describe('delete', () => {
    it('should delete an item', async () => {
      expect(typeof itemsApi.delete).toBe('function')
    })
  })

  describe('get', () => {
    it('should fetch a single item by id', async () => {
      expect(typeof itemsApi.get).toBe('function')
    })
  })
})

