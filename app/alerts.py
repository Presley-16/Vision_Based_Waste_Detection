"""Email/SMS alert logic for confirmed illegal dumping detections.

Email uses Gmail SMTP; SMS uses Twilio. Both read credentials from
environment variables (.env) and are no-ops with a printed warning if those
are left blank, so the rest of the pipeline keeps working before the
alerting accounts are provisioned.
"""
import os
import smtplib
from email.message import EmailMessage

from twilio.rest import Client


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
    """Send an SMS alert via Twilio. Returns True on success."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not account_sid or not auth_token or not from_number:
        print("[alerts] TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER not set — skipping SMS alert")
        return False

    client = Client(account_sid, auth_token)
    client.messages.create(body=message, from_=from_number, to=to_number)
    return True


def notify_new_report(report, detections: list[dict]) -> None:
    """Fan out an alert to every configured recipient for a new report."""
    waste_types = ", ".join(sorted({d["class_name"] for d in detections})) or "unclassified waste"
    subject = f"New illegal dumping report — {waste_types}"
    body = (
        f"Report #{report.id} submitted at {report.submitted_at.isoformat()}\n"
        f"Location: {report.latitude}, {report.longitude}\n"
        f"Detected: {waste_types}\n"
        f"Image: {report.image_path}"
    )

    for address in _split_env_list("ALERT_RECIPIENTS"):
        send_email_alert(subject, body, address)

    for number in _split_env_list("ALERT_PHONE_NUMBERS"):
        send_sms_alert(f"{subject}. Location: {report.latitude},{report.longitude}", number)


def _split_env_list(var_name: str) -> list[str]:
    raw = os.environ.get(var_name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]
