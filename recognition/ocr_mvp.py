import os
import cv2
import pandas as pd
import pytesseract
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
import numpy as np
import requests
from symspellpy.symspellpy import SymSpell, Verbosity

from recognition.fuzzy_match import CardNameCorrector

# Konfiguration
dir_path = "tests/test_images"
card_output = "tests/test_carddata.csv"
dictionary_path = "cards/card_names_symspell_clean.txt"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# OCR & Bildverarbeitung
def extract_card_name_area(image: np.ndarray, crop_ratio_height: float = 0.3, crop_ratio_width: float = 0.8):
    h, w = image.shape[:2]
    return image[int(h * 0.23):int(h * 0.255), int(w * 0.32):int(w * 0.6)]

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
        raise ValueError(f"Bild konnte nicht geladen werden: {path}")
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
    image_cv = load_image_cv2(image_path)
    cropped = extract_card_name_area(image_cv)
    ocr_raw, ocr_corrected = extract_card_name(cropped, corrector)
    if show_gui:
        show_image_gui(image_cv, cropped, ocr_raw, ocr_corrected)
    card_info = fetch_card_information(ocr_corrected)
    return {
        "card_name": ocr_corrected,
        "price": card_info[0] if card_info else None,
        "color_identity": card_info[1] if card_info else None
    }

def main():
    corrector = CardNameCorrector(dictionary_path=dictionary_path)
    images = [img for img in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, img))]
    all_card_data = []

    for image in images:
        full_path = os.path.join(dir_path, image)
        print(f"📸 Verarbeite: {full_path}")
        data = process_image(full_path, corrector, show_gui=True)
        if data["card_name"]:
            all_card_data.append(data)

    df = pd.DataFrame(all_card_data)
    df.to_csv(card_output, index=False)
    print(f"✅ CSV geschrieben: {card_output}")

if __name__ == "__main__":
    main()
