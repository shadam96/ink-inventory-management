import { itemsApi, type Item } from './api'

// The whole item catalog, sorted by name, for item dropdowns. GET /items
// caps page_size at 100, so a single page silently drops every item past
// the first hundred.
export async function fetchAllItems(): Promise<Item[]> {
  const byId = new Map<string, Item>()
  for (let page = 1; ; page++) {
    const response = await itemsApi.list({ page, page_size: 100, sort_by: 'name' })
    // An item added mid-loop shifts the next page by one, repeating its
    // first item - keying by id keeps that one copy.
    for (const item of response.items ?? []) byId.set(item.id, item)
    // A response without a page count ends the loop rather than spinning
    if (page >= (response.pages ?? 1)) break
  }
  return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name))
}
