from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from db import tokens_collection
import base64
import re
from collections import Counter
import emoji
import textstat


def build_credentials(user_tokens):
    return Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],
        scopes=user_tokens["scopes"]
    )


def fetch_sent_messages_from_tokens(user_tokens, max_results=100):
    creds = build_credentials(user_tokens)
    service = build('gmail', 'v1', credentials=creds)

    response = service.users().messages().list(
        userId='me',
        labelIds=['SENT'],
        maxResults=max_results
    ).execute()

    messages = []
    message_ids = response.get('messages', [])

    for msg in message_ids:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        payload = msg_data.get('payload', {})
        parts = payload.get('parts', [])
        body = ""

        for part in parts:
            mime_type = part.get('mimeType')
            data = part.get('body', {}).get('data')

            if not data:
                continue

            try:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                body = decoded
                if mime_type == 'text/plain':
                    break  # Prefer plain text
            except Exception:
                continue

        if body:
            messages.append(body.strip())

    print(f"🔍 Total message bodies extracted: {len(messages)} / requested: {max_results}")
    return messages


def extract_persona_features(messages):
    greetings = []
    signoffs = []
    total_emojis = 0
    total_sentences = 0
    total_words = 0
    tone_scores = []

    for msg in messages:
        lines = msg.strip().splitlines()
        if not lines:
            continue

        # 🔍 Detect greetings from first line
        first_line = lines[0].strip()
        if any(word in first_line.lower() for word in ["hi", "hello", "dear"]):
            greetings.append(first_line)

        # 🔍 Detect signoffs from last 3-4 lines
        last_lines = [line.strip() for line in lines[-4:] if line.strip()]
        print("🔎 Last few lines to check for signoff:", last_lines)

        for line in reversed(last_lines):
            if any(word in line.lower() for word in ["thanks", "regards", "best", "sincerely", "cheers"]):
                signoffs.append(line)
                break  # only take first matching signoff

        total_emojis += count_emojis(msg)
        sentences = re.split(r'[.!?]+', msg)
        total_sentences += len([s for s in sentences if s.strip()])
        total_words += len(msg.split())

        try:
            tone_scores.append(textstat.flesch_reading_ease(msg))
        except:
            continue

    avg_tone = sum(tone_scores) / len(tone_scores) if tone_scores else 0

    return {
        "top_greetings": most_common(greetings, 2),
        "top_signoffs": most_common(signoffs, 2),
        "emoji_level": categorize_emoji_level(total_emojis, len(messages)),
        "avg_sentence_length": round(total_words / max(total_sentences, 1)),
        "tone": categorize_tone(avg_tone),
        "email_sample_count": len(messages)
    }


def most_common(items, top_n):
    return [item for item, _ in Counter(items).most_common(top_n)]


def count_emojis(text):
    count = sum(1 for char in text if char in emoji.EMOJI_DATA)
    if count > 0:
        print(f"📨 Emoji detected: {count} in email")
    return count


def categorize_emoji_level(emoji_count, msg_count):
    avg = emoji_count / max(msg_count, 1)
    if avg == 0:
        return "none"
    elif avg < 2:
        return "light"
    else:
        return "frequent"


def categorize_tone(score):
    if score >= 60:
        return "casual"
    elif score >= 30:
        return "neutral"
    else:
        return "formal"


def save_persona(user_email, persona_data):
    tokens_collection.update_one(
        {"_id": user_email},
        {"$set": {"persona": persona_data}},
        upsert=True
    )


def generate_user_persona(user_email):
    user_tokens = tokens_collection.find_one({"_id": user_email})
    if not user_tokens:
        return {"error": "User tokens not found."}

    messages = fetch_sent_messages_from_tokens(user_tokens)
    if not messages:
        return {"error": "No sent messages found."}

    persona = extract_persona_features(messages)
    save_persona(user_email, persona)
    return persona