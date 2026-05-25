import requests


def get_latest_celtics_game():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

    data = requests.get(url).json()

    for game in data["events"]:
        competitors = game["competitions"][0]["competitors"]

        for team in competitors:
            if team["team"]["abbreviation"] == "BOS":
                return game

    return None


def get_latest_celtics_game_row():
    return get_latest_celtics_game()


def get_celtics_stats_message(game=None):
    if game is None:
        game = get_latest_celtics_game()

    if not game:
        return "❌ No Celtics game found today."

    competition = game["competitions"][0]

    home = competition["competitors"][0]
    away = competition["competitors"][1]

    home_team = home["team"]["abbreviation"]
    away_team = away["team"]["abbreviation"]

    home_score = home["score"]
    away_score = away["score"]

    status = competition["status"]["type"]["description"]

    return (
        f"🏀 Celtics Game Update\n\n"
        f"{away_team} {away_score} - {home_score} {home_team}\n"
        f"Status: {status}"
    )