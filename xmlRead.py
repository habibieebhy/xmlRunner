# xmlRead.py

import xml.etree.ElementTree as ET
import requests
import os
import json # Useful for debugging, though requests handles JSON directly

# --- Configuration ---
# IMPORTANT: Update this path to the SIMPLIFIED XML file you want to read.
# Make sure this script has read access to this file.
# Assuming a typical Debian Downloads folder path. Replace 'your_username' and 'tallyExports2.xml'
# Ensure this path points to the simplified XML file you saved.
LOCAL_XML_FILE_PATH = '/home/rgos/Downloads/tallyExports2.xml' # <-- Ensure this is the correct path to your simplified XML

# IMPORTANT: Update this URL to the address and port where your Flask backend is running.
# Assuming Flask is running on your local machine on port 5050.
FLASK_BACKEND_URL = 'http://localhost:5050/api/upload_tally_data'

# Define the fields we want to extract and the cell index where they are located
# in the SIMPLIFIED Spreadsheetml XML structure (Item Name, Quantity, Price).
ITEM_FIELDS_MAP = {
    'itemName': {'cell_index': 0}, # Item name is in the first cell (index 0)
    'stockQty': {'cell_index': 1}, # Quantity is in the second cell (index 1)
    'rate': {'cell_index': 2} # Price is in the third cell (index 2)
}

# Define the namespace used in the XML for elements like <ss:Table>, <ss:Row>, <ss:Cell>
# You can find this namespace at the root <Workbook> tag: xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
SS_NAMESPACE = 'urn:schemas-microsoft-com:office:spreadsheet'
# Helper function to create a tag name with the namespace
def ns(tag):
    return f'{{{SS_NAMESPACE}}}{tag}'


# --- Function to parse the XML file (Rewritten for Simplified Spreadsheetml) ---
def parse_xml_file(xml_file_path):
    """
    Reads and parses the SIMPLIFIED XML file (Spreadsheetml format) to extract
    Item Name, Quantity, and Price based on cell positions.

    Args:
        xml_file_path (str): The full path to the local XML file.

    Returns:
        list: A list of dictionaries, where each dictionary represents an item
              with extracted 'itemName', 'stockQty', and 'rate'.
        None: If the file cannot be read or parsed.
    """
    extracted_data = []

    if not os.path.exists(xml_file_path):
        print(f"Error: XML file not found at {xml_file_path}")
        return None

    try:
        # Parse the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Find the Worksheet and the Table containing the data
        # Assuming the relevant data is in the first Worksheet and its first Table
        # Need to use the namespace for 'Worksheet' and 'Table'
        worksheet = root.find(ns('Worksheet'))
        if worksheet is None:
            print("Error: Could not find Worksheet element in XML.")
            return None

        table = worksheet.find(ns('Table'))
        if table is None:
            print("Error: Could not find Table element in Worksheet.")
            return None

        # Iterate through each Row in the Table
        # We skip the first row as it contains headers
        rows = table.findall(ns('Row'))
        if not rows:
            print("Warning: No Row elements found in the Table.")
            return []

        # Start processing from the second row (index 1) to skip headers
        # Row index 0 is the header row
        for row_index, row_elem in enumerate(rows):
            if row_index == 0: # Skip the header row
                continue

            # Find all Cell elements within the current Row
            cells = row_elem.findall(ns('Cell'))
            # We expect exactly 3 cells for Item Name, Quantity, and Price in the simplified format
            if len(cells) != 3:
                print(f"Warning: Skipping row {row_index} as it does not have exactly 3 cells ({len(cells)} found).")
                continue

            item_data = {}
            extraction_successful = True # Flag to track if we got all required fields

            # --- Extract Item Name (from cell index 0) ---
            name_cell = cells[ITEM_FIELDS_MAP['itemName']['cell_index']]
            name_data_elem = name_cell.find(ns('Data'))
            item_data['itemName'] = name_data_elem.text.strip() if name_data_elem is not None and name_data_elem.text is not None else 'N/A'
            if item_data['itemName'] == 'N/A':
                 print(f"Warning: Item Name not found in row {row_index}. Skipping this row.")
                 extraction_successful = False


            # --- Extract Quantity (from cell index 1) ---
            if extraction_successful:
                qty_cell = cells[ITEM_FIELDS_MAP['stockQty']['cell_index']]
                qty_data_elem = qty_cell.find(ns('Data'))
                qty_value_str = qty_data_elem.text.strip() if qty_data_elem is not None and qty_data_elem.text is not None else '0' # Default to 0 if not found/empty
                qty_value = 0
                try:
                    # Attempt to convert quantity to an integer
                    cleaned_value = qty_value_str.replace(',', '') # Remove commas
                    qty_value = int(float(cleaned_value)) # Convert via float to handle decimals if any, then to int
                except ValueError:
                    print(f"Warning: Could not convert Quantity '{qty_value_str}' to number for item '{item_data['itemName']}' in row {row_index}. Using 0.")
                    qty_value = 0 # Use 0 if conversion fails
                except Exception as e:
                     print(f"Error processing Quantity '{qty_value_str}' for item '{item_data['itemName']}' in row {row_index}: {e}. Using 0.")
                     qty_value = 0
                item_data['stockQty'] = qty_value


            # --- Extract Price (from cell index 2) ---
            if extraction_successful:
                price_cell = cells[ITEM_FIELDS_MAP['rate']['cell_index']]
                price_data_elem = price_cell.find(ns('Data'))
                price_value_str = price_data_elem.text.strip() if price_data_elem is not None and price_data_elem.text is not None else '0.0' # Default to 0.0
                price_value = 0.0
                try:
                    # Attempt to convert price to a float
                    cleaned_value = price_value_str.replace(',', '') # Remove commas
                    price_value = float(cleaned_value)
                except ValueError:
                    print(f"Warning: Could not convert Price '{price_value_str}' to number for item '{item_data['itemName']}' in row {row_index}. Using 0.0.")
                    price_value = 0.0 # Use 0.0 if conversion fails
                except Exception as e:
                     print(f"Error processing Price '{price_value_str}' for item '{item_data['itemName']}' in row {row_index}: {e}. Using 0.0.")
                     price_value = 0.0
                item_data['rate'] = price_value


            # Only add the item if extraction was successful and it has a valid name
            if extraction_successful and item_data['itemName'] != 'N/A':
                 extracted_data.append(item_data)


        print(f"Successfully extracted data for {len(extracted_data)} items.")
        return extracted_data

    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        # --- More detailed error for parsing ---
        print("Please check if the XML file is valid and matches the expected Spreadsheetml format.")
        return None
    except Exception as e:
        # --- Catch any other unexpected errors during processing ---
        print(f"An unexpected error occurred during XML parsing: {e}")
        print("This might be due to an unexpected structure or data issue in the XML.")
        return None

