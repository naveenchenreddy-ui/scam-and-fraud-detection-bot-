from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from urllib.parse import parse_qs
from twilio.rest import Client
from textblob import TextBlob
import uvicorn
import re
from collections import Counter

try:
    from pymongo import MongoClient
except Exception as exc:  # pragma: no cover - import guard for environments without MongoDB driver
    MongoClient = None

load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="WhatsApp NLP Bot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
mongo_client = None
db = None
conversations_collection = None
messages_collection = None

try:
    if MongoClient is not None:
        mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        mongo_client.admin.command("ping")
        db = mongo_client["whatsapp_nlp_bot"]
        conversations_collection = db["conversations"]
        messages_collection = db["messages"]
        logger.info("Connected to MongoDB")
    else:
        raise RuntimeError("pymongo is not available")
except Exception as e:
    logger.warning(f"MongoDB connection error: {e}")

# Twilio client
twilio_client = None
try:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialized")
        logger.info(f"TWILIO_WHATSAPP_NUMBER={TWILIO_WHATSAPP_NUMBER}")
    else:
        logger.warning("Twilio credentials are missing in environment")
except Exception as e:
    logger.warning(f"Twilio initialization error: {e}")


# Pydantic models
class Message(BaseModel):
    phone_number: str
    text: str
    sender: str  # "user" or "bot"
    timestamp: Optional[datetime] = None
    sentiment: Optional[str] = None


class Conversation(BaseModel):
    phone_number: str
    messages: List[Message] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "active"


class WhatsAppWebhook(BaseModel):
    From: str
    Body: str
    MessageSid: str


class DashboardStats(BaseModel):
    total_conversations: int
    total_messages: int
    active_conversations: int
    sentiment_distribution: dict


# NLP Functions
def analyze_sentiment(text: str) -> str:
    """Analyze sentiment using TextBlob with a lightweight fallback."""
    if not text:
        return "neutral"

    try:
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
    except Exception:
        text_lower = text.lower()
        positive_words = ["love", "great", "good", "happy", "thanks", "thank", "excellent", "awesome"]
        negative_words = ["bad", "terrible", "hate", "angry", "sad", "issue", "problem"]
        positive_hits = sum(1 for word in positive_words if word in text_lower)
        negative_hits = sum(1 for word in negative_words if word in text_lower)
        if positive_hits > negative_hits:
            return "positive"
        if negative_hits > positive_hits:
            return "negative"
        return "neutral"

    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"


def detect_scam(text: str) -> Dict:
    """Detect possible scam indicators in a text.

    Returns a dict: {"is_scam": bool, "reasons": List[str], "urls": List[str]}
    """
    if not text:
        return {"is_scam": False, "reasons": [], "urls": []}

    reasons = []
    urls = re.findall(r'http[s]?://\S+', text)

    # Common URL shorteners or suspicious domains
    shorteners = ["bit.ly", "t.co", "tinyurl", "goo.gl", "onelink.me", "ow.ly"]
    for u in urls:
        hostname = re.sub(r'https?://', '', u).split('/')[0].lower()
        if any(s in hostname for s in shorteners):
            reasons.append("shortened_link")
        if re.search(r'onelink|short|click|verify|login', u.lower()):
            reasons.append("suspicious_link")

    # Suspicious language often used in scams
    suspicious_words = [
        "urgent", "immediately", "verify", "click", "login", "account",
        "suspend", "password", "prize", "congratulations", "winner", "claim"
    ]
    if any(w in text.lower() for w in suspicious_words):
        reasons.append("suspicious_language")

    # Presence of extremely short or encoded tokens (e.g., many punctuation characters)
    if re.search(r'\b\w{1,2}:[0-9a-f]{6,}\b', text.lower()):
        reasons.append("encoded_token")

    is_scam = len(reasons) > 0
    return {"is_scam": is_scam, "reasons": list(dict.fromkeys(reasons)), "urls": urls}


