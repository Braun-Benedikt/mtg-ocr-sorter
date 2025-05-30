import os
import platform
import cv2
import time
import subprocess
import tempfile
import pandas as pd
import pytesseract
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
import numpy as np
import requests
from symspellpy.symspellpy import SymSpell, Verbosity

from fuzzy_match import CardNameCorrector


# Global Constants (if any specific ones are needed beyond defaults in main)
# Example: CROP_RATIO_HEIGHT_START = 0.23 (if used by other functions externally)
# For now, we assume these are mainly for extract_card_name_area and can be kept there or made local.

def capture_images_from_camera() -> str | None:
    """
    Captures a single image from the default camera.

    The image is saved as "current_capture.jpg" in the "captured_images" directory,
    which is created if it doesn't exist. The directory is not cleared by this function.

    Returns:
        The full filepath string of the captured image if successful.
        None if any error occurs (e.g., libcamera-still not found, command execution error).
    """
    # Create directory for captured images
    # Project root is assumed to be the parent of the 'recognition' directory
    project_root = Path(__file__).resolve().parent.parent
    capture_dir = project_root / "captured_images"

    # Create the directory if it doesn't exist, but do not clear it.
    os.makedirs(capture_dir, exist_ok=True)

    filename = "current_capture.jpg"
    filepath = capture_dir / filename
    command = ['libcamera-still', '-o', str(filepath), '--nopreview']

    print(f"Attempting to capture image to: {filepath}")

    try:
        # Execute the command
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"📸 Image captured and saved: {filepath} using libcamera-still.")
        return str(filepath)

    except FileNotFoundError:
        print("Error: libcamera-still command not found. Please ensure it is installed and in PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing libcamera-still for {filepath}: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return None
    except Exception as e:  # Catch any other unexpected errors during subprocess execution
        print(f"An unexpected error occurred while trying to capture {filepath}: {e}")
        return None


# Default crop ratios used in extract_card_name_area
# These can be defined as constants if they are intended to be fixed,
# or passed as parameters if they should be configurable per call.
# Based on the current implementation, they are fixed.
CROP_RATIO_HEIGHT_START = 0.23
CROP_RATIO_HEIGHT_END = 0.255
CROP_RATIO_WIDTH_START = 0.32
CROP_RATIO_WIDTH_END = 0.60

# Conditional Tesseract path for Windows
if platform.system() == "Windows":
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        print(f"INFO: Tesseract executable not found at {tesseract_path}. Assuming it's in PATH.")
# For other OS, assume Tesseract is in PATH and no specific command is needed.

# Configuration
base_path = Path(__file__).resolve().parent
dir_path = base_path / "tests" / "test_images"
card_output = base_path / "tests" / "test_carddata.csv"
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

    cropped = extract_card_name_area(image_cv)  # Uses default ratios from constants
    ocr_raw, ocr_corrected = extract_card_name(cropped, corrector)

    if show_gui:
        # Ensure show_image_gui can handle potentially empty strings if ocr_raw/ocr_corrected are empty
        show_image_gui(image_cv, cropped, ocr_raw if ocr_raw else "N/A", ocr_corrected if ocr_corrected else "N/A")

    card_info_data = None
    if ocr_corrected:  # Only fetch info if we have a corrected name
        card_info_data = fetch_card_information(ocr_corrected)

    return {
        "image_path": image_path,
        "ocr_name_raw": ocr_raw,
        "card_name": ocr_corrected,
        "price": card_info_data[0] if card_info_data else None,
        "color_identity": card_info_data[1] if card_info_data else None,
        "error": None  # Explicitly set error to None if successful
    }


def main(image_dir: str = "tests/test_images",
         output_csv_file: str = "tests/test_carddata.csv",
         dict_path: str = "cards/card_names_symspell_clean.txt",
         show_gui_flag: bool = True,  # Added flag for GUI for easier testing
         use_camera: bool = False):
    # Ensure the dictionary path is correct relative to this script or an absolute path
    # If dict_path is relative like "cards/...", it's relative to CWD.
    # If ocr_mvp.py is in recognition/, then "cards/" is ../recognition/cards if CWD is project root
    # Or it's recognition/cards/ if CWD is recognition/
    # For consistency, let's assume dict_path is relative to project root or absolute.
    # The CardNameCorrector expects an absolute path or path relative to its own location.
    # Let's try to make it more robust by resolving from script location if relative.

    script_dir = os.path.dirname(__file__)  # Directory of ocr_mvp.py
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

    all_card_data = []

    if use_camera:
        print("Attempting to use camera for image acquisition...")
        project_root = Path(__file__).resolve().parent.parent
        capture_dir = project_root / "captured_images"

        # Create the directory if it doesn't exist
        os.makedirs(capture_dir, exist_ok=True)

        # Clear existing files in the directory
        print(f"Clearing existing files in {capture_dir}...")
        for item in capture_dir.iterdir():
            if item.is_file():
                try:
                    os.remove(item)
                    print(f"Removed {item}")
                except OSError as e:
                    print(f"Error removing file {item}: {e}")

        print("Starting camera capture loop...")
        while True:
            captured_image_path = capture_images_from_camera()

            if captured_image_path:
                print(f"📸 Processing captured image: {captured_image_path}")
                data = process_image(captured_image_path, corrector, show_gui=show_gui_flag)

                # Add to all_card_data regardless of error, process_image handles error reporting internally
                # but we only stop if card_name is not found.
                all_card_data.append(data)  # Append data even if it contains an error from process_image

                if data.get("error"):  # If process_image itself had an error (e.g. file not found after capture)
                    print(f"Error processing {captured_image_path}. See details above. Stopping capture.")
                    break

                card_name = data.get("card_name")
                if not card_name:
                    print("ℹ️ No card name recognized, stopping capture.")
                    break
                else:
                    print(f"Recognized card: {card_name}. Continuing capture...")
            else:
                print("⚠️ Camera capture failed, stopping process.")
                break  # Exit loop if camera capture fails

            print("Waiting for 1 second before next capture...")
            time.sleep(1)  # Delay for camera cooldown or card repositioning

    else:  # Not use_camera: process from directory
        if not image_dir or not os.path.isdir(image_dir):
            print(f"Error: Image directory '{image_dir}' not found or not specified.")
            return
        print(f"Using directory for image acquisition: {image_dir}")

        image_paths_to_process = []
        image_files_in_dir = [img for img in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, img))]
        if not image_files_in_dir:
            print(f"No image files found in directory: {image_dir}")
            return
        image_paths_to_process = [os.path.join(image_dir, img_name) for img_name in image_files_in_dir]

        if not image_paths_to_process:
            print("No images to process from directory.")
            return

        for full_path in image_paths_to_process:
            print(f"📸 Verarbeite: {full_path}")
            data = process_image(full_path, corrector, show_gui=show_gui_flag)
            # Add to CSV if no critical error during image loading in process_image
            if data.get("error") is None or "Image not found or unable to read" not in data.get("error", ""):
                all_card_data.append(data)
            # If card_name is empty, price and color will be None. This is fine.

    if not all_card_data:
        print("No card data processed or to write to CSV.")
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
    #      show_gui_flag=False,
    #      use_camera=False) # Example with use_camera

    # Default paths, GUI off for potential automated runs
    # main(show_gui_flag=False)

    # Example: Run with camera
    # main(show_gui_flag=False, use_camera=True, output_csv_file="tests/camera_carddata.csv")

    # Example usage of the new function (optional, can be commented out)
    # if __name__ == "__main__":
    #     # Default run (from directory, GUI off)
    #     # main(show_gui_flag=False)

    #     # Run with camera input, no GUI, save to a different CSV
    #     main(output_csv_file="tests/camera_output.csv", show_gui_flag=False, use_camera=True)

    #     # Test with specific image directory
    #     # main(image_dir="path/to/your/images", show_gui_flag=False)

    # Keep the original simple call for default behavior if no specific test is needed here.
    main(show_gui_flag=False)