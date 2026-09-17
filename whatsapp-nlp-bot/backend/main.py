
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import logging
import joblib
import uvicorn
from twilio.rest import Client
from urllib.parse import parse_qs

# Load environment
load_dotenv()

# Configuration
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_fraud_detection_model.pkl")
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
if not os.path.exists(MODEL_PATH) and os.path.exists(DEFAULT_MODEL_PATH):
    MODEL_PATH = DEFAULT_MODEL_PATH

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "hi")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="WhatsApp NLP Bot API", version="1.0.0")

# Enable CORS for cloud & local frontend deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversations: Dict[str, List[Dict]] = {}


class SendMessageRequest(BaseModel):
    phone_number: str
    text: str
    sender: str = "user"


@app.get("/")
async def root():
    return {
        "name": "WhatsApp NLP Bot API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }

# ⭐ LOAD TRAINED MODEL
trained_model = None
vectorizer = None
try:
    loaded_data = joblib.load(MODEL_PATH)
    if isinstance(loaded_data, dict):
        trained_model = loaded_data.get("model")
        vectorizer = loaded_data.get("vectorizer")
    else:
        trained_model = loaded_data
    logger.info(f"✓ Loaded fraud detection model from {MODEL_PATH}")
    if trained_model is not None and hasattr(trained_model, "classes_"):
        logger.info(f"✓ Model classes: {trained_model.classes_}")
except Exception as exc:
    logger.error(f"✗ Failed to load model: {exc}")
    logger.warning("Using fallback (all messages marked as legitimate)")

# Twilio client
twilio_client = None
try:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("✓ Twilio client initialized")
except Exception as e:
    logger.error(f"✗ Twilio initialization error: {e}")


# ⭐ CORE: Analyze message with trained model
def analyze_with_trained_model(text: str) -> Dict:
    """
    Classify text using TF-IDF + Logistic Regression model
    
    Returns:
        {
            "category": "fraud" or "legitimate",
            "confidence": 0.0-1.0,
            "probabilities": {"fraud": 0.95, "legitimate": 0.05},
            "model_type": "tfidf_logistic_regression"
        }
    """
    
    if trained_model is None:
        logger.warning("Model unavailable - using fallback")
        return {
            "category": "legitimate",
            "confidence": 0.0,
            "probabilities": {},
            "model_type": "fallback_unavailable",
        }

    try:
        input_data = [text]
        if vectorizer is not None:
            input_data = vectorizer.transform(input_data)

        raw_pred = trained_model.predict(input_data)[0]
        if raw_pred == 1 or str(raw_pred).lower() in ["1", "fraud"]:
            prediction = "fraud"
        else:
            prediction = "legitimate"
        
        prob_dict = {}
        confidence = 0.0
        if hasattr(trained_model, "predict_proba"):
            probabilities = trained_model.predict_proba(input_data)[0]
            for label, prob in zip(trained_model.classes_, probabilities):
                mapped_label = "fraud" if (label == 1 or str(label).lower() in ["1", "fraud"]) else "legitimate"
                prob_dict[mapped_label] = round(float(prob), 4)
            confidence = prob_dict.get(prediction, float(max(probabilities)))
        else:
            confidence = 1.0
            prob_dict = {prediction: 1.0}
        
        logger.info(f"Classification: {prediction} (confidence: {confidence:.2%})")

        return {
            "category": prediction,
            "confidence": confidence,
            "probabilities": prob_dict,
            "model_type": "tfidf_logistic_regression",
        }
    
    except Exception as e:
        logger.error(f"Model prediction error: {e}")
        return {
            "category": "legitimate",
            "confidence": 0.0,
            "probabilities": {},
            "model_type": "error",
        }


# ⭐ Generate response based on model output
def build_response(category: str, language: str) -> str:
    """
    Build localized response based on model classification
    
    Args:
        category: "fraud" or "legitimate" (from model)
        language: "en", "hi", or "te"
    """
    
    category = str(category or "legitimate").lower()
    if category not in ["fraud", "legitimate"]:
        category = "legitimate"
    
    responses = {
        "en": {
            "legitimate": "✅ Message looks safe. Still avoid unknown links & never share OTPs.",
            "fraud": "🚨 FRAUD ALERT! Don't click links, don't share OTPs/passwords, don't send money."
        },
        "hi": {
            "legitimate": "✅ संदेश सुरक्षित है। फिर भी अज्ञात लिंक न खोलें और OTP न दें।",
            "fraud": "🚨 धोखाधड़ी! लिंक न क्लिक करें, OTP न दें, पैसे न भेजें।"
        },
        "te": {
            "legitimate": "✅ సందేశం సురక్షితం. అయినా అనుకోని లింక్ తెరవకండి, OTP ఇవ్వకండి.",
            "fraud": "🚨 మోసం! లింక్ క్లిక్ చేయకండి, OTP ఇవ్వకండి, డబ్బు పంపకండి."
        }
    }
    
    lang = language if language in responses else "en"
    return responses[lang].get(category, responses[lang]["legitimate"])


# ⭐ WhatsApp Webhook - Routes to model
@app.post("/api/messages/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook for incoming WhatsApp messages
    Routes to trained fraud detection model
    """
    
    try:
        # Parse request
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
            raise HTTPException(status_code=400, detail="Missing From or Body")

        phone_number = from_value.replace("whatsapp:", "").strip()
        user_message = body_value.strip()
        
        logger.info(f"Received from {phone_number}: {user_message}")

        # ⭐ ROUTE TO TRAINED MODEL
        classification = analyze_with_trained_model(user_message)
        category = classification["category"]  # "fraud" or "legitimate"
        confidence = classification["confidence"]
        
        # Generate response
        locale = "hi"  # Or get from user preferences
        bot_response = build_response(category, locale)
        
        # Add confidence info if fraud
        if category == "fraud":
            bot_response += f"\n\n(Confidence: {confidence:.0%})"
        
        logger.info(f"Classification: {category} ({confidence:.2%})")
        logger.info(f"Sending response: {bot_response}")

        # Send response
        background_tasks.add_task(send_whatsapp_message, phone_number, bot_response)

        return {
            "success": True,
            "user_message": user_message,
            "analysis": {
                "category": category,
                "confidence": confidence,
                "probabilities": classification.get("probabilities", {}),
                "model": "tfidf_logistic_regression"
            },
            "response": bot_response
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Send WhatsApp message
def send_whatsapp_message(phone_number: str, message: str):
    """Send message via Twilio WhatsApp API"""
    
    try:
        if not twilio_client:
            logger.error("Twilio not configured")
            return
        
        twilio_client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{phone_number}",
            body=message
        )
        
        logger.info(f"✓ Message sent to {phone_number}")
    
    except Exception as e:
        logger.error(f"✗ Failed to send message: {e}")


def record_message(phone_number: str, text: str, sender: str, sentiment: str = "neutral"):
    timestamp = datetime.now()
    messages = conversations.setdefault(phone_number, [])
    messages.append({
        "_id": f"{phone_number}-{len(messages) + 1}",
        "phone_number": phone_number,
        "text": text,
        "sender": sender,
        "sentiment": sentiment,
        "timestamp": timestamp,
    })


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    messages = [message for items in conversations.values() for message in items]
    sentiment_distribution: Dict[str, int] = {}
    for message in messages:
        sentiment = message.get("sentiment", "neutral")
        sentiment_distribution[sentiment] = sentiment_distribution.get(sentiment, 0) + 1

    return {
        "total_conversations": len(conversations),
        "total_messages": len(messages),
        "active_conversations": len(conversations),
        "sentiment_distribution": sentiment_distribution,
    }


@app.get("/api/conversations")
async def get_conversations(skip: int = 0, limit: int = 10):
    items = []
    for phone_number, messages in conversations.items():
        items.append({
            "_id": phone_number,
            "phone_number": phone_number,
            "status": "active",
            "updated_at": messages[-1]["timestamp"] if messages else datetime.now(),
            "messages": messages[-1:],
        })
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"data": items[skip:skip + limit], "total": len(items)}


@app.get("/api/conversations/{phone_number}")
async def get_conversation(phone_number: str):
    if phone_number not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"data": conversations[phone_number]}


@app.get("/api/messages/{phone_number}")
async def get_messages(phone_number: str, skip: int = 0, limit: int = 50):
    messages = conversations.get(phone_number, [])
    return {"data": messages[skip:skip + limit], "total": len(messages)}


@app.post("/api/messages/send")
async def send_message(message: SendMessageRequest, background_tasks: BackgroundTasks):
    phone_number = message.phone_number.strip()
    text = message.text.strip()
    if not phone_number or not text:
        raise HTTPException(status_code=400, detail="phone_number and text are required")

    record_message(phone_number, text, message.sender)
    background_tasks.add_task(send_whatsapp_message, phone_number, text)
    return {"success": True, "message": conversations[phone_number][-1]}


# Health check
@app.get("/health")
async def health_check():
    model_status = "loaded" if trained_model else "not loaded"
    twilio_status = "configured" if twilio_client else "not configured"
    
    return {
        "status": "healthy",
        "model": model_status,
        "twilio": twilio_status,
        "timestamp": datetime.now().isoformat()
    }


# Test endpoint
@app.post("/api/test/classify")
async def test_classify(text: str):
    """Test endpoint to classify a message"""
    
    classification = analyze_with_trained_model(text)
    response = build_response(classification["category"], "en")
    
    return {
        "text": text,
        "classification": classification,
        "response": response
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)