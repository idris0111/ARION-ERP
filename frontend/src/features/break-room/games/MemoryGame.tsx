import { useEffect, useState } from 'react'

const icons=['✦','◆','●','☾','❋','▲']
const shuffle=()=>[...icons,...icons].map((value,index)=>({value,id:index})).sort(()=>Math.random()-.5)

export default function MemoryGame({paused}:{paused:boolean}){
  const [cards]=useState(shuffle)
  const [open,setOpen]=useState<number[]>([])
  const [matched,setMatched]=useState<string[]>([])
  const [moves,setMoves]=useState(0)
  useEffect(()=>{if(open.length!==2)return;const [first,second]=open;if(cards[first].value===cards[second].value){setMatched(old=>[...old,cards[first].value]);setOpen([])}else{const id=window.setTimeout(()=>setOpen([]),800);return()=>window.clearTimeout(id)}},[open,cards])
  const flip=(index:number)=>{if(paused||open.length===2||open.includes(index)||matched.includes(cards[index].value))return;setOpen(old=>[...old,index]);setMoves(value=>value+1)}
  return <div className="mini-game"><p>Найдите шесть пар. Ходов: {moves}</p><div className="memory-grid">{cards.map((card,index)=><button key={card.id} className={open.includes(index)||matched.includes(card.value)?'revealed':''} onClick={()=>flip(index)} aria-label={open.includes(index)||matched.includes(card.value)?card.value:'Закрытая карточка'}>{open.includes(index)||matched.includes(card.value)?card.value:'?'}</button>)}</div>{matched.length===icons.length&&<strong className="game-result">Все пары найдены. Хорошая пауза!</strong>}</div>
}
