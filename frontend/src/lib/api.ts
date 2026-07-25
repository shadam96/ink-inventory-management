import axios, { AxiosError, AxiosInstance } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Single-flight lock for token refresh: concurrent 401s (e.g. several
// requests firing around the same time) share one in-flight refresh call
// instead of each independently POSTing /auth/refresh. Without this, if
// the backend rotates/invalidates the refresh token on use, the first
// concurrent refresh succeeds but the second fails (using the
// already-consumed token) and logs the user out even though a valid
// refreshed session exists from the first call.
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const response = await axios.post(`${API_URL}/auth/refresh`, {
    refresh_token: refreshToken,
  })

  const { access_token, refresh_token: newRefreshToken } = response.data
  localStorage.setItem('access_token', access_token)
  localStorage.setItem('refresh_token', newRefreshToken)
  return access_token
}

// Response interceptor - handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config

    // Handle 401 - try token refresh
    if (error.response?.status === 401 && originalRequest) {
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
          })
        }
        const accessToken = await refreshPromise

        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return api(originalRequest)
      } catch {
        // Refresh failed - clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// API Response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  detail: string
}

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await api.post('/auth/login', { username, password })
    return response.data
  },
  
  refresh: async (refreshToken: string) => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },
  
  me: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },
}

// Items API
export const itemsApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; sort_by?: string; sort_order?: 'asc' | 'desc' }) => {
    const response = await api.get('/items', { params })
    return response.data as PaginatedResponse<Item>
  },
  
  get: async (id: string) => {
    const response = await api.get(`/items/${id}`)
    return response.data as Item
  },
  
  create: async (data: CreateItemData) => {
    const response = await api.post('/items', data)
    return response.data
  },
  
  update: async (id: string, data: Partial<CreateItemData>) => {
    const response = await api.put(`/items/${id}`, data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/items/${id}`)
  },
}

// Inventory View API
export const inventoryApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; sort_by?: string; sort_order?: 'asc' | 'desc' }) => {
    const response = await api.get('/inventory', { params })
    return response.data as PaginatedResponse<InventoryRow>
  },

  totalCost: async (params?: { search?: string }) => {
    const response = await api.get('/inventory/total-cost', { params })
    return response.data as InventoryTotalCost
  },
}

// Batches API
export const batchesApi = {
  list: async (params?: { page?: number; page_size?: number; item_id?: string; status_filter?: string; sort_by?: string; sort_order?: 'asc' | 'desc' }) => {
    const response = await api.get('/batches', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/batches/${id}`)
    return response.data
  },
}

// Receiving API
export const receivingApi = {
  receive: async (data: ReceiveItemData) => {
    const response = await api.post('/receiving/receive', data)
    return response.data
  },
  
  receiveMultiple: async (data: ReceiveMultipleData) => {
    const response = await api.post('/receiving/receive-multiple', data)
    return response.data
  },
  
  validateBarcode: async (barcode: string) => {
    const response = await api.post('/receiving/validate-barcode', { barcode })
    return response.data
  },
  
  generateBatchNumber: async () => {
    const response = await api.get('/receiving/generate-batch-number')
    return response.data
  },
}

// Picking API
export const pickingApi = {
  suggestBatches: async (itemId: string, quantity: number = 0) => {
    const response = await api.post('/picking/suggest-batches', { item_id: itemId, quantity_needed: quantity })
    return response.data
  },

  executePick: async (data: ExecutePickData) => {
    const response = await api.post('/picking/execute-pick', data)
    return response.data
  },

  dispatch: async (data: DispatchData) => {
    const response = await api.post('/picking/dispatch', data)
    return response.data as DispatchResponse
  },

  consume: async (data: { batch_id: string; quantity: number; notes?: string }) => {
    const response = await api.post('/picking/consume', data)
    return response.data
  },

  generateDispatchDocument: async (
    referenceNumber: string,
    documentType: 'pick_note' | 'delivery_note',
    action: 'print' | 'email',
  ) => {
    const response = await api.post(
      `/picking/dispatches/${encodeURIComponent(referenceNumber)}/document`,
      { document_type: documentType, action },
    )
    return response.data as DispatchDocumentResponse
  },
}

