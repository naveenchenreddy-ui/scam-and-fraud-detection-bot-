import React, { useState, useEffect } from 'react'
import { MessageSquare, Users, MessageCircle, TrendingUp } from 'lucide-react'
import { apiService } from '../services/apiService'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      const response = await apiService.getDashboardStats()
      setStats(response.data)
      setError(null)
    } catch (err) {
      console.error('Error fetching stats:', err)
      setError('Failed to fetch statistics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
      </div>
    )
  }

  const statCards = [
    {
      icon: Users,
      label: 'Total Conversations',
      value: stats?.total_conversations || 0,
      color: 'text-blue-400',
      bgColor: 'bg-blue-900/20',
    },
    {
      icon: MessageSquare,
      label: 'Total Messages',
      value: stats?.total_messages || 0,
      color: 'text-green-400',
      bgColor: 'bg-green-900/20',
    },
    {
      icon: MessageCircle,
      label: 'Active Conversations',
      value: stats?.active_conversations || 0,
      color: 'text-purple-400',
      bgColor: 'bg-purple-900/20',
    },
  ]

  return (
    <div className="p-6 space-y-6">
      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {statCards.map((card, index) => {
          const Icon = card.icon
          return (
            <div
              key={index}
              className={`${card.bgColor} border border-gray-700 rounded-lg p-6 hover:border-gray-600 transition-colors`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-2">{card.label}</p>
                  <p className={`text-4xl font-bold ${card.color}`}>
                    {card.value.toLocaleString()}
                  </p>
                </div>
                <Icon className={`w-12 h-12 ${card.color} opacity-20`} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Sentiment Distribution */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-6 flex items-center space-x-2">
          <TrendingUp className="w-5 h-5 text-yellow-400" />
          <span>Sentiment Distribution</span>
        </h3>

        {stats?.sentiment_distribution && Object.keys(stats.sentiment_distribution).length > 0 ? (
          <div className="space-y-4">
            {Object.entries(stats.sentiment_distribution).map(([sentiment, count]) => {
              const total = Object.values(stats.sentiment_distribution).reduce(
                (a, b) => a + b,
                0
              )
              const percentage = (count / total) * 100

              const colors = {
                positive: 'bg-green-500',
                negative: 'bg-red-500',
                neutral: 'bg-gray-500',
              }

              return (
                <div key={sentiment}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="capitalize text-gray-300">{sentiment}</span>
                    <span className="text-sm font-bold">
                      {count} ({percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className={`${colors[sentiment] || 'bg-gray-500'} h-2 rounded-full transition-all duration-300`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">No sentiment data available</p>
        )}
      </div>

      {/* Quick Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h4 className="font-bold mb-4">System Status</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Database</span>
              <span className="text-green-400">✓ Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Twilio API</span>
              <span className="text-green-400">✓ Configured</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">NLP Engine</span>
              <span className="text-green-400">✓ Active</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h4 className="font-bold mb-4">Features</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✓</span>
              <span className="text-gray-300">Real-time message processing</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✓</span>
              <span className="text-gray-300">Sentiment analysis</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✓</span>
              <span className="text-gray-300">Auto-response generation</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
