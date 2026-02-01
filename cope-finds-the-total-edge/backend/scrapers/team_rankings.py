"""
Team Rankings scraper for NBA team statistics
Scrapes: Offensive Efficiency, Defensive Efficiency, Pace
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, Optional
import logging
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    TEAM_RANKINGS_OFFENSE_URL,
    TEAM_RANKINGS_DEFENSE_URL,
    TEAM_RANKINGS_PACE_URL,
    TEAM_NAME_MAP
)
from models import TeamStats, get_session

logger = logging.getLogger(__name__)


# Team name mappings for Team Rankings site
TEAM_RANKINGS_NAME_MAP = {
    # Atlanta Hawks
    "Atlanta": "ATL",
    "Atlanta Hawks": "ATL",
    "Hawks": "ATL",
    # Boston Celtics
    "Boston": "BOS",
    "Boston Celtics": "BOS",
    "Celtics": "BOS",
    # Brooklyn Nets
    "Brooklyn": "BKN",
    "Brooklyn Nets": "BKN",
    "Nets": "BKN",
    # Charlotte Hornets
    "Charlotte": "CHA",
    "Charlotte Hornets": "CHA",
    "Hornets": "CHA",
    # Chicago Bulls
    "Chicago": "CHI",
    "Chicago Bulls": "CHI",
    "Bulls": "CHI",
    # Cleveland Cavaliers
    "Cleveland": "CLE",
    "Cleveland Cavaliers": "CLE",
    "Cavaliers": "CLE",
    "Cavs": "CLE",
    # Dallas Mavericks
    "Dallas": "DAL",
    "Dallas Mavericks": "DAL",
    "Mavericks": "DAL",
    "Mavs": "DAL",
    # Denver Nuggets
    "Denver": "DEN",
    "Denver Nuggets": "DEN",
    "Nuggets": "DEN",
    # Detroit Pistons
    "Detroit": "DET",
    "Detroit Pistons": "DET",
    "Pistons": "DET",
    # Golden State Warriors
    "Golden State": "GSW",
    "Golden St": "GSW",
    "Golden State Warriors": "GSW",
    "Warriors": "GSW",
    # Houston Rockets
    "Houston": "HOU",
    "Houston Rockets": "HOU",
    "Rockets": "HOU",
    # Indiana Pacers
    "Indiana": "IND",
    "Indiana Pacers": "IND",
    "Pacers": "IND",
    # Los Angeles Clippers
    "LA Clippers": "LAC",
    "L.A. Clippers": "LAC",
    "Los Angeles Clippers": "LAC",
    "Clippers": "LAC",
    # Los Angeles Lakers
    "LA Lakers": "LAL",
    "L.A. Lakers": "LAL",
    "Los Angeles Lakers": "LAL",
    "Lakers": "LAL",
    # Memphis Grizzlies
    "Memphis": "MEM",
    "Memphis Grizzlies": "MEM",
    "Grizzlies": "MEM",
    # Miami Heat
    "Miami": "MIA",
    "Miami Heat": "MIA",
    "Heat": "MIA",
    # Milwaukee Bucks
    "Milwaukee": "MIL",
    "Milwaukee Bucks": "MIL",
    "Bucks": "MIL",
    # Minnesota Timberwolves
    "Minnesota": "MIN",
    "Minnesota Timberwolves": "MIN",
    "Timberwolves": "MIN",
    "Wolves": "MIN",
    # New Orleans Pelicans
    "New Orleans": "NOP",
    "New Orleans Pelicans": "NOP",
    "Pelicans": "NOP",
    # New York Knicks
    "New York": "NYK",
    "New York Knicks": "NYK",
    "Knicks": "NYK",
    # Oklahoma City Thunder
    "Oklahoma City": "OKC",
    "Okla City": "OKC",
    "Oklahoma City Thunder": "OKC",
    "Thunder": "OKC",
    # Orlando Magic
    "Orlando": "ORL",
    "Orlando Magic": "ORL",
    "Magic": "ORL",
    # Philadelphia 76ers
    "Philadelphia": "PHI",
    "Philadelphia 76ers": "PHI",
    "76ers": "PHI",
    "Sixers": "PHI",
    # Phoenix Suns
    "Phoenix": "PHX",
    "Phoenix Suns": "PHX",
    "Suns": "PHX",
    # Portland Trail Blazers
    "Portland": "POR",
    "Portland Trail Blazers": "POR",
    "Trail Blazers": "POR",
    "Blazers": "POR",
    # Sacramento Kings
    "Sacramento": "SAC",
    "Sacramento Kings": "SAC",
    "Kings": "SAC",
    # San Antonio Spurs
    "San Antonio": "SAS",
    "San Antonio Spurs": "SAS",
    "Spurs": "SAS",
    # Toronto Raptors
    "Toronto": "TOR",
    "Toronto Raptors": "TOR",
    "Raptors": "TOR",
    # Utah Jazz
    "Utah": "UTA",
    "Utah Jazz": "UTA",
    "Jazz": "UTA",
    # Washington Wizards
    "Washington": "WAS",
    "Washington Wizards": "WAS",
    "Wizards": "WAS",
}


class TeamRankingsScraper:
    """Scraper for Team Rankings NBA statistics"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _parse_team_name(self, name: str) -> Optional[str]:
        """Convert team name to abbreviation"""
        name = name.strip()

        # Try direct match
        if name in TEAM_RANKINGS_NAME_MAP:
            return TEAM_RANKINGS_NAME_MAP[name]

        # Try partial match
        for key, abbrev in TEAM_RANKINGS_NAME_MAP.items():
            if key.lower() in name.lower() or name.lower() in key.lower():
                return abbrev

        logger.warning(f"Could not map team name: {name}")
        return None

    def _parse_stat_table(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Parse the statistics table from Team Rankings"""
        stats = {}

        try:
            # Find the main data table
            table = soup.find("table", {"class": "tr-table"})
            if not table:
                table = soup.find("table", {"id": "DataTables_Table_0"})
            if not table:
                # Try finding any table with data
                tables = soup.find_all("table")
                for t in tables:
                    if t.find("tbody"):
                        table = t
                        break

            if not table:
                logger.error("Could not find stats table")
                return stats

            tbody = table.find("tbody")
            if not tbody:
                logger.error("Could not find table body")
                return stats

            rows = tbody.find_all("tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    # Team Rankings table structure:
                    # Column 0: Rank (1, 2, 3...)
                    # Column 1: Team name (with link)
                    # Column 2: Current season stat value
                    team_cell = cells[1]  # Team name is in second column
                    team_link = team_cell.find("a")
                    team_name = team_link.text.strip() if team_link else team_cell.text.strip()

                    # Stat value is in third cell (current season)
                    stat_value = cells[2].text.strip()

                    team_abbrev = self._parse_team_name(team_name)
                    if team_abbrev:
                        try:
                            # Remove any non-numeric characters except decimal point
                            stat_value = re.sub(r"[^\d.]", "", stat_value)
                            stats[team_abbrev] = float(stat_value)
                        except ValueError:
                            logger.warning(f"Could not parse stat value: {stat_value}")

        except Exception as e:
            logger.error(f"Error parsing stat table: {e}")

        return stats

    def scrape_offensive_efficiency(self) -> Dict[str, float]:
        """Scrape offensive efficiency ratings"""
        logger.info("Scraping offensive efficiency...")
        soup = self._fetch_page(TEAM_RANKINGS_OFFENSE_URL)
        if soup:
            stats = self._parse_stat_table(soup)
            logger.info(f"Got offensive efficiency for {len(stats)} teams")
            return stats
        return {}

    def scrape_defensive_efficiency(self) -> Dict[str, float]:
        """Scrape defensive efficiency ratings"""
        logger.info("Scraping defensive efficiency...")
        soup = self._fetch_page(TEAM_RANKINGS_DEFENSE_URL)
        if soup:
            stats = self._parse_stat_table(soup)
            logger.info(f"Got defensive efficiency for {len(stats)} teams")
            return stats
        return {}

    def scrape_pace(self) -> Dict[str, float]:
        """Scrape pace (possessions per game)"""
        logger.info("Scraping pace...")
        soup = self._fetch_page(TEAM_RANKINGS_PACE_URL)
        if soup:
            stats = self._parse_stat_table(soup)
            logger.info(f"Got pace for {len(stats)} teams")
            return stats
        return {}

    def scrape_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Scrape all team statistics

        Returns:
            Dictionary with team abbreviations as keys, containing:
            - offensive_efficiency
            - defensive_efficiency
            - pace
        """
        off_eff = self.scrape_offensive_efficiency()
        def_eff = self.scrape_defensive_efficiency()
        pace = self.scrape_pace()

        # Combine all stats
        all_teams = set(list(off_eff.keys()) + list(def_eff.keys()) + list(pace.keys()))

        combined = {}
        for team in all_teams:
            combined[team] = {
                "offensive_efficiency": off_eff.get(team),
                "defensive_efficiency": def_eff.get(team),
                "pace": pace.get(team)
            }

        return combined

    def save_to_database(self, stats: Dict[str, Dict[str, float]]) -> int:
        """Save scraped stats to database"""
        session = get_session()
        saved_count = 0

        try:
            for team_abbrev, team_stats in stats.items():
                # Check if we have all three stats
                if all(team_stats.get(k) is not None for k in ["offensive_efficiency", "defensive_efficiency", "pace"]):
                    # Delete old stats for this team
                    session.query(TeamStats).filter(TeamStats.team_abbrev == team_abbrev).delete()

                    # Insert new stats
                    new_stats = TeamStats(
                        team_abbrev=team_abbrev,
                        team_name=team_abbrev,  # Will be updated with full name if needed
                        offensive_efficiency=team_stats["offensive_efficiency"],
                        defensive_efficiency=team_stats["defensive_efficiency"],
                        pace=team_stats["pace"],
                        scraped_at=datetime.utcnow()
                    )
                    session.add(new_stats)
                    saved_count += 1

            session.commit()
            logger.info(f"Saved stats for {saved_count} teams to database")

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            session.rollback()
        finally:
            session.close()

        return saved_count


def get_team_stats() -> Dict[str, Dict[str, float]]:
    """
    Get team stats from database or scrape if not available

    Returns:
        Dictionary of team stats
    """
    session = get_session()

    try:
        # Get most recent stats from database
        stats = session.query(TeamStats).all()

        if stats:
            # Check if stats are recent (within 24 hours)
            most_recent = max(s.scraped_at for s in stats)
            if (datetime.utcnow() - most_recent).total_seconds() < 86400:
                return {
                    s.team_abbrev: {
                        "offensive_efficiency": s.offensive_efficiency,
                        "defensive_efficiency": s.defensive_efficiency,
                        "pace": s.pace
                    }
                    for s in stats
                }

        # Scrape fresh stats
        scraper = TeamRankingsScraper()
        new_stats = scraper.scrape_all_stats()
        scraper.save_to_database(new_stats)
        return new_stats

    finally:
        session.close()


def main():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)

    print("\n=== Testing Team Rankings Scraper ===\n")

    scraper = TeamRankingsScraper()
    stats = scraper.scrape_all_stats()

    if stats:
        print(f"Scraped stats for {len(stats)} teams:\n")

        # Sort by offensive efficiency
        sorted_teams = sorted(
            stats.items(),
            key=lambda x: x[1].get("offensive_efficiency", 0) or 0,
            reverse=True
        )

        print(f"{'Team':<6} {'Off Eff':>8} {'Def Eff':>8} {'Pace':>8}")
        print("-" * 35)

        for team, team_stats in sorted_teams:
            off = team_stats.get("offensive_efficiency", "N/A")
            def_ = team_stats.get("defensive_efficiency", "N/A")
            pace = team_stats.get("pace", "N/A")

            off_str = f"{off:.1f}" if isinstance(off, float) else off
            def_str = f"{def_:.1f}" if isinstance(def_, float) else def_
            pace_str = f"{pace:.1f}" if isinstance(pace, float) else pace

            print(f"{team:<6} {off_str:>8} {def_str:>8} {pace_str:>8}")

        # Save to database
        print("\nSaving to database...")
        saved = scraper.save_to_database(stats)
        print(f"Saved {saved} teams to database")
    else:
        print("Failed to scrape stats")


if __name__ == "__main__":
    main()
