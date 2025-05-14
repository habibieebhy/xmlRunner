@echo off
echo Setting up Tally Inventory App...

REM Define paths relative to the script's location (script is in the root)
SET "APP_ROOT=%~dp0"
SET "BACKEND_DIR=%APP_ROOT%backend"
SET "VENV_DIR=%BACKEND_DIR%\venv"
SET "XML_READ_SCRIPT=%APP_ROOT%xmlRead.py"
SET "REQUIREMENTS_FILE=%APP_ROOT%requirements.txt"
SET "APP_PY_PATH=%BACKEND_DIR%\venv\app.py"

REM --- Step 0: Copy app.py into venv folder (assuming it's in backend/ initially) ---
REM This assumes app.py is initially in the backend/ folder before setup.
REM If app.py is already in backend/venv/ in the zip, you can remove this step.
echo Copying app.py to venv directory...
IF NOT EXIST "%BACKEND_DIR%\" mkdir "%BACKEND_DIR%"
IF EXIST "%BACKEND_DIR%\app.py" (
    copy "%BACKEND_DIR%\app.py" "%VENV_DIR%\"
    IF %ERRORLEVEL% NEQ 0 (
        echo WARNING: Failed to copy app.py. Ensure backend\app.py exists.
    ) ELSE (
        echo app.py copied.
    )
)


REM --- Step 1: Check for Python (Basic Check) ---
echo Checking for Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Python 3.x is not found or not in PATH.
    echo Please install Python 3.x from https://www.python.org/downloads/ and ensure "Add Python to PATH" is checked.
    echo.
    goto :end
) ELSE (
    echo Python found.
)

REM --- Step 2: Create and Activate Virtual Environment ---
echo Creating or activating virtual environment...
IF NOT EXIST "%VENV_DIR%" (
    echo Creating virtual environment at "%VENV_DIR%"
    python -m venv "%VENV_DIR%"
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment.
        goto :end
    )
) ELSE (
    echo Virtual environment already exists.
)

REM Activate the virtual environment
REM Activation script path for Windows venv is usually in Scripts\
IF EXIST "%VENV_DIR%\Scripts\activate.bat" (
    CALL "%VENV_DIR%\Scripts\activate.bat"
) ELSE (
    echo ERROR: Virtual environment activation script not found at "%VENV_DIR%\Scripts\activate.bat".
    goto :end
)

echo Virtual environment activated.

REM --- Step 3: Install Dependencies ---
echo Installing Python dependencies from %REQUIREMENTS_FILE%...
pip install --upgrade pip
pip install -r "%REQUIREMENTS_FILE%"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Python dependencies.
    echo Please check the error messages above and ensure you have an internet connection.
    goto :end
)
echo Dependencies installed successfully.

REM --- Step 4: Set up Task Scheduler ---
echo Setting up Task Scheduler task to run xmlRead.py every 6 hours...
REM Get the full path to the python executable in the venv
REM Need to deactivate first to ensure 'where python' finds the venv python correctly after activation
IF DEFINED VIRTUAL_ENV (
    deactivate
)
CALL "%VENV_DIR%\Scripts\activate.bat"
FOR /f "delims=" %%i IN ('where python') DO SET VENV_PYTHON_EXE=%%i
IF DEFINED VIRTUAL_ENV (
    deactivate
)


IF NOT DEFINED VENV_PYTHON_EXE (
    echo ERROR: Could not find python executable in activated virtual environment.
    echo Please ensure the virtual environment was created correctly.
    goto :end
)

REM Create the task
REM /tn: Task Name
REM /tr: Task Run (the command to execute) - Use quotes around paths with spaces
REM /sc: Schedule type (hourly)
REM /mo: Modifier (every 6 hours)
REM /st: Start Time (optional, start immediately or at a specific time)
REM /f: Force creation if task already exists
REM /rl HIGHEST: Run with highest privileges (often needed for Task Scheduler reliability)
echo Creating task: TallyInventoryXmlRead
echo Command: "%VENV_PYTHON_EXE%" "%XML_READ_SCRIPT%"
schtasks /create /tn "TallyInventoryXmlRead" /tr "\"%VENV_PYTHON_EXE%\" \"%XML_READ_SCRIPT%\"" /sc hourly /mo 6 /st 00:00 /f /rl HIGHEST
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Failed to create Task Scheduler task. This step requires running the Command Prompt **as Administrator**.
    echo Please run this script as Administrator or manually create the task using the Task Scheduler GUI if needed.
    echo.
) ELSE (
    echo Task "TallyInventoryXmlRead" created successfully.
)

echo.
echo Setup script finished.
echo Please refer to the README.txt for the next steps (manual configuration and starting the server).

:end
REM Deactivate the virtual environment (optional, but good practice)
IF DEFINED VIRTUAL_ENV (
    deactivate
    echo Virtual environment deactivated.
)
pause
```

**Steps to Create the Deployable Zip:**

1.  Organize your project files into the structure shown above within a folder (e.g., `TallyInventoryApp_v1.0`).
2.  Ensure your **built React app files** are in `TallyInventoryApp_v1.0/frontend/vite-project/dist/`.
3.  Place your **Google Sheets credentials JSON file** in `TallyInventoryApp_v1.0/credentials/`.
4.  Place your `xmlRead.py` file in the root of `TallyInventoryApp_v1.0/`.
5.  Place your `app.py` file in `TallyInventoryApp_v1.0/backend/venv/`.
6.  Create `requirements.txt` in the root.
7.  Create `setup.bat` in the root.
8.  Create `start_server.bat` in the root.
9.  Create `README.txt` in the root.
10. Zip the entire `TallyInventoryApp_v1.0` folder.

This package provides a good level of automation for setting up the Python environment and scheduling the data reading task, 
but the vendor will still need to handle Python installation (if necessary), update the XML file path, and manage the Flask server process manually. 
It's a balance between automation and the complexity of a true installer/service set
