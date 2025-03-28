import os
from flask import Flask, request, jsonify
import google.generativeai as genai
from flask_cors import CORS
import json
import re

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load API key from environment variable
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Prompt template for structured IPC response
prompt_template = """Provide a structured JSON response based on the Indian Penal Code, 1860.
The output should strictly follow this format:

{
  "art section": "[Section Name or Number]",
  "category": "[Category of Crime]",
  "Punishment": "[Punishment as per IPC]",
  "Applicable": "[Who the law applies to]",
  "Brief description": "[Short and unique explanation]"
}

Use concise and clear language. Ensure the details are accurate based on IPC provisions.
"""

# Route to get AI response
@app.route("/get_response", methods=["POST"])
def get_response():
    try:
        # Get input from the user
        data = request.get_json()
        user_input = data.get("prompt", "")
        full_prompt = prompt_template + "\nIPC Section: " + user_input

        # Generate response from Gemini AI
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
        response = model.generate_content(full_prompt)

        # Handle the AI response
        response_text = response.text.strip()

        # Log the raw response to inspect if it's malformed or incomplete
        # print("Raw AI response:", response_text)

        # Perform string operations to clean and sanitize the response
        cleaned_response = sanitize_response(response_text)

        # Try parsing the sanitized response as JSON
        try:
            response_json = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Log and return the response if it's still invalid JSON
            print("Error parsing sanitized response:", cleaned_response)
            return jsonify({"error": "AI response is not in valid JSON format."}), 400

        # Ensure that the response contains all required keys
        expected_keys = ["art section", "category", "Punishment", "Applicable", "Brief description"]
        if not all(key in response_json for key in expected_keys):
            return jsonify({"error": "Response missing required fields."}), 400

        # Return the structured response
        return jsonify({"response": response_json})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def sanitize_response(response_text):
    """
    Function to clean and format the AI response into valid JSON.
    """
    # Remove unnecessary newlines and extra spaces
    cleaned_text = response_text.replace("\n", " ").strip()

    # Fix common mistakes like missing colons or commas
    cleaned_text = re.sub(r'(\w)\s*:', r'"\1":', cleaned_text)  # Ensures keys are quoted
    cleaned_text = re.sub(r'(\w)\s*"', r'"\1": "', cleaned_text)  # Ensure correct key-value structure

    # Add quotes around values that are unquoted (simple cases)
    cleaned_text = re.sub(r'(?<=:\s)(\w+)', r'"\1"', cleaned_text)

    # Ensure the response starts and ends with curly braces
    if not cleaned_text.startswith("{"):
        cleaned_text = "{" + cleaned_text
    if not cleaned_text.endswith("}"):
        cleaned_text = cleaned_text + "}"

    return cleaned_text

if __name__ == "__main__":
    app.run(debug=True, port=6000)
