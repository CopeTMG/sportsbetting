# 🏀 Cope Finds the Total Edge

**NBA Totals Betting Calculator** - An automated system for finding edges in NBA game totals.

## Features

- **Real-time Odds**: Fetches FanDuel totals from The Odds API
- **Team Analytics**: Scrapes Team Rankings for offensive/defensive efficiency and pace
- **Injury Adjustments**: Pulls injury data from SportsDataIO and adjusts projections
- **Edge Detection**: Flags games with 5+ point edges
- **SMS Alerts**: Sends text alerts when significant edges are found
- **Automated Scheduling**: Runs analysis at 9 AM and 3 PM daily
- **Web Dashboard**: Track games, bets, and ROI
- **Bet Tracking**: Record bets and track performance

## Projection Formula

```
Team A Score = (Team A Off Eff × Team A Pace + Team B Def Eff × Team A Pace) / 2
Team B Score = (Team B Off Eff × Team B Pace + Team A Def Eff × Team B Pace) / 2
Game Total = Team A Score + Team B Score
```

### Injury Adjustments
- Star players OUT: -3-5% on projected total
- Rotation players OUT: -1-3% on projected total

## Quick Start

```bash
# Clone and setup
cd cope-finds-the-total-edge
chmod +x setup.sh
./setup.sh

# Activate environment
source venv/bin/activate

# Run the application
python run.py full
```

## Commands

| Command | Description |
|---------|-------------|
| `python run.py web` | Start web dashboard only |
| `python run.py analyze` | Run one-time analysis |
| `python run.py schedule` | Start with scheduler (9 AM & 3 PM) |
| `python run.py full` | Run analysis + start with scheduler |
| `python run.py test-alert` | Send a test SMS |

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# API Keys (already configured)
ODDS_API_KEY=your_key
SPORTSDATA_API_KEY=your_key

# Twilio (for SMS alerts)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
ALERT_PHONE_NUMBER=+12253042634
```

## Web Dashboard

Access at `http://localhost:5000` after starting.

**Features:**
- Today's games with projections
- Edge highlighting (5+ points)
- Injury reports
- Bet tracking
- ROI statistics
- Manual refresh button
- SMS alert trigger

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/games` | GET | Get today's games with projections |
| `/api/refresh` | POST | Refresh all data |
| `/api/bets` | GET/POST | Get or create bets |
| `/api/bets/<id>/settle` | POST | Settle a bet |
| `/api/stats` | GET | Get betting statistics |
| `/api/injuries` | GET | Get injury report |
| `/api/team-stats` | GET | Get team statistics |
| `/api/send-alert` | POST | Send SMS alert |

## Project Structure

```
cope-finds-the-total-edge/
├── backend/
│   ├── api/
│   │   ├── odds_api.py         # The Odds API client
│   │   └── sportsdata_api.py   # SportsDataIO client
│   ├── scrapers/
│   │   └── team_rankings.py    # Team Rankings scraper
│   ├── services/
│   │   ├── calculator.py       # Projection engine
│   │   ├── alerts.py           # SMS alerts
│   │   └── scheduler.py        # Job scheduler
│   ├── models/
│   │   └── database.py         # SQLite models
│   ├── app.py                  # Flask application
│   └── config.py               # Configuration
├── frontend/
│   ├── templates/
│   │   └── index.html          # Dashboard template
│   └── static/
│       ├── css/style.css       # Styles
│       └── js/app.js           # Dashboard JS
├── data/                       # SQLite database
├── logs/                       # Application logs
├── run.py                      # Main entry point
├── requirements.txt            # Python dependencies
└── setup.sh                    # Setup script
```

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **APIs**: The Odds API, SportsDataIO
- **SMS**: Twilio
- **Scheduling**: APScheduler

## Deployment

### Local
```bash
python run.py full
```

### Cloud (e.g., Railway, Heroku)
1. Set environment variables
2. Install dependencies: `pip install -r requirements.txt`
3. Start: `python run.py schedule --host 0.0.0.0 --port $PORT`

## License

MIT

---

Built for finding edges in NBA totals betting. Use responsibly.
