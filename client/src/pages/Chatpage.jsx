import React from 'react'
import ChatBox from '../components/ChatBox'
import ChatSidebar from '../components/ChatSidebar'


const Chatpage = () => {
  return (
    <div className='h-[92vh] flex w-full'>
        {/* Sidebar - Fixed width, full height */}
        <div className='w-[25%] h-full p-4 rounded-xl'>
        <ChatSidebar/>
      </div>
      
        {/* Chat Area - Remaining width, full height */}
        <div className='flex-1 overflow-hidden p-4 rounded-xl'>
        <ChatBox/>
      </div>
    </div>
  )
}

export default Chatpage
