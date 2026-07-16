# Quick API Testing Guide

## Testing the Message Processing & MongoDB Integration

This guide provides ready-to-use cURL commands and examples to test the WhatsApp NLP Bot system.

---

## Prerequisites

```bash
# Start the system
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Verify backend is running
curl http://localhost:8000/health
```

---

## 1. Health Check

### Command
```bash
curl http://localhost:8000/health
```

### Response
```json
{
  "status": "healthy",
  "timestamp": "2024-07-02T10:30:00.000000",
  "mongodb": "connected",
  "twilio": "configured"
}
```

---

## 2. Test Message Analysis (Without WhatsApp)

### Test Sentiment Analysis

```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "I love your product! It is amazing!",
    "sender": "user"
  }'
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "text": "I love your product! It is amazing!",
    "sentiment": "positive",
    "intent": "feedback",
    "entities": {
      "numbers": [],
      "emails": [],
      "urls": [],
      "keywords": ["love", "product", "amazing"]
    }
  }
}
```

---

### Test Help Intent

```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "I have a problem with my account. Can you help me?",
    "sender": "user"
  }'
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "text": "I have a problem with my account. Can you help me?",
    "sentiment": "negative",
    "intent": "help",
    "entities": {
      "numbers": [],
      "emails": [],
      "urls": [],
      "keywords": ["problem", "account", "help"]
    }
  }
}
```

---

### Test Product Inquiry

```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "What is the price of your premium plan?",
    "sender": "user"
  }'
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "text": "What is the price of your premium plan?",
    "sentiment": "neutral",
    "intent": "product_inquiry",
    "entities": {
      "numbers": [],
      "emails": [],
      "urls": [],
      "keywords": ["price", "premium", "plan"]
    }
  }
}
```

---

### Test Email Extraction

```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "Please contact me at john.doe@company.com for the invoice",
    "sender": "user"
  }'
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "text": "Please contact me at john.doe@company.com for the invoice",
    "sentiment": "neutral",
    "intent": "billing",
    "entities": {
      "numbers": [],
      "emails": ["john.doe@company.com"],
      "urls": [],
      "keywords": ["contact", "company", "invoice"]
    }
  }
}
```

---

## 3. Simulate WhatsApp Webhook (for testing without Twilio)

### Manual Webhook Test

```bash
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "Hi, I need help with my account",
    "MessageSid": "SM1234567890abcdef"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook processed",
  "analysis": {
    "sentiment": "negative",
    "intent": "help",
    "entities_found": 2
  }
}
```

---

### Multiple Webhook Tests (Simulate Conversation)

```bash
# Message 1: Greeting
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "Hi there!",
    "MessageSid": "SM001"
  }'

# Message 2: Problem
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "I have an issue with my order",
    "MessageSid": "SM002"
  }'

# Message 3: More details
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "The order was supposed to arrive yesterday",
    "MessageSid": "SM003"
  }'

# Message 4: Gratitude
curl -X POST http://localhost:8000/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+1234567890",
    "Body": "Thanks for your help!",
    "MessageSid": "SM004"
  }'
```

---

## 4. Query MongoDB Data

### View All Conversations

```bash
curl http://localhost:8000/api/conversations
```

**Response:**
```json
{
  "success": true,
  "total": 1,
  "data": [
    {
      "_id": "66a3b4c5d1e2f3g4h5i6j7k8",
      "phone_number": "+1234567890",
      "message_count": 4,
      "created_at": "2024-07-02T10:30:00.000000",
      "updated_at": "2024-07-02T10:35:00.000000",
      "status": "active",
      "sentiment_count": {
        "negative": 2,
        "neutral": 1,
        "positive": 1
      },
      "intent_count": {
        "greeting": 1,
        "help": 2,
        "gratitude": 1
      }
    }
  ]
}
```

---

### Get Specific Conversation

```bash
curl http://localhost:8000/api/conversations/+1234567890
```

**Response:**
```json
{
  "success": true,
  "conversation": {
    "_id": "66a3b4c5d1e2f3g4h5i6j7k8",
    "phone_number": "+1234567890",
    "message_count": 4,
    "status": "active",
    "sentiment_count": {...},
    "intent_count": {...}
  },
  "messages": [
    {
      "_id": "msg_001",
      "text": "Hi there!",
      "sender": "user",
      "sentiment": "neutral",
      "intent": "greeting",
      "timestamp": "2024-07-02T10:30:00.000000"
    },
    {
      "_id": "msg_002",
      "text": "👋 Hello! How can I help you today?",
      "sender": "bot",
      "sentiment": "neutral",
      "intent": "response",
      "timestamp": "2024-07-02T10:30:01.000000"
    }
    ...
  ]
}
```

---

### Get Conversation Analytics

```bash
curl http://localhost:8000/api/conversations/+1234567890/analytics
```

**Response:**
```json
{
  "success": true,
  "phone_number": "+1234567890",
  "total_messages": 8,
  "user_messages": 4,
  "bot_messages": 4,
  "sentiment_breakdown": {
    "positive": 1,
    "negative": 2,
    "neutral": 1
  },
  "intent_breakdown": {
    "greeting": 1,
    "help": 2,
    "gratitude": 1
  },
  "avg_response_time_seconds": 1.23
}
```

---

### Get All Messages for a Conversation

```bash
curl "http://localhost:8000/api/messages/+1234567890?skip=0&limit=50"
```

---

## 5. Dashboard Analytics

### Get Overall Statistics

