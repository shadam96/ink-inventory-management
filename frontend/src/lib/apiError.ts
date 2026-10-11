/**
 * Extract a user-facing message from a failed API call.
 *
 * FastAPI sends `detail` as a string for HTTPException/ValueError, but as an
 * array of `{loc, msg, type}` objects for request-validation (422) errors -
 * passing that array straight to a toast renders plain objects as React
 * children and throws. Strings pass through, validation arrays are reduced to
 * their `msg` fields, and anything else (network errors, no response) gets
 * the fallback.
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } } | null | undefined)
    ?.response?.data?.detail

  if (typeof detail === 'string') return detail || fallback

  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => (entry as { msg?: unknown } | null)?.msg)
      .filter((msg): msg is string => typeof msg === 'string' && msg !== '')
    if (messages.length > 0) return messages.join('; ')
  }

  return fallback
}
