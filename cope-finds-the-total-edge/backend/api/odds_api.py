"""
The Odds API integration for fetching NBA odds
Focuses on FanDuel totals (over/under)
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ODDS_API_KEY, ODDS_API_BASE, TEAM_NAME_MAP

logger = logging.getLogger(__name__)


class OddsAPI:
    """Client for The Odds API"""

    def __init__(self, api_key: str = ODDS_API_KEY):
        self.api_key = api_key
        self.base_url = ODDS_API_BASE
        self.sport = "basketball_nba"

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make a request to The Odds API"""
        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Log remaining requests
            remaining = response.headers.get("x-requests-remaining", "unknown")
            logger.info(f"Odds API requests remaining: {remaining}")

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Odds API request failed: {e}")
            return None

    def get_nba_games(self) -> list:
        """Get list of upcoming NBA games"""
        endpoint = f"sports/{self.sport}/events"
        data = self._make_request(endpoint)
        return data if data else []

    def get_nba_odds(self, markets: str = "totals", bookmakers: str = "fanduel") -> list:
        """
        Get NBA odds from FanDuel

        Args:
            markets: Type of odds (totals, spreads, h2h)
            bookmakers: Which sportsbook (fanduel, draftkings, etc.)

        Returns:
            List of games with odds
        """
        endpoint = f"sports/{self.sport}/odds"
        params = {
            "regions": "us",
            "markets": markets,
            "bookmakers": bookmakers,
            "oddsFormat": "american"
        }

        data = self._make_request(endpoint, params)
        return data if data else []

    def get_todays_games_with_totals(self) -> list:
        """
        Get today's NBA games with FanDuel totals

        Returns:
            List of game dictionaries with:
            - game_id
            - commence_time
            - home_team
            - away_team
            - fanduel_total
            - over_odds
            - under_odds
        """
        raw_odds = self.get_nba_odds(markets="totals", bookmakers="fanduel")

        if not raw_odds:
            logger.warning("No odds data received from API")
            return []

        games = []
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)

        for game in raw_odds:
            try:
                # Parse commence time
                commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
                game_date = commence_time.date()

                # Only include today's and tomorrow's games
                if game_date < today or game_date > tomorrow:
                    continue

                game_data = {
                    "game_id": game["id"],
                    "commence_time": commence_time,
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "home_team_abbrev": TEAM_NAME_MAP.get(game["home_team"], game["home_team"]),
                    "away_team_abbrev": TEAM_NAME_MAP.get(game["away_team"], game["away_team"]),
                    "fanduel_total": None,
                    "over_odds": None,
                    "under_odds": None
                }

                # Extract FanDuel totals
                bookmakers = game.get("bookmakers", [])
                for bookmaker in bookmakers:
                    if bookmaker["key"] == "fanduel":
                        markets = bookmaker.get("markets", [])
                        for market in markets:
                            if market["key"] == "totals":
                                outcomes = market.get("outcomes", [])
                                for outcome in outcomes:
                                    if outcome["name"] == "Over":
                                        game_data["fanduel_total"] = outcome["point"]
                                        game_data["over_odds"] = outcome["price"]
                                    elif outcome["name"] == "Under":
                                        game_data["under_odds"] = outcome["price"]

                # Only include games with valid totals
                if game_data["fanduel_total"] is not None:
                    games.append(game_data)
                    logger.info(
                        f"Found game: {game_data['away_team']} @ {game_data['home_team']} "
                        f"- Total: {game_data['fanduel_total']}"
                    )

            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing game data: {e}")
                continue

        logger.info(f"Found {len(games)} games with FanDuel totals")
        return games

    def get_remaining_requests(self) -> Optional[int]:
        """Check how many API requests are remaining"""
        # Make a minimal request to check headers
        endpoint = f"sports/{self.sport}/events"
        params = {"apiKey": self.api_key}
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            return int(response.headers.get("x-requests-remaining", 0))
        except Exception:
            return None


def main():
    """Test the Odds API client"""
    logging.basicConfig(level=logging.INFO)
    client = OddsAPI()

    print("\n=== Testing Odds API ===\n")

    # Get today's games with totals
    games = client.get_todays_games_with_totals()

    if games:
        print(f"Found {len(games)} games:\n")
        for game in games:
            print(f"  {game['away_team']} @ {game['home_team']}")
            print(f"    Time: {game['commence_time']}")
            print(f"    Total: {game['fanduel_total']}")
            print(f"    Over: {game['over_odds']}, Under: {game['under_odds']}")
            print()
    else:
        print("No games found (might be off-season or no games today)")

    # Check remaining requests
    remaining = client.get_remaining_requests()
    print(f"\nAPI requests remaining: {remaining}")


if __name__ == "__main__":
    main()
