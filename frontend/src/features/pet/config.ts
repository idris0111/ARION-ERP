import type { Pet, PetAppearance } from '../break-room/types'

const asset=(name:string)=>`${import.meta.env.BASE_URL}assets/pets/${name}/companion.glb`

export const palette:Record<string,string>={sand:'#c99565',cloud:'#d4dbe1',cocoa:'#7d5948',peach:'#e4a986',sage:'#8cae9c',slate:'#7b8aa0',cream:'#f1e0be',charcoal:'#444a55'}
export const eyePalette:Record<string,string>={warm:'#69412c',blue:'#5c9cca',green:'#5c9d7f',amber:'#c69248'}
export type SpeciesConfig={label:string;modelPath:string;assetReady:boolean;scale:number;camera:[number,number,number];target:[number,number,number];ears:string[];tails:string[];colors:string[];clips:Partial<Record<string,string>>}
const commonClips={idle:'Idle',blink:'Blink',breathing:'Breathing',wave:'Wave',happy:'Happy',excited:'Excited',talk:'Talk',listen:'Listen',thinking:'Thinking',sleepy:'Sleepy',sleep:'Sleep',sad:'Sad',supportive:'Sit',petted:'Happy',playful:'Playful',jump:'Jump',sit:'Sit'}
const colors=Object.keys(palette)
export const species={
  cat:{label:'Кот',modelPath:asset('cat'),assetReady:false,scale:1,camera:[0,1.3,3.7],target:[0,.85,0],ears:['pointed','soft'],tails:['long','fluffy'],colors,clips:commonClips},
  dog:{label:'Собака',modelPath:asset('dog'),assetReady:false,scale:1,camera:[0,1.35,4],target:[0,.8,0],ears:['floppy','pointed'],tails:['long','short'],colors,clips:commonClips},
  fox:{label:'Лиса',modelPath:asset('fox'),assetReady:false,scale:1,camera:[0,1.25,3.9],target:[0,.8,0],ears:['pointed'],tails:['fluffy'],colors,clips:commonClips},
  rabbit:{label:'Кролик',modelPath:asset('rabbit'),assetReady:false,scale:1,camera:[0,1.4,3.8],target:[0,.9,0],ears:['long','soft'],tails:['short'],colors,clips:commonClips},
  panda:{label:'Панда',modelPath:asset('panda'),assetReady:false,scale:1,camera:[0,1.45,4.2],target:[0,.9,0],ears:['round'],tails:['short'],colors,clips:commonClips},
  bear:{label:'Медведь',modelPath:asset('bear'),assetReady:false,scale:1,camera:[0,1.5,4.4],target:[0,.9,0],ears:['round'],tails:['short'],colors,clips:commonClips},
  wolf:{label:'Волк',modelPath:asset('wolf'),assetReady:false,scale:1,camera:[0,1.4,4.1],target:[0,.9,0],ears:['pointed'],tails:['fluffy'],colors,clips:commonClips},
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
