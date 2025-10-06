# F1 Superfan - Project Requirements

## 1. Overview

The F1 Superfan project is an application designed to run on an NVIDIA Jetson Nano. It uses a CSI camera to capture periodic snapshots of a Formula 1 broadcast. These images are then processed by a multimodal Large Language Model (LLM) to extract structured data from on-screen graphics, such as timing tables and tire information. The extracted data is stored in a database for real-time viewing and post-race analysis.

## 2. Core Components

- **Image Processor**: A service responsible for capturing images from the camera at configured intervals or via manual triggers.
- **Inference Worker**: A background service that monitors a directory for new images, runs them through the LLM for data extraction, validates the output, and prepares it for storage.
- **Database Handler**: An abstraction layer that manages storing the extracted data into either a PostgreSQL database or a local SQLite file.
- **Web Server**: A Flask-based web application that provides a user interface for live video preview, manual capture, and viewing extracted data.

## 3. Functional Requirements

### FR-1: Image Capture
- The system shall be configurable to capture images automatically at a periodic interval (default: 10 seconds).
- The system shall support manual image capture triggered from the web interface.
- The capture mode (periodic, manual, or both) shall be configurable.
- All newly captured raw images shall be saved to a designated `input` directory.

### FR-2: Data Extraction
- The Inference Worker shall continuously monitor the `input` directory for new images.
- The system shall use specialized, configurable prompts for each type of data to be extracted.
- The initial data extraction priority is:
    1. Current Lap number
    2. Timing Table (position, driver, gap, interval per driver)
    3. Tire age and compound
- The output from the LLM shall be parsed as JSON.

### FR-3: Data Validation
- After extraction, the system shall perform a sanity check on the generated data (e.g., is it valid JSON?).
- If validation fails, the corresponding image shall be moved to a `failed` directory.
- An error log (in JSON format) containing the image filename and the reason for failure (e.g., `JSON_VALIDATION_FAILED`, `LLM_UNAVAILABLE`) shall be created.

### FR-4: LLM Configuration
- The LLM model used for inference shall be configurable (default: `granite3.2-vision:2b`).
- The Ollama host endpoint (local or remote) shall be configurable.

### FR-5: Data Storage
- Validated JSON data shall be persisted to a database.
- The system shall use a PostgreSQL database if connection details are provided in the configuration.
- If PostgreSQL is not configured, the system shall automatically fall back to using a local SQLite database file.
- All extracted data will be stored to allow for historical analysis.

### FR-6: Image File Management
- After an image is successfully processed and its data is stored, the image file shall be moved from the `input` directory to a `processed` directory.

### FR-7: Web Interface
- A live video preview from the camera shall be displayed.
- A "Manual Capture" button shall be provided to trigger image capture on demand.
- A section of the UI shall display the most recently extracted data in real-time.
- No user authentication or password protection is required.

## 4. Non-Functional Requirements

### NFR-1: Configuration
- All primary application settings shall be managed through a single `config.yaml` file.
- Configurable parameters shall include:
    - Camera settings (resolution, FPS)
    - Capture settings (mode, interval)
    - LLM settings (host, model, prompts per data type)
    - Storage paths for input, processed, and failed images
    - Database settings (type, connection details)
    - Logging level

### NFR-2: Error Handling
- The system shall gracefully handle common failure modes, including camera disconnection, LLM timeouts, and database connection errors.
- All significant events and errors shall be logged with appropriate detail.


### PROJECT STRUCTURE
# F1 Superfan - Project Structure

This structure separates concerns into distinct modules, making the application easier to manage, test, and scale.

```
f1-superfan/
├── config/
│   └── config.yaml             # Main application configuration
├── data/
│   ├── input/                  # Directory for newly captured images
│   ├── processed/              # Directory for successfully processed images
│   ├── failed/                 # Directory for images that failed processing
│   └── f1_data.db              # SQLite database fallback
├── src/
│   ├── __init__.py
│   ├── server.py               # Flask web server for UI and API
│   ├── image_processor.py      # GStreamer camera capture & frame management
│   ├── inference_worker.py     # Monitors 'input' dir, runs LLM, saves data
│   ├── database_handler.py     # Handles SQLite/Postgres data storage
│   ├── config_loader.py        # Loads and validates config.yaml
│   └── utils.py                # Shared utility functions (e.g., data validation)
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── templates/
│   └── index.html              # Main web UI
├── main.py                     # Main entry point to start all services
├── requirements.txt            # Python dependencies
└── REQUIREMENTS.md             # Detailed project requirements
```


### config.yaml.example

This example YAML file demonstrates how the application will be configured, incorporating all the options you requested.

```yaml config.yaml.example
# F1 Superfan - Example Configuration

camera:
  resolution: "1280x720"
  fps: 30

capture:
  # Capture mode can be 'periodic', 'manual', or 'both'
  mode: "both"
  interval_seconds: 10
  storage_paths:
    input: "data/input"
    processed: "data/processed"
    failed: "data/failed"

llm:
  ollama_host: "http://localhost:11434"
  model: "granite3.2-vision:2b"
  prompts:
    current_lap: "What is the current lap number shown in the image? Respond with JSON `{\"lap_number\": X}`."
    timing_table: "Extract the full timing table from the image. For each driver, provide position, name, gap, and interval. Provide the response in a JSON object with a key 'timing_table' containing a list of drivers."
    tire_info: "Extract the tire compound and age for each driver visible in the image. Respond with a JSON object containing a list of drivers with their tire info."

database:
  # Database type can be 'postgres' or 'sqlite'
  type: "sqlite"

  # For 'sqlite', only the path is needed
  path: "data/f1_data.db"

  # For 'postgres', fill out the connection details below
  # host: "localhost"
  # port: 5432
  # user: "f1_user"
  # password: "your_password"
  # dbname: "f1_superfan"

logging:
  # Logging level can be DEBUG, INFO, WARNING, ERROR
  level: "INFO"
```
