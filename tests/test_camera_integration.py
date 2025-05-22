import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import os
import sys
import cv2 # Required for cv2.VideoCapture, cv2.imwrite, etc.
import time # Required for time.sleep
import numpy as np
from pathlib import Path

# Ensure the 'recognition' module can be imported
# This assumes 'tests' is a subdirectory of the project root, and 'recognition' is another subdirectory.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from recognition.ocr_mvp import capture_images_from_camera, main as ocr_main

class TestCameraIntegration(unittest.TestCase):

    def setUp(self):
        # Create a dummy NumPy array for a mock image frame
        self.mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Define the project root and the expected capture directory
        self.project_root = Path(__file__).resolve().parent.parent
        self.capture_dir_path = self.project_root / "captured_images"

    @patch('recognition.ocr_mvp.cv2.imwrite')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.os.makedirs')
    @patch('recognition.ocr_mvp.os.remove')
    @patch('recognition.ocr_mvp.Path.iterdir')
    @patch('recognition.ocr_mvp.Path.exists')
    @patch('recognition.ocr_mvp.cv2.VideoCapture')
    def test_capture_images_successful(self, mock_video_capture, mock_path_exists, mock_iterdir, mock_os_remove, mock_os_makedirs, mock_time_sleep, mock_cv2_imwrite):
        # --- Mocks Setup ---
        mock_camera_instance = MagicMock()
        mock_camera_instance.isOpened.return_value = True
        mock_camera_instance.read.return_value = (True, self.mock_frame)
        mock_video_capture.return_value = mock_camera_instance

        # Mock filesystem interactions
        mock_path_exists.return_value = False # Simulate directory doesn't exist initially
        mock_iterdir.return_value = [] # Simulate empty directory if it existed

        num_images = 3
        delay_seconds = 2

        # --- Call the function ---
        result_paths = capture_images_from_camera(num_images=num_images, delay_seconds=delay_seconds)

        # --- Assertions ---
        # Directory creation
        mock_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        
        # Camera operations
        mock_video_capture.assert_called_once_with(0)
        self.assertEqual(mock_camera_instance.read.call_count, num_images)
        mock_camera_instance.release.assert_called_once()

        # Image writing
        self.assertEqual(mock_cv2_imwrite.call_count, num_images)
        expected_paths = []
        for i in range(num_images):
            expected_filepath = self.capture_dir_path / f"capture_{i}.jpg"
            expected_paths.append(str(expected_filepath))
            # Check if cv2.imwrite was called with the correct path and frame
            # Note: cv2.imwrite expects a string path
            mock_cv2_imwrite.assert_any_call(str(expected_filepath), self.mock_frame)
        
        self.assertEqual(result_paths, expected_paths)

        # Time.sleep calls
        self.assertEqual(mock_time_sleep.call_count, num_images - 1)
        if num_images > 1:
            mock_time_sleep.assert_called_with(delay_seconds) # Checks the last call or any call if only one type

    @patch('recognition.ocr_mvp.cv2.VideoCapture')
    def test_capture_images_camera_init_failure(self, mock_video_capture):
        mock_camera_instance = MagicMock()
        mock_camera_instance.isOpened.return_value = False
        mock_video_capture.return_value = mock_camera_instance

        result_paths = capture_images_from_camera()

        mock_video_capture.assert_called_once_with(0)
        self.assertEqual(result_paths, [])
        # Ensure camera.release() is not called if it wasn't opened
        mock_camera_instance.release.assert_not_called()

    @patch('recognition.ocr_mvp.cv2.imwrite')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.os.makedirs')
    @patch('recognition.ocr_mvp.Path.exists')
    @patch('recognition.ocr_mvp.cv2.VideoCapture')
    def test_capture_images_frame_read_failure(self, mock_video_capture, mock_path_exists, mock_os_makedirs, mock_time_sleep, mock_cv2_imwrite):
        mock_camera_instance = MagicMock()
        mock_camera_instance.isOpened.return_value = True
        # Simulate failure on the second attempt to read
        mock_camera_instance.read.side_effect = [(True, self.mock_frame), (False, None), (True, self.mock_frame)]
        mock_video_capture.return_value = mock_camera_instance
        mock_path_exists.return_value = False # Directory doesn't exist

        num_images = 3
        delay_seconds = 1

        result_paths = capture_images_from_camera(num_images=num_images, delay_seconds=delay_seconds)

        mock_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        self.assertEqual(mock_camera_instance.read.call_count, num_images) # Still tries to read all
        mock_camera_instance.release.assert_called_once()

        # Should only write 2 images successfully
        self.assertEqual(mock_cv2_imwrite.call_count, 2)
        expected_paths = [
            str(self.capture_dir_path / "capture_0.jpg"),
            str(self.capture_dir_path / "capture_2.jpg") # Skips capture_1.jpg
        ]
        self.assertEqual(result_paths, expected_paths)
        
        # Sleep should be called for successful captures before the last one
        # Here, first capture is success, second fails, third is success.
        # Sleep after first, sleep after (non-existent successful) second.
        # It sleeps for (num_images - 1) times if all successful.
        # If a frame read fails, it continues to the next iteration, and if that's not the last image, it sleeps.
        # The current logic in capture_images_from_camera will sleep after a failed capture if it's not the last image.
        # In this test (3 images, 2nd fails):
        # 1. Capture 0 (success) -> sleep
        # 2. Capture 1 (fail) -> print error, loop continues
        # 3. Capture 2 (success) -> no sleep (last image)
        # So, sleep is called once.
        self.assertEqual(mock_time_sleep.call_count, 1) # Sleep after capture_0
        mock_time_sleep.assert_called_with(delay_seconds)


    @patch('recognition.ocr_mvp.process_image')
    @patch('recognition.ocr_mvp.capture_images_from_camera')
    @patch('recognition.ocr_mvp.CardNameCorrector') # Mock the corrector initialization
    @patch('recognition.ocr_mvp.pd.DataFrame.to_csv') # Mock CSV writing
    @patch('recognition.ocr_mvp.os.path.isdir') # Mock directory check for non-camera mode
    def test_ocr_main_with_camera_success(self, mock_isdir, mock_to_csv, mock_corrector, mock_capture_images, mock_process_image):
        mock_isdir.return_value = True # For the non-camera path, though not strictly needed if camera path is taken
        mock_capture_images.return_value = ["cam_img1.jpg", "cam_img2.jpg"]
        # Mock process_image to return a structure that main can handle
        mock_process_image.return_value = {
            "image_path": "dummy_path", "ocr_name_raw": "raw", "card_name": "corrected",
            "price": "1.0", "color_identity": "W", "error": None
        }
        # Mock CardNameCorrector instance
        mock_corrector_instance = MagicMock()
        mock_corrector.return_value = mock_corrector_instance

        ocr_main(use_camera=True, show_gui_flag=False, output_csv_file="dummy.csv", dict_path="dummy_dict.txt")

        mock_capture_images.assert_called_once()
        # Check calls to process_image
        expected_calls = [
            call("cam_img1.jpg", mock_corrector_instance, show_gui=False),
            call("cam_img2.jpg", mock_corrector_instance, show_gui=False)
        ]
        mock_process_image.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(mock_process_image.call_count, 2)
        mock_to_csv.assert_called_once() # Check that CSV writing is attempted

    @patch('recognition.ocr_mvp.process_image')
    @patch('recognition.ocr_mvp.capture_images_from_camera')
    @patch('recognition.ocr_mvp.CardNameCorrector')
    @patch('recognition.ocr_mvp.pd.DataFrame.to_csv')
    @patch('recognition.ocr_mvp.os.path.isdir')
    def test_ocr_main_with_camera_no_images_captured(self, mock_isdir, mock_to_csv, mock_corrector, mock_capture_images, mock_process_image):
        mock_isdir.return_value = True
        mock_capture_images.return_value = [] # Simulate no images captured
        mock_corrector_instance = MagicMock()
        mock_corrector.return_value = mock_corrector_instance

        ocr_main(use_camera=True, show_gui_flag=False, output_csv_file="dummy.csv", dict_path="dummy_dict.txt")

        mock_capture_images.assert_called_once()
        mock_process_image.assert_not_called()
        mock_to_csv.assert_not_called() # No data to write

    # Test for directory clearing
    @patch('recognition.ocr_mvp.cv2.imwrite')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.os.makedirs')
    @patch('recognition.ocr_mvp.os.remove')
    @patch('recognition.ocr_mvp.Path.iterdir')
    @patch('recognition.ocr_mvp.Path.exists')
    @patch('recognition.ocr_mvp.cv2.VideoCapture')
    def test_capture_images_clears_existing_directory(self, mock_video_capture, mock_path_exists, mock_iterdir, mock_os_remove, mock_os_makedirs, mock_time_sleep, mock_cv2_imwrite):
        mock_camera_instance = MagicMock()
        mock_camera_instance.isOpened.return_value = True
        mock_camera_instance.read.return_value = (True, self.mock_frame)
        mock_video_capture.return_value = mock_camera_instance

        mock_path_exists.return_value = True # Simulate directory *does* exist

        # Simulate existing files in the directory
        mock_file_item = MagicMock(spec=Path)
        mock_file_item.is_file.return_value = True
        mock_file_item.name = "old_capture.jpg" 
        
        mock_dir_item = MagicMock(spec=Path) # Should not be removed by current logic
        mock_dir_item.is_file.return_value = False

        mock_iterdir.return_value = [mock_file_item, mock_dir_item]

        num_images = 1
        capture_images_from_camera(num_images=num_images, delay_seconds=1)

        # Check that os.makedirs was called (it will be, with exist_ok=True)
        mock_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        
        # Check that iterdir was called to list files
        mock_iterdir.assert_called_once()
        
        # Check that os.remove was called for the file item
        mock_os_remove.assert_called_once_with(mock_file_item)
        
        # Ensure cv2.imwrite is still called for new images
        self.assertEqual(mock_cv2_imwrite.call_count, num_images)


if __name__ == '__main__':
    unittest.main()
