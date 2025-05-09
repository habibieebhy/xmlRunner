@echo off
REM This script runs the setup, starts the web server, and runs xmlRead.py once.
REM It assumes the script is located in the project root directory.
REM This script needs to be run $"AS ADMINISTRATOR"$ for the Task Scheduler setup to work.

SET "APP_ROOT=%~dp0"
SET "SETUP_SCRIPT=%APP_ROOT%setup.bat"
SET "START_SERVER_SCRIPT=%APP_ROOT%start_server.bat"
SET "XML_READ_SCRIPT=%APP_ROOT%xmlRead.py"
SET "BACKEND_DIR=%APP_ROOT%backend"
SET "VENV_DIR=%BACKEND_DIR%\venv"

echo Running the setup script...
REM Call the setup script. This will handle venv creation, dependency installation, and Task Scheduler setup.
REM This step requires Administrator privileges.
CALL "%SETUP_SCRIPT%"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Setup script failed. Please check the messages above.
    echo Ensure you ran this script AS ADMINISTRATOR.
    echo.
    goto :end
)
echo Setup script completed successfully.

echo.
echo Starting the web server...
REM Use the 'start' command to run the start_server.bat script in a new window.
REM This prevents this script from waiting for the server script to finish.
start "Flask Web Server" "%START_SERVER_SCRIPT%"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Failed to start the web server script.
    echo You may need to run start_server.bat manually.
    echo.
    REM Continue to try running xmlRead.py even if server start warning occurred
) ELSE (
    echo Web server script started in a new window.
    REM Give the server a moment to start up before sending data
    timeout /t 5 /nobreak >nul
    echo Giving the server a few seconds to start...
)

echo.
echo Running xmlRead.py once for initial data load...

REM Activate the virtual environment to run xmlRead.py
REM Activation script path for Windows venv is usually in Scripts\
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
    CALL "%VENV_DIR%\Scripts\activate.bat"
    echo Virtual environment activated for initial xmlRead.py run.
) ELSE (
    echo ERROR: Virtual environment activation script not found at "%VENV_DIR%\Scripts\activate.bat".
    echo Cannot run xmlRead.py. Please run setup.bat first.
    goto :end
)

REM Run the xmlRead.py script using the python executable from the activated venv
python "%XML_READ_SCRIPT%"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Initial run of xmlRead.py failed. Please check the output above.
    echo.
) ELSE (
    echo Initial run of xmlRead.py completed successfully.
)

REM Deactivate the virtual environment after running xmlRead.py
IF DEFINED VIRTUAL_ENV (
    deactivate
    echo Virtual environment deactivated after initial xmlRead.py run.
)


echo.
echo Automated installation, server startup, and initial data load script finished.
echo Please refer to the README.txt for manual configuration steps (Google Sheet ID, Tally XML path)
echo and how to access the application in your browser (http://localhost:5050/).

:end
REM The 'pause' command keeps the window open after the script finishes or an error occurs
pause
