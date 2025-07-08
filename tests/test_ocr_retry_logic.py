import unittest
from unittest.mock import patch, call, MagicMock
import numpy as np
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from recognition and web_app
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import the module to be tested
from recognition import ocr_mvp

# Define a dummy CardNameCorrector for tests
class DummyCorrector:
    def __init__(self, dictionary_path=None):
        pass # No actual dictionary loading needed for these tests

    def correct(self, text: str) -> str:
        # Simple mock: if text is "Raw Correct", return "Corrected Card"
        if "Raw Correct" in text:
            return "Corrected Card"
        return "" # Default to no correction

# Keep a reference to original global crop ratios for restoration/comparison
ORIGINAL_CROP_RATIO_WIDTH_START = ocr_mvp.CROP_RATIO_WIDTH_START
ORIGINAL_CROP_RATIO_WIDTH_END = ocr_mvp.CROP_RATIO_WIDTH_END

class TestOCRRetryLogic(unittest.TestCase):

    def setUp(self):
        # Reset global crop ratios before each test to ensure independence
        ocr_mvp.CROP_RATIO_WIDTH_START = ORIGINAL_CROP_RATIO_WIDTH_START
        ocr_mvp.CROP_RATIO_WIDTH_END = ORIGINAL_CROP_RATIO_WIDTH_END

        # Mock image for processing
        self.mock_image_cv = np.zeros((100, 100, 3), dtype=np.uint8) # 100x100 dummy image
        self.mock_image_path = "dummy/path/to/image.jpg"
        self.dummy_corrector = DummyCorrector()

    def tearDown(self):
        # Restore original crop ratios after each test
        ocr_mvp.CROP_RATIO_WIDTH_START = ORIGINAL_CROP_RATIO_WIDTH_START
        ocr_mvp.CROP_RATIO_WIDTH_END = ORIGINAL_CROP_RATIO_WIDTH_END

    @patch('recognition.ocr_mvp.load_image_cv2')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.add_card')
    @patch('recognition.ocr_mvp.fetch_card_information')
    def test_success_on_first_try(self, mock_fetch_info, mock_add_card, mock_extract_name, mock_extract_area, mock_load_image):
        mock_load_image.return_value = self.mock_image_cv
        # First crop area (modifier 0.0)
        mock_crop_area_attempt1 = np.zeros((10, 30, 3), dtype=np.uint8) # Dummy cropped image
        mock_extract_area.return_value = mock_crop_area_attempt1
        mock_extract_name.return_value = ("Raw Text", "Corrected Card") # Success on first try
        mock_add_card.return_value = 1 # Dummy card ID
        mock_fetch_info.return_value = {"price": 1.0, "color_identity": "W", "cmc": 1.0, "type_line":"Creature", "image_uri":""}

        result = ocr_mvp.process_image_to_db(self.mock_image_path, self.dummy_corrector)

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Corrected Card")
        mock_load_image.assert_called_once_with(self.mock_image_path)
        # Check that extract_card_name_area was called for the first attempt
        mock_extract_area.assert_called_once_with(self.mock_image_cv, width_modifier_factor=0.0)
        # Check that extract_card_name was called with the crop from the first attempt
        mock_extract_name.assert_called_once_with(mock_crop_area_attempt1, self.dummy_corrector)
        mock_add_card.assert_called_once()
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_START, ORIGINAL_CROP_RATIO_WIDTH_START)
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_END, ORIGINAL_CROP_RATIO_WIDTH_END)

    @patch('recognition.ocr_mvp.load_image_cv2')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.add_card')
    @patch('recognition.ocr_mvp.fetch_card_information')
    def test_success_on_third_try(self, mock_fetch_info, mock_add_card, mock_extract_name, mock_extract_area, mock_load_image):
        mock_load_image.return_value = self.mock_image_cv

        # Define distinct crop areas for each attempt to ensure correct one is passed
        mock_crop_area_attempt1 = np.zeros((10, 30, 3), dtype=np.uint8) # For modifier 0.0
        mock_crop_area_attempt2 = np.zeros((10, 32, 3), dtype=np.uint8) # For modifier 0.02
        mock_crop_area_attempt3 = np.zeros((10, 34, 3), dtype=np.uint8) # For modifier 0.04

        mock_extract_area.side_effect = [
            mock_crop_area_attempt1,
            mock_crop_area_attempt2,
            mock_crop_area_attempt3
        ]
        mock_extract_name.side_effect = [
            ("Raw Fail 1", ""),       # Attempt 1 (modifier 0.0) - fails
            ("Raw Fail 2", ""),       # Attempt 2 (modifier 0.02) - fails
            ("Raw Success", "Corrected Card") # Attempt 3 (modifier 0.04) - succeeds
        ]
        mock_add_card.return_value = 1
        mock_fetch_info.return_value = {"price": 1.0, "color_identity": "U", "cmc": 2.0, "type_line":"Instant", "image_uri":""}

        result = ocr_mvp.process_image_to_db(self.mock_image_path, self.dummy_corrector)

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Corrected Card")
        self.assertEqual(mock_extract_area.call_count, 3)
        self.assertEqual(mock_extract_name.call_count, 3)

        expected_area_calls = [
            call(self.mock_image_cv, width_modifier_factor=0.0),
            call(self.mock_image_cv, width_modifier_factor=0.02),
            call(self.mock_image_cv, width_modifier_factor=0.04)
        ]
        mock_extract_area.assert_has_calls(expected_area_calls)

        expected_name_calls = [
            call(mock_crop_area_attempt1, self.dummy_corrector),
            call(mock_crop_area_attempt2, self.dummy_corrector),
            call(mock_crop_area_attempt3, self.dummy_corrector)
        ]
        mock_extract_name.assert_has_calls(expected_name_calls)

        mock_add_card.assert_called_once()
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_START, ORIGINAL_CROP_RATIO_WIDTH_START)
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_END, ORIGINAL_CROP_RATIO_WIDTH_END)

    @patch('recognition.ocr_mvp.load_image_cv2')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.add_card')
    @patch('recognition.ocr_mvp.fetch_card_information')
    def test_failure_on_all_retries(self, mock_fetch_info, mock_add_card, mock_extract_name, mock_extract_area, mock_load_image):
        mock_load_image.return_value = self.mock_image_cv

        # All attempts return an empty crop or an uncorrectable name
        mock_generic_crop_area = np.zeros((10,30,3), dtype=np.uint8)
        mock_extract_area.return_value = mock_generic_crop_area # Same crop for all for simplicity
        mock_extract_name.return_value = ("Raw Gibberish", "") # Always fails to correct

        result = ocr_mvp.process_image_to_db(self.mock_image_path, self.dummy_corrector)

        self.assertIsNone(result) # Should return None as no card identified
        self.assertEqual(mock_extract_area.call_count, 5) # All 5 modifiers attempted
        self.assertEqual(mock_extract_name.call_count, 5)

        width_modifier_factors = [0.0, 0.02, 0.04, -0.02, -0.04]
        expected_area_calls = [call(self.mock_image_cv, width_modifier_factor=mod) for mod in width_modifier_factors]
        mock_extract_area.assert_has_calls(expected_area_calls)

        mock_add_card.assert_not_called() # No card should be added
        mock_fetch_info.assert_not_called()
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_START, ORIGINAL_CROP_RATIO_WIDTH_START)
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_END, ORIGINAL_CROP_RATIO_WIDTH_END)

    @patch('recognition.ocr_mvp.load_image_cv2')
    @patch('recognition.ocr_mvp.extract_card_name_area')
    @patch('recognition.ocr_mvp.extract_card_name')
    @patch('recognition.ocr_mvp.add_card')
    @patch('recognition.ocr_mvp.fetch_card_information')
    def test_empty_crop_on_an_attempt(self, mock_fetch_info, mock_add_card, mock_extract_name, mock_extract_area, mock_load_image):
        mock_load_image.return_value = self.mock_image_cv

        mock_crop_area_attempt1 = np.zeros((10, 30, 3), dtype=np.uint8)
        mock_empty_crop_area_attempt2 = np.zeros((0, 0, 3), dtype=np.uint8) # Empty crop
        mock_crop_area_attempt3 = np.zeros((10, 34, 3), dtype=np.uint8)

        mock_extract_area.side_effect = [
            mock_crop_area_attempt1,
            mock_empty_crop_area_attempt2, # This attempt will result in an empty crop
            mock_crop_area_attempt3
        ]
        mock_extract_name.side_effect = [
            ("Raw Fail 1", ""), # Attempt 1 (modifier 0.0) - fails
            # extract_card_name should not be called for attempt 2 due to empty crop
            ("Raw Success", "Corrected Card") # Attempt 3 (modifier 0.04) - succeeds
        ]
        mock_add_card.return_value = 1
        mock_fetch_info.return_value = {"price": 0.5, "color_identity": "B", "cmc": 3.0, "type_line":"Sorcery", "image_uri":""}

        result = ocr_mvp.process_image_to_db(self.mock_image_path, self.dummy_corrector)

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Corrected Card")

        # extract_card_name_area is called 3 times
        self.assertEqual(mock_extract_area.call_count, 3)
        expected_area_calls = [
            call(self.mock_image_cv, width_modifier_factor=0.0),
            call(self.mock_image_cv, width_modifier_factor=0.02), # This one returns empty crop
            call(self.mock_image_cv, width_modifier_factor=0.04)
        ]
        mock_extract_area.assert_has_calls(expected_area_calls)

        # extract_card_name is called only twice (skips the one with empty crop)
        self.assertEqual(mock_extract_name.call_count, 2)
        expected_name_calls = [
            call(mock_crop_area_attempt1, self.dummy_corrector),
            # No call for the empty crop from attempt 2
            call(mock_crop_area_attempt3, self.dummy_corrector)
        ]
        mock_extract_name.assert_has_calls(expected_name_calls)

        mock_add_card.assert_called_once()
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_START, ORIGINAL_CROP_RATIO_WIDTH_START)
        self.assertEqual(ocr_mvp.CROP_RATIO_WIDTH_END, ORIGINAL_CROP_RATIO_WIDTH_END)

    def test_extract_card_name_area_width_modification(self):
        # Test the extract_card_name_area directly for width modification logic
        # Using actual global constants for this test, but they are reset in setUp/tearDown
        # For this test, we assume CROP_RATIO_WIDTH_START = 0.32 and CROP_RATIO_WIDTH_END = 0.60
        # Original width ratio = 0.60 - 0.32 = 0.28

        image = np.zeros((100, 200, 3), dtype=np.uint8) # H=100, W=200

        # Case 1: No modifier
        cropped_img_no_mod = ocr_mvp.extract_card_name_area(image, width_modifier_factor=0.0)
        expected_w_start_no_mod = int(200 * ocr_mvp.CROP_RATIO_WIDTH_START) # 200 * 0.32 = 64
        expected_w_end_no_mod = int(200 * ocr_mvp.CROP_RATIO_WIDTH_END)     # 200 * 0.60 = 120
        self.assertEqual(cropped_img_no_mod.shape[1], expected_w_end_no_mod - expected_w_start_no_mod) # Expected width 56

        # Case 2: Positive modifier (e.g., 0.1 = 10% wider)
        # Original width = 0.28. Change = 0.28 * 0.1 = 0.028
        # New wr_start = 0.32 - 0.014 = 0.306
        # New wr_end = 0.60 + 0.014 = 0.614
        cropped_img_pos_mod = ocr_mvp.extract_card_name_area(image, width_modifier_factor=0.1)
        expected_w_start_pos_mod = int(200 * (ocr_mvp.CROP_RATIO_WIDTH_START - ( (ocr_mvp.CROP_RATIO_WIDTH_END - ocr_mvp.CROP_RATIO_WIDTH_START) * 0.1 / 2.0)))
        expected_w_end_pos_mod = int(200 * (ocr_mvp.CROP_RATIO_WIDTH_END + ( (ocr_mvp.CROP_RATIO_WIDTH_END - ocr_mvp.CROP_RATIO_WIDTH_START) * 0.1 / 2.0)))
        actual_width_pos_mod = cropped_img_pos_mod.shape[1]
        # Check within a small tolerance due to int conversion
        self.assertAlmostEqual(actual_width_pos_mod, expected_w_end_pos_mod - expected_w_start_pos_mod, delta=1)


        # Case 3: Negative modifier (e.g., -0.1 = 10% narrower)
        # Original width = 0.28. Change = 0.28 * -0.1 = -0.028
        # New wr_start = 0.32 - (-0.014) = 0.334
        # New wr_end = 0.60 + (-0.014) = 0.586
        cropped_img_neg_mod = ocr_mvp.extract_card_name_area(image, width_modifier_factor=-0.1)
        expected_w_start_neg_mod = int(200 * (ocr_mvp.CROP_RATIO_WIDTH_START - ( (ocr_mvp.CROP_RATIO_WIDTH_END - ocr_mvp.CROP_RATIO_WIDTH_START) * -0.1 / 2.0)))
        expected_w_end_neg_mod = int(200 * (ocr_mvp.CROP_RATIO_WIDTH_END + ( (ocr_mvp.CROP_RATIO_WIDTH_END - ocr_mvp.CROP_RATIO_WIDTH_START) * -0.1 / 2.0)))
        actual_width_neg_mod = cropped_img_neg_mod.shape[1]
        self.assertAlmostEqual(actual_width_neg_mod, expected_w_end_neg_mod - expected_w_start_neg_mod, delta=1)

        # Case 4: Modifier large enough to hit clamp (e.g. -2.0 makes it very small, should clamp at 0 width or fallback)
        # The implementation has a fallback if _wr_start >= _wr_end. Let's test that.
        # If CROP_RATIO_WIDTH_START = 0.32, CROP_RATIO_WIDTH_END = 0.60
        # A modifier of -3.0 would make width_change_ratio = 0.28 * -3.0 = -0.84
        # new_wr_start = 0.32 - (-0.84/2) = 0.32 + 0.42 = 0.74
        # new_wr_end = 0.60 + (-0.84/2) = 0.60 - 0.42 = 0.18
        # Here new_wr_start (0.74) > new_wr_end (0.18), so it should fallback to original width.
        with patch('builtins.print') as mock_print: # To capture the warning
            cropped_img_fallback = ocr_mvp.extract_card_name_area(image, width_modifier_factor=-3.0)
            self.assertEqual(cropped_img_fallback.shape[1], expected_w_end_no_mod - expected_w_start_no_mod) # Should be original width
            mock_print.assert_any_call("Warning: width_modifier_factor -3.0 resulted in invalid crop ratios. Using original width.")


if __name__ == '__main__':
    unittest.main()
