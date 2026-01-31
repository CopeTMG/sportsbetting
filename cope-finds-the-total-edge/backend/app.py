"""
Flask Web Application for Cope Finds the Total Edge
NBA Totals Betting Calculator Dashboard
"""
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATABASE_PATH, EDGE_THRESHOLD
from models import Game, Bet, TeamStats, Alert, InjuryReport, init_db, get_session
from services.calculator import TotalsCalculator, run_analysis
from services.alerts import SMSAlertService

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static")
)
CORS(app)

# Initialize database
init_db()


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("index.html")


@app.route("/api/games")
def get_games():
    """Get today's games with projections"""
    session = get_session()

    try:
        # Get today's games from database
        today = datetime.utcnow().date()
        games = session.query(Game).filter(
            Game.game_date >= datetime(today.year, today.month, today.day)
        ).order_by(Game.edge.desc()).all()

        result = []
        for game in games:
            injured = json.loads(game.injured_players) if game.injured_players else []
            result.append({
                "id": game.id,
                "game_id": game.game_id,
                "game_date": game.game_date.isoformat() if game.game_date else None,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "fanduel_total": game.fanduel_total,
                "over_odds": game.fanduel_over_odds,
                "under_odds": game.fanduel_under_odds,
                "projected_total": game.projected_total,
                "raw_projected_total": game.raw_projected_total,
                "injury_adjustment": game.injury_adjustment,
                "edge": game.edge,
                "edge_direction": game.edge_direction,
                "has_edge": abs(game.edge or 0) >= EDGE_THRESHOLD,
                "injured_players": injured,
                "home_stats": {
                    "off_eff": game.home_off_eff,
                    "def_eff": game.home_def_eff,
                    "pace": game.home_pace
                },
                "away_stats": {
                    "off_eff": game.away_off_eff,
                    "def_eff": game.away_def_eff,
                    "pace": game.away_pace
                }
            })

        return jsonify({"success": True, "games": result, "count": len(result)})

    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/refresh", methods=["POST"])
def refresh_data():
    """Refresh all data - fetch new odds and recalculate"""
    try:
        logger.info("Starting data refresh...")
        analyses = run_analysis()

        # Check for edges and send alerts
        significant = [a for a in analyses if a.get("has_significant_edge")]
        if significant:
            alert_service = SMSAlertService()
            alert_service.send_edge_alert(significant)

        return jsonify({
            "success": True,
            "message": f"Analyzed {len(analyses)} games",
            "games_with_edges": len(significant)
        })

    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bets", methods=["GET", "POST"])
def bets():
    """Get or create bets"""
    session = get_session()

    try:
        if request.method == "GET":
            # Get all bets
            all_bets = session.query(Bet).order_by(Bet.placed_at.desc()).all()
            result = []

            for bet in all_bets:
                result.append({
                    "id": bet.id,
                    "game_id": bet.game_id,
                    "game_date": bet.game_date.isoformat() if bet.game_date else None,
                    "home_team": bet.home_team,
                    "away_team": bet.away_team,
                    "bet_type": bet.bet_type,
                    "line": bet.line,
                    "odds": bet.odds,
                    "stake": bet.stake,
                    "projected_total": bet.projected_total,
                    "edge": bet.edge,
                    "result": bet.result,
                    "actual_total": bet.actual_total,
                    "profit": bet.profit,
                    "placed_at": bet.placed_at.isoformat() if bet.placed_at else None,
                    "settled_at": bet.settled_at.isoformat() if bet.settled_at else None
                })

            return jsonify({"success": True, "bets": result})

        elif request.method == "POST":
            # Create new bet
            data = request.json

            bet = Bet(
                game_id=data["game_id"],
                game_date=datetime.fromisoformat(data["game_date"]),
                home_team=data["home_team"],
                away_team=data["away_team"],
                bet_type=data["bet_type"],
                line=data["line"],
                odds=data["odds"],
                stake=data["stake"],
                projected_total=data.get("projected_total"),
                edge=data.get("edge"),
                placed_at=datetime.utcnow()
            )

            session.add(bet)
            session.commit()

            return jsonify({"success": True, "bet_id": bet.id})

    except Exception as e:
        logger.error(f"Error with bets: {e}")
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/bets/<int:bet_id>/settle", methods=["POST"])
def settle_bet(bet_id):
    """Settle a bet with the actual result"""
    session = get_session()

    try:
        data = request.json
        bet = session.query(Bet).filter(Bet.id == bet_id).first()

        if not bet:
            return jsonify({"success": False, "error": "Bet not found"}), 404

        actual_total = data["actual_total"]
        bet.actual_total = actual_total
        bet.settled_at = datetime.utcnow()

        # Determine result
        if bet.bet_type == "OVER":
            if actual_total > bet.line:
                bet.result = "WIN"
            elif actual_total < bet.line:
                bet.result = "LOSS"
            else:
                bet.result = "PUSH"
        else:  # UNDER
            if actual_total < bet.line:
                bet.result = "WIN"
            elif actual_total > bet.line:
                bet.result = "LOSS"
            else:
                bet.result = "PUSH"

        # Calculate profit
        if bet.result == "WIN":
            if bet.odds > 0:
                bet.profit = bet.stake * (bet.odds / 100)
            else:
                bet.profit = bet.stake * (100 / abs(bet.odds))
        elif bet.result == "LOSS":
            bet.profit = -bet.stake
        else:
            bet.profit = 0

        session.commit()

        return jsonify({
            "success": True,
            "result": bet.result,
            "profit": bet.profit
        })

    except Exception as e:
        logger.error(f"Error settling bet: {e}")
        session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/stats")
