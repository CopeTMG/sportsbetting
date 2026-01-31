"""
SMS Alert Service using Twilio
Sends alerts when significant edges (5+ points) are found
"""
from datetime import datetime
from typing import List, Dict, Optional
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    ALERT_PHONE_NUMBER,
    EDGE_THRESHOLD
)
from models import Alert, get_session

logger = logging.getLogger(__name__)


class SMSAlertService:
    """SMS Alert Service using Twilio"""

    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.from_number = TWILIO_PHONE_NUMBER
        self.to_number = ALERT_PHONE_NUMBER
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Twilio client if credentials are available"""
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.warning("Twilio package not installed. SMS alerts disabled.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.warning("Twilio credentials not configured. SMS alerts disabled.")

    def is_configured(self) -> bool:
        """Check if SMS alerts are properly configured"""
        return (
            self.client is not None and
            self.from_number and
            self.to_number
        )

    def format_edge_alert(self, games: List[Dict]) -> str:
        """Format games with edges into an SMS message"""
        if not games:
            return ""

        lines = ["🏀 NBA EDGE ALERT 🏀\n"]

        for game in games:
            away = game.get("away_team_abbrev", game.get("away_team", ""))
            home = game.get("home_team_abbrev", game.get("home_team", ""))
            edge = game.get("edge", 0)
            direction = game.get("edge_direction", "")
            total = game.get("fanduel_total", 0)
            projected = game.get("adjusted_projected_total", 0)

            lines.append(f"{away}@{home}")
            lines.append(f"FD: {total} | Proj: {projected}")
            lines.append(f"▶ {direction} {total} ({abs(edge):+.1f}pts)")
            lines.append("")

        lines.append(f"Time: {datetime.now().strftime('%I:%M %p')}")

        return "\n".join(lines)

    def send_sms(self, message: str, to_number: str = None) -> bool:
        """
        Send an SMS message

        Args:
            message: Message content
            to_number: Phone number to send to (uses default if not specified)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SMS not configured. Message not sent.")
            print(f"\n[SMS PREVIEW - Not Sent]\n{message}\n")
            return False

        target_number = to_number or self.to_number

        try:
            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=target_number
            )

            logger.info(f"SMS sent successfully. SID: {sms.sid}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def send_edge_alert(
        self,
        games: List[Dict],
        to_number: str = None
    ) -> bool:
        """
        Send alert for games with significant edges

        Args:
            games: List of game analyses with significant edges
            to_number: Phone number to send to

        Returns:
            True if sent successfully
        """
        if not games:
            logger.info("No games with significant edges. No alert sent.")
            return False

        # Filter to only significant edges
        significant_games = [
            g for g in games
            if abs(g.get("edge", 0)) >= EDGE_THRESHOLD
        ]

        if not significant_games:
            logger.info("No games meet edge threshold. No alert sent.")
            return False

        # Format and send message
        message = self.format_edge_alert(significant_games)
        success = self.send_sms(message, to_number)

        # Log the alert
        self._log_alert(significant_games, message, success, to_number)

        return success

    def _log_alert(
        self,
        games: List[Dict],
        message: str,
        success: bool,
        to_number: str = None
    ):
        """Log sent alert to database"""
        session = get_session()

        try:
            for game in games:
                alert = Alert(
                    game_id=game.get("game_id", "unknown"),
                    message=message,
                    sent_at=datetime.utcnow(),
                    sent_to=to_number or self.to_number,
                    success=success
                )
                session.add(alert)

            session.commit()
            logger.info(f"Logged {len(games)} alerts to database")

        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
            session.rollback()
        finally:
            session.close()

    def check_if_alert_sent(self, game_id: str) -> bool:
        """Check if an alert has already been sent for a game today"""
        session = get_session()

        try:
            today = datetime.utcnow().date()
            existing = session.query(Alert).filter(
                Alert.game_id == game_id,
                Alert.success == True
            ).first()

            if existing:
                alert_date = existing.sent_at.date()
                return alert_date == today

            return False

        finally:
            session.close()


def send_test_sms(message: str = None) -> bool:
    """Send a test SMS"""
    service = SMSAlertService()

    if message is None:
        message = "🏀 Test alert from Cope Finds the Total Edge! System is working."

    return service.send_sms(message)


def main():
    """Test the SMS alert service"""
    logging.basicConfig(level=logging.INFO)

    print("\n=== Testing SMS Alert Service ===\n")

    service = SMSAlertService()

    print(f"Configured: {service.is_configured()}")
    print(f"From Number: {service.from_number or 'Not set'}")
    print(f"To Number: {service.to_number or 'Not set'}")

    # Create test games
    test_games = [
        {
            "game_id": "test123",
            "away_team": "Los Angeles Lakers",
            "home_team": "Boston Celtics",
            "away_team_abbrev": "LAL",
            "home_team_abbrev": "BOS",
            "fanduel_total": 225.5,
            "adjusted_projected_total": 232.0,
            "edge": 6.5,
            "edge_direction": "OVER"
        },
        {
            "game_id": "test456",
            "away_team": "Phoenix Suns",
            "home_team": "Denver Nuggets",
            "away_team_abbrev": "PHX",
            "home_team_abbrev": "DEN",
            "fanduel_total": 230.0,
            "adjusted_projected_total": 223.5,
            "edge": -6.5,
            "edge_direction": "UNDER"
        }
    ]

    # Format message
    message = service.format_edge_alert(test_games)
    print("\n--- Message Preview ---")
    print(message)
    print("-----------------------\n")

    # Try to send (will preview only if not configured)
    if not service.is_configured():
        print("SMS not configured. Set these environment variables:")
        print("  TWILIO_ACCOUNT_SID")
        print("  TWILIO_AUTH_TOKEN")
        print("  TWILIO_PHONE_NUMBER")
    else:
        confirm = input("Send test SMS? (y/n): ")
        if confirm.lower() == 'y':
            success = service.send_edge_alert(test_games)
            print(f"Send result: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    main()
