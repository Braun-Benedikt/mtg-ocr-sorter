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

    # Note: The original test_fetch_card_information has been removed as per plan.
    # New tests for fetch_card_information will be added at the module level (pytest style).

    @patch('recognition.ocr_mvp.fetch_card_information')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.load_image_cv2')
    @patch('recognition.ocr_mvp.cv2.rotate') # Added mock for cv2.rotate
    def test_process_image(self, mock_cv2_rotate, mock_load_image, mock_extract_area, mock_extract_name, mock_fetch_info): # Added mock_cv2_rotate to params
        dummy_path = "dummy/path/to/image.png"
        mock_corrector = MagicMock() # Dummy corrector for process_image

        # --- Test Case 1: Full successful processing ---
        mock_loaded_image = MagicMock(name="cv2_image_mock")
        mock_load_image.return_value = mock_loaded_image

        mock_rotated_image = MagicMock(name="rotated_image_mock") # Mock for the rotated image
        mock_cv2_rotate.return_value = mock_rotated_image # cv2.rotate will return this

        mock_extract_area.return_value = MagicMock(name="cropped_image_mock") # Dummy cropped image
        mock_extract_name.return_value = ("Raw OCR Text", "Corrected Card Name")
        mock_fetch_info.return_value = {"price": "1.99", "color_identity": "B", "cmc": 1.0, "type_line": "Artifact", "image_uri": "uri"} # Match new return type

        # The function being tested is process_image_to_db, not process_image
        # Need to adjust the import and call if the test is for process_image_to_db
        # Assuming the test is for a function named 'process_image' as per the original test code
        # If it's for process_image_to_db, the structure of the returned dict is different.
        # For now, sticking to 'process_image' and its expected dict structure.
        # Let's assume the function signature is process_image(image_path, corrector, show_gui)
        # and it returns a dict like:
        # {"image_path": ..., "ocr_name_raw": ..., "card_name": ..., "price": ..., "color_identity": ...}
        #
        # This test targets `process_image_to_db`.
        from recognition.ocr_mvp import process_image_to_db # Import here to use the actual function

        # Mocking add_card which is called by process_image_to_db
        with patch('recognition.ocr_mvp.add_card') as mock_add_card:
            mock_add_card.return_value = 123 # Dummy card ID for the created card

            result = process_image_to_db(dummy_path, mock_corrector, show_gui=False)

            # Assertions for Case 1: Full successful processing
            mock_load_image.assert_called_once_with(dummy_path)
            mock_cv2_rotate.assert_called_once_with(mock_loaded_image, cv2.ROTATE_90_CLOCKWISE)
            mock_extract_area.assert_called_once_with(mock_rotated_image)
            mock_extract_name.assert_called_once_with(mock_extract_area.return_value, mock_corrector)
            mock_fetch_info.assert_called_once_with("Corrected Card Name")
            mock_add_card.assert_called_once_with(
                name="Corrected Card Name",
                ocr_name_raw="Raw OCR Text",
                price="1.99",
                color_identity="B",
                image_path=dummy_path,
                cmc=1.0,
                type_line="Artifact",
                image_uri="uri"
            )
        
            expected_result = {
                "id": 123,
                "name": "Corrected Card Name",
                "ocr_name_raw": "Raw OCR Text",
                "price": "1.99",
                "color_identity": "B",
                "image_path": dummy_path,
                "cmc": 1.0,
                "type_line": "Artifact",
                "image_uri": "uri"
            }
            self.assertEqual(result, expected_result)

        # Reset mocks for the next case
        mock_load_image.reset_mock()
        mock_cv2_rotate.reset_mock()
        mock_extract_area.reset_mock()
        mock_extract_name.reset_mock()
        mock_fetch_info.reset_mock()
        # mock_add_card is reset by exiting the 'with' block

        # --- Test Case 2: No corrected card name found (ocr_corrected is empty) ---
        # Re-setup mocks for this specific path
        mock_loaded_image_case2 = MagicMock(name="cv2_image_mock_2")
        mock_load_image.return_value = mock_loaded_image_case2

        mock_rotated_image_case2 = MagicMock(name="rotated_image_mock_2")
        mock_cv2_rotate.return_value = mock_rotated_image_case2

        mock_extract_area.return_value = MagicMock(name="cropped_image_mock_2")
        mock_extract_name.return_value = ("Raw OCR Text Only", "") # Empty corrected name

        with patch('recognition.ocr_mvp.add_card') as mock_add_card_2:
            result_no_correction = process_image_to_db(dummy_path, mock_corrector, show_gui=False)

            mock_load_image.assert_called_once_with(dummy_path)
            mock_cv2_rotate.assert_called_once_with(mock_loaded_image_case2, cv2.ROTATE_90_CLOCKWISE)
            mock_extract_area.assert_called_once_with(mock_rotated_image_case2)
            mock_extract_name.assert_called_once_with(mock_extract_area.return_value, mock_corrector)

            mock_fetch_info.assert_not_called()
            mock_add_card_2.assert_not_called() # add_card should not be called

        self.assertIsNone(result_no_correction) # process_image_to_db returns None if no corrected name

        # Reset mocks for the next case
        mock_load_image.reset_mock()
        mock_cv2_rotate.reset_mock()
        mock_extract_area.reset_mock()
        mock_extract_name.reset_mock()
        mock_fetch_info.reset_mock()

        # --- Test Case 3: load_image_cv2 returns None (simulating load failure) ---
        mock_load_image.return_value = None # Simulate load_image_cv2 returning None
        
        # No need to patch add_card here as it won't be reached
        result_load_fail = process_image_to_db(dummy_path, mock_corrector, show_gui=False)
        
        self.assertIsNone(result_load_fail) # Expect None if image loading fails

        mock_load_image.assert_called_once_with(dummy_path)
        mock_cv2_rotate.assert_not_called() # Rotate should not be called if load fails
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


