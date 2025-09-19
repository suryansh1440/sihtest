import React from 'react'
import { useDispatch } from 'react-redux'
import { addMessage } from '../slices/chatSlice'
import { useState } from 'react'
import { axiosInstance } from '../lib/axios'
import toast from 'react-hot-toast'


const InputBox = () => {
    const [input,setInput] = useState('')
    const [isSendingMessage,setSendingMessage] = useState(false)
    const dispatch = useDispatch()

    const handleSubmit =async (e) => {
        e.preventDefault()
        console.log(input)
        dispatch(addMessage({message:input,role:'user'}))
        setSendingMessage(true)
        try{
            const response = await axiosInstance.post('/ask',{ query: input })
            console.log(response.data)
            const data = response?.data || {}
            // Normalize AI message shape to { report, graphs, maps, thought }
            const aiPayload = {
                role:'ai',
                report: data.report || null,
                graphs: Array.isArray(data.graphs) ? data.graphs : [],
                maps: Array.isArray(data.maps) ? data.maps : [],
                thought: typeof data.thought === 'string' ? data.thought : undefined,
            }
            dispatch(addMessage(aiPayload))

        }catch(error){
            const msg = error?.response?.data?.error || error?.message || 'Request failed'
            toast.error(msg)
        }finally{
            setInput('')
            setSendingMessage(false)
        }


    }
  return (
    <div className='flex items-center gap-2 rounded-xl'>
      <input
        type="text"
        placeholder='Enter your message'
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className='flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
      />
      <button
        onClick={handleSubmit}
        disabled={isSendingMessage}
        className='inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-white font-medium shadow-sm hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed'
      >
        {isSendingMessage ? 'Sending...' : 'Send'}
      </button>
    </div>
  )
}

export default InputBox
