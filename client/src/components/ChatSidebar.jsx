import React from 'react'

const ChatSidebar = () => {
  return (
    <div className='h-full bg-white/70 backdrop-blur border-r border-slate-200 shadow-sm overflow-hidden rounded-xl flex flex-col'>
      {/* Header */}
      <div className='p-4 border-b border-slate-200 bg-white/50'>
        <h2 className='text-lg font-semibold text-slate-800'>Chat History</h2>
        <p className='text-sm text-slate-600 mt-1'>Recent conversations</p>
      </div>
      
      {/* Chat List */}
      <div className='flex-1 overflow-y-auto p-4 space-y-2'>
        {/* Sample chat items */}
        <div className='p-3 rounded-lg bg-blue-50 border border-blue-200 cursor-pointer hover:bg-blue-100 transition-colors'>
          <div className='font-medium text-blue-900 text-sm'>Database Analysis</div>
          <div className='text-xs text-blue-700 mt-1'>Show me sales data for Q4...</div>
          <div className='text-xs text-slate-500 mt-1'>2 hours ago</div>
        </div>
        
        <div className='p-3 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors'>
          <div className='font-medium text-slate-800 text-sm'>User Analytics</div>
          <div className='text-xs text-slate-600 mt-1'>What are the top performing...</div>
          <div className='text-xs text-slate-500 mt-1'>1 day ago</div>
        </div>
        
        <div className='p-3 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors'>
          <div className='font-medium text-slate-800 text-sm'>Revenue Report</div>
          <div className='text-xs text-slate-600 mt-1'>Generate monthly revenue...</div>
          <div className='text-xs text-slate-500 mt-1'>3 days ago</div>
        </div>
        
        <div className='p-3 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer hover:bg-slate-100 transition-colors'>
          <div className='font-medium text-slate-800 text-sm'>Customer Insights</div>
          <div className='text-xs text-slate-600 mt-1'>Analyze customer behavior...</div>
          <div className='text-xs text-slate-500 mt-1'>1 week ago</div>
        </div>
      </div>
      
      {/* Footer */}
      <div className='p-4 border-t border-slate-200 bg-white/50'>
        <button className='w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors'>
          + New Chat
        </button>
      </div>
    </div>
  )
}

export default ChatSidebar
