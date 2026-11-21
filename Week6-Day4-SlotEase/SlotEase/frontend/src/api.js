// Thin fetch wrapper. All calls go to /api (nginx / vite proxy -> FastAPI).
const BASE = import.meta.env.VITE_API_BASE || '/api'
const TOKEN_KEY = 'slotease.token'
const AI_KEY = 'slotease.openai'

export const storage = {
  get(k) { try { return localStorage.getItem(k) } catch { return null } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v) } catch { /* ignore */ } },
}

export const getToken = () => storage.get(TOKEN_KEY)
export const setToken = (t) => storage.set(TOKEN_KEY, t)

export function getAiSettings() {
  try { return JSON.parse(storage.get(AI_KEY)) || { key: '', model: 'gpt-4o-mini' } } catch { return { key: '', model: 'gpt-4o-mini' } }
}
export function setAiSettings(s) { storage.set(AI_KEY, s ? JSON.stringify(s) : null) }

export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code }
}

export async function api(path, { method = 'GET', body, auth = true, headers = {} } = {}) {
  const h = { 'Content-Type': 'application/json', ...headers }
  const token = getToken()
  if (auth && token) h.Authorization = `Bearer ${token}`
  let res
  try {
    res = await fetch(BASE + path, { method, headers: h, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(0, 'NETWORK', 'Cannot reach the server. Is the backend running?')
  }
  const text = await res.text()
  const data = text ? (() => { try { return JSON.parse(text) } catch { return { message: text } } })() : null
  if (!res.ok) {
    if (res.status === 401 && auth && token) {
      setToken(null)
      window.dispatchEvent(new Event('slotease:logout'))
    }
    throw new ApiError(res.status, data?.error || 'ERROR', data?.message || data?.detail || `Request failed (${res.status})`)
  }
  return data
}

export const aiHeaders = () => {
  const { key } = getAiSettings()
  return key ? { 'X-OpenAI-Key': key } : {}
}
