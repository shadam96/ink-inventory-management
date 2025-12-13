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

// Response interceptor - handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config
    
    // Handle 401 - try token refresh
    if (error.response?.status === 401 && originalRequest) {
      const refreshToken = localStorage.getItem('refresh_token')
      
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          
          const { access_token, refresh_token: newRefreshToken } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', newRefreshToken)
          
          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
          // Refresh failed - clear tokens and redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
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
  list: async (params?: { page?: number; page_size?: number; search?: string }) => {
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

// Batches API
export const batchesApi = {
  list: async (params?: { item_id?: string; status?: string }) => {
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
  suggestBatches: async (itemId: string, quantity: number) => {
    const response = await api.post('/picking/suggest-batches', { item_id: itemId, quantity })
    return response.data
  },
  
  executePick: async (data: ExecutePickData) => {
    const response = await api.post('/picking/execute-pick', data)
    return response.data
  },
  
  dispatch: async (data: DispatchData) => {
    const response = await api.post('/picking/dispatch', data)
    return response.data
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
  list: async (params?: { page?: number; customer_id?: string }) => {
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
  list: async () => {
    const response = await api.get('/customers')
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/customers/${id}`)
    return response.data
  },
  
  create: async (data: CreateCustomerData) => {
    const response = await api.post('/customers', data)
    return response.data
  },
}

// Types
export interface Item {
  id: string
  sku: string
  name: string
  description?: string
  supplier: string
  unit_of_measure: string
  cost_price: number
  reorder_point: number
  min_stock: number
  max_stock: number
  created_at: string
  updated_at: string
}

export interface CreateItemData {
  sku: string
  name: string
  description?: string
  supplier: string
  unit_of_measure: string
  cost_price: number
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
  batch_number?: string
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
  customer_id: string
  picks: { batch_id: string; quantity: number }[]
  reference_number?: string
  notes?: string
}

export interface DashboardKPIs {
  inventory_value: number
  items_in_stock: number
  at_risk_value: number
  at_risk_percentage: number
  low_stock_items: number
  critical_low_stock: number
  unread_alerts: number
  recent_receipts: number
  recent_dispatches: number
}

export interface CreateDeliveryNoteData {
  customer_id: string
  items: { batch_id: string; quantity: number }[]
  is_consignment?: boolean
  notes?: string
}

export interface CreateCustomerData {
  name: string
  email?: string
  phone?: string
  address?: string
  contact_person?: string
}

export default api

