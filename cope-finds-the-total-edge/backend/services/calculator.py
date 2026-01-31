"""
NBA Totals Calculation Engine
Core logic for Cope Finds the Total Edge
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    STAR_PLAYER_ADJUSTMENT,
    ROTATION_PLAYER_ADJUSTMENT,
    EDGE_THRESHOLD
)
from api.odds_api import OddsAPI
from api.sportsdata_api import SportsDataAPI, get_injuries_for_teams
from scrapers.team_rankings import TeamRankingsScraper, get_team_stats
from models import Game, get_session, init_db

logger = logging.getLogger(__name__)


class TotalsCalculator:
    """
    Calculate projected NBA game totals using efficiency and pace metrics

    Formula:
    Team A Score = (Team A Off Eff × Team A Pace + Team B Def Eff × Team A Pace) / 2
    Team B Score = (Team B Off Eff × Team B Pace + Team A Def Eff × Team B Pace) / 2
    Game Total = Team A Score + Team B Score
    """

    def __init__(self):
        self.odds_api = OddsAPI()
        self.sportsdata_api = SportsDataAPI()
        self.team_stats = {}
        self.injuries = {}

    def load_data(self) -> bool:
        """Load all required data"""
        logger.info("Loading team stats and injury data...")

        # Load team stats
        self.team_stats = get_team_stats()
        if not self.team_stats:
            logger.error("Failed to load team stats")
            return False

        logger.info(f"Loaded stats for {len(self.team_stats)} teams")

        # Load injuries
        self.injuries = self.sportsdata_api.get_injuries_by_team()
        logger.info(f"Loaded injuries for {len(self.injuries)} teams")

        return True

    def calculate_team_score(
        self,
        team_off_eff: float,
        team_pace: float,
        opp_def_eff: float
    ) -> float:
        """
        Calculate projected score for one team

        Formula: (Team Off Eff × Team Pace + Opp Def Eff × Team Pace) / 2

        Note: Efficiency is points per 100 possessions
        Pace is possessions per game
        So we need to normalize: (Efficiency / 100) * Pace
        """
        # Average the team's offensive efficiency with opponent's defensive efficiency
        # Then multiply by the team's pace, normalized to per-possession
        avg_eff = (team_off_eff + opp_def_eff) / 2
        projected_score = (avg_eff / 100) * team_pace

        return projected_score

    def calculate_game_total(
        self,
        home_team: str,
        away_team: str
    ) -> Optional[Dict]:
        """
        Calculate projected total for a game

        Returns dict with projected scores and total, or None if data missing
        """
        # Get team stats
        home_stats = self.team_stats.get(home_team)
        away_stats = self.team_stats.get(away_team)

        if not home_stats or not away_stats:
            logger.warning(f"Missing stats for {home_team} or {away_team}")
            return None

        # Check we have all required stats
        required = ["offensive_efficiency", "defensive_efficiency", "pace"]
        for stat in required:
            if home_stats.get(stat) is None or away_stats.get(stat) is None:
                logger.warning(f"Missing {stat} for {home_team} or {away_team}")
                return None

        # Calculate raw projections
        home_score = self.calculate_team_score(
            team_off_eff=home_stats["offensive_efficiency"],
            team_pace=home_stats["pace"],
            opp_def_eff=away_stats["defensive_efficiency"]
        )

        away_score = self.calculate_team_score(
            team_off_eff=away_stats["offensive_efficiency"],
            team_pace=away_stats["pace"],
            opp_def_eff=home_stats["defensive_efficiency"]
        )

        raw_total = home_score + away_score

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_stats": home_stats,
            "away_stats": away_stats,
            "projected_home_score": round(home_score, 1),
            "projected_away_score": round(away_score, 1),
            "raw_projected_total": round(raw_total, 1)
        }

    def calculate_injury_adjustment(
        self,
        home_team: str,
        away_team: str
    ) -> Tuple[float, List[Dict]]:
        """
        Calculate total adjustment based on injuries

        Returns:
            Tuple of (adjustment_points, list of injured players)
        """
        adjustment = 0.0
        injured_players = []

        # Get injuries for both teams
        home_injuries = self.injuries.get(home_team, [])
        away_injuries = self.injuries.get(away_team, [])

        for team, team_injuries in [(home_team, home_injuries), (away_team, away_injuries)]:
            for inj in team_injuries:
                # Only adjust for players who are OUT
                if inj["status"].lower() not in ["out", "o"]:
                    continue

                injured_players.append({
                    "team": team,
                    "name": inj["player_name"],
                    "is_star": inj["is_star_player"],
                    "status": inj["status"],
                    "injury": inj.get("injury", "Unknown")
                })

                # Calculate adjustment
                # Star players reduce projected total more
                if inj["is_star_player"]:
                    # Star player out reduces total by 3-5% (we use 4%)
                    # Applied to the average NBA game total (~225)
                    adj = 225 * STAR_PLAYER_ADJUSTMENT
                    logger.info(f"Star player {inj['player_name']} OUT - adjusting by -{adj:.1f}")
                else:
                    # Rotation player out reduces total by 1-3% (we use 2%)
                    adj = 225 * ROTATION_PLAYER_ADJUSTMENT
                    logger.debug(f"Rotation player {inj['player_name']} OUT - adjusting by -{adj:.1f}")

                adjustment -= adj

        return round(adjustment, 1), injured_players

    def analyze_game(self, game_data: Dict) -> Optional[Dict]:
        """
        Full analysis of a single game

        Args:
            game_data: Dictionary from OddsAPI with game info and FanDuel odds

        Returns:
            Complete analysis including projection, edge, and recommendations
        """
        home_team = game_data.get("home_team_abbrev")
        away_team = game_data.get("away_team_abbrev")
        fanduel_total = game_data.get("fanduel_total")

        if not all([home_team, away_team, fanduel_total]):
            logger.warning("Missing required game data")
            return None

        # Calculate raw projection
        projection = self.calculate_game_total(home_team, away_team)
        if not projection:
            return None

        # Calculate injury adjustment
        injury_adj, injured_players = self.calculate_injury_adjustment(home_team, away_team)

        # Apply injury adjustment to get final projection
        adjusted_total = projection["raw_projected_total"] + injury_adj

        # Calculate edge
        edge = adjusted_total - fanduel_total

        # Determine direction
        if edge > 0:
            edge_direction = "OVER"
        elif edge < 0:
            edge_direction = "UNDER"
        else:
            edge_direction = "NONE"

        # Flag significant edges
        has_edge = abs(edge) >= EDGE_THRESHOLD

        analysis = {
            # Game info
            "game_id": game_data.get("game_id"),
            "commence_time": game_data.get("commence_time"),
            "home_team": game_data.get("home_team"),
            "away_team": game_data.get("away_team"),
            "home_team_abbrev": home_team,
            "away_team_abbrev": away_team,

            # FanDuel odds
            "fanduel_total": fanduel_total,
            "over_odds": game_data.get("over_odds"),
            "under_odds": game_data.get("under_odds"),

            # Team stats
            "home_off_eff": projection["home_stats"]["offensive_efficiency"],
            "home_def_eff": projection["home_stats"]["defensive_efficiency"],
            "home_pace": projection["home_stats"]["pace"],
            "away_off_eff": projection["away_stats"]["offensive_efficiency"],
            "away_def_eff": projection["away_stats"]["defensive_efficiency"],
            "away_pace": projection["away_stats"]["pace"],

            # Projections
            "projected_home_score": projection["projected_home_score"],
            "projected_away_score": projection["projected_away_score"],
            "raw_projected_total": projection["raw_projected_total"],
            "injury_adjustment": injury_adj,
            "adjusted_projected_total": round(adjusted_total, 1),

            # Edge analysis
            "edge": round(edge, 1),
            "edge_direction": edge_direction,
            "has_significant_edge": has_edge,

            # Injuries
            "injured_players": injured_players,
            "injured_players_count": len(injured_players),

            # Timestamp
            "analyzed_at": datetime.utcnow().isoformat()
        }

        return analysis

    def analyze_todays_games(self) -> List[Dict]:
        """
        Analyze all of today's games

        Returns:
            List of game analyses sorted by edge magnitude
        """
        # Load fresh data
        if not self.load_data():
            logger.error("Failed to load required data")
            return []

        # Get today's games with odds
        games = self.odds_api.get_todays_games_with_totals()
        if not games:
            logger.info("No games found for today")
            return []

        logger.info(f"Analyzing {len(games)} games...")

        analyses = []
        for game in games:
            analysis = self.analyze_game(game)
            if analysis:
                analyses.append(analysis)

        # Sort by absolute edge (biggest edges first)
        analyses.sort(key=lambda x: abs(x["edge"]), reverse=True)

        return analyses

    def save_analyses_to_database(self, analyses: List[Dict]) -> int:
        """Save game analyses to database"""
        session = get_session()
        saved_count = 0

        try:
            for analysis in analyses:
                # Check if game already exists
                existing = session.query(Game).filter(
                    Game.game_id == analysis["game_id"]
                ).first()

                if existing:
                    # Update existing record
                    for key, value in {
                        "fanduel_total": analysis["fanduel_total"],
                        "fanduel_over_odds": analysis["over_odds"],
                        "fanduel_under_odds": analysis["under_odds"],
                        "home_off_eff": analysis["home_off_eff"],
                        "home_def_eff": analysis["home_def_eff"],
                        "home_pace": analysis["home_pace"],
                        "away_off_eff": analysis["away_off_eff"],
                        "away_def_eff": analysis["away_def_eff"],
                        "away_pace": analysis["away_pace"],
                        "projected_home_score": analysis["projected_home_score"],
                        "projected_away_score": analysis["projected_away_score"],
                        "projected_total": analysis["adjusted_projected_total"],
                        "raw_projected_total": analysis["raw_projected_total"],
                        "edge": analysis["edge"],
                        "edge_direction": analysis["edge_direction"],
                        "injury_adjustment": analysis["injury_adjustment"],
                        "injured_players": json.dumps(analysis["injured_players"]),
                    }.items():
                        setattr(existing, key, value)
                else:
                    # Create new record
                    game = Game(
                        game_id=analysis["game_id"],
                        game_date=analysis["commence_time"],
                        home_team=analysis["home_team"],
                        away_team=analysis["away_team"],
                        fanduel_total=analysis["fanduel_total"],
                        fanduel_over_odds=analysis["over_odds"],
                        fanduel_under_odds=analysis["under_odds"],
                        home_off_eff=analysis["home_off_eff"],
                        home_def_eff=analysis["home_def_eff"],
                        home_pace=analysis["home_pace"],
                        away_off_eff=analysis["away_off_eff"],
                        away_def_eff=analysis["away_def_eff"],
                        away_pace=analysis["away_pace"],
                        projected_home_score=analysis["projected_home_score"],
                        projected_away_score=analysis["projected_away_score"],
                        projected_total=analysis["adjusted_projected_total"],
                        raw_projected_total=analysis["raw_projected_total"],
                        edge=analysis["edge"],
                        edge_direction=analysis["edge_direction"],
                        injury_adjustment=analysis["injury_adjustment"],
                        injured_players=json.dumps(analysis["injured_players"]),
                    )
                    session.add(game)

                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} game analyses to database")

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            session.rollback()
        finally:
            session.close()

        return saved_count

    def get_significant_edges(self, analyses: List[Dict]) -> List[Dict]:
        """Get games with significant edges (5+ points)"""
        return [a for a in analyses if a["has_significant_edge"]]


def run_analysis() -> List[Dict]:
    """
    Run full analysis pipeline

    Returns:
        List of game analyses
    """
    # Initialize database
    init_db()

    # Run analysis
    calculator = TotalsCalculator()
    analyses = calculator.analyze_todays_games()

    if analyses:
        # Save to database
        calculator.save_analyses_to_database(analyses)

    return analyses


def main():
    """Test the calculator"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("   COPE FINDS THE TOTAL EDGE - NBA Totals Calculator")
    print("=" * 60 + "\n")

    analyses = run_analysis()

    if not analyses:
        print("No games to analyze today.")
        return

    print(f"Analyzed {len(analyses)} games:\n")

    # Print each game
    for i, game in enumerate(analyses, 1):
        edge_flag = "🔥" if game["has_significant_edge"] else "  "

        print(f"{edge_flag} Game {i}: {game['away_team']} @ {game['home_team']}")
        print(f"   Time: {game['commence_time']}")
        print(f"   FanDuel Total: {game['fanduel_total']}")
        print(f"   Our Projection: {game['adjusted_projected_total']} (raw: {game['raw_projected_total']})")
        print(f"   Injury Adjustment: {game['injury_adjustment']}")
        print(f"   EDGE: {game['edge']:+.1f} points ({game['edge_direction']})")

        if game["injured_players"]:
            print(f"   Injuries ({game['injured_players_count']}):")
            for inj in game["injured_players"]:
                star = "⭐" if inj["is_star"] else ""
                print(f"      - {inj['name']} ({inj['team']}) {star}")
        print()

    # Summary of significant edges
    significant = [g for g in analyses if g["has_significant_edge"]]
    if significant:
        print("\n" + "=" * 60)
        print(f"   🎯 SIGNIFICANT EDGES FOUND: {len(significant)}")
        print("=" * 60)

        for game in significant:
            print(f"\n   {game['away_team']} @ {game['home_team']}")
            print(f"   Play: {game['edge_direction']} {game['fanduel_total']}")
            print(f"   Edge: {abs(game['edge']):.1f} points")
    else:
        print("\n   No significant edges (5+ points) found today.")


if __name__ == "__main__":
    main()
