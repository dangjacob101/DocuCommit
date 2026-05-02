const listeners = new Map()

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set())
  listeners.get(event).add(fn)
}

export function off(event, fn) {
  const set = listeners.get(event)
  if (set) set.delete(fn)
}

export function emit(event, payload) {
  const set = listeners.get(event)
  if (!set) return
  for (const fn of set) fn(payload)
}
