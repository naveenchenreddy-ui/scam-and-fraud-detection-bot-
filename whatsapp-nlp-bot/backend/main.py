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
import joblib
import uvicorn
try:
    from mysql.connector import pooling
except Exception:  # pragma: no cover - import guard for environments without MySQL driver
    pooling = None

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "whatsapp_nlp_bot")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "hi")
MODEL_PATH = os.getenv(
    "MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "fraud_phishing_nlp_model.pkl"),
)
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

class MySQLDatabase:
    """Small repository for the conversation and message tables."""

    def __init__(self):
        self.pool = None
        if pooling is None:
            logger.warning("mysql-connector-python is not available")
            return
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="whatsapp_nlp_pool", pool_size=5,
                host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
            )
            self._create_tables()
            logger.info("Connected to MySQL")
        except Exception as exc:
            logger.warning(f"MySQL connection error: {exc}")
            self.pool = None

    def _connection(self):
        if self.pool is None:
            raise RuntimeError("MySQL is not connected")
        return self.pool.get_connection()

    def _create_tables(self):
        connection = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(64) NOT NULL UNIQUE,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    message_count INT NOT NULL DEFAULT 0,
                    preferred_language VARCHAR(8) NULL,
                    sentiment_count JSON NULL,
                    intent_count JSON NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(64) NOT NULL,
                    text TEXT NOT NULL,
                    sender VARCHAR(16) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    sentiment VARCHAR(32) NULL,
                    intent VARCHAR(64) NULL,
                    classification JSON NULL,
                    preferred_language VARCHAR(8) NULL,
                    message_sid VARCHAR(128) NULL,
                    status VARCHAR(32) NULL,
                    linked_to_message VARCHAR(64) NULL,
                    entities JSON NULL,
                    sent_at DATETIME NULL,
                    INDEX idx_messages_phone_time (phone_number, timestamp)
                )
            """)
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def _json(value):
        return json.dumps(value) if value is not None else None

    @staticmethod
    def _message_row(row):
        if row is None:
            return None
        row["_id"] = str(row.pop("id"))
        for key in ("classification", "entities"):
            if isinstance(row.get(key), str):
                row[key] = json.loads(row[key])
        return row

    @staticmethod
    def _conversation_row(row):
        if row is None:
            return None
        row["_id"] = str(row.pop("id"))
        for key in ("sentiment_count", "intent_count"):
            if isinstance(row.get(key), str):
                row[key] = json.loads(row[key])
        return row

    def insert_message(self, message):
        values = (
            message.get("phone_number"), message.get("text", ""), message.get("sender"),
            message.get("timestamp") or datetime.now(), message.get("sentiment"),
            message.get("intent"), self._json(message.get("classification")),
            message.get("preferred_language"), message.get("message_sid"),
            message.get("status"), message.get("linked_to_message"), self._json(message.get("entities")),
        )
        connection = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO messages
                (phone_number, text, sender, timestamp, sentiment, intent, classification,
                 preferred_language, message_sid, status, linked_to_message, entities)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, values)
            connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            connection.close()

    def update_message_status(self, message_id, status, sent_at):
        connection = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute("UPDATE messages SET status = %s, sent_at = %s WHERE id = %s", (status, sent_at, message_id))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def get_language(self, phone_number):
        connection = self._connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT preferred_language FROM conversations WHERE phone_number = %s", (phone_number,))
            row = cursor.fetchone()
            return row["preferred_language"] if row else None
        finally:
            cursor.close()
            connection.close()

    def save_language(self, phone_number, language):
        now = datetime.now()
        connection = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO conversations (phone_number, created_at, updated_at, status, preferred_language)
                VALUES (%s, %s, %s, 'active', %s)
                ON DUPLICATE KEY UPDATE preferred_language = VALUES(preferred_language), updated_at = VALUES(updated_at)
            """, (phone_number, now, now, language))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def list_conversations(self, skip, limit):
        connection = self._connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC LIMIT %s OFFSET %s", (limit, skip))
            rows = [self._conversation_row(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) AS total FROM conversations")
            return rows, cursor.fetchone()["total"]
        finally:
            cursor.close()
            connection.close()

    def get_conversation(self, phone_number):
        connection = self._connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM conversations WHERE phone_number = %s", (phone_number,))
            conversation = self._conversation_row(cursor.fetchone())
            cursor.execute("SELECT * FROM messages WHERE phone_number = %s ORDER BY timestamp ASC, id ASC", (phone_number,))
            messages = [self._message_row(row) for row in cursor.fetchall()]
            return conversation, messages
        finally:
            cursor.close()
            connection.close()

    def get_messages(self, phone_number, skip, limit):
        connection = self._connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM messages WHERE phone_number = %s ORDER BY timestamp DESC, id DESC LIMIT %s OFFSET %s", (phone_number, limit, skip))
            messages = [self._message_row(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) AS total FROM messages WHERE phone_number = %s", (phone_number,))
            return messages, cursor.fetchone()["total"]
        finally:
            cursor.close()
            connection.close()

    def stats(self):
        connection = self._connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COUNT(*) AS total FROM conversations")
            total_conversations = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM messages")
            total_messages = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM conversations WHERE status = 'active'")
            active_conversations = cursor.fetchone()["total"]
            cursor.execute("SELECT sentiment, COUNT(*) AS count FROM messages WHERE sender = 'user' AND sentiment IS NOT NULL GROUP BY sentiment")
            sentiment_distribution = {row["sentiment"]: row["count"] for row in cursor.fetchall()}
            cursor.execute("SELECT intent, COUNT(*) AS count FROM messages WHERE sender = 'user' AND intent IS NOT NULL GROUP BY intent")
            intent_distribution = {row["intent"]: row["count"] for row in cursor.fetchall()}
            return total_conversations, total_messages, active_conversations, sentiment_distribution, intent_distribution
        finally:
            cursor.close()
            connection.close()

    def update_conversation(self, phone_number, sentiment=None, intent=None):
        now = datetime.now()
        connection = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO conversations (phone_number, created_at, updated_at, status, message_count)
                VALUES (%s, %s, %s, 'active', 1)
                ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at), message_count = message_count + 1
            """, (phone_number, now, now))
            connection.commit()
        finally:
            cursor.close()
            connection.close()


database = MySQLDatabase()

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

trained_model = None
try:
    trained_model = joblib.load(MODEL_PATH)
    logger.info(f"Loaded fraud detection model from {MODEL_PATH}")
except Exception as exc:
    logger.warning(f"Fraud detection model is unavailable: {exc}")


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


# ------------------------------------------------------------------
# NLP / message analysis
#
# All message classification now goes through the trained TF-IDF +
# Logistic Regression model (see fraud_phishing_nlp_model.pkl, trained
# in the companion notebook). The previous keyword/regex heuristics
# have been removed in favor of this single model-based analysis path.
# ------------------------------------------------------------------

def analyze_with_trained_model(text: str) -> Dict:
    """Classify text with the TF-IDF and Logistic Regression model.

    Returns: {
        "category": "fraud" | "legitimate",
        "confidence": float,
        "class_probabilities": {label: probability, ...},
        "method": "tfidf_logistic_regression",
    }
    """
    if trained_model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Trained fraud model not found at {MODEL_PATH}. "
                "Copy fraud_phishing_nlp_model.pkl into backend/ first."
            ),
        )

    prediction = str(trained_model.predict([text])[0]).lower()
    probabilities = trained_model.predict_proba([text])[0]
    class_probabilities = {
        str(label): round(float(probability), 4)
        for label, probability in zip(trained_model.classes_, probabilities)
    }
    confidence = max(class_probabilities.values())

    return {
        "category": prediction,
        "confidence": confidence,
        "class_probabilities": class_probabilities,
        "method": "tfidf_logistic_regression",
    }


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
    """Read the language preference for a user from MySQL if available."""
    try:
        if database.pool is None:
            return None
        normalized_phone = normalize_phone_number(phone_number)
        language = database.get_language(normalized_phone)
        if not language:
            return None
        return normalize_language(language)
    except Exception:
        return None


def save_user_language(phone_number: str, language: str):
    """Persist the selected language for the user."""
    try:
        if database.pool is None:
            return
        normalized_phone = normalize_phone_number(phone_number)
        database.save_language(normalized_phone, normalize_language(language))
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
    """Return a simple user-friendly response in the selected language.

    `category` is the label returned by the trained model ("fraud" or
    "legitimate"); it is mapped onto the "safe" / "fraud" response
    templates below.
    """
    lang = normalize_language(language)
    category = str(category or "legitimate").lower()
    if category == "legitimate":
        category = "safe"
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


def generate_bot_response(user_message: str, sentiment: str, intent: str, locale: str = "en", category: str = "legitimate") -> str:
    """Minimal response generator for the WhatsApp app.

    `category` comes straight from analyze_with_trained_model() ("fraud"
    or "legitimate").
    """
    if category == "fraud":
        return build_localized_response("fraud", locale)

    if intent == "greeting":
        return "Hello! How can I help?" if locale == "en" else "नमस्कार! मैं आपकी मदद कैसे कर सकता हूँ?" if locale == "hi" else "హలో! నేను ఎలా సహాయం చేయగలను?"
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
        "mysql": "connected" if database.pool else "disconnected",
        "twilio": "configured" if twilio_client else "not configured"
    }


@app.post("/api/messages/send")
async def send_message(message: Message, background_tasks: BackgroundTasks):
    """Send a message via WhatsApp"""
    try:
        message.timestamp = datetime.now()
        message_dict = message.dict()
        message_id = database.insert_message(message_dict)
        
        # Send via Twilio (non-blocking)
        background_tasks.add_task(
            send_whatsapp_message,
            message.phone_number,
            message.text
        )
        
        return {
            "success": True,
            "message_id": str(message_id),
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
            language_prompt = get_language_prompt()
            background_tasks.add_task(send_whatsapp_message, phone_number, language_prompt)
            return {
                "success": True,
                "message": "Language selection required",
                "language_prompt": language_prompt,
            }

        locale = saved_language
        sentiment = None
        intent = "fraud_detection"
        classification = analyze_with_trained_model(user_message)
        category = classification.get("category", "legitimate")

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
        incoming_message_id = database.insert_message(incoming_msg)

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
            "linked_to_message": str(incoming_message_id),
        }
        database.insert_message(bot_msg)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/conversations")
async def get_conversations(skip: int = 0, limit: int = 10):
    """Get all conversations"""
    try:
        conversations, total = database.list_conversations(skip, limit)
        
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
        conversation, messages = database.get_conversation(phone_number)
        
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
        messages, total = database.get_messages(phone_number, skip, limit)
        
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
        total_conversations, total_messages, active_conversations, sentiment_distribution, intent_distribution = database.stats()
        
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
        _, messages = database.get_conversation(phone_number)
        
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
        classification = analyze_with_trained_model(message.text)
        locale = normalize_language(os.getenv("DEFAULT_LOCALE", "hi"))

        return {
            "success": True,
            "analysis": {
                "text": message.text,
                "intent": "fraud_detection",
                "classification": classification,
                "localized_response": build_localized_response(classification.get("category", "legitimate"), locale),
            }
        }
    except HTTPException:
        raise
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
            database.update_message_status(message_id, "sent", datetime.now())

        logger.info(f"WhatsApp message sent to {phone_number}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")


def update_conversation(phone_number: str, sentiment: str = None, intent: str = None):
    """Update conversation timestamp and statistics"""
    try:
        database.update_conversation(phone_number, sentiment, intent)
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )