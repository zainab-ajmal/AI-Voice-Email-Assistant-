from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from llm_handler import process_with_llm
import whisper
import os
from dotenv import load_dotenv
import traceback
from google_auth_oauthlib.flow import Flow
from db import tokens_collection
from gmail_api_sender import gmail_send_user
import json
from googleapiclient.discovery import build
from gmail_metadata import get_user_metadata
from gtts import gTTS
import uuid
from persona_modeler import generate_user_persona
from embedding_cache import build_user_embedding_cache, retrieve_similar_emails
from gmail_label_manager import create_gmail_label
from google.oauth2.credentials import Credentials
#import openai
import re

# Load environment variables
load_dotenv()
#openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app
app = FastAPI()

# Load Whisper model
model = whisper.load_model("small")

# Google OAuth
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    'https://www.googleapis.com/auth/gmail.labels',
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

@app.get("/")
def read_root():
    return {"message": "Voice Email Assistant API is running!"}

@app.get("/authorize")
def authorize():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/oauth2callback"
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        return RedirectResponse(authorization_url)
    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/oauth2callback"
        )
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials

        user_info = build('oauth2', 'v2', credentials=credentials).userinfo().get().execute()
        user_email = user_info['email']

        tokens_collection.update_one(
            {"_id": user_email},
            {"$set": {
                "_id": user_email,
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }},
            upsert=True
        )

        return {"message": f"Authorization complete. Tokens saved for {user_email}."}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/transcribe")
def transcribe_audio():
    try:
        result = model.transcribe("command.wav")
        return {
            "transcription": result["text"],
            "llm_response": process_with_llm(result["text"])
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/send_email")
def send_email_route():
    try:
        result = model.transcribe("command.wav")
        transcription = result["text"]
        llm_response = process_with_llm(transcription)

        email_data = json.loads(llm_response)
        recipient = email_data.get("recipient")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")

        user_email = os.getenv("SENDER_EMAIL")
        user_tokens = tokens_collection.find_one({"_id": user_email})
        if not user_tokens:
            return JSONResponse(status_code=400, content={"error": f"Tokens not found for {user_email}."})

        email_send_result = gmail_send_user(user_tokens, recipient, subject, body)

        return {
            "transcription": transcription,
            "llm_response": email_data,
            "email_send_result": email_send_result
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/get_metadata")
def get_metadata():
    try:
        return get_user_metadata(os.getenv("SENDER_EMAIL"))
    except Exception as e:
        return {"error": str(e)}

@app.get("/inbox_summary")
def inbox_summary():
    try:
        result = get_user_metadata(os.getenv("SENDER_EMAIL"))
        return {"summary": result.get("smart_summary", "No summary available.")}
    except Exception as e:
        return {"error": str(e)}

@app.get("/inbox_summary_audio")
def inbox_summary_audio():
    try:
        summary = get_user_metadata(os.getenv("SENDER_EMAIL")).get("smart_summary", "You have no new messages.")
        tts = gTTS(summary)
        filename = f"inbox_summary_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join("static", filename)
        os.makedirs("static", exist_ok=True)
        tts.save(filepath)
        return FileResponse(filepath, media_type="audio/mpeg", filename=filename)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/generate_persona")
def generate_persona_route():
    try:
        return generate_user_persona(os.getenv("SENDER_EMAIL"))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/build_embedding_cache")
def build_cache():
    email = os.getenv("SENDER_EMAIL")
    index, metadata = build_user_embedding_cache(email)
    return {"message": f"Embedding cache built for {len(metadata)} emails"}

@app.post("/semantic_voice_search")
def semantic_voice_search():
    try:
        result = model.transcribe("command.wav")
        transcription = result["text"]
        llm_response = process_with_llm(f"Extract a short semantic email search phrase from: '{transcription}'")

        llm_query = json.loads(llm_response) if isinstance(llm_response, str) else llm_response
        query_parts = [
            llm_query.get("subject", ""),
            f"from {llm_query['recipient']}" if llm_query.get("recipient") else "",
            llm_query.get("body", "")
        ]
        query_str = " ".join([part for part in query_parts if part]).strip()

        results = retrieve_similar_emails(os.getenv("SENDER_EMAIL"), query_str)

        return {
            "transcription": transcription,
            "llm_query": llm_query,
            "query_used": query_str,
            "matches": results
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def extract_labels_from_transcription(text: str):
    text = text.lower().strip()

    # Must contain the word 'label' or 'labels' to proceed
    if "label" not in text:
        return []

    # Remove trigger words to isolate label names
    cleaned = re.sub(r"(create|make|add)?\s*(labels|label)?\s*(like|for)?", "", text).strip()

    # Remove filler words and punctuations
    cleaned = re.sub(r"[^\w\s,]", "", cleaned)

    # Split on common conjunctions or commas
    raw_labels = re.split(r"\band\b|,|\s+and\s+", cleaned)
    labels = [label.strip() for label in raw_labels if label.strip()]

    print("🪄 Extracted labels:", labels)
    return labels


@app.post("/voice_create_labels")
def voice_create_labels():
    result = model.transcribe("command.wav")
    transcription = result["text"]
    print("📝 You said:", transcription)

    labels = extract_labels_from_transcription(transcription)

    user_email = os.getenv("SENDER_EMAIL")
    user_tokens = tokens_collection.find_one({"_id": user_email})
    if not user_tokens:
        return JSONResponse(status_code=400, content={"error": f"Tokens not found for {user_email}. Please authorize first."})

    creds = Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],
        scopes=user_tokens["scopes"]
    )
    service = build("gmail", "v1", credentials=creds)

    existing_labels = {
        label["name"].lower()
        for label in service.users().labels().list(userId="me").execute().get("labels", [])
    }

    results = []
    for label in labels:
        label_clean = label.strip()
        if label_clean.lower() in existing_labels:
            results.append({"label": label_clean, "status": "already_exists"})
        else:
            results.append(create_gmail_label(service, label_clean))

    return {
        "transcription": transcription,
        "labels_created": results
    }
