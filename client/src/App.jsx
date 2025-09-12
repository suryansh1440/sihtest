import React from 'react'
import Navbar from './components/Navbar'
import Chatpage from './pages/Chatpage'
import { Toaster } from 'react-hot-toast'
const App = () => {
  return (
    <div className='w-full h-[100vh] bg-gradient-to-b from-slate-50 to-slate-100'>
      <Navbar />
      <div className='max-w-5xl mx-auto px-4 sm:px-6 lg:px-8'>
        <Chatpage />
        <Toaster/>
      </div>
    </div>
  )
}

export default App