// Dashboard API
export const dashboardApi = {
  getKpis: async () => {
    const response = await api.get('/dashboard/kpis')
    return response.data as DashboardKPIs
  },
  
  getInventoryValue: async () => {
    const response = await api.get('/dashboard/inventory-value')
    return response.data
  },
  
  getInventoryDistribution: async () => {
    const response = await api.get('/dashboard/inventory-distribution')
    return response.data
  },
  
  getExpirationRisk: async () => {
    const response = await api.get('/dashboard/expiration-risk')
    return response.data
  },
  
  getLowStock: async () => {
    const response = await api.get('/dashboard/low-stock')
    return response.data
  },
  
  getRecentActivity: async (days = 7) => {
    const response = await api.get('/dashboard/recent-activity', { params: { days } })
    return response.data
  },
}

// System settings API (FX rates are read-only - the daily scheduler is the
// writer; min_shelf_life_days is editable via update()).
export const systemSettingsApi = {
  get: async () => {
    const response = await api.get('/settings/system')
    return response.data as SystemSettings
  },

  update: async (data: { min_shelf_life_days: number }) => {
    const response = await api.put('/settings/system', data)
    return response.data as SystemSettings
  },
}

// Alerts API
export const alertsApi = {
  getSummary: async () => {
    const response = await api.get('/alerts/summary')
    return response.data
  },
  
  list: async (params?: { unread_only?: boolean }) => {
    const response = await api.get('/alerts', { params })
    return response.data
  },
  
  markRead: async (id: string) => {
    const response = await api.put(`/alerts/${id}/read`)
    return response.data
  },
  
  markAllRead: async () => {
    const response = await api.put('/alerts/read-all')
    return response.data
  },
}

