import requests
import xml.etree.ElementTree as ET
import json
import logging
import time
from datetime import datetime

# --- Logging ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Config ---
TALLY_API_URL = 'http://localhost:9000/'
FLASK_BACKEND_URL = 'http://localhost:5050/api/upload_tally_data'

TALLY_XML_REQUEST_PAYLOAD = """
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
          <SVFROMDATE>20240401</SVFROMDATE>
          <SVTODATE>20240531</SVTODATE>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <SVVIEWNAME>Accounting Voucher View</SVVIEWNAME>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>
"""

# --- Helpers ---

def element_to_dict(element):
    """Recursive conversion of XML to dict."""
    def recursive_parse(elem):
        result = {}
        for child in elem:
            key = child.tag.split('}')[-1]
            if len(child):
                value = recursive_parse(child)
            else:
                value = child.text.strip() if child.text else None

            if key.endswith('.LIST'):
                key = key.replace('.LIST', '')
                result.setdefault(key, []).append(value)
            else:
                result[key] = value
        return result
    return recursive_parse(element)

def parse_tally_response(xml_string):
    try:
        root = ET.fromstring(xml_string)
        request_data = root.find('.//REQUESTDATA')
        if request_data is None:
            logging.error("REQUESTDATA not found in Tally response.")
            return None

        tally_messages = []
        for tally_msg in request_data.findall('.//TALLYMESSAGE'):
            for voucher in tally_msg.findall('.//VOUCHER'):
                v_data = element_to_dict(voucher)
                tally_messages.append(v_data)

        if tally_messages:
            return {'REQUESTDATA': {'TALLYMESSAGE': tally_messages}}
        else:
            logging.warning("No VOUCHER data found inside REQUESTDATA.")
            return None
    except ET.ParseError as e:
        logging.error(f"XML Parse Error: {e}")
        return None

def send_data_to_flask(data):
    if not data:
        logging.warning("No data to send to Flask.")
        return False

    for attempt in range(3):
        try:
            response = requests.post(
                FLASK_BACKEND_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            json_response = response.json()
            if json_response.get('status') == 'success':
                logging.info("Data successfully sent to Flask backend.")
                return True
            else:
                logging.error("Flask responded with an error: %s", json_response)
        except requests.exceptions.RequestException as e:
            logging.warning("Attempt %d failed: %s", attempt + 1, str(e))
            time.sleep(2 ** attempt)
    logging.error("All attempts to send data failed.")
    return False

# --- Main Execution ---

def main():
    logging.info("Starting Tally-to-Flask integration")
    try:
        # Send request to Tally
        response = requests.post(
            TALLY_API_URL,
            data=TALLY_XML_REQUEST_PAYLOAD,
            headers={'Content-Type': 'application/xml'},
            timeout=15
        )
        response.raise_for_status()
        logging.info("Tally response received.")

        # Parse XML response
        parsed_data = parse_tally_response(response.text)
        if not parsed_data:
            logging.error("Failed to parse Tally response.")
            return

        # Send parsed data to Flask
        send_data_to_flask(parsed_data)

    except Exception as e:
        logging.error("Main execution failed: %s", str(e), exc_info=True)

if __name__ == '__main__':
    main()