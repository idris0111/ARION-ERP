import type { Pet, PetAppearance } from '../break-room/types'

const asset=(name:string)=>`${import.meta.env.BASE_URL}assets/pets/${name}/companion.glb`

export const palette:Record<string,string>={sand:'#c99565',cloud:'#d4dbe1',cocoa:'#7d5948',peach:'#e4a986',sage:'#8cae9c',slate:'#7b8aa0',cream:'#f1e0be',charcoal:'#444a55'}
export const eyePalette:Record<string,string>={warm:'#69412c',blue:'#5c9cca',green:'#5c9d7f',amber:'#c69248'}
export type SpeciesConfig={label:string;modelPath:string;assetReady:boolean;scale:number;offset?:[number,number,number];camera:[number,number,number];target:[number,number,number];ears:string[];tails:string[];colors:string[];clips:Partial<Record<string,string>>}
const animalClips={idle:'Idle',blink:'Idle',breathing:'Idle',wave:'Idle_2',happy:'Idle_2',excited:'Gallop',talk:'Idle_2',listen:'Idle',thinking:'Idle_2_HeadLow',sleepy:'Idle_2_HeadLow',sleep:'Idle_2_HeadLow',sad:'Idle_2_HeadLow',supportive:'Idle_2',petted:'Idle_2',playful:'Gallop',jump:'Jump_ToIdle',sit:'Idle_2_HeadLow'}
const catClips={idle:'Idle',blink:'Idle',breathing:'Idle',wave:'Headbutt',happy:'Headbutt',excited:'Jump_Loop',talk:'Idle',listen:'Idle',thinking:'Idle',sleepy:'Idle',sleep:'Idle',sad:'Idle',supportive:'Headbutt',petted:'Headbutt',playful:'Run',jump:'Jump_Start',sit:'Idle'}
const rabbitClips={idle:'Idle',blink:'Idle',breathing:'Idle',wave:'Wave',happy:'Yes',excited:'Jump',talk:'Yes',listen:'Idle',thinking:'No',sleepy:'Duck',sleep:'Duck',sad:'No',supportive:'Yes',petted:'Yes',playful:'Run',jump:'Jump',sit:'Duck'}
const pandaClips={...rabbitClips,sleepy:'Sitting_Idle',sleep:'Sitting_Idle',sit:'Sitting_Idle',supportive:'Sitting_Idle',petted:'Yes'}
const colors=Object.keys(palette)
export const species={
  cat:{label:'Кот',modelPath:asset('cat'),assetReady:true,scale:1,camera:[0,1.1,3.8],target:[0,.85,0],ears:['pointed','soft'],tails:['long','fluffy'],colors,clips:catClips},
  dog:{label:'Собака',modelPath:asset('dog'),assetReady:true,scale:.63,camera:[0,1.25,5],target:[0,.95,0],ears:['floppy','pointed'],tails:['long','short'],colors,clips:animalClips},
  fox:{label:'Лиса',modelPath:asset('fox'),assetReady:true,scale:.72,camera:[0,1.2,5],target:[0,.9,0],ears:['pointed'],tails:['fluffy'],colors,clips:animalClips},
  rabbit:{label:'Кролик',modelPath:asset('rabbit'),assetReady:true,scale:.57,camera:[0,1.2,3.8],target:[0,.95,0],ears:['long','soft'],tails:['short'],colors,clips:rabbitClips},
  panda:{label:'Панда',modelPath:asset('panda'),assetReady:true,scale:.6,camera:[0,1.2,3.8],target:[0,.95,0],ears:['round'],tails:['short'],colors,clips:pandaClips},
  bear:{label:'Медведь',modelPath:asset('bear'),assetReady:true,scale:.0028,offset:[300,-892,-680],camera:[0,1.15,3.8],target:[0,.9,0],ears:['round'],tails:['short'],colors,clips:{}},
  wolf:{label:'Волк',modelPath:asset('wolf'),assetReady:true,scale:.72,camera:[0,1.2,5],target:[0,.9,0],ears:['pointed'],tails:['fluffy'],colors,clips:animalClips},
} satisfies Record<string,SpeciesConfig>
export type SpeciesId=keyof typeof species
export const speciesIds=Object.keys(species) as SpeciesId[]
export const speciesFor=(id?:string):SpeciesConfig=>species[id as SpeciesId]||species.cat

export type Attachment={label:string;path:string;anchor:'head'|'neck'|'eyes'|'body';ready:boolean;thumbnail?:string}
export const clothes:Record<string,Attachment>={
  hoodie:{label:'Худи',path:'assets/pets/items/hoodie.glb',anchor:'body',ready:false},
  sweater:{label:'Свитер',path:'assets/pets/items/sweater.glb',anchor:'body',ready:false},
  jacket:{label:'Куртка',path:'assets/pets/items/jacket.glb',anchor:'body',ready:false},
  shirt:{label:'Футболка',path:'assets/pets/items/shirt.glb',anchor:'body',ready:false},
  scarf:{label:'Шарф',path:'assets/pets/items/scarf.glb',anchor:'neck',ready:false},
}
export const accessories:Record<string,Attachment>={
  collar:{label:'Ошейник',path:'assets/pets/items/collar.glb',anchor:'neck',ready:false},
  glasses:{label:'Очки',path:'assets/pets/items/glasses.glb',anchor:'eyes',ready:false},
  bow:{label:'Бант',path:'assets/pets/items/bow.glb',anchor:'neck',ready:false},
  hat:{label:'Шляпа',path:'assets/pets/items/hat.glb',anchor:'head',ready:false},
  necklace:{label:'Подвеска',path:'assets/pets/items/necklace.glb',anchor:'neck',ready:false},
  bell:{label:'Колокольчик',path:'assets/pets/items/bell.glb',anchor:'neck',ready:false},
  headphones:{label:'Наушники',path:'assets/pets/items/headphones.glb',anchor:'head',ready:false},
}

export const appearanceOptions={
  body_style:['classic','compact','tall'],primary_color:colors,secondary_color:colors,
  eye_color:Object.keys(eyePalette),face_markings:['','mask','blaze','freckles'],body_markings:['','spots','stripe'],
  clothes:['',...Object.keys(clothes)],accessory:['',...Object.keys(accessories)],
  room:['cozy','forest','mountains','beach','night','minimal'],
} as const
export const defaults:PetAppearance={body_style:'classic',primary_color:'sand',secondary_color:'cream',eye_color:'warm',ears:'classic',tail:'classic',face_markings:'',body_markings:'',clothes:'',accessory:'',room:'cozy'}
export const appearanceOf=(pet:Partial<Pet>):PetAppearance=>({...defaults,...pet.appearance,primary_color:pet.appearance?.primary_color||pet.color||defaults.primary_color,eye_color:pet.appearance?.eye_color||pet.eyes||defaults.eye_color,room:pet.appearance?.room||pet.background||defaults.room})
