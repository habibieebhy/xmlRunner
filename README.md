# xmlRunner

Its a 3 step process

1. The xmlRead.py reads the xml file data from the device and sends it to Flask Backend

2. The Flask Backend (app.py) recieves the data and sends it to Google Sheets "xml-data-pipeline"

3. The Reaact frontned asks for the same data from flask backend at InventoryDisplay.jsx and and displays it at node port localhost:5173

# NOTE: 
1. IN DEVELOPMENT : Must Run both ports "npm run dev" for frontend and "python3 app.py" for backend and then run "python3 xmlRead.py" separately to work.

2. IN (AFTER) BUILD : After running npm run build, flask backend looks for static files from frontend in the "dist" folder so only running "python3 app.py" and then run "python3 xmlRead.py" will work. UI will display on port 5050 or 5000.
