import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import type { Entity, Page, User } from '../types'

const ACCESS = 'nexora_access'
const REFRESH = 'nexora_refresh'
let refreshPromise: Promise<string> | null = null
export const authStore = {
  access: () => sessionStorage.getItem(ACCESS),
  refresh: () => localStorage.getItem(REFRESH),
  set: (access: string, refresh?: string) => { sessionStorage.setItem(ACCESS, access); if (refresh) localStorage.setItem(REFRESH, refresh) },
  clear: () => { sessionStorage.removeItem(ACCESS); localStorage.removeItem(REFRESH) },
}

export const http = axios.create({ baseURL: '/api/', timeout: 20000 })
http.interceptors.request.use(config => {
  const token = authStore.access()
  if (token) config.headers.Authorization = `Bearer ${token}`
  const organization = localStorage.getItem('nexora_organization')
  if (organization && !config.url?.startsWith('organizations/')) config.headers['X-Organization-ID'] = organization
  return config
})
http.interceptors.response.use(response => response, async (error: AxiosError) => {
  const request = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined
  if (error.response?.status !== 401 || !request || request._retry || request.url?.includes('account/login/') || request.url?.includes('account/token/refresh/')) return Promise.reject(error)
  const refresh = authStore.refresh()
  if (!refresh) { authStore.clear(); window.dispatchEvent(new Event('nexora:logout')); return Promise.reject(error) }
  request._retry = true
  try {
    refreshPromise ||= axios.post('/api/account/token/refresh/', { refresh }).then(({ data }) => { authStore.set(data.access, data.refresh || refresh); return data.access }).finally(() => { refreshPromise = null })
    const access = await refreshPromise
    request.headers = { ...request.headers, Authorization: `Bearer ${access}` } as typeof request.headers
    return http(request)
  } catch (refreshError) { authStore.clear(); window.dispatchEvent(new Event('nexora:logout')); return Promise.reject(refreshError) }
})

export const api = {
  restore: async () => {
    if (authStore.access()) return true
    const refresh = authStore.refresh()
    if (!refresh) return false
    try {
      const { data } = await axios.post<{access:string;refresh?:string}>('/api/account/token/refresh/', { refresh })
      authStore.set(data.access, data.refresh || refresh)
      return true
    } catch { authStore.clear(); return false }
  },
  login: async (username: string, password: string) => { const { data } = await http.post<{access:string;refresh:string}>('account/login/', { username, password }); authStore.set(data.access, data.refresh); return data },
  me: async () => (await http.get<User>('account/me/')).data,
  list: async <T extends Entity = Entity>(endpoint: string, params: Record<string, unknown> = {}) => {
    const { data } = await http.get<Page<T> | T[]>(endpoint, { params })
    return Array.isArray(data) ? { count: data.length, next: null, previous: null, results: data } : data
  },
  detail: async <T extends Entity = Entity>(endpoint: string, id: string | number) => (await http.get<T>(`${endpoint}${id}/`)).data,
  create: async <T extends Entity = Entity>(endpoint: string, payload: Record<string, unknown>) => (await http.post<T>(endpoint, payload)).data,
  update: async <T extends Entity = Entity>(endpoint: string, id: number, payload: Record<string, unknown>) => (await http.patch<T>(`${endpoint}${id}/`, payload)).data,
  remove: async (endpoint: string, id: number) => (await http.delete(`${endpoint}${id}/`)).data,
  action: async (endpoint: string, id: number, action: string, payload: Record<string, unknown> = {}) => {
    const { data } = await http.post(`${endpoint}${id}/${action}/`, payload)
    if (action === 'post' && ['sales/', 'inventories/'].includes(endpoint)) localStorage.setItem('break_last_work_event', String(Date.now()))
    return data
  },
  download: async (path: string, filename: string) => { const { data } = await http.get(path, { responseType: 'blob' }); const url = URL.createObjectURL(data); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url) },
}

export function readableError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Сервер недоступен. Проверьте соединение с Django API.'
    const data = error.response.data
    if (typeof data === 'string') return data
    if (data && typeof data === 'object') return Object.entries(data).map(([key, value]) => key === 'detail' ? String(value) : `${key}: ${Array.isArray(value) ? value.join(', ') : String(value)}`).join(' · ')
  }
  return error instanceof Error ? error.message : 'Не удалось выполнить операцию.'
}
