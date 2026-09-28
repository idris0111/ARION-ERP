import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { breakApi } from './api'

export function useBreakSession(){
  const active=useRef<number|null>(null)
  const client=useQueryClient()
  const end=async()=>{
    const id=active.current
    if(id!==null){
      await breakApi.endSession(id)
      if(active.current===id)active.current=null
      client.invalidateQueries({queryKey:['break-room-stats']})
    }
  }
  const start=async(type:string)=>{
    if(active.current!==null)await end()
    active.current=(await breakApi.startSession(type)).id
  }
  useEffect(()=>()=>{if(active.current!==null)void breakApi.endSession(active.current)},[])
  return {start,end}
}
