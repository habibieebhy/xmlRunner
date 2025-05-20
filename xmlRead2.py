import requests
import json
import os
import xml.etree.ElementTree as ET
import schedule
import time

TALLY_URL = "http://localhost:9000"
AVAILABLE_COLLECTIONS_FILE = "available_collections.json"
EXPORT_FOLDER = "exports"

# Add the URL for your Flask application endpoint
FLASK_APP_URL = "http://localhost:5000/api/upload_tally_data"

COLLECTIONS_TO_TRY = [
    "Company",
    "Ledger",
    "StockItem",
    "Group",
    "CostCategory",
    "CostCentre",
    "Currency",
    "Unit",
    "Godown",
]

ENVELOPE_TEMPLATE = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>{collection_id}</ID>
  </HEADER>
  <BODY>
    <DESC></DESC>
  </BODY>
</ENVELOPE>"""

# Query Tally and return raw XML if available
def query_tally(collection_id):
    body = ENVELOPE_TEMPLATE.format(collection_id=collection_id)
    headers = {"Content-Type": "text/xml"}
    try:
        res = requests.post(TALLY_URL, data=body, headers=headers, timeout=10)
        if "<ENVELOPE>" in res.text:
            return res.text
        return None
    except Exception as e:
        print(f" Error querying {collection_id}: {e}")
        return None

# Save available collections
def create_available_directory():
    available_collections = []
    print("\n Checking available collections in Tally...\n")
    for coll in COLLECTIONS_TO_TRY:
        response = query_tally(coll)
        if response:
            print(f" Found: {coll}")
            available_collections.append(coll)
        else:
            print(f" Not Found: {coll}")

    with open(AVAILABLE_COLLECTIONS_FILE, "w") as file:
        json.dump(available_collections, file)
    print(f"\n Available collections saved to {AVAILABLE_COLLECTIONS_FILE}\n")

    return available_collections

# Pretty-print nested XML data
def print_element(elem, indent=0):
    text = elem.text.strip() if elem.text else ""
    if text:
        print("  " * indent + f"{elem.tag}: {text}")
    for child in elem:
        print_element(child, indent + 1)

# Extract and print data, also save XML file
def extract_and_save_data(xml_text, collection_name):
    print(f"\n Data from collection: {collection_name}\n{'-'*60}")
    try:
        root = ET.fromstring(xml_text)
        body = root.find(".//BODY")
        if body is None:
            print(" No BODY tag found.")
            return

        data = body.find(".//DATA")
        if data is None:
            print(" No DATA tag found.")
            return

        print_element(data)

        # Save XML
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        with open(f"{EXPORT_FOLDER}/{collection_name}.xml", "w", encoding="utf-8") as file:
            file.write(xml_text)
        print(f"💾 Saved XML to {EXPORT_FOLDER}/{collection_name}.xml")

    except ET.ParseError as e:
        print(f"❌ XML Parse Error for {collection_name}: {e}")

# Function to send data to Flask
def send_data_to_flask(xml_text, collection_name):
    headers = {"Content-Type": "text/xml"}
    try:
        print(f" Sending data for {collection_name} to Flask at {FLASK_APP_URL}...")
        # Send the XML text as the request body
        res = requests.post(FLASK_APP_URL, data=xml_text, headers=headers, timeout=10)
        res.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f" Successfully sent data for {collection_name} to Flask. Response: {res.text}")
    except requests.exceptions.RequestException as e:
        print(f" Error sending data for {collection_name} to Flask: {e}")
    except Exception as e:
        print(f" An unexpected error occurred while sending data for {collection_name} to Flask: {e}")

# Main flow
def main():
    available_collections = create_available_directory()

    for coll in available_collections:
        print(f"\n Querying Tally for collection: {coll}")
        xml_response = query_tally(coll)
        if xml_response:

            # ✅ Add the call to send data to Flask
            send_data_to_flask(xml_response, coll)

        else:
            print(f" Failed to get data for {coll}")

    print("\n All collections processed.")

if __name__ == "__main__":
    #RUN IMMIDIATELY
    main()
    # Schedule the main function to run every 2 minutes
    schedule.every(2).minutes.do(main)

    print("📆 Starting periodic data extraction... Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")