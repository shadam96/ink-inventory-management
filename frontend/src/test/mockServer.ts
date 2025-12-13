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
  phone: '123-456-7890',
  address: '123 Test St',
  contact_person: 'John Doe',
  is_active: true,
  is_vmi_customer: false,
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
export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE_URL}/api/v1/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      token_type: 'bearer',
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/auth/register`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockUser,
      username: body.username,
      email: body.email,
      full_name: body.full_name,
      role: body.role,
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/auth/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  // Items endpoints
  http.get(`${API_BASE_URL}/api/v1/inventory/items`, () => {
    return HttpResponse.json({
      items: [mockItem],
      total: 1,
      page: 1,
      page_size: 20,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/inventory/items`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockItem,
      ...body,
      id: '2',
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/inventory/items/:id`, async ({ params, request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockItem,
      ...body,
      id: params.id,
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/inventory/items/:id`, () => {
    return HttpResponse.json({ message: 'Item deleted' })
  }),

  // Customers endpoints
  http.get(`${API_BASE_URL}/api/v1/customers`, () => {
    return HttpResponse.json({
      items: [mockCustomer],
      total: 1,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/customers`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      ...mockCustomer,
      ...body,
      id: '2',
    })
  }),

  // Batches endpoints
  http.get(`${API_BASE_URL}/api/v1/batches`, () => {
    return HttpResponse.json({
      items: [mockBatch],
      total: 1,
    })
  }),

  // Alerts endpoints
  http.get(`${API_BASE_URL}/api/v1/alerts`, () => {
    return HttpResponse.json({
      items: [mockAlert],
      total: 1,
      unread_count: 1,
    })
  }),

  http.patch(`${API_BASE_URL}/api/v1/alerts/:id/read`, () => {
    return HttpResponse.json({
      ...mockAlert,
      is_read: true,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/alerts/mark-all-read`, () => {
    return HttpResponse.json({ message: 'All alerts marked as read' })
  }),

  // Dashboard endpoints
  http.get(`${API_BASE_URL}/api/v1/dashboard/summary`, () => {
    return HttpResponse.json({
      total_inventory_value: 10000,
      at_risk_percentage: 15.5,
      low_stock_items_count: 3,
      unread_alerts_count: 5,
      total_items: 50,
      total_batches: 100,
      active_batches: 80,
    })
  }),

  // Receiving endpoints
  http.post(`${API_BASE_URL}/api/v1/receiving/validate-barcode`, async ({ request }) => {
    const body = await request.json() as any
    return HttpResponse.json({
      valid: true,
      item: mockItem,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/receiving/receive`, () => {
    return HttpResponse.json(mockBatch)
  }),

  // Picking endpoints
  http.get(`${API_BASE_URL}/api/v1/picking/suggest-batches/:item_id`, () => {
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

