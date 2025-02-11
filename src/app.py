from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from keplergl import KeplerGl
import os

app = Flask(__name__)
CORS(app)

# Load the initial dataset
file_path = 'D:/IaaC/DataVis/data_vis_project/Barcelona_Sale.csv'
data = pd.read_csv(file_path)

OUTPUT_DIR = "output_maps"  # Directory to store map files
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/process-prompt", methods=["POST"])
def process_prompt():
    prompt = request.json.get("prompt")
    
    # Parse prompt (example: "Show houses under 35k")
    if "under" in prompt:
        price_limit = int(prompt.split("under")[1].strip().replace("k", "000"))
        filtered_data = data[data["PRICE"] < price_limit]
    else:
        return jsonify({"error": "Invalid prompt format"}), 400

    # Get the bounding box for the filtered data
    if not filtered_data.empty:
        min_lat, max_lat = filtered_data["LATITUDE"].min(), filtered_data["LATITUDE"].max()
        min_lon, max_lon = filtered_data["LONGITUDE"].min(), filtered_data["LONGITUDE"].max()
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        zoom_level = 10  # Adjust as necessary for your data's spread
    else:
        # Default view if no data matches the filter
        center_lat, center_lon, zoom_level = 41.3851, 2.1734, 12  # Centered on Barcelona

    # Create a new Kepler map with adjusted view
    filtered_map = KeplerGl(height=600)
    filtered_map.add_data(data=filtered_data[['LATITUDE', 'LONGITUDE', 'PRICE']], name="Filtered Houses")
    config = {
        "version": "v1",
        "config": {
            "mapState": {
                "latitude": center_lat,
                "longitude": center_lon,
                "zoom": zoom_level
            }
        }
    }
    filtered_map.config = config

    # Save the map
    new_map_file = os.path.join(OUTPUT_DIR, "filtered_map.html")
    filtered_map.save_to_html(file_name=new_map_file)
    
    return jsonify({"filteredMap": "filtered_map.html"})

@app.route("/maps/<filename>")
def get_map(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