# --- Function to send data to the Flask backend ---
def send_data_to_flask(data, flask_url):
    """
    Sends the extracted data as a JSON POST request to the Flask backend.

    Args:
        data (list): The list of dictionaries containing inventory data.
        flask_url (str): The URL of the Flask backend endpoint.

    Returns:
        bool: True if the data was sent successfully, False otherwise.
    """
    if not data:
        print("No data to send.")
        return False

    try:
        # Send the data as JSON in a POST request
        print(f"Sending data to Flask backend at {flask_url}...")
        # requests.post automatically sends the 'json' argument with Content-Type: application/json
        response = requests.post(flask_url, json=data)

        # Check if the request was successful (status code 2xx)
        response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)

        print(f"Data successfully sent. Flask response status: {response.status_code}")
        try:
            # Attempt to print JSON response from Flask if available
            print(f"Flask response message: {response.json().get('message', 'No message')}")
        except json.JSONDecodeError:
            print("Flask response is not JSON.")
            print(f"Flask response text: {response.text}")

        return True

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Flask backend at {flask_url}.")
        print("Please ensure your Flask app is running.")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"Error sending data to Flask: HTTP error occurred: {e}")
        print(f"Response body: {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending data to Flask: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during data sending: {e}")
        return False

# --- Main execution block ---
if __name__ == '__main__':
    print("Starting XML data sender script...")

    # 1. Parse the XML file
    inventory_data = parse_xml_file(LOCAL_XML_FILE_PATH)

    # 2. If parsing was successful, send the data to Flask
    if inventory_data is not None:
        if inventory_data: # Check if any data was actually extracted
            send_data_to_flask(inventory_data, FLASK_BACKEND_URL)
        else:
            print("No inventory data extracted from the XML file.")
    else:
        print("Failed to parse the XML file. Data not sent.")

    print("Script finished.")
