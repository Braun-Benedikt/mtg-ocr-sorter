import os
import sys # Crucial import
from flask import Flask, jsonify, request, send_file, render_template
from werkzeug.utils import secure_filename
import io
import csv
from pathlib import Path # Crucial import
import subprocess # For libcamera-still check in if __name__ == '__main__'
import requests # For fetching EDHREC data
import re # For formatting commander names

# --- sys.path modification ---
# This logic assumes app.py is located inside the 'web_app' directory.
# Correctly identify project root:
# app_file_path will be /path/to/project_root/web_app/app.py
# web_app_folder will be /path/to/project_root/web_app
# project_root_folder will be /path/to/project_root
app_file_path = Path(__file__).resolve()
web_app_folder = app_file_path.parent
project_root_folder = web_app_folder.parent

# Add project_root_folder to sys.path if it's not already there.
# This allows imports like 'from recognition.ocr_mvp import ...'
if str(project_root_folder) not in sys.path:
    sys.path.insert(0, str(project_root_folder))
# --- End sys.path modification ---

# Now, project-specific imports
try:
    from web_app.database import init_db, add_card, get_cards, delete_card, get_legendary_creatures
except ModuleNotFoundError as e:
    print(f"ERROR: Could not import database module from web_app.database: {e}")
    print(f"Project root: {project_root_folder}, sys.path: {sys.path}")
    # Define dummy functions if import fails, so the script can still be imported
    def init_db(): print("DUMMY init_db: web_app.database not found")
    def add_card(name, **kwargs): print(f"DUMMY add_card: {name}"); return None
    def get_cards(**kwargs): print("DUMMY get_cards"); return []
    def delete_card(card_id): print(f"DUMMY delete_card: {card_id}"); return False
    def get_legendary_creatures(): print("DUMMY get_legendary_creatures"); return []

try:
    from recognition.ocr_mvp import capture_images_from_camera, process_image_to_db, CardNameCorrector, setup_crop_interactively
    # Define DEFAULT_DICT_PATH using project_root_folder, AFTER project_root_folder is defined.
    DEFAULT_DICT_PATH = str(project_root_folder / "recognition" / "cards" / "card_names_symspell_clean.txt")
except ModuleNotFoundError as e:
    print(f"ERROR: Could not import from recognition.ocr_mvp: {e}")
    print(f"Project root: {project_root_folder}, sys.path: {sys.path}")
    # Define dummy functions
    def capture_images_from_camera(): print("DUMMY capture_images_from_camera"); return None
    def process_image_to_db(img_path, corrector, show_gui): print(f"DUMMY process_image_to_db: {img_path}"); return None
    class CardNameCorrector: # Dummy class
        def __init__(self, dictionary_path):
            print(f"DUMMY CardNameCorrector initialized with {dictionary_path}")
            # Attempt to create a dummy dictionary if the specified one isn't found during dummy init
            # This helps avoid a crash if the main init_db for corrector fails later due to missing dict.
            dict_dir = os.path.dirname(dictionary_path)
            if dict_dir and not os.path.exists(dict_dir): # Ensure base directory exists
                os.makedirs(dict_dir, exist_ok=True)
            if not os.path.exists(dictionary_path):
                 print(f"Warning: Dummy CardNameCorrector - dictionary not found at {dictionary_path}. Creating placeholder.")
                 try:
                     with open(dictionary_path, 'w') as f: f.write("dummyocr\n")
                 except Exception as ex_write:
                     print(f"Could not write placeholder dictionary for dummy: {ex_write}")

app = Flask(__name__) # static_folder='static', template_folder='templates' are default if named so

try:
    with app.app_context():
        init_db()
        print("Database initialized via app.py.")
except Exception as e:
    print(f"Error initializing database from app.py: {e}")

try:
    if not os.path.exists(DEFAULT_DICT_PATH):
        print(f"CRITICAL: Dictionary file not found at {DEFAULT_DICT_PATH}.")
        os.makedirs(os.path.dirname(DEFAULT_DICT_PATH), exist_ok=True)
        with open(DEFAULT_DICT_PATH, 'w') as f: f.write("dummy\n")
        card_corrector = None
        print("A dummy dictionary was created.")
    else:
        print(f"Loading CardNameCorrector with dictionary: {DEFAULT_DICT_PATH}")
        card_corrector = CardNameCorrector(dictionary_path=DEFAULT_DICT_PATH)
        print("CardNameCorrector loaded successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize CardNameCorrector: {e}")
    card_corrector = None

