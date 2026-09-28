import { http } from '../../api/client'
import type { BreakSession, BreakSettings, BreakStats, Pet, PetMessage, PetSettings, Scene, Sound, SoundPreset } from './types'

export const breakApi = {
  settings: async()=> (await http.get<BreakSettings>('break-room/settings/')).data,
  updateSettings: async(values:Partial<BreakSettings>)=> (await http.patch<BreakSettings>('break-room/settings/',values)).data,
  updateOrganization: async(values:{break_room_enabled?:boolean;break_room_games_enabled?:boolean;break_room_pet_enabled?:boolean})=>(await http.patch('break-room/organization/',values)).data,
  scenes: async()=> (await http.get<Scene[]>('break-room/scenes/')).data,
  sounds: async()=> (await http.get<Sound[]>('break-room/sounds/')).data,
  presets: async()=> (await http.get<SoundPreset[]>('break-room/presets/')).data,
  createPreset: async(values:{name:string;sounds:Record<string,number>;master_volume:number})=>(await http.post<SoundPreset>('break-room/presets/',values)).data,
  deletePreset: async(id:number)=>http.delete(`break-room/presets/${id}/`),
  pet: async()=> (await http.get<Pet|null>('pets/me/')).data,
  createPet: async(values:Partial<Pet>)=> (await http.post<Pet>('pets/',values)).data,
  updatePet: async(values:Partial<Pet>)=> (await http.patch<Pet>('pets/me/',values)).data,
  deletePet: async()=>http.delete('pets/me/'),
  petOptions: async()=> (await http.get<{species:Record<string,{label:string;ears:string[];tails:string[]}>;personalities:string[];styles:string[]}>('pets/options/')).data,
  appearanceOptions: async()=> (await http.get<Record<string,string[]>>('pets/appearance-options/')).data,
  petSettings: async()=> (await http.get<PetSettings>('pets/settings/')).data,
  updatePetSettings: async(values:Partial<PetSettings>)=> (await http.patch<PetSettings>('pets/settings/',values)).data,
  interact: async(interaction_type:string)=> (await http.post<{message:string;mood:string;animation:string}>('pets/interact/',{interaction_type})).data,
  messages: async()=> (await http.get<PetMessage[]>('pets/messages/')).data,
  chat: async(message:string)=> (await http.post<{message:string;mood:string;animation:string}>('pets/chat/',{message})).data,
  clearMessages: async()=>http.delete('pets/messages/'),
  stats: async()=> (await http.get<BreakStats>('break-room/sessions/')).data,
  startSession: async(break_type:string)=> (await http.post<BreakSession>('break-room/sessions/',{break_type})).data,
  endSession: async(id:number)=> (await http.patch<BreakSession>(`break-room/sessions/${id}/`,{})).data,
}
