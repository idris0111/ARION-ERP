import { useEffect, useReducer, useRef, type TouchEvent } from 'react'

const SIZE=18
type Point={x:number;y:number}
type Direction='up'|'right'|'down'|'left'
type Status='ready'|'playing'|'over'|'won'
type Game={snake:Point[];food:Point;direction:Direction;nextDirection:Direction;score:number;status:Status;seed:number}
type Action={type:'start'|'tick'}|{type:'turn';direction:Direction}|{type:'reset';seed:number}

const vectors:Record<Direction,Point>={up:{x:0,y:-1},right:{x:1,y:0},down:{x:0,y:1},left:{x:-1,y:0}}
const opposite:Record<Direction,Direction>={up:'down',right:'left',down:'up',left:'right'}
const initialSnake:Point[]=[{x:8,y:9},{x:7,y:9},{x:6,y:9}]
const same=(a:Point,b:Point)=>a.x===b.x&&a.y===b.y

function placeFood(snake:Point[],seed:number):{food:Point;seed:number}{
  const nextSeed=(Math.imul(seed,1664525)+1013904223)>>>0
  const occupied=new Set(snake.map(({x,y})=>y*SIZE+x))
  const free:number[]=[]
  for(let index=0;index<SIZE*SIZE;index++)if(!occupied.has(index))free.push(index)
  const index=free[nextSeed%free.length]
  return {food:{x:index%SIZE,y:Math.floor(index/SIZE)},seed:nextSeed}
}

function newGame(seed:number):Game{
  const snake=[...initialSnake]
  const placement=placeFood(snake,seed)
  return {snake,food:placement.food,direction:'right',nextDirection:'right',score:0,status:'ready',seed:placement.seed}
}

function reduceGame(state:Game,action:Action):Game{
  if(action.type==='reset')return {...newGame(action.seed),status:'playing'}
  if(action.type==='start')return state.status==='ready'?{...state,status:'playing'}:state
  if(action.type==='turn'){
    if(state.status==='over'||state.status==='won'||action.direction===opposite[state.direction])return state
    return {...state,nextDirection:action.direction,status:state.status==='ready'?'playing':state.status}
  }
  if(state.status!=='playing')return state
  const vector=vectors[state.nextDirection]
  const head={x:state.snake[0].x+vector.x,y:state.snake[0].y+vector.y}
  const ate=same(head,state.food)
  const body=ate?state.snake:state.snake.slice(0,-1)
  if(head.x<0||head.y<0||head.x>=SIZE||head.y>=SIZE||body.some(segment=>same(segment,head)))return {...state,status:'over'}
  const snake=[head,...state.snake.slice(0,ate?undefined:-1)]
  if(!ate)return {...state,snake,direction:state.nextDirection}
  if(snake.length===SIZE*SIZE)return {...state,snake,score:state.score+1,status:'won',direction:state.nextDirection}
  const placement=placeFood(snake,state.seed)
  return {...state,snake,food:placement.food,seed:placement.seed,score:state.score+1,direction:state.nextDirection}
}

const keyDirection:Record<string,Direction>={ArrowUp:'up',ArrowRight:'right',ArrowDown:'down',ArrowLeft:'left',w:'up',d:'right',s:'down',a:'left'}

export default function SnakeGame({paused}:{paused:boolean}){
  const [game,dispatch]=useReducer(reduceGame,Date.now(),newGame)
  const touchStart=useRef<Point|null>(null)
  useEffect(()=>{
    if(paused||game.status!=='playing')return
    const timer=window.setInterval(()=>dispatch({type:'tick'}),Math.max(90,175-game.score*3))
    return()=>window.clearInterval(timer)
  },[paused,game.status,game.score])
  useEffect(()=>{
    const onKey=(event:KeyboardEvent)=>{
      const direction=keyDirection[event.key]||keyDirection[event.key.toLowerCase()]
      if(direction){event.preventDefault();if(!paused)dispatch({type:'turn',direction})}
      else if(event.code==='Space'&&game.status==='ready'){event.preventDefault();if(!paused)dispatch({type:'start'})}
    }
    window.addEventListener('keydown',onKey)
    return()=>window.removeEventListener('keydown',onKey)
  },[paused,game.status])
  const onTouchStart=(event:TouchEvent<HTMLDivElement>)=>{touchStart.current={x:event.touches[0].clientX,y:event.touches[0].clientY}}
  const onTouchEnd=(event:TouchEvent<HTMLDivElement>)=>{
    if(paused||!touchStart.current)return
    const dx=event.changedTouches[0].clientX-touchStart.current.x
    const dy=event.changedTouches[0].clientY-touchStart.current.y
    touchStart.current=null
    if(Math.max(Math.abs(dx),Math.abs(dy))<24)return
    dispatch({type:'turn',direction:Math.abs(dx)>Math.abs(dy)?dx>0?'right':'left':dy>0?'down':'up'})
  }
  const occupied=new Set(game.snake.map(({x,y})=>y*SIZE+x))
  const head=game.snake[0].y*SIZE+game.snake[0].x
  const food=game.food.y*SIZE+game.food.x
  return <div className="snake-game">
    <div className="snake-heading"><div><strong>Змейка</strong><span>Собирайте ягоды и не сталкивайтесь со стенами или хвостом.</span></div><div className="snake-score">Счёт <strong>{game.score}</strong></div></div>
    <div className="snake-board-frame" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      <div className="snake-board" role="img" aria-label={`Поле игры «Змейка». Счёт: ${game.score}. ${game.status==='over'?'Игра окончена.':game.status==='won'?'Победа.':''}`}>
        {Array.from({length:SIZE*SIZE},(_,index)=><span key={index} aria-hidden="true" className={`snake-cell${occupied.has(index)?index===head?' head':' body':index===food?' food':''}`}/>)}
      </div>
      {game.status!=='playing'&&<div className="snake-overlay"><strong>{game.status==='ready'?'Готовы играть?':game.status==='won'?'Поле заполнено!':'Игра окончена'}</strong><span>{game.status==='ready'?'Нажмите «Начать» или стрелку на клавиатуре.':`Ваш счёт: ${game.score}`}</span><button type="button" onClick={()=>game.status==='ready'?dispatch({type:'start'}):dispatch({type:'reset',seed:Date.now()})}>{game.status==='ready'?'Начать':'Заново'}</button></div>}
    </div>
    <div className="snake-controls" aria-label="Управление змейкой"><button type="button" className="up" aria-label="Вверх" disabled={paused} onClick={()=>dispatch({type:'turn',direction:'up'})}>↑</button><button type="button" className="left" aria-label="Влево" disabled={paused} onClick={()=>dispatch({type:'turn',direction:'left'})}>←</button><button type="button" className="down" aria-label="Вниз" disabled={paused} onClick={()=>dispatch({type:'turn',direction:'down'})}>↓</button><button type="button" className="right" aria-label="Вправо" disabled={paused} onClick={()=>dispatch({type:'turn',direction:'right'})}>→</button></div>
    <p className="snake-hint">Стрелки или WASD · свайп по полю · кнопки под полем</p>
  </div>
}
