# WhatsApp NLP Bot with React Dashboard

A complete end-to-end application for WhatsApp customer support automation using NLP (Natural Language Processing), built with FastAPI, React, MongoDB, and Twilio API integration.

## 🎯 Features

- **Real-time Message Processing**: Receive and process WhatsApp messages in real-time
- **Sentiment Analysis**: Analyze user sentiment using TextBlob NLP
- **Auto-Response Generation**: Generate intelligent responses based on message context and sentiment
- **React Dashboard**: Beautiful, responsive dashboard with Tailwind CSS
- **Conversation Management**: View and manage all conversations
- **Message History**: Complete message history with sentiment analysis
- **Statistics & Analytics**: Real-time dashboard with key metrics
- **Twilio Integration**: Send/receive WhatsApp messages via Twilio API
- **MongoDB Database**: Scalable database for storing conversations and messages
- **FastAPI Backend**: High-performance Python backend with automatic API documentation

## 📦 Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **MongoDB**: NoSQL database
- **Twilio**: WhatsApp messaging API
- **TextBlob**: NLP library for sentiment analysis
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI library
- **Vite**: Frontend build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client
- **Lucide React**: Icon library
- **React Router**: Client-side routing

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Python 3.11**: Backend runtime
- **Node.js 18**: Frontend runtime

## 📂 Project Structure

```
whatsapp-nlp-bot/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── Dockerfile              # Backend Docker image
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable components
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx   # Dashboard page
│   │   │   ├── Conversations.jsx # Conversations list
│   │   │   ├── ConversationDetail.jsx # Chat interface
│   │   │   └── Settings.jsx    # Settings page
│   │   ├── services/
│   │   │   └── apiService.js   # API communication
│   │   ├── utils/
│   │   │   └── helpers.js      # Utility functions
│   │   ├── App.jsx             # Main App component
│   │   ├── main.jsx            # Entry point
│   │   └── index.css           # Global styles
│   ├── package.json            # Node dependencies
│   ├── vite.config.js          # Vite configuration
│   ├── tailwind.config.js      # Tailwind configuration
│   ├── postcss.config.js       # PostCSS configuration
│   ├── index.html              # HTML template
│   └── Dockerfile              # Frontend Docker image
├── docker-compose.yml          # Docker Compose configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # This file

```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 7.0+
- Docker & Docker Compose (optional)

### Option 1: Local Development Setup

#### 1. Clone and Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Twilio credentials
nano .env  # or use your editor of choice
```

#### 2. Setup MongoDB

```bash
# Install MongoDB (if not already installed)
# macOS: brew install mongodb-community
# Ubuntu: follow MongoDB installation guide

# Start MongoDB
mongod
```

#### 3. Run FastAPI Server

```bash
# In backend directory with venv activated
python -m uvicorn main:app --reload
```

Server will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 4. Setup Frontend

```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file (already provided)
# Edit if needed for different API URL

# Start development server
npm run dev
```

Dashboard will be available at: `http://localhost:3000`

### Option 2: Docker Compose (Recommended)

```bash
# In project root directory

# Create .env file for Docker
cat > .env << EOF
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+1234567890
EOF

# Build and start all services
docker-compose up --build

# MongoDB: localhost:27017
# FastAPI: http://localhost:8000
# React Dashboard: http://localhost:3000
```

## 🔐 Environment Variables

### Backend (.env)

```env
# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017

# Twilio Configuration (Get from https://www.twilio.com)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+1234567890  # Your Twilio WhatsApp number

# Server Configuration
DEBUG=True
LOG_LEVEL=INFO
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api
```

## 📡 API Endpoints

### Health & Status
- `GET /` - API info
- `GET /health` - Health check

### Conversations
- `GET /api/conversations` - Get all conversations
- `GET /api/conversations/{phone_number}` - Get specific conversation

### Messages
- `GET /api/messages/{phone_number}` - Get messages for conversation
- `POST /api/messages/send` - Send a message
- `POST /api/messages/webhook` - Receive webhook from Twilio

### Analytics
- `GET /api/dashboard/stats` - Get dashboard statistics

## 🎨 Frontend Pages

### Dashboard
- Overall statistics (conversations, messages, active chats)
- Sentiment distribution charts
- System status and features
- Real-time metrics

