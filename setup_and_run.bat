@echo off
REM E-Commerce Returns Assistant - Quick Start Setup (Windows)
REM Run this script to set up and run the Returns Assistant locally

echo.
echo ════════════════════════════════════════════════════════════════
echo   E-Commerce Returns Assistant - Quick Start Setup (Windows)
echo ════════════════════════════════════════════════════════════════
echo.

REM Step 1: Clone repository
echo ^[1/5^] Cloning repository...
git clone https://github.com/scaledown-team/scaledown.git
cd scaledown
echo ✓ Repository cloned!
echo.

REM Step 2: Create virtual environment
echo ^[2/5^] Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat
echo ✓ Virtual environment created and activated!
echo.

REM Step 3: Install dependencies
echo ^[3/5^] Installing dependencies...
pip install -e .
echo ✓ Dependencies installed!
echo.

REM Step 4: Run tests
echo ^[4/5^] Running tests (26 tests)...
python -m pytest tests/test_returns.py -v --tb=short
echo.

REM Step 5: Run the demo
echo ^[5/5^] Running the Returns Assistant Demo...
echo.
python examples/returns_demo.py
echo.

echo ════════════════════════════════════════════════════════════════
echo ✓ Setup Complete! Returns Assistant is ready to use
echo ════════════════════════════════════════════════════════════════
echo.
echo Next steps:
echo   1. Check scaledown\returns\README.md for documentation
echo   2. Explore examples\returns_demo.py to see usage
echo   3. Run: python examples\returns_demo.py (anytime)
echo   4. Run tests: pytest tests\test_returns.py -v
echo.
pause
