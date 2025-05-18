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
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')

if not GOOGLE_SHEETS_CREDENTIALS_JSON:
    print("WARNING: GOOGLE_SHEETS_CREDENTIALS_JSON environment variable not set.")
    print("Google Sheets integration will not work without credentials.")


# --- In-memory storage ---
# Modified to store data organized by collection name
inventory_data_by_collection = {}  # Dictionary of lists: {'CollectionName': [data_items]}
columns_by_collection = {}         # Dictionary of columns: {'CollectionName': [column_defs]}
last_update_time = None            # Still tracking last update time globally


# --- Endpoint to receive Tally data (now accepts XML, parses, and stores by collection) ---
@app.route('/api/upload_tally_data', methods=['POST'])
def upload_tally_data():
    global inventory_data_by_collection, columns_by_collection, last_update_time

    # Debug info
    print("\n===== RECEIVED TALLY DATA REQUEST =====")
    print(f"Request content type: {request.content_type}")
    print(f"Request size: {len(request.data)} bytes")
    
    xml_data_bytes = request.data

    if not xml_data_bytes:
        return jsonify({"status": "error", "message": "No data received in the request body."}), 400

    print(f"First 200 characters of raw data:")
    print(xml_data_bytes[:200].decode('utf-8', errors='ignore'))
    print("======================================\n")

    try:
        xml_data_string = xml_data_bytes.decode('utf-8')
        tally_dict = xmltodict.parse(xml_data_string)

        data_list_of_dicts = []
        collection_name = "UnknownCollection"  # Default name if not identified

        # Attempt to navigate the common Tally XML structure and find the list of records
        if 'ENVELOPE' in tally_dict and 'BODY' in tally_dict['ENVELOPE'] and \
           'DATA' in tally_dict['ENVELOPE']['BODY'] and \
           'COLLECTION' in tally_dict['ENVELOPE']['BODY']['DATA']:

            collection_section = tally_dict['ENVELOPE']['BODY']['DATA']['COLLECTION']

            found_data = False
            # Iterate through keys in COLLECTION to find a list or handle single dict case
            for key, value in collection_section.items():
                # Check if the value is data we want (list of dicts or single dict)
                # and if the key is uppercase (often the collection tag name)
                if key.isupper():  # Simple heuristic to identify collection tag
                    if isinstance(value, list):
                        data_list_of_dicts = value
                        collection_name = key  # Use the key as the collection name
                        found_data = True
                        print(f"Parsed data list under key: '{key}' with {len(data_list_of_dicts)} items.")
                        break  # Stop searching after finding the first potential collection data

                    elif isinstance(value, dict):
                        data_list_of_dicts = [value]  # Wrap single dictionary in a list
                        collection_name = key  # Use the key as the collection name
                        found_data = True
                        print(f"Parsed single data item under key: '{key}'. Wrapped in list.")
                        break  # Stop searching

            if not found_data:
                print("Warning: Could not find expected data list/item within the COLLECTION section.")
                print("Keys found in COLLECTION:", collection_section.keys())

        if not data_list_of_dicts:
            print("No data records extracted from XML.")
            return jsonify({"status": "error", "message": "No data records found in XML"}), 400

        # --- Store the data by collection name ---
        inventory_data_by_collection[collection_name] = data_list_of_dicts
        
        # --- Also store column definitions for this collection ---
        if data_list_of_dicts and len(data_list_of_dicts) > 0:
            columns = [{"id": k, "name": k} for k in data_list_of_dicts[0].keys()]
            columns_by_collection[collection_name] = columns
        
        last_update_time = datetime.datetime.now()
        print(f"Stored {len(data_list_of_dicts)} items for collection '{collection_name}' at {last_update_time.isoformat()}")
        print(f"Now storing data for {len(inventory_data_by_collection)} collections total.")

        # Send to Google Sheets - passing the collection name now
        send_to_google_sheets(data_list_of_dicts, collection_name)

        return jsonify({
            "status": "success",
            "message": f"Received XML, parsed, and stored {len(data_list_of_dicts)} items for '{collection_name}'."
        }), 200

    except xmltodict.expat.ExpatError as e:
        print(f"XML Parsing Error: {e}")
        print("Received raw data snippet:", xml_data_bytes[:500].decode('utf-8', errors='ignore') + "...")
        return jsonify({"status": "error", "message": f"Failed to parse XML: {e}"}), 400
    except Exception as e:
        print(f"An unexpected error occurred during processing: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to process received data: {str(e)}"}), 500


def send_to_google_sheets(data, collection_name="UnknownCollection"):
    """
    Send data to Google Sheets, with collection name to potentially use different sheets
    """
    if not data:
        print("No data to send to Google Sheets.")
        return

    if not GOOGLE_SHEETS_CREDENTIALS_JSON:
        print("Google Sheets credentials JSON content not found. Skipping Google Sheets upload.")
        return

    try:
        credentials_info = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(
            credentials_info, scopes=scopes
        )
        client = gspread.authorize(creds)

        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == 'your-google-sheet-id':
             print("Error: GOOGLE_SHEET_ID is not configured. Cannot send data to Google Sheets.")
             return

        # Try to use a sheet named after the collection, if not found, use sheet1
        try:
            sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(collection_name)
            print(f"Using sheet '{collection_name}' for this collection's data.")
        except:
            print(f"Sheet '{collection_name}' not found. Using default sheet1.")
            sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

        headers = []
        if data:
            # Get keys from the first item dictionary
            headers = list(data[0].keys())

        rows = [headers]  # Start with the headers row
        for record in data:
            # Create a row ensuring order matches headers and handling missing keys
            rows.append([record.get(k, "") for k in headers])

        if headers:  # Only append rows if there are headers (meaning data was not empty)
             # Decide if you want to clear the sheet before appending or just keep adding
             sheet.clear()  # Clear the sheet before each upload for this collection
             sheet.append_rows(rows, value_input_option='USER_ENTERED')
             print(f"Appended {len(rows)} rows to Google Sheet '{sheet.title}'.")
        else:
             print("No data rows to append to Google Sheet after headers.")

    except json.JSONDecodeError:
        print("Error: Could not parse GOOGLE_SHEETS_CREDENTIALS_JSON. Ensure it's valid JSON.")
    except Exception as e:
        print(f"Error sending to Google Sheets: {e}")
        print("Please check your Google Sheets configuration, credentials JSON content, and sheet permissions.")


@app.route('/api/get_processed_columns', methods=['GET'])
def get_processed_columns():
    """
    Return columns organized by collection name to match frontend expectations
    """
    return jsonify(columns_by_collection), 200


@app.route('/api/get_latest_data', methods=['GET'])
def get_latest_data():
    """
    Return data organized by collection name to match frontend expectations
    """
    global inventory_data_by_collection, last_update_time

    return jsonify({
        "data": inventory_data_by_collection,  # Now returns dict with collection names as keys
        "last_update": last_update_time.isoformat() if last_update_time else None,
        "message": f"Data for {len(inventory_data_by_collection)} collections" if inventory_data_by_collection else "No data yet."
    }), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    # This serves your static React build files
    react_dist = os.path.abspath('../frontend/vite-project/dist')
    if ".." in path:
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
    Debug endpoint to see what collections and how much data are stored
    """
    collection_stats = {}
    for coll_name, data in inventory_data_by_collection.items():
        collection_stats[coll_name] = {
            "record_count": len(data),
            "sample_keys": list(data[0].keys())[:5] if data and len(data) > 0 else []
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