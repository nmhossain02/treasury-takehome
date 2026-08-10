const SESSION_KEY = 'label-lens.demo-session.v1'
let memorySession: string | undefined

function createSessionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `demo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

export function getDemoSessionId(): string {
  if (memorySession) return memorySession

  try {
    const stored = window.localStorage.getItem(SESSION_KEY)
    if (stored) {
      memorySession = stored
      return stored
    }
    memorySession = createSessionId()
    window.localStorage.setItem(SESSION_KEY, memorySession)
    return memorySession
  } catch {
    memorySession = createSessionId()
    return memorySession
  }
}

export function resetSessionForTests(): void {
  memorySession = undefined
}
