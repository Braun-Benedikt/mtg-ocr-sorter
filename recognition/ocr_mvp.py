import os
import platform
import cv2
import time
import subprocess
import tempfile
import pandas as pd # Keep for now, might be removed if no other part uses it
import pytesseract
import tkinter as tk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from pathlib import Path
import numpy as np
import requests
from symspellpy.symspellpy import SymSpell, Verbosity

# --- Add project root to sys.path for web_app import ---
import sys
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# --- End sys.path modification ---

try:
    from recognition.fuzzy_match import CardNameCorrector
except ModuleNotFoundError: # If running ocr_mvp.py directly from recognition/ for some reason
    from fuzzy_match import CardNameCorrector

try:
    from web_app.database import add_card, init_db
except ModuleNotFoundError as e:
    print(f"Could not import from web_app.database: {e}")
    print("Ensure web_app/database.py exists and project root is in sys.path.")
    # Define dummy functions if import fails, so the script can still be imported by other modules
    # without crashing, though it won't save to DB.
    def add_card(name: str, ocr_name_raw: str = None, price: float = None, color_identity: str = None, image_path: str = None, cmc: float = 0.0, type_line: str = '', image_uri: str = ''):
        print(f"DUMMY add_card called: {name}, cmc: {cmc}, type: {type_line}, image_uri: {image_uri} (Database not available)")
        return None
    def init_db():
        print("DUMMY init_db called (Database not available)")


# Global Constants
CROP_RATIO_HEIGHT_START = 0.23
CROP_RATIO_HEIGHT_END = 0.255
CROP_RATIO_WIDTH_START = 0.32
CROP_RATIO_WIDTH_END = 0.60

if platform.system() == "Windows":
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        print(f"INFO: Tesseract executable not found at {tesseract_path}. Assuming it's in PATH.")

# Default paths (dictionary_path might be passed by main.py)
dictionary_path_default = project_root / "recognition" / "cards" / "card_names_multilingual_symspell_clean.txt"


