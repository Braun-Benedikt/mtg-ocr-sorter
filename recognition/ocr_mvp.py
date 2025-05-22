import os
import platform # Added
import cv2
import pandas as pd
import pytesseract
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
import numpy as np
import requests
from symspellpy.symspellpy import SymSpell, Verbosity

from .fuzzy_match import CardNameCorrector

# Global Constants (if any specific ones are needed beyond defaults in main)
# Example: CROP_RATIO_HEIGHT_START = 0.23 (if used by other functions externally)
# For now, we assume these are mainly for extract_card_name_area and can be kept there or made local.

# Default crop ratios used in extract_card_name_area
# These can be defined as constants if they are intended to be fixed,
# or passed as parameters if they should be configurable per call.
# Based on the current implementation, they are fixed.
CROP_RATIO_HEIGHT_START = 0.23
CROP_RATIO_HEIGHT_END = 0.255
CROP_RATIO_WIDTH_START = 0.32
CROP_RATIO_WIDTH_END = 0.60

# Konfiguration
base_path = Path(__file__).resolve().parent
dir_path = base_path / "tests" / "test_images"
card_output = base_path / "tests"/ "test_carddata.csv"
dictionary_path = base_path / "cards" / "card_names_symspell_clean.txt"

# OCR & Bildverarbeitung
def extract_card_name_area(image: np.ndarray, 
                           hr_start: float = CROP_RATIO_HEIGHT_START, hr_end: float = CROP_RATIO_HEIGHT_END, 
                           wr_start: float = CROP_RATIO_WIDTH_START, wr_end: float = CROP_RATIO_WIDTH_END):
    h, w = image.shape[:2]
    return image[int(h * hr_start):int(h * hr_end), int(w * wr_start):int(w * wr_end)]

def extract_card_name(image: np.ndarray, corrector) -> tuple[str, str]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ocr_raw = pytesseract.image_to_string(gray, lang="eng")

    lines = [line.strip() for line in ocr_raw.split("\n") if line.strip()]
    if not lines:
        return "", ""

    best_term = ""
    best_score = -1
    for line in lines:
        print("OCR-Zeile:", repr(line))
        suggestions = corrector.symspell.lookup(line, Verbosity.TOP, max_edit_distance=2)
        for suggestion in suggestions:
            if suggestion.term in corrector.valid_names and suggestion.count > best_score:
                best_term = suggestion.term
                best_score = suggestion.count

    return ocr_raw.strip(), best_term if best_term else ""

def load_image_cv2(path: str) -> np.ndarray:
    image = cv2.imread(path)
    if image is None:
        # The test expects "Image not found or unable to read"
        raise ValueError(f"Image not found or unable to read: {path}") 
    return image

def cv2_to_tk(image: np.ndarray):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)
    pil_img = pil_img.resize((400, int(pil_img.height * 400 / pil_img.width)))
    return ImageTk.PhotoImage(pil_img)

def fetch_card_information(card_name):
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price = data.get('prices', {}).get('eur') or data.get('prices', {}).get('usd')
        color_id_list = data.get('color_identity', [])
        color_id = "".join(color_id_list)
        return [price, color_id]
    except Exception as e:
        print(f"⚠️ Fehler bei API für {card_name}: {e}")
        return None

def show_image_gui(original, cropped, ocr_raw, ocr_corrected):
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
        text=f"🃏 OCR: {ocr_raw or '[nichts erkannt]'}\n🔍 Korrigiert: {ocr_corrected}",
        font=("Helvetica", 14),
        justify="center"
    )
    result_label.pack(pady=20)
    root.mainloop()

