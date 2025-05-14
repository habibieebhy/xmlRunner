@echo off
REM This script starts the Flask web server.
REM It assumes the script is located in the project root directory.

REM Define paths relative to the script's location (script is in the root)
SET "APP_ROOT=%~dp0"
SET "BACKEND_DIR=%APP_ROOT%backend"
SET "VENV_DIR=%BACKEND_DIR%\venv"
REM Path to the Flask application script within the venv
SET "FLASK_APP_SCRIPT=%VENV_DIR%\app.py"

echo Starting Flask Web Server...

REM Activate the virtual environment
REM Check if the activate script exists in the expected location
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
    REM Call the activate script. CALL is used to return to the batch script after activation.
    CALL "%VENV_DIR%\Scripts\activate.bat"
    echo Virtual environment activated.
) ELSE (
    REM If the activate script is not found, print an error message
    echo ERROR: Virtual environment activation script not found at "%VENV_DIR%\Scripts\activate.bat".
    echo Please run setup.bat first to create the virtual environment and install dependencies.
    goto :end
)

REM Start the Flask app
REM Running directly in the console.
REM Closing this Command Prompt window will stop the Flask development server.
echo Running Flask app. Press Ctrl+C to stop.
REM Use the 'python' command which is now available in the activated virtual environment
python "%FLASK_APP_SCRIPT%"

:end
REM The 'pause' command keeps the window open after the script finishes or an error occurs
pause
