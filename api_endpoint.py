from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from llm_handler import process_with_llm
import whisper
import os
from dotenv import load_dotenv
import traceback
from google_auth_oauthlib.flow import Flow
from db import tokens_collection
from gmail_api_sender import gmail_send_user
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from googleapiclient.discovery import build
from gmail_metadata import get_user_metadata
from fastapi import Body
import traceback
from gmail_metadata import get_user_metadata
from gtts import gTTS
import uuid
from fastapi.responses import FileResponse

# Load environment
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load Whisper model once
model = whisper.load_model("small")

# Google OAuth config
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
"https://www.googleapis.com/auth/gmail.readonly",
"https://www.googleapis.com/auth/gmail.send",
"https://www.googleapis.com/auth/userinfo.email",
"openid"
]
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for local testing

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
            scopes=SCOPES,  # 🔴 Uses updated SCOPES including userinfo.email
            redirect_uri="http://localhost:8000/oauth2callback"
        )
        flow.fetch_token(authorization_response=str(request.url))

        credentials = flow.credentials

        # 🔥 Build user info service
        user_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_service.userinfo().get().execute()
        user_email = user_info['email']

        user_tokens = {
            "_id": user_email,  # ✅ Use email as _id for unique identification
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }

        # ✅ Save tokens in MongoDB with email as _id
        tokens_collection.update_one(
            {"_id": user_email},
            {"$set": user_tokens},
            upsert=True
        )

        print("Tokens saved for user:", user_tokens)
        return {"message": f"Authorization complete. Tokens saved for {user_email}."}

    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.post("/transcribe")
def transcribe_audio():
    try:
        # Step 1: Transcribe audio
        result = model.transcribe("command.wav")
        transcription = result["text"]
        print("🎤 Transcription:", transcription)

        # Step 2: Get LLM response
        llm_response = process_with_llm(transcription)
        print("🤖 LLM Response:", llm_response)

        return {
            "transcription": transcription,
            "llm_response": llm_response
        }

    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})


# Initialize Whisper model
model = whisper.load_model("small")

@app.post("/send_email")
def send_email_route():
    try:
       # Step 1: Transcribe audio
        result = model.transcribe("command.wav")
        transcription = result["text"]
        print("🎤 Transcription:", transcription)

        # Step 2: Process with LLM to get structured email data
        llm_response = process_with_llm(transcription)
        print("🤖 LLM Response:", llm_response)

        # Step 3: Parse LLM response (assuming it's JSON string)
        email_data = json.loads(llm_response)

        recipient = email_data.get("recipient")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")

        # Step 4: Send email
        email_send_result = send_email(recipient, subject, body)
        print("📧 Email Send Result:", email_send_result)

        return {
            "transcription": transcription,
            "llm_response": email_data,
            "email_send_result": email_send_result
        }

    except Exception as e:
        print("🔥 Error:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/get_metadata")
def get_metadata():
    try:
        user_email = "zainab.ajmal68@gmail.com"
        metadata = get_user_metadata(user_email)
        return metadata
    except Exception as e:
        return {"error": str(e)}

@app.get("/inbox_summary")
def inbox_summary():
    try:
        # Simulate user (later: extract from session)
        user_email = "zainab.ajmal68@gmail.com"

        # Get metadata
        result = get_user_metadata(user_email)
        if "error" in result:
            return JSONResponse(status_code=400, content={"error": result["error"]})

        summary = result.get("smart_summary", "No summary available.")

        return {
            "summary": summary,
            "text": summary
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.get("/inbox_summary_audio")
def inbox_summary_audio():
    try:
        user_email = "zainab.ajmal68@gmail.com"
        result = get_user_metadata(user_email)

        summary = result.get("smart_summary", "You have no new messages.")

        # Generate audio
        tts = gTTS(summary)
        filename = f"inbox_summary_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join("static", filename)

        os.makedirs("static", exist_ok=True)
        tts.save(filepath)

        return FileResponse(filepath, media_type="audio/mpeg", filename=filename)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