def process_image(image_path: str, corrector: CardNameCorrector, show_gui: bool = True):
    try:
        image_cv = load_image_cv2(image_path)
    except ValueError as e:
        print(f"Error processing {image_path}: {e}")
        return {
            "image_path": image_path,
            "ocr_name_raw": None,
            "card_name": None,
            "price": None,
            "color_identity": None,
            "error": str(e)
        }

    cropped = extract_card_name_area(image_cv) # Uses default ratios from constants
    ocr_raw, ocr_corrected = extract_card_name(cropped, corrector)

    if show_gui:
        # Ensure show_image_gui can handle potentially empty strings if ocr_raw/ocr_corrected are empty
        show_image_gui(image_cv, cropped, ocr_raw if ocr_raw else "N/A", ocr_corrected if ocr_corrected else "N/A")

    card_info_data = None
    if ocr_corrected: # Only fetch info if we have a corrected name
        card_info_data = fetch_card_information(ocr_corrected)
    
    return {
        "image_path": image_path,
        "ocr_name_raw": ocr_raw,
        "card_name": ocr_corrected,
        "price": card_info_data[0] if card_info_data else None,
        "color_identity": card_info_data[1] if card_info_data else None,
        "error": None # Explicitly set error to None if successful
    }

def main(image_dir: str = "tests/test_images",
         output_csv_file: str = "tests/test_carddata.csv",
         dict_path: str = "cards/card_names_symspell_clean.txt",
         show_gui_flag: bool = True): # Added flag for GUI for easier testing
    
    # Ensure the dictionary path is correct relative to this script or an absolute path
    # If dict_path is relative like "cards/...", it's relative to CWD.
    # If ocr_mvp.py is in recognition/, then "cards/" is ../recognition/cards if CWD is project root
    # Or it's recognition/cards/ if CWD is recognition/
    # For consistency, let's assume dict_path is relative to project root or absolute.
    # The CardNameCorrector expects an absolute path or path relative to its own location.
    # Let's try to make it more robust by resolving from script location if relative.
    
    script_dir = os.path.dirname(__file__) # Directory of ocr_mvp.py
    if not os.path.isabs(dict_path) and dict_path.startswith("cards/"):
        # This assumes "cards/" is a subdir relative to where fuzzy_match.py (and thus CardNameCorrector) is.
        # CardNameCorrector itself handles `../recognition/cards` structure.
        # So, if dict_path is "cards/card_names_symspell_clean.txt", CardNameCorrector will look for
        # `recognition/cards/card_names_symspell_clean.txt` if fuzzy_match.py is in `recognition/`
        # This seems fine.
        pass


    try:
        corrector = CardNameCorrector(dictionary_path=dict_path)
    except FileNotFoundError as e:
        print(f"Error initializing CardNameCorrector: {e}")
        print(f"Please ensure the dictionary file exists at: {os.path.abspath(dict_path)}")
        return

    if not os.path.isdir(image_dir):
        print(f"Error: Image directory not found at {os.path.abspath(image_dir)}")
        return

    images = [img for img in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, img))]
    all_card_data = []

    for image_file_name in images:
        full_path = os.path.join(image_dir, image_file_name)
        print(f"📸 Verarbeite: {full_path}")
        # Pass the show_gui_flag to process_image
        data = process_image(full_path, corrector, show_gui=show_gui_flag)
        
        # Only add to CSV if there was no critical error and we have a card name (even if not corrected)
        # The test for process_image expects price/color to be None if card_name is empty.
        # We should add to CSV if processing happened, even if Scryfall found nothing.
        if data.get("error") is None: # Add if no load error
             all_card_data.append(data)
        # If card_name is empty, price and color will be None. This is fine.

    if not all_card_data:
        print("No card data processed or to write.")
        return

    df = pd.DataFrame(all_card_data)
    
    try:
        df.to_csv(output_csv_file, index=False)
        print(f"✅ CSV geschrieben: {os.path.abspath(output_csv_file)}")
    except Exception as e:
        print(f"Error writing CSV to {os.path.abspath(output_csv_file)}: {e}")


if __name__ == "__main__":
    # Example of how to run with non-default paths:
    # main(image_dir="path/to/your/images", 
    #      output_csv_file="path/to/your/output.csv",
    #      dict_path="path/to/your/dictionary.txt",
    #      show_gui_flag=False) # For non-interactive runs
    main(show_gui_flag=False) # Default paths, GUI off for potential automated runs
