from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from db import tokens_collection
from collections import Counter


def categorize_thread(thread_labels):
    """
    Categorize a thread based on Gmail labels.
    """
    if "IMPORTANT" in thread_labels:
        return "High Priority"
    elif any(label in thread_labels for label in ["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "SPAM"]):
        return "Low Priority"
    else:
        return "Normal"


def format_label_name(label_id):
    """
    Make Gmail label IDs more human-readable.
    """
    mapping = {
        "CATEGORY_PROMOTIONS": "Promotions",
        "CATEGORY_SOCIAL": "Social",
        "CATEGORY_UPDATES": "Updates",
        "CATEGORY_FORUMS": "Forums",
        "IMPORTANT": "Important",
        "INBOX": "Inbox",
        "SPAM": "Spam",
        "SENT": "Sent",
        "DRAFT": "Draft",
        "CHAT": "Chat",
        "TRASH": "Trash",
        "UNREAD": "Unread",
        "STARRED": "Starred"
    }
    return mapping.get(label_id, label_id.replace("_", " ").title())


def get_user_metadata(user_email):
    """
    Retrieves user's Gmail labels and recent thread metadata.
    Enhances readability with summaries, category digest, and readable labels.
    """
    user_tokens = tokens_collection.find_one({"_id": user_email})
    if not user_tokens:
        return {"error": "User not authorized"}

    # Create credentials from stored tokens
    creds = Credentials(
        token=user_tokens["token"],
        refresh_token=user_tokens["refresh_token"],
        token_uri=user_tokens["token_uri"],
        client_id=user_tokens["client_id"],
        client_secret=user_tokens["client_secret"],
        scopes=user_tokens["scopes"]
    )

    try:
        # Build Gmail API client
        service = build("gmail", "v1", credentials=creds)

        # Fetch all Gmail labels
        labels_response = service.users().labels().list(userId="me").execute()
        labels = [label["name"] for label in labels_response.get("labels", [])]

        # Fetch metadata for the latest 10 threads
        threads_response = service.users().threads().list(userId="me", maxResults=50).execute()
        threads_metadata = []

        for thread in threads_response.get("threads", []):
            thread_detail = service.users().threads().get(userId="me", id=thread["id"]).execute()
            messages = thread_detail.get("messages", [])
            if not messages:
                continue

            latest_msg = messages[-1]
            headers = {
                h['name']: h['value']
                for h in latest_msg.get("payload", {}).get("headers", [])
            }

            snippet = thread_detail.get("snippet", "")
            sender = headers.get("From", "Unknown")
            subject = headers.get("Subject", "(No Subject)")
            date = headers.get("Date", "Unknown")
            label_ids = latest_msg.get("labelIds", [])

            category = categorize_thread(label_ids)
            readable_labels = [format_label_name(lid) for lid in label_ids]

            summary = f"📩 From {sender} | Subject: '{subject}' | {category} | {len(messages)} msg(s) on {date}"

            threads_metadata.append({
                "snippet": snippet,
                "from": sender,
                "subject": subject,
                "date": date,
                "labels": readable_labels,
                "category": category,
                "message_count": len(messages),
                "summary": summary
            })

        # Digest statistics
        category_counts = Counter(t["category"] for t in threads_metadata)
        sender_counts = Counter(t["from"] for t in threads_metadata)
        digest = {
            "total_threads": len(threads_metadata),
            "category_breakdown": dict(category_counts),
            "top_senders": sender_counts.most_common(3)
        }

        # Smart metrics
        unread_count = sum(1 for t in threads_metadata if "Unread" in t["labels"] and "Inbox" in t["labels"])
        promo_count = sum(1 for t in threads_metadata if "Promotions" in t["labels"])
        university_senders = ["nu.edu.pk", "university.edu", "classroom.google.com"]
        university_count = sum(
            1 for t in threads_metadata if any(domain in t["from"] for domain in university_senders)
        )

        smart_summary = (
            f"Out of {digest['total_threads']} recent emails: "
            f"{unread_count} unread, {promo_count} promotions, "
            f"{digest['category_breakdown'].get('High Priority', 0)} high priority. "
            f"{university_count} email(s) are from university's domain. "
            f"Top senders include: {', '.join(sender for sender, _ in digest['top_senders'])}."
        )

        return {
            "labels": labels,
            "inbox_digest": digest,
            "recent_threads": threads_metadata,
            "smart_summary": smart_summary
        }

    except Exception as e:
        return {"error": str(e)}
