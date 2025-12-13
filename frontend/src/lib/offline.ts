import { openDB, DBSchema, IDBPDatabase } from 'idb'

// Database schema
interface InventoryDB extends DBSchema {
  pendingOperations: {
    key: string
    value: {
      id: string
      type: 'receive' | 'pick' | 'create' | 'update' | 'delete'
      endpoint: string
      method: 'POST' | 'PUT' | 'DELETE'
      data: any
      timestamp: number
      retryCount: number
    }
    indexes: { 'by-timestamp': number }
  }
  cachedItems: {
    key: string
    value: {
      id: string
      data: any
      cachedAt: number
    }
  }
  cachedBatches: {
    key: string
    value: {
      id: string
      data: any
      cachedAt: number
    }
  }
  cachedCustomers: {
    key: string
    value: {
      id: string
      data: any
      cachedAt: number
    }
  }
}

let db: IDBPDatabase<InventoryDB> | null = null

// Initialize database
export async function initDB(): Promise<IDBPDatabase<InventoryDB>> {
  if (db) return db

  db = await openDB<InventoryDB>('inventory-offline-db', 1, {
    upgrade(database) {
      // Pending operations store (for background sync)
      const pendingStore = database.createObjectStore('pendingOperations', {
        keyPath: 'id',
      })
      pendingStore.createIndex('by-timestamp', 'timestamp')

      // Cached data stores
      database.createObjectStore('cachedItems', { keyPath: 'id' })
      database.createObjectStore('cachedBatches', { keyPath: 'id' })
      database.createObjectStore('cachedCustomers', { keyPath: 'id' })
    },
  })

  return db
}

// Check if online
export function isOnline(): boolean {
  return navigator.onLine
}

// Add pending operation for background sync
export async function addPendingOperation(
  type: 'receive' | 'pick' | 'create' | 'update' | 'delete',
  endpoint: string,
  method: 'POST' | 'PUT' | 'DELETE',
  data: any
): Promise<string> {
  const database = await initDB()
  const id = `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`

  await database.add('pendingOperations', {
    id,
    type,
    endpoint,
    method,
    data,
    timestamp: Date.now(),
    retryCount: 0,
  })

  // Request background sync if available
  if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
    const registration = await navigator.serviceWorker.ready
    await (registration as any).sync.register('sync-pending-operations')
  }

  return id
}

// Get all pending operations
export async function getPendingOperations() {
  const database = await initDB()
  return database.getAllFromIndex('pendingOperations', 'by-timestamp')
}

// Remove pending operation
export async function removePendingOperation(id: string) {
  const database = await initDB()
  await database.delete('pendingOperations', id)
}

// Update retry count
export async function incrementRetryCount(id: string) {
  const database = await initDB()
  const operation = await database.get('pendingOperations', id)
  if (operation) {
    operation.retryCount++
    await database.put('pendingOperations', operation)
  }
}

// Cache items locally
export async function cacheItems(items: any[]) {
  const database = await initDB()
  const tx = database.transaction('cachedItems', 'readwrite')

  for (const item of items) {
    await tx.store.put({
      id: item.id,
      data: item,
      cachedAt: Date.now(),
    })
  }

  await tx.done
}

// Get cached items
export async function getCachedItems(): Promise<any[]> {
  const database = await initDB()
  const cached = await database.getAll('cachedItems')
  return cached.map((c) => c.data)
}

// Cache batches locally
export async function cacheBatches(batches: any[]) {
  const database = await initDB()
  const tx = database.transaction('cachedBatches', 'readwrite')

  for (const batch of batches) {
    await tx.store.put({
      id: batch.id,
      data: batch,
      cachedAt: Date.now(),
    })
  }

  await tx.done
}

// Get cached batches
export async function getCachedBatches(): Promise<any[]> {
  const database = await initDB()
  const cached = await database.getAll('cachedBatches')
  return cached.map((c) => c.data)
}

// Cache customers locally
export async function cacheCustomers(customers: any[]) {
  const database = await initDB()
  const tx = database.transaction('cachedCustomers', 'readwrite')

  for (const customer of customers) {
    await tx.store.put({
      id: customer.id,
      data: customer,
      cachedAt: Date.now(),
    })
  }

  await tx.done
}

// Get cached customers
export async function getCachedCustomers(): Promise<any[]> {
  const database = await initDB()
  const cached = await database.getAll('cachedCustomers')
  return cached.map((c) => c.data)
}

// Clear all caches
export async function clearAllCaches() {
  const database = await initDB()
  await database.clear('cachedItems')
  await database.clear('cachedBatches')
  await database.clear('cachedCustomers')
}

// Get pending operations count
export async function getPendingCount(): Promise<number> {
  const database = await initDB()
  return database.count('pendingOperations')
}

// Sync pending operations when online
export async function syncPendingOperations(
  apiCall: (endpoint: string, method: string, data: any) => Promise<any>
): Promise<{ success: number; failed: number }> {
  if (!isOnline()) {
    return { success: 0, failed: 0 }
  }

  const operations = await getPendingOperations()
  let success = 0
  let failed = 0

  for (const operation of operations) {
    try {
      await apiCall(operation.endpoint, operation.method, operation.data)
      await removePendingOperation(operation.id)
      success++
    } catch (error) {
      await incrementRetryCount(operation.id)

      // Remove after 3 retries
      if (operation.retryCount >= 3) {
        await removePendingOperation(operation.id)
        failed++
      }
    }
  }

  return { success, failed }
}

// Online/offline event handlers
export function setupOnlineHandlers(
  onOnline: () => void,
  onOffline: () => void
) {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)

  // Initial check
  if (isOnline()) {
    onOnline()
  } else {
    onOffline()
  }

  // Cleanup function
  return () => {
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
  }
}


