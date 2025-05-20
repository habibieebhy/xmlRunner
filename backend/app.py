# backend/venv/app.py

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
from dotenv import load_dotenv
import xmltodict

# Load environment variables from a .env file.
load_dotenv()
print(f"DEBUG: Value of GOOGLE_SHEETS_CREDENTIALS_JSON from os.getenv: {os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')[:50]}...")

# Path from app.py (in backend/venv/) to frontend/vite-project/dist/
app = Flask(__name__, static_folder='../frontend/vite-project/dist')

# --- Configure CORS ---
ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5050",
    "http://127.0.0.1:5050",
    "http://localhost:5173",
    # Add any other origins where your frontend might run
]
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})


# --- Configuration for Google Sheets ---
GOOGLE_SHEET_ID = '1-Z8e2EBkNaUTveXdB_edaoKT7KBhCMJilDdy1vxEZAw'

# Initialize client globally, set to None initially.
# This variable will hold the authorized gspread client if credentials are valid.
gspread_client = None

# Attempt to load and authorize Google Sheets credentials once at startup
raw_credentials = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
if not raw_credentials:
    print("Warning: GOOGLE_SHEETS_CREDENTIALS_JSON environment variable is empty or missing. Google Sheets features will be unavailable.")
else:
    try:
        # Strip any leading/trailing quotes that might be around the JSON string
        raw_credentials = raw_credentials.strip().lstrip("'\"").rstrip("'\"")
        creds_dict = json.loads(raw_credentials)
        # Replace escaped newlines with actual newlines in the private key
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        # Define scopes for Google Sheets API access
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file" # drive.file allows the app to only access files it creates or opens. Use .drive for all files
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        print("Google Sheets client initialized successfully.")
    except json.JSONDecodeError:
        print("Error: Could not parse GOOGLE_SHEETS_CREDENTIALS_JSON. Ensure it's valid JSON. Google Sheets will not be available.")
        gspread_client = None # Explicitly set to None on error
    except Exception as e:
        print(f"Error initializing Google Sheets client: {e}. Google Sheets will not be available.")
        gspread_client = None # Explicitly set to None on error


# --- In-memory storage ---
# Stores data organized by collection name: {'CollectionName': [data_items]}
inventory_data_by_collection = {}
# Stores column definitions: {'CollectionName': [column_defs]}
columns_by_collection = {}
# Tracks the last update time globally
last_update_time = None


# --- Endpoint to receive Tally data (now accepts XML, parses, and stores by collection) ---
@app.route('/api/upload_tally_data', methods=['POST'])
def upload_tally_data():
    global inventory_data_by_collection, columns_by_collection, last_update_time

    # Debug information for the received request
    print("\n===== RECEIVED TALLY DATA REQUEST =====")
    print(f"Request content type: {request.content_type}")
    print(f"Request size: {len(request.data)} bytes")
    
    xml_data_bytes = request.data

    if not xml_data_bytes:
        return jsonify({"status": "error", "message": "No data received in the request body."}), 400

    print(f"First 200 characters of raw data:\n{xml_data_bytes[:200].decode('utf-8', errors='ignore')}")
    print("======================================\n")

    try:
        xml_data_string = xml_data_bytes.decode('utf-8')
        tally_dict = xmltodict.parse(xml_data_string)

        data_list_of_dicts = []
        collection_name = "UnknownCollection"  # Default name if not identified

        # Navigate the common Tally XML structure to find the list of records
        if 'ENVELOPE' in tally_dict and 'BODY' in tally_dict['ENVELOPE'] and \
           'DATA' in tally_dict['ENVELOPE']['BODY'] and \
           'COLLECTION' in tally_dict['ENVELOPE']['BODY']['DATA']:

            collection_section = tally_dict['ENVELOPE']['BODY']['DATA']['COLLECTION']

            found_data = False
            # Iterate through keys in COLLECTION to find a list or handle single dict case
            for key, value in collection_section.items():
                # Heuristic to identify the primary collection tag (often uppercase)
                if key.isupper():
                    if isinstance(value, list):
                        data_list_of_dicts = value
                        collection_name = key  # Use the key as the collection name
                        found_data = True
                        print(f"Parsed data list under key: '{key}' with {len(data_list_of_dicts)} items.")
                        break  # Stop searching after finding the first potential collection data

                    elif isinstance(value, dict):
                        data_list_of_dicts = [value]  # Wrap a single dictionary in a list
                        collection_name = key  # Use the key as the collection name
                        found_data = True
                        print(f"Parsed single data item under key: '{key}'. Wrapped in list.")
                        break  # Stop searching

            if not found_data:
                print(f"Warning: Could not find expected data list/item within the COLLECTION section. Keys found: {collection_section.keys()}")

        if not data_list_of_dicts:
            print("No data records extracted from XML.")
            return jsonify({"status": "error", "message": "No data records found in XML"}), 400

        # Store the data by collection name in the in-memory storage
        inventory_data_by_collection[collection_name] = data_list_of_dicts
        
        # Store column definitions for this collection
        if data_list_of_dicts: # Check if list is not empty
            columns = [{"id": k, "name": k} for k in data_list_of_dicts[0].keys()]
            columns_by_collection[collection_name] = columns
        
        last_update_time = datetime.datetime.now()
        print(f"Stored {len(data_list_of_dicts)} items for collection '{collection_name}' at {last_update_time.isoformat()}")
        print(f"Currently storing data for {len(inventory_data_by_collection)} collections total.")

        # Send to Google Sheets if the client was successfully initialized
        if gspread_client:
            send_to_google_sheets(data_list_of_dicts, collection_name, gspread_client=gspread_client)
        else:
            print("Google Sheets client not available. Skipping data upload to Google Sheets.")


        return jsonify({
            "status": "success",
            "message": f"Received XML, parsed, and stored {len(data_list_of_dicts)} items for '{collection_name}'."
        }), 200

    except xmltodict.expat.ExpatError as e:
        print(f"XML Parsing Error: {e}")
        print(f"Received raw data snippet: {xml_data_bytes[:500].decode('utf-8', errors='ignore')}...")
        return jsonify({"status": "error", "message": f"Failed to parse XML: {e}"}), 400
    except Exception as e:
        print(f"An unexpected error occurred during processing: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to process received data: {str(e)}"}), 500