def classify_message(text: str) -> Dict:
    """Classify message into categories: scam, phishing, fake_news, safe.

    Returns: {"category": str, "confidence": float, "reasons": List[str]}
    """
    reasons = []
    text_lower = (text or "").lower()

    # Run scam detector
    scam_info = detect_scam(text)
    if scam_info.get("is_scam"):
        reasons.extend(scam_info.get("reasons", []))

    # Phishing heuristics: requests for credentials, password reset prompts, login links
    phishing_indicators = ["verify your account", "login", "password", "reset your password", "enter your", "one-time passcode", "otp", "ssn", "account suspended"]
    if any(p in text_lower for p in phishing_indicators):
        reasons.append("phishing_language")

    # Fake news heuristics: sensational phrases, all caps, 'breaking', 'unbelievable', 'viral'
    fake_news_indicators = ["breaking", "unbelievable", "shocking", "viral", "confirmed", "sources say", "exclusive"]
    if any(f in text_lower for f in fake_news_indicators) or (sum(1 for c in text if c.isupper()) > max(10, len(text) * 0.2)):
        reasons.append("fake_news_language")

    # Decide category
    category = "safe"
    confidence = 0.0

    if "phishing_language" in reasons:
        category = "phishing"
        confidence = 0.85
    elif scam_info.get("is_scam"):
        category = "scam"
        confidence = 0.8
    elif "fake_news_language" in reasons:
        category = "fake_news"
        confidence = 0.7
    else:
        category = "safe"
        confidence = 0.5

    # refine confidence based on number of reasons
    confidence = min(0.99, confidence + 0.05 * max(0, len(reasons) - 1))

    return {"category": category, "confidence": round(confidence, 2), "reasons": list(dict.fromkeys(reasons))}


def detect_threat_type(text: str) -> str:
    """Classify the message into one of: scam, phishing, fake_news, safe.

    Uses simple heuristics: relies on `detect_scam` and keyword patterns.
    """
    text_lower = text.lower() if text else ""

    # Check for phishing: credential requests + link or urgent action
    phishing_keywords = ["password", "login", "verify", "credentials", "ssn", "bank", "account", "card"]
    has_phishing_kw = any(k in text_lower for k in phishing_keywords)
    has_link = bool(re.search(r'http[s]?://', text_lower))
    if has_phishing_kw and has_link:
        return "phishing"

    # Check scam using existing detector
    try:
        scam_info = detect_scam(text)
        if scam_info.get("is_scam"):
            return "scam"
    except Exception:
        pass

    # Fake news heuristic: sensational phrases, many exclamation marks, ALL CAPS claims
    fake_keywords = ["breaking", "exclusive", "shocking", "rumor", "viral", "unbelievable"]
    if any(k in text_lower for k in fake_keywords) or text.count("!") >= 3 or re.search(r'\b[A-Z]{6,}\b', text):
        return "fake_news"

    return "safe"


