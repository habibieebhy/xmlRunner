import React, { useState } from "react";
import InventoryDisplay from "./InventoryDisplay";

function App() {
  // State to control the visibility of the dialog box
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Function to open the dialog box
  const openDialog = () => {
    setIsDialogOpen(true);
  };

  // Function to close the dialog box
  const closeDialog = () => {
    setIsDialogOpen(false);
  };

  // Function to handle redirection to the original site
  const redirectToSite = () => {
    window.location.href = "https://www.mycoco.site"; // Redirect to the original site
  };

  return (
    <>
      <InventoryDisplay />

      {/* Button to trigger dialog box (you can add it anywhere in the App as needed) */}
      <button onClick={openDialog} className="dialog-button">
        Our primary site 
      </button>

      {/* Dialog Box */}
      {isDialogOpen && (
        <div className="dialog-bottom">
          <div className="dialog-content">
            <p>Want to visit our original site?</p>
            <div className="dialog-buttons">
              <button className="dialog-button" onClick={redirectToSite}>
                Go to Original Site
              </button>
              <button className="dialog-button cancel" onClick={closeDialog}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default App;