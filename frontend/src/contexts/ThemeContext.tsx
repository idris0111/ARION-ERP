import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export const themes = ['light', 'dark', 'blue', 'purple', 'emerald'] as const
export type Theme = typeof themes[number]
const ThemeContext = createContext<{theme: Theme; setTheme:(theme:Theme)=>void}|null>(null)

export function ThemeProvider({children}:{children:ReactNode}) {
  const [theme,setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('nexora_theme')
    return themes.find(item => item === saved) || 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('nexora_theme', theme)
  }, [theme])
  return <ThemeContext.Provider value={{theme,setTheme}}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('ThemeProvider missing')
  return context
}
