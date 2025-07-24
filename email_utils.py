# email_utils.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText

def gmail_send_user(user_tokens, recipient, subject, body):
    creds = Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],  
        scopes=user_tokens["scopes"]
    )

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = {'raw': raw_message}
        sent = service.users().messages().send(userId="me", body=send_message).execute()

        return {"status": "success", "message_id": sent['id']}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    #save email in the draft section
def save_to_drafts(user_tokens, recipient, subject, body):
    creds = Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],  
        scopes=user_tokens["scopes"]
    )

    try:
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_draft_request = {
            'message': {'raw': raw_message}
        }

        draft = service.users().drafts().create(userId='me', body=create_draft_request).execute()

        return {"status": "success", "message": "Draft saved to Gmail.", "draft_id": draft['id']}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# Open email in system notepad for review
def open_email_in_editor(email_data):
    import os
    filename = "review_email.txt"
    with open(filename, "w") as f:
        f.write(f"To: {email_data['recipient']}\nSubject: {email_data['subject']}\n\n{email_data['body']}")
    os.system(f"notepad {filename}")  # For Windows
    return "Opened email for review."
