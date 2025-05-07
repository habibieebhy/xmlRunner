# backend/venv/app.py

# Import necessary Flask components
from flask import Flask, jsonify, request, send_from_directory
import os
import datetime # To track the last update time
# Import the CORS class
from flask_cors import CORS

# --- Google Sheets Imports ---
# You need to install these libraries: pip install gspread google-auth google-auth-oauthlib google-auth-httplib2
import gspread
from google.oauth2.service_account import Credentials
# import pandas as pd # Often useful for handling data before sending to Sheets

# Create a Flask application instance
# __name__ is a special Python variable that gets the name of the current module.
# Flask uses this to know where to look for resources like templates and static files.
# Configure static folder to serve the built React app
# CORRECTED PATH: Assumes React build output is in frontend/vite-project/dist relative to the backend/venv folder
app = Flask(__name__, static_folder='../../frontend/vite-project/dist')

# --- Configure CORS ---
# This will allow requests from the React development server's origin (http://localhost:5173)
# to access your Flask API endpoints during development.
# For production, when Flask serves the static files, CORS is not needed for API calls
# from the same origin. You might configure this conditionally or remove it for production.
# Note: This CORS configuration is primarily for when you run the React dev server separately.
# When Flask serves the built React app, CORS is typically not needed for API calls
# to the same Flask server.
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


# --- Configuration for Google Sheets ---
# IMPORTANT: You MUST fill in these values
# Path to the JSON key file you downloaded from Google Cloud Console for your Service Account
GOOGLE_SHEETS_CREDENTIALS_PATH = '/home/rgos/pyth-sql-all/vendor-pipeline/backend/venv/xmlRead-to-gsheets.json' # <-- CHANGE THIS PATH

# The ID of your Google Sheet. You can find this in the sheet's URL:
# https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit
GOOGLE_SHEET_ID = '1Wm2_KrFCnSCzR9w9YpxdfdoqnT62anWUJdv7q4rOcrE' # <-- CHANGE THIS ID


# --- In-memory storage for the latest data received ---
# This is temporary storage. Data will be lost if the Flask app restarts.
# For persistence, consider using a small local database or file storage.
latest_inventory_data = []
last_update_time = None

# --- Define the fixed columns we expect/process ---
# These are the columns the backend expects from the script and the frontend will display.
# The 'id' keys should match the keys sent by xmlRead.py (itemName, stockQty, rate).
# The 'name' keys are for display in the frontend.
PROCESSED_COLUMNS = [
    {"id": "itemName", "name": "Item Name"},
    {"id": "stockQty", "name": "Stock Quantity"},
    {"id": "rate", "name": "Rate"}, # Assuming this is the sale/standard rate
]


# --- API Endpoint for the first Python script to send data ---
# This endpoint receives the data extracted by xmlRead.py
@app.route('/api/upload_tally_data', methods=['POST'])
def upload_tally_data():
    """
    Receives inventory data (as JSON) from the xmlRead.py script.
    Stores it in memory and triggers sending to Google Sheets.
    """
    global latest_inventory_data, last_update_time

    # --- Step 1: Receive data from the xmlRead.py script ---
    # The script sends data as JSON.
    try:
        # Get the JSON data from the request body
        tally_data_payload = request.json
        if not tally_data_payload:
             print("Received empty data payload.")
             return jsonify({"status": "error", "message": "No data received in the request body."}), 400

        print(f"Received data payload with {len(tally_data_payload)} items from script.")

        # --- Step 2: Validate and Store the Data ---
        # We'll do a basic validation to ensure the received data is a list
        # and contains dictionaries, and then store it.
        # More robust validation could check for expected keys in each dictionary.
        if isinstance(tally_data_payload, list):
             # Simple storage in the global variable
             latest_inventory_data = tally_data_payload
             last_update_time = datetime.datetime.now()
             print(f"Successfully stored {len(latest_inventory_data)} items.")

             # --- Step 3: Trigger Sending to Google Sheets ---
             # Call a separate function to handle the Google Sheets upload
             # This call might block if the upload is slow.
             # For large datasets, consider running this in a background thread/process.
             send_to_google_sheets(latest_inventory_data) # This function needs to be implemented

             return jsonify({"status": "success", "message": f"Data received and processing initiated for {len(latest_inventory_data)} items."})
        else:
            print("Received data is not a list.")
            return jsonify({"status": "error", "message": "Received data is not in the expected list format."}), 400

    except Exception as e:
        # Catch any errors during data reception or initial processing
        print(f"Error processing uploaded data: {e}")
        return jsonify({"status": "error", "message": f"Failed to process uploaded data: {e}"}), 500

