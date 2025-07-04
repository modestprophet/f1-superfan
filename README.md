# Jetson Nano Camera with Ollama

This application allows you to perform LLM inference using a Jetson Nano's CSI camera and Ollama. It captures images from a Waveshare IMX219 IR camera, sends them to an Ollama server for inference, and displays the results on a web interface.

## Requirements

- Jetson Nano 4GB
- Waveshare IMX219 IR camera
- Python 3.6+
- Flask
- OpenCV
- Requests
- Ollama server (can be running on a different machine)

## Installation

1. Clone this repository
2. Install the required Python packages:
   ```
   pip install flask opencv-python requests
   ```
3. Make sure your Waveshare IMX219 IR camera is properly connected to the Jetson Nano

## Usage

1. Start the server:
   ```
   python server.py
   ```
2. Open a web browser and navigate to `http://<jetson-nano-ip>:5000`
3. The web interface will display:
   - Live camera feed from the Jetson Nano
   - Configuration options for Ollama (host and model)
   - A text area for entering your prompt
   - A button to run inference
   - An area to display the inference results

4. Enter your Ollama host URL (e.g., `http://localhost:11434` if Ollama is running on the same machine)
5. Select an Ollama model that supports image input (e.g., `llava`, `llava-llama3`, `moondream`)
6. Enter your prompt (e.g., "Describe what you see in this image")
7. Click "Run Inference" to capture the current frame and send it to Ollama for processing
8. The inference results will be displayed in the result area

## How It Works

The application consists of two main components:

1. **Backend (server.py)**:
   - Uses the gstreamer_pipeline from simple_camera.py to capture frames from the CSI camera
   - Provides API endpoints for:
     - Serving the web interface
     - Streaming the camera feed
     - Capturing the current frame
     - Running inference with Ollama

2. **Frontend (templates/index.html)**:
   - Displays the camera feed
   - Provides input fields for Ollama configuration and prompt
   - Sends requests to the backend API
   - Displays the inference results

## Troubleshooting

- If the camera feed doesn't appear, check that the camera is properly connected and that the gstreamer pipeline is configured correctly
- If inference fails, check that the Ollama server is running and accessible from the Jetson Nano
- Make sure the Ollama model you're using supports image input

## License

This project is licensed under the MIT License - see the LICENSE file for details.




## proompts
**Task:** Convert the table data from the image into well-structured JSON format using the following guidelines:

1. **Data Analysis:**
   - Carefully analyze the table structure and relationships between columns
   - Identify column headers from:
     * Explicit labels in the table
     * Consistent data patterns
     * Contextual relationships between columns
   - For ambiguous columns, create descriptive keys using: 
     ```python
     key_name = " ".join([data_pattern, data_type, unit]).strip().lower().replace(" ", "_")
     ```

2. **Data Normalization:**
   - Convert number-like strings to appropriate numeric types
   - Preserve text exactly as shown for non-numeric data
   - Handle merged cells by repeating values or using null where appropriate
   - Maintain original data order

3. **Output Requirements:**
   ```json
   {
     "table_data": [
       {
         "inferred_column_1": "value",
         "explicit_column_2": 123,
         "derived_header_3": "data"
       }
     ],
     "conversion_notes": {
       "assumptions_made": ["list of key inferences"],
       "data_warnings": ["potential inconsistencies"]
     }
   }
   ```

4. **Error Handling:**
   - Flag and document any irregularities in `conversion_notes`
   - Maintain original data integrity when uncertainties exist
   - Use null values for empty cells

**Example Conversion:**
Input Table:
```
|   | Item          | QTY | Per 100g |
|---|---------------|-----|----------|
| 1 | Apples        | 12  | $0.75    |
| 2 | Organic Flour | 5   | $1.20    |
```

Output JSON:
```json
{
  "table_data": [
    {
      "row_id": 1,
      "item_name": "Apples",
      "quantity": 12,
      "price_per_100g": 0.75
    },
    {
      "row_id": 2,
      "item_name": "Organic Flour",
      "quantity": 5,
      "price_per_100g": 1.20
    }
  ],
  "conversion_notes": {
    "assumptions_made": [
      "Inferred 'row_id' from row numbers",
      "Standardized currency formatting"
    ],
    "data_warnings": []
  }
}
```

**Special Instructions:**
- Prioritize data fidelity over formatting
- Document all non-explicit decisions in conversion_notes
- Use JSON-compatible data types
- Maintain original row order and grouping