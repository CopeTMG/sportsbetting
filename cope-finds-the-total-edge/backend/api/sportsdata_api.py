"""
SportsDataIO API integration for NBA injury data
"""
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SPORTSDATA_API_KEY, SPORTSDATA_API_BASE, STAR_PLAYERS, TEAM_NAME_MAP
from models import InjuryReport, get_session

logger = logging.getLogger(__name__)


# SportsDataIO team abbreviation mappings
SPORTSDATA_TEAM_MAP = {
    "ATL": "ATL",
    "BKN": "BKN",
    "BOS": "BOS",
    "CHA": "CHA",
    "CHI": "CHI",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GS": "GSW",
    "GSW": "GSW",
    "HOU": "HOU",
    "IND": "IND",
    "LAC": "LAC",
    "LAL": "LAL",
    "MEM": "MEM",
    "MIA": "MIA",
    "MIL": "MIL",
    "MIN": "MIN",
    "NO": "NOP",
    "NOP": "NOP",
    "NY": "NYK",
    "NYK": "NYK",
    "OKC": "OKC",
    "ORL": "ORL",
    "PHI": "PHI",
    "PHO": "PHX",
    "PHX": "PHX",
    "POR": "POR",
    "SAC": "SAC",
    "SA": "SAS",
    "SAS": "SAS",
    "TOR": "TOR",
    "UTA": "UTA",
    "WAS": "WAS",
}


class SportsDataAPI:
    """Client for SportsDataIO NBA API"""

    def __init__(self, api_key: str = SPORTSDATA_API_KEY):
        self.api_key = api_key
        self.base_url = SPORTSDATA_API_BASE

    def _make_request(self, endpoint: str) -> Optional[dict]:
        """Make a request to SportsDataIO API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SportsDataIO API request failed: {e}")
            return None

    def get_injuries(self) -> List[Dict]:
        """
        Get current NBA injuries

        Returns:
            List of injury dictionaries with:
            - player_id
            - player_name
            - team
            - team_abbrev
            - status (Out, Questionable, Probable, etc.)
            - injury
            - is_star_player
        """
        data = self._make_request("scores/json/InjuredPlayers")

        if not data:
            logger.warning("No injury data received")
            return []

        injuries = []

        for player in data:
            try:
                team_raw = player.get("Team", "")
                team_abbrev = SPORTSDATA_TEAM_MAP.get(team_raw, team_raw)
                player_name = player.get("Name", "")

                injury = {
                    "player_id": player.get("PlayerID"),
                    "player_name": player_name,
                    "team": team_raw,
                    "team_abbrev": team_abbrev,
                    "status": player.get("Status", "Unknown"),
                    "injury": player.get("Injury", "Unknown"),
                    "is_star_player": player_name in STAR_PLAYERS
                }

                injuries.append(injury)

            except Exception as e:
                logger.error(f"Error parsing injury data: {e}")
                continue

        logger.info(f"Found {len(injuries)} injured players")
        return injuries

    def get_injuries_by_team(self) -> Dict[str, List[Dict]]:
        """
        Get injuries organized by team

        Returns:
            Dictionary with team abbreviations as keys, list of injuries as values
        """
        injuries = self.get_injuries()
        by_team = {}

        for injury in injuries:
            team = injury["team_abbrev"]
            if team not in by_team:
                by_team[team] = []
            by_team[team].append(injury)

        return by_team

    def get_team_injuries(self, team_abbrev: str) -> List[Dict]:
        """Get injuries for a specific team"""
        all_injuries = self.get_injuries_by_team()
        return all_injuries.get(team_abbrev, [])

    def get_players_out(self, team_abbrev: str) -> List[Dict]:
        """
        Get players who are OUT for a specific team
        (These are the ones we need for projection adjustments)
        """
        team_injuries = self.get_team_injuries(team_abbrev)
        return [
            inj for inj in team_injuries
            if inj["status"].lower() in ["out", "o"]
        ]

    def save_injuries_to_database(self) -> int:
        """Fetch and save injuries to database"""
        injuries = self.get_injuries()
        session = get_session()
        saved_count = 0

        try:
            # Clear old injuries
            session.query(InjuryReport).delete()

            for inj in injuries:
                injury_record = InjuryReport(
                    player_id=inj["player_id"],
                    player_name=inj["player_name"],
                    team=inj["team"],
                    team_abbrev=inj["team_abbrev"],
                    status=inj["status"],
                    injury=inj["injury"],
                    is_star_player=inj["is_star_player"],
                    fetched_at=datetime.utcnow()
                )
                session.add(injury_record)
                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} injuries to database")

        except Exception as e:
            logger.error(f"Error saving injuries to database: {e}")
            session.rollback()
        finally:
            session.close()

        return saved_count

    def get_todays_games(self) -> List[Dict]:
        """Get today's NBA games from SportsDataIO"""
        today = datetime.now().strftime("%Y-%m-%d")
        endpoint = f"scores/json/GamesByDate/{today}"
        data = self._make_request(endpoint)
        return data if data else []

    def get_player_stats(self, player_id: int) -> Optional[Dict]:
        """Get player stats (for determining player impact)"""
        endpoint = f"stats/json/Player/{player_id}"
        return self._make_request(endpoint)


def get_injuries_for_teams(home_team: str, away_team: str) -> Dict[str, List[Dict]]:
    """
    Get injuries for both teams in a game

    Returns:
        Dictionary with "home" and "away" keys, each containing list of OUT players
    """
    api = SportsDataAPI()
    all_injuries = api.get_injuries_by_team()

    home_injuries = [
        inj for inj in all_injuries.get(home_team, [])
        if inj["status"].lower() in ["out", "o"]
    ]

    away_injuries = [
        inj for inj in all_injuries.get(away_team, [])
        if inj["status"].lower() in ["out", "o"]
    ]

    return {
        "home": home_injuries,
        "away": away_injuries,
        "home_team": home_team,
        "away_team": away_team
    }


def main():
    """Test the SportsDataIO API client"""
    logging.basicConfig(level=logging.INFO)

    print("\n=== Testing SportsDataIO API ===\n")

    api = SportsDataAPI()

    # Get all injuries
    injuries = api.get_injuries()

    if injuries:
        print(f"Found {len(injuries)} injured players:\n")

        # Group by team
        by_team = api.get_injuries_by_team()

        for team, team_injuries in sorted(by_team.items()):
            print(f"\n{team}:")
            for inj in team_injuries:
                star = "⭐ " if inj["is_star_player"] else "   "
                print(f"  {star}{inj['player_name']} - {inj['status']} ({inj['injury']})")

        # Count star players out
        star_count = sum(1 for inj in injuries if inj["is_star_player"] and inj["status"].lower() in ["out", "o"])
        print(f"\n\nStar players OUT: {star_count}")

        # Save to database
        print("\nSaving to database...")
        saved = api.save_injuries_to_database()
        print(f"Saved {saved} injuries to database")
    else:
        print("No injuries found (or API error)")


if __name__ == "__main__":
    main()
