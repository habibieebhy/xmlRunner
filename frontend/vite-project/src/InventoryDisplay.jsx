// frontend/src/components/InventoryDisplay.jsx

import React, { useState, useEffect } from 'react';
// You might need to install axios: npm install axios or yarn add axios
// import axios from 'axios'; // Using fetch for simplicity here

// Define the URLs for your Flask backend API
// Make sure these match the port your Flask app is running on (5050)
const API_URL = 'http://localhost:5050/api/get_latest_data';
const COLUMNS_API_URL = 'http://localhost:5050/api/get_processed_columns';


function InventoryDisplay() {
  // State to hold the inventory data fetched from the backend
  const [inventoryData, setInventoryData] = useState([]);
  // State to hold the column mapping (id and name) fetched from the backend
  const [columnMapping, setColumnMapping] = useState([]);
  // State to track loading status
  const [isLoading, setIsLoading] = useState(true);
  // State to hold any error messages
  const [error, setError] = useState(null);
  // State to hold the timestamp of the last update
  const [lastUpdate, setLastUpdate] = useState(null);

  // useEffect hook to fetch data when the component mounts
  useEffect(() => {
    // Function to fetch data from the Flask backend
    const fetchData = async () => {
      try {
        // --- Step 1: Fetch the list of columns (id and name mapping) ---
        const columnsResponse = await fetch(COLUMNS_API_URL);
        if (!columnsResponse.ok) {
             throw new Error(`HTTP error! status: ${columnsResponse.status} from ${COLUMNS_API_URL}`);
        }
        const columnsData = await columnsResponse.json();
        // Store the column mapping in state
        setColumnMapping(columnsData);

        // --- Step 2: Fetch the actual inventory data ---
        const dataResponse = await fetch(API_URL);
        if (!dataResponse.ok) {
          throw new Error(`HTTP error! status: ${dataResponse.status} from ${API_URL}`);
        }
        const result = await dataResponse.json();

        // --- Step 3: Update state with fetched data and last update time ---
        // The 'data' property from the Flask response contains the list of items
        setInventoryData(result.data);
        // The 'last_update' property contains the timestamp
        setLastUpdate(result.last_update ? new Date(result.last_update).toLocaleString() : 'N/A');

      } catch (error) {
        // Catch and set any errors that occur during fetching
        console.error("Error fetching inventory data:", error);
        setError("Failed to fetch inventory data. Please ensure the Flask backend is running and accessible.");
      } finally {
        // Set loading to false once fetching is complete (success or failure)
        setIsLoading(false);
      }
    };

    // Call the fetchData function when the component mounts
    fetchData();

    // Optional: Set up an interval to refetch data periodically
    // const intervalId = setInterval(fetchData, 15000); // Refetch every 15 seconds (adjust as needed)

    // Cleanup function to clear the interval when the component unmounts
    // return () => clearInterval(intervalId);

  }, []); // The empty dependency array ensures this effect runs only once on mount

  // --- Render the UI ---
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Inventory Data</h1>

      {/* Display loading message */}
      {isLoading && <p>Loading inventory data...</p>}

      {/* Display error message */}
      {error && <p className="text-red-500">{error}</p>}

      {/* Display the last update time */}
      {!isLoading && !error && <p className="text-sm text-gray-600 mb-4">Last Updated: {lastUpdate}</p>}

      {/* Display the data table if data is available and no error */}
      {/* Ensure columnMapping is also loaded before rendering the table */}
      {!isLoading && !error && inventoryData.length > 0 && columnMapping.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-300 rounded-lg shadow-md">
            <thead>
              <tr>
                {/* Render table headers using column names from the mapping */}
                {columnMapping.map((col, index) => (
                  <th key={col.id || index} className="py-2 px-4 border-b bg-gray-200 text-left text-sm font-semibold text-gray-700">
                    {col.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Render table rows with data */}
              {inventoryData.map((item, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-100">
                  {/* Render table cells for each item */}
                  {/* Use the column id from the mapping to access the correct value in the item object */}
                   {columnMapping.map((col, colIndex) => (
                       <td key={col.id || colIndex} className="py-2 px-4 border-b text-sm text-gray-800">
                           {/* Access data using the column id */}
                           {item[col.id]}
                       </td>
                   ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Message if no data is available after loading */}
      {!isLoading && !error && inventoryData.length === 0 && (
        <p>No inventory data available yet. Please ensure the Python script has run successfully.</p>
      )}
       {/* Message if columns couldn't be loaded */}
      {!isLoading && !error && inventoryData.length > 0 && columnMapping.length === 0 && (
        <p className="text-red-500">Could not load column information from the backend.</p>
      )}
    </div>
  );
}

export default InventoryDisplay;
