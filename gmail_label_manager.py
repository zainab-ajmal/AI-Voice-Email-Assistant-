from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from db import tokens_collection

def create_gmail_label(service, label_name):
    try:
        label_obj = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }

        created_label = service.users().labels().create(userId='me', body=label_obj).execute()
        return {"label": created_label["name"], "status": "created"}

    except Exception as e:
        return {"label": label_name, "status": f"error: {str(e)}"}
