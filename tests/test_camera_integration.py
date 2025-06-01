import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import os
import sys
import subprocess  # For mocking subprocess.run
import time  # Required for time.sleep
import numpy as np  # Still potentially used by process_image or its dependencies
from pathlib import Path
import pandas as pd  # For checking DataFrame creation / CSV writing

# Ensure the 'recognition' module can be imported
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from recognition.ocr_mvp import capture_images_from_camera, main as ocr_main


class TestCameraIntegration(unittest.TestCase):

    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.capture_dir_path = self.project_root / "captured_images"
        self.expected_image_path = str(self.capture_dir_path / "current_capture.jpg")

    @patch('recognition.ocr_mvp.subprocess.run')
    @patch('recognition.ocr_mvp.os.makedirs')
    @patch('recognition.ocr_mvp.Path.exists')  # Though os.makedirs has exist_ok=True, explicit check might be there
    def test_capture_images_successful(self, mock_path_exists, mock_os_makedirs, mock_subprocess_run):
        # --- Mocks Setup ---
        mock_subprocess_run.return_value = MagicMock(check=True, stdout="Captured", stderr="")
        # Simulate directory might or might not exist, os.makedirs handles it
        mock_path_exists.return_value = False  # Let's say it doesn't exist for this test

        # --- Call the function ---
        result_path = capture_images_from_camera()

        # --- Assertions ---
        # Directory creation (os.makedirs in ocr_mvp.py creates the capture_dir directly)
        mock_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)

        # Subprocess call for libcamera-still
        expected_command = ['libcamera-still', '-o', self.expected_image_path, '--nopreview']
        mock_subprocess_run.assert_called_once_with(expected_command, check=True, capture_output=True, text=True)

        self.assertEqual(result_path, self.expected_image_path)

    @patch('recognition.ocr_mvp.subprocess.run')
    @patch('recognition.ocr_mvp.os.makedirs')
    def test_capture_images_libcamera_failure(self, mock_os_makedirs, mock_subprocess_run):
        # Test FileNotFoundError
        mock_subprocess_run.side_effect = FileNotFoundError("libcamera-still not found")
        result_path_not_found = capture_images_from_camera()
        self.assertIsNone(result_path_not_found)
        mock_os_makedirs.assert_called_with(self.capture_dir_path, exist_ok=True)  # Called once for this attempt

        # Reset side_effect for next test case
        mock_subprocess_run.side_effect = None

        # Test CalledProcessError
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="Error")
        result_path_called_error = capture_images_from_camera()
        self.assertIsNone(result_path_called_error)
        mock_os_makedirs.assert_called_with(self.capture_dir_path, exist_ok=True)  # Called again for this attempt
        self.assertEqual(mock_os_makedirs.call_count, 2)

    # Tests for ocr_main (main function in ocr_mvp.py)
    @patch('recognition.ocr_mvp.pd.DataFrame')  # Mock DataFrame to check its creation and to_csv
    @patch('recognition.ocr_mvp.CardNameCorrector')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.process_image')
    @patch('recognition.ocr_mvp.capture_images_from_camera')  # Mock the function within ocr_mvp's scope
    @patch('recognition.ocr_mvp.os.remove')
    @patch('recognition.ocr_mvp.Path.iterdir')
    @patch('recognition.ocr_mvp.Path.exists')  # For directory clearing in ocr_main
    @patch('recognition.ocr_mvp.os.makedirs')  # For directory clearing/creation in ocr_main
    def test_ocr_main_with_camera_success_and_stops_on_no_card_name(
            self, mock_main_os_makedirs, mock_main_path_exists, mock_main_iterdir, mock_main_os_remove,
            mock_capture_from_camera_func, mock_process_image_func, mock_time_sleep,
            mock_card_name_corrector, mock_pd_dataframe
    ):
        # --- Mocks Setup for ocr_main ---
        mock_card_name_corrector.return_value = MagicMock()  # Corrector instance

        # Simulate directory clearing
        mock_main_path_exists.return_value = True  # Directory exists
        mock_file_item = MagicMock(spec=Path)
        mock_file_item.is_file.return_value = True
        mock_file_item.name = "old_image.jpg"
        mock_main_iterdir.return_value = [mock_file_item]  # One file to remove

        # Simulate sequence of captures and processing
        path1 = str(self.capture_dir_path / "current_capture_1.jpg")  # Use different paths for clarity if needed
        path2 = str(self.capture_dir_path / "current_capture_2.jpg")
        path3 = str(self.capture_dir_path / "current_capture_3.jpg")

        mock_capture_from_camera_func.side_effect = [path1, path2, path3]

        data_card_A = {"card_name": "Card A", "price": "1.00", "error": None, "image_path": path1}
        data_card_B = {"card_name": "Card B", "price": "2.00", "error": None, "image_path": path2}
        data_no_card = {"card_name": None, "price": None, "error": None, "image_path": path3}  # Stops the loop
        mock_process_image_func.side_effect = [data_card_A, data_card_B, data_no_card]

        mock_df_instance = MagicMock()
        mock_pd_dataframe.return_value = mock_df_instance

        # --- Call ocr_main ---
        ocr_main(use_camera=True, show_gui_flag=False, output_csv_file="test_output.csv", dict_path="dummy_dict.txt")

        # --- Assertions for ocr_main ---
        # Directory creation/clearing by ocr_main
        mock_main_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        mock_main_path_exists.assert_called_once_with(self.capture_dir_path)  # Check if dir exists
        mock_main_iterdir.assert_called_once()  # To list files for removal
        mock_main_os_remove.assert_called_once_with(mock_file_item)  # Removal of the old file

        # Camera and processing calls
        self.assertEqual(mock_capture_from_camera_func.call_count, 3)
        self.assertEqual(mock_process_image_func.call_count, 3)
        mock_process_image_func.assert_has_calls([
            call(path1, mock_card_name_corrector.return_value, show_gui=False),
            call(path2, mock_card_name_corrector.return_value, show_gui=False),
            call(path3, mock_card_name_corrector.return_value, show_gui=False)
        ])

        # time.sleep calls (after 1st and 2nd successful card name recognition)
        self.assertEqual(mock_time_sleep.call_count, 2)
        mock_time_sleep.assert_called_with(1)

        # CSV Writing
        mock_pd_dataframe.assert_called_once_with([data_card_A, data_card_B, data_no_card])  # all data is passed
        mock_df_instance.to_csv.assert_called_once_with("test_output.csv", index=False)

    @patch('recognition.ocr_mvp.pd.DataFrame.to_csv')
    @patch('recognition.ocr_mvp.CardNameCorrector')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.process_image')
    @patch('recognition.ocr_mvp.capture_images_from_camera')
    @patch('recognition.ocr_mvp.os.remove')
    @patch('recognition.ocr_mvp.Path.iterdir')
    @patch('recognition.ocr_mvp.Path.exists')
    @patch('recognition.ocr_mvp.os.makedirs')
    def test_ocr_main_with_camera_capture_fails_immediately(
            self, mock_main_os_makedirs, mock_main_path_exists, mock_main_iterdir, mock_main_os_remove,
            mock_capture_from_camera_func, mock_process_image_func, mock_time_sleep,
            mock_card_name_corrector, mock_to_csv
    ):
        mock_card_name_corrector.return_value = MagicMock()
        mock_main_path_exists.return_value = False  # Dir doesn't exist initially
        mock_capture_from_camera_func.return_value = None  # Simulate immediate capture failure

        ocr_main(use_camera=True, show_gui_flag=False, output_csv_file="test_output.csv")

        mock_main_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        mock_main_path_exists.assert_called_once_with(self.capture_dir_path)  # Checked once
        # iterdir and remove should not be called if path_exists was false or if it was true but empty.
        # If it was true and not empty, they would be called. Let's assume empty for simplicity or non-existent.
        # For this test, what matters is behavior *after* clearing.

        mock_capture_from_camera_func.assert_called_once()
        mock_process_image_func.assert_not_called()
        mock_time_sleep.assert_not_called()
        mock_to_csv.assert_not_called()  # No data to write

    @patch('recognition.ocr_mvp.pd.DataFrame')
    @patch('recognition.ocr_mvp.CardNameCorrector')
    @patch('recognition.ocr_mvp.time.sleep')
    @patch('recognition.ocr_mvp.process_image')
    @patch('recognition.ocr_mvp.capture_images_from_camera')
    @patch('recognition.ocr_mvp.os.remove')  # Mocks for directory clearing
    @patch('recognition.ocr_mvp.Path.iterdir')
    @patch('recognition.ocr_mvp.Path.exists')
    @patch('recognition.ocr_mvp.os.makedirs')
    def test_ocr_main_stops_on_process_image_error(
            self, mock_main_os_makedirs, mock_main_path_exists, mock_main_iterdir, mock_main_os_remove,
            mock_capture_from_camera_func, mock_process_image_func, mock_time_sleep,
            mock_card_name_corrector, mock_pd_dataframe
    ):
        mock_card_name_corrector.return_value = MagicMock()
        mock_main_path_exists.return_value = True
        mock_main_iterdir.return_value = []  # Empty dir

        captured_path = str(self.capture_dir_path / "current_capture_err.jpg")
        mock_capture_from_camera_func.return_value = captured_path

        # Simulate process_image returning an error
        error_data = {"error": "Major processing failure", "card_name": None, "image_path": captured_path}
        mock_process_image_func.return_value = error_data

        mock_df_instance = MagicMock()
        mock_pd_dataframe.return_value = mock_df_instance

        ocr_main(use_camera=True, show_gui_flag=False, output_csv_file="error_output.csv")

        mock_main_os_makedirs.assert_called_once_with(self.capture_dir_path, exist_ok=True)
        mock_capture_from_camera_func.assert_called_once()
        mock_process_image_func.assert_called_once_with(captured_path, mock_card_name_corrector.return_value,
                                                        show_gui=False)

        # Loop should break due to data.get("error") being true
        mock_time_sleep.assert_not_called()

        # Data with error IS appended and written to CSV
        mock_pd_dataframe.assert_called_once_with([error_data])
        mock_df_instance.to_csv.assert_called_once_with("error_output.csv", index=False)


if __name__ == '__main__':
    unittest.main()
