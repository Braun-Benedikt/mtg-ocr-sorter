import os
import sys # Crucial import
from flask import Flask, jsonify, request, send_file, render_template
from werkzeug.utils import secure_filename
import io
import csv
from pathlib import Path # Crucial import
import subprocess # For libcamera-still check in if __name__ == '__main__'

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
    from web_app.database import init_db, add_card, get_cards, delete_card
except ModuleNotFoundError as e:
    print(f"ERROR: Could not import database module from web_app.database: {e}")
    print(f"Project root: {project_root_folder}, sys.path: {sys.path}")
    # Define dummy functions if import fails, so the script can still be imported
    def init_db(): print("DUMMY init_db: web_app.database not found")
    def add_card(name, **kwargs): print(f"DUMMY add_card: {name}"); return None
    def get_cards(**kwargs): print("DUMMY get_cards"); return []
    def delete_card(card_id): print(f"DUMMY delete_card: {card_id}"); return False

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
        try: mana_cost = int(mana_cost_str)
        except ValueError: return jsonify({"error": "Invalid mana_cost parameter"}), 400
    cards_data = get_cards(color=color, mana_cost=mana_cost)
    return jsonify(cards_data), 200

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
