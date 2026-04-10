import { describe, it, expect, afterEach } from 'vitest'
import { he, enUS, el, tr } from 'date-fns/locale'
import i18n from '@/i18n'
import { getDateFnsLocale } from './dateLocale'

describe('getDateFnsLocale', () => {
  afterEach(async () => {
    await i18n.changeLanguage('he')
  })

  it('returns Hebrew locale for he', async () => {
    await i18n.changeLanguage('he')
    expect(getDateFnsLocale()).toBe(he)
  })

  it('returns English (US) locale for en', async () => {
    await i18n.changeLanguage('en')
    expect(getDateFnsLocale()).toBe(enUS)
  })

  it('returns Greek locale for el', async () => {
    await i18n.changeLanguage('el')
    expect(getDateFnsLocale()).toBe(el)
  })

  it('returns Turkish locale for tr', async () => {
    await i18n.changeLanguage('tr')
    expect(getDateFnsLocale()).toBe(tr)
  })
})
