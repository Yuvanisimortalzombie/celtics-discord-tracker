import importlib.util
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

try:
    from twilio.rest import Client
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False

import requests
from nba_api.stats.endpoints import boxscoresummaryv2


def load_celtics_stats_module():
    root = Path(__file__).resolve().parent
    module_path = root / "celtics_stats.py"
    spec = importlib.util.spec_from_file_location("celtics_stats", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


celtics_stats = load_celtics_stats_module()
get_celtics_stats_message = celtics_stats.get_celtics_stats_message

CARRIER_GATEWAYS = {
    "att": "txt.att.net",
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "metro": "mymetropcs.com",
    "uscellular": "email.uscc.net",
    "boost": "sms.myboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "googlefi": "msg.fi.google.com",
    "xfinity": "vtext.com",
}

DEFAULT_DISCORD_WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1495454317405016115/3-Dvcf60QSAO-nN-nuFxV3ey1eEZTBTR-sTrpOzf97cBaPR5vNEH8QSgcT3YquOJdWCF",
)
LAST_SENT_FILE = Path(os.environ.get("LAST_SENT_FILE", Path(__file__).resolve().parent / ".last_sent_game_id"))


def build_sms_gateway_address() -> str | None:
    sms_email = os.environ.get("SMS_GATEWAY_EMAIL")
    if sms_email:
        return sms_email

    phone = os.environ.get("SMS_PHONE_NUMBER")
    carrier = os.environ.get("SMS_CARRIER")
    gateway = os.environ.get("SMS_GATEWAY_DOMAIN")

    if phone and gateway:
        return f"{phone}@{gateway}"

    if phone and carrier:
        carrier_key = carrier.strip().lower()
        domain = CARRIER_GATEWAYS.get(carrier_key)
        if domain:
            return f"{phone}@{domain}"
        print("Unknown carrier. Supported carriers:", ", ".join(sorted(CARRIER_GATEWAYS)))

    return None


def send_sms_via_email(body: str) -> bool:
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    sms_email = build_sms_gateway_address()

    if not all([smtp_server, smtp_port, smtp_user, smtp_password, sms_email]):
        print(
            "Missing email SMS gateway settings.\n"
            "Set SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and "
            "either SMS_GATEWAY_EMAIL or SMS_PHONE_NUMBER + SMS_CARRIER."
        )
        return False

    msg = MIMEText(body)
    msg["Subject"] = "Celtics Stats"
    msg["From"] = smtp_user
    msg["To"] = sms_email

    try:
        if smtp_port == 587:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
    except Exception as exc:
        print("Failed to send SMS via email gateway:", exc)
        return False

    print("SMS sent via email gateway to", sms_email)
    return True


def send_sms_via_twilio(body: str) -> bool:
    if not _TWILIO_AVAILABLE:
        print("Twilio library is not installed.")
        return False

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_FROM_PHONE")
    to_phone = os.environ.get("TWILIO_TO_PHONE")

    if not all([account_sid, auth_token, from_phone, to_phone]):
        print(
            "Missing Twilio credentials. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "TWILIO_FROM_PHONE, and TWILIO_TO_PHONE environment variables."
        )
        return False

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(body=body, from_=from_phone, to=to_phone)
        print("SMS sent, message SID:", message.sid)
        return True
    except Exception as exc:
        print("Failed to send SMS via Twilio:", exc)
        return False


def send_discord_fallback(body: str) -> bool:
    webhook_url = DEFAULT_DISCORD_WEBHOOK
    if not webhook_url:
        print("Discord webhook is not configured. Set DISCORD_WEBHOOK_URL.")
        return False

    data = {"content": body[:1800]}
    try:
        r = requests.post(webhook_url, json=data)
        print("Discord Status:", r.status_code)
        if r.status_code in [200, 204]:
            print("Discord message sent successfully.")
            return True
        print("Discord failed. Response:", r.text)
        return False
    except Exception as exc:
        print("Discord request failed:", exc)
        return False


def load_last_sent_game_id() -> str | None:
    try:
        return LAST_SENT_FILE.read_text().strip()
    except FileNotFoundError:
        return None
    except Exception as exc:
        print("Unable to read last sent file:", exc)
        return None


def save_last_sent_game_id(game_id: str) -> None:
    try:
        LAST_SENT_FILE.write_text(str(game_id))
    except Exception as exc:
        print("Unable to save last sent game id:", exc)


def get_latest_celtics_game_status(game_id: str) -> dict:
    status_frame = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id).get_data_frames()[0]
    if status_frame.empty:
        raise RuntimeError(f"No status data returned for game {game_id}.")

    status = status_frame.loc[0, ["GAME_STATUS_ID", "GAME_STATUS_TEXT"]].to_dict()
    return {
        "GAME_STATUS_ID": int(status["GAME_STATUS_ID"]),
        "GAME_STATUS_TEXT": str(status["GAME_STATUS_TEXT"]),
    }


def main():
    latest_game_row = celtics_stats.get_latest_celtics_game_row()
    latest_game_id = str(latest_game_row["GAME_ID"])

    try:
        status = get_latest_celtics_game_status(latest_game_id)
    except Exception as exc:
        print("Unable to determine game status for game", latest_game_id, ":", exc)
        return

    print(
        f"Latest Celtics game {latest_game_id} status: "
        f"{status['GAME_STATUS_TEXT']} ({status['GAME_STATUS_ID']})"
    )

    if status["GAME_STATUS_ID"] != 3:
        print("The latest game is not final yet. No notification will be sent.")
        return

    last_sent_game_id = load_last_sent_game_id()
    if last_sent_game_id == latest_game_id:
        print("Stats already sent for latest game", latest_game_id)
        return

    body = get_celtics_stats_message(latest_game_row)
    print("Message length:", len(body))
    body = body[:1800]

    sent = False
    if build_sms_gateway_address() is not None:
        sent = send_sms_via_email(body)
    elif os.environ.get("TWILIO_ACCOUNT_SID"):
        sent = send_sms_via_twilio(body)
    else:
        print(
            "No SMS route configured. Using carrier email gateway is the most direct "
            "route to your iPhone.\n"
            "Set SMS_PHONE_NUMBER and SMS_CARRIER, or SMS_GATEWAY_EMAIL, plus SMTP_* settings."
        )

    if not sent:
        print("Trying Discord fallback...")
        sent = send_discord_fallback(body)

    if sent:
        save_last_sent_game_id(latest_game_id)
    else:
        print(
            "Failed to send by SMS or Discord.\n"
            "For direct iPhone SMS, set SMS_PHONE_NUMBER and SMS_CARRIER, "
            "plus SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD.\n"
            "If that still doesn't work, set DISCORD_WEBHOOK_URL for fallback."
        )


if __name__ == "__main__":
    main()
