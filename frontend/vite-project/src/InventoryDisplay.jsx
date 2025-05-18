// frontend/src/components/InventoryDisplayTables.jsx

import React, { useState, useEffect } from 'react';

// Update API URLs to match your Flask backend endpoints
const API_URL = 'http://localhost:5000/api/get_latest_data';
const COLUMNS_API_URL = 'http://localhost:5000/api/get_processed_columns';

// Optional: Mapping for more user-friendly table titles
const COLLECTION_TITLES = {
    'Ledger': 'Ledger Data',
    'StockItem': 'Stock Item Data', 
    'Company': 'Company Data',
    'Group': 'Group Data',
    'CostCategory': 'Cost Category Data',
    'CostCentre': 'Cost Centre Data',
    'Currency': 'Currency Data',
    'Unit': 'Unit Data',
    'Godown': 'Godown Data',
    // Add other collection names from your COLLECTIONS_TO_TRY list as needed
};

function InventoryDisplayTables() {
  // State variables to hold data and columns for ALL collections
  // Use objects where keys are collection names
  const [collectionData, setCollectionData] = useState({}); // { CollectionName: [...] }
  const [collectionColumns, setCollectionColumns] = useState({}); // { CollectionName: [...] }

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    let isMounted = true; // Flag to prevent state updates if component unmounts

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch columns for all collections
        const columnsResponse = await fetch(COLUMNS_API_URL);
        if (!columnsResponse.ok) {
          throw new Error(`HTTP error! status: ${columnsResponse.status} from ${COLUMNS_API_URL}`);
        }
        const columnsData = await columnsResponse.json(); // Expected: { CollectionName1: [...], CollectionName2: [...] }

        // Fetch the latest data for all collections
        const dataResponse = await fetch(API_URL);
        if (!dataResponse.ok) {
          throw new Error(`HTTP error! status: ${dataResponse.status} from ${API_URL}`);
        }
        const result = await dataResponse.json(); // Expected: { data: { CollectionName1: [...], CollectionName2: [...] }, last_update: "..." }

        if (isMounted) {
          // Update state with fetched data and columns objects directly
          // Ensure data and columns properties exist and are objects
          setCollectionColumns(columnsData || {});
          setCollectionData(result.data || {});

          setLastUpdate(
            result.last_update
              ? new Date(result.last_update).toLocaleString()
              : 'N/A'
          );
        }
      } catch (err) {
        console.error('Error fetching Tally data:', err);
        if (isMounted) {
          setError(
            'Failed to fetch Tally data. Please ensure the Flask backend is running and accessible.'
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    // Initial fetch
    fetchData();

    // Set up interval for periodic fetching (every 15 seconds)
    const intervalId = setInterval(fetchData, 15000);

    // Cleanup function to clear interval and prevent state updates on unmount
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []); // Empty dependency array means this effect runs only once on mount


    // Get a list of collection names for which we have both data and columns
    const availableCollections = Object.keys(collectionData).filter(collectionName =>
        collectionData[collectionName] &&
        collectionData[collectionName].length > 0 &&
        collectionColumns[collectionName] &&
        collectionColumns[collectionName].length > 0
    );


  return (
    <div className="inventory-container"> {/* Main container class */}
      <h1 className="inventory-title">Tally Data Display</h1> {/* Title class */}

      {isLoading && <p className="loading-message">Loading Tally data...</p>} {/* Loading message class */}
      {error && <p className="error-message">{error}</p>} {/* Error message class */}
      {!isLoading && !error && lastUpdate && <p className="last-update">Last Updated: {lastUpdate}</p>} {/* Last update class */}


      {!isLoading && !error && availableCollections.length === 0 && (
         <p className="no-data-message">
             No Tally data available yet. Please ensure the Flask backend is running,
             connected to Tally, and has successfully uploaded data.
         </p>
      )}

      {/* --- Dynamic Table Rendering --- */}
      {!isLoading && !error && availableCollections.length > 0 && (
          availableCollections.map(collectionName => {
              const data = collectionData[collectionName];
              const columns = collectionColumns[collectionName];
              const tableTitle = COLLECTION_TITLES[collectionName] || `${collectionName} Data`; // Use friendly title or collection name

              return (
                  <div key={collectionName} className="table-section"> {/* Use collection name as key */}
                      <h2 className="table-title">{tableTitle}</h2> {/* Dynamic section title */}
                      {data && data.length > 0 ? (
                          <div className="table-container"> {/* Table container class */}
                              <table className="data-table"> {/* Table class */}
                                  <thead>
                                      <tr>
                                          {columns.map((col, index) => (
                                              <th key={col.id || index} className="table-header">{col.name}</th>
                                          ))}
                                      </tr>
                                  </thead>
                                  <tbody>
                                      {data.map((item, rowIndex) => (
                                          <tr key={rowIndex} className="table-row"> {/* Row class */}
                                              {columns.map((col, colIndex) => (
                                                  <td key={col.id || colIndex} className="table-cell"> {/* Cell class */}
                                                      {/* Access data using the column ID as the key */}
                                                      {item[col.id] !== undefined ? String(item[col.id]) : ''} {/* Convert to string for rendering */}
                                                  </td>
                                              ))}
                                          </tr>
                                      ))}
                                  </tbody>
                              </table>
                          </div>
                      ) : (
                          <p className="no-data-message">No {tableTitle.toLowerCase()} available yet.</p>
                      )}
                  </div>
              );
          })
      )}

    </div>
  );
}

export default InventoryDisplayTables;