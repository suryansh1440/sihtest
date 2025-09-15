import React from 'react'
import Navbar from './components/Navbar'
import Chatpage from './pages/Chatpage'
import { Toaster } from 'react-hot-toast'
import ChatMap from './components/ChatMap'
const App = () => {
  return (
    <div className='w-full h-[100vh] bg-gradient-to-b from-slate-50 to-slate-100 relative'>
      <Navbar />
      <div className='w-full mx-auto'>
        <Chatpage />
        <Toaster/>
      </div>
      <ChatMap/>
    </div>
  )
}

export default App
