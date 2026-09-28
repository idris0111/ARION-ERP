import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useAnimations, useGLTF } from '@react-three/drei'
import { clone } from 'three/addons/utils/SkeletonUtils.js'
import { LoopOnce, LoopRepeat, MathUtils, Mesh, MeshPhysicalMaterial, MeshStandardMaterial, type AnimationAction, type Group, type Material, type Object3D } from 'three'
import type { Pet } from '../break-room/types'
import { accessories, appearanceOf, clothes, eyePalette, palette, type Attachment, type SpeciesConfig } from './config'
import type { PetAnimation } from './usePetAnimation'

const names={head:['Head','head','Head_CTRL'],neck:['NeckAttach','neck_attach','Neck'],eyes:['EyesAttach','eyes_attach','Head'],body:['BodyAttach','body_attach','Spine']}
const findAnchor=(root:Object3D,anchor:Attachment['anchor'])=>{
  for(const name of names[anchor]){const node=root.getObjectByName(name);if(node)return node}
  return root
}

function PetAttachment({root,item}:{root:Object3D;item:Attachment}){
  const {scene}=useGLTF(`${import.meta.env.BASE_URL}${item.path}`,true,true)
  const attachment=useMemo(()=>clone(scene),[scene])
  useEffect(()=>{
    const target=findAnchor(root,item.anchor)
    target.add(attachment)
    return()=>{target.remove(attachment)}
  },[root,attachment,item.anchor])
  return null
}

function materialFor(original:Material,slot:string,primary:string,secondary:string,iris:string){
  const material=original.clone()
  const normalized=slot.toLowerCase()
  if(material instanceof MeshStandardMaterial){
    if(normalized.includes('fur_primary')){material.color.set(primary);material.roughness=.86;material.metalness=0}
    if(normalized.includes('fur_secondary')){material.color.set(secondary);material.roughness=.88;material.metalness=0}
    if(normalized.includes('eye_iris')){material.color.set(iris);material.roughness=.18;material.metalness=0}
    if(normalized.includes('fabric')){material.roughness=.9;material.metalness=0}
    if(normalized.includes('metal')){material.roughness=.3;material.metalness=.65}
  }
  if(material instanceof MeshPhysicalMaterial&&normalized.includes('eye')){
    material.clearcoat=1;material.clearcoatRoughness=.07
  }
  return material
}

type Props={pet:Partial<Pet>;spec:SpeciesConfig;animation:PetAnimation;reducedMotion:boolean;eyeTarget:[number,number];onReady:()=>void}
export function PetModel({pet,spec,animation,reducedMotion,eyeTarget,onReady}:Props){
  const {scene,animations}=useGLTF(spec.modelPath,true,true)
  const appearance=appearanceOf(pet)
  const {model,materials}=useMemo(()=>{
    const copy=clone(scene)
    const created:Material[]=[]
    copy.traverse(node=>{
      const mesh=node as Mesh
      if(!mesh.isMesh)return
      mesh.castShadow=true;mesh.receiveShadow=true
      const recolor=(material:Material)=>{
        const updated=materialFor(material,material.name||mesh.name,palette[appearance.primary_color]||palette.sand,palette[appearance.secondary_color]||palette.cream,eyePalette[appearance.eye_color]||eyePalette.warm)
        created.push(updated);return updated
      }
      mesh.material=Array.isArray(mesh.material)?mesh.material.map(recolor):recolor(mesh.material)
    })
    return {model:copy,materials:created}
  },[scene,appearance.primary_color,appearance.secondary_color,appearance.eye_color])
  useEffect(()=>()=>{materials.forEach(material=>material.dispose())},[materials])
  useEffect(()=>{onReady()},[model,onReady])
  const root=useRef<Group>(null)
  const {actions}=useAnimations(animations,root)
  const previous=useRef<AnimationAction|null>(null)
  useEffect(()=>{
    const requested=spec.clips[animation]||spec.clips.idle||'Idle'
    const name=Object.keys(actions).find(key=>key.toLowerCase()===requested.toLowerCase())
    const next=(name&&actions[name])||actions.Idle||Object.values(actions)[0]
    if(!next||previous.current===next)return
    next.reset().setEffectiveWeight(1).fadeIn(.32)
    const repeat=animation==='idle'||animation==='sleep'||animation==='sleepy'
    next.setLoop(repeat?LoopRepeat:LoopOnce,repeat?Infinity:1)
    next.clampWhenFinished=true
    next.play()
    if(previous.current)previous.current.crossFadeTo(next,.32,false)
    previous.current=next
    return()=>{next.fadeOut(.22)}
  },[actions,animation,spec.clips])
  const head=useMemo(()=>findAnchor(model,'head'),[model])
  const faceMeshes=useMemo(()=>{const meshes:Mesh[]=[];model.traverse(node=>{const mesh=node as Mesh;if(mesh.isMesh&&mesh.morphTargetDictionary&&mesh.morphTargetInfluences)meshes.push(mesh)});return meshes},[model])
  useFrame(({clock})=>{
    const t=clock.elapsedTime
    if(head!==model){
      const follow=reducedMotion?0:.055
      head.rotation.y=MathUtils.lerp(head.rotation.y,eyeTarget[0]*follow+Math.sin(t*.28)*.018,.025)
      head.rotation.x=MathUtils.lerp(head.rotation.x,-eyeTarget[1]*follow+Math.sin(t*.47)*.012,.025)
    }
    for(const mesh of faceMeshes){
      const dictionary=mesh.morphTargetDictionary||{}
      const values=mesh.morphTargetInfluences||[]
      const set=(aliases:string[],target:number)=>{const key=aliases.find(alias=>dictionary[alias]!==undefined);if(key!==undefined){const index=dictionary[key];values[index]=MathUtils.lerp(values[index]||0,target,.18)}}
      set(['Blink','blink','eyeBlinkLeft','eyeBlinkRight'],animation==='blink'||animation==='sleep'||animation==='sleepy'||animation==='petted'?1:0)
      set(['Smile','smile','mouthSmile'],['happy','excited','playful','petted','supportive'].includes(animation)?1:0)
      const mouth=animation==='talk'&&!reducedMotion ? .17+Math.abs(Math.sin(t*8))*.35 : 0
      set(['MouthOpen','mouthOpen','jawOpen'],mouth)
      set(['Sad','sad','browSad'],animation==='sad'?0.8:0)
      set(['BodyCompact','bodyCompact'],appearance.body_style==='compact'?1:0)
      set(['BodyTall','bodyTall'],appearance.body_style==='tall'?1:0)
      set(['EarPointed','earPointed'],appearance.ears==='pointed'?1:0)
      set(['EarFloppy','earFloppy'],appearance.ears==='floppy'?1:0)
      set(['EarLong','earLong'],appearance.ears==='long'?1:0)
      set(['TailFluffy','tailFluffy'],appearance.tail==='fluffy'?1:0)
      set(['TailShort','tailShort'],appearance.tail==='short'?1:0)
    }
  })
  const bodyScale=appearance.body_style==='compact'?.96:appearance.body_style==='tall'?1.04:1
  return <group ref={root} scale={spec.scale*bodyScale} dispose={null}>
    <primitive object={model} dispose={null}/>
    {appearance.clothes&&clothes[appearance.clothes]?.ready&&<PetAttachment root={model} item={clothes[appearance.clothes]}/>}
    {appearance.accessory&&accessories[appearance.accessory]?.ready&&<PetAttachment root={model} item={accessories[appearance.accessory]}/>}
  </group>
}
