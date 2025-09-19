import React from 'react'
import InputBox from './InputBox'
import { useSelector } from 'react-redux'
import Analysis from './Analysis'
import { useDispatch } from 'react-redux'
import { setIsChatMapOpen, setSelectedMap } from '../slices/chatmap'

const ChatBox = () => {
  const chats = useSelector((state) => state.chat.chats)

  const dispatch = useDispatch()

  return (
    <div className='flex flex-col h-full w-full bg-white/70 backdrop-blur border-r border-slate-200 shadow-sm rounded-lg overflow-hidden'>
      <div className='flex-1 overflow-y-auto px-3 py-4'>
        {chats.length === 0 && (
          <div className='text-center text-slate-500 text-sm'>Start the conversation by sending a message.</div>
        )}

        {chats.map((chat, idx) => (
          <div key={idx} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-sm border ${chat.role === 'user' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-800 border-slate-200'}`}>
              {chat.role === 'user' && (
                <p className='whitespace-pre-wrap leading-relaxed'>{chat.message}</p>
              )}

              {chat.role !== 'user' && (
                <div className='space-y-3'>
                  {chat.report?.title && (
                    <h3 className='text-lg font-semibold text-slate-800'>{chat.report.title}</h3>
                  )}
                  {chat.report?.content && (
                    <p className='text-slate-700 whitespace-pre-wrap'>{chat.report.content}</p>
                  )}
                  {Array.isArray(chat.graphs) && chat.graphs.length > 0 && (
                    <Analysis graphs={chat.graphs} />
                  )}
                  {Array.isArray(chat.maps) && chat.maps.length > 0 && (
                    <div className='pt-1'>
                      <button
                        className='inline-flex items-center gap-2 rounded-md bg-slate-900 text-white px-3 py-1.5 text-sm hover:bg-slate-700'
                        onClick={() => {
                          // open map and select the first map by default
                          dispatch(setSelectedMap({ chatId: chat.id, mapIndex: 0 }))
                          dispatch(setIsChatMapOpen(true))
                        }}
                      >
                        View map ({chat.maps.length})
                      </button>
                    </div>
                  )}
                </div>
              )}
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
