# Magic: The Gathering Card Sorter & Cataloger

## Description
This project aims to catalog and sort Magic: The Gathering (MTG) cards using image recognition. It is designed to run on a Raspberry Pi connected to a physical sorting machine. The project is currently in development.

## Current Features
*   Image-based card identification.
*   OCR (Tesseract) to extract card names from images.
*   Fuzzy name correction using SymSpell against a comprehensive MTG card dictionary.
*   Fetching card details (price, color identity) from the Scryfall API.
*   Processing a directory of card images and outputting data to a CSV file.

## Project Structure
*   `main.py`: Intended main entry point for the application (currently under development).
*   `recognition/`: Contains the core card recognition logic.
    *   `ocr_mvp.py`: Main script for current image processing workflow.
    *   `fuzzy_match.py`: Implements the card name correction.
    *   `cards/`: Stores the dictionary files for SymSpell.
*   `tools/`: Scripts for building and maintaining the card dictionary.
    *   `build_symspell_dictionary.py`: Fetches card names from Scryfall and creates an initial dictionary.
    *   `symspell_dict_bereinigung.py`: Cleans the dictionary file.
*   `tests/`: (Will contain) Unit tests for the project.
*   `requirements.txt`: Python dependencies.
*   `README.md`: This file.

## Setup Instructions
### Python
Python 3.x required.

### Tesseract OCR
*   Tesseract OCR must be installed.
*   Installation instructions can be found at: [https://tesseract-ocr.github.io/tessdoc/Installation.html](https://tesseract-ocr.github.io/tessdoc/Installation.html)
*   The path to `tesseract.exe` (on Windows) or the Tesseract command might need to be configured in `recognition/ocr_mvp.py`.

### Python Dependencies
*   Install dependencies using pip:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: `requirements.txt` will be updated in a subsequent step).

### Card Dictionary
The card dictionary is essential for the fuzzy name correction. To generate it:
1.  Run `python tools/build_symspell_dictionary.py`. This script fetches card names from Scryfall and creates the initial dictionary at `recognition/cards/card_names_symspell.txt`.
2.  Run `python tools/symspell_dict_bereinigung.py`. This script cleans the dictionary created in the previous step and saves it as `recognition/cards/card_names_symspell_clean.txt`.

(Note: The paths in `ocr_mvp.py` and `fuzzy_match.py` are relative to their own location (e.g., `cards/`). If you run the scripts in `tools/` from the project root directory, ensure the output paths within those scripts correctly point to `recognition/cards/` or adjust the scripts accordingly.)

## Running the Image Processing
*   The current main processing script is `recognition/ocr_mvp.py`.
*   Execute it using:
    ```bash
    python recognition/ocr_mvp.py
    ```
*   Images for processing should be placed in the `tests/test_images` directory, as this path is currently hardcoded in `ocr_mvp.py`.
*   The output, a CSV file containing card data, will be saved to `tests/test_carddata.csv`.

## Future Goals
*   Integration with a Raspberry Pi and a physical card sorting machine.
*   Development of `main.py` as the primary application interface.
*   Improved error handling and configuration options.

## Web Interface Setup and Usage

The project now includes a web interface to interact with the card scanner.

### Prerequisites

Ensure all dependencies are installed by running:
```bash
pip install -r requirements.txt
```
This includes Flask for the web server. Ensure Tesseract OCR and libcamera-still (on Raspberry Pi) are also installed and configured as per the main setup instructions.

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
