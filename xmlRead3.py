import requests

# Tally API URL
TALLY_API_URL = 'http://localhost:9000/'

# XML Payload to request Day Book (example)
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

# Send the XML request and print the raw response
def main():
    try:
        print(f"📡 Sending request to Tally at {TALLY_API_URL} ...")
        response = requests.post(TALLY_API_URL, data=TALLY_XML_REQUEST_PAYLOAD)
        response.raise_for_status()
        print("✅ Response received. Showing first 5000 characters:\n")
        print(response.text[:5000])  # Show only the first 5000 characters
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()