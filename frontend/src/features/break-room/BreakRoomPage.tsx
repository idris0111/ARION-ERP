import { lazy, Suspense } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Brain, CloudSun, Heart, Settings2, Volume2, Wind } from 'lucide-react'
import { readableError } from '../../api/client'
import { Button, EmptyState, LoadingSkeleton } from '../../components/ui'
import { useBreakSettings, useBreakStats } from './useBreakRoom'
import './break-room.css'

const NaturePage=lazy(()=>import('./NaturePage'))
const SoundsPage=lazy(()=>import('./SoundsPage'))
const GamesPage=lazy(()=>import('./GamesPage'))
const PetPage=lazy(()=>import('./PetPage'))
const BreathingPage=lazy(()=>import('./BreathingPage'))
const BreakSettingsPage=lazy(()=>import('./BreakSettingsPage'))
const sections=[{key:'nature',title:'Nature',description:'Пейзажи и короткие прогулки взглядом',icon:CloudSun},{key:'sounds',title:'Sounds',description:'Соберите собственный звуковой фон',icon:Volume2},{key:'games',title:'Mini Games',description:'Пара минут для внимания',icon:Brain},{key:'pet',title:'My Pet',description:'Личный компаньон для разговора',icon:Heart},{key:'breathing',title:'Breathing',description:'Тихая пауза и дыхание',icon:Wind}] as const

export default function BreakRoomPage(){
  const {pathname}=useLocation()
  const section=pathname.split('/')[2]||'home'
  const {data:settings,isLoading,error}=useBreakSettings()
  const {data:stats}=useBreakStats(Boolean(settings?.policy.enabled))
  const favorites=(()=>{try{return JSON.parse(localStorage.getItem('break_favorite_scenes')||'[]') as string[]}catch{return []}})()
  if(isLoading)return <LoadingSkeleton/>
  if(error)return <EmptyState title="Break Room недоступен" description={readableError(error)}/>
  if(!settings)return <EmptyState title="Не удалось загрузить настройки"/>
  const disabled=!settings.policy.enabled
  const content=section==='nature'?<NaturePage/>:section==='sounds'?<SoundsPage/>:section==='games'?<GamesPage/>:section==='pet'?<PetPage/>:section==='breathing'?<BreathingPage/>:section==='settings'?<BreakSettingsPage/>:null
  return <div className="break-room"><nav className="break-nav" aria-label="Разделы Break Room"><NavLink to="/break-room" end>Обзор</NavLink>{sections.map(item=><NavLink key={item.key} to={`/break-room/${item.key}`}>{item.title}</NavLink>)}<NavLink to="/break-room/settings"><Settings2 size={14}/> Настройки</NavLink></nav>{disabled&&section!=='settings'?<div className="surface break-disabled"><h2>Break Room выключен</h2><p>{settings.policy.organization_enabled?'Включите его в личных настройках, когда захотите сделать паузу.':'Администратор компании отключил эту функцию.'}</p><Link to="/break-room/settings"><Button>Открыть настройки</Button></Link></div>:content?<Suspense fallback={<LoadingSkeleton/>}>{content}</Suspense>:<><div className="break-hero"><img src={`${import.meta.env.BASE_URL}break-room/mountains.png`} alt="Тихое озеро у гор"/><div className="break-hero-shade"/><div className="break-hero-copy"><span className="break-eyebrow">YOUR SPACE TO RESET</span><h1>Небольшая пауза<br/>пойдёт на пользу</h1><p>Даже две минуты помогут сменить ритм. Выберите то, что сейчас подходит.</p><Link to="/break-room/nature"><Button variant="primary"><CloudSun size={17}/> Выбрать сцену</Button></Link></div></div><div className="break-stats"><div className="surface"><small>Время отдыха сегодня</small><strong>{Math.round((stats?.seconds_today||0)/60)} мин</strong></div><div className="surface"><small>Коротких перерывов</small><strong>{stats?.sessions_today||0}</strong></div><div className="surface"><small>Избранных сцен</small><strong>{favorites.length}</strong></div></div><div className="break-section-title"><span className="break-eyebrow">EXPLORE</span><h2>Как хотите отдохнуть?</h2></div><div className="break-action-grid">{sections.filter(item=>item.key!=='games'||settings.policy.games_enabled).filter(item=>item.key!=='pet'||settings.policy.pet_enabled).map(item=><Link className="surface break-action-card" key={item.key} to={`/break-room/${item.key}`}><item.icon size={24}/><strong>{item.title}</strong><small>{item.description}</small><span>Открыть →</span></Link>)}</div>{settings.focus_mode&&<p className="break-note">Focus Mode включён. Напоминания не появятся; этот раздел открыт только по вашему выбору.</p>}</>}</div>
}
