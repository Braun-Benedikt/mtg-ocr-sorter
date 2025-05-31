import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow importing recognition and web_app
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from recognition.ocr_mvp import main_process_entries, init_db as ocr_init_db, setup_crop_interactively
    from web_app.database import init_db as webapp_init_db
except ModuleNotFoundError as e:
    print(f"Failed to import modules: {e}")
    print("Please ensure that the script is run from the project root directory")
    print("and all submodules (recognition, web_app) are present.")
    sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process Magic: The Gathering card images using OCR, store in DB."
    )
    
    parser.add_argument(
        "-i", "--image_dir",
        default=str(project_root / "tests" / "test_images"), # Default relative to project root
        type=str,
        help=f"Directory containing card images. Default: tests/test_images"
    )
    
    # Output CSV argument is removed as primary output is DB.
    # Kept for potential future use or if some part of ocr_mvp still uses it, but main flow is DB.
    # parser.add_argument(
    #     "-o", "--output_csv",
    #     default="tests/test_carddata.csv", # Default relative to project root
    #     type=str,
    #     help="Path to save the output CSV file (legacy). Default: tests/test_carddata.csv"
    # )
    
    parser.add_argument(
        "-d", "--dict_path",
        default=str(project_root / "recognition" / "cards" / "card_names_symspell_clean.txt"), # Default relative to project root
        type=str,
        help="Path to the SymSpell dictionary file. Default: recognition/cards/card_names_symspell_clean.txt"
    )
    
    parser.add_argument(
        "-ng", "--no_gui",
        action="store_true",
        help="Disable GUI image preview if image_dir processing is used."
    )

    parser.add_argument(
        "-uc", "--use_camera",
        action="store_true",
        help="Use the camera for image input instead of a directory. --image_dir is ignored if set."
    )

    parser.add_argument(
        "--init_db",
        action="store_true",
        help="Initialize the database before processing."
    )

    parser.add_argument(
        "--configure_crop",
        action="store_true",
        help="Run interactive crop configuration tool."
    )

    args = parser.parse_args()

    if args.configure_crop:
        print("Running interactive crop configuration tool...")
        setup_crop_interactively()
        # At this point, global crop ratios in ocr_mvp should be updated.
        # The user might be instructed by the tool to restart the main processing if they want to use new ratios.
        # Or, we can ask the user if they want to proceed with processing.
        # For now, let's just print a message and proceed.
        # If setup_crop_interactively handles its own errors/user exit, flow will continue here.
        print("Crop configuration finished. Proceeding with main script...")
        # Optionally, could add:
        # if not confirm_proceed("Do you want to continue with processing?"):
        #     sys.exit("User chose to exit after crop configuration.")


    if args.init_db:
        print("Initializing database (called from main.py)...")
        # It's better to use the one from web_app as it's the source of truth for DB schema
        webapp_init_db()
        # ocr_init_db() # This one is also fine as they should be identical

    print(f"Starting card processing:")
    abs_image_dir = os.path.abspath(args.image_dir) if not args.use_camera else 'N/A (Camera input)'
    abs_dict_path = os.path.abspath(args.dict_path)
    
    print(f"  Image Source: {'Camera' if args.use_camera else abs_image_dir}")
    print(f"  Dictionary Path: {abs_dict_path}")
    print(f"  Show GUI: {not args.no_gui}")

    # Call the main processing function from ocr_mvp
    main_process_entries(
        image_dir=args.image_dir if not args.use_camera else None,
        # output_csv_file=args.output_csv, # No longer primary, ocr_mvp doesn't use it for main flow
        dict_path=args.dict_path,
        show_gui_flag=not args.no_gui,
        use_camera=args.use_camera
    )

    print("Processing via main.py complete.")
