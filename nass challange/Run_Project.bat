@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating project virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment. Install Python 3 and try again.
        pause
        exit /b 1
    )
)

echo Installing or verifying project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo AstroHealth is starting. Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C in this window to stop the server.
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo The application stopped with an error.
    pause
    exit /b 1
)
endlocal
