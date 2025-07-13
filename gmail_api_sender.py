from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText

def gmail_send_user(user_tokens, recipient, subject, body):
    """
    Sends an email using Gmail API with the provided user's tokens.

    Parameters:
        user_tokens (dict): The user's stored OAuth tokens.
        recipient (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body text.

    Returns:
        dict: Status and message ID or error.
    """

    # Create credentials object from saved user tokens
    creds = Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],
        scopes=user_tokens["scopes"]
    )

    try:
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Create the email message
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_message = {'raw': raw_message}

        # Send the email
        sent = service.users().messages().send(userId="me", body=send_message).execute()

        return {"status": "success", "message_id": sent['id']}

    except Exception as e:
        return {"status": "error", "message": str(e)}
