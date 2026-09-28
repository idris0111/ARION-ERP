import { lazy, Suspense, useEffect, useRef, useState, type PointerEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { MessageCircle, Minus, Send, X } from 'lucide-react'
import { breakApi } from '../break-room/api'
import { useBreakSettings } from '../break-room/useBreakRoom'
import type { Pet } from '../break-room/types'
import { speciesFor } from './config'
import { usePetAnimation } from './usePetAnimation'
import { usePetSettings } from './PetSettingsPanel'
import './pet.css'

const PetCanvas3D=lazy(()=>import('./PetCanvas3D'))
const quick:[string,string][]=[['pet','Погладить'],['joke','Шутка'],['support','Поддержка'],['motivate','Вдохнови'],['rest','Отдохнуть'],['play','Играть']]
const clamp=(value:number,min:number,max:number)=>Math.max(min,Math.min(max,value))

export default function MiniPetWidget(){
  const {pathname}=useLocation()
  const {data:breakSettings}=useBreakSettings()
  const {data:settings,update}=usePetSettings()
  const onDashboard=pathname==='/'
  const shown=Boolean(breakSettings?.policy.pet_enabled&&settings?.pet_enabled&&(settings.show_mini_pet||onDashboard&&breakSettings.show_pet_on_dashboard)&&(settings.show_on_all_pages||onDashboard)&&!(breakSettings?.focus_mode&&settings.focus_mode_hides_pet))
  const {data:pet}=useQuery({queryKey:['my-pet'],queryFn:breakApi.pet,enabled:shown,staleTime:60_000})
  const client=useQueryClient()
  const [panel,setPanel]=useState(false)
  const [collapsed,setCollapsed]=useState(false)
  const [message,setMessage]=useState('')
  const [input,setInput]=useState('')
  const [busy,setBusy]=useState(false)
  const [position,setPosition]=useState<{x:number;y:number}|null>(null)
  const dragging=useRef<{x:number;y:number;startX:number;startY:number;moved:boolean}|null>(null)
  const suppressClick=useRef(false)
  const reduced=Boolean(breakSettings?.reduced_motion||settings?.reduced_motion||!settings?.animation_enabled)
  const {animation,play}=usePetAnimation(reduced)

  useEffect(()=>{
    const saved=settings?.preferred_position
    if(saved?.x!==undefined&&saved.y!==undefined)setPosition({x:clamp(saved.x,8,window.innerWidth-150),y:clamp(saved.y,8,window.innerHeight-130)})
  },[settings?.preferred_position?.x,settings?.preferred_position?.y])
  useEffect(()=>{
    if(!shown||!pet||!settings?.auto_reactions||!onDashboard)return
    const check=()=>{
      const event=Number(localStorage.getItem('break_last_work_event')||0)
      const previous=Number(localStorage.getItem('break_last_reaction_at')||0)
      if(event>previous&&Date.now()-event<15*60_000&&Date.now()-previous>2*60*60_000){
        setMessage('Отличная работа! Самое время немного передохнуть.')
        play('happy')
        localStorage.setItem('break_last_reaction_at',String(Date.now()))
      }
    }
    check();const timer=window.setInterval(check,30_000);return()=>window.clearInterval(timer)
  },[shown,pet?.id,settings?.auto_reactions,onDashboard,play])

  if(!shown||!pet||!pet.is_active)return null
  const hasModel=speciesFor(pet.animal_type).assetReady
  const interact=async(kind:string)=>{
    try{const reply=await breakApi.interact(kind);setMessage(reply.message);play(kind==='pet'?'petted':reply.animation);client.setQueryData<Pet|null>(['my-pet'],old=>old?{...old,mood:reply.mood}:old)}catch{setMessage('Не удалось связаться с питомцем.')}
  }
  const send=async()=>{
    if(!input.trim()||busy)return
    setBusy(true);play('listen')
    try{const reply=await breakApi.chat(input.trim());setMessage(reply.message);setInput('');play(reply.animation==='calm'?'sit':'talk');client.setQueryData<Pet|null>(['my-pet'],old=>old?{...old,mood:reply.mood}:old)}catch{setMessage('Не удалось отправить сообщение.')}finally{setBusy(false)}
  }
  const onPointerDown=(event:PointerEvent<HTMLDivElement>)=>{
    if((event.target as HTMLElement).closest('.mini-pet-panel,button:not(.mini-pet-trigger),input,a'))return
    const bounds=event.currentTarget.getBoundingClientRect()
    dragging.current={x:event.clientX,y:event.clientY,startX:bounds.left,startY:bounds.top,moved:false}
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  const onPointerMove=(event:PointerEvent<HTMLDivElement>)=>{
    const drag=dragging.current;if(!drag)return
    if(Math.abs(event.clientX-drag.x)+Math.abs(event.clientY-drag.y)>6)drag.moved=true
    if(drag.moved)setPosition({x:clamp(drag.startX+event.clientX-drag.x,8,window.innerWidth-150),y:clamp(drag.startY+event.clientY-drag.y,8,window.innerHeight-130)})
  }
  const onPointerUp=(event:PointerEvent<HTMLDivElement>)=>{
    if(dragging.current?.moved){
      suppressClick.current=true
      const rect=event.currentTarget.getBoundingClientRect()
      const side=rect.left+rect.width/2<window.innerWidth/2?8:window.innerWidth-rect.width-8
      const next={x:clamp(side,8,window.innerWidth-rect.width-8),y:clamp(position?.y??rect.top,8,window.innerHeight-rect.height-8)}
      setPosition(next);void update({preferred_position:next}).catch(()=>undefined)
      window.setTimeout(()=>{suppressClick.current=false},100)
    }
    dragging.current=null
  }
  const style=position?{left:position.x,top:position.y,right:'auto',bottom:'auto'}:undefined
  return <div className={`mini-pet-widget ${panel?'panel-open':''} ${collapsed?'collapsed':''} ${hasModel?'has-model':'awaiting-model'}`} style={style} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}>
    {collapsed?<button className="mini-pet-reopen" onClick={()=>setCollapsed(false)} aria-label="Открыть питомца"><MessageCircle size={19}/></button>:<>
      <button className="mini-pet-trigger" onClick={()=>{if(!suppressClick.current)setPanel(value=>!value)}} aria-label={`Открыть панель питомца ${pet.name}`} aria-expanded={panel}>{hasModel?<Suspense fallback={<span>{pet.name}</span>}><PetCanvas3D pet={pet} animation={animation} quality={settings?.quality} reducedMotion={reduced} mini/></Suspense>:<span className="mini-pet-asset-label"><span aria-hidden="true">✦</span><strong>{pet.name}</strong><small>3D скоро</small></span>}</button>
      <div className="mini-pet-title"><span className="mini-pet-drag-handle" title="Перетащить питомца">⋮⋮ {pet.name}</span><button onClick={()=>setCollapsed(true)} aria-label="Свернуть питомца"><Minus size={13}/></button></div>
      {panel&&<div className="mini-pet-panel surface"><div className="mini-pet-panel-head"><div><strong>{pet.name}</strong><small>{pet.mood}</small></div><button onClick={()=>setPanel(false)} aria-label="Закрыть панель"><X size={16}/></button></div>{hasModel&&<div className="mini-pet-panel-stage"><Suspense fallback={null}><PetCanvas3D pet={pet} animation={animation} quality={settings?.quality} reducedMotion={reduced} mini/></Suspense></div>}<p>{message||'Я рядом, когда захочется сделать паузу.'}</p><div className="mini-pet-quick">{quick.map(([kind,label])=><button key={kind} onClick={()=>void interact(kind)}>{label}</button>)}</div><form onSubmit={event=>{event.preventDefault();void send()}}><input value={input} onChange={event=>setInput(event.target.value)} maxLength={500} placeholder="Напишите питомцу…" aria-label="Сообщение питомцу"/><button disabled={busy||!input.trim()} aria-label="Отправить"><Send size={15}/></button></form><div className="mini-pet-links"><Link to="/break-room/pet" onClick={()=>setPanel(false)}>Полная страница</Link><Link to="/break-room/pet?edit=1" onClick={()=>setPanel(false)}>Настроить</Link><button onClick={()=>void update({show_mini_pet:false})}>Скрыть</button></div></div>}
    </>}
  </div>
}
