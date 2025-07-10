import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_email(recipient, subject, body):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_pass = os.getenv("SENDER_APP_PASSWORD")

    # Create message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Connect to Gmail SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, recipient, msg.as_string())

        return {"status": "success", "message": f"Email sent to {recipient}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}