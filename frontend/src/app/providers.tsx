import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { api, authStore } from '../api/client'
import type { Organization, User } from '../types'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30000, refetchOnWindowFocus: false } } })
type Session = { user: User | null; loading: boolean; login: (username:string,password:string)=>Promise<void>; logout:()=>void; organization: string; setOrganization:(id:string)=>void; organizations:Organization[]; theme:'light'|'dark'; toggleTheme:()=>void }
const SessionContext = createContext<Session | null>(null)
export const useSession = () => { const value = useContext(SessionContext); if (!value) throw new Error('SessionProvider missing'); return value }
export function AppProviders({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}><SessionProvider>{children}</SessionProvider></QueryClientProvider>
}

function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(authStore.access() || authStore.refresh()))
  const [organization, setOrg] = useState(localStorage.getItem('nexora_organization') || '')
  const [theme, setTheme] = useState<'light'|'dark'>(() => localStorage.getItem('nexora_theme') === 'dark' ? 'dark' : 'light')
  useEffect(() => { document.documentElement.classList.toggle('dark', theme === 'dark'); localStorage.setItem('nexora_theme', theme) }, [theme])
  useEffect(() => { api.restore().then(restored => restored ? api.me() : null).then(setUser).catch(() => { authStore.clear(); setUser(null) }).finally(() => setLoading(false)) }, [])
  const logout = useCallback(() => { authStore.clear(); setUser(null); setOrg(''); localStorage.removeItem('nexora_organization'); localStorage.removeItem('nexora_currency'); queryClient.clear() }, [])
  useEffect(() => { window.addEventListener('nexora:logout', logout); return () => window.removeEventListener('nexora:logout', logout) }, [logout])
  const login = async (username:string,password:string) => { await api.login(username,password); setUser(await api.me()); queryClient.clear() }
  const setOrganization = (id:string) => { setOrg(id); id ? localStorage.setItem('nexora_organization',id) : localStorage.removeItem('nexora_organization'); queryClient.clear() }
  const { data } = useQuery({ queryKey:['organizations'], queryFn:()=>api.list<Organization>('organizations/',{page_size:100}), enabled:!!user })
  useEffect(() => {
    const companies = data?.results || []
    if (!companies.length) return
    const selected = companies.find(item => String(item.id) === organization)
    if (!selected) {
      const first = companies[0]
      setOrg(String(first.id))
      localStorage.setItem('nexora_organization', String(first.id))
      localStorage.setItem('nexora_currency', first.currency || 'TJS')
    } else {
      localStorage.setItem('nexora_currency', selected.currency || 'TJS')
    }
  }, [data, organization])
  const value = { user, loading, login, logout, organization, setOrganization, organizations:data?.results||[], theme, toggleTheme:()=>setTheme(t=>t==='light'?'dark' as const:'light' as const) }
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
