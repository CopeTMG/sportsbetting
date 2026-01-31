#!/usr/bin/env python3
"""
Cope Finds the Total Edge
NBA Totals Betting Calculator

Main entry point for running the application
"""
import argparse
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from models import init_db
from services.calculator import run_analysis
from services.alerts import SMSAlertService
from services.scheduler import start_scheduler, run_once


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(os.path.dirname(__file__), "logs", "app.log")
            )
        ]
    )


def run_web_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the Flask web server"""
    from backend.app import app
    print(f"\n🏀 Starting Cope Finds the Total Edge on http://{host}:{port}")
    print("   Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)


def run_web_with_scheduler(host: str = "0.0.0.0", port: int = 5000):
    """Run web server with background scheduler"""
    from backend.app import app

    # Start scheduler in background
    scheduler = start_scheduler()

    print(f"\n🏀 Starting Cope Finds the Total Edge on http://{host}:{port}")
    print("   Scheduler running for 9 AM and 3 PM analysis")
    print("   Press Ctrl+C to stop\n")

    try:
        app.run(host=host, port=port, debug=False)
    finally:
        scheduler.shutdown()


def run_analysis_only():
    """Run analysis without web server"""
    print("\n" + "=" * 60)
    print("   COPE FINDS THE TOTAL EDGE - NBA Totals Calculator")
    print("=" * 60 + "\n")

    analyses = run_analysis()

    if not analyses:
        print("No games to analyze today.")
        return

    print(f"Analyzed {len(analyses)} games:\n")

    for i, game in enumerate(analyses, 1):
        edge_flag = "🔥" if game["has_significant_edge"] else "  "

        print(f"{edge_flag} Game {i}: {game['away_team']} @ {game['home_team']}")
        print(f"   FanDuel Total: {game['fanduel_total']}")
        print(f"   Our Projection: {game['adjusted_projected_total']} (raw: {game['raw_projected_total']})")
        print(f"   Injury Adjustment: {game['injury_adjustment']}")
        print(f"   EDGE: {game['edge']:+.1f} points ({game['edge_direction']})")

        if game["injured_players"]:
            print(f"   Injuries:")
            for inj in game["injured_players"]:
                star = "⭐" if inj["is_star"] else ""
                print(f"      - {inj['name']} ({inj['team']}) {star}")
        print()

    # Summary
    significant = [g for g in analyses if g["has_significant_edge"]]
    if significant:
        print("\n" + "=" * 60)
        print(f"   🎯 SIGNIFICANT EDGES: {len(significant)}")
        print("=" * 60)

        for game in significant:
            print(f"\n   {game['away_team']} @ {game['home_team']}")
            print(f"   Play: {game['edge_direction']} {game['fanduel_total']}")
            print(f"   Edge: {abs(game['edge']):.1f} points")

        return significant
    else:
        print("\n   No significant edges (5+ points) found today.")
        return []


def send_test_alert():
    """Send a test SMS alert"""
    from backend.services.alerts import send_test_sms
    print("Sending test SMS...")
    success = send_test_sms()
    if success:
        print("Test SMS sent successfully!")
    else:
        print("Test SMS failed. Check Twilio configuration.")


def main():
    parser = argparse.ArgumentParser(
        description="Cope Finds the Total Edge - NBA Totals Betting Calculator"
    )

    parser.add_argument(
        "command",
        choices=["web", "analyze", "schedule", "test-alert", "full"],
        help="Command to run"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for web server (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for web server (default: 5000)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.verbose)
    os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
    init_db()

    # Run command
    if args.command == "web":
        run_web_server(args.host, args.port, args.debug)

    elif args.command == "analyze":
        significant = run_analysis_only()
        if significant:
            send_alerts = input("\nSend SMS alerts for these edges? (y/n): ").lower() == 'y'
            if send_alerts:
                alert_service = SMSAlertService()
                alert_service.send_edge_alert(significant)

    elif args.command == "schedule":
        run_web_with_scheduler(args.host, args.port)

    elif args.command == "test-alert":
        send_test_alert()

    elif args.command == "full":
        # Run analysis then start web server with scheduler
        print("Running initial analysis...")
        run_analysis_only()
        print("\nStarting web server with scheduler...")
        run_web_with_scheduler(args.host, args.port)


if __name__ == "__main__":
    main()
