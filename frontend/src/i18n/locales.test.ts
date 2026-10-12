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

// i18next plural key suffixes (CLDR plural categories). Which categories a
// language needs is a property of that language's own grammar, not
// something every locale file has to mirror - Hebrew has a distinct "two"
// category (e.g. listTitle_two) that English/Greek/Turkish simply don't
// use, since their CLDR rules never resolve to "two". Normalizing these
// away before comparing keeps the test's real purpose (catch missing or
// mistyped translations) without demanding identical plural forms across
// languages that don't grammatically have them.
const PLURAL_SUFFIXES = ['_zero', '_one', '_two', '_few', '_many', '_other']

function normalizePluralKey(key: string): string {
  const suffix = PLURAL_SUFFIXES.find((s) => key.endsWith(s))
  return suffix ? key.slice(0, -suffix.length) : key
}

function collectNormalizedKeys(obj: Record<string, unknown>): string[] {
  return [...new Set(collectKeys(obj).map(normalizePluralKey))].sort()
}

describe('Locale file structural parity', () => {
  const heKeys = collectNormalizedKeys(he)

  it('he.json has keys (sanity check)', () => {
    expect(heKeys.length).toBeGreaterThan(100)
  })

  for (const [name, locale] of [
    ['en', en],
    ['el', el],
    ['tr', tr],
  ] as const) {
    describe(`${name}.json`, () => {
      const localeKeys = collectNormalizedKeys(locale as Record<string, unknown>)

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
