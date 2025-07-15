# Magic: The Gathering Card Sorter & Cataloger

## 1. Description
This project aims to catalog and sort Magic: The Gathering (MTG) cards using image recognition. It is primarily designed with the Raspberry Pi in mind, envisioning future integration with a physical card sorting machine. The application allows users to scan cards, identify them using OCR and advanced name correction, fetch detailed information from online databases, and manage their collection through both a command-line interface and a user-friendly web application. The project is currently in active development.

## 2. Features

*   **Card Identification:**
    *   **Image Capture:** Supports image input from files or direct capture using `libcamera-still` on compatible systems (e.g., Raspberry Pi).
    *   **OCR Technology:** Utilizes Tesseract OCR to extract text from card images, focusing on the card name area.
    *   **Fuzzy Name Correction:** Implements SymSpell for robust fuzzy matching, correcting common OCR errors against a comprehensive MTG card name dictionary.
    *   **Interactive Crop Configuration:** A tool to visually define the card name area on an image, optimizing recognition accuracy. Accessible via CLI and Web UI.
*   **Data Enrichment (Scryfall API):**
    *   Automatically fetches detailed card information for recognized cards, including current market price (EUR/USD), color identity, Converted Mana Cost (CMC), full type line, and card image URI from the Scryfall API.
*   **Database Storage (SQLite):**
    *   Stores cataloged card details in a local SQLite database (`web_app/magic_cards.db`).
    *   Key data points include: ID, recognized name, raw OCR text, price, color identity, image path (local), timestamp, CMC, type line, and Scryfall image URI.
*   **Hardware Integration:**
    *   **GPIO Control:** Complete hardware control system for physical card sorting machine using Raspberry Pi GPIO pins.
    *   **Motor Control:** Controls conveyor belt motor for card transport.
    *   **Sensor Integration:** Light barrier sensor for detecting card presence and timing.
    *   **Sorting Mechanisms:** Dual sorting flaps and main sorting mechanism for directing cards to different output bins.
    *   **Development Mode:** Mock GPIO interface for development and testing on non-Raspberry Pi systems.
*   **Command-Line Interface (`main.py`):**
    *   Process card images in batches from a specified directory.
    *   Capture and process images directly from a connected camera.
    *   Initialize or re-initialize the card database.
    *   Access the interactive crop area configuration tool.
*   **Web Application (`web_app/app.py`):**
    *   **Real-time Card Scanning:** Scan cards using a connected camera, with results appearing dynamically in the collection.
    *   **Comprehensive Card List:** View all cataloged cards with their details.
    *   **Advanced Filtering:** Filter the card list by color identity (e.g., W, UB, RUG), Converted Mana Cost (CMC), and maximum price.
    *   **CSV Export:** Download the entire card database as a CSV file.
    *   **Card Deletion:** Easily remove cards from the database via the web interface.
    *   **Web-Triggered Crop Configuration:** Initiate the crop area setup process from the web UI (interaction occurs in the server console).
    *   **EDHREC Deck Suggestions:** Recommends a Commander and a list of owned cards for a potential deck, based on your collected legendary creatures and suggestions from EDHREC.
    *   **Custom Sorting Rules:** Configure automatic sorting rules based on card attributes (CMC, price, color identity, type line, name). Rules can use various operators (>, >=, <, <=, =, !=, contains, starts_with, ends_with) to determine which pile cards should be sorted into.
*   **Dictionary Management:**
    *   Includes tools to build an initial card name dictionary by fetching data from Scryfall.
    *   Provides scripts to clean and process this dictionary for optimal use with SymSpell.

## 3. Project Structure

*   `main.py`: Command-Line Interface (CLI) entry point.
*   `gpio_control.py`: Hardware control module for physical card sorting machine, including motor control, sensor integration, and sorting mechanisms.
*   `test_crop_setup.py`: Testing utility for verifying crop configuration functionality.
*   `web_app/`: Contains the Flask web application.
    *   `app.py`: Main Flask application file, defines routes and web functionalities.
    *   `database.py`: Handles all SQLite database interactions (initialization, CRUD operations).
    *   `magic_cards.db`: Default SQLite database file created in this directory.
    *   `static/`: Contains static assets like CSS (`style.css`) and JavaScript (`script.js`).
    *   `templates/`: HTML templates for the web interface (`index.html`, `suggestions.html`).
