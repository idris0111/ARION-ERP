import { useCallback, useEffect, useRef, useState } from 'react'

export type PetAnimation='idle'|'blink'|'breathing'|'wave'|'happy'|'excited'|'talk'|'listen'|'thinking'|'sleepy'|'sleep'|'sad'|'supportive'|'petted'|'playful'|'jump'|'sit'
const duration:Partial<Record<PetAnimation,number>>={blink:180,breathing:1800,wave:1750,happy:1650,excited:2100,talk:2600,listen:1800,thinking:2100,sad:2200,supportive:2200,petted:1800,playful:2100,jump:1250,sit:2200}
const aliases:Record<string,PetAnimation>={calm:'supportive',pet:'petted',listening:'listen',talking:'talk',waving:'wave',sleeping:'sleep'}

export function usePetAnimation(reducedMotion=false){
  const [animation,setAnimation]=useState<PetAnimation>('idle')
  const timer=useRef<number|undefined>(undefined)
  const lastAction=useRef(Date.now())
  const play=useCallback((requested:PetAnimation|string)=>{
    window.clearTimeout(timer.current)
    lastAction.current=Date.now()
    const canonical=aliases[requested]||(requested as PetAnimation)
    const next:PetAnimation=reducedMotion&&['jump','excited','playful','wave'].includes(canonical)?'happy':canonical
    setAnimation(next)
    const length=duration[next]
    if(length)timer.current=window.setTimeout(()=>setAnimation('idle'),length)
  },[reducedMotion])
  useEffect(()=>{
    if(reducedMotion)return
    const interval=window.setInterval(()=>{
      if(Date.now()-lastAction.current>5*60_000){setAnimation(current=>current==='idle'?'sleepy':current);return}
      if(Math.random()<.55)setAnimation(current=>{
        if(current!=='idle')return current
        window.clearTimeout(timer.current)
        timer.current=window.setTimeout(()=>setAnimation('idle'),duration.blink)
        return 'blink'
      })
    },4200)
    return()=>window.clearInterval(interval)
  },[reducedMotion])
  useEffect(()=>()=>window.clearTimeout(timer.current),[])
  return {animation,play}
}