# --- New Pytest-style tests for fetch_card_information ---
import pytest # Optional: if using pytest fixtures or markers

@patch('recognition.ocr_mvp.requests.get')
def test_fetch_card_information_success(mock_get):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "Sol Ring",
        "cmc": 1.0,
        "type_line": "Artifact",
        "color_identity": ["C"],
        "prices": {"usd": "1.50", "eur": "1.20"},
        "image_uris": {"normal": "https://example.com/sol_ring.jpg"}
    }
    mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise for success
    mock_get.return_value = mock_response

    card_info = fetch_card_information("Sol Ring")

    assert card_info is not None
    assert card_info["price"] == "1.20" # Assuming EUR is preferred by the function
    assert card_info["color_identity"] == "C"
    assert card_info["cmc"] == 1.0
    assert card_info["type_line"] == "Artifact"
    assert card_info["image_uri"] == "https://example.com/sol_ring.jpg"
    # The function in ocr_mvp.py uses a timeout, so we should expect it in the call.
    mock_get.assert_called_once_with("https://api.scryfall.com/cards/named?exact=Sol Ring", timeout=10)

@patch('recognition.ocr_mvp.requests.get')
def test_fetch_card_information_api_error(mock_get):
    # We need requests.exceptions.RequestException for this test
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("API down")

    card_info = fetch_card_information("Unknown Card")
    assert card_info is None

@patch('recognition.ocr_mvp.requests.get')
def test_fetch_card_information_missing_fields(mock_get):
    # Test behavior when some fields are missing from Scryfall response
    mock_response = MagicMock()
    mock_response.json.return_value = { # Missing cmc, type_line, image_uris
        "name": "Test Card",
        "color_identity": ["W"],
        "prices": {"usd": "0.10"} # EUR is missing, USD should be used
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    card_info = fetch_card_information("Test Card")

    assert card_info is not None
    assert card_info["price"] == "0.10" # USD fallback
    assert card_info["color_identity"] == "W" # Should still get color
    assert card_info["cmc"] == 0.0 # Default value
    assert card_info["type_line"] == "" # Default value
    assert card_info["image_uri"] == "" # Default value
    mock_get.assert_called_once_with("https://api.scryfall.com/cards/named?exact=Test Card", timeout=10)
