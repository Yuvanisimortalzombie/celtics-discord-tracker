from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder

TEAM_ID = 1610612738  # Celtics


def get_latest_celtics_game_row():
    games = leaguegamefinder.LeagueGameFinder(team_id_nullable=TEAM_ID).get_data_frames()[0]
    if games.empty:
        raise RuntimeError("No Celtics game data available.")
    return games.iloc[0]


def get_celtics_stats_message(game_row=None) -> str:
    if game_row is None:
        game_row = get_latest_celtics_game_row()

    game_id = str(game_row["GAME_ID"])
    print("Fetching box score for game", game_id)
    box_score = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
    players = box_score.get_data_frames()[0]

    celtics = players[players["teamTricode"] == "BOS"]
    celtics_clean = celtics[[
        "nameI",
        "minutes",
        "points",
        "reboundsTotal",
        "assists",
        "steals",
        "blocks",
    ]].copy()

    celtics_clean.columns = [
        "Player",
        "Min",
        "PTS",
        "REB",
        "AST",
        "STL",
        "BLK",
    ]

    celtics_clean = celtics_clean[celtics_clean["Min"].astype(str).str.strip() != ""]
    celtics_clean = celtics_clean.sort_values(by="PTS", ascending=False)

    matchup = str(game_row.get("MATCHUP", "BOS"))
    game_date = str(game_row.get("GAME_DATE", ""))
    result = str(game_row.get("WL", ""))

    title = "CELTICS BOX SCORE"
    header = f"{title:^70}"
    subheader = f"{game_date} | {matchup} {result}".strip()

    message = "🏀 " + header + "\n"
    message += f"{subheader:^70}" + "\n"
    message += "=" * 70 + "\n"
    message += f"{'PLAYER':<18}{'MIN':>6}{'PTS':>6}{'REB':>6}{'AST':>6}{'STL':>6}{'BLK':>6}\n"
    message += "-" * 70 + "\n"

    team_totals = {"PTS": 0, "REB": 0, "AST": 0, "STL": 0, "BLK": 0}
    for _, row in celtics_clean.iterrows():
        player = str(row["Player"])
        mins = str(row["Min"])
        pts = int(row["PTS"])
        reb = int(row["REB"])
        ast = int(row["AST"])
        stl = int(row["STL"])
        blk = int(row["BLK"])

        team_totals["PTS"] += pts
        team_totals["REB"] += reb
        team_totals["AST"] += ast
        team_totals["STL"] += stl
        team_totals["BLK"] += blk

        message += f"{player:<18}{mins:>6}{pts:>6}{reb:>6}{ast:>6}{stl:>6}{blk:>6}\n"

    message += "=" * 70 + "\n"
    message += f"{'TEAM TOTALS':<18}{'':>6}{team_totals['PTS']:>6}{team_totals['REB']:>6}{team_totals['AST']:>6}{team_totals['STL']:>6}{team_totals['BLK']:>6}\n"
    message += "=" * 70

    return message


if __name__ == "__main__":
    print(get_celtics_stats_message())
