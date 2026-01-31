"""
Database models for Cope Finds the Total Edge
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH

Base = declarative_base()


class Game(Base):
    """Store game information and projections"""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    game_id = Column(String(100), unique=True, nullable=False)
    game_date = Column(DateTime, nullable=False)
    home_team = Column(String(50), nullable=False)
    away_team = Column(String(50), nullable=False)

    # FanDuel odds
    fanduel_total = Column(Float)
    fanduel_over_odds = Column(Integer)
    fanduel_under_odds = Column(Integer)

    # Team stats
    home_off_eff = Column(Float)
    home_def_eff = Column(Float)
    home_pace = Column(Float)
    away_off_eff = Column(Float)
    away_def_eff = Column(Float)
    away_pace = Column(Float)

    # Projections
    projected_home_score = Column(Float)
    projected_away_score = Column(Float)
    projected_total = Column(Float)
    raw_projected_total = Column(Float)  # Before injury adjustments

    # Edge calculation
    edge = Column(Float)
    edge_direction = Column(String(10))  # "OVER" or "UNDER"

    # Injury adjustments
    injury_adjustment = Column(Float, default=0.0)
    injured_players = Column(Text)  # JSON string of injured players

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Game {self.away_team} @ {self.home_team} ({self.game_date})>"


class Bet(Base):
    """Track bet history"""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True)
    game_id = Column(String(100), nullable=False)
    game_date = Column(DateTime, nullable=False)
    home_team = Column(String(50), nullable=False)
    away_team = Column(String(50), nullable=False)

    # Bet details
    bet_type = Column(String(20), nullable=False)  # "OVER" or "UNDER"
    line = Column(Float, nullable=False)
    odds = Column(Integer, nullable=False)
    stake = Column(Float, nullable=False)

    # Our projection at time of bet
    projected_total = Column(Float)
    edge = Column(Float)

    # Result
    actual_total = Column(Float)
    result = Column(String(10))  # "WIN", "LOSS", "PUSH"
    profit = Column(Float)

    # Timestamps
    placed_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime)

    def __repr__(self):
        return f"<Bet {self.bet_type} {self.line} on {self.away_team}@{self.home_team}>"


class TeamStats(Base):
    """Store team efficiency and pace stats"""
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True)
    team_abbrev = Column(String(10), nullable=False)
    team_name = Column(String(50), nullable=False)

    offensive_efficiency = Column(Float)
    defensive_efficiency = Column(Float)
    pace = Column(Float)

    # When stats were scraped
    scraped_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TeamStats {self.team_abbrev}>"


class Alert(Base):
    """Track sent alerts"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    game_id = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    sent_to = Column(String(20), nullable=False)
    success = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Alert {self.game_id} at {self.sent_at}>"


class InjuryReport(Base):
    """Store injury data"""
    __tablename__ = "injuries"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    player_name = Column(String(100), nullable=False)
    team = Column(String(50), nullable=False)
    team_abbrev = Column(String(10))
    status = Column(String(50))  # Out, Questionable, Probable, etc.
    injury = Column(String(100))
    is_star_player = Column(Boolean, default=False)

    # When data was fetched
    fetched_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Injury {self.player_name} ({self.status})>"


def init_db():
    """Initialize the database"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    engine = create_engine(f"sqlite:///{DATABASE_PATH}")
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a database session"""
    engine = create_engine(f"sqlite:///{DATABASE_PATH}")
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
