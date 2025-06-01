# Magic: The Gathering Card Sorter & Cataloger

## Description
This project aims to catalog and sort Magic: The Gathering (MTG) cards using image recognition. It is designed to run on a Raspberry Pi connected to a physical sorting machine. The project is currently in development.

## Current Features
*   `main.py` serves as the main Command Line Interface (CLI) entry point for the application.
*   Image-based card identification using OCR (Tesseract) to extract card names and fuzzy name correction (SymSpell).
*   Fetching card details (e.g., price, color identity) from the Scryfall API.
*   Primary data storage via a database, with CSV export functionality available through the web application.
*   Web interface for enhanced user interaction, including:
    *   Card scanning via connected camera.
    *   List view of all cataloged cards.
    *   Filtering capabilities (e.g., by color, mana cost).
    *   CSV export of the card database.

## Project Structure
*   `main.py`: CLI entry point for batch processing of images and direct camera input.
*   `web_app/app.py`: Entry point for the Flask web application, providing an interactive user interface for card scanning, viewing, and database management.
*   `recognition/`: Contains the card recognition logic.
    *   `ocr_mvp.py`: Core module for image processing (OCR, fuzzy matching), utilized by both `main.py` and the web app.
    *   `fuzzy_match.py`: Implements the card name correction using SymSpell.
    *   `cards/`: Stores dictionary files for SymSpell.
*   `tools/`: Contains scripts for building and maintaining the card dictionary.
    *   `build_symspell_dictionary.py`: Fetches card names from Scryfall to create the initial SymSpell dictionary.
    *   `symspell_dict_bereinigung.py`: Cleans and processes the dictionary file.
*   `tests/`: Directory for unit tests (currently under development).
*   `requirements.txt`: Lists Python dependencies for the project.
*   `README.md`: This file.

## Setup Instructions
### Python
Python 3.x required.

### Tesseract OCR
*   Tesseract OCR must be installed and accessible in your system's PATH for the OCR functionality to work.
*   Installation instructions can be found at: [https://tesseract-ocr.github.io/tessdoc/Installation.html](https://tesseract-ocr.github.io/tessdoc/Installation.html)
*   Ensure that the Tesseract command (`tesseract`) is available system-wide. `pytesseract` (used by the application) typically relies on this.

### Python Dependencies
*   Install dependencies using pip:
    ```bash
    pip install -r requirements.txt
    ```

### Card Dictionary
The card dictionary is essential for accurate fuzzy name correction. To generate or update it:
1.  Ensure you are in the project's root directory.
2.  Run `python tools/build_symspell_dictionary.py`. This script fetches card names from Scryfall and creates the initial dictionary at `recognition/cards/card_names_symspell.txt`.
3.  Run `python tools/symspell_dict_bereinigung.py`. This script cleans the dictionary from the previous step and saves the processed version to `recognition/cards/card_names_symspell_clean.txt`.

(Note: The application (`main.py` and `web_app/app.py`) expects the dictionary files to be located in `recognition/cards/`. The tool scripts are configured to place the generated files there when executed from the project root directory. The paths within `recognition/ocr_mvp.py` and `recognition/fuzzy_match.py` for accessing these dictionary files are relative to their own script locations.)

## Command-Line Usage (main.py)
The primary command-line interface for the application is `main.py`. It allows for batch processing of images from a directory or direct input from a camera.

### Basic Execution
To run the CLI application, navigate to the project root directory and use:
```bash
python main.py [OPTIONS]
```

### Key Command-Line Arguments
*   `-i, --image_dir PATH`: Specifies the directory containing card images to process.
    *   Default: `tests/test_images` (relative to the project root).
*   `-d, --dict_path PATH`: Sets the path to the SymSpell dictionary file.
    *   Default: `recognition/cards/card_names_symspell_clean.txt` (relative to the project root).
*   `-uc, --use_camera`: Use a connected camera for image input instead of processing a directory. If this flag is present, `--image_dir` is ignored.
*   `-ng, --no_gui`: Disables the GUI image preview when processing images from a directory.
*   `--init_db`: Initializes or re-initializes the database before any processing. This is useful for a fresh start or schema updates.
*   `--configure_crop`: Starts an interactive tool to configure the card image cropping area. This helps optimize recognition accuracy.

### Examples
*   Process images from the default directory:
    ```bash
    python main.py
    ```
*   Process images from a custom directory:
    ```bash
    python main.py --image_dir path/to/your/images
    ```
*   Use camera input:
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

The application primarily stores data in a database. CSV export is available via the web interface.

## Future Goals
*   Full integration with a Raspberry Pi and a physical card sorting machine, including hardware control.
*   Comprehensive unit and integration testing to ensure robustness.
*   Ongoing improvements to error handling, logging, and configuration flexibility.
*   Enhanced card data model (e.g., storing set information, foil status, etc.).

## Web Interface Setup and Usage

The project now includes a web interface to interact with the card scanner.

### Prerequisites

1.  **Python Dependencies**: Install all required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    This includes Flask (for the web server) and other necessary libraries.
2.  **Tesseract OCR**: Tesseract OCR must be installed and accessible in your system's PATH. It is used by the backend for card name recognition. Refer to the "Tesseract OCR" subsection under "Setup Instructions" for more details.
3.  **Card Dictionary**: A valid SymSpell dictionary file (e.g., `recognition/cards/card_names_symspell_clean.txt`) must be present. This file is crucial for correcting OCR'd card names. Refer to the "Card Dictionary" subsection under "Setup Instructions" for generation steps.
4.  **Camera (Optional for Scanning)**: For the "Scan Card" feature to work with a physical camera (especially on Raspberry Pi), `libcamera-still` should be installed and functional. The server will warn if it's not detected.

### Running the Web Server

1.  Navigate to the project's root directory.
2.  Start the Flask web server:
    ```bash
    python web_app/app.py
    ```
3.  The server will typically start on `0.0.0.0:5000`, meaning it's accessible from other devices on the same network.

### Accessing the Web Interface

1.  Open a web browser on a device connected to the same network as your Raspberry Pi (or the machine running the server).
2.  Navigate to `http://<YOUR_RASPBERRY_PI_IP_ADDRESS>:5000`. Replace `<YOUR_RASPBERRY_PI_IP_ADDRESS>` with the actual IP address of your Raspberry Pi. If running on a local machine for testing, you can use `http://127.0.0.1:5000` or `http://localhost:5000`.

### Using the Interface

*   **Scan Card**: Click the "Scan Card" button to trigger the camera (if connected and configured) to capture an image. The system will attempt to OCR the card, identify it, and save its details. The card list will update automatically.
*   **Card List**: Displays all cards currently stored in the database.
*   **Filters**:
    *   **Color**: Enter a color letter (e.g., W, U, B, R, G) or combination (e.g., WU, BR) to filter cards by their color identity.
    *   **Mana Cost (CMC)**: Enter a number to filter by Converted Mana Cost. (Note: This filter's effectiveness depends on whether CMC data is available and accurately stored for scanned cards).
    *   Click "Apply Filters" to refresh the card list based on your criteria.
    *   Click "Clear Filters" to remove all filter criteria and show all cards.
*   **Download CSV**: Click the "Download CSV" button to export all card data currently in the database as a CSV file.
