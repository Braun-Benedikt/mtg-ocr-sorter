import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import os
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Attempt to import functions from recognition.ocr_mvp
# This also helps to catch if TESSERACT_CMD_PATH is an immediate problem
try:
    from recognition.ocr_mvp import (
        load_image_cv2,
        extract_card_name_area,
        extract_card_name,
        fetch_card_information,
        process_image,
        CROP_RATIO_HEIGHT_START, CROP_RATIO_HEIGHT_END,
        CROP_RATIO_WIDTH_START, CROP_RATIO_WIDTH_END
    )
    # We need cv2 and requests for type hinting and exceptions if not fully mocked
    import cv2 
    import requests
except ImportError as e:
    print(f"Error importing ocr_mvp or its dependencies: {e}")
    print("Ensure Tesseract is installed if TESSERACT_CMD_PATH is the issue, though it should be mocked for tests.")
    # If Tesseract is not installed, pytesseract might raise an error on import or at runtime
    # For tests, we mock pytesseract.image_to_string, so the command itself might not be called.
    # However, the initial setup of TESSERACT_CMD_PATH in ocr_mvp.py might still be problematic
    # if it relies on tesseract being present to even define the variable.
    # This is a known potential issue mentioned in the prompt.
    # For now, we'll proceed assuming the mocks will bypass direct Tesseract calls.
    pass


