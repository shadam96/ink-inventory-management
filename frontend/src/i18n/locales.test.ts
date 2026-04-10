import { describe, it, expect } from 'vitest'
import he from './locales/he.json'
import en from './locales/en.json'
import el from './locales/el.json'
import tr from './locales/tr.json'

/**
 * Recursively collect all leaf-key paths from a nested object.
 * e.g. { a: { b: "x" } } → ["a.b"]
 */
function collectKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = []
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...collectKeys(v as Record<string, unknown>, path))
    } else {
      keys.push(path)
    }
  }
  return keys.sort()
}

describe('Locale file structural parity', () => {
  const heKeys = collectKeys(he)

  it('he.json has keys (sanity check)', () => {
    expect(heKeys.length).toBeGreaterThan(100)
  })

  for (const [name, locale] of [
    ['en', en],
    ['el', el],
    ['tr', tr],
  ] as const) {
    describe(`${name}.json`, () => {
      const localeKeys = collectKeys(locale as Record<string, unknown>)

      it('has the same number of keys as he.json', () => {
        expect(localeKeys.length).toBe(heKeys.length)
      })

      it('contains every key from he.json', () => {
        const missing = heKeys.filter((k) => !localeKeys.includes(k))
        expect(missing).toEqual([])
      })

      it('has no extra keys beyond he.json', () => {
        const extra = localeKeys.filter((k) => !heKeys.includes(k))
        expect(extra).toEqual([])
      })
    })
  }
})
