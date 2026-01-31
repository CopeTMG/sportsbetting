"""
Configuration for Cope Finds the Total Edge
NBA Totals Betting Calculator
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "422cc16604f89831f448bbe16798f7ee")
SPORTSDATA_API_KEY = os.getenv("SPORTSDATA_API_KEY", "4638cd6877924bd6bdcc5bbf0369aa40")

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER", "+12253042634")

# API Endpoints
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORTSDATA_API_BASE = "https://api.sportsdata.io/v3/nba"

# Team Rankings URL for scraping
TEAM_RANKINGS_OFFENSE_URL = "https://www.teamrankings.com/nba/stat/offensive-efficiency"
TEAM_RANKINGS_DEFENSE_URL = "https://www.teamrankings.com/nba/stat/defensive-efficiency"
TEAM_RANKINGS_PACE_URL = "https://www.teamrankings.com/nba/stat/possessions-per-game"

# Database
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "betting.db")

# Edge threshold for alerts
EDGE_THRESHOLD = 5.0

# Injury adjustment percentages
STAR_PLAYER_ADJUSTMENT = 0.04  # 4% (middle of 3-5%)
ROTATION_PLAYER_ADJUSTMENT = 0.02  # 2% (middle of 1-3%)

# Schedule times (24-hour format)
SCHEDULE_TIMES = ["09:00", "15:00"]

# Logging
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "app.log")

# NBA Team name mappings (different APIs use different names)
TEAM_NAME_MAP = {
    # The Odds API names -> Standard abbreviations
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "LA Clippers": "LAC",
    "LA Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

# Reverse mapping
ABBREV_TO_FULL = {v: k for k, v in TEAM_NAME_MAP.items()}

# Star players list (for injury adjustments)
STAR_PLAYERS = [
    "LeBron James", "Stephen Curry", "Kevin Durant", "Giannis Antetokounmpo",
    "Luka Doncic", "Nikola Jokic", "Joel Embiid", "Jayson Tatum", "Ja Morant",
    "Damian Lillard", "Anthony Davis", "Devin Booker", "Trae Young",
    "Donovan Mitchell", "Jimmy Butler", "Kawhi Leonard", "Paul George",
    "Anthony Edwards", "Shai Gilgeous-Alexander", "Tyrese Haliburton",
    "De'Aaron Fox", "Zion Williamson", "LaMelo Ball", "Bam Adebayo",
    "Domantas Sabonis", "Karl-Anthony Towns", "Kyrie Irving", "James Harden",
    "Jaylen Brown", "Paolo Banchero", "Chet Holmgren", "Victor Wembanyama",
    "Jalen Brunson", "Tyrese Maxey", "Lauri Markkanen", "Scottie Barnes"
]