def detect_intent(text: str) -> str:
    """Detect user intent from message."""
    text_lower = text.lower()

    # If scam indicators are present, prefer scam_report intent
    try:
        scam_info = detect_scam(text)
        if scam_info.get("is_scam"):
            return "scam_report"
    except Exception:
        pass

    intent_patterns = {
        "greeting": ["hello", "hi", "hey", "greetings", "hiya", "sup"],
        "help": ["help", "support", "assist", "issue", "problem", "error", "bug"],
        "scam_report": ["scam", "phish", "phishing", "fraud", "suspicious", "scammer", "suspicious link", "report scam", "detect scam"],
        "gratitude": ["thank", "thanks", "appreciate", "appreciate", "grateful"],
        "farewell": ["bye", "goodbye", "see you", "later", "exit"],
        "product_inquiry": ["product", "price", "cost", "feature", "how much", "what's the price"],
        "account": ["account", "login", "password", "reset", "profile"],
        "billing": ["bill", "invoice", "payment", "charge", "refund", "cancel"],
        "feedback": ["feedback", "review", "rating", "suggestion", "complaint"]
    }
    
    for intent, keywords in intent_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            return intent
    
    return "general_inquiry"


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities and important terms from text."""
    entities = {
        "numbers": re.findall(r'\d+', text),
        "emails": re.findall(r'[\w\.-]+@[\w\.-]+', text),
        "urls": re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text),
        "keywords": extract_keywords(text)
    }
    try:
        entities["scam"] = detect_scam(text)
    except Exception:
        entities["scam"] = {"is_scam": False, "reasons": [], "urls": []}
    return entities


def extract_keywords(text: str) -> List[str]:
    """Extract important keywords from text."""
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "can", "i", "you", "he", "she", "it", "we", "they", "what", "which",
        "who", "when", "where", "why", "how", "this", "that", "these", "those"
    }
    
    words = text.lower().split()
    keywords = [word.strip('.,!?;:') for word in words 
                if word.lower().strip('.,!?;:') not in stop_words 
                and len(word.strip('.,!?;:')) > 3]
    
    return keywords[:5]  # Return top 5 keywords


def generate_bot_response(user_message: str, sentiment: str, intent: str) -> str:
    """Generate bot response based on sentiment, intent and message."""
    message_lower = user_message.lower()
    
    # Intent-based responses
    if intent == "greeting":
        return "👋 Hello! How can I help you today?"
    elif intent == "help":
        return "🆘 I'm here to help! Can you describe the issue in detail?"
    elif intent == "gratitude":
        return "😊 You're welcome! Happy to assist!"
    elif intent == "farewell":
        return "👋 Goodbye! Feel free to reach out anytime!"
    elif intent == "product_inquiry":
        return "📦 Great question! I'd be happy to tell you more about our products. What would you like to know?"
    elif intent == "account":
        return "🔐 For account-related inquiries, please visit our account settings or contact support."
    elif intent == "billing":
        return "💳 For billing inquiries, please provide more details so I can assist you better."
    elif intent == "feedback":
        return "⭐ Thank you for your feedback! We appreciate your input."
    elif intent == "scam_report":
        return "⚠️ It looks like you're reporting a scam. Please share the suspicious message or link so I can analyze it for common scam indicators (shortened links, mismatched domains, urgent requests)."
    
    # Sentiment-based responses
    if sentiment == "negative":
        return "😟 I'm sorry to hear that. Let me help you resolve this issue. Can you provide more details?"
    elif sentiment == "positive":
        return "😄 Great! I'm glad I could help! Is there anything else I can assist you with?"
    
    return "Got it! I'm processing your request. How else can I assist?"


# API Endpoints

@app.get("/")
async def root():
    return {
        "message": "WhatsApp NLP Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/")
async def root_post():
    return {
        "message": "WhatsApp NLP Bot API received POST",
        "status": "ok"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mongodb": "connected" if mongo_client else "disconnected",
        "twilio": "configured" if twilio_client else "not configured"
    }


@app.post("/api/messages/send")
async def send_message(message: Message, background_tasks: BackgroundTasks):
    """Send a message via WhatsApp"""
    try:
        # Store message in MongoDB
        message.timestamp = datetime.now()
        message_dict = message.dict()
        result = messages_collection.insert_one(message_dict)
        
        # Send via Twilio (non-blocking)
        background_tasks.add_task(
            send_whatsapp_message,
            message.phone_number,
            message.text
        )
        
        return {
            "success": True,
            "message_id": str(result.inserted_id),
            "timestamp": message.timestamp
        }
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp messages with NLP analysis"""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            body_bytes = await request.body()
            form = parse_qs(body_bytes.decode("utf-8"))
            from_value = form.get("From", [None])[0]
            body_value = form.get("Body", [None])[0]
            message_sid = form.get("MessageSid", [None])[0]
        else:
            payload = await request.json()
            from_value = payload.get("From")
            body_value = payload.get("Body")
            message_sid = payload.get("MessageSid")

        if not from_value or not body_value:
            raise HTTPException(status_code=400, detail="Missing From or Body in webhook request")

        phone_number = from_value.replace("whatsapp:", "")
        user_message = body_value
        
        # Enhanced NLP Analysis
        sentiment = analyze_sentiment(user_message)
        intent = detect_intent(user_message)
        entities = extract_entities(user_message)
        classification = classify_message(user_message)
        
        # Store incoming message with full analysis
        incoming_msg = {
            "phone_number": phone_number,
            "text": user_message,
            "sender": "user",
            "sentiment": sentiment,
            "intent": intent,
            "entities": entities,
            "classification": classification,
            "timestamp": datetime.now(),
            "message_sid": message_sid,
            "status": "processed"
        }
        incoming_result = messages_collection.insert_one(incoming_msg)
        logger.info(f"Stored user message: {incoming_result.inserted_id}")
        
        # Generate response based on analysis
        bot_response = generate_bot_response(user_message, sentiment, intent)

        # If scam detected, generate a detailed actionable report for the user
        try:
            scam_info = entities.get("scam", {})
            if scam_info and scam_info.get("is_scam"):
                reasons = scam_info.get("reasons", [])
                urls = scam_info.get("urls", [])
                reasons_readable = ", ".join(reasons) if reasons else "unspecified indicators"
                urls_readable = "\n".join(urls) if urls else "(no URLs found)"
                bot_response = (
                    "⚠️ I detected possible scam indicators in that message.\n\n"
                    f"Reasons: {reasons_readable}.\n"
                    f"Suspicious URLs:\n{urls_readable}\n\n"
                    "Advice: Do NOT click these links. Verify the sender via official channels, avoid sharing personal info, and report the message to your provider."
                )
                # Prepend a short classification verdict for clarity in WhatsApp
                try:
                    verdict = classification.get("category", "unknown").upper()
                    confidence = classification.get("confidence", 0)
                    bot_response = f"[Verdict: {verdict} — {int(confidence*100)}%]\n\n" + bot_response
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error building scam response: {e}")
        
        # Store bot response
        bot_msg = {
            "phone_number": phone_number,
            "text": bot_response,
            "sender": "bot",
            "sentiment": "neutral",
            "intent": "response",
            "classification": classification,
            "timestamp": datetime.now(),
            "status": "pending",
            "linked_to_message": str(incoming_result.inserted_id)
        }
        bot_result = messages_collection.insert_one(bot_msg)
        logger.info(f"Stored bot response: {bot_result.inserted_id}")
        
        # Send response via Twilio
        background_tasks.add_task(
            send_whatsapp_message,
            phone_number,
            bot_response,
            str(bot_result.inserted_id)
        )
        
        # Update conversation
        update_conversation(phone_number, sentiment, intent)
        
        return {
            "success": True,
            "message": "Webhook processed",
            "analysis": {
                "sentiment": sentiment,
                "intent": intent,
                "classification": classification,
                "entities_found": len(entities.get("keywords", []))
            }
        }
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/conversations")
async def get_conversations(skip: int = 0, limit: int = 10):
    """Get all conversations"""
    try:
        conversations = list(
            conversations_collection.find()
            .skip(skip)
            .limit(limit)
            .sort("updated_at", -1)
        )
        
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
        
        total = conversations_collection.count_documents({})
        
        return {
            "success": True,
            "total": total,
            "data": conversations
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{phone_number}")
async def get_conversation(phone_number: str):
    """Get specific conversation"""
    try:
        # Get conversation
        conversation = conversations_collection.find_one(
            {"phone_number": phone_number}
        )
        
        # Get messages
        messages = list(
            messages_collection.find(
                {"phone_number": phone_number}
            ).sort("timestamp", 1)
        )
        
        if conversation:
            conversation["_id"] = str(conversation["_id"])
        
        for msg in messages:
            msg["_id"] = str(msg["_id"])
            msg["timestamp"] = msg["timestamp"].isoformat()
        
        return {
            "success": True,
            "conversation": conversation,
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages/{phone_number}")
async def get_messages(phone_number: str, skip: int = 0, limit: int = 50):
    """Get messages for a conversation"""
    try:
        messages = list(
            messages_collection.find(
                {"phone_number": phone_number}
            )
            .skip(skip)
            .limit(limit)
            .sort("timestamp", -1)
        )
        
        for msg in messages:
            msg["_id"] = str(msg["_id"])
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        total = messages_collection.count_documents({"phone_number": phone_number})
        
        return {
            "success": True,
            "total": total,
            "data": messages
        }
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        total_conversations = conversations_collection.count_documents({})
        total_messages = messages_collection.count_documents({})
        active_conversations = conversations_collection.count_documents(
            {"status": "active"}
        )
        
        # Sentiment distribution
        sentiment_pipeline = [
            {"$match": {"sender": "user"}},
            {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}}}
        ]
        sentiment_data = list(messages_collection.aggregate(sentiment_pipeline))
        sentiment_distribution = {
            item["_id"]: item["count"] for item in sentiment_data
        }
        
        # Intent distribution
        intent_pipeline = [
            {"$match": {"sender": "user"}},
            {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None}}}
        ]
        intent_data = list(messages_collection.aggregate(intent_pipeline))
        intent_distribution = {
            item["_id"]: item["count"] for item in intent_data
        }
        
        return {
            "success": True,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_conversations": active_conversations,
            "sentiment_distribution": sentiment_distribution,
            "intent_distribution": intent_distribution
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{phone_number}/analytics")
async def get_conversation_analytics(phone_number: str):
    """Get detailed analytics for a conversation"""
    try:
        # Get all messages
        messages = list(
            messages_collection.find(
                {"phone_number": phone_number}
            ).sort("timestamp", 1)
        )
        
        # Calculate statistics
        user_messages = [m for m in messages if m.get("sender") == "user"]
        bot_messages = [m for m in messages if m.get("sender") == "bot"]
        
        # Sentiment analysis
        sentiment_counts = {}
        intent_counts = {}
        
        for msg in user_messages:
            sentiment = msg.get("sentiment", "neutral")
            intent = msg.get("intent", "unknown")
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Calculate response time average
        response_times = []
        for i in range(len(user_messages)):
            if i < len(bot_messages):
                user_msg_time = user_messages[i].get("timestamp")
                bot_msg_time = bot_messages[i].get("timestamp")
                if user_msg_time and bot_msg_time:
                    diff = (bot_msg_time - user_msg_time).total_seconds()
                    response_times.append(diff)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "success": True,
            "phone_number": phone_number,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "bot_messages": len(bot_messages),
            "sentiment_breakdown": sentiment_counts,
            "intent_breakdown": intent_counts,
            "avg_response_time_seconds": round(avg_response_time, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/analyze")
async def analyze_message(message: Message):
    """Analyze a message without storing it"""
    try:
        sentiment = analyze_sentiment(message.text)
        intent = detect_intent(message.text)
        entities = extract_entities(message.text)
        # Include scam analysis and full classification
        scam_info = detect_scam(message.text)
        entities["scam"] = scam_info
        classification = classify_message(message.text)
        
        return {
            "success": True,
            "analysis": {
                "text": message.text,
                "sentiment": sentiment,
                "intent": intent,
                "entities": entities,
                "classification": classification
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Helper functions
def send_whatsapp_message(phone_number: str, message: str, message_id: str = None):
    """Send WhatsApp message via Twilio"""
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
            logger.error("Twilio credentials are not fully configured. Check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_NUMBER.")
            return

        if twilio_client is None:
            logger.error("Twilio client is not initialized. Check credentials and startup logs.")
            return

        from_address = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
        to_address = f"whatsapp:{phone_number}"
        logger.info(f"Sending WhatsApp message from {from_address} to {to_address}")

        try:
            twilio_client.messages.create(
                from_=from_address,
                to=to_address,
                body=message
            )
        except Exception as send_exc:
            logger.error(f"Twilio send failed from {from_address} to {to_address}: {send_exc}")
            return

        if message_id:
            try:
                from bson import ObjectId
                query_id = ObjectId(message_id)
            except Exception:
                query_id = message_id

            messages_collection.update_one(
                {"_id": query_id},
                {"$set": {"status": "sent", "sent_at": datetime.now()}}
            )

        logger.info(f"WhatsApp message sent to {phone_number}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")


def update_conversation(phone_number: str, sentiment: str = None, intent: str = None):
    """Update conversation timestamp and statistics"""
    try:
        update_data = {
            "updated_at": datetime.now(),
        }
        
        if sentiment:
            update_data[f"sentiment_count.{sentiment}"] = 1
        
        if intent:
            update_data[f"intent_count.{intent}"] = 1
        
        update_command = {
            "$set": update_data,
            "$inc": {"message_count": 1}
        }

        insert_data = {
            "phone_number": phone_number,
            "created_at": datetime.now(),
            "status": "active"
        }

        if sentiment is None and intent is None:
            update_command["$setOnInsert"] = insert_data
        else:
            update_command["$setOnInsert"] = insert_data

        conversations_collection.update_one(
            {"phone_number": phone_number},
            update_command,
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
