"""Email/SMS sending: municipal alerts for new reports, and password-reset codes.

Email uses Gmail SMTP. SMS goes through an Android phone running the free
"SMS Gateway for Android" app (texts are sent from that phone's own SIM and
SMS bundle) when SMS_GATEWAY_URL is set, otherwise through Twilio. Everything
reads its credentials from .env and is a no-op with a printed warning if
they're left blank, so the rest of the system keeps working without them.
"""
import base64
import ipaddress
import json
import os
import re
import smtplib
import threading
import urllib.request
from email.message import EmailMessage
from urllib.parse import urlsplit

from twilio.rest import Client

from model.waste_types import type_label

SMS_GATEWAY_TIMEOUT = 15  # seconds


def send_email_alert(subject: str, body: str, to_address: str) -> bool:
    """Send an email alert via Gmail SMTP. Returns True on success."""
    sender = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_PASSWORD")
    if not sender or not password:
        print("[alerts] EMAIL_ADDRESS/EMAIL_PASSWORD not set — skipping email alert")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_address
    message.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(message)
    return True


def send_sms_alert(message: str, to_number: str) -> bool:
    """Send one SMS. Returns False if no SMS service is set up; raises if sending fails."""
    to_number = sms_number(to_number)
    if os.environ.get("SMS_GATEWAY_URL"):
        return _send_via_phone(message, to_number)

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not account_sid or not auth_token or not from_number:
        print("[alerts] no SMS service set up (SMS_GATEWAY_URL or TWILIO_*) — skipping SMS")
        return False

    client = Client(account_sid, auth_token)
    client.messages.create(body=message, from_=from_number, to=to_number)
    return True


def _send_via_phone(message: str, to_number: str) -> bool:
    """Hand the text to the Android phone running SMS Gateway, which sends it from its SIM.

    SMS_GATEWAY_URL is the app's send address: http://<phone-ip>:8080/message in
    Local Server mode, or https://api.sms-gate.app/3rdparty/v1/messages in Cloud mode.
    """
    credentials = f"{os.environ.get('SMS_GATEWAY_USERNAME', '')}:{os.environ.get('SMS_GATEWAY_PASSWORD', '')}"
    request = urllib.request.Request(
        os.environ["SMS_GATEWAY_URL"],
        data=json.dumps({"textMessage": {"text": message}, "phoneNumbers": [to_number]}).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
        },
    )
    # Any non-2xx answer raises urllib.error.HTTPError; an unreachable phone raises URLError.
    with _gateway_opener(request.full_url).open(request, timeout=SMS_GATEWAY_TIMEOUT) as response:
        response.read()
    return True


def _gateway_opener(url: str) -> urllib.request.OpenerDirector:
    """A phone on the local network is called directly: an office/system web proxy can't reach it."""
    host = urlsplit(url).hostname or ""
    try:
        local = ipaddress.ip_address(host).is_private
    except ValueError:
        local = host == "localhost" or host.endswith(".local")
    return urllib.request.build_opener(urllib.request.ProxyHandler({})) if local else urllib.request.build_opener()


def sms_number(phone: str) -> str:
    """A phone number as typed ("077 123 4567", "+263 77...") in the international +<country><number> form.

    Local numbers starting with 0 get SMS_COUNTRY_CODE (default 263, Zimbabwe).
    """
    digits = re.sub(r"[^\d+]", "", phone or "")
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("+"):
        return digits
    if digits.startswith("0"):
        return "+" + os.environ.get("SMS_COUNTRY_CODE", "263") + digits[1:]
    return "+" + digits


def notify_new_report(report, detections: list[dict]) -> None:
    """Alert every configured municipal recipient (ALERT_RECIPIENTS / ALERT_PHONE_NUMBERS).

    Sent on a background thread, so the citizen's upload isn't kept waiting on
    email or SMS, and a failed alert can't fail the report that was just saved.
    """
    emails = _split_env_list("ALERT_RECIPIENTS")
    numbers = _split_env_list("ALERT_PHONE_NUMBERS")
    if not emails and not numbers:
        return

    waste_types = ", ".join(sorted({type_label(d["class_name"]) for d in detections})) or "unclassified waste"
    confidence = max((d["confidence"] for d in detections), default=0)
    map_link = f"https://maps.google.com/?q={report.latitude:.5f},{report.longitude:.5f}"
    dashboard = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    dashboard_line = f"\nDashboard: {dashboard}/municipal/" if dashboard else ""

    subject = f"New illegal waste dumping report — {waste_types}"
    body = (
        f"Report #{report.id} submitted at {report.submitted_at.isoformat()}\n"
        f"Location: {report.latitude}, {report.longitude}\n"
        f"Map: {map_link}\n"
        f"Detected: {waste_types} ({confidence:.0%})\n"
        f"Image: {report.image_path}"
        f"{dashboard_line}"
    )
    sms = (f"PlanetWatch: new illegal waste dumping report #{report.id} ({waste_types}, {confidence:.0%}).\n"
           f"Location: {map_link}{dashboard_line}")

    threading.Thread(target=_deliver_alerts, args=(subject, body, sms, emails, numbers), daemon=True).start()


def _deliver_alerts(subject: str, body: str, sms: str, emails: list[str], numbers: list[str]) -> None:
    for address in emails:
        try:
            send_email_alert(subject, body, address)
        except Exception as exc:
            print(f"[alerts] email alert to {address} failed: {exc}")
    for number in numbers:
        try:
            send_sms_alert(sms, number)
        except Exception as exc:
            print(f"[alerts] SMS alert to {number} failed: {exc}")


def _split_env_list(var_name: str) -> list[str]:
    raw = os.environ.get(var_name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]
