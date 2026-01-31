"""
Scheduler Service for Cope Finds the Total Edge
Runs analysis at 9 AM and 3 PM daily
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCHEDULE_TIMES, EDGE_THRESHOLD
from services.calculator import run_analysis
from services.alerts import SMSAlertService

logger = logging.getLogger(__name__)


def scheduled_job():
    """
    Main scheduled job that runs analysis and sends alerts
    """
    logger.info(f"=== Starting scheduled analysis at {datetime.now()} ===")

    try:
        # Run the analysis
        analyses = run_analysis()

        if not analyses:
            logger.info("No games found for analysis")
            return

        # Find games with significant edges
        significant = [a for a in analyses if a.get("has_significant_edge")]

        logger.info(f"Analysis complete: {len(analyses)} games, {len(significant)} with edges")

        # Send SMS alerts for significant edges
        if significant:
            alert_service = SMSAlertService()
            success = alert_service.send_edge_alert(significant)
            if success:
                logger.info(f"SMS alert sent for {len(significant)} games")
            else:
                logger.warning("SMS alert failed or not configured")

            # Log the edges
            for game in significant:
                logger.info(
                    f"  EDGE: {game['away_team_abbrev']}@{game['home_team_abbrev']} "
                    f"- {game['edge_direction']} {game['fanduel_total']} "
                    f"(+{abs(game['edge']):.1f}pts)"
                )
        else:
            logger.info("No significant edges found")

    except Exception as e:
        logger.error(f"Scheduled job failed: {e}")


def create_scheduler() -> BackgroundScheduler:
    """
    Create and configure the scheduler

    Returns:
        Configured BackgroundScheduler
    """
    scheduler = BackgroundScheduler()

    # Parse schedule times and add jobs
    for time_str in SCHEDULE_TIMES:
        hour, minute = map(int, time_str.split(":"))

        # Create cron trigger for specific time
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone="America/New_York"  # Eastern time for NBA
        )

        scheduler.add_job(
            scheduled_job,
            trigger=trigger,
            id=f"analysis_{time_str}",
            name=f"NBA Analysis at {time_str}",
            replace_existing=True
        )

        logger.info(f"Scheduled job for {time_str} ET")

    return scheduler


def start_scheduler() -> BackgroundScheduler:
    """
    Start the scheduler

    Returns:
        Running BackgroundScheduler
    """
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler


def run_once():
    """Run the analysis job once immediately"""
    logger.info("Running one-time analysis...")
    scheduled_job()


def main():
    """Test the scheduler"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("\n=== Cope Finds the Total Edge - Scheduler ===\n")

    # Show schedule
    print(f"Scheduled times: {SCHEDULE_TIMES}")

    # Option to run immediately
    run_now = input("\nRun analysis now? (y/n): ").lower() == 'y'

    if run_now:
        run_once()

    # Option to start scheduler
    start = input("\nStart scheduler? (y/n): ").lower() == 'y'

    if start:
        scheduler = start_scheduler()

        print("\nScheduler running. Jobs scheduled:")
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: next run at {job.next_run_time}")

        print("\nPress Ctrl+C to exit...")

        try:
            while True:
                import time
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.shutdown()
            print("\nScheduler stopped.")


if __name__ == "__main__":
    main()
