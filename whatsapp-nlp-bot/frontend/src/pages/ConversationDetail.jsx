import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Loader } from 'lucide-react'
import { apiService } from '../services/apiService'
import { formatDate, getSentimentColor } from '../utils/helpers'

function ConversationDetail() {
  const { phoneNumber } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetchMessages()
    const interval = setInterval(fetchMessages, 3000)
    return () => clearInterval(interval)
  }, [phoneNumber])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchMessages = async () => {
    try {
      const decodedPhone = decodeURIComponent(phoneNumber)
      const response = await apiService.getMessages(decodedPhone, 0, 100)
      setMessages(response.data.data || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching messages:', err)
      setError('Failed to fetch messages')
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!newMessage.trim()) return

    try {
      setSending(true)
      const decodedPhone = decodeURIComponent(phoneNumber)
      await apiService.sendMessage(decodedPhone, newMessage)
      setNewMessage('')
      await fetchMessages()
    } catch (err) {
      console.error('Error sending message:', err)
      setError('Failed to send message')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
      </div>
    )
  }

  const decodedPhone = decodeURIComponent(phoneNumber)

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/conversations')}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-xl font-bold">{decodedPhone}</h2>
            <p className="text-xs text-gray-400">{messages.length} messages</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border-b border-red-500 text-red-400 px-6 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-400 mb-2">No messages yet</p>
              <p className="text-gray-500 text-sm">Start a conversation below</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message._id}
              className={`flex ${
                message.sender === 'user' ? 'justify-end' : 'justify-start'
              } mb-2`}
            >
              <div
                className={`max-w-xs px-4 py-3 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-100'
                }`}
              >
                <p className="break-words">{message.text}</p>
                <div className="flex items-center justify-between mt-2 space-x-2">
                  <span className="text-xs opacity-70">
                    {formatDate(message.timestamp)}
                  </span>
                  {message.sentiment && (
                    <span
                      className={`text-xs px-2 py-1 rounded ${getSentimentColor(
                        message.sentiment
                      )}`}
                    >
                      {message.sentiment}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
        <form onSubmit={handleSendMessage} className="flex items-center space-x-3">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type a message..."
            disabled={sending}
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sending || !newMessage.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed p-2 rounded-lg transition-colors flex items-center space-x-2"
          >
            {sending ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default ConversationDetail
