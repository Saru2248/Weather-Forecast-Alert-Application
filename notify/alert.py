"""
============================================================
notify/alert.py — Notification System
============================================================
Sends weather alert notifications via:
  1. Email (Gmail SMTP) — when EMAIL_ENABLED=True in .env
  2. Telegram Bot       — when TELEGRAM_ENABLED=True in .env

Features:
  - HTML-formatted email with severity color coding
  - Telegram message with markdown formatting
  - Alert deduplication (only sends UNNOTIFIED alerts)
  - Marks alerts as notified after sending

Configuration (in .env):
  EMAIL_ENABLED=True
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your_email@gmail.com
  SMTP_PASSWORD=your_app_password    ← Use Gmail App Password
  ALERT_RECIPIENT=recipient@gmail.com

  TELEGRAM_ENABLED=True
  TELEGRAM_BOT_TOKEN=xxx
  TELEGRAM_CHAT_ID=xxx

Email Setup Guide:
  1. Go to Gmail → Settings → Security
  2. Enable 2-Factor Authentication
  3. Go to App Passwords → Generate for "Mail"
  4. Use that 16-char password as SMTP_PASSWORD
"""

import sys
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from db.models import AlertLog, Location


# ──────────────────────────────────────────────────────────
# Severity Color Mapping (for HTML email)
# ──────────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "LOW":      "#4CAF50",   # Green
    "MEDIUM":   "#FF9800",   # Orange
    "HIGH":     "#F44336",   # Red
    "CRITICAL": "#9C27B0",   # Purple
}

ALERT_ICONS = {
    "RAIN": "🌧️",
    "HEAT": "🌡️",
    "WIND": "💨",
    "UV":   "☀️",
}


# ──────────────────────────────────────────────────────────
# EMAIL NOTIFICATION
# ──────────────────────────────────────────────────────────

def build_html_email(alerts: list[AlertLog], location_name: str) -> str:
    """
    Builds an HTML email body for weather alerts.
    Color-coded by severity, includes all alert details.
    """
    rows = ""
    for alert in alerts:
        color = SEVERITY_COLORS.get(alert.severity, "#666")
        icon = ALERT_ICONS.get(alert.alert_type, "⚠️")
        forecast_time = (
            alert.forecast_time.strftime("%d %b %Y %H:%M UTC")
            if alert.forecast_time else "N/A"
        )
        rows += f"""
        <div style="border-left: 5px solid {color}; padding: 15px; margin: 15px 0;
                    background: #f9f9f9; border-radius: 4px;">
            <h3 style="color: {color}; margin: 0 0 10px 0;">{icon} {alert.title}</h3>
            <p><strong>Severity:</strong>
               <span style="color: {color}; font-weight: bold;">{alert.severity}</span></p>
            <p><strong>Type:</strong> {alert.alert_type}</p>
            <p><strong>Expected at:</strong> {forecast_time}</p>
            <p style="white-space: pre-line;">{alert.message}</p>
            <p style="color: #999; font-size: 12px;">
                Alert generated: {alert.alert_time.strftime('%d %b %Y %H:%M UTC')}
            </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #fff; }}
            .header {{ background: #1a237e; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .footer {{ background: #f5f5f5; padding: 15px; text-align: center;
                       font-size: 12px; color: #999; border-radius: 0 0 8px 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🌦️ Weather Alert Notification</h2>
            <p>Location: {location_name} | Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}</p>
        </div>

        <div style="padding: 20px; border: 1px solid #ddd;">
            <p>{len(alerts)} weather alert(s) require your attention:</p>
            {rows}
        </div>

        <div class="footer">
            <p>Weather Forecast &amp; Alert System | Powered by Open-Meteo API</p>
            <p>This is an automated notification. Do not reply to this email.</p>
        </div>
    </body>
    </html>
    """


def send_email_notification(alerts: list[AlertLog], location_name: str) -> bool:
    """
    Sends an HTML alert email via Gmail SMTP.

    Parameters:
        alerts        : List of AlertLog objects to send
        location_name : City name for email subject

    Returns:
        True if sent successfully, False otherwise
    """
    if not settings.EMAIL_ENABLED:
        logger.debug("📧 Email notifications disabled (EMAIL_ENABLED=False)")
        return False

    if not alerts:
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚠️ Weather Alert: {len(alerts)} alert(s) for {location_name}"
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_RECIPIENT

        # Plain text fallback
        plain_text = "\n\n".join([f"{a.title}\n{a.message}" for a in alerts])
        msg.attach(MIMEText(plain_text, "plain"))

        # HTML body
        html_body = build_html_email(alerts, location_name)
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_USER,
                settings.ALERT_RECIPIENT,
                msg.as_string()
            )

        logger.success(f"📧 Email sent to {settings.ALERT_RECIPIENT} for {location_name}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Email auth failed. Check SMTP_USER and SMTP_PASSWORD in .env")
        return False
    except Exception as e:
        logger.error(f"❌ Email send failed: {e}")
        return False


