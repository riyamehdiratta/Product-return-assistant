#!/bin/bash

# E-Commerce Returns Assistant - Quick Start Setup
# Run this script to set up and run the Returns Assistant locally

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  E-Commerce Returns Assistant - Quick Start Setup              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Clone repository
echo "📦 Step 1: Cloning repository..."
git clone https://github.com/scaledown-team/scaledown.git
cd scaledown
echo "✅ Repository cloned!"
echo ""

# Step 2: Create virtual environment
echo "🔧 Step 2: Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    .venv\Scripts\activate
else
    # macOS/Linux
    source .venv/bin/activate
fi
echo "✅ Virtual environment created and activated!"
echo ""

# Step 3: Install dependencies
echo "📥 Step 3: Installing dependencies..."
pip install -e .
echo "✅ Dependencies installed!"
echo ""

# Step 4: Run tests
echo "🧪 Step 4: Running tests (26 tests)..."
python -m pytest tests/test_returns.py -v --tb=short
echo ""

# Step 5: Run the demo
echo "🚀 Step 5: Running the Returns Assistant Demo..."
echo ""
python examples/returns_demo.py
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Setup Complete! Returns Assistant is ready to use          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Next steps:"
echo "  1. Check scaledown/returns/README.md for documentation"
echo "  2. Explore examples/returns_demo.py to see usage"
echo "  3. Run: python examples/returns_demo.py (anytime)"
echo "  4. Run tests: pytest tests/test_returns.py -v"
echo ""
