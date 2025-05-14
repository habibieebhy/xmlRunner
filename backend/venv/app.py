# backend/venv/app.py

# Import necessary Flask components
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
import json # Needed to parse the JSON string from the environment variable
from dotenv import load_dotenv # Import dotenv to load environment variables

# Load environment variables from a .env file.
# By default, load_dotenv() looks for a .env file in the current directory
load_dotenv()


# Create a Flask application instance
# Path from app.py (in backend/venv/) to frontend/vite-project/dist/
app = Flask(__name__, static_folder='../../frontend/vite-project/dist')

# --- Configure CORS ---
# Allowing specific origins for API routes during development.
# This is more secure than allowing all origins (*).
# Include both the Flask serving origin and the React dev server origin.
ALLOWED_ORIGINS = [
    "http://localhost:5050",
    "http://127.0.0.1:5050", 
    "http://localhost:5173"  # React development server default port
]
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})


# --- Configuration for Google Sheets ---
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID') # <-- CHANGE THIS ID MANUALLY PER DEPLOYMENT

GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')

# Check if the credentials environment variable is set
if not GOOGLE_SHEETS_CREDENTIALS_JSON:
    print("WARNING: GOOGLE_SHEETS_CREDENTIALS_JSON environment variable not set.")
    print("Google Sheets integration will not work without credentials.")


# --- In-memory storage ---
latest_inventory_data = []
last_update_time = None

# --- Endpoint to receive Tally data ---
@app.route('/api/upload_tally_data', methods=['POST'])
def upload_tally_data():
    global latest_inventory_data, last_update_time

    # Use request.get_json() to parse the incoming JSON body
    # Set silent=True to avoid errors if the data is not JSON
    payload = request.get_json(silent=True)

    # --- MODIFIED VALIDATION ---
    # Accept either a list or a dictionary as the top-level payload
    if not payload:
        return jsonify({"status": "error", "message": "No data received in the request body."}), 400

    cleaned_data = []
    if isinstance(payload, list):
        # If it's already a list, use it directly
        cleaned_data = payload
        print(f"Received a JSON array payload with {len(payload)} items.")
    elif isinstance(payload, dict):
        # If it's a dictionary, wrap it in a list
        cleaned_data = [payload]
        print("Received a JSON object payload. Wrapped in a list.")
    else:
        # If it's neither a list nor a dictionary, return an error
        return jsonify({"status": "error", "message": "Expected a JSON dictionary or array payload."}), 400


    # Extract and process the list of items
    try:
        # At this point, cleaned_data is always a list

        if not cleaned_data:
            # This case might be hit if the list is empty, which is acceptable
            # if Tally returns no items, but we'll keep the check.
            print("Received an empty list of items.")
            # Optionally return a success message for an empty list
            # return jsonify({"status": "success", "message": "Received an empty list of items."})
            # For now, we'll proceed with an empty list.

        latest_inventory_data = cleaned_data
        last_update_time = datetime.datetime.now()
        print(f"Stored {len(latest_inventory_data)} items at {last_update_time.isoformat()}")

        # Send to Google Sheets
        send_to_google_sheets(latest_inventory_data)

        return jsonify({
            "status": "success",
            "message": f"Received and stored {len(latest_inventory_data)} items."
        })

    except Exception as e:
        # Catch any errors during data processing after successful JSON parsing
        print(f"Error processing received data: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to process received data: {str(e)}"}), 500


def send_to_google_sheets(data):
    if not data:
        print("No data to send to Google Sheets.")
        return

    # Check if credentials JSON content is available
    if not GOOGLE_SHEETS_CREDENTIALS_JSON:
        print("Google Sheets credentials JSON content not found. Skipping Google Sheets upload.")
        return

    try:
        # Parse the JSON string content into a Python dictionary
        credentials_info = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        # Authenticate using the dictionary content
        creds = Credentials.from_service_account_info(
            credentials_info, scopes=scopes
        )
        client = gspread.authorize(creds)

        # Check if GOOGLE_SHEET_ID is configured
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == 'your-google-sheet-id':
             print("Error: GOOGLE_SHEET_ID is not configured. Cannot send data to Google Sheets.")
             return

        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

        # Build headers dynamically from the first record if data is not empty
        headers = []
        if data:
            # Get keys from the first item dictionary
            headers = list(data[0].keys())

        rows = [headers] # Start with the headers row
        for record in data:
            # Create a row ensuring order matches headers and handling missing keys
            rows.append([record.get(k, "") for k in headers])

        # Only append rows if there are headers (meaning data was not empty)
        if headers:
             sheet.append_rows(rows)
             print(f"Appended {len(rows)} rows to Google Sheet.")
        else:
             print("No data rows to append to Google Sheet after headers.")

    except json.JSONDecodeError:
        print("Error: Could not parse GOOGLE_SHEETS_CREDENTIALS_JSON. Ensure it's valid JSON.")
    except Exception as e:
        print(f"Error sending to Google Sheets: {e}")
        print("Please check your Google Sheets configuration, credentials JSON content, and sheet permissions.")


@app.route('/api/get_processed_columns', methods=['GET'])
def get_processed_columns():
    # Dynamically get column names from the keys of the first item in latest_inventory_data
    # This assumes all items have the same keys, which should be the case if parsing is consistent.
    if latest_inventory_data and isinstance(latest_inventory_data, list) and len(latest_inventory_data) > 0:
        # Get keys from the first item dictionary
        keys = list(latest_inventory_data[0].keys())
    else:
        # Return a default set of columns or an empty list if no data is loaded
        # Returning an empty list is safer if the frontend handles it gracefully.
        # If you prefer default columns, define them here:
        # keys = ['itemName', 'stockQty', 'rate'] # Example default keys
        keys = []


    columns = [{"id": k, "name": k} for k in keys]
    # If no data is loaded, you might want to return default headers for the table structure
    # For example:
    # if not columns:
    #     columns = [{"id": "itemName", "name": "Item Name"}, {"id": "stockQty", "name": "Stock Quantity"}, {"id": "rate", "name": "Rate"}]

    return jsonify(columns)


@app.route('/api/get_latest_data', methods=['GET'])
def get_latest_data():
    global latest_inventory_data, last_update_time

    return jsonify({
        "data": latest_inventory_data,
        "last_update": last_update_time.isoformat() if last_update_time else None,
        "message": f"{len(latest_inventory_data)} items" if latest_inventory_data else "No data yet."
    })


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    # Assuming your React build output is in frontend/vite-project/dist relative to app.py (in backend/venv/)
    react_dist = os.path.abspath('../../frontend/vite-project/dist')
    if ".." in path:
        return "Not Found", 404

    full_path = os.path.join(react_dist, path)
    if path == "" or (os.path.exists(full_path) and os.path.isfile(full_path)):
        return send_from_directory(react_dist, path or 'index.html')
    return send_from_directory(react_dist, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5050)
