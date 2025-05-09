Tally Inventory App Setup Instructions (VENDOR SIDE COMPUTER)

1.  **Extract the Zip File:** Unzip the "TallyInventoryApp_v1.0.zip" file to a desired location on your computer (e.g., `C:\Programs\TallyApp\`). This will create a folder named "TallyInventoryApp_v1.0".

2.  **Install Python 3.x:** If Python 3.x is not already installed, please download and install it from the official website: [https://www.python.org/downloads/](https://www.python.org/downloads/)
    * During installation, **make sure to check the option "Add Python to PATH"**.

3.  **Place Your Google Sheets Credentials File:**
    * Obtain your Google Sheets service account credentials JSON file.
    * Place this JSON file inside the `credentials\` folder within the extracted application directory (e.g., `C:\Programs\TallyApp\TallyInventoryApp_v1.0\credentials\`).
    * **Rename the JSON file to `service_account.json`**.

4.  **Run the Setup Script (as Administrator):**
    * Open Command Prompt **as Administrator**. To do this, search for "Command Prompt" in the Start Menu, right-click it, and select "Run as administrator".
    * Navigate to the extracted application folder (e.g., `cd C:\Programs\TallyApp\TallyInventoryApp_v1.0`).
    * Run the setup script: `setup.bat`

    This script will create a virtual environment, install necessary components, and set up the scheduled task for reading XML.

5.  **Update Configuration in Python Files:**
    * Open the file `backend\venv\app.py` in a text editor (like Notepad).
    * Find the line `GOOGLE_SHEET_ID = 'your-google-sheet-id'` and replace `'your-google-sheet-id'` with the actual ID of your Google Sheet.
    * Open the file `xmlRead.py` (in the main application folder) in a text editor.
    * Find the line `LOCAL_XML_FILE_PATH = 'path/to/tally/export.xml'` and update it to the exact path where Tally exports the XML file on this computer (e.g., `C:\Tally Exports\tallyExports2.xml`).

6.  **Start the Web Server:**
    * Open Command Prompt (you don't need Administrator for this).
    * Navigate to the application folder (e.g., `cd C:\Programs\TallyApp\TallyInventoryApp_v1.0`).
    * Run the server startup script: `start_server.bat`
    * **Keep this Command Prompt window open.** Closing it will stop the web server. For a more permanent solution, the server should be set up as a Windows Service (requires more advanced configuration).

7.  **Access the Application:**
    * Open a web browser and go to: `http://localhost:5050/`

The scheduled task "TallyInventoryXmlRead" will run 'xmlRead.py' every 6 hours automatically using the Task Scheduler. The web server ('start_server.bat') needs to be running for the web interface and Google Sheets uploads to work.