@app.route('/')
def index():
    return render_template('index.html') # Serve the main HTML page

@app.route('/configure_crop', methods=['POST'])
def configure_crop_route():
    try:
        setup_crop_interactively()
        return jsonify({"message": "Crop configuration process started. Check server display."}), 200
    except Exception as e:
        return jsonify({"error": "Failed to start crop configuration", "details": str(e)}), 500

@app.route('/scan', methods=['POST'])
def scan_card():
    if card_corrector is None:
        return jsonify({"error": "CardNameCorrector not initialized. Cannot process scan."}), 500
    image_path = capture_images_from_camera()
    if image_path is None:
        return jsonify({"error": "Failed to capture image from camera"}), 500
    processed_card_data = process_image_to_db(image_path, card_corrector, show_gui=False)
    if processed_card_data and processed_card_data.get("id"):
        try: os.remove(image_path)
        except OSError as e: print(f"Error removing temporary image {image_path}: {e}")
        return jsonify(processed_card_data), 201
    elif processed_card_data:
        return jsonify({"message": "Image processed, but no card identified or saved.", "details": processed_card_data}), 200
    else:
        try: os.remove(image_path)
        except OSError as e: print(f"Error removing temporary image {image_path} after failed processing: {e}")
        return jsonify({"error": "Failed to process image or save card data"}), 500

@app.route('/cards', methods=['GET'])
def get_all_cards():
    color = request.args.get('color')
    mana_cost_str = request.args.get('mana_cost')
    mana_cost = None
    if mana_cost_str:
        try: mana_cost = int(mana_cost_str) # The database expects float for cmc, but API uses int for mana_cost. This might need alignment. For now, respecting existing int conversion.
        except ValueError: return jsonify({"error": "Invalid mana_cost parameter"}), 400

    max_price_str = request.args.get('max_price')
    max_price = None
    if max_price_str:
        try:
            max_price = float(max_price_str)
        except ValueError:
            return jsonify({"error": "Invalid max_price parameter"}), 400

    cards_data = get_cards(color=color, mana_cost=mana_cost, max_price=max_price)
    return jsonify(cards_data), 200

def fetch_all_edhrec_cards(commander_name: str):
    """
    Fetches card recommendations for a given commander from EDHREC.
    """
    def format_commander_name(name: str) -> str:
        """
        Formats the commander name for the EDHREC URL.
        e.g., "Ao, Merchant of White" -> "ao-merchant-of-white"
        """
        name = name.lower()
        # Remove apostrophes and commas
        name = re.sub(r"['|,]", "", name)
        # Replace spaces and other non-alphanumeric characters (except hyphens) with hyphens
        name = re.sub(r"[^a-z0-9]+", "-", name)
        # Remove leading/trailing hyphens that might result from multiple replacements
        name = name.strip('-')
        return name

    formatted_name = format_commander_name(commander_name)
    if not formatted_name:
        print(f"Error: Could not format commander name: {commander_name}")
        return {}

    url = f"https://json.edhrec.com/pages/commanders/{formatted_name}.json"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching EDHREC data for {commander_name} (Formatted: {formatted_name}). Status: {response.status_code}, Response: {response.text[:200]}")
            return {} # Or raise ValueError as per original spec, returning {} for now to avoid unhandled exceptions in caller
    except requests.exceptions.RequestException as e:
        print(f"Request failed for EDHREC data for {commander_name} (Formatted: {formatted_name}): {e}")
        return {}

    try:
        json_response = response.json()
    except ValueError as e: # Includes JSONDecodeError
        print(f"Error parsing JSON response from EDHREC for {commander_name} (Formatted: {formatted_name}): {e}")
        return {}

    categorized_cards = {}
    if 'container' in json_response and 'json_dict' in json_response['container'] and 'cardlists' in json_response['container']['json_dict']:
        for section in json_response['container']['json_dict']['cardlists']:
            label = section.get('tag', 'unlabeled')
            # Ensure 'cardviews' exists and is a list before list comprehension
            cardviews = section.get('cardviews', [])
            if not isinstance(cardviews, list):
                print(f"Warning: 'cardviews' for section '{label}' is not a list. Skipping.")
                card_names = []
            else:
                card_names = [card.get('name') for card in cardviews if card.get('name')]

            if card_names: # Only add section if there are card names
                categorized_cards[label] = card_names
    else:
        print(f"Unexpected JSON structure from EDHREC for {commander_name} (Formatted: {formatted_name}). Response: {json_response}")
        # Fallback: Try to get any cards if the structure is partially different
        if 'cardlist' in json_response: # A common flat list structure in some EDHREC fallbacks
             card_names = [card.get('name') for card in json_response['cardlist'] if card.get('name')]
             if card_names:
                 categorized_cards['general'] = card_names

    return categorized_cards

