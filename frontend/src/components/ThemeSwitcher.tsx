import * as Dropdown from '@radix-ui/react-dropdown-menu'
import { Palette } from 'lucide-react'
import { themes, useTheme } from '../contexts/ThemeContext'
import { Button } from './ui'

export function ThemeSwitcher(){const {theme,setTheme}=useTheme();return <Dropdown.Root><Dropdown.Trigger asChild><Button variant="ghost" title="Тема" aria-label="Выбрать тему"><Palette size={17}/><span className="theme-label">Тема</span></Button></Dropdown.Trigger><Dropdown.Portal><Dropdown.Content className="dropdown-content" align="end">{themes.map(item=><Dropdown.Item key={item} className="dropdown-item" onSelect={()=>setTheme(item)}>{item[0].toUpperCase()+item.slice(1)}{theme===item?' ✓':''}</Dropdown.Item>)}</Dropdown.Content></Dropdown.Portal></Dropdown.Root>}
