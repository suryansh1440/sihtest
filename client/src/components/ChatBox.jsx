import React from 'react'
import InputBox from './InputBox'
import { useSelector } from 'react-redux'
import Analysis from './Analysis'
import { useDispatch } from 'react-redux'
import { setIsChatMapOpen } from '../slices/chatmap'

const ChatBox = () => {
  const chats = useSelector((state) => state.chat.chats)

  const dispatch = useDispatch()

  return (
    <div className='flex flex-col h-full w-full bg-white/70 backdrop-blur border-r border-slate-200 shadow-sm rounded-lg overflow-hidden'>
      <div className='flex-1 overflow-y-auto px-2 py-4'>
        {chats.length === 0 && (
          <div className='text-center text-slate-500 text-sm'>Start the conversation by sending a message.</div>
        )}

        {/* temp  */}
        <p onClick={()=>{
          dispatch(setIsChatMapOpen(true))
        }} className='text-red-300'>see map analysis here</p>


        {chats.map((chat, idx) => (
          <div key={idx} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-2 shadow-sm border ${chat.role === 'user' ? 'bg-blue-600 text-white border-blue-600' : 'bg-slate-50 text-slate-800 border-slate-200'}`}>
              <p className='whitespace-pre-wrap leading-relaxed'>{chat.message}</p>
              {chat.role !== 'user' && chat.graphs && <Analysis graphs={chat.graphs} />}
            </div>
          </div>
        ))}
      </div>
      <div className='border-t border-slate-200 bg-white p-3'>
        <InputBox/>
      </div>
    </div>
  )
}

export default ChatBox
