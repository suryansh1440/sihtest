import React from 'react'
import ChatBox from '../components/ChatBox'

const Chatpage = () => {
  return (
    <div className='h-[calc(100vh-64px)] py-4'>
      <div className='h-full bg-white/70 backdrop-blur rounded-xl border border-slate-200 shadow-sm overflow-hidden'>
        <ChatBox/>
      </div>
    </div>
  )
}

export default Chatpage
