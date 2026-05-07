"""통신 도구 — iMessage / Slack webhook / SMTP email / Discord webhook."""
from __future__ import annotations

import json
import os
import smtplib
import subprocess
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jarvis.tools.registry import REGISTRY, Tool


def _imessage_send(recipient: str, message: str) -> str:
    """iMessage/SMS 전송 — Messages.app via osascript.

    recipient: 전화번호 (+82...) 또는 Apple ID 이메일.
    """
    if not recipient or not message:
        return "recipient/message 비어있음"
    # AppleScript escape
    rec = recipient.replace('"', '\\"')
    msg = message.replace('"', '\\"').replace("\n", "\\n")
    script = (
        f'tell application "Messages"\n'
        f'  set targetService to 1st service whose service type = iMessage\n'
        f'  set targetBuddy to buddy "{rec}" of targetService\n'
        f'  send "{msg}" to targetBuddy\n'
        f'end tell'
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            return f"OK: {recipient}에게 전송됨"
        return f"실패: {r.stderr.strip()[:200]}"
    except Exception as e:
        return f"오류: {e}"


def _slack_webhook(message: str, webhook_url: str = "") -> str:
    """Slack incoming webhook으로 메시지 전송.

    webhook_url 미제공 시 SLACK_WEBHOOK_URL 환경변수.
    """
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        return "SLACK_WEBHOOK_URL 미설정 (https://api.slack.com/messaging/webhooks)"
    try:
        body = json.dumps({"text": message}).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"OK ({r.status}): {r.read().decode()[:100]}"
    except Exception as e:
        return f"실패: {e}"


def _discord_webhook(message: str, webhook_url: str = "", username: str = "Jarvis") -> str:
    """Discord webhook 전송."""
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return "DISCORD_WEBHOOK_URL 미설정"
    try:
        body = json.dumps({"content": message, "username": username}).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"OK ({r.status})"
    except Exception as e:
        return f"실패: {e}"


def _smtp_send(to: str, subject: str, body: str, html: bool = False) -> str:
    """SMTP 이메일 전송. 환경변수: SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/SMTP_FROM."""
    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    pwd = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", user)
    if not (host and user and pwd):
        return "SMTP_HOST/SMTP_USER/SMTP_PASS 환경변수 필요"
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return f"OK: {to}"
    except Exception as e:
        return f"SMTP 실패: {e}"


def _telegram_send(message: str, chat_id: str = "") -> str:
    """Telegram Bot API. 환경변수: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not cid:
        return "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정"
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({"chat_id": cid, "text": message}).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"OK ({r.status})"
    except Exception as e:
        return f"실패: {e}"


REGISTRY.register(Tool(
    name="imessage_send",
    description="iMessage/SMS 메시지 전송. recipient: 전화번호(+82...) 또는 Apple ID. macOS Messages.app 자동화 권한 필요.",
    input_schema={
        "type": "object",
        "properties": {
            "recipient": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["recipient", "message"],
    },
    handler=_imessage_send,
))

REGISTRY.register(Tool(
    name="slack_send",
    description="Slack 채널 메시지 (incoming webhook). SLACK_WEBHOOK_URL env 또는 인자.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "webhook_url": {"type": "string", "default": ""},
        },
        "required": ["message"],
    },
    handler=_slack_webhook,
))

REGISTRY.register(Tool(
    name="discord_send",
    description="Discord webhook 메시지. DISCORD_WEBHOOK_URL env 또는 인자.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "webhook_url": {"type": "string", "default": ""},
            "username": {"type": "string", "default": "Jarvis"},
        },
        "required": ["message"],
    },
    handler=_discord_webhook,
))

REGISTRY.register(Tool(
    name="email_send",
    description="SMTP 이메일 전송. SMTP_HOST/PORT/USER/PASS/FROM 환경변수 필요.",
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "html": {"type": "boolean", "default": False},
        },
        "required": ["to", "subject", "body"],
    },
    handler=_smtp_send,
))

REGISTRY.register(Tool(
    name="telegram_send",
    description="Telegram bot 메시지. TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 필요.",
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "chat_id": {"type": "string", "default": ""},
        },
        "required": ["message"],
    },
    handler=_telegram_send,
))
