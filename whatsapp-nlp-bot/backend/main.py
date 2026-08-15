from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import logging
from urllib.parse import parse_qs
from twilio.rest import Client
from textblob import TextBlob
import uvicorn
import re
from urllib.request import Request as UrlRequest, urlopen

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
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "hi")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "facebook/bart-large-mnli")
HF_BASE_URL = os.getenv("HF_BASE_URL", "https://api-inference.huggingface.co/models")
LANGUAGE_OPTIONS = {
    "1": "en",
    "2": "hi",
    "3": "te",
    "en": "en",
    "hi": "hi",
    "te": "te",
    "english": "en",
    "hindi": "hi",
    "hindhi": "hi",
    "हिंदी": "hi",
    "हिन्दी": "hi",
    "telugu": "te",
    "తెలుగు": "te",
}

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


def call_huggingface_api(text: str) -> Dict:
    """Call the Hugging Face inference API for scam classification."""
    if not HF_TOKEN:
        return {"category": "safe", "confidence": 0.4, "reasons": ["no_model_configured"]}

    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": ["safe", "suspicious", "fraud"]},
    }

    try:
        request = UrlRequest(
            f"{HF_BASE_URL}/{HF_MODEL}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

        labels = result.get("labels", [])
        scores = result.get("scores", [])
        if labels and scores:
            best_index = max(range(len(scores)), key=lambda i: scores[i])
            return {
                "category": labels[best_index],
                "confidence": round(float(scores[best_index]), 2),
                "reasons": ["huggingface_classification"],
            }
    except Exception as exc:
        logger.warning(f"Hugging Face API failed: {exc}")

    return {"category": "safe", "confidence": 0.4, "reasons": ["fallback_logic"]}


def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone numbers so the same user always maps to one stored preference."""
    if not phone_number:
        return ""
    value = str(phone_number).strip()
    value = value.replace("whatsapp:", "").replace(" ", "")
    if value.startswith("+"):
        value = value[1:]
    return value


def normalize_language(value: str) -> str:
    """Normalize language input to en/hi/te."""
    if not value:
        return DEFAULT_LOCALE
    key = str(value).strip().lower()
    if key in LANGUAGE_OPTIONS:
        return LANGUAGE_OPTIONS[key]
    if key in {"telugu", "తెలుగు"}:
        return "te"
    if key in {"hindi", "hindhi", "हिंदी", "हिन्दी"}:
        return "hi"
    if key in {"english"}:
        return "en"
    return DEFAULT_LOCALE


def detect_language_selection(text: str) -> Optional[str]:
    """Detect whether the user explicitly chose a language from the menu."""
    if not text:
        return None

    value = str(text).strip().lower().replace(".", "").strip()
    if value in {"1", "2", "3"}:
        return LANGUAGE_OPTIONS[value]

    # Only accept explicit language names; ignore greetings or message content.
    if value in {"english", "hindi", "hindhi", "telugu", "हिंदी", "हिन्दी", "తెలుగు"}:
        return LANGUAGE_OPTIONS.get(value)

    # Support common writing variations from WhatsApp users.
    aliases = {
        "hi": None,
        "hello": None,
        "hey": None,
        "tel": None,
        "te": None,
    }
    if value in aliases:
        return None

    return None


def get_user_language(phone_number: str) -> Optional[str]:
    """Read the language preference for a user from MongoDB if available."""
    try:
        if conversations_collection is None:
            return None
        normalized_phone = normalize_phone_number(phone_number)
        record = conversations_collection.find_one({"phone_number": normalized_phone})
        if not record:
            return None
        return normalize_language(record.get("preferred_language"))
    except Exception:
        return None


def save_user_language(phone_number: str, language: str):
    """Persist the selected language for the user."""
    try:
        if conversations_collection is None:
            return
        normalized_phone = normalize_phone_number(phone_number)
        conversations_collection.update_one(
            {"phone_number": normalized_phone},
            {"$set": {"phone_number": normalized_phone, "preferred_language": normalize_language(language), "updated_at": datetime.now()}},
            upsert=True,
        )
    except Exception as exc:
        logger.warning(f"Could not save language: {exc}")


def get_language_prompt() -> str:
    """Return the language menu shown to a first-time user in all three languages."""
    return (
        "Please choose your language / अपनी भाषा चुनें / మీ భాషను ఎంచుకోండి\n"
        "1. English\n"
        "2. हिन्दी\n"
        "3. తెలుగు\n\n"
        "Reply with 1, 2, or 3."
    )


def build_localized_response(category: str, language: str) -> str:
    """Return a simple user-friendly response in the selected language."""
    lang = normalize_language(language)
    category = str(category or "safe").lower()
    templates = {
        "en": {
            "safe": "✅ Your message looks safe. Please still avoid unknown links and never share OTPs or passwords.",
            "suspicious": "⚠️ This message looks suspicious. Do not click links, do not share OTPs, and verify through official contacts.",
            "fraud": "🚨 This message appears to be a fraud attempt. Do not share personal details, banking information, or OTPs. Contact the official office directly.",
        },
        "hi": {
            "safe": "✅ आपका संदेश सुरक्षित लग रहा है। फिर भी अज्ञात लिंक पर क्लिक न करें और OTP/पासवर्ड कभी न दें।",
            "suspicious": "⚠️ यह संदेश संदिग्ध लगता है। लिंक पर क्लिक न करें, OTP न दें, और आधिकारिक संपर्क से पुष्टि करें।",
            "fraud": "🚨 यह संदेश धोखाधड़ी का प्रयास लग रहा है। अपनी व्यक्तिगत जानकारी, बैंक विवरण या OTP कभी साझा न करें। आधिकारिक कार्यालय से सीधे संपर्क करें।",
        },
        "te": {
            "safe": "✅ మీ సందేశం सुरक्षितంగా కనిపిస్తుంది. అయినా అనుకోని లింక్లపై క్లిక్ చేయకండి మరియు OTP/పాస్వర్డ్ ఇవ్వకండి.",
            "suspicious": "⚠️ ఈ సందేశం sospectionado గా కనిపిస్తోంది. లింక్‌లను నొక్కవద్దు, OTP ఇవ్వవద్దు, మరియు అధికారిక సంప్రదింపులతో ధృవీకరించండి.",
            "fraud": "🚨 ఈ సందేశం మోసం ప్రయత్నంగా కనిపిస్తోంది. వ్యక్తిగత సమాచారం, బ్యాంక్ వివరాలు లేదా OTPలను never పంచుకోండి. అధికారిక కార్యాలయాన్ని సంప్రదించండి.",
        }
    }
    text = templates.get(lang, templates["en"]).get(category, templates.get(lang, templates["en"])["safe"])
    return text


def analyze_with_huggingface(text: str) -> Dict:
    """Classify the message with Hugging Face and fallback to local logic."""
    hf_result = call_huggingface_api(text)
    category = str(hf_result.get("category", "safe")).lower()
    if category not in {"safe", "suspicious", "fraud"}:
        category = "safe"

    if category == "safe" and detect_scam(text).get("is_scam"):
        category = "fraud"

    return {
        "category": category,
        "confidence": float(hf_result.get("confidence", 0.65) or 0.65),
        "reasons": hf_result.get("reasons", ["analysis"]),
        "method": "huggingface",
    }


def generate_bot_response(user_message: str, sentiment: str, intent: str, locale: str = "en", category: str = "safe") -> str:
    """Minimal response generator for the WhatsApp app."""
    if category in {"suspicious", "fraud"}:
        return build_localized_response(category, locale)

    if intent == "greeting":
        return "Hello! How can I help?" if locale == "en" else "नमस्कार! मैं आपकी मदद कैसे कर सकता हूँ?" if locale == "hi" else "హలో! నేను ఎలా సహాయం చేయగలను?"
    if intent == "scam_report":
        return build_localized_response("fraud", locale)
    if sentiment == "negative":
        return "I am here to help." if locale == "en" else "मैं आपकी मदद के लिए यहाँ हूँ।" if locale == "hi" else "నాకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను."
    return build_localized_response("safe", locale)


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

        phone_number = normalize_phone_number(from_value)
        user_message = body_value.strip()

        selected_language = detect_language_selection(user_message)
        if selected_language:
            save_user_language(phone_number, selected_language)
            locale = selected_language
            bot_response = "Language saved. Please send your message now."
            if locale == "hi":
                bot_response = "भाषा सेव हो गई है। अब अपना संदेश भेजें।"
            elif locale == "te":
                bot_response = "భాష సేవ్ అయింది. ఇప్పుడు మీ సందేశాన్ని పంపండి."
            background_tasks.add_task(send_whatsapp_message, phone_number, bot_response)
            return {"success": True, "message": "Language saved"}

        saved_language = get_user_language(phone_number)
        if not saved_language:
            locale = DEFAULT_LOCALE
            bot_response = get_language_prompt()
            background_tasks.add_task(send_whatsapp_message, phone_number, bot_response)
            return {"success": True, "message": "Language selection prompt sent"}

        locale = saved_language
        sentiment = analyze_sentiment(user_message)
        intent = detect_intent(user_message)
        classification = analyze_with_huggingface(user_message)
        category = classification.get("category", "safe")

        incoming_msg = {
            "phone_number": phone_number,
            "text": user_message,
            "sender": "user",
            "sentiment": sentiment,
            "intent": intent,
            "classification": classification,
            "preferred_language": locale,
            "timestamp": datetime.now(),
            "message_sid": message_sid,
            "status": "processed",
        }
        incoming_result = messages_collection.insert_one(incoming_msg)

        bot_response = generate_bot_response(user_message, sentiment, intent, locale=locale, category=category)
        bot_msg = {
            "phone_number": phone_number,
            "text": bot_response,
            "sender": "bot",
            "sentiment": "neutral",
            "intent": "response",
            "classification": classification,
            "preferred_language": locale,
            "timestamp": datetime.now(),
            "status": "pending",
            "linked_to_message": str(incoming_result.inserted_id),
        }
        messages_collection.insert_one(bot_msg)
        background_tasks.add_task(send_whatsapp_message, phone_number, bot_response)

        return {
            "success": True,
            "message": "Webhook processed",
            "analysis": {
                "sentiment": sentiment,
                "intent": intent,
                "language": locale,
                "classification": classification,
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
    """Analyze a message without storing it."""
    try:
        sentiment = analyze_sentiment(message.text)
        intent = detect_intent(message.text)
        classification = analyze_with_huggingface(message.text)
        locale = normalize_language(os.getenv("DEFAULT_LOCALE", "hi"))

        return {
            "success": True,
            "analysis": {
                "text": message.text,
                "sentiment": sentiment,
                "intent": intent,
                "classification": classification,
                "localized_response": build_localized_response(classification.get("category", "safe"), locale),
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
