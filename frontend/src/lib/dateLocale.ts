import { he, enUS, el, tr, type Locale } from 'date-fns/locale'
import i18n from '@/i18n'
import { resolveLanguage, type LanguageCode } from '@/i18n/config'

const LOCALE_MAP: Record<LanguageCode, Locale> = {
  he,
  en: enUS,
  el,
  tr,
}

/**
 * Returns the date-fns Locale for the current i18next language.
 * Use with `format(date, pattern, { locale: getDateFnsLocale() })`
 * or `formatDistanceToNow(date, { locale: getDateFnsLocale() })`.
 */
export function getDateFnsLocale(): Locale {
  return LOCALE_MAP[resolveLanguage(i18n.language).code]
}
