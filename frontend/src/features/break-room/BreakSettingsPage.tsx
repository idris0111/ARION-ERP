import { useEffect, useState } from 'react'
import { readableError } from '../../api/client'
import { useSession } from '../../app/providers'
import { Button, LoadingSkeleton } from '../../components/ui'
import { breakApi } from './api'
import { useBreakSettings } from './useBreakRoom'
import type { BreakSettings } from './types'

const booleanFields:[keyof BreakSettings,string][]=[['enabled','Включить Break Room'],['show_pet_on_dashboard','Показывать питомца на Dashboard'],['pet_sound','Звук питомца'],['pet_animations','Анимация питомца'],['nature_autoplay','Автозапуск видео сцены'],['focus_mode','Focus Mode'],['reduced_motion','Меньше анимации']]

export default function BreakSettingsPage(){
  const {data,isLoading,update,refresh}=useBreakSettings()
  const {user,organization}=useSession()
  const [form,setForm]=useState<Partial<BreakSettings>>({})
  const [failure,setFailure]=useState('')
  const [saved,setSaved]=useState(false)
  useEffect(()=>{if(data)setForm(data)},[data])
  if(isLoading)return <LoadingSkeleton/>
  if(!data)return <p className="break-error">Не удалось загрузить настройки.</p>
  const change=(field:keyof BreakSettings,value:unknown)=>setForm(old=>({...old,[field]:value}))
  const save=async()=>{try{await update(form);setSaved(true);setFailure('')}catch(error){setFailure(readableError(error))}}
  const admin=Boolean(user?.is_superuser||['SUPER_ADMIN','ADMIN','DIRECTOR'].includes(user?.role||''))
  const organizationToggle=async(field:'break_room_enabled'|'break_room_games_enabled'|'break_room_pet_enabled',value:boolean)=>{try{await breakApi.updateOrganization({[field]:value});await refresh();setFailure('')}catch(error){setFailure(readableError(error))}}
  return <div className="break-section"><div className="break-section-title"><span className="break-eyebrow">PREFERENCES</span><h2>Ваш Break Room</h2><p>Вы решаете, какие функции доступны и когда они появляются. Напоминания по умолчанию выключены.</p></div>{failure&&<p className="break-error">{failure}</p>}{saved&&<p className="break-success">Настройки сохранены.</p>}<div className="surface break-settings-panel">{booleanFields.map(([field,label])=><label key={field} className="break-setting-row"><span>{label}</span><input type="checkbox" checked={Boolean(form[field])} onChange={event=>change(field,event.target.checked)}/></label>)}<label className="break-setting-row"><span>Напоминания</span><select value={form.reminders||'NEVER'} onChange={event=>change('reminders',event.target.value)}><option value="NEVER">Никогда</option><option value="RARELY">Редко</option><option value="SOMETIMES">Иногда</option><option value="OFTEN">Часто</option></select></label><label className="break-setting-row"><span>Обычная длина перерыва</span><select value={form.default_duration||5} onChange={event=>change('default_duration',Number(event.target.value))}>{[2,5,10,15].map(value=><option key={value} value={value}>{value} мин</option>)}</select></label><label className="break-setting-row"><span>Громкость по умолчанию</span><input type="range" min="0" max="100" value={form.volume??50} onChange={event=>change('volume',Number(event.target.value))}/><small>{form.volume??50}%</small></label><div className="break-settings-actions"><Button variant="primary" onClick={()=>void save()}>Сохранить настройки</Button></div></div>{admin&&organization&&<div className="surface break-settings-panel"><h3>Настройки компании</h3><p>Эти переключатели действуют для всех пользователей выбранной компании.</p><label className="break-setting-row"><span>Разрешить Break Room</span><input type="checkbox" checked={data.policy.organization_enabled} onChange={event=>void organizationToggle('break_room_enabled',event.target.checked)}/></label><label className="break-setting-row"><span>Разрешить мини-игры</span><input type="checkbox" checked={data.policy.organization_games_enabled} onChange={event=>void organizationToggle('break_room_games_enabled',event.target.checked)}/></label><label className="break-setting-row"><span>Разрешить питомца</span><input type="checkbox" checked={data.policy.organization_pet_enabled} onChange={event=>void organizationToggle('break_room_pet_enabled',event.target.checked)}/></label></div>}</div>
}