# --- Helper function to send data to Google Sheets ---
# This function is called by upload_tally_data
def send_to_google_sheets(data):
    """
    Handles the logic for authenticating and sending data to Google Sheets.
    This function is now implemented to connect to Google Sheets API.
    """
    if not data:
        print("No data to send to Google Sheets.")
        return

    print("Attempting to send data to Google Sheets...")
    try:
        # 1. Authenticate using the service account key file
        # The scopes define what permissions your application needs (read/write to Sheets and Drive)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        # Ensure GOOGLE_SHEETS_CREDENTIALS_PATH is set in Configuration section above
        credentials = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scopes)

        # Authorize the client using the credentials
        client = gspread.authorize(credentials)

        # 2. Open the Google Sheet by ID
        # Ensure GOOGLE_SHEET_ID is set in Configuration section above
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1 # .sheet1 gets the first worksheet. You can use .worksheet("Sheet Name") for a specific sheet.

        # 3. Prepare data for Google Sheets (list of lists)
        # First row should be headers (column names from PROCESSED_COLUMNS)
        headers = [col['name'] for col in PROCESSED_COLUMNS]
        rows_to_insert = [headers]
        for item in data:
            # Ensure columns are in the correct order based on PROCESSED_COLUMNS IDs
            # Use .get(key, "") to handle cases where a key might be missing in an item dictionary
            row = [item.get(col['id'], "") for col in PROCESSED_COLUMNS]
            rows_to_insert.append(row)

        # 4. Clear existing data (optional, use with caution!) or append
        # Clearing the sheet before appending ensures you always have the latest data only.
        # Use with extreme caution as this will delete ALL data in the sheet!
        # print("Clearing existing sheet data...")
        # sheet.clear()

        # 5. Insert the data
        # Using append_rows adds the data after the last row in the sheet.
        # If you cleared the sheet, this will start from the first row.
        # If you didn't clear, it will add data at the bottom.
        print(f"Appending {len(rows_to_insert)} rows to Google Sheets...")
        sheet.append_rows(rows_to_insert)
        # Alternatively, you could use sheet.update('A1', rows_to_insert) to overwrite data starting from cell A1.

        print("Data successfully sent to Google Sheets.")

    except FileNotFoundError:
        print(f"Error: Google Sheets credentials file not found at {GOOGLE_SHEETS_CREDENTIALS_PATH}")
        print("Please ensure the GOOGLE_SHEETS_CREDENTIALS_PATH is correct.")
    except Exception as e:
        print(f"Error sending data to Google Sheets: {e}")
        print("Please check your Google Sheets configuration, credentials, and sheet permissions.")
        # Consider logging this error or having a retry mechanism
        # This function doesn't return an HTTP response, so log the error internally.


# --- API Endpoint for the React frontend to get the list of processed columns ---
# The frontend calls this to know which columns to display headers for.
@app.route('/api/get_processed_columns', methods=['GET'])
def get_processed_columns():
    """
    Returns the list of columns that the backend processes and expects.
    The frontend uses this to know what headers to display.
    """
    # Return the PROCESSED_COLUMNS list defined above
    return jsonify(PROCESSED_COLUMNS)


# --- API Endpoint for the React frontend to get the latest data ---
# The frontend calls this to get the data to display in the table.
@app.route('/api/get_latest_data', methods=['GET'])
def get_latest_data():
    """
    Returns the latest inventory data received by the backend to the React frontend.
    """
    global latest_inventory_data, last_update_time

    # Prepare data for the frontend
    # We send the raw data received, the frontend will use get_processed_columns
    # to map IDs to names for display.
    # Include headers for convenience, though frontend could build them from get_processed_columns.
    headers = [col['name'] for col in PROCESSED_COLUMNS]


    return jsonify({
        "data": latest_inventory_data, # Send the raw data list
        "headers": headers, # Send the display headers
        "last_update": last_update_time.isoformat() if last_update_time else None, # Send timestamp
        "message": f"Returning {len(latest_inventory_data)} items." if latest_inventory_data else "No data received yet."
    })


# --- Serve the React Frontend (Static Files) ---
# This route serves the index.html file from your built React app
# It handles requests to the root URL and any other paths (for client-side routing)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    # Assuming your React build output is in frontend/vite-project/dist relative to the backend/venv folder
    react_dist_dir = os.path.abspath('../../frontend/vite-project/dist')

    # Basic security check to prevent directory traversal
    if ".." in path:
        return "Not Found", 404

    # Construct the full path to the requested file
    requested_file = os.path.join(react_dist_dir, path)

    # If the requested path is empty, serve index.html
    # If the requested path exists and is a file, serve it
    if path == "" or os.path.exists(requested_file) and os.path.isfile(requested_file):
         # For the root path or if a specific file is requested and exists, serve it
         # If path is empty, send_from_directory serves index.html by default
         return send_from_directory(react_dist_dir, path if path else 'index.html')
    else:
        # If the requested path is not a file (e.g., a route like /items/123),
        # assume it's a client-side route and serve index.html so React Router can handle it.
        # This is common for Single Page Applications (SPAs) built with React.
        return send_from_directory(react_dist_dir, 'index.html')


# --- Main entry point to run the app ---
if __name__ == '__main__':
    # Run the Flask development server
    # debug=True is good for development, turn off for production
    # host='0.0.0.0' allows access from other machines on the network (be cautious)
    # port=5050 matches the configuration in xmlRead.py
    app.run(debug=True, port=5050)
