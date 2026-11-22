export const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
export function getToken() { return localStorage.getItem('il_token') }
export function saveAuth(x) { localStorage.setItem('il_token', x.token); localStorage.setItem('il_user', JSON.stringify(x.user)) }
export function clearAuth() { localStorage.removeItem('il_token'); localStorage.removeItem('il_user') }
export function getCachedUser() { try { return JSON.parse(localStorage.getItem('il_user')) } catch { return null } }
export async function api(path, opts={}) {
  const headers = { ...(opts.body instanceof FormData ? {} : {'Content-Type': 'application/json'}), ...opts.headers }
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`
  let response
  try { response = await fetch(`${BASE}${path}`, { ...opts, headers }) }
  catch { throw Error('Cannot connect to API. Start the backend on port 8000.') }
  if (opts.blob) { if (!response.ok) throw Error(`Media request failed: ${response.status}`); return response.blob() }
  const raw = await response.text()
  let data
  try { data = JSON.parse(raw) } catch { data = {detail: raw || 'Unexpected response'} }
  if (!response.ok) {
    if (response.status === 401) { clearAuth(); window.dispatchEvent(new Event('interviewloop:unauthorized')) }
    throw Error(Array.isArray(data.detail) ? data.detail.map(x => x.msg).join('; ') : data.detail || data.message || `HTTP ${response.status}`)
  }
  return data
}
export const post = (path, data) => api(path, {method:'POST', body: data instanceof FormData ? data : JSON.stringify(data ?? {})})
export const patch = (path, data) => api(path, {method:'PATCH', body: JSON.stringify(data)})
export const remove = path => api(path, {method:'DELETE'})
