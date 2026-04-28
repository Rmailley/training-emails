import hmac
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "fitness@robmailley.com")
API_BASE = "https://api.smtp2go.com/v3"


def send_email(subject: str, html_body: str, text_body: str, **_) -> Optional[str]:
    """Send an email via SMTP2GO API. Returns message ID on success, None on failure."""
    try:
        resp = requests.post(
            f"{API_BASE}/email/send",
            json={
                "api_key": os.getenv("SMTP2GO_API_KEY"),
                "to": [EMAIL_ADDRESS],
                "sender": EMAIL_ADDRESS,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        message_id = data.get("data", {}).get("email_id", "")
        logger.info(f"Email sent: {subject} — email_id: {message_id}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to send email '{subject}': {e}")
        return None


def verify_webhook_secret(token: str) -> bool:
    """Verify the secret token passed in the inbound webhook URL path."""
    expected = os.getenv("SMTP2GO_WEBHOOK_SECRET", "")
    if not expected:
        return True  # no secret configured — allow all (dev mode)
    return hmac.compare_digest(token, expected)
