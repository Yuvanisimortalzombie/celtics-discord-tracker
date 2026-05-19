import importlib.util
from pathlib import Path
import requests


def load_celtics_stats_module():
    root = Path(__file__).resolve().parent
    module_path = root / "celtics_stats.py"

    spec = importlib.util.spec_from_file_location("celtics_stats", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load your existing stats code
celtics_stats = load_celtics_stats_module()
get_celtics_stats_message = celtics_stats.get_celtics_stats_message


# Your Discord webhook
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1495454317405016115/3-Dvcf60QSAO-nN-nuFxV3ey1eEZTBTR-sTrpOzf97cBaPR5vNEH8QSgcT3YquOJdWCF"
LAST_SENT_FILE = Path(".last_sent_game_id")

def send_discord(body):
    payload = {
        "content": body[:1800]  # Discord limit safety
    }

    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload)

        print("Discord Status:", r.status_code)

        if r.status_code in [200, 204]:
            print("✅ Stats sent to Discord")
            return True
        else:
            print("❌ Discord error:", r.text)
            return False

    except Exception as e:
        print("Request failed:", e)
        return False

def get_latest_game_id():
    row = celtics_stats.get_latest_celtics_game_row()
    return str(row["GAME_ID"]), row


def load_last_sent():
    try:
        return LAST_SENT_FILE.read_text().strip()
    except:
        return None


def save_last_sent(game_id):
    LAST_SENT_FILE.write_text(game_id)

def main():
    latest_game_id, latest_game_row = get_latest_game_id()

    print("Latest game:", latest_game_id)

    last_sent = load_last_sent()

    if last_sent == latest_game_id:
        print("Already sent this game's stats.")
        return

    body = get_celtics_stats_message(latest_game_row)

    sent = send_discord(body)

    if sent:
        save_last_sent(latest_game_id)

if __name__ == "__main__":
            main()