def setup_crop_interactively():
    """
    Allows the user to interactively select a crop area on an image (captured or dummy)
    and updates the global crop ratio constants.
    """
    image_path = capture_images_from_camera()
    image = None

    if image_path:
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to read captured image from {image_path}. Using fallback dummy image.")
            # Fall through to dummy image creation if imread fails

    if image is None: # If capture failed or reading failed
        print("Using fallback dummy image for ROI selection.")
        image = np.zeros((480, 680, 3), dtype=np.uint8) # Black image HxW
        cv2.putText(image, "Please select the card name area.", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if image is None: # Should not happen if dummy image logic is correct
        print("Error: Could not load or create an image for ROI selection.")
        return

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Placeholder for the selected ROI, to be updated by the callback
    # Using a list to allow modification in the callback scope
    selected_roi = [None]

    def onselect(eclick, erelease):
        # eclick and erelease are MouseEvents on press and release
        # eclick.xdata, eclick.ydata, erelease.xdata, erelease.ydata
        x1, y1 = int(eclick.xdata), int(eclick.ydata)
        x2, y2 = int(erelease.xdata), int(erelease.ydata)
        # Store as (x, y, w, h)
        # Ensure x1,y1 is top-left and x2,y2 is bottom-right
        _x = min(x1, x2)
        _y = min(y1, y2)
        _w = abs(x1 - x2)
        _h = abs(y1 - y2)
        selected_roi[0] = (_x, _y, _w, _h)
        print(f"ROI drawn: (x={_x}, y={_y}, w={_w}, h={_h})") # Log the raw selection

    fig, ax = plt.subplots()
    ax.imshow(image_rgb)
    ax.set_title("Select card name area. Close window to confirm selection or cancel.")

    # RectangleSelector
    # Important: The selector object must be assigned to a variable,
    # otherwise it will be garbage collected and won't work.
    rs = RectangleSelector(ax, onselect,
                           useblit=True,
                           button=[1],  # Left mouse button
                           minspanx=5, minspany=5,
                           spancoords='pixels',
                           interactive=True)

    print("Please select the crop area in the Matplotlib window.")
    print("Close the window when done, or to cancel if no selection was made.")
    plt.show() # This is a blocking call. Window needs to be closed by user.

    # After the window is closed, check if an ROI was selected
    if selected_roi[0] is not None:
        r = selected_roi[0]
        x, y, w, h = r # These are already int from the onselect callback
        print(f"Final ROI chosen: (x={x}, y={y}, w={w}, h={h})")

        img_h, img_w = image_rgb.shape[:2] # Get dimensions from the RGB image

        if w > 0 and h > 0: # Ensure valid selection (width and height are positive)
            # Calculate new ratios
            new_hr_start = y / img_h
            new_hr_end = (y + h) / img_h
            new_wr_start = x / img_w
            new_wr_end = (x + w) / img_w

            # Update global variables
            global CROP_RATIO_HEIGHT_START, CROP_RATIO_HEIGHT_END
            global CROP_RATIO_WIDTH_START, CROP_RATIO_WIDTH_END

            CROP_RATIO_HEIGHT_START = new_hr_start
            CROP_RATIO_HEIGHT_END = new_hr_end
            CROP_RATIO_WIDTH_START = new_wr_start
            CROP_RATIO_WIDTH_END = new_wr_end

            # Using globals().update() is also an option here if preferred:
            # globals().update({
            #     'CROP_RATIO_HEIGHT_START': new_hr_start,
            #     'CROP_RATIO_HEIGHT_END': new_hr_end,
            #     'CROP_RATIO_WIDTH_START': new_wr_start,
            #     'CROP_RATIO_WIDTH_END': new_wr_end
            # })

            print("\n--- Crop Ratios Updated (using Matplotlib selection) ---")
            print(f"CROP_RATIO_HEIGHT_START = {CROP_RATIO_HEIGHT_START:.4f}")
            print(f"CROP_RATIO_HEIGHT_END = {CROP_RATIO_HEIGHT_END:.4f}")
            print(f"CROP_RATIO_WIDTH_START = {CROP_RATIO_WIDTH_START:.4f}")
            print(f"CROP_RATIO_WIDTH_END = {CROP_RATIO_WIDTH_END:.4f}")
            print("--------------------------------------------------------\n")
        else:
            print("No valid ROI selected (width or height is zero). Crop ratios not updated.")
    else:
        print("ROI selection cancelled or window closed before selection. Crop ratios not updated.")


def capture_images_from_camera() -> str | None:
    capture_dir = project_root / "captured_images"
    os.makedirs(capture_dir, exist_ok=True)
    filename = f"capture_{int(time.time())}.jpg" # Unique filename
    filepath = capture_dir / filename
    command = ['libcamera-still', '-o', str(filepath), '--nopreview', '-t', '500'] # Short timeout

    print(f"Attempting to capture image to: {filepath}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"📸 Image captured and saved: {filepath}")
        return str(filepath)
    except FileNotFoundError:
        print("Error: libcamera-still command not found.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing libcamera-still: {e}")
        if e.stdout: print(f"STDOUT: {e.stdout}")
        if e.stderr: print(f"STDERR: {e.stderr}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def extract_card_name_area(image: np.ndarray,
                           hr_start: float = None, hr_end: float = None,
                           wr_start: float = None, wr_end: float = None):
    """
    Extracts the card name area from an image using specified ratios.
    If ratios are not provided, it uses the current global CROP_RATIO_* constants from the module.
    """
    h, w = image.shape[:2]

    # Use current global values if specific ratios are not provided
    # These local variables will hold the ratios to be used.
    actual_hr_start = hr_start if hr_start is not None else CROP_RATIO_HEIGHT_START
    actual_hr_end = hr_end if hr_end is not None else CROP_RATIO_HEIGHT_END
    actual_wr_start = wr_start if wr_start is not None else CROP_RATIO_WIDTH_START
    actual_wr_end = wr_end if wr_end is not None else CROP_RATIO_WIDTH_END

    cropped_img = image[int(h * actual_hr_start):int(h * actual_hr_end), int(w * actual_wr_start):int(w * actual_wr_end)]

    return cropped_img


def extract_card_name(image: np.ndarray, corrector, language="eng") -> tuple[str, str]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Try multiple language configurations for better recognition
    ocr_results = []
    
    # Try English first
    try:
        ocr_eng = pytesseract.image_to_string(gray, lang="eng")
        ocr_results.append(("eng", ocr_eng))
    except Exception as e:
        print(f"Warning: English OCR failed: {e}")
    
    # Try German if specified or if English failed
    if language == "deu" or not ocr_results:
        try:
            ocr_deu = pytesseract.image_to_string(gray, lang="deu")
            ocr_results.append(("deu", ocr_deu))
        except Exception as e:
            print(f"Warning: German OCR failed: {e}")
    
    # Try combined English+German if both are available
    if len(ocr_results) >= 2:
        try:
            ocr_combined = pytesseract.image_to_string(gray, lang="eng+deu")
            ocr_results.append(("eng+deu", ocr_combined))
        except Exception as e:
            print(f"Warning: Combined OCR failed: {e}")
    
    # If no OCR results, return empty
    if not ocr_results:
        return "", ""
    
    # Process all OCR results
    all_lines = []
    for lang, ocr_text in ocr_results:
        lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
        all_lines.extend([(lang, line) for line in lines])
    
    if not all_lines:
        return "", ""
    
    best_term = ""
    best_score = -1
    
    # Check if corrector and its symspell attribute are properly initialized
    if corrector and hasattr(corrector, 'symspell') and hasattr(corrector.symspell, 'lookup') and hasattr(corrector, 'valid_names'):
        for lang, line in all_lines:
            suggestions = corrector.symspell.lookup(line, Verbosity.TOP, max_edit_distance=2)
            for suggestion in suggestions:
                if suggestion.term in corrector.valid_names and suggestion.count > best_score:
                    best_term = suggestion.term
                    best_score = suggestion.count
    else:
        print("Warning: CardNameCorrector not fully initialized. Skipping fuzzy matching.")
        # Fallback: use the longest line from OCR if no correction is possible
        if all_lines:
            best_term = max(all_lines, key=lambda x: len(x[1]))[1]
    
    # Return the first OCR result as raw text, and the best corrected term
    return ocr_results[0][1].strip(), best_term


def load_image_cv2(path: str) -> np.ndarray | None:
    if not os.path.exists(path):
        print(f"Error: Image file not found at {path}")
        return None
    image = cv2.imread(path)
    if image is None:
        print(f"Error: Unable to read image at {path} (cv2.imread returned None)")
        return None
    return image


def cv2_to_tk(image: np.ndarray):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)
    pil_img = pil_img.resize((400, int(pil_img.height * 400 / pil_img.width)))
    return ImageTk.PhotoImage(pil_img)


def fetch_card_information(card_name):
    if not card_name: return None
    
    # Try to fetch card information using the exact name first
    card_info = _fetch_card_by_name(card_name)
    if card_info:
        return card_info
    
    # If that fails, try to find the card by searching for it
    # This is useful for German cards where we might need to find the English equivalent
    card_info = _search_card_by_name(card_name)
    if card_info:
        return card_info
    
    return None

def _fetch_card_by_name(card_name):
    """Fetch card information by exact name"""
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return _extract_card_data(data)
    except requests.RequestException as e:
        print(f"⚠️ API Error for {card_name}: {e}")
        return None

def _search_card_by_name(card_name):
    """Search for card by name (fuzzy search)"""
    url = f"https://api.scryfall.com/cards/search"
    params = {"q": f'!"{card_name}"', "unique": "cards"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('data') and len(data['data']) > 0:
            # Return the first (most relevant) result
            return _extract_card_data(data['data'][0])
        else:
            print(f"⚠️ No card found for: {card_name}")
            return None
            
    except requests.RequestException as e:
        print(f"⚠️ Search API Error for {card_name}: {e}")
        return None

def _extract_card_data(data):
    """Extract card data from Scryfall API response"""
    price = data.get('prices', {}).get('eur') or data.get('prices', {}).get('usd')
    color_id_list = data.get('color_identity', [])
    color_id = "".join(color_id_list) if color_id_list else "C"
    cmc = data.get('cmc', 0.0)
    type_line = data.get('type_line', '')
    image_uri = data.get('image_uris', {}).get('normal', '')
    return {"price": price, "color_identity": color_id, "cmc": cmc, "type_line": type_line, "image_uri": image_uri}


def show_image_gui(original, cropped, ocr_raw, ocr_corrected):
    # This function uses Tkinter and might not be suitable for a web server environment.
    # It should ideally be conditionally called or removed if running in a headless server context.
    # For now, it's kept but will only be called if show_gui_flag is True.
    try:
        root = tk.Tk()
        root.title("Magic-Karte OCR-Vorschau")

        tk_img1 = cv2_to_tk(original)
        label1 = tk.Label(root, image=tk_img1, text="Original", compound="top")
        label1.pack(padx=10, pady=10)

        tk_img2 = cv2_to_tk(cropped)
        label2 = tk.Label(root, image=tk_img2, text="Zugeschnittener Namebereich", compound="top")
        label2.pack(padx=10, pady=10)

        result_label = tk.Label(
            root,
            text=f"🃏 OCR: {ocr_raw or '[nichts erkannt]'}\n🔍 Korrigiert: {ocr_corrected or '[nicht korrigiert]'}",
            font=("Helvetica", 14),
            justify="center"
        )
        result_label.pack(pady=20)
        root.mainloop()
    except tk.TclError as e: # Catches errors like $DISPLAY not being set
        print(f"Tkinter GUI error: {e}. GUI might not be available in this environment.")
    except NameError as e: # If tk was not imported (should not happen with restored imports)
        print(f"show_image_gui error: {e}. Tkinter might not be imported.")


def process_image_to_db(image_path: str, corrector: CardNameCorrector, show_gui: bool = False):
    # Initialize database (ensures table exists) - consider calling this once at app start
    # init_db() # Moved to web app startup

    image_cv = load_image_cv2(image_path)
    if image_cv is None:
        print(f"Error loading image {image_path}, cannot process.")
        return None # Indicate failure

    cropped = extract_card_name_area(image_cv)
    ocr_raw, ocr_corrected = extract_card_name(cropped, corrector)

    if not ocr_corrected:
        print(f"No card name could be reliably extracted for {image_path}.")
        # Optionally, still save with raw OCR if needed, or just return
        # add_card(name="UNKNOWN", ocr_name_raw=ocr_raw, image_path=image_path)
        return None # Indicate failure to identify a card

    print(f"Recognized: {ocr_corrected} (Raw: {ocr_raw}) from {image_path}")

    card_info = fetch_card_information(ocr_corrected)
    price = card_info['price'] if card_info else None
    color_identity = card_info['color_identity'] if card_info else None
    cmc = card_info['cmc'] if card_info else 0.0
    type_line = card_info['type_line'] if card_info else ''
    image_uri = card_info['image_uri'] if card_info else ''

    try:
        card_id = add_card(
            name=ocr_corrected,
            ocr_name_raw=ocr_raw,
            price=price,
            color_identity=color_identity,
            image_path=image_path,
            cmc=cmc,
            type_line=type_line,
            image_uri=image_uri
        )
        print(f"Card '{ocr_corrected}' saved to database with ID: {card_id}.")

        if show_gui: # Conditional GUI display
            show_image_gui(image_cv, cropped, ocr_raw, ocr_corrected)

        return {
            "id": card_id,
            "name": ocr_corrected,
            "ocr_name_raw": ocr_raw,
            "price": price,
            "color_identity": color_identity,
            "image_path": image_path,
            "cmc": cmc,
            "type_line": type_line,
            "image_uri": image_uri
        }
    except Exception as e:
        print(f"Error saving card '{ocr_corrected}' to database: {e}")
        return None


# Main function for processing (e.g., from directory or single camera shot)
# This is mostly for standalone testing now or if main.py calls it.
# The web app will likely call process_image_to_db or capture_and_process directly.
def main_process_entries(image_dir: str = None,
                         output_csv_file: str = None, # No longer used for CSV
                         dict_path: str = None,
                         show_gui_flag: bool = False,
                         use_camera: bool = False):

    # Resolve dictionary path
    if dict_path is None:
        # If recognition/ocr_mvp.py is run directly, __file__ is recognition/ocr_mvp.py
        # project_root is parent of recognition/
        # dictionary_path_default is project_root/recognition/cards/...
        resolved_dict_path = dictionary_path_default
    elif not os.path.isabs(dict_path):
        # If a relative path is given, assume it's relative to project root
        resolved_dict_path = project_root / dict_path
    else:
        resolved_dict_path = Path(dict_path)

    if not resolved_dict_path.exists():
        print(f"Error: Dictionary file not found at {resolved_dict_path}")
        print("Please run tools/build_symspell_dictionary.py and tools/symspell_dict_bereinigung.py")
        return

    try:
        # CardNameCorrector expects path relative to its own location (fuzzy_match.py)
        # or an absolute path.
        # If fuzzy_match.py is in recognition/, and dict is in recognition/cards/
        # then relative path from fuzzy_match.py is "cards/card_name_symspell_clean.txt"
        # If dict_path from main.py is "recognition/cards/card_names_symspell_clean.txt" (rel to project root)
        # CardNameCorrector needs to handle this.
        # For simplicity, we pass the absolute path to CardNameCorrector.
        corrector = CardNameCorrector(dictionary_path=str(resolved_dict_path))
    except FileNotFoundError as e:
        print(f"Error initializing CardNameCorrector: {e}")
        return
    except Exception as e: # Catch other potential errors from CardNameCorrector init
        print(f"An unexpected error occurred initializing CardNameCorrector: {e}")
        return

    # Initialize DB (make sure table exists)
    # This should ideally be done once when the application (web server) starts.
    # Calling it here is safe due to "IF NOT EXISTS" in table creation.
    try:
        init_db()
    except Exception as e:
        print(f"Failed to initialize database: {e}. Card processing might fail to save.")
        # Depending on requirements, might want to exit or continue without DB.

    if use_camera:
        print("Attempting camera capture and processing...")
        captured_image_path = capture_images_from_camera()
        if captured_image_path:
            process_image_to_db(captured_image_path, corrector, show_gui=show_gui_flag)
            # After processing, we might want to remove the captured image if it's temporary
            # For now, let's keep it.
            # try:
            #     os.remove(captured_image_path)
            #     print(f"Removed temporary image: {captured_image_path}")
            # except OSError as e:
            #     print(f"Error removing temporary image {captured_image_path}: {e}")
        else:
            print("Camera capture failed. Nothing to process.")
    elif image_dir:
        if not os.path.isdir(image_dir):
            print(f"Error: Image directory '{image_dir}' not found.")
            return
        print(f"Processing images from directory: {image_dir}")
        for img_name in os.listdir(image_dir):
            full_path = os.path.join(image_dir, img_name)
            if os.path.isfile(full_path) and img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                print(f"Processing: {full_path}")
                process_image_to_db(full_path, corrector, show_gui=show_gui_flag)
            else:
                print(f"Skipping non-image file or directory: {img_name}")
    else:
        print("No image source specified (camera or directory). Exiting.")

    print("Processing complete.")


# This direct execution block is for testing ocr_mvp.py itself.
if __name__ == "__main__":
    print("Running ocr_mvp.py directly for testing...")

    # Create a dummy image for testing if no test images exist.
    # This helps ensure the script can run end-to-end for basic checks.
    test_image_dir = project_root / "tests" / "test_images"
    os.makedirs(test_image_dir, exist_ok=True)
    dummy_image_path = test_image_dir / "dummy_card.png"

    if not list(test_image_dir.glob('*.[jp][pn]g')): # Check if any jpg/png exists
        print(f"No test images found in {test_image_dir}. Creating a dummy image.")
        try:
            # Create a simple black image
            dummy_img = np.zeros((680, 480, 3), dtype=np.uint8) # Typical card aspect ratio
            cv2.putText(dummy_img, "Test Card Name", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            cv2.imwrite(str(dummy_image_path), dummy_img)
            print(f"Dummy image created at {dummy_image_path}")
        except Exception as e:
            print(f"Could not create dummy image: {e}")

    # Ensure the dictionary exists, otherwise CardNameCorrector will fail.
    # The dictionary is expected at project_root/recognition/cards/card_names_symspell_clean.txt
    dict_file = project_root / "recognition" / "cards" / "card_names_symspell_clean.txt"
    if not dict_file.exists():
        print(f"ERROR: Dictionary file not found at {dict_file}")
        print("Please generate it first using tools/build_symspell_dictionary.py and tools/symspell_dict_bereinigung.py")
        print("Skipping main_process_entries due to missing dictionary.")
    else:
        print(f"Using dictionary: {dict_file}")
        # Test processing from directory (using the potentially created dummy image)
        # GUI is off for automated tests.
        main_process_entries(image_dir=str(test_image_dir), show_gui_flag=False, dict_path=str(dict_file))

        # Example of testing with camera (will likely fail in CI/non-Pi environments)
        # print("\nTesting with camera (this might not work if no camera or libcamera-still):")
        # main_process_entries(use_camera=True, show_gui_flag=False, dict_path=str(dict_file))
