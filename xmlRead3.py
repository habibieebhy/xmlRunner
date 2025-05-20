import requests
import json
import os
import re
import schedule
import time
from lxml import etree as ET
from datetime import datetime

# ================== CONFIGURATION ==================
TALLY_URL = "http://localhost:9000"
FLASK_APP_URL = "http://localhost:5000/api/upload_tally_data"
AVAILABLE_COLLECTIONS_FILE = "available_collections.json"
EXPORT_FOLDER = "exports"
LOG_FILE = "tally_import.log"

COLLECTIONS_TO_TRY = [
    "Company", "Ledger", "StockItem", "Group",
    "CostCategory", "CostCentre", "Currency", "Unit", "Godown"
]

ENVELOPE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>{collection_id}</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""

# ================== HELPER FUNCTIONS ==================
def log_message(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    print(log_entry.strip())

def sanitize_tally_xml(xml_text):
    """Fix Tally's XML quirks and special characters"""
    # Add XML declaration if missing
    if not xml_text.startswith('<?xml'):
        xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_text
    
    # Replace problematic characters
    char_replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    
    # First pass replacement
    for unsafe, safe in char_replacements.items():
        xml_text = xml_text.replace(unsafe, safe)
    
    # CDATA wrapping for known problematic fields
    cdata_fields = ['NAME', 'ADDRESS', 'DESCRIPTION', 'LEDGERNAME', 'PARENT']
    for field in cdata_fields:
        xml_text = re.sub(
            rf'<{field}>(.*?)</{field}>',
            lambda m: f'<{field}><![CDATA[{m.group(1)}]]></{field}>',
            xml_text,
            flags=re.DOTALL
        )
    
    # Remove non-printable characters
    xml_text = ''.join(c for c in xml_text if c in ('\t', '\n', '\r') or c.isprintable())
    
    return xml_text

def validate_xml(xml_text):
    """Validate XML structure with CDATA preservation"""
    try:
        parser = ET.XMLParser(
            recover=False,
            strip_cdata=False,
            resolve_entities=False
        )
        ET.fromstring(xml_text.encode('utf-8'), parser=parser)
        return True, None
    except ET.XMLSyntaxError as e:
        error_msg = f"XML Validation Error (Line {e.position[0]}, Column {e.position[1]}): {e.msg}"
        return False, error_msg

# ================== CORE FUNCTIONALITY ==================
def query_tally(collection_id):
    """Query Tally ERP with enhanced XML handling"""
    body = ENVELOPE_TEMPLATE.format(collection_id=collection_id)
    headers = {"Content-Type": "text/xml"}
    
    try:
        response = requests.post(
            TALLY_URL,
            data=body,
            headers=headers,
            timeout=15
        )
        
        if not response.ok:
            log_message(f"Tally returned {response.status_code} for {collection_id}", "ERROR")
            return None

        raw_xml = response.text
        sanitized_xml = sanitize_tally_xml(raw_xml)
        
        # Validate after sanitization
        is_valid, validation_error = validate_xml(sanitized_xml)
        if not is_valid:
            log_message(f"Invalid XML from Tally for {collection_id}: {validation_error}", "ERROR")
            return None
            
        return sanitized_xml
        
    except Exception as e:
        log_message(f"Connection error for {collection_id}: {str(e)}", "ERROR")
        return None

def process_collection(collection_id):
    """Full processing pipeline for a single collection"""
    log_message(f"Processing {collection_id}...")
    
    # Step 1: Fetch data from Tally
    xml_data = query_tally(collection_id)
    if not xml_data:
        return False
    
    # Step 2: Save to local file
    try:
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        output_path = os.path.join(EXPORT_FOLDER, f"{collection_id}.xml")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_data)
        log_message(f"Saved {collection_id}.xml")
    except Exception as e:
        log_message(f"File save failed for {collection_id}: {str(e)}", "ERROR")
        return False
    
    # Step 3: Send to Flask
    if not send_to_flask(xml_data, collection_id):
        return False
    
    return True

def send_to_flask(xml_text, collection_name):
    """Enhanced Flask transmission with validation"""
    headers = {"Content-Type": "application/xml"}
    
    try:
        # Pre-send validation
        is_valid, validation_error = validate_xml(xml_text)
        if not is_valid:
            log_message(f"Pre-flight validation failed for {collection_name}: {validation_error}", "ERROR")
            return False
        
        response = requests.post(
            FLASK_APP_URL,
            data=xml_text.encode('utf-8'),
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 400:
            log_message(f"Flask rejected {collection_name}: {response.text[:200]}", "ERROR")
            return False
            
        response.raise_for_status()
        log_message(f"Successfully sent {collection_name} to Flask")
        return True
        
    except requests.exceptions.RequestException as e:
        log_message(f"Network error sending {collection_name}: {str(e)}", "ERROR")
        return False

# ================== SCHEDULER & MAIN FLOW ==================
def discover_collections():
    """Find available Tally collections"""
    available = []
    log_message("Starting collection discovery...")
    
    for coll in COLLECTIONS_TO_TRY:
        if query_tally(coll):
            available.append(coll)
            log_message(f"Discovered collection: {coll}")
        else:
            log_message(f"Collection not found: {coll}", "WARNING")
    
    with open(AVAILABLE_COLLECTIONS_FILE, "w") as f:
        json.dump(available, f)
    
    log_message(f"Saved discovered collections to {AVAILABLE_COLLECTIONS_FILE}")
    return available

def main_job():
    """Main processing job for scheduled runs"""
    collections = discover_collections()
    success_count = 0
    
    for coll in collections:
        if process_collection(coll):
            success_count += 1
    
    log_message(f"Job completed: {success_count}/{len(collections)} collections processed")

if __name__ == "__main__":
    # Initial run
    log_message("=== Tally Data Import Started ===")
    main_job()
    
    # Scheduled runs
    schedule.every(2).minutes.do(main_job)
    log_message("Scheduler started - Ctrl+C to exit")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log_message("=== Process Stopped by User ===")

# ================== GIT SAFETY ==================
# Create .gitignore if missing
if not os.path.exists(".gitignore"):
    with open(".gitignore", "w") as f:
        f.write("\n".join([
            "# Auto-generated",
            "__pycache__/",
            "*.xml",
            "exports/",
            "*.log",
            ".env",
            "*.json"
        ]))
