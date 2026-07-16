import React, { useState } from 'react'
import { Settings as SettingsIcon, Copy, Check } from 'lucide-react'

function Settings() {
  const [copied, setCopied] = useState(null)

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const settings = [
    {
      label: 'API Base URL',
      value: 'http://localhost:8000/api',
      description: 'FastAPI server endpoint',
    },
    {
      label: 'Frontend URL',
      value: 'http://localhost:3000',
      description: 'React dashboard URL',
    },
    {
      label: 'WebSocket URL',
      value: 'ws://localhost:8000/ws',
      description: 'Real-time message updates',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center space-x-2 mb-6">
        <SettingsIcon className="w-6 h-6 text-blue-400" />
        <h2 className="text-2xl font-bold">Settings & Configuration</h2>
      </div>

      {/* Connection Settings */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-6">Connection Settings</h3>
        <div className="space-y-4">
          {settings.map((setting, index) => (
            <div key={index} className="border-b border-gray-700 pb-4 last:border-b-0">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-gray-300">
                  {setting.label}
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <code className="flex-1 bg-gray-900 px-4 py-2 rounded text-sm text-green-400 border border-gray-700 overflow-x-auto">
                  {setting.value}
                </code>
                <button
                  onClick={() => handleCopy(setting.value, index)}
                  className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  {copied === index ? (
                    <Check className="w-5 h-5 text-green-400" />
                  ) : (
                    <Copy className="w-5 h-5 text-gray-400" />
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">{setting.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Environment Variables */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-6">Backend Environment Variables</h3>
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300 overflow-x-auto space-y-2">
          <div><span className="text-blue-400">MONGO_URL</span>=mongodb://localhost:27017</div>
          <div><span className="text-blue-400">TWILIO_ACCOUNT_SID</span>=your_account_sid</div>
          <div><span className="text-blue-400">TWILIO_AUTH_TOKEN</span>=your_auth_token</div>
          <div><span className="text-blue-400">TWILIO_WHATSAPP_NUMBER</span>=+1234567890</div>
          <div><span className="text-blue-400">DEBUG</span>=True</div>
        </div>
      </div>

      {/* Quick Start Guide */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-6">Quick Start Guide</h3>
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-green-400 mb-2">1. Install Dependencies</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              pip install -r backend/requirements.txt
            </code>
          </div>
          <div>
            <h4 className="font-semibold text-green-400 mb-2">2. Start MongoDB</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              mongod
            </code>
          </div>
          <div>
            <h4 className="font-semibold text-green-400 mb-2">3. Configure .env</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              cp backend/.env.example backend/.env
            </code>
          </div>
          <div>
            <h4 className="font-semibold text-green-400 mb-2">4. Run FastAPI Server</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              cd backend && python -m uvicorn main:app --reload
            </code>
          </div>
          <div>
            <h4 className="font-semibold text-green-400 mb-2">5. Install Frontend Dependencies</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              cd frontend && npm install
            </code>
          </div>
          <div>
            <h4 className="font-semibold text-green-400 mb-2">6. Start React Dashboard</h4>
            <code className="block bg-gray-900 px-4 py-2 rounded text-sm text-gray-300">
              npm run dev
            </code>
          </div>
        </div>
      </div>

      {/* API Documentation */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-6">API Documentation</h3>
        <p className="text-gray-400 mb-4">
          Interactive API documentation is available at:
        </p>
        <div className="space-y-2">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="block bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-center transition-colors"
          >
            Swagger UI Documentation
          </a>
          <a
            href="http://localhost:8000/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="block bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded text-center transition-colors"
          >
            ReDoc Documentation
          </a>
        </div>
      </div>
    </div>
  )
}

export default Settings
