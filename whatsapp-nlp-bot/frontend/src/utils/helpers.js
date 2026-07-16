import { formatDistanceToNow, format } from 'date-fns'

export const formatDate = (date) => {
  if (!date) return ''
  try {
    return format(new Date(date), 'MMM dd, yyyy HH:mm')
  } catch {
    return ''
  }
}

export const formatTimeAgo = (date) => {
  if (!date) return ''
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true })
  } catch {
    return ''
  }
}

export const getSentimentColor = (sentiment) => {
  switch (sentiment?.toLowerCase()) {
    case 'positive':
      return 'text-green-400'
    case 'negative':
      return 'text-red-400'
    case 'neutral':
      return 'text-gray-400'
    default:
      return 'text-gray-400'
  }
}

export const getSentimentBgColor = (sentiment) => {
  switch (sentiment?.toLowerCase()) {
    case 'positive':
      return 'bg-green-900'
    case 'negative':
      return 'bg-red-900'
    case 'neutral':
      return 'bg-gray-700'
    default:
      return 'bg-gray-700'
  }
}

export const formatPhoneNumber = (phone) => {
  if (!phone) return ''
  const cleaned = phone.replace(/\D/g, '')
  if (cleaned.length === 10) {
    return `+1${cleaned}`
  }
  return `+${cleaned}`
}

export const truncateText = (text, length = 50) => {
  return text.length > length ? text.substring(0, length) + '...' : text
}
