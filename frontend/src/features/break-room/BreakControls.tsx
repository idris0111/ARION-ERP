import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Focus, Leaf } from 'lucide-react'
import { useSession } from '../../app/providers'
import { Button } from '../../components/ui'
import { useBreakSettings } from './useBreakRoom'

export function FocusToggle(){
  const {data,update}=useBreakSettings()
  if(!data?.policy.enabled)return null
  return <Button variant="ghost" size="icon" title={data.focus_mode?'Выключить Focus Mode':'Включить Focus Mode'} aria-label={data.focus_mode?'Выключить Focus Mode':'Включить Focus Mode'} onClick={()=>void update({focus_mode:!data.focus_mode})}><Focus size={18} className={data.focus_mode?'focus-active':''}/></Button>
}

export function BreakReminder(){
  const {user}=useSession()
  const {data,update}=useBreakSettings()
  const [visible,setVisible]=useState(false)
  const interval=data?.reminders==='RARELY'?120:data?.reminders==='SOMETIMES'?75:data?.reminders==='OFTEN'?45:0
  const key=`break_reminder_at_${user?.id||0}`
  useEffect(()=>{
    if(!interval||!data?.policy.enabled||data.focus_mode){setVisible(false);return}
    if(!localStorage.getItem(key))localStorage.setItem(key,String(Date.now()))
    const check=()=>{if(document.visibilityState==='visible'&&Date.now()-Number(localStorage.getItem(key)||Date.now())>=interval*60_000)setVisible(true)}
    const id=window.setInterval(check,60_000);check();return()=>window.clearInterval(id)
  },[interval,data?.policy.enabled,data?.focus_mode,key])
  if(!visible||!data?.policy.enabled||data.focus_mode)return null
  const dismiss=()=>{localStorage.setItem(key,String(Date.now()));setVisible(false)}
  return <div className="break-reminder"><Leaf size={18}/><span>Вы давно работаете. Хотите сделать короткий перерыв?</span><Link to="/break-room" onClick={dismiss}>Сделать паузу</Link><button onClick={dismiss}>Позже</button><button onClick={()=>{dismiss();void update({reminders:'NEVER'})}}>Не напоминать</button></div>
}