```bash
curl http://localhost:8000/api/dashboard/stats
```

**Response:**
```json
{
  "success": true,
  "total_conversations": 5,
  "total_messages": 45,
  "active_conversations": 4,
  "sentiment_distribution": {
    "positive": 15,
    "negative": 10,
    "neutral": 20
  },
  "intent_distribution": {
    "greeting": 5,
    "help": 12,
    "product_inquiry": 8,
    "feedback": 3,
    "general_inquiry": 17
  }
}
```

---

## 6. MongoDB Direct Queries (Using mongosh)

### Connect to MongoDB
```bash
docker exec -it whatsapp_nlp_mongodb mongosh mongodb://admin:password@localhost:27017/whatsapp_nlp_bot

# Or use mongosh directly if installed
mongosh "mongodb://admin:password@localhost:27017/whatsapp_nlp_bot"
```

### Query Messages

```javascript
// All messages
db.messages.find().pretty()

// User messages only
db.messages.find({"sender": "user"}).pretty()

// Bot responses only
db.messages.find({"sender": "bot"}).pretty()

// Negative sentiment messages
db.messages.find({"sentiment": "negative"}).pretty()

// Help intent messages
db.messages.find({"intent": "help"}).pretty()

// Count by sentiment
db.messages.aggregate([
  {"$match": {"sender": "user"}},
  {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}
])

// Count by intent
db.messages.aggregate([
  {"$match": {"sender": "user"}},
  {"$group": {"_id": "$intent", "count": {"$sum": 1}}}
])

// Recent messages (last 10)
db.messages.find().sort({"timestamp": -1}).limit(10).pretty()

// Messages from specific phone number
db.messages.find({"phone_number": "+1234567890"}).pretty()
```

### Query Conversations

```javascript
// All conversations
db.conversations.find().pretty()

// Active conversations
db.conversations.find({"status": "active"}).pretty()

// Conversations with message count
db.conversations.find({}, {"phone_number": 1, "message_count": 1}).pretty()

// Sort by last updated
db.conversations.find().sort({"updated_at": -1}).pretty()
```

---

## 7. Test Different Intents

### Greeting
```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1111111111", "text": "Hello there!", "sender": "user"}'
```

### Farewell
```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1111111111", "text": "Goodbye, see you later!", "sender": "user"}'
```

### Account Related
```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1111111111", "text": "I need to reset my password", "sender": "user"}'
```

### Billing Related
```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1111111111", "text": "Can I get a refund for my order?", "sender": "user"}'
```

---

## 8. Batch Testing (Test Suite)

### Save as `test_bot.sh`

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing WhatsApp NLP Bot ==="
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
curl -s $BASE_URL/health | jq .
echo ""

# Test 2: Analyze Positive Message
echo "Test 2: Positive Sentiment"
curl -s -X POST $BASE_URL/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "text": "Your product is amazing!", "sender": "user"}' | jq .
echo ""

# Test 3: Analyze Negative Message
echo "Test 3: Negative Sentiment"
curl -s -X POST $BASE_URL/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "text": "This is terrible and broken", "sender": "user"}' | jq .
echo ""

# Test 4: Analyze Help Request
echo "Test 4: Help Intent"
curl -s -X POST $BASE_URL/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "text": "I need support with my issue", "sender": "user"}' | jq .
echo ""

# Test 5: Webhook Simulation
echo "Test 5: Webhook Simulation"
curl -s -X POST $BASE_URL/api/messages/webhook \
  -H "Content-Type: application/json" \
  -d '{"From": "whatsapp:+1234567890", "Body": "Hi bot!", "MessageSid": "TEST001"}' | jq .
echo ""

# Test 6: Get Conversations
echo "Test 6: Get Conversations"
curl -s $BASE_URL/api/conversations | jq .
echo ""

# Test 7: Get Analytics
echo "Test 7: Dashboard Stats"
curl -s $BASE_URL/api/dashboard/stats | jq .
echo ""

echo "=== All tests completed ==="
```

### Run the test suite
```bash
chmod +x test_bot.sh
./test_bot.sh
```

---

## 9. Postman Collection (Optional)

### Import into Postman

You can import these into Postman as a collection:

```json
{
  "info": {
    "name": "WhatsApp NLP Bot API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health"
      }
    },
    {
      "name": "Analyze Message",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/messages/analyze",
        "body": {
          "mode": "raw",
          "raw": "{\"phone_number\": \"+1234567890\", \"text\": \"Hi!\", \"sender\": \"user\"}"
        }
      }
    },
    {
      "name": "Webhook Test",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/messages/webhook",
        "body": {
          "mode": "raw",
          "raw": "{\"From\": \"whatsapp:+1234567890\", \"Body\": \"Hello\", \"MessageSid\": \"TEST001\"}"
        }
      }
    },
    {
      "name": "Get Conversations",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/conversations"
      }
    },
    {
      "name": "Dashboard Stats",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/dashboard/stats"
      }
    }
  ]
}
```

---

## Summary

| Test | Command | Tests |
|------|---------|-------|
| Sentiment | analyze endpoint | Positive, Negative, Neutral |
| Intent | analyze endpoint | Help, Greeting, Product, etc. |
| Entities | analyze endpoint | Emails, URLs, Numbers |
| Webhook | webhook endpoint | Message reception & processing |
| Data | GET endpoints | Retrieval & aggregation |
| Analytics | dashboard stats | Overall statistics |
| MongoDB | mongosh queries | Direct database access |
