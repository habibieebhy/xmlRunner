// frontend/src/components/InventoryDisplay.jsx

import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:5050/api/get_latest_data';
const COLUMNS_API_URL = 'http://localhost:5050/api/get_processed_columns';

function InventoryDisplay() {
  const [inventoryData, setInventoryData] = useState([]);
  const [columnMapping, setColumnMapping] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch columns and data in parallel
      const [columnsRes, dataRes] = await Promise.all([
        fetch(COLUMNS_API_URL),
        fetch(API_URL)
      ]);

      if (!columnsRes.ok || !dataRes.ok) {
        throw new Error('Failed to fetch data from backend');
      }

      const [columns, data] = await Promise.all([
        columnsRes.json(),
        dataRes.json()
      ]);

      setColumnMapping(columns);
      setInventoryData(data.data);
      setLastUpdate(data.last_update ? new Date(data.last_update).toLocaleString() : 'N/A');
      setError(null);
    } catch (error) {
      console.error("Error fetching data:", error);
      setError("Failed to fetch data. Please check the backend connection.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchData();

    // Refresh data every 10 seconds
    const intervalId = setInterval(fetchData, 10000);

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="inventory-container">
      <h1 className="inventory-title">Tally Data Dashboard</h1>
      
      {/* Status indicators */}
      {isLoading && <p className="loading-message">Loading data...</p>}
      {error && <p className="error-message">{error}</p>}
      {!isLoading && !error && (
        <p className="last-update">
          Last Updated: {lastUpdate || 'Never'}
        </p>
      )}

      {/* Dynamic table */}
      {!isLoading && !error && inventoryData.length > 0 && columnMapping.length > 0 && (
        <div className="table-container">
          <table className="inventory-table">
            <thead>
              <tr>
                {columnMapping.map((col) => (
                  <th key={col.id} className="table-header">
                    {col.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inventoryData.map((item, index) => (
                <tr key={index} className="table-row">
                  {columnMapping.map((col) => (
                    <td key={`${index}-${col.id}`} className="table-cell">
                      {item[col.id] || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && inventoryData.length === 0 && (
        <p className="no-data-message">
          No data available. Please upload data through the Tally integration.
        </p>
      )}
    </div>
  );
}

export default InventoryDisplay;