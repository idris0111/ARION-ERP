import { useEffect, useState } from 'react'
import { Pause, Play, RotateCcw } from 'lucide-react'

export function BreakTimer({minutes,onComplete}:{minutes:number;onComplete:()=>void}){
  const [remaining,setRemaining]=useState(Math.round(minutes*60))
  const [running,setRunning]=useState(true)
  useEffect(()=>{setRemaining(Math.round(minutes*60));setRunning(true)},[minutes])
  useEffect(()=>{
    if(!running||remaining<=0)return
    const id=window.setTimeout(()=>setRemaining(value=>value-1),1000)
    return()=>window.clearTimeout(id)
  },[running,remaining])
  useEffect(()=>{if(remaining===0){setRunning(false);onComplete()}},[remaining])
  const time=`${Math.floor(remaining/60).toString().padStart(2,'0')}:${(remaining%60).toString().padStart(2,'0')}`
  return <div className="break-timer" aria-label={`Осталось ${time}`}><strong>{time}</strong><button type="button" onClick={()=>setRunning(value=>!value)} aria-label={running?'Пауза':'Продолжить'}>{running?<Pause size={16}/>:<Play size={16}/>}</button><button type="button" onClick={()=>{setRemaining(Math.round(minutes*60));setRunning(true)}} aria-label="Перезапустить"><RotateCcw size={16}/></button></div>
}
