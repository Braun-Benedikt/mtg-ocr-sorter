import argparse
import os
import sys

# Add project root to sys.path if main.py is intended to be run from anywhere
# For this project structure, recognition.ocr_mvp should be importable if
# main.py is in the root and Python is run from the root.
# However, to be robust, especially if ocr_mvp itself has relative path logic
# for its own internal imports or file access that assumes a CWD,
# it might be good to ensure sys.path includes the project root.
# For now, let's assume direct import works as it's a common pattern.
try:
    from recognition.ocr_mvp import main as process_cards_main
except ModuleNotFoundError:
    # This block allows running main.py directly from the root project directory
    # even if the 'recognition' module isn't installed in the environment,
    # by adding the project root to sys.path.
    print("Module 'recognition.ocr_mvp' not found. Attempting to add project root to sys.path.")
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path: # Avoid adding duplicate paths
        sys.path.insert(0, project_root)
    try:
        from recognition.ocr_mvp import main as process_cards_main
    except ModuleNotFoundError as e:
        print(f"Failed to import 'recognition.ocr_mvp' even after adding project root to path: {e}")
        print("Please ensure that the script is run from the project root directory or that the project modules are correctly installed.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process Magic: The Gathering card images using OCR and Scryfall API."
    )
    
    parser.add_argument(
        "-i", "--image_dir",
        default="tests/test_images",
        type=str,
        help="Directory containing card images. Default: tests/test_images"
    )
    
    parser.add_argument(
        "-o", "--output_csv",
        default="tests/test_carddata.csv",
        type=str,
        help="Path to save the output CSV file. Default: tests/test_carddata.csv"
    )
    
    parser.add_argument(
        "-d", "--dict_path",
        default="recognition/cards/card_names_symspell_clean.txt",
        type=str,
        help="Path to the SymSpell dictionary file. Default: recognition/cards/card_names_symspell_clean.txt"
    )
    
    parser.add_argument(
        "-ng", "--no_gui",
        action="store_true", # Default is False. If flag is present, args.no_gui becomes True.
        help="Disable GUI image preview. If set, GUI will not be shown."
    )

    args = parser.parse_args()

    # The `main` function in ocr_mvp.py expects `show_gui_flag`.
    # `ocr_mvp.main` has a default `show_gui_flag=True`.
    # If args.no_gui is True (because --no_gui was specified), then show_gui_flag should be False.
    # If args.no_gui is False (default, --no_gui not specified), then show_gui_flag should be True.
    # So, show_gui_flag = not args.no_gui
    
    print(f"Starting card processing with the following settings:")
    # Use os.path.abspath to show full paths for clarity
    print(f"  Image Directory: {os.path.abspath(args.image_dir)}")
    print(f"  Output CSV: {os.path.abspath(args.output_csv)}")
    print(f"  Dictionary Path: {os.path.abspath(args.dict_path)}")
    print(f"  Show GUI: {not args.no_gui}")

    process_cards_main(
        image_dir=args.image_dir,
        output_csv_file=args.output_csv,
        dict_path=args.dict_path,
        show_gui_flag=not args.no_gui
    )

    print("Processing complete.")
