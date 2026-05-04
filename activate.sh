#!/bin/bash
# Activate virtual environment for the Cybersecurity SOC Platform
# Usage: source activate.sh

echo "Activating virtual environment..."
source .venv/Scripts/activate

echo ""
echo "Virtual environment activated!"
echo "To start the Django server, run:"
echo "  cd cybersec_backend"
echo "  python manage.py runserver 8000"
