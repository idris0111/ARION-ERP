import { useEffect, useState } from 'react'

type Cell='X'|'O'|null
const lines=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
const winner=(board:Cell[])=>lines.find(line=>line.every(index=>board[index]&&board[index]===board[line[0]]))?.map(index=>board[index])[0]||null

export default function TicTacToe({paused}:{paused:boolean}){
  const [board,setBoard]=useState<Cell[]>(Array(9).fill(null))
  const [turn,setTurn]=useState<'X'|'O'>('X')
  const win=winner(board),draw=!win&&board.every(Boolean)
  useEffect(()=>{if(turn!=='O'||win||draw||paused)return;const id=window.setTimeout(()=>{const open=board.map((cell,index)=>cell===null?index:-1).filter(index=>index>=0);const immediate=(symbol:Cell)=>open.find(index=>{const next=[...board];next[index]=symbol;return winner(next)===symbol});const index=immediate('O')??immediate('X')??(open.includes(4)?4:open[Math.floor(Math.random()*open.length)]);if(index!==undefined){setBoard(old=>old.map((cell,position)=>position===index?'O':cell));setTurn('X')}},500);return()=>window.clearTimeout(id)},[turn,board,paused,win,draw])
  const play=(index:number)=>{if(paused||turn!=='X'||board[index]||win||draw)return;setBoard(old=>old.map((cell,position)=>position===index?'X':cell));setTurn('O')}
  return <div className="mini-game"><p>Крестики-нолики: вы играете за X.</p><div className="tic-grid">{board.map((cell,index)=><button key={index} onClick={()=>play(index)} aria-label={`Клетка ${index+1}: ${cell||'пусто'}`}>{cell}</button>)}</div><strong className="game-result">{win?win==='X'?'Вы выиграли — отличная игра!':'Питомец победил. Можно попробовать снова.':draw?'Ничья. Хорошо сыграно.':turn==='X'?'Ваш ход':'Ход соперника…'}</strong></div>
}
