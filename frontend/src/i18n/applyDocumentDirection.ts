import i18n from './index'
import { resolveLanguage } from './config'

/**
 * Synchronizes <html lang> and <html dir> with the current i18next language.
 * Call once before mount, then i18next's `languageChanged` event keeps it
 * up to date for the lifetime of the app.
 */
export function applyDocumentDirection(): void {
  const apply = (lng: string | undefined) => {
    const def = resolveLanguage(lng)
    const root = document.documentElement
    if (root.lang !== def.code) root.lang = def.code
    if (root.dir !== def.dir) root.dir = def.dir
  }

  apply(i18n.language)
  i18n.on('languageChanged', apply)
}