def send_to_google_sheets(data, collection_name="UnknownCollection", gspread_client=None):
    """
    Sends data to Google Sheets. It attempts to find a worksheet named after the collection;
    otherwise, it defaults to 'Sheet1'.
    """
    if not data:
        print("No data to send to Google Sheets.")
        return

    if gspread_client is None:
        print("Google Sheets client not provided. Skipping Google Sheets upload.")
        return

    try:
        client = gspread_client

        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == 'your-google-sheet-id':
            print("Error: GOOGLE_SHEET_ID is not configured. Cannot send data to Google Sheets.")
            return

        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        try:
            sheet = spreadsheet.worksheet(collection_name)
            print(f"Using worksheet '{collection_name}' for this collection's data.")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Worksheet '{collection_name}' not found. Using default 'Sheet1'.")
            sheet = spreadsheet.worksheet('Sheet1')
        except Exception as sheet_err:
            print(f"An unexpected error occurred while accessing worksheet: {sheet_err}. Falling back to 'Sheet1'.")
            sheet = spreadsheet.worksheet('Sheet1')

        headers = []
        if data:
            # --- MODIFICATION 1: More robust header extraction ---
            # Extract all unique keys from ALL records to ensure all possible columns are captured.
            all_keys = set()
            for record in data:
                all_keys.update(record.keys())
            headers = sorted(list(all_keys)) # Sort headers for consistent order

        rows = [headers] # Start with the headers row
        for record in data:
            row_values = []
            for k in headers:
                value = record.get(k, "") # Get the value or an empty string if key is missing

                # --- MODIFICATION 2: NEW LOGIC TO FLATTEN NESTED OBJECTS ---
                if isinstance(value, dict):
                    # Convert dictionary to a string representation (e.g., JSON string)
                    # This turns {"@TYPE": "Amount"} into '{"@TYPE": "Amount"}' (a string)
                    row_values.append(json.dumps(value))
                elif isinstance(value, list):
                    # Convert list to a string representation (e.g., JSON string)
                    row_values.append(json.dumps(value))
                else:
                    # For simple values (strings, numbers, booleans), use them directly
                    row_values.append(value)
                # --- END NEW LOGIC ---

            rows.append(row_values)

        if headers:
            #sheet.clear()
            sheet.append_rows(rows, value_input_option='USER_ENTERED')
            print(f"Successfully appended {len(rows)} rows to Google Sheet '{sheet.title}'.")
        else:
            print("No data rows to append to Google Sheet after headers were determined.")

    except Exception as e:
        print(f"Error sending data to Google Sheets: {e}")
        print("Please check your Google Sheets configuration, service account permissions, and network connectivity.")

@app.route('/api/get_processed_columns', methods=['GET'])
def get_processed_columns():
    """
    Returns columns organized by collection name to match frontend expectations.
    """
    return jsonify(columns_by_collection), 200


@app.route('/api/get_latest_data', methods=['GET'])
def get_latest_data():
    """
    Returns data organized by collection name to match frontend expectations.
    """
    global inventory_data_by_collection, last_update_time

    return jsonify({
        "data": inventory_data_by_collection,  # Returns dict with collection names as keys
        "last_update": last_update_time.isoformat() if last_update_time else None,
        "message": f"Data for {len(inventory_data_by_collection)} collections" if inventory_data_by_collection else "No data yet."
    }), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """
    Serves your static React build files.
    """
    react_dist = os.path.abspath('../frontend/vite-project/dist')
    # Prevent directory traversal attacks
    if ".." in path or path.startswith('/'):
        return "Not Found", 404

    full_path = os.path.join(react_dist, path)
    if path == "" or (os.path.exists(full_path) and os.path.isfile(full_path)):
        return send_from_directory(react_dist, path or 'index.html')
    # Fallback for client-side routing (e.g., React Router)
    return send_from_directory(react_dist, 'index.html')


# Add a debug endpoint to see what collections are currently stored
@app.route('/api/debug/collections', methods=['GET'])
def debug_collections():
    """
    Debug endpoint to see what collections and how much data are stored in memory.
    """
    collection_stats = {}
    for coll_name, data in inventory_data_by_collection.items():
        collection_stats[coll_name] = {
            "record_count": len(data),
            "sample_keys": list(data[0].keys())[:5] if data else [] # Use 'data' instead of 'data and len(data) > 0'
        }
    
    return jsonify({
        "collections": list(inventory_data_by_collection.keys()),
        "stats": collection_stats,
        "last_update": last_update_time.isoformat() if last_update_time else None
    }), 200


if __name__ == '__main__':
    print("Flask app running.")
    print("Listening for Tally XML data POSTs on /api/upload_tally_data")
    print("React frontend can fetch data/columns from /api/get_latest_data and /api/get_processed_columns")
    print("Debug endpoint available at /api/debug/collections")

    # Change to host="0.0.0.0" to make it accessible from other devices on the network
    app.run(debug=True, port=5000, host="localhost", use_reloader=True)