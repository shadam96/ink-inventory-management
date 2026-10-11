import { describe, it, expect } from 'vitest'
import { getApiErrorMessage } from '../apiError'

const withDetail = (detail: unknown) => ({ response: { data: { detail } } })

describe('getApiErrorMessage', () => {
  it('returns a string detail as-is', () => {
    expect(getApiErrorMessage(withDetail('Batch not found'), 'fallback')).toBe('Batch not found')
  })

  it('joins the msg fields of a validation (422) detail array', () => {
    const detail = [
      { loc: ['body', 'quantity'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'item_id'], msg: 'Field required', type: 'missing' },
    ]
    expect(getApiErrorMessage(withDetail(detail), 'fallback')).toBe(
      'Input should be greater than 0; Field required',
    )
  })

  it('falls back when a detail array has no usable msg', () => {
    expect(getApiErrorMessage(withDetail([{ loc: ['body'] }, null]), 'fallback')).toBe('fallback')
    expect(getApiErrorMessage(withDetail([]), 'fallback')).toBe('fallback')
  })

  it('falls back for an empty string or non-string detail', () => {
    expect(getApiErrorMessage(withDetail(''), 'fallback')).toBe('fallback')
    expect(getApiErrorMessage(withDetail({ msg: 'nope' }), 'fallback')).toBe('fallback')
  })

  it('falls back on a network error with no response', () => {
    expect(getApiErrorMessage(new Error('Network Error'), 'fallback')).toBe('fallback')
  })

  it('falls back when the error is not an object', () => {
    expect(getApiErrorMessage(undefined, 'fallback')).toBe('fallback')
    expect(getApiErrorMessage(null, 'fallback')).toBe('fallback')
    expect(getApiErrorMessage('boom', 'fallback')).toBe('fallback')
  })
})
