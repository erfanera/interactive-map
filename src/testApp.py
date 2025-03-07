from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from keplergl import KeplerGl
import os
import openai

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set OpenAI API key
openai.api_key = "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"  # Replace with your actual OpenAI API key

# Load datasets
houses_file = "data/cleaned_barcelona_houses.csv"  # Update with correct filename
restaurants_file = "data/cleaned_barcelona_restaurants.csv"
supermarkets_file = "data/cleaned_barcelona_supermarkets.csv"

houses_data = pd.read_csv(houses_file)
restaurants_data = pd.read_csv(restaurants_file)
print(restaurants_data)
supermarkets_data = pd.read_csv(supermarkets_file)

OUTPUT_DIR = "output_maps"  # Directory to store map files
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/process-prompt", methods=["POST"])
def process_prompt():
    prompt = request.json.get("prompt")

    # Validate prompt
    if not prompt or not prompt.strip():
        return jsonify({"error": "The query is empty. Please enter a valid query."}), 400

    # **Step 1: Classify Query (Houses, Restaurants, Supermarkets)**
    classification_prompt = f"""
    You are an AI assistant that classifies user queries into one of three categories:
    - "houses": If the query is related to buying, selling, pricing, or analyzing houses, apartments, or real estate data.
    - "restaurants": If the query is related to restaurants, food, cuisines, meals, dietary options, popularity, or restaurant features.
    - "supermarkets": If the query is about finding supermarkets, grocery stores, or specific supermarket chains (e.g., Carrefour, Lidl, Caprabo).

    Classify the following user query into either "houses", "restaurants", or "supermarkets".
    Only return the classification without any explanation.

    User query: "{prompt}"
    """

    try:
        # OpenAI API Call for classification
        classification_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": classification_prompt}],
            temperature=0
        )
        category = classification_response['choices'][0]['message']['content'].strip().lower()
        print(f"Query Category: {category}")  # Debugging

        # **Step 2: Choose Dataset & Pre-Prompt**
        if category == "houses":
            dataset = houses_data
            pre_prompt = f"""
            You are provided with a dataset containing real estate listings in Barcelona.

            **Columns Available:**
            - PRICE: Price of the property.
            - UNITPRICE: Price per square meter.
            - CONSTRUCTEDAREA: Total constructed area in square meters.
            - ROOMNUMBER: Number of rooms in the house.
            - BATHNUMBER: Number of bathrooms.
            - HASTERRACE, HASLIFT, HASAIRCONDITIONING, HASPARKINGSPACE: Binary indicators for amenities (1 for Yes, 0 for No).
            - DISTANCE_TO_CITY_CENTER: Distance from the property to the city center in km.
            - longitude, latitude: Location coordinates.
            - if someone ask for balcony use HASTERRACE
            **Example Queries:**
            - "Find houses under 500k" → filtered_data = data[data["PRICE"] < 500000]
            - "Show houses with at least 3 rooms and 2 bathrooms" → filtered_data = data[(data["ROOMNUMBER"] >= 3) & (data["BATHNUMBER"] >= 2)]
            - "Find houses with a swimming pool" → filtered_data = data[data["HASSWIMMINGPOOL"] == 1]
            - "Find houses near the city center under 300k" → filtered_data = data[(data["PRICE"] < 300000) & (data["DISTANCE_TO_CITY_CENTER"] < 2)]

            Based on the user query, generate Python code to filter the dataset.
            **Return only Python code without explanations.**

            User query: "{prompt}"
            """

        elif category == "restaurants":
            dataset = restaurants_data
            pre_prompt = f"""
            You are provided with a dataset of restaurants in Barcelona.

            **Columns Available:**
            - restaurant_name: Name of the restaurant.
            - total_reviews_count: integer that shows number of popularity
            - vegetarian_friendly, vegan_options, gluten_free: Dietary accommodations (Y for Yes, N for No).
            - longitude, latitude: Geolocation.

            **How to Process Queries**
            1. If the query mentions **diets (vegetarian, vegan, gluten-free)**, filter on vegetarian_friendly, vegan_options, or gluten_free.
            2. If the query mentions **ranking (e.g., top X)**, sort by total_reviews_count and use .head(X).
            3. If the query mentions **cuisine type**, filter using cuisines.

            **Example Queries and Code**
            - "Find top 5 vegetarian-friendly restaurants with good reviews"  
              

              filtered_data = data[data["vegetarian_friendly"] == "Y"].sort_values(by="total_reviews_count", ascending=True).head(5)


            **User Query:** "{prompt}"
            """

        elif category == "supermarkets":
            dataset = supermarkets_data
            pre_prompt = f"""
            You are provided with a dataset containing supermarket locations in Barcelona.

            **Columns Available:**
            - name: The name of the supermarket (e.g., Carrefour, Lidl, Caprabo).
            - latitude, longitude: Geolocation of the supermarket.

            **Example Queries:**
            - "Find all Carrefour supermarkets" → filtered_data = data[data["name"].str.contains("Carrefour", case=False, na=False)]

            Based on the user query, generate Python code to filter the dataset.
            **Return only Python code without explanations.**

            User query: "{prompt}"
            """
        else:
            return jsonify({"error": "Unable to classify query. Please refine your request."}), 400

        # **Step 3: Generate Filtering Code**
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": pre_prompt}],
            temperature=0
        )
        generated_code = response['choices'][0]['message']['content']
        print("Generated Code:\n", generated_code)  # Debugging

        # Extract Python code using regex
        import re
        match = re.search(r" python(.*?)", generated_code, re.DOTALL)

        if match:
            sanitized_code = match.group(1).strip()
        else:
            sanitized_code = generated_code.strip()

        print("Sanitized Code:\n", sanitized_code)  # Debugging

        # Execute the sanitized code
        local_vars = {
            "data": dataset.copy(),
            "pd": pd
        }
        exec(sanitized_code, {}, local_vars)
        filtered_data = local_vars.get("filtered_data")

        # **Step 4: Handle Results**
        if filtered_data is None or filtered_data.empty:
            return jsonify({"error": "No data matches the query."}), 400

        # Generate a new map
        barcelona_lat = 41.3851  # Central latitude of Barcelona
        barcelona_lon = 2.1734   # Central longitude of Barcelona
        zoom_level = 12          # Default zoom level for the city

        # Generate a new map
       
       
        # Update map configuration to always focus on Barcelona
        config = {
            "version": "v1",
            "config": {
                "mapState": {
                    "latitude": barcelona_lat,
                    "longitude": barcelona_lon,
                    "zoom": zoom_level
                }
            }
        }
        

        filtered_map = KeplerGl(height=600)
        filtered_map.add_data(data=filtered_data[['latitude', 'longitude']], name="Filtered Data")
        filtered_map.config = config

        # Save the map
        new_map_file = os.path.join(OUTPUT_DIR, "filtered_map.html")
        filtered_map.save_to_html(file_name=new_map_file)
        return jsonify({"filteredMap": "filtered_map.html"})

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": f"Failed to process the query. Error: {str(e)}"}), 500

@app.route("/maps/<filename>")
def get_map(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)