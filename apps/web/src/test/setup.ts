import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { resetSessionForTests } from '../session'

beforeEach(() => {
  window.localStorage.clear()
  resetSessionForTests()
  vi.stubGlobal('crypto', { randomUUID: vi.fn(() => '00000000-0000-4000-8000-000000000001') })
  vi.stubGlobal('performance', { now: vi.fn(() => Date.now()) })
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn(() => 'blob:test-photo'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
