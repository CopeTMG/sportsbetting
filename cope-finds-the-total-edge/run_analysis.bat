@echo off
REM Cope Finds the Total Edge - Scheduled Analysis
REM This script runs the NBA totals analysis and sends alerts if edges are found

cd /d "C:\Users\Trader\Documents\Sports Betting\sportsbetting-claude-nba-betting-calculator-NJB6j\cope-finds-the-total-edge"

REM Run the analysis
py -3.13 run.py analyze

REM Log completion time
echo Analysis completed at %date% %time% >> logs\scheduled_runs.log
