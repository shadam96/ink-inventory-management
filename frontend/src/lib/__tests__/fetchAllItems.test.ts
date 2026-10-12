import { describe, it, expect, beforeEach, vi } from 'vitest'
import { itemsApi, type Item, type PaginatedResponse } from '@/lib/api'
import { fetchAllItems } from '@/lib/fetchAllItems'

vi.mock('@/lib/api', () => ({
  itemsApi: { list: vi.fn() },
}))

const item = (id: string, name: string) => ({ id, name }) as Item

const pageOf = (page: number, pages: number, items: Item[]) =>
  ({ items, total: 0, page, page_size: 100, pages }) as PaginatedResponse<Item>

describe('fetchAllItems', () => {
  beforeEach(() => {
    vi.mocked(itemsApi.list).mockReset()
  })

  it('fetches every page and returns the items sorted by name', async () => {
    vi.mocked(itemsApi.list)
      .mockResolvedValueOnce(pageOf(1, 3, [item('1', 'Cyan'), item('2', 'black')]))
      .mockResolvedValueOnce(pageOf(2, 3, [item('3', 'Yellow'), item('4', 'Amber')]))
      .mockResolvedValueOnce(pageOf(3, 3, [item('5', 'Magenta')]))

    const items = await fetchAllItems()

    expect(items.map((i) => i.name)).toEqual(['Amber', 'black', 'Cyan', 'Magenta', 'Yellow'])
    expect(itemsApi.list).toHaveBeenCalledTimes(3)
    expect(itemsApi.list).toHaveBeenNthCalledWith(1, { page: 1, page_size: 100, sort_by: 'name' })
    expect(itemsApi.list).toHaveBeenNthCalledWith(3, { page: 3, page_size: 100, sort_by: 'name' })
  })

  it('lists an item once even if it shifted onto the next page between requests', async () => {
    vi.mocked(itemsApi.list)
      .mockResolvedValueOnce(pageOf(1, 2, [item('1', 'Black'), item('2', 'Cyan')]))
      .mockResolvedValueOnce(pageOf(2, 2, [item('2', 'Cyan'), item('3', 'Yellow')]))

    const items = await fetchAllItems()

    expect(items.map((i) => i.id)).toEqual(['1', '2', '3'])
  })

  it('stops after one request when the response has no page count', async () => {
    vi.mocked(itemsApi.list).mockResolvedValue({ items: [item('1', 'Black')] } as PaginatedResponse<Item>)

    const items = await fetchAllItems()

    expect(items).toHaveLength(1)
    expect(itemsApi.list).toHaveBeenCalledTimes(1)
  })
})
