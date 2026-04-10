import { describe, it, expect, afterEach } from 'vitest'
import i18n from './index'
import { applyDocumentDirection } from './applyDocumentDirection'

describe('applyDocumentDirection', () => {
  // Ensure we restore Hebrew after each test so other test files
  // that depend on the Hebrew default aren't affected.
  afterEach(async () => {
    await i18n.changeLanguage('he')
  })

  it('sets <html lang> and <html dir> for Hebrew (RTL)', async () => {
    applyDocumentDirection()
    await i18n.changeLanguage('he')

    expect(document.documentElement.lang).toBe('he')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('sets <html lang> and <html dir> for English (LTR)', async () => {
    applyDocumentDirection()
    await i18n.changeLanguage('en')

    expect(document.documentElement.lang).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('sets <html lang> and <html dir> for Greek (LTR)', async () => {
    applyDocumentDirection()
    await i18n.changeLanguage('el')

    expect(document.documentElement.lang).toBe('el')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('sets <html lang> and <html dir> for Turkish (LTR)', async () => {
    applyDocumentDirection()
    await i18n.changeLanguage('tr')

    expect(document.documentElement.lang).toBe('tr')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('falls back to Hebrew for unsupported languages', async () => {
    applyDocumentDirection()
    await i18n.changeLanguage('ja')

    expect(document.documentElement.lang).toBe('he')
    expect(document.documentElement.dir).toBe('rtl')
  })
})
