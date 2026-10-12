import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

const API_BASE_URL = 'http://localhost:8000/api/v1'

// Mock data
export const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

export const mockItem = {
  id: '1',
  sku: 'INK-001',
  name: 'Test Ink',
  description: 'Test description',
  supplier: 'Test Supplier',
  unit_of_measure: 'Liter',
  cost_price: 100.5,
  reorder_point: 10,
  min_stock: 5,
  max_stock: 100,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockCustomer = {
  id: '1',
  name: 'Test Customer',
  email: 'customer@example.com',
  phone_primary: '123-456-7890',
  phone_secondary: null,
  address: '123 Test St',
  contact_person: 'John Doe',
  is_active: true,
  is_vmi_customer: false,
  machines: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockBatch = {
  id: '1',
  batch_number: 'BATCH-001',
  item_id: '1',
  item_sku: 'INK-001',
  item_name: 'Test Ink',
  quantity_received: 100,
  quantity_available: 80,
  expiration_date: '2025-06-01',
  receipt_date: '2024-01-01',
  status: 'active',
  created_at: '2024-01-01T00:00:00Z',
}

export const mockAlert = {
  id: '1',
  alert_type: 'expiration',
  severity: 'warning',
  title: 'Expiration Warning',
  message: 'Batch BATCH-001 expires in 30 days',
  related_entity_type: 'batch',
  related_entity_id: '1',
  is_read: false,
  created_at: '2024-01-01T00:00:00Z',
}

// API handlers
//
// API_BASE_URL already includes /api/v1 (it's the axios baseURL from
// lib/api.ts), and every real apiXxx.method() call passes only the path
// *below* that base (e.g. api.get('/items')) - so handler paths here must
// not repeat /api/v1 themselves, and must match those relative paths
// exactly (lib/api.ts is the source of truth for what each call hits).
export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE_URL}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      token_type: 'bearer',
    })
  }),

  http.get(`${API_BASE_URL}/auth/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  // Items endpoints
  http.get(`${API_BASE_URL}/items`, () => {
    return HttpResponse.json({
      items: [mockItem],
      total: 1,
      page: 1,
      page_size: 20,
    })
  }),

  http.post(`${API_BASE_URL}/items`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockItem,
      ...body,
      id: '2',
    })
  }),

  http.put(`${API_BASE_URL}/items/:id`, async ({ params, request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockItem,
      ...body,
      id: params.id,
    })
  }),

  http.delete(`${API_BASE_URL}/items/:id`, () => {
    return HttpResponse.json({ message: 'Item deleted' })
  }),

  // Customers endpoints
  http.get(`${API_BASE_URL}/customers`, () => {
    return HttpResponse.json({
      items: [mockCustomer],
      total: 1,
    })
  }),

  http.post(`${API_BASE_URL}/customers`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockCustomer,
      ...body,
      id: '2',
    })
  }),

  // Batches endpoints
  http.get(`${API_BASE_URL}/batches`, () => {
    return HttpResponse.json({
      items: [mockBatch],
      total: 1,
    })
  }),

  // Alerts endpoints
  http.get(`${API_BASE_URL}/alerts`, () => {
    return HttpResponse.json({
      items: [mockAlert],
      total: 1,
      unread_count: 1,
    })
  }),

  http.put(`${API_BASE_URL}/alerts/:id/read`, () => {
    return HttpResponse.json({
      ...mockAlert,
      is_read: true,
    })
  }),

  http.put(`${API_BASE_URL}/alerts/read-all`, () => {
    return HttpResponse.json({ message: 'All alerts marked as read' })
  }),

  // Dashboard endpoints
  http.get(`${API_BASE_URL}/dashboard/kpis`, () => {
    return HttpResponse.json({
      inventory_value_by_currency: { ILS: 10000 },
      at_risk_value_by_currency: { ILS: 1550 },
      at_risk_percentage: 15.5,
      low_stock_items: 3,
      critical_low_stock: 1,
      items_in_stock: 50,
      unread_alerts: 5,
      recent_receipts: 10,
      recent_dispatches: 4,
    })
  }),

  // Receiving endpoints
  http.post(`${API_BASE_URL}/receiving/validate-barcode`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      valid: true,
      item: mockItem,
    })
  }),

  http.post(`${API_BASE_URL}/receiving/receive`, () => {
    return HttpResponse.json(mockBatch)
  }),

  // Picking endpoints
  http.get(`${API_BASE_URL}/picking/suggest-batches/:item_id`, () => {
    return HttpResponse.json({
      suggested_batches: [
        {
          batch_id: '1',
          batch_number: 'BATCH-001',
          quantity_to_pick: 10,
          expiration_date: '2025-06-01',
          days_until_expiration: 180,
          warning_level: 'safe',
        },
      ],
      total_available: 80,
    })
  }),
]

// Setup mock server
export const server = setupServer(...handlers)

