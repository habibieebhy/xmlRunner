import requests
import xml.etree.ElementTree as ET
import json

# --- Config ---
TALLY_API_URL = 'http://localhost:9000/'
FLASK_BACKEND_URL = 'http://localhost:5050/api/upload_tally_data'

# --- XML Payload: Day Book for 1st April 2024 ---
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
          <SVTODATE>20240401</SVTODATE>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <SVVIEWNAME>Accounting Voucher View</SVVIEWNAME>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>
"""

# --- Fetch from Tally ---
def fetch_data_from_tally(tally_url, xml_payload):
    print("📡 Sending request to Tally...")
    try:
        response = requests.post(tally_url, data=xml_payload)
        response.raise_for_status()
        print("✅ Response received.")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Tally fetch error: {e}")
        return None

# --- XML Element → Dict ---
def element_to_dict(element):
    data = {}
    for child in element:
        if len(child) > 0:
            data[child.tag] = element_to_dict(child)
        else:
            data[child.tag] = child.text.strip() if child.text else None
    return data

# --- Parse Tally XML ---
def parse_and_filter_tally_response(xml_string):
    if not xml_string:
        return None

    try:
        root = ET.fromstring(xml_string)
        request_data = root.find('.//REQUESTDATA')

        if request_data is None:
            print("⚠️ <REQUESTDATA> not found.")
            return None

        for tally_msg in request_data.findall('TALLYMESSAGE'):
            parsed = element_to_dict(tally_msg)
            for key, voucher in parsed.items():
                if isinstance(voucher, dict):
                    if (
                        voucher.get("VOUCHERTYPENAME", "").lower() == "payment"
                        and voucher.get("DATE", "") == "20240401"
                        and "5000" in json.dumps(voucher)
                    ):
                        print("🎯 Found matching voucher.")
                        return {
                            "REQUESTDATA": {
                                "TALLYMESSAGE": [{key: voucher}]
                            }
                        }

        print("❌ No matching voucher found.")
        return None

    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None

# --- Send to Flask ---
def send_data_to_flask(data, flask_url):
    try:
        print("📡 Sending filtered voucher to Flask...")
        response = requests.post(flask_url, json=data)
        response.raise_for_status()
        print(f"✅ Success! Flask responded: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Flask send error: {e}")
        return False

# --- Main ---
def main():
    xml_response = fetch_data_from_tally(TALLY_API_URL, TALLY_XML_REQUEST_PAYLOAD)

    if xml_response:
        parsed_voucher = parse_and_filter_tally_response(xml_response)

        if parsed_voucher:
            print("\n📦 Final JSON Payload:")
            print(json.dumps(parsed_voucher, indent=2))
            send_data_to_flask(parsed_voucher, FLASK_BACKEND_URL)
        else:
            print("🚫 No voucher to send.")

if __name__ == '__main__':
    main()