*   `recognition/`: Core image recognition and card processing logic.
    *   `ocr_mvp.py`: Handles image capture, OCR, cropping, Scryfall API interaction, and saving card data.
    *   `fuzzy_match.py`: Implements the `CardNameCorrector` class using SymSpell for name correction.
    *   `cards/`: Stores dictionary files for SymSpell (e.g., `card_names_symspell_clean.txt`).
*   `tools/`: Utility scripts.
    *   `build_symspell_dictionary.py`: Fetches card names from Scryfall to create the initial dictionary.
    *   `symspell_dict_bereinigung.py`: Cleans and processes the dictionary file.
*   `tests/`: Contains unit tests and test resources.
    *   `test_images/`: Sample images for testing.
    *   Python test files (e.g., `test_ocr_mvp.py`, `test_web_app.py`, `test_camera_integration.py`).
*   `requirements.txt`: Lists Python dependencies for the project.
*   `README.md`: This file.

## 4. Prerequisites

*   **Operating System:** Developed on Linux (Raspberry Pi OS). Should be compatible with other OSs where Python and Tesseract can be installed, but camera functionality is Linux-focused.
*   **Python:** Python 3.x (developed with 3.9+).
*   **Tesseract OCR:**
    *   Must be installed and accessible in your system's PATH.
    *   Installation instructions: [Tesseract OCR Documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html)
    *   Ensure the `tesseract` command is available. `pytesseract` (used by this project) relies on it.
*   **`libcamera-utils` (for Raspberry Pi Camera Users):**
    *   If using the camera feature on a Raspberry Pi with a libcamera-based camera module, `libcamera-utils` (which includes `libcamera-still`) must be installed.
    *   Typically installed via: `sudo apt update && sudo apt install libcamera-utils`
*   **RPi.GPIO (for Hardware Control):**
    *   Required for GPIO control on Raspberry Pi systems.
    *   Automatically installed via `requirements.txt` on Raspberry Pi.
    *   Mock interface available for development on non-Raspberry Pi systems.

## 5. Installation

1.  **Clone the Repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Set up a Python Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Verify Tesseract OCR Installation:**
    Ensure Tesseract is installed and correctly configured as per the Prerequisites section.
5.  **Set Up the Card Name Dictionary:**
    The dictionary is crucial for accurate card name correction. Generate it by running the following scripts from the project's root directory:
    *   **Step 1: Build initial dictionary from Scryfall:**
        ```bash
        python tools/build_symspell_dictionary.py
        ```
        This creates `recognition/cards/card_names_symspell.txt`.
    *   **Step 2: Clean and process the dictionary:**
        ```bash
        python tools/symspell_dict_bereinigung.py
        ```
        This creates the final `recognition/cards/card_names_symspell_clean.txt`, which is used by the application.
    *   **Verification:** Ensure `recognition/cards/card_names_symspell_clean.txt` has been successfully created.

## 6. Configuration

*   **Crop Area Configuration:**
    *   **Purpose:** To optimize card name recognition accuracy by precisely defining the area where the card's name is located on the image. This is highly recommended, especially if recognition results are poor.
    *   **How to Run:**
        *   **CLI:** Execute `python main.py --configure_crop` from the project root. An image will be captured (or a dummy image used), and a Matplotlib window will appear. Select the name area and close the window.
        *   **Web Application:** Click the "Configure Crop Area" button on the main page. This triggers the same interactive process, which will occur in the console/terminal where the `web_app/app.py` server is running.
    *   **How it Works:** The selection updates internal ratio constants within `recognition/ocr_mvp.py`, which are then used for all subsequent image cropping. These settings persist as long as the application is running or until reconfigured.
