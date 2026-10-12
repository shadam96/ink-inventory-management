import { describe, it, expect, beforeEach, vi } from 'vitest'

/**
 * Regression test for the retry-count off-by-one: syncPendingOperations
 * compared operation.retryCount (a snapshot taken before the call) against
 * the freshly-persisted count from incrementRetryCount, so the real cutoff
 * was 4 failed sync attempts, not the documented 3.
 *
 * idb (IndexedDB) isn't available in the jsdom test environment, so this
 * mocks the idb module with a minimal in-memory store implementing just
 * the operations offline.ts actually uses.
 */

type Record = { id: string; retryCount: number; [key: string]: any }

function createFakeDb() {
  const store = new Map<string, Record>()
  return {
    add: async (_storeName: string, value: Record) => {
      store.set(value.id, value)
    },
    get: async (_storeName: string, id: string) => store.get(id),
    put: async (_storeName: string, value: Record) => {
      store.set(value.id, value)
    },
    delete: async (_storeName: string, id: string) => {
      store.delete(id)
    },
    getAllFromIndex: async () =>
      Array.from(store.values()).sort((a, b) => a.timestamp - b.timestamp),
    count: async () => store.size,
  }
}

vi.mock('idb', () => ({
  openDB: vi.fn(async () => createFakeDb()),
}))

describe('offline.ts sync retry cutoff', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('removes a pending operation only after 3 failed sync attempts, not 4', async () => {
    const offline = await import('../offline')

    const id = await offline.addPendingOperation('receive', '/receiving/receive', 'POST', {})

    const apiCallAlwaysFails = vi.fn().mockRejectedValue(new Error('network error'))

    // Attempt 1: retryCount becomes 1, still below the cutoff - not removed.
    await offline.syncPendingOperations(apiCallAlwaysFails)
    expect(await offline.getPendingCount()).toBe(1)

    // Attempt 2: retryCount becomes 2, still below the cutoff - not removed.
    await offline.syncPendingOperations(apiCallAlwaysFails)
    expect(await offline.getPendingCount()).toBe(1)

    // Attempt 3: retryCount becomes 3, hits the cutoff - must be removed
    // on THIS attempt, not the 4th.
    const result = await offline.syncPendingOperations(apiCallAlwaysFails)
    expect(await offline.getPendingCount()).toBe(0)
    expect(result.failed).toBe(1)
    void id
  })
})
