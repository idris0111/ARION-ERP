import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Heart, Maximize2, Minimize2, Play, Volume2, VolumeX, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { readableError } from '../../api/client'
import { Button, EmptyState, LoadingSkeleton } from '../../components/ui'
import { breakApi } from './api'
import { BreakTimer } from './BreakTimer'
import { useBreakSession } from './useBreakSession'
import { useBreakSettings } from './useBreakRoom'
import { useSoundMixer } from './useSoundMixer'
import type { Scene } from './types'

const sceneImage=(scene:Scene)=>scene.image_url||`${import.meta.env.BASE_URL}break-room/${scene.image_key}.png`

export default function NaturePage(){
  const {data:scenes,isLoading,error}=useQuery({queryKey:['break-scenes'],queryFn:breakApi.scenes})
  const {data:settings}=useBreakSettings()
  const {start,end}=useBreakSession()
  const sound=useSoundMixer(settings?.volume||50)
  const [active,setActive]=useState<Scene|null>(null)
  const [minutes,setMinutes]=useState(5)
  const [timerKey,setTimerKey]=useState(0)
  const [complete,setComplete]=useState(false)
  const [controls,setControls]=useState(true)
  const [lastInteraction,setLastInteraction]=useState(0)
  const [favorites,setFavorites]=useState<string[]>(()=>{try{return JSON.parse(localStorage.getItem('break_favorite_scenes')||'[]')}catch{return []}})
  const [failure,setFailure]=useState('')
  const frame=useRef<HTMLDivElement>(null)
  const navigate=useNavigate()

  useEffect(()=>{if(settings)setMinutes(settings.default_duration)},[settings?.default_duration])
  useEffect(()=>{if(!active)return;setControls(true);const id=window.setTimeout(()=>setControls(false),4200);return()=>window.clearTimeout(id)},[active,lastInteraction])
  const enter=async(scene:Scene)=>{try{await start('nature');setFailure('');setActive(scene);setComplete(false);setTimerKey(value=>value+1)}catch(error){setFailure(readableError(error))}}
  const leave=async()=>{sound.stopAll();await end();if(document.fullscreenElement)await document.exitFullscreen();setActive(null);setComplete(false)}
  const favorite=(id:string)=>setFavorites(old=>{const next=old.includes(id)?old.filter(item=>item!==id):[...old,id];localStorage.setItem('break_favorite_scenes',JSON.stringify(next));return next})
  const ambience=active?.image_key==='ocean'?'ocean':active?.image_key==='forest'?'forest':'wind'
  if(isLoading)return <LoadingSkeleton/>
  if(error)return <EmptyState title="Сцены недоступны" description={readableError(error)}/>
  if(active)return <div ref={frame} className="nature-player" onMouseMove={()=>setLastInteraction(Date.now())} onTouchStart={()=>setLastInteraction(Date.now())}>
    {active.video_url?<video key={active.id} src={active.video_url} poster={sceneImage(active)} autoPlay={settings?.nature_autoplay} muted loop playsInline preload="none"/>:<img src={sceneImage(active)} alt={active.name}/>}
    <div className="nature-shade"/>
    <div className={`nature-controls ${controls?'visible':''}`}><div className="nature-top"><div><span className="break-eyebrow">NATURE / SHORT BREAK</span><h2>{active.name}</h2><p>{active.description}</p></div><button onClick={()=>void leave()} aria-label="Закрыть сцену"><X size={20}/></button></div><div className="nature-bottom"><div className="nature-actions"><Button onClick={()=>void sound.toggle(ambience)}>{sound.levels[ambience]?<Volume2 size={16}/>:<VolumeX size={16}/>} {sound.levels[ambience]?'Звук включён':'Включить звук'}</Button><label>Громкость <input type="range" min="0" max="100" value={sound.master} onChange={e=>sound.setMaster(Number(e.target.value))}/></label><Button onClick={()=>void (document.fullscreenElement?document.exitFullscreen():frame.current?.requestFullscreen())}>{document.fullscreenElement?<Minimize2 size={16}/>:<Maximize2 size={16}/>} Экран</Button><Button onClick={()=>favorite(active.id)}><Heart size={16} fill={favorites.includes(active.id)?'currentColor':'none'}/> Избранное</Button></div><div className="nature-timing"><div className="duration-options">{[2,5,10,15].map(value=><button key={value} className={minutes===value?'active':''} onClick={()=>{setMinutes(value);setTimerKey(key=>key+1)}}>{value} мин</button>)}<label>Своё <input type="number" min="1" max="60" value={minutes} onChange={e=>setMinutes(Math.min(60,Math.max(1,Number(e.target.value)||1)))}/></label></div>{!complete&&<BreakTimer key={timerKey} minutes={minutes} onComplete={()=>{void end();sound.stopAll();setComplete(true)}}/>}</div></div></div>
    {complete&&<div className="break-complete"><h2>Перерыв завершён</h2><p>Готовы продолжить?</p><Button variant="primary" onClick={()=>{void leave().then(()=>navigate('/'))}}>Вернуться к работе</Button><Button onClick={()=>void start('nature').then(()=>{setComplete(false);setTimerKey(key=>key+1)})}>Остаться здесь</Button></div>}
  </div>
  return <div className="break-section"><div className="break-section-title"><span className="break-eyebrow">NATURE</span><h2>Выберите атмосферу</h2><p>Откройте одну сцену и оставьте рабочие задачи за пределами экрана на несколько минут.</p></div>{failure&&<p className="break-error">{failure}</p>}<div className="nature-grid">{scenes?.map(scene=><button className="nature-card" key={scene.id} onClick={()=>void enter(scene)}><img loading="lazy" src={scene.thumbnail_url||sceneImage(scene)} alt=""/><span className="nature-card-shade"/><span className="nature-card-copy"><strong>{scene.name}</strong><small>{scene.description}</small></span><span className="nature-card-play"><Play size={16}/></span></button>)}</div></div>
}
