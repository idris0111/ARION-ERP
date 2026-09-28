import { useQuery, useQueryClient } from '@tanstack/react-query'
import { readableError } from '../../api/client'
import { breakApi } from '../break-room/api'
import type { PetSettings } from '../break-room/types'

const toggles:[keyof PetSettings,string][]=[['pet_enabled','Включить питомца'],['show_mini_pet','Показывать мини-питомца'],['show_on_all_pages','Показывать на всех страницах'],['auto_reactions','Реакции на рабочие события'],['sound_enabled','Звук'],['animation_enabled','Анимации'],['reduced_motion','Меньше движения'],['focus_mode_hides_pet','Скрывать при Focus Mode']]

export function usePetSettings(){
  const client=useQueryClient()
  const query=useQuery({queryKey:['pet-settings'],queryFn:breakApi.petSettings,staleTime:60_000})
  const update=async(value:Partial<PetSettings>)=>{const data=await breakApi.updatePetSettings(value);client.setQueryData(['pet-settings'],data);return data}
  return {...query,update}
}

export function PetSettingsPanel(){
  const {data,update,error}=usePetSettings()
  if(error)return <p className="break-error">{readableError(error)}</p>
  if(!data)return <p>Загрузка настроек…</p>
  const toggle=(key:keyof PetSettings,value:boolean)=>void update({[key]:value}).catch(()=>undefined)
  return <div className="surface break-settings-panel pet-settings-panel"><h3>Настройки питомца</h3>
    {toggles.map(([key,label])=><label key={key} className="break-setting-row"><span>{label}</span><input type="checkbox" checked={Boolean(data[key])} onChange={e=>toggle(key,e.target.checked)}/></label>)}
    <label className="break-setting-row"><span>Качество 3D</span><select value={data.quality} onChange={e=>void update({quality:e.target.value as PetSettings['quality']})}><option value="high">Высокое</option><option value="balanced">Сбалансированное</option><option value="performance">Экономное</option></select></label>
    <label className="break-setting-row"><span>Режим по умолчанию</span><select value={data.default_mode} onChange={e=>void update({default_mode:e.target.value as PetSettings['default_mode']})}><option value="mini">Мини</option><option value="panel">Панель</option></select></label>
    <label className="break-setting-row"><span>Предложения перерыва</span><select value={data.reminder_frequency} onChange={e=>void update({reminder_frequency:e.target.value as PetSettings['reminder_frequency']})}><option value="NEVER">Никогда</option><option value="RARELY">Редко</option><option value="SOMETIMES">Иногда</option><option value="OFTEN">Часто</option></select></label>
  </div>
}
