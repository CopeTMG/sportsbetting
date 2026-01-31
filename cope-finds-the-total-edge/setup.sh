#!/bin/bash
# Setup script for Cope Finds the Total Edge

echo "🏀 Setting up Cope Finds the Total Edge..."
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create directories
echo "Creating directories..."
mkdir -p data logs

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Twilio credentials for SMS alerts"
fi

# Initialize database
echo "Initializing database..."
python -c "from backend.models import init_db; init_db(); print('Database initialized!')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  python run.py full"
echo ""
echo "Available commands:"
echo "  python run.py web        - Start web dashboard only"
echo "  python run.py analyze    - Run one-time analysis"
echo "  python run.py schedule   - Start with scheduler (9 AM & 3 PM)"
echo "  python run.py full       - Run analysis then start with scheduler"
echo "  python run.py test-alert - Send a test SMS"
echo ""
