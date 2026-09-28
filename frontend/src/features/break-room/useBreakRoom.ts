import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSession } from '../../app/providers'
import { breakApi } from './api'
import type { BreakSettings } from './types'

export function useBreakSettings(){
  const {user,organization}=useSession()
  const client=useQueryClient()
  const key=['break-room-settings',user?.id,organization]
  const query=useQuery({queryKey:key,queryFn:breakApi.settings,enabled:!!user,staleTime:60_000})
  const update=async(values:Partial<BreakSettings>)=>{const result=await breakApi.updateSettings(values);client.setQueryData(key,result);return result}
  const refresh=()=>client.invalidateQueries({queryKey:['break-room-settings']})
  return {...query,update,refresh}
}

export function useBreakStats(enabled=true){
  const {user}=useSession()
  return useQuery({queryKey:['break-room-stats',user?.id],queryFn:breakApi.stats,enabled:!!user&&enabled,staleTime:30_000})
}
