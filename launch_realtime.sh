#!/bin/bash
# Real-Time Production App Setup and Launch Script

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  E-Commerce Returns Assistant - REAL-TIME SETUP               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to project directory
cd "/Users/riyamehdiratta/Intel Genz program/scaledown"

echo "✅ Step 1: Installing dependencies..."
pip install -q flask flask-sqlalchemy flask-cors python-dotenv

echo "✅ Step 2: Initializing database..."
python -c "
from app_realtime import app, db
with app.app_context():
    db.create_all()
    print('   Database initialized successfully')
"

echo "✅ Step 3: Starting real-time server..."
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🚀 REAL-TIME SERVER RUNNING                                  ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  🌐 Open your browser:  http://localhost:8000                 ║"
echo "║                                                                ║"
echo "║  Features:                                                     ║"
echo "║  ✓ Real-Time Dashboard with live metrics                      ║"
echo "║  ✓ Seller Management with policy parsing                      ║"
echo "║  ✓ Return Request Processing with auto-eligibility            ║"
echo "║  ✓ Chat Support with conversation history                     ║"
echo "║  ✓ Analytics with fraud detection                             ║"
echo "║  ✓ Data Export (CSV)                                          ║"
echo "║  ✓ SQLite persistence (auto-save all data)                    ║"
echo "║                                                                ║"
echo "║  Database: returns_assistant.db                               ║"
echo "║  Press Ctrl+C to stop                                         ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python app_realtime.py
