"""
"You have a new message" alerts for the oga.

RULE: an alert NEVER contains anything the sender wrote. It only says that
something arrived, plus a link to the inbox. (The server can't read messages
anyway; this rule keeps it that way if someone changes things later.)

Turn on with env vars (any or both):
  ALERT_EMAIL=oga@example.com        + EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD ...
  TELEGRAM_BOT_TOKEN=123:abc         + TELEGRAM_CHAT_ID=456
At most one alert every ALERT_COOLDOWN_MINUTES (default 10), so a burst of
messages doesn't spam the oga's phone.
"""
import json
import logging
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

log = logging.getLogger(__name__)
TEXT = "📬 You have a new message in your Suggestion Box."


def _telegram(text):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": settings.TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5).read()


def notify_new_message(inbox_url=""):
    if not (settings.ALERT_EMAIL or (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)):
        return
    # cache.add only succeeds if the key isn't there yet -> simple cooldown.
    if not cache.add("alerts:cooldown", 1, settings.ALERT_COOLDOWN_MINUTES * 60):
        return
    text = TEXT + (f"\nOpen it: {inbox_url}" if inbox_url else "")
    if settings.ALERT_EMAIL:
        try:
            send_mail("New message in your Suggestion Box", text, None, [settings.ALERT_EMAIL], fail_silently=False)
        except Exception:  # never let an alert break a sender's submission
            log.warning("Email alert failed")
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        try:
            _telegram(text)
        except Exception:
            log.warning("Telegram alert failed")