@app.route('/deck_suggestions', methods=['GET'])
def deck_suggestions_route():
    legendaries = get_legendary_creatures()

    if not legendaries:
        return render_template('suggestions.html', error_message="No legendary creatures found in your collection.")

    all_user_cards_data = get_cards()
    # Convert user card names to lowercase for case-insensitive comparison
    user_card_names = {card['name'].lower() for card in all_user_cards_data if card.get('name')}

    best_commander_info = None
    max_matches = -1

    for commander_data in legendaries:
        commander_name = commander_data['name']
        # Skip commanders with no name (should not happen with current DB schema but good practice)
        if not commander_name:
            continue

        print(f"Fetching EDHREC suggestions for: {commander_name}") # Log which commander is being processed
        edhrec_cards_by_category = fetch_all_edhrec_cards(commander_name)

        if not edhrec_cards_by_category:
            print(f"No EDHREC suggestions found for {commander_name} or error occurred.")
            continue

        all_edhrec_suggestions = set()
        for category_cards in edhrec_cards_by_category.values():
            for card_name in category_cards:
                if isinstance(card_name, str): # Ensure card_name is a string
                    all_edhrec_suggestions.add(card_name.lower())

        if not all_edhrec_suggestions:
            print(f"EDHREC suggestions were empty for {commander_name} after processing categories.")
            continue

        owned_suggestions = list(all_edhrec_suggestions.intersection(user_card_names))
        current_match_count = len(owned_suggestions)

        print(f"Commander: {commander_name}, Matches: {current_match_count}, Owned suggestions: {owned_suggestions[:5]}...") # Log matches

        if current_match_count > max_matches:
            max_matches = current_match_count
            best_commander_info = {
                'name': commander_name,
                'suggestions': owned_suggestions,
                'match_count': current_match_count,
                'image_uri': commander_data.get('image_uri') # Pass image URI to template
            }

    if best_commander_info and best_commander_info['match_count'] > 0:
        print(f"Best commander: {best_commander_info['name']} with {best_commander_info['match_count']} matches.")
        return render_template('suggestions.html',
                               commander_name=best_commander_info['name'],
                               suggested_cards=best_commander_info['suggestions'],
                               match_count=best_commander_info['match_count'],
                               commander_image_uri=best_commander_info.get('image_uri'))
    else:
        print("Could not find a suitable commander or no matches found after checking all legendaries.")
        return render_template('suggestions.html', message="Could not find a commander with significant matches in your collection based on EDHREC suggestions.")

@app.route('/export/csv', methods=['GET'])
def export_cards_csv():
    cards_data = get_cards()
    if not cards_data:
        return jsonify({"message": "No cards to export."}), 404
    csv_buffer = io.StringIO()
    if cards_data: fieldnames = cards_data[0].keys()
    else: fieldnames = ['id', 'name', 'ocr_name_raw', 'price', 'color_identity', 'image_path', 'timestamp']
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cards_data)
    csv_buffer.seek(0)
    mem_csv = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
    csv_buffer.close()
    return send_file(mem_csv, as_attachment=True, download_name='scanned_cards.csv', mimetype='text/csv')

@app.route('/cards/delete/<int:card_id>', methods=['DELETE'])
def delete_card_route(card_id):
    try:
        if delete_card(card_id):
            return jsonify({"message": "Card deleted successfully"}), 200
        else:
            return jsonify({"error": "Card not found"}), 404
    except Exception as e:
        print(f"Error deleting card with ID {card_id}: {e}") # Log the error
        return jsonify({"error": "Failed to delete card"}), 500

if __name__ == '__main__':
    dict_dir = project_root_folder / "recognition" / "cards"
    os.makedirs(dict_dir, exist_ok=True)
    dummy_dict_for_local_run = dict_dir / "card_names_symspell_clean.txt"
    if not dummy_dict_for_local_run.exists():
        with open(dummy_dict_for_local_run, 'w') as f: f.write("TestCard\nSol Ring\nIsland")
    try:
        subprocess.run(['libcamera-still', '--version'], capture_output=True, check=True, text=True)
        print("libcamera-still found.")
    except Exception: # More general exception for CI environments
        print("WARNING: libcamera-still not found or not runnable. /scan endpoint will likely fail.")
    app.run(debug=True, host='0.0.0.0', port=5000)