*   **Tesseract Path (Optional Manual Override):**
    *   If Tesseract is installed but not in your system's PATH, you can manually set the path to the Tesseract executable within `recognition/ocr_mvp.py`. Look for the `pytesseract.pytesseract.tesseract_cmd` line. This is primarily relevant for Windows users who install Tesseract to a custom location.
*   **Dictionary Path (CLI Only):**
    *   The `main.py` script accepts a `-d` or `--dict_path` argument to specify a custom location for the SymSpell dictionary file. The web application uses a default path (`recognition/cards/card_names_symspell_clean.txt`).

## 7. Usage

### A. Command-Line Interface (`main.py`)

The CLI is suitable for batch processing images or quick tests with a camera.

*   **Basic Execution:**
    Navigate to the project root directory and run:
    ```bash
    python main.py [OPTIONS]
    ```

*   **Key Command-Line Arguments:**
    *   `-i, --image_dir PATH`: Specifies the directory containing card images to process.
        *   Default: `tests/test_images` (relative to project root).
    *   `-d, --dict_path PATH`: Sets the path to the SymSpell dictionary file.
        *   Default: `recognition/cards/card_names_symspell_clean.txt` (relative to project root).
    *   `-ng, --no_gui`: Disables the Tkinter-based GUI image preview when processing images from a directory.
    *   `-uc, --use_camera`: Use a connected camera for image input instead of processing a directory. If this flag is present, `--image_dir` is ignored.
    *   `--init_db`: Initializes or re-initializes the database (`web_app/magic_cards.db`) before any processing. Useful for a fresh start.
    *   `--configure_crop`: Starts the interactive tool to configure the card image cropping area.

*   **Examples:**
    *   Process images from the default directory:
        ```bash
        python main.py
        ```
    *   Process images from a custom directory:
        ```bash
        python main.py --image_dir path/to/your/images
        ```
    *   Use camera input (ensure camera is configured and `libcamera-still` is available if on RPi):
        ```bash
        python main.py --use_camera
        ```
    *   Initialize the database and then process images:
        ```bash
        python main.py --init_db --image_dir path/to/your/images
        ```
    *   Configure cropping settings:
        ```bash
        python main.py --configure_crop
        ```

### B. Web Application (`web_app/app.py`)

The web application provides a richer, interactive experience for managing your card collection.

*   **Running the Web Server:**
    1.  Navigate to the project's root directory.
    2.  Start the Flask web server:
        ```bash
        python web_app/app.py
        ```
    3.  The server will typically start on `0.0.0.0:5000`, making it accessible from other devices on the same network.

