# Twilio WhatsApp Webhook Configuration Guide

## Current Status

✅ Backend is running on `http://localhost:8000`  
✅ NLP analysis pipeline is ready  
✅ MongoDB integration is complete  
❌ Twilio webhook not configured yet → Messages aren't reaching your NLP system

## The Problem

When you send a message to your WhatsApp bot, Twilio currently shows:
```
"Configure your WhatsApp Sandbox's Inbound URL to change this message."
```

This means Twilio doesn't know where to send messages. We need to tell Twilio to send them to your backend webhook.

---

## Solution: Configure Twilio Webhook

### Step 1: Make Your Backend Accessible to Twilio

**Option A: Using ngrok (Easiest for Testing)**

ngrok creates a public URL that tunnels to your local backend.

1. **Download ngrok** from https://ngrok.com/download

2. **Extract and run** (in a new terminal):
```bash
# Navigate to ngrok location
cd C:\path\to\ngrok

# Create tunnel to port 8000
ngrok http 8000
```

You'll see output like:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

**Copy this URL** (e.g., `https://abc123.ngrok.io`)

**Important:** This URL is temporary and changes each time you restart ngrok!

---

### Step 2: Configure Twilio Webhook

1. **Go to Twilio Console**:
   - https://console.twilio.com
   - Login with your credentials

2. **Navigate to WhatsApp Sandbox Settings**:
   - Click: Messaging → WhatsApp → Sandbox
   - OR: https://console.twilio.com/messaging/whatsapp/senders

3. **Set the Webhook URL**:

   In the "When a message comes in" field, enter:
   ```
   https://your-ngrok-url.ngrok.io/api/messages/webhook
   ```

   Example (replace with YOUR ngrok URL):
   ```
   https://abc123.ngrok.io/api/messages/webhook
   ```

   **Method:** POST (default is correct)

4. **Click "Save"**

---

### Step 3: Test the Integration

1. **Send a message** to your WhatsApp bot

2. **Expected Response:**
   ```
   🆘 I'm here to help! Can you describe the issue in detail?
   ```
   (Or another NLP-based response)

3. **Check MongoDB** for stored message:
   ```bash
   # In another terminal, connect to MongoDB
   mongosh "mongodb://admin:password@localhost:27017/whatsapp_nlp_bot"
   
   # View stored messages
   db.messages.find().pretty()
   ```

---

## Production Setup (For Real Server)

Once you deploy to a real server:

1. **Replace ngrok URL** with your server URL:
   ```
   https://your-domain.com/api/messages/webhook
   ```

2. **Make sure your server:**
   - Has HTTPS enabled
   - Port 8000 is accessible
   - Has valid SSL certificate

3. **Update environment variables**:
   ```bash
   TWILIO_ACCOUNT_SID=your_sid
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_WHATSAPP_NUMBER=+1234567890
   ```

---

## Message Flow After Webhook Configuration

```
User sends WhatsApp message
         ↓
Twilio receives message
         ↓
Twilio sends to webhook:
POST https://your-ngrok-url.ngrok.io/api/messages/webhook
{
  "From": "whatsapp:+1234567890",
  "Body": "Your message here",
  "MessageSid": "SM..."
}
         ↓
Your Backend (/api/messages/webhook endpoint)
         ├─ Analyzes sentiment
         ├─ Detects intent
         ├─ Extracts entities
         └─ Generates response
         ↓
Stores in MongoDB
         ├─ User message (with analysis)
         └─ Bot response
         ↓
Sends response back via Twilio
         ↓
User receives response on WhatsApp
```

---

## Verify Setup

### Test 1: Check Backend is Accessible

```bash
# From your machine
curl http://localhost:8000/health

# Should return:
{
  "status": "healthy",
  "mongodb": "connected",
  "twilio": "configured"
}
```

### Test 2: Check ngrok tunnel

