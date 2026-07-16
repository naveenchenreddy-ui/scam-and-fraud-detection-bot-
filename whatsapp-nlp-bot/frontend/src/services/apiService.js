import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const apiService = {
  // Dashboard
  getDashboardStats: () => api.get('/dashboard/stats'),
  
  // Conversations
  getConversations: (skip = 0, limit = 10) =>
    api.get('/conversations', { params: { skip, limit } }),
  
  getConversation: (phoneNumber) =>
    api.get(`/conversations/${phoneNumber}`),
  
  // Messages
  getMessages: (phoneNumber, skip = 0, limit = 50) =>
    api.get(`/messages/${phoneNumber}`, { params: { skip, limit } }),
  
  sendMessage: (phoneNumber, text) =>
    api.post('/messages/send', {
      phone_number: phoneNumber,
      text,
      sender: 'user',
    }),
  
  // Webhook (for testing)
  sendWebhookMessage: (phoneNumber, text) =>
    api.post('/messages/webhook', {
      From: `whatsapp:${phoneNumber}`,
      Body: text,
      MessageSid: `MSG_${Date.now()}`,
    }),
  
  // Health check
  getHealth: () =>
    axios.get('http://localhost:8000/health'),
}

export default api