// Delivery Notes API
export const deliveryNotesApi = {
  list: async (params?: { page?: number; page_size?: number; customer_id?: string; sort_by?: string; sort_order?: 'asc' | 'desc' }) => {
    const response = await api.get('/delivery-notes', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/delivery-notes/${id}`)
    return response.data
  },
  
  create: async (data: CreateDeliveryNoteData) => {
    const response = await api.post('/delivery-notes', data)
    return response.data
  },
  
  downloadPdf: async (id: string) => {
    const response = await api.get(`/delivery-notes/${id}/pdf`, {
      responseType: 'blob',
    })
    return response.data
  },
}

// Customers API
export const customersApi = {
  list: async (params?: { page?: number; page_size?: number; search?: string; is_active?: boolean; is_vmi?: boolean }) => {
    const response = await api.get('/customers', { params })
    return response.data as PaginatedResponse<Customer>
  },

  get: async (id: string) => {
    const response = await api.get(`/customers/${id}`)
    return response.data as Customer
  },

  create: async (data: CreateCustomerData) => {
    const response = await api.post('/customers', data)
    return response.data
  },

  update: async (id: string, data: Partial<CreateCustomerData> & { is_active?: boolean }) => {
    const response = await api.put(`/customers/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    const response = await api.delete(`/customers/${id}`)
    return response.data
  },
}

// Types
export type ItemColor = 'cyan' | 'magenta' | 'yellow' | 'black' | 'white' | 'other'

export interface Item {
  id: string
  sku: string
  barcode?: string
  name: string
  description?: string
  supplier: string
  unit_of_measure: string
  color: ItemColor
  cost_price: number
  currency: 'ILS' | 'USD' | 'EUR' | 'TRY'
  reorder_point: number
  min_stock: number
  max_stock: number
  total_quantity_available?: number
  created_at: string
  updated_at: string
}

export interface CreateItemData {
  sku: string
  barcode?: string
  name: string
  description?: string
  supplier: string
  unit_of_measure: string
  color?: ItemColor
  cost_price: number
  currency: 'ILS' | 'USD' | 'EUR' | 'TRY'
  reorder_point?: number
  min_stock?: number
  max_stock?: number
}

export interface Batch {
  id: string
  item_id: string
  batch_number: string
  quantity_available: number
  quantity_received: number
  expiration_date: string
  receipt_date: string
  status: string
}

export interface ReceiveItemData {
  item_id: string
  quantity: number
  expiration_date: string
  manufacturing_date?: string
  batch_number?: string
  supplier_batch_number?: string
  location_id?: string
  notes?: string
}

export interface ReceiveMultipleData {
  items: ReceiveItemData[]
}

export interface ExecutePickData {
  batch_id: string
  quantity: number
  reference_number?: string
  notes?: string
}

export interface DispatchData {
  items: { batch_id: string; quantity: number }[]
  customer_id?: string
  reference_number?: string
  notes?: string
}

export interface DispatchResponse {
  success: boolean
  reference_number: string
  items_dispatched: number
  total_quantity: number
  movements: { movement_id: string; batch_id: string; quantity: number; quantity_remaining: number }[]
}

export interface DispatchDocumentResponse {
  success: boolean
  document_type: 'pick_note' | 'delivery_note'
  action: 'print' | 'email'
  reference_number: string
  message: string
  /** Only set for a successful action="print" - base64-encoded PDF bytes. */
  pdf_base64?: string | null
}

/** Cost values keyed by the per-item currency they were entered in. */
export type CurrencyTotals = Partial<Record<'ILS' | 'USD' | 'EUR' | 'TRY', number>>

export interface DashboardKPIs {
  inventory_value_by_currency: CurrencyTotals
  items_in_stock: number
  at_risk_value_by_currency: CurrencyTotals
  at_risk_percentage: number
  low_stock_items: number
  critical_low_stock: number
  unread_alerts: number
  recent_receipts: number
  recent_dispatches: number
}

export interface SystemSettings {
  /** Price of 1 USD in ILS. */
  usd_to_ils: number
  /** Price of 1 EUR in ILS. */
  eur_to_ils: number
  /** Price of 1 Turkish Lira in ILS. */
  try_to_ils: number
  /** Minimum days of shelf life required to receive a batch (hard block below this). */
  min_shelf_life_days: number
  /** ISO-8601 timestamp of the last Frankfurter refresh. */
  updated_at: string
}

export interface CreateDeliveryNoteData {
  customer_id: string
  items: { batch_id: string; quantity: number }[]
  is_consignment?: boolean
  notes?: string
}

export interface CustomerMachine {
  id: string
  customer_id: string
  machine_type: string
  installation_date?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CustomerMachineInput {
  machine_type: string
  installation_date?: string | null
  notes?: string | null
}

export interface Customer {
  id: string
  name: string
  email?: string
  phone_primary?: string
  phone_secondary?: string
  address?: string
  contact_person?: string
  is_active: boolean
  is_vmi_customer: boolean
  notes?: string
  machines: CustomerMachine[]
  created_at: string
  updated_at: string
}

export interface InventoryRow {
  item_id: string
  sku: string
  name: string
  description?: string
  batch_number: string
  quantity_available: number
  unit_of_measure: string
  cost_price: number
  currency: string
  supplier: string
  expiration_date: string
  receipt_dates: string[]
  status: string
}

export interface InventoryTotalCost {
  totals: Record<string, number>
  product_count: number
  total_quantity: number
}

export interface CreateCustomerData {
  name: string
  email?: string
  phone_primary?: string
  phone_secondary?: string
  address?: string
  contact_person?: string
  is_vmi_customer?: boolean
  notes?: string
  machines?: CustomerMachineInput[]
}

export default api

