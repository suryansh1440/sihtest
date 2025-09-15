import React from 'react'

const Navbar = () => {
  return (
    <nav className="bg-white border-b border-slate-200 shadow-sm h-[8vh]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Brand */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <h1 className="text-xl font-bold text-slate-800">MCP Chat</h1>
            </div>
          </div>
          
          {/* Navigation Items */}
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-4">
              <a href="#" className="text-slate-600 hover:text-slate-900 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Dashboard
              </a>
              <a href="#" className="text-slate-600 hover:text-slate-900 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Analytics
              </a>
              <a href="#" className="text-slate-600 hover:text-slate-900 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Settings
              </a>
            </div>
          </div>
          
          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <div className="relative">
              <button className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Profile
              </button>
            </div>
            <div className="relative">
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
                New Chat
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
