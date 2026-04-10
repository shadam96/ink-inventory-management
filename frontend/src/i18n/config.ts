/**
 * Central language registry. Single source of truth for supported languages,
 * their native labels, text direction, and date-fns locale binding.
 */

export type LanguageCode = 'he' | 'en' | 'el' | 'tr'

export interface LanguageDefinition {
  /** BCP-47 short code used by i18next */
  code: LanguageCode
  /** Native-script label shown in the language switcher */
  label: string
  /** Emoji flag shown in the header language picker */
  flag: string
  /** Text direction for the document root */
  dir: 'rtl' | 'ltr'
  /** BCP-47 locale tag used for Intl APIs (NumberFormat, DateTimeFormat) */
  intlLocale: string
}

export const SUPPORTED_LANGUAGES: readonly LanguageDefinition[] = [
  { code: 'he', label: 'עברית', flag: '🇮🇱', dir: 'rtl', intlLocale: 'he-IL' },
  { code: 'en', label: 'English', flag: '🇬🇧', dir: 'ltr', intlLocale: 'en-US' },
  { code: 'el', label: 'Ελληνικά', flag: '🇬🇷', dir: 'ltr', intlLocale: 'el-GR' },
  { code: 'tr', label: 'Türkçe', flag: '🇹🇷', dir: 'ltr', intlLocale: 'tr-TR' },
] as const

export const SUPPORTED_LANGUAGE_CODES: readonly LanguageCode[] =
  SUPPORTED_LANGUAGES.map((l) => l.code)

export const DEFAULT_LANGUAGE: LanguageCode = 'he'

/** Resolve a language definition from any i18next language string. */
export function resolveLanguage(lng: string | undefined): LanguageDefinition {
  if (!lng) return SUPPORTED_LANGUAGES[0]
  const base = lng.split('-')[0].toLowerCase() as LanguageCode
  return (
    SUPPORTED_LANGUAGES.find((l) => l.code === base) ?? SUPPORTED_LANGUAGES[0]
  )
}

export function isRTL(lng: string | undefined): boolean {
  return resolveLanguage(lng).dir === 'rtl'
}