### Conversations
- List of all conversations
- Paginated view
- Last message preview
- Conversation status
- Last updated timestamp

### Conversation Detail
- Full message history
- Chat interface
- Sentiment analysis per message
- Message timestamps
- Send new messages

### Settings
- Configuration guide
- API documentation links
- Environment variables reference
- Quick start guide

## 📊 Database Schema

### Conversations Collection
```json
{
  "_id": ObjectId,
  "phone_number": "string",
  "messages": [ObjectId],
  "created_at": ISODate,
  "updated_at": ISODate,
  "status": "active|inactive"
}
```

### Messages Collection
```json
{
  "_id": ObjectId,
  "phone_number": "string",
  "text": "string",
  "sender": "user|bot",
  "sentiment": "positive|negative|neutral",
  "timestamp": ISODate,
  "message_sid": "string"
}
```

## 🔌 Twilio Setup

1. **Create Twilio Account**
   - Go to https://www.twilio.com
   - Sign up for free account
   - Verify phone number

2. **Setup WhatsApp Sandbox**
   - Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
   - Get your Twilio WhatsApp number
   - Join the sandbox by sending "join <code>" to the Twilio number

3. **Configure Webhooks**
   - Copy your FastAPI server URL
   - Go to Twilio Console → Messaging → Whatsapp
   - Set webhook URL: `https://your-domain.com/api/messages/webhook`
   - Method: POST

4. **Get Credentials**
   - Account SID: Twilio Console → Account
   - Auth Token: Twilio Console → Account
   - WhatsApp Number: From setup above

## 🧪 Testing

### Test Message Send
```bash
curl -X POST http://localhost:8000/api/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "Hello!",
    "sender": "user"
  }'
```

### Test Webhook Simulation
```bash
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "Test message",
    "MessageSid": "SM123456789"
  }'
```

## 📈 Performance Optimization

- **Frontend**: Lazy loading with React Router, code splitting with Vite
- **Backend**: Async/await with FastAPI, connection pooling for MongoDB
- **Database**: Indexed queries, pagination for large datasets
- **Caching**: Regular polling instead of WebSockets for demos

## 🐛 Troubleshooting

### API Connection Issues
1. Check FastAPI server is running: `http://localhost:8000/health`
2. Verify CORS settings in main.py
3. Check network connectivity

### MongoDB Connection Issues
1. Ensure MongoDB is running: `mongod`
2. Check MONGO_URL in .env
3. Verify credentials if auth enabled

### Twilio Integration Issues
1. Verify credentials in .env
2. Check webhook URL configuration
3. Monitor Twilio logs in console

### Frontend Build Issues
1. Clear node_modules: `rm -rf node_modules && npm install`
2. Clear Vite cache: `rm -rf dist node_modules/.vite`
3. Update Node.js version

## 📚 Documentation

- **FastAPI Docs**: http://localhost:8000/docs
- **FastAPI ReDoc**: http://localhost:8000/redoc
- **React Documentation**: https://react.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Twilio Docs**: https://www.twilio.com/docs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 📞 Support

For issues and questions:
1. Check existing issues in the repository
2. Create detailed bug reports with:
   - Environment details
   - Reproduction steps
   - Error logs
   - Expected vs actual behavior

## 🎓 Learning Resources

- **FastAPI Tutorial**: https://fastapi.tiangolo.com
- **MongoDB Guide**: https://docs.mongodb.com
- **React Hooks**: https://react.dev/reference/react
- **Tailwind Utilities**: https://tailwindcss.com/docs/utility-first
- **NLP with TextBlob**: https://textblob.readthedocs.io

## 🚀 Deployment

### Production Checklist

- [ ] Update environment variables for production
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS for production domain
- [ ] Set DEBUG=False in backend
- [ ] Use production-grade database
- [ ] Setup monitoring and logging
- [ ] Configure backup strategy
- [ ] Setup CI/CD pipeline

### Deployment Platforms

- **Backend**: Heroku, Railway, Render, AWS Lambda
- **Frontend**: Vercel, Netlify, AWS S3 + CloudFront
- **Database**: MongoDB Atlas, AWS DocumentDB

## 🎉 Congratulations!

Your WhatsApp NLP Bot is ready! Start building amazing customer support automation.

---

Made with ❤️ by WhatsApp Bot Team
