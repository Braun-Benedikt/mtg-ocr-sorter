import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path to allow importing from recognition
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the module itself to access its global variables directly
import recognition.ocr_mvp as ocr_mvp

print("--- Test Script: Initial Hardcoded Default Crop Ratios (from module load) ---")
print(f"Initial HS: {ocr_mvp.CROP_RATIO_HEIGHT_START:.4f}")
print(f"Initial HE: {ocr_mvp.CROP_RATIO_HEIGHT_END:.4f}")
print(f"Initial WS: {ocr_mvp.CROP_RATIO_WIDTH_START:.4f}")
print(f"Initial WE: {ocr_mvp.CROP_RATIO_WIDTH_END:.4f}")

# Create a dummy image
dummy_image_height = 200  # Using a different dimension for clarity
dummy_image_width = 300
dummy_image = np.zeros((dummy_image_height, dummy_image_width, 3), dtype=np.uint8)
print(f"\nUsing dummy image of shape: ({dummy_image_height}, {dummy_image_width}, 3)")

# --- Test 1: Crop with initial global ratios ---
print("\n--- Test Script: Cropping with initial global ratios (implicit) ---")
cropped_before_setup = ocr_mvp.extract_card_name_area(dummy_image)
shape_before = cropped_before_setup.shape
print(f"Shape of cropped image BEFORE setup: {shape_before}")

# Calculate expected shape with initial ratios
expected_h_before = int(dummy_image_height * (ocr_mvp.CROP_RATIO_HEIGHT_END - ocr_mvp.CROP_RATIO_HEIGHT_START))
expected_w_before = int(dummy_image_width * (ocr_mvp.CROP_RATIO_WIDTH_END - ocr_mvp.CROP_RATIO_WIDTH_START))
print(f"Expected shape BEFORE: ({expected_h_before}, {expected_w_before}, 3)")

if shape_before[0] == expected_h_before and shape_before[1] == expected_w_before:
    print("SUCCESS: Crop shape BEFORE setup is consistent with initial global ratios.")
else:
    print("FAILURE: Crop shape BEFORE setup is NOT consistent.")


# --- Test 2: Call setup_crop_interactively (modified test version) ---
print("\n--- Test Script: Calling setup_crop_interactively (test version) ---")
ocr_mvp.setup_crop_interactively() # This will print its own messages
print("--- Test Script: Returned from setup_crop_interactively ---\n")

# --- Test 3: Verify global variables updated ---
print("--- Test Script: Verifying updated global crop ratios in ocr_mvp ---")
current_hs = ocr_mvp.CROP_RATIO_HEIGHT_START
current_he = ocr_mvp.CROP_RATIO_HEIGHT_END
current_ws = ocr_mvp.CROP_RATIO_WIDTH_START
current_we = ocr_mvp.CROP_RATIO_WIDTH_END

print(f"Current HS (from module): {current_hs:.4f}")
print(f"Current HE (from module): {current_he:.4f}")
print(f"Current WS (from module): {current_ws:.4f}")
print(f"Current WE (from module): {current_we:.4f}")

# Expected values from the modified setup_crop_interactively function
expected_hs_after_setup = 0.10
expected_he_after_setup = 0.20
expected_ws_after_setup = 0.15
expected_we_after_setup = 0.25

globals_updated_correctly = (
    np.isclose(current_hs, expected_hs_after_setup) and
    np.isclose(current_he, expected_he_after_setup) and
    np.isclose(current_ws, expected_ws_after_setup) and
    np.isclose(current_we, expected_we_after_setup)
)

if globals_updated_correctly:
    print("SUCCESS: Global crop ratios in ocr_mvp module correctly updated.")
else:
    print("FAILURE: Global crop ratios in ocr_mvp module NOT correctly updated.")

# --- Test 4: Crop with new global ratios ---
print("\n--- Test Script: Cropping with new global ratios (implicit) ---")
cropped_after_setup = ocr_mvp.extract_card_name_area(dummy_image)
shape_after = cropped_after_setup.shape
print(f"Shape of cropped image AFTER setup: {shape_after}")

# Calculate expected shape with new (test-defined) ratios
expected_h_after = int(dummy_image_height * (expected_he_after_setup - expected_hs_after_setup))
expected_w_after = int(dummy_image_width * (expected_we_after_setup - expected_ws_after_setup))
print(f"Expected shape AFTER: ({expected_h_after}, {expected_w_after}, 3)")

shape_after_correct = (shape_after[0] == expected_h_after and shape_after[1] == expected_w_after)

if shape_after_correct:
    print("SUCCESS: Crop shape AFTER setup is consistent with NEW global ratios.")
else:
    print("FAILURE: Crop shape AFTER setup is NOT consistent with new global ratios.")

# --- Final Verification ---
print("\n--- Test Script: Final Results ---")
if globals_updated_correctly and shape_after_correct and shape_before != shape_after:
    print("OVERALL SUCCESS: extract_card_name_area dynamically used the updated global crop ratios.")
else:
    print("OVERALL FAILURE: Conditions for dynamic update not fully met.")
    if not (shape_before != shape_after):
        print("Reason for failure: Shapes before and after are the same, indicating no change in effective ratios.")
    if not globals_updated_correctly:
        print("Reason for failure: Global variables were not updated as expected.")
    if not shape_after_correct:
         print(f"Reason for failure: Shape after update ({shape_after}) does not match expected ({expected_h_after}, {expected_w_after}).")


print("\n--- Test Script: Finished ---")
