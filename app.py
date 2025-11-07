from flask import Flask, request, jsonify
from flask_cors import CORS
import xmltodict
import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# In-memory store (for debugging / UI if you view locally)
inventory_data_by_collection = {}
last_update_time = None

# Folder where processed JSON will be stored
EXPORT_FOLDER = "parsed_exports"
os.makedirs(EXPORT_FOLDER, exist_ok=True)


@app.route("/api/upload_tally_data", methods=["POST"])
def upload_tally_data():
    """
    Receives raw XML from xmlRead2.py, converts to JSON,
    stores in memory AND saves to disk.
    """
    global inventory_data_by_collection, last_update_time

    raw_xml = request.data
    if not raw_xml:
        return jsonify({"status": "error", "message": "Empty request"}), 400

    # Parse XML → Python dict
    try:
        parsed = xmltodict.parse(raw_xml.decode("utf-8"))
    except Exception as e:
        return jsonify({"status": "error", "message": f"XML parse failed: {str(e)}"}), 400

    # Extract collection + records
    collection_name = "UnknownCollection"
    data_items = []

    try:
        collection_section = parsed["ENVELOPE"]["BODY"]["DATA"]["COLLECTION"]
        for key, value in collection_section.items():
            if key.isupper():  # This is the real data list
                collection_name = key
                data_items = value if isinstance(value, list) else [value]
                break
    except:
        return jsonify({"status": "error", "message": "Invalid Tally XML"}), 400

    if not data_items:
        return jsonify({"status": "error", "message": "No records found"}), 400

    # Update RAM mirror (for debug UI)
    inventory_data_by_collection[collection_name] = data_items
    last_update_time = datetime.datetime.now()

    # ✅ Save parsed JSON to disk
    file_path = f"{EXPORT_FOLDER}/{collection_name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_items, f, indent=2)

    print(f"💾 Saved {len(data_items)} records → {file_path}")

    return jsonify({
        "status": "success",
        "collection": collection_name,
        "records_saved": len(data_items),
        "file": file_path
    }), 200


@app.route("/api/get_latest_data", methods=["GET"])
def get_latest_data():
    """Return in-memory snapshot for debugging/local UI."""
    return jsonify({
        "data": inventory_data_by_collection,
        "last_update": last_update_time.isoformat() if last_update_time else None
    })


if __name__ == "__main__":
    print("🚀 Tally Local Sync Receiver Running on Port 6000")
    print("Waiting for xmlRead2.py to POST data...")
    app.run(host="0.0.0.0", port=6000, debug=True)
