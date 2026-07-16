import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Phone, Clock, MessageSquare } from 'lucide-react'
import { apiService } from '../services/apiService'
import { formatTimeAgo, truncateText } from '../utils/helpers'

function Conversations() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    fetchConversations()
  }, [page])

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const response = await apiService.getConversations(page * 10, 10)
      setConversations(response.data.data || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching conversations:', err)
      setError('Failed to fetch conversations')
    } finally {
      setLoading(false)
    }
  }

  const handleConversationClick = (phoneNumber) => {
    navigate(`/conversations/${encodeURIComponent(phoneNumber)}`)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Conversations</h2>
        <div className="text-sm text-gray-400">
          Page {page + 1}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {conversations.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
          <MessageSquare className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400">No conversations yet</p>
          <p className="text-gray-500 text-sm mt-2">
            Conversations will appear here when messages are received
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {conversations.map((conversation) => (
            <div
              key={conversation._id}
              onClick={() => handleConversationClick(conversation.phone_number)}
              className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-blue-500 hover:bg-gray-750 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-2">
                    <Phone className="w-4 h-4 text-green-400 flex-shrink-0" />
                    <span className="font-bold text-white group-hover:text-blue-400 transition-colors">
                      {conversation.phone_number}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        conversation.status === 'active'
                          ? 'bg-green-900 text-green-300'
                          : 'bg-gray-700 text-gray-300'
                      }`}
                    >
                      {conversation.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400">
                    {conversation.messages && conversation.messages.length > 0
                      ? truncateText(
                          conversation.messages[conversation.messages.length - 1]?.text,
                          80
                        )
                      : 'No messages'}
                  </p>
                </div>
                <div className="text-right text-xs text-gray-500 flex-shrink-0 ml-4">
                  {conversation.updated_at && (
                    <div className="flex items-center space-x-1 justify-end">
                      <Clock className="w-3 h-3" />
                      <span>{formatTimeAgo(conversation.updated_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {conversations.length > 0 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg transition-colors"
          >
            Previous
          </button>
          <span className="text-gray-400 text-sm">Page {page + 1}</span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={conversations.length < 10}
            className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default Conversations