def get_stats():
    """Get betting statistics and ROI"""
    session = get_session()

    try:
        bets = session.query(Bet).all()

        total_bets = len(bets)
        settled_bets = [b for b in bets if b.result]
        wins = len([b for b in settled_bets if b.result == "WIN"])
        losses = len([b for b in settled_bets if b.result == "LOSS"])
        pushes = len([b for b in settled_bets if b.result == "PUSH"])

        total_staked = sum(b.stake or 0 for b in settled_bets)
        total_profit = sum(b.profit or 0 for b in settled_bets)
        roi = (total_profit / total_staked * 100) if total_staked > 0 else 0

        # Stats by edge size
        edge_stats = {}
        for edge_range in [(5, 7), (7, 10), (10, float("inf"))]:
            range_bets = [b for b in settled_bets if edge_range[0] <= abs(b.edge or 0) < edge_range[1]]
            if range_bets:
                range_wins = len([b for b in range_bets if b.result == "WIN"])
                range_profit = sum(b.profit or 0 for b in range_bets)
                range_staked = sum(b.stake or 0 for b in range_bets)
                edge_stats[f"{edge_range[0]}-{edge_range[1] if edge_range[1] != float('inf') else '+'}"] = {
                    "bets": len(range_bets),
                    "wins": range_wins,
                    "win_rate": range_wins / len(range_bets) * 100 if range_bets else 0,
                    "profit": range_profit,
                    "roi": (range_profit / range_staked * 100) if range_staked > 0 else 0
                }

        return jsonify({
            "success": True,
            "stats": {
                "total_bets": total_bets,
                "settled_bets": len(settled_bets),
                "pending_bets": total_bets - len(settled_bets),
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "win_rate": (wins / len(settled_bets) * 100) if settled_bets else 0,
                "total_staked": total_staked,
                "total_profit": total_profit,
                "roi": roi,
                "by_edge": edge_stats
            }
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/injuries")
def get_injuries():
    """Get current injury report"""
    session = get_session()

    try:
        injuries = session.query(InjuryReport).order_by(
            InjuryReport.is_star_player.desc(),
            InjuryReport.team_abbrev
        ).all()

        result = []
        for inj in injuries:
            result.append({
                "player_name": inj.player_name,
                "team": inj.team,
                "team_abbrev": inj.team_abbrev,
                "status": inj.status,
                "injury": inj.injury,
                "is_star_player": inj.is_star_player
            })

        return jsonify({"success": True, "injuries": result, "count": len(result)})

    except Exception as e:
        logger.error(f"Error getting injuries: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/team-stats")
def get_team_stats():
    """Get all team stats"""
    session = get_session()

    try:
        stats = session.query(TeamStats).order_by(
            TeamStats.offensive_efficiency.desc()
        ).all()

        result = []
        for s in stats:
            result.append({
                "team": s.team_abbrev,
                "off_eff": s.offensive_efficiency,
                "def_eff": s.defensive_efficiency,
                "pace": s.pace,
                "scraped_at": s.scraped_at.isoformat() if s.scraped_at else None
            })

        return jsonify({"success": True, "stats": result})

    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/send-alert", methods=["POST"])
def send_alert():
    """Manually send SMS alert for current edges"""
    try:
        # Get games with edges
        session = get_session()
        today = datetime.utcnow().date()

        games = session.query(Game).filter(
            Game.game_date >= datetime(today.year, today.month, today.day)
        ).all()

        significant = []
        for game in games:
            if abs(game.edge or 0) >= EDGE_THRESHOLD:
                injured = json.loads(game.injured_players) if game.injured_players else []
                significant.append({
                    "game_id": game.game_id,
                    "away_team": game.away_team,
                    "home_team": game.home_team,
                    "away_team_abbrev": game.away_team.split()[-1][:3].upper() if game.away_team else "",
                    "home_team_abbrev": game.home_team.split()[-1][:3].upper() if game.home_team else "",
                    "fanduel_total": game.fanduel_total,
                    "adjusted_projected_total": game.projected_total,
                    "edge": game.edge,
                    "edge_direction": game.edge_direction
                })

        session.close()

        if not significant:
            return jsonify({"success": False, "message": "No significant edges to alert"})

        alert_service = SMSAlertService()
        success = alert_service.send_edge_alert(significant)

        return jsonify({
            "success": success,
            "message": f"Alert {'sent' if success else 'failed'} for {len(significant)} games"
        })

    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