class TestOcrMvp(unittest.TestCase):

    @patch('recognition.ocr_mvp.cv2.imread')
    def test_load_image_cv2(self, mock_cv2_imread):
        # Test successful image load
        mock_img = MagicMock()
        mock_cv2_imread.return_value = mock_img
        result = load_image_cv2("dummy_path.jpg")
        self.assertEqual(result, mock_img)
        mock_cv2_imread.assert_called_once_with("dummy_path.jpg")

        # Test image load failure (imread returns None)
        mock_cv2_imread.return_value = None
        with self.assertRaises(ValueError) as context:
            load_image_cv2("another_dummy_path.jpg")
        self.assertTrue("Image not found or unable to read" in str(context.exception))

    def test_extract_card_name_area(self):
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        h, w, _ = dummy_image.shape

        # Using default ratios from ocr_mvp.py for consistency
        # Default crop_ratio_height: 0.23 to 0.255
        # Default crop_ratio_width: 0.32 to 0.60
        # These were the values in the prompt, let's ensure they are used or imported
        
        # Expected height: h * (0.255 - 0.23)
        # Expected width: w * (0.6 - 0.32)
        # Corrected to use the imported constants
        expected_h = int(h * (CROP_RATIO_HEIGHT_END - CROP_RATIO_HEIGHT_START))
        expected_w = int(w * (CROP_RATIO_WIDTH_END - CROP_RATIO_WIDTH_START))

        cropped_image = extract_card_name_area(dummy_image) # Uses default ratios
        self.assertEqual(cropped_image.shape[0], expected_h)
        self.assertEqual(cropped_image.shape[1], expected_w)
        self.assertEqual(cropped_image.shape[2], 3)

        # Test with custom ratios
        custom_hr_start, custom_hr_end = 0.1, 0.2
        custom_wr_start, custom_wr_end = 0.1, 0.2
        expected_custom_h = int(h * (custom_hr_end - custom_hr_start))
        expected_custom_w = int(w * (custom_wr_end - custom_wr_start))
        
        cropped_custom = extract_card_name_area(dummy_image, custom_hr_start, custom_hr_end, custom_wr_start, custom_wr_end)
        self.assertEqual(cropped_custom.shape[0], expected_custom_h)
        self.assertEqual(cropped_custom.shape[1], expected_custom_w)


    @patch('recognition.ocr_mvp.pytesseract.image_to_string')
    def test_extract_card_name(self, mock_image_to_string):
        dummy_image_area = np.zeros((50, 50, 3), dtype=np.uint8) # Not really used by mock

        # Mock CardNameCorrector
        mock_corrector = MagicMock()
        
        # --- Test Case 1: Successful correction ---
        raw_text_from_ocr = "Lighning Bolt\nSome other text\n"
        mock_image_to_string.return_value = raw_text_from_ocr
        
        # Mock symspell.lookup behavior
        mock_suggestion = MagicMock()
        mock_suggestion.term = "Lightning Bolt"
        mock_suggestion.count = 1 # distance or count, depending on SymSpell version/usage
        mock_suggestion.distance = 1 # SymSpellPy uses distance
        
        mock_corrector.correct.return_value = "Lightning Bolt"

        ocr_raw, ocr_corrected = extract_card_name(dummy_image_area, mock_corrector)
        
        mock_image_to_string.assert_called_once_with(dummy_image_area)
        mock_corrector.correct.assert_called_once_with("Lighning Bolt") # Assumes first line, stripped
        
        self.assertEqual(ocr_raw, "Lighning Bolt") # Should be the first line, stripped
        self.assertEqual(ocr_corrected, "Lightning Bolt")

        # Reset mocks for next case
        mock_image_to_string.reset_mock()
        mock_corrector.correct.reset_mock()

        # --- Test Case 2: No valid suggestion found (corrector returns original) ---
        raw_text_no_match = "Unkown Card Name\n"
        mock_image_to_string.return_value = raw_text_no_match
        mock_corrector.correct.return_value = "Unkown Card Name" # Corrector returns original if no good match

        ocr_raw_no_match, ocr_corrected_no_match = extract_card_name(dummy_image_area, mock_corrector)
        
        self.assertEqual(ocr_raw_no_match, "Unkown Card Name")
        self.assertEqual(ocr_corrected_no_match, "Unkown Card Name")
        mock_corrector.correct.assert_called_once_with("Unkown Card Name")
        
        # --- Test Case 3: OCR returns empty string ---
        mock_image_to_string.return_value = ""
        mock_corrector.correct.return_value = "" # Corrector might return empty for empty

        ocr_raw_empty, ocr_corrected_empty = extract_card_name(dummy_image_area, mock_corrector)
        self.assertEqual(ocr_raw_empty, "")
        self.assertEqual(ocr_corrected_empty, "")
        # corrector.correct might not be called if raw is empty, depends on implementation
        # Current ocr_mvp.py calls correct even with empty string.
        mock_corrector.correct.assert_called_once_with("")


    @patch('recognition.ocr_mvp.requests.get')
    def test_fetch_card_information(self, mock_requests_get):
        # --- Test Case 1: Successful API call with EUR price ---
        mock_response_eur = MagicMock()
        mock_response_eur.json.return_value = {"prices": {"eur": "1.23", "usd": "1.50"}, "color_identity": ["R"]}
        mock_response_eur.raise_for_status = MagicMock() # Does nothing by default
        mock_requests_get.return_value = mock_response_eur

        result_eur = fetch_card_information("Test Card EUR")
        self.assertEqual(result_eur, ["1.23", "R"])
        mock_requests_get.assert_called_with("https://api.scryfall.com/cards/named", params={"exact": "Test Card EUR"})
        mock_response_eur.raise_for_status.assert_called_once()

        # --- Test Case 2: Successful API call with USD price (EUR is null) ---
        mock_response_usd = MagicMock()
        mock_response_usd.json.return_value = {"prices": {"eur": None, "usd": "1.50"}, "color_identity": ["U"]}
        mock_response_usd.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response_usd

        result_usd = fetch_card_information("Test Card USD")
        self.assertEqual(result_usd, ["1.50", "U"])
        
        # --- Test Case 3: Price is missing ---
        mock_response_no_price = MagicMock()
        mock_response_no_price.json.return_value = {"prices": {"eur": None, "usd": None}, "color_identity": ["B"]}
        mock_response_no_price.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response_no_price
        
        result_no_price = fetch_card_information("Test Card No Price")
        self.assertEqual(result_no_price, [None, "B"]) # Expect None for price

        # --- Test Case 4: API error (e.g., 404) ---
        mock_response_error = MagicMock()
        mock_response_error.raise_for_status.side_effect = requests.exceptions.HTTPError("Test HTTP Error")
        mock_requests_get.return_value = mock_response_error

        result_error = fetch_card_information("Test Card Error")
        self.assertIsNone(result_error)
        
        # --- Test Case 5: API returns unexpected JSON (e.g. 'prices' key missing) ---
        mock_response_bad_json = MagicMock()
        mock_response_bad_json.json.return_value = {"color_identity": ["W"]} # Missing 'prices'
        mock_response_bad_json.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response_bad_json

        result_bad_json = fetch_card_information("Test Card Bad JSON")
        self.assertEqual(result_bad_json, [None, "W"]) # Price is None, color may be found


    @patch('recognition.ocr_mvp.fetch_card_information')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.load_image_cv2')
    def test_process_image(self, mock_load_image, mock_extract_area, mock_extract_name, mock_fetch_info):
        dummy_path = "dummy/path/to/image.png"
        mock_corrector = MagicMock() # Dummy corrector for process_image

        # --- Test Case 1: Full successful processing ---
        mock_load_image.return_value = MagicMock(name="cv2_image_mock") # Dummy image object
        mock_extract_area.return_value = MagicMock(name="cropped_image_mock") # Dummy cropped image
        mock_extract_name.return_value = ("Raw OCR Text", "Corrected Card Name")
        mock_fetch_info.return_value = ["1.99", "B"]

        result = process_image(dummy_path, mock_corrector, show_gui=False)

        mock_load_image.assert_called_once_with(dummy_path)
        mock_extract_area.assert_called_once_with(mock_load_image.return_value)
        mock_extract_name.assert_called_once_with(mock_extract_area.return_value, mock_corrector)
        mock_fetch_info.assert_called_once_with("Corrected Card Name")
        
        expected_result = {
            "image_path": dummy_path,
            "ocr_name_raw": "Raw OCR Text",
            "card_name": "Corrected Card Name",
            "price": "1.99",
            "color_identity": "B"
        }
        self.assertEqual(result, expected_result)

        # Reset mocks for the next case
        mock_load_image.reset_mock()
        mock_extract_area.reset_mock()
        mock_extract_name.reset_mock()
        mock_fetch_info.reset_mock()

        # --- Test Case 2: No corrected card name found (ocr_corrected is empty) ---
        mock_load_image.return_value = MagicMock(name="cv2_image_mock_2")
        mock_extract_area.return_value = MagicMock(name="cropped_image_mock_2")
        mock_extract_name.return_value = ("Raw OCR Text Only", "") # Empty corrected name

        result_no_correction = process_image(dummy_path, mock_corrector, show_gui=False)

        mock_load_image.assert_called_once_with(dummy_path)
        mock_extract_area.assert_called_once_with(mock_load_image.return_value)
        mock_extract_name.assert_called_once_with(mock_extract_area.return_value, mock_corrector)
        
        mock_fetch_info.assert_not_called() # Crucial assertion

        expected_result_no_correction = {
            "image_path": dummy_path,
            "ocr_name_raw": "Raw OCR Text Only",
            "card_name": "",
            "price": None,
            "color_identity": None
        }
        self.assertEqual(result_no_correction, expected_result_no_correction)

        # --- Test Case 3: load_image_cv2 fails ---
        mock_load_image.reset_mock()
        mock_extract_area.reset_mock()
        mock_extract_name.reset_mock()
        mock_fetch_info.reset_mock()
        
        mock_load_image.side_effect = ValueError("Failed to load image")
        
        result_load_fail = process_image(dummy_path, mock_corrector, show_gui=False)
        
        expected_result_load_fail = {
            "image_path": dummy_path,
            "ocr_name_raw": None,
            "card_name": None,
            "price": None,
            "color_identity": None,
            "error": "Failed to load image"
        }
        self.assertEqual(result_load_fail, expected_result_load_fail)
        mock_load_image.assert_called_once_with(dummy_path)
        mock_extract_area.assert_not_called()
        mock_extract_name.assert_not_called()
        mock_fetch_info.assert_not_called()


if __name__ == '__main__':
    # This is to ensure that the TESSERACT_CMD_PATH in ocr_mvp.py
    # doesn't cause an immediate crash if tesseract isn't installed
    # when running this test file directly. Tests should mock out
    # pytesseract.image_to_string anyway.
    if 'recognition.ocr_mvp' in sys.modules:
        if hasattr(sys.modules['recognition.ocr_mvp'], 'pytesseract'):
            sys.modules['recognition.ocr_mvp'].pytesseract.tesseract_cmd = "mocked_tesseract_cmd_for_tests"
    
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
