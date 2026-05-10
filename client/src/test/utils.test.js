import { describe, it, expect } from 'vitest'
import { slugify } from '../utils.js'

describe('slugify()', () => {
  it('lowercases the title', () => {
    expect(slugify('Hello World')).toBe('hello-world')
  })

  it('replaces spaces with hyphens', () => {
    expect(slugify('Service Agreement')).toBe('service-agreement')
  })

  it('handles multiple consecutive spaces', () => {
    expect(slugify('Section  3  Policy')).toBe('section-3-policy')
  })

  it('strips special characters', () => {
    expect(slugify('Contract (v2.0)!')).toBe('contract-v20')
  })

  it('trims leading and trailing hyphens', () => {
    expect(slugify('  --Hello--  ')).toBe('hello')
  })

  it('handles all-uppercase titles', () => {
    expect(slugify('ACME CORP NDA')).toBe('acme-corp-nda')
  })

  it('handles already-slugified strings', () => {
    expect(slugify('main')).toBe('main')
  })

  it('returns an empty string for empty input', () => {
    expect(slugify('')).toBe('')
  })

  it('replaces underscores with hyphens', () => {
    expect(slugify('section_3_emissions')).toBe('section-3-emissions')
  })
})