*   **Accessing the Web Interface:**
    1.  Open a web browser on a device connected to the same network as the machine running the server.
    2.  Navigate to `http://<SERVER_IP_ADDRESS>:5000`. Replace `<SERVER_IP_ADDRESS>` with the actual IP address of your server (e.g., your Raspberry Pi's IP). If running locally for testing, use `http://127.0.0.1:5000` or `http://localhost:5000`.

*   **Features and How to Use:**
    *   **Main Page (`/`):**
        *   Displays the list of currently cataloged cards.
        *   Provides a "Scan Card" button.
        *   Shows filter options (Color, Mana Cost, Max Price).
        *   Links/buttons for "Download CSV", "Configure Crop Area", and "Deck Suggestions".
    *   **Scan Card:**
        *   Click the "Scan Card" button. This triggers the connected camera to capture an image.
        *   The system processes the image, identifies the card, fetches its data, and adds it to the database. The card list updates automatically.
    *   **Card List & Filters:**
        *   The main page displays cards from the database.
        *   **Color:** Enter color letters (W, U, B, R, G, or combinations like WU, BRG) to filter by color identity.
        *   **Mana Cost (CMC):** Enter a number to filter by Converted Mana Cost.
        *   **Max Price:** Enter a number to filter cards up to that maximum price.
        *   Click "Apply Filters" to update the list. Click "Clear Filters" to reset.
    *   **Download CSV (`/export/csv`):**
        *   Click the "Download CSV" button to export all card data currently in the database to a `scanned_cards.csv` file.
    *   **Delete Card:**
        *   Each card in the list has a "Delete" button. Clicking it will remove the card from the database.
    *   **Configure Crop Area:**
        *   Click the "Configure Crop Area" button. This initiates the interactive crop setup process in the server's console window (similar to the CLI version).
    *   **Deck Suggestions (`/deck_suggestions`):**
        *   Click the "Deck Suggestions" button/link.
        *   The system identifies legendary creatures in your collection.
        *   It then queries EDHREC for popular cards associated with those commanders.
        *   It determines which commander has the most matching cards already in your collection and displays the commander, the list of owned suggested cards, and the match count.
    *   **Custom Sorting Rules:**
        *   **Adding Rules:** Use the "Custom Sorting Rules" section to create automatic sorting rules. Each rule consists of:
            *   **Rule Name:** A descriptive name for the rule (e.g., "High CMC Cards")
            *   **Attribute:** The card property to check (CMC, Price, Color Identity, Type Line, or Card Name)
            *   **Operator:** Comparison operator (>, >=, <, <=, =, !=, contains, starts_with, ends_with)
            *   **Value:** The value to compare against
            *   **Sort Direction:** Which pile the card should go to (Left or Right)
        *   **Rule Examples:**
            *   CMC > 3 → Left Pile (high mana cost cards)
            *   Price >= 20.0 → Right Pile (expensive cards)
            *   Color Identity contains "U" → Left Pile (blue cards)
            *   Type Line contains "Creature" → Right Pile (creatures)
        *   **Rule Evaluation:** When a card is scanned, the system evaluates all active rules in order. The first matching rule determines the sort direction. If no rules match, recognized cards go right and unrecognized cards go left.
        *   **Managing Rules:** View all active rules in the "Active Rules" section. Delete rules by clicking the "Delete" button next to each rule.

## 8. Database

*   **Storage:** Card data is stored in an SQLite database.
*   **Default File Location:** `web_app/magic_cards.db` (created automatically in the `web_app` directory if it doesn't exist upon app startup or DB initialization).
*   **Content:** Stores details for each cataloged card, including name, OCR data, price, color identity, image URI, etc.
*   **Export:** The entire database can be exported to a CSV file via the web interface.

## 9. Hardware Integration

The project includes a complete hardware control system for physical card sorting machines using Raspberry Pi GPIO pins.

*   **GPIO Pin Configuration:**
    *   **Motor Control (Pin 23):** Controls the conveyor belt motor for card transport.
    *   **Light Barrier Sensor (Pin 24):** Detects card presence and timing for sorting operations.
    *   **Left Sorting Flap (Pins 14 & 15):** Dual-pin control for left sorting mechanism (pins must maintain same state).
    *   **Main Sorting Mechanism (Pin 18):** Controls the main sorting mechanism for right sorting or delayed left sorting.
*   **Sorting Operations:**
    *   **Right Sorting:** Activates motor, waits for card detection, triggers main sorting mechanism, then activates left flap for timing control.
    *   **Left Sorting:** Similar sequence but with different timing and mechanism activation.
    *   **Custom Sorting:** Automatically determines sort direction based on configured rules. If no rules are set, recognized cards go right and unrecognized cards go left.
    *   **Development Mode:** Mock GPIO interface allows development and testing on non-Raspberry Pi systems.
*   **Hardware Requirements:**
    *   Raspberry Pi with GPIO access
    *   Relay modules for motor and sorting mechanism control
    *   Light barrier sensor for card detection
    *   Conveyor belt system
    *   Sorting flaps and mechanisms
*   **Safety Features:**
    *   Automatic GPIO cleanup on program termination
    *   Mock interface prevents hardware damage during development
    *   Proper initialization and state management for all GPIO pins

## 10. Tools

The `tools/` directory contains scripts essential for the application's accuracy:

*   `tools/build_symspell_dictionary.py`:
    *   This script fetches a list of all MTG card names from the Scryfall API.
    *   It creates an initial, raw dictionary file (`recognition/cards/card_names_symspell.txt`).
*   `tools/symspell_dict_bereinigung.py`:
    *   This script processes the raw dictionary generated by `build_symspell_dictionary.py`.
    *   It cleans the names (e.g., removing special characters or formatting unsuitable for SymSpell) and prepares the final dictionary (`recognition/cards/card_names_symspell_clean.txt`).
*   **Importance:** Running these tools in sequence is crucial for the `CardNameCorrector` to function effectively and provide accurate fuzzy matching for OCR'd card names.

## 11. Testing

*   The `tests/` directory contains various Python scripts for unit and integration testing.
    *   Examples include `test_ocr_mvp.py`, `test_fuzzy_match.py`, `test_web_app.py`, and `test_camera_integration.py`.
*   `tests/test_images/` provides a small set of sample card images that can be used with `main.py` (it's the default image directory).
*   To run tests, you would typically use a test runner like `pytest` (not explicitly configured in the project yet, but tests are structured to be compatible). For now, some tests might be runnable directly or via their `if __name__ == "__main__":` blocks.

## 12. Troubleshooting

*   **"libcamera-still not found" or Camera Issues (Raspberry Pi):**
    *   Ensure `libcamera-utils` is installed: `sudo apt install libcamera-utils`.
    *   Verify the camera is properly connected and configured in `raspi-config`.
    *   The web application will show a warning if `libcamera-still` is not detected at startup, and the "Scan Card" feature will likely fail.
*   **"Dictionary file not found" (e.g., `recognition/cards/card_names_symspell_clean.txt`):**
    *   You must run the dictionary generation scripts as described in the "Installation" section (step 5).
    *   The web application might create a placeholder dummy dictionary on startup if the file is missing, but card name correction will not work correctly.
*   **Tesseract OCR Not Found or Not Working:**
    *   Confirm Tesseract OCR is installed correctly on your system.
    *   Ensure the `tesseract` command is in your system's PATH.
    *   For Windows, if installed to a non-default location, you might need to set `pytesseract.pytesseract.tesseract_cmd` in `recognition/ocr_mvp.py`.
*   **Low Card Name Recognition Accuracy:**
    *   **Use the Crop Configuration Tool:** This is the most important step. Access it via `python main.py --configure_crop` or the "Configure Crop Area" button in the web app. Accurately selecting the name region significantly improves OCR.
    *   **Lighting and Focus:** Ensure good, even lighting on the card and that the camera is focused correctly. Shadows and glare can severely impact OCR.
    *   **Card Condition:** Very worn or damaged cards might be harder to recognize.
*   **Web App Issues (e.g., 404 errors, features not working):**
    *   Ensure the Flask server (`python web_app/app.py`) is running without errors in the console.
    *   Check for any error messages in the server console output.
    *   Verify all dependencies in `requirements.txt` are installed in your active Python environment.
*   **Hardware/GPIO Issues:**
    *   **Mock GPIO Mode:** If you see "MockGPIO: Initialized" messages, the system is running in development mode without actual hardware.
    *   **RPi.GPIO Import Errors:** Ensure RPi.GPIO is installed (`pip install RPi.GPIO`) on Raspberry Pi systems.
    *   **GPIO Permission Issues:** On Raspberry Pi, ensure your user has GPIO access or run with appropriate permissions.
    *   **Hardware Not Responding:** Check physical connections, relay module power, and GPIO pin assignments in `gpio_control.py`.

## 13. Future Goals / Roadmap

*   **Hardware Integration:** ✅ **COMPLETED** - Full integration with Raspberry Pi and physical card sorting machine, including GPIO control components.
*   **Enhanced Testing:** Comprehensive unit and integration testing suite with automated runs.
*   **System Improvements:** Ongoing improvements to error handling, logging capabilities, and overall configuration flexibility.
*   **Data Model Enhancement:** Enhanced card data model (e.g., storing MTG set information, foil status, card language).
*   **UI/UX Improvements:** Enhanced user interface and experience for the web application.
*   **Performance Optimization:** Optimize OCR accuracy and processing speed for real-time card sorting.
*   **Advanced Sorting Logic:** Implement more sophisticated sorting algorithms based on card value, rarity, or user-defined criteria.