# ──────────────────────────────────────────────────────────
# TELEGRAM NOTIFICATION
# ──────────────────────────────────────────────────────────

def build_telegram_message(alerts: list[AlertLog], location_name: str) -> str:
    """
    Builds a Telegram-formatted message for weather alerts.
    Uses MarkdownV2 formatting.
    """
    lines = [f"🌦️ *Weather Alert — {location_name}*\n"]

    for alert in alerts:
        icon = ALERT_ICONS.get(alert.alert_type, "⚠️")
        forecast_time = (
            alert.forecast_time.strftime("%d %b %H:%M")
            if alert.forecast_time else "N/A"
        )
        lines.append(
            f"{icon} *{alert.alert_type}* | {alert.severity}\n"
            f"📍 {location_name} | 🕐 {forecast_time}\n"
            f"📊 Value: {alert.trigger_value:.1f} | Threshold: {alert.threshold_used:.1f}\n"
            f"💬 {alert.message[:200]}...\n"
        )

    lines.append(f"\n_Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}_")
    return "\n".join(lines)


def send_telegram_notification(alerts: list[AlertLog], location_name: str) -> bool:
    """
    Sends weather alert notification to a Telegram chat.

    Setup:
      1. Create a bot via @BotFather on Telegram
      2. Get your chat ID via @userinfobot
      3. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

    Parameters:
        alerts        : List of AlertLog objects
        location_name : City name for message header

    Returns:
        True if sent successfully, False otherwise
    """
    if not settings.TELEGRAM_ENABLED:
        logger.debug("📱 Telegram notifications disabled (TELEGRAM_ENABLED=False)")
        return False

    if not alerts:
        return True

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        return False

    try:
        message = build_telegram_message(alerts, location_name)
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

        logger.success(f"📱 Telegram message sent for {location_name}")
        return True

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Telegram API error: {e.response.status_code} — {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ Telegram send failed: {e}")
        return False


# ──────────────────────────────────────────────────────────
# UNIFIED NOTIFICATION DISPATCHER
# ──────────────────────────────────────────────────────────

def send_notification_for_new_alerts(db: Session) -> int:
    """
    Finds all unnotified alerts in the DB and sends notifications.
    Marks alerts as notified after successful send.

    This is called automatically by the scheduler after each
    data ingestion + alert engine run.

    Parameters:
        db : SQLAlchemy session

    Returns:
        Number of alerts notified
    """
    if not settings.EMAIL_ENABLED and not settings.TELEGRAM_ENABLED:
        logger.info("📬 No notification channels enabled. Set EMAIL_ENABLED or TELEGRAM_ENABLED in .env")
        return 0

    # Find all unnotified active alerts
    unnotified = (
        db.query(AlertLog)
        .filter(AlertLog.is_notified == False, AlertLog.is_active == True)
        .all()
    )

    if not unnotified:
        logger.info("📬 No unnotified alerts to send.")
        return 0

    logger.info(f"📬 Found {len(unnotified)} unnotified alert(s). Sending notifications...")

    # Group alerts by location
    from collections import defaultdict
    by_location: dict[int, list[AlertLog]] = defaultdict(list)
    for alert in unnotified:
        by_location[alert.location_id].append(alert)

    notified_count = 0

    for location_id, alerts in by_location.items():
        location = db.query(Location).filter(Location.id == location_id).first()
        location_name = location.city if location else f"Location #{location_id}"

        # Send email
        email_sent = send_email_notification(alerts, location_name)

        # Send Telegram
        telegram_sent = send_telegram_notification(alerts, location_name)

        # Mark as notified if at least one channel worked
        if email_sent or telegram_sent or (not settings.EMAIL_ENABLED and not settings.TELEGRAM_ENABLED):
            for alert in alerts:
                alert.is_notified = True
                alert.notified_at = datetime.utcnow()
            notified_count += len(alerts)

    db.commit()
    logger.success(f"✅ Notifications sent for {notified_count} alert(s).")
    return notified_count


# ──────────────────────────────────────────────────────────
# Console Notification (Always Active — for Demo)
# ──────────────────────────────────────────────────────────

def print_alert_to_console(alert: AlertLog, city: str):
    """
    Prints a formatted alert to the terminal.
    Always active regardless of notification settings.
    Useful for demos and development.
    """
    icon = ALERT_ICONS.get(alert.alert_type, "⚠️")
    severity_bar = "█" * {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(alert.severity, 1)

    print(f"\n{'='*60}")
    print(f"{icon}  WEATHER ALERT — {city.upper()}")
    print(f"{'='*60}")
    print(f"  Type     : {alert.alert_type}")
    print(f"  Severity : {alert.severity} {severity_bar}")
    print(f"  Title    : {alert.title}")
    print(f"  Value    : {alert.trigger_value} (threshold: {alert.threshold_used})")
    print(f"  Message  :\n    {alert.message}")
    print(f"{'='*60}\n")
