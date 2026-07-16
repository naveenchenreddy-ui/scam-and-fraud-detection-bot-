import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Menu, X, MessageSquare, BarChart3, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Conversations from './pages/Conversations'
import ConversationDetail from './pages/ConversationDetail'
import { apiService } from './services/apiService'

function App() {
  const [isOpen, setIsOpen] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      await apiService.getHealth()
      setIsConnected(true)
      setLoading(false)
    } catch (error) {
      console.error('Connection error:', error)
      setIsConnected(false)
      setLoading(false)
    }
  }

  return (
    <Router>
      <div className="flex h-screen bg-gray-900 text-white">
        {/* Sidebar */}
        <aside className={`${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed inset-y-0 left-0 z-50 w-64 bg-gray-800 border-r border-gray-700 transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:relative lg:w-64`}>
          <div className="h-full flex flex-col">
            {/* Logo */}
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-8 h-8 text-green-400" />
                <h1 className="text-xl font-bold">WhatsApp Bot</h1>
              </div>
              <p className="text-xs text-gray-400 mt-2">NLP Dashboard</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-6 space-y-4">
              <Link
                to="/"
                className="flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                onClick={() => setIsOpen(false)}
              >
                <BarChart3 className="w-5 h-5 text-green-400" />
                <span>Dashboard</span>
              </Link>
              <Link
                to="/conversations"
                className="flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                onClick={() => setIsOpen(false)}
              >
                <MessageSquare className="w-5 h-5 text-blue-400" />
                <span>Conversations</span>
              </Link>
              <Link
                to="/settings"
                className="flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                onClick={() => setIsOpen(false)}
              >
                <Settings className="w-5 h-5 text-gray-400" />
                <span>Settings</span>
              </Link>
            </nav>

            {/* Status */}
            <div className="p-6 border-t border-gray-700">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
                <span className="text-sm">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-700"
              >
                {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
              <h2 className="text-2xl font-bold flex-1 lg:flex-none">
                WhatsApp NLP Bot Dashboard
              </h2>
              <div className="flex items-center space-x-2">
                {loading ? (
                  <span className="text-gray-400 text-sm">Checking...</span>
                ) : isConnected ? (
                  <span className="text-green-400 text-sm">✓ API Connected</span>
                ) : (
                  <span className="text-red-400 text-sm">✗ API Offline</span>
                )}
              </div>
            </div>
          </header>

          {/* Page Content */}
          <main className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400 mx-auto mb-4"></div>
                  <p className="text-gray-400">Loading...</p>
                </div>
              </div>
            ) : !isConnected ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center bg-gray-800 p-8 rounded-lg border border-red-500">
                  <p className="text-red-400 mb-2">⚠️ API Connection Failed</p>
                  <p className="text-gray-400 text-sm">Make sure FastAPI server is running on port 8000</p>
                  <p className="text-gray-500 text-xs mt-4">Command: python -m uvicorn main:app --reload</p>
                </div>
              </div>
            ) : (
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/conversations" element={<Conversations />} />
                <Route path="/conversations/:phoneNumber" element={<ConversationDetail />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            )}
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