```bash
# In terminal where ngrok is running, you should see:
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

### Test 3: Send WhatsApp Message

Send text to your Twilio WhatsApp number and check:
1. **WhatsApp**: Did you get a bot response?
2. **MongoDB**: Was the message stored?
3. **Backend logs**: Check for analysis output

---

## Testing Different Intents

Try these messages to see different responses:

| Message | Expected Response |
|---------|-------------------|
| "Hi there!" | "👋 Hello! How can I help you today?" |
| "I have a problem" | "🆘 I'm here to help! Can you describe the issue in detail?" |
| "Thanks!" | "😊 You're welcome! Happy to assist!" |
| "Goodbye" | "👋 Goodbye! Feel free to reach out anytime!" |
| "What's your product price?" | "📦 Great question! I'd be happy to tell you more about our products." |
| "Can I reset my password?" | "🔐 For account-related inquiries, please visit our account settings..." |
| "I want a refund" | "💳 For billing inquiries, please provide more details..." |
| "This is amazing!" | "😄 Great! I'm glad I could help!" |

---

## View Data in MongoDB

### Check stored messages

```bash
# Connect to MongoDB
mongosh "mongodb://admin:password@localhost:27017/whatsapp_nlp_bot"

# View all messages
db.messages.find().pretty()

# View user messages only
db.messages.find({"sender": "user"}).pretty()

# View messages with analysis
db.messages.find({"sender": "user"}, {text: 1, sentiment: 1, intent: 1}).pretty()

# View conversations
db.conversations.find().pretty()
```

---

## Troubleshooting

### Issue: "Webhook not responding" error

**Solution:**
1. Make sure backend is running: `Uvicorn running on http://0.0.0.0:8000`
2. Check ngrok tunnel is active
3. Verify URL format: `https://abc123.ngrok.io/api/messages/webhook`

### Issue: Messages not storing in MongoDB

**Solution:**
1. Check MongoDB is running: `docker ps`
2. View backend logs for errors
3. Verify `MONGO_URL` environment variable

### Issue: Bot not responding

**Solution:**
1. Check webhook URL in Twilio console
2. Test webhook manually: 
   ```bash
   curl -X POST https://your-ngrok-url.ngrok.io/api/messages/webhook \
     -H "Content-Type: application/json" \
     -d '{"From": "whatsapp:+1234567890", "Body": "Hi", "MessageSid": "TEST"}'
   ```

### Issue: ngrok URL expires

ngrok free tier URLs expire every 2 hours. 

**Solutions:**
- Get ngrok static URL (paid)
- Use ngrok command with specific settings
- Deploy to production server with permanent URL

---

## API Endpoints Available

### Webhook (Twilio sends messages here)
```
POST /api/messages/webhook
```

### Manual Testing (without Twilio)
```
POST /api/messages/analyze
```

Example:
```bash
curl -X POST http://localhost:8000/api/messages/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "text": "I have a problem with my order",
    "sender": "user"
  }'
```

### Get Conversations
```
GET /api/conversations
GET /api/conversations/{phone_number}
GET /api/conversations/{phone_number}/analytics
```

### Dashboard Stats
```
GET /api/dashboard/stats
```

---

## Summary

To get messages flowing through your NLP system:

1. ✅ **Backend running**: `http://localhost:8000`
2. ✅ **MongoDB connected**: Stores all data
3. ⏳ **Configure Twilio Webhook**: Point to your backend
4. ⏳ **Test with WhatsApp**: Send a message
5. ⏳ **Verify in MongoDB**: Check stored message

Once webhook is configured, every message will be:
- Received from Twilio
- Analyzed (sentiment, intent, entities)
- Stored in MongoDB
- Response generated and sent back
- All tracked in database

---

## Quick Setup Commands

```bash
# Terminal 1: Start backend (already running)
cd backend
..\venv\Scripts\python -m uvicorn main:app --reload

# Terminal 2: Start ngrok tunnel
ngrok http 8000

# Terminal 3: Monitor MongoDB
mongosh "mongodb://admin:password@localhost:27017/whatsapp_nlp_bot"
db.messages.find().watch()
```

Now send a WhatsApp message and watch the data flow through the system!
